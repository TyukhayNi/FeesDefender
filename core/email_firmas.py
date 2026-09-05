"""Leer la firma de un correo: quien firma, con que telefono y con que cargo.

NO conoce el CRM. Devuelve lo que dice el correo, con la constancia de lo que no pudo
leer; quien decide que hacer con eso es `scripts/crm_colaboradores_firmas.py`.

Verdad de campo que fija el diseno, medida el 2026-09-04 sobre los 6 `.eml` de W-02Q38C:

- **Solo 3 de 6 traen marcador de firma.** Anclar el localizador en el marcador pierde la
  mitad en silencio. Lo que aparece en los 6 bloques es una **linea con la direccion
  corporativa**, asi que el ancla es esa y el marcador solo aprieta el limite superior.
- **La firma del cuerpo NO es la del `From:`.** En 2 de los 6 pertenece a otra persona
  (un reenvio, y un bloque citado). Por eso la atribucion sale del email de la **linea
  ancla** que creo el bloque -- nunca de una busqueda posterior en su texto, que puede
  contener tambien la direccion de una firma vecina -- y un bloque sin email no se
  atribuye a nadie.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path

from core.utils import normalize_es_phone

#: El colaborador es personal propio del cliente (E&V). Una direccion de otro dominio
#: no se mira: un tercero de la operacion no es un colaborador del despacho.
DOMINIO_COLABORADOR = "engelvoelkers.com"

#: Cuantas lineas hacia atras se mira desde la linea del email cuando NO hay marcador.
#: Las dos plantillas medidas caben en 12; con mas se empieza a arrastrar prosa.
_VENTANA_ATRAS = 12
#: Y cuantas hacia delante: en la plantilla de Barcelona el email va al final, pero
#: queda un `<direccion>` de cortesia detras.
_VENTANA_ADELANTE = 4

#: [ \t] y no \s: \s incluye el salto de linea, y una linea de cita vacia (un ">" solo,
#: sin nada detras) se comeria el salto y fusionaria esa linea con la siguiente (H-02).
_RE_CITA = re.compile(r"(?m)^[ \t]*>+[ \t]?")

_RE_MARCADOR = re.compile(
    r"(?im)^\s*(?:--\s*|enviado desde mi.*|sent from my.*|obtener outlook.*|get outlook.*)$"
)

#: El dominio se reconoce COMPLETO, con su final anclado (H-02, R1): sin esto,
#: "ana@engelvoelkers.com.tercero.example" -- el dominio de un TERCERO que solo
#: EMPIEZA como el nuestro -- se leia como "ana@engelvoelkers.com", una direccion
#: que no esta en el texto. El doble lookahead negativo dice: lo que sigue al
#: dominio no puede ser (a) un caracter que extienda la MISMA etiqueta
#: (letra/digito/guion), ni (b) un punto seguido de otra etiqueta de dominio
#: (".tercero", ".example"...). Un punto SUELTO de fin de frase, sin mas dominio
#: detras ("...ana@engelvoelkers.com."), sigue reconociendose: ahi el punto no va
#: seguido de una letra/digito/guion, asi que (b) no se dispara.
_RE_EMAIL_COLAB = re.compile(
    r"[\w.+-]+@" + DOMINIO_COLABORADOR.replace(".", r"\.") + r"(?![\w-])(?!\.[\w-])",
    re.IGNORECASE,
)

#: Que convierte una direccion en una FIRMA. Sin al menos una de estas, una direccion
#: suelta en un texto produciria una «firma» inventada de quien solo se menciona.
#:
#: La marca, la razon social y la etiqueta de telefono van ANCLADAS a linea propia
#: (H-01): el corpus entero es correspondencia SOBRE operaciones de E&V, asi que "la
#: marca aparece en algun punto de la ventana" no es una puerta, es la norma. Un correo
#: que solo MENCIONA la gestion de E&V de paso, con una direccion suelta de un
#: colaborador sin firmar, no debe corroborar. La propiedad es que la ventana tenga
#: FORMA de firma:
#:   - la marca y la razon social estan SOLAS en su propia linea, nada mas (admitiendo
#:     asteriscos de negrita, forma juridica y puntuacion alrededor) -- una razon
#:     social que arranca una frase en prosa ("EV MMC SPAIN es la empresa que...") no
#:     tiene esa forma y no debe corroborar (hallazgo B, R2);
#:   - una etiqueta de telefono solo corrobora si lo que la sigue tiene FORMA de
#:     telefono (digitos, espacios, +, ., -, (, ), *, <, > y una extension opcional al
#:     final, "/ Ext. NNNN") y nada mas en la linea -- una etiqueta seguida de prosa
#:     ("Telefono de atencion al cliente 900 123 456...") no corrobora (hallazgo C, R2).
#:
#: Los separadores INTERNOS de la marca y de la razon social son `[ \t]*`/`[ \t]+` y
#: no `\s*`/`\s+` (hallazgo D, R2, para la marca; H-10, R1, para la razon social --
#: EL MISMO defecto, cerrado para una alternativa y dejado abierto para la de al
#: lado): `\s` incluye el salto de linea, y dejaria corroborar "ENGEL"/"VOLKERS" o
#: "EV"/"MMC"/"SPAIN" en lineas DISTINTAS separadas por saltos (que no tiene forma
#: de firma real). El precio deliberado de este cierre: una marca o razon social
#: partida en varias lineas por el ajuste de longitud del cliente de correo deja de
#: reconocerse. Es el intercambio correcto -- se prefiere perder una firma
#: legitima a inventar una. NO "arreglar" esto volviendo a `\s*`/`\s+`.
#:
#: La alternativa de telefono exige ADEMAS que lo que sigue a la etiqueta tenga al
#: menos un DIGITO (H-10, R1): la clase `[0-9+()*<>.\- \t]+` admitia una linea de
#: solo signos ("Móvil: ---", sin un solo digito) como si tuviera forma de
#: telefono. La propiedad es que corrobore un TELEFONO, no una etiqueta seguida de
#: cualquier combinacion de signos -- por eso el digito obligatorio va en medio
#: (`[+()*<>.\- \t]*\d[0-9+()*<>.\- \t]*`), permitiendo cualquier cantidad de
#: signos antes y despues, pero exigiendo que exista al menos uno.
_RE_CORROBORA = re.compile(
    r"(?im)^\s*\*?\s*engel[ \t]*&?[ \t]*v[öo]lkers\s*\*?\s*$"
    r"|^\s*\*?[ \t]*ev[ \t]+mmc[ \t]+spain[ \t]*,?[ \t]*"
    r"(?:s\.?[ \t]*l\.?[ \t]*u\.?|s\.?[ \t]*l\.?|s\.?[ \t]*a\.?)?\.?[ \t]*\*?[ \t]*$"
    r"|^\s*\*?\s*(?:telf|tel[ée]fono|tel\.\s*fijo|m[óo]vil|movil|mobile)\b"
    r"[ \t]*:?[ \t]*"
    r"[+()*<>.\- \t]*\d[0-9+()*<>.\- \t]*"
    r"(?:[ \t]*/[ \t]*ext\.?[ \t]*\d+)?"
    r"[ \t]*\.?[ \t]*\*?[ \t]*$"
)


def desmarcar(texto: str) -> str:
    """Quita las marcas de cita `>` del principio de cada linea.

    Garantia exacta (Hallazgo E, R2): `len(desmarcar(t).split("\\n")) ==
    len(t.split("\\n"))` para cualquier `t` -- el numero de lineas se conserva, y con
    el la correspondencia posicional (la linea i del texto original es la linea i del
    desmarcado). Esto se comprueba con `split("\\n")`, NO con `splitlines()`:
    `splitlines()` no cuenta el segmento vacio final (`''.splitlines() == []` pero
    `''.split("\\n") == ['']`), asi que compara mal cuando el texto termina en `>` o en
    una linea vacia. La task siguiente cruza el numero de linea de un bloque
    desmarcado contra las zonas citadas del texto original, y depende de esta garantia
    medida con el instrumento correcto.

    **No toca los asteriscos de negrita**: `leer_campos` los necesita para localizar la
    linea del nombre, que es lo que posiciona el cargo (que no tiene etiqueta).
    """
    return _RE_CITA.sub("", texto or "")


@dataclass(frozen=True)
class BloqueFirma:
    """Un bloque que parece una firma, con de donde salio.

    `procedencia` la rellena `atribuir` (Task 6): `"directo"` o `"citado"`.
    """
    texto: str
    email: str = ""
    linea: int = 0
    fichero: str = ""
    procedencia: str = "directo"


#: Verbos con los que un cliente de correo introduce el mensaje citado, seguidos de
#: dos puntos ("...Ferran <email> va escriure:", "...escribio:", "...wrote:",
#: "...schrieb:"). Task 12, defecto medido 2026-09-05 sobre un correo real de
#: W-02Q38C: esta linea trae una direccion @engelvoelkers.com que HOY ancla un
#: bloque como cualquier otra, y su ventana (que mira hasta `_VENTANA_ATRAS` lineas
#: hacia atras) puede cubrir la firma de OTRA persona que este justo encima -- ver
#: `_es_cabecera_de_cita`.
#:
#: LISTA DELIBERADAMENTE INCOMPLETA -- no se persigue el caso general (cada cliente
#: de correo y cada idioma tiene su propia frase de atribucion). Cubre los 4 verbos
#: medidos o mas habituales: espanol ("escribio"/"escribió"), catalan ("va
#: escriure"), ingles ("wrote"), aleman ("schrieb"). NO cubre frances ("a ecrit"),
#: italiano ("ha scritto"), portugues ("escreveu") ni ningun otro idioma o variante
#: de cliente de correo no medida -- una cabecera en esas formas NO se descarta hoy
#: y puede seguir anclando un bloque bogus. Ampliar esta lista es seguro (solo
#: reduce el conjunto de bloques que se crean), pero unicamente cuando el corpus
#: real mida una forma nueva -- no por anticipacion.
_RE_ATRIBUCION_VERBO = re.compile(r"(?i)\b(?:escribi[oó]|va\s+escriure|wrote|schrieb)\s*:")

#: La cabecera Outlook De:/From: precede a la direccion en su MISMA linea
#: ("De: Nombre <email>" / "From: Name <email>"). Anclada a inicio de linea (con el
#: doble punto obligatorio justo detras, salvo espacios) para no disparar con el
#: "de" comun del castellano en mitad de una frase ("De acuerdo con..."): sin la
#: exigencia del `:` inmediato, cualquier linea que empezara por "de " colaria.
_RE_ATRIBUCION_LABEL = re.compile(r"(?i)^\s*(?:de|from)\s*:")


def _es_cabecera_de_cita(lineas: list[str], i: int) -> bool:
    """La linea `i` (donde se ancloria un bloque) pertenece a una cabecera de
    atribucion de cita y por tanto NO debe anclar nada.

    Se comprueba tambien la linea ANTERIOR y la SIGUIENTE para el verbo (no para
    la etiqueta De:/From:, que siempre precede a la direccion en su propia
    linea): el envoltorio del cliente de correo puede partir la cabecera en dos
    lineas, con la direccion sola en una y el verbo+":" en la otra. Se han medido
    los DOS sentidos de ese corte: el catalan real parte "...Nombre <" /
    "email> va escriure:" (verbo en la MISMA linea que la direccion, la
    fecha/nombre en la ANTERIOR); y un segundo caso real (Task 12+, R1, H-03)
    parte "...Nombre <email>" / "escribió:" (la direccion sola en su linea, el
    verbo en la SIGUIENTE). Mirar solo una de las dos direcciones deja abierto el
    cruce de identidad que motivo el filtro: con solo la anterior cubierta, esta
    segunda forma SI anclaba un bloque -- y su ventana, mirando hacia atras, podia
    alcanzar la firma real de otra persona.
    """
    candidatas = [lineas[i]]
    if i > 0:
        candidatas.append(lineas[i - 1])
    if i + 1 < len(lineas):
        candidatas.append(lineas[i + 1])
    if any(_RE_ATRIBUCION_VERBO.search(c) for c in candidatas):
        return True
    return bool(_RE_ATRIBUCION_LABEL.match(lineas[i]))


def localizar_bloques(texto: str, *, fichero: str = "") -> list[BloqueFirma]:
    """Los bloques que parecen una firma, uno por linea con direccion corroborada.

    Desmarca el texto ANTES de buscar (Hallazgo A, R2 -- regresion del arreglo de R1):
    las anclas de `_RE_CORROBORA` exigen inicio de linea, y no pueden depender de si
    el llamador ya le paso el texto desmarcado o no. `desmarcar` es idempotente (un
    texto sin `>` no cambia), asi que un llamador que ya desmarco no sufre nada -- y
    esto es lo que permite localizar una firma CITADA linea a linea (un reenvio con
    `>` en cada linea), que es justo uno de los dos escenarios que motivan el modulo
    entero (ver docstring de cabecera).

    Las lineas se cuentan con `split("\\n")`, NO con `splitlines()` (H-06, R1):
    `splitlines()` trata como salto de linea un conjunto MAS AMPLIO de caracteres
    (entre otros, U+2028/U+2029), y `zonas_citadas` -- que `atribuir` cruza con
    `linea` para decidir la procedencia -- cuenta con `split("\\n")`. Si aqui se
    contara distinto, un texto con uno de esos separadores desalinearia los dos
    recuentos y `atribuir` consultaria la citacion de una linea que no es. Usar la
    misma convencion en los dos sitios es lo que mantiene el cruce alineado; ver
    tambien el docstring de `desmarcar`, cuya garantia esta medida con este mismo
    instrumento.

    Un mismo correo puede dar varios bloques para la misma persona (la plantilla de
    Barcelona repite la direccion al final); `consolidar` los une.

    Una direccion en una cabecera de atribucion de cita ("...fulano@ev.com>
    escribio:") NO ancla bloque (Task 12, defecto medido 2026-09-05): esa direccion
    no firma nada, solo aparece porque el cliente de correo cita al autor del
    mensaje anterior -- y su ventana, mirando hacia atras, puede cubrir la firma de
    OTRA persona real. Ver `_es_cabecera_de_cita`.

    **Cada bloque se acota por SU PROPIA firma, no por la del vecino** (H-01,
    CRITICO, R1): con dos firmas seguidas y sin separacion de sobra, la ventana
    fija (`_VENTANA_ATRAS`/`_VENTANA_ADELANTE`) de una persona alcanzaba los campos
    de la persona de al lado -- hacia atras (la firma de abajo arrastraba el movil
    de la de arriba) y hacia delante (un marcador `-- ` que viene DESPUES del ancla
    no limitaba nada, asi que una simple mencion de una direccion arrastraba la
    firma de quien viniera detras). La propiedad: los bloques se calculan en DOS
    pasadas. La primera fija el INICIO de cada uno con el criterio de siempre
    (marcador anterior, ventana fija) ACOTADO ADEMAS por donde termina el bloque
    anterior. La segunda fija el FIN de cada uno con el criterio de siempre
    (marcador posterior, ventana fija) ACOTADO ADEMAS por donde EMPIEZA el
    siguiente bloque (su propio `inicio`, no solo la linea de su ancla): asi
    ningun bloque puede leer ni un campo que ya pertenece al de al lado, y los
    bloques nunca se solapan.
    """
    texto = desmarcar(texto)
    lineas = texto.split("\n")
    marcadores = [i for i, ln in enumerate(lineas) if _RE_MARCADOR.match(ln)]
    anclas = [i for i, ln in enumerate(lineas)
             if _RE_EMAIL_COLAB.search(ln) and not _es_cabecera_de_cita(lineas, i)]

    # Primera pasada: el INICIO de cada bloque. Igual que siempre (marcador
    # anterior mas cercano, o ventana fija hacia atras), acotado ademas por donde
    # termina el bloque anterior -- para que la ventana de este nunca alcance un
    # campo que es del anterior.
    inicios: list[int] = []
    for pos, i in enumerate(anclas):
        previos = [m for m in marcadores if m < i]
        candidato_marcador = previos[-1] + 1 if previos else 0
        limite_bloque_anterior = anclas[pos - 1] + 1 if pos > 0 else 0
        inicios.append(max(candidato_marcador, i - _VENTANA_ATRAS, limite_bloque_anterior))

    bloques: list[BloqueFirma] = []
    for pos, i in enumerate(anclas):
        m_ancla = _RE_EMAIL_COLAB.search(lineas[i])
        inicio = inicios[pos]

        # El marcador mas cercano por DEBAJO aprieta el limite inferior, en espejo
        # del que aprieta el superior: sin esto, un marcador que viene DESPUES del
        # ancla (p.ej. una mencion de paso justo antes de un "-- " real de otra
        # persona) no limitaba nada y la ventana arrastraba la firma siguiente.
        siguientes = [m for m in marcadores if m > i]
        candidato_marcador_fin = siguientes[0] if siguientes else len(lineas)
        # Y el bloque siguiente empieza donde su PROPIO `inicio` (ya acotado)
        # dice, no en la linea cruda de su ancla: eso es lo que impide que este
        # bloque alcance a leer un campo que ya quedo dentro del bloque de al
        # lado (H-01).
        limite_bloque_siguiente = inicios[pos + 1] if pos + 1 < len(anclas) else len(lineas)
        fin = min(candidato_marcador_fin, i + 1 + _VENTANA_ADELANTE, limite_bloque_siguiente)
        cuerpo = "\n".join(lineas[inicio:fin])

        if not _RE_CORROBORA.search(cuerpo):
            continue
        # El email del bloque es el de SU LINEA ANCLA (`m_ancla`), no uno que se
        # vuelva a buscar despues dentro de `cuerpo`. La ventana de un bloque
        # puede contener MAS de una direccion -- la propia y la de una firma
        # vecina, cuando dos firmas caen a menos de _VENTANA_ATRAS/_VENTANA_ADELANTE
        # lineas de distancia -- y una busqueda posterior en el texto no tiene
        # forma de distinguir cual de las dos era la que disparo ESTE bloque.
        # `atribuir` ya no re-deriva el email; lo toma de aqui (Task 6, hallazgo
        # espejo del 2026-09-04).
        #
        # `linea` es la del ANCLA (`i`), NO la del inicio de la ventana (H-06,
        # R1): `atribuir` la usa para decidir la procedencia, y la linea que
        # identifica de quien es la firma es la del ancla -- la ventana puede
        # empezar varias lineas por encima, en prosa que no esta citada aunque
        # el ancla si lo este (o al reves).
        bloques.append(BloqueFirma(
            texto=cuerpo, email=m_ancla.group(0).lower(), linea=i + 1, fichero=fichero,
        ))
    return bloques


PROCEDENCIA_DIRECTO = "directo"
PROCEDENCIA_CITADO = "citado"


def zonas_citadas(texto: str) -> list[tuple[int, int]]:
    """Rangos de linea (0-indexed, fin exclusivo) que llegan con marca de cita.

    Se calculan sobre el texto ORIGINAL, antes de desmarcar: despues ya no se distingue
    lo citado de lo escrito.

    Cuenta las lineas con `split("\\n")`, NO con `splitlines()`: es la misma convencion
    con la que `desmarcar` tiene medida y documentada su garantia de conservar el
    indice de linea (ver su docstring). `localizar_bloques` calcula `linea` sobre
    `texto.split("\\n")` del texto DESMARCADO -- la MISMA convencion, no una
    parecida.

    **Ojo, esto NO es "solo difieren en el segmento vacio final"** (H-06, R1: la
    version anterior de este comentario lo afirmaba, y es falso). `splitlines()`
    trata como salto de linea un conjunto de caracteres MAS AMPLIO que `split("\\n")`
    -- entre otros, el separador de linea Unicode U+2028 y el separador de parrafo
    U+2029 -- asi que un texto que contenga alguno de esos dos metodos de contar
    lineas puede DIFERIR en TODA la numeracion a partir de ahi, no solo en el
    ultimo segmento. Medido: la cadena `"a\\u2028b\\u2028c\\u2028d\\u2028e\\n--\\n"
    "> ENGEL&VOLKERS\\n> Móvil: 611111111\\n> ana@engelvoelkers.com"` da 5 lineas
    con `split("\\n")` (lo que cuenta esta funcion) y 9 con `splitlines()` (lo que
    contaba antes `localizar_bloques`): el indice del ancla quedaba fuera del rango
    que esta funcion conocia, y la firma salia `directo` aunque estuviera citada.
    La garantia que SI es cierta -- y la que de verdad importa aqui -- es que
    `localizar_bloques` cuenta con esta MISMA funcion (`split("\\n")`), asi que los
    indices de las dos siempre se refieren a la misma linea.
    """
    zonas: list[tuple[int, int]] = []
    inicio: int | None = None
    lineas = texto.split("\n")
    for i, ln in enumerate(lineas):
        if _RE_CITA.match(ln):
            if inicio is None:
                inicio = i
        elif inicio is not None:
            zonas.append((inicio, i))
            inicio = None
    if inicio is not None:
        zonas.append((inicio, len(lineas)))
    return zonas


def _en_zona_citada(linea0: int, zonas: list[tuple[int, int]]) -> bool:
    return any(a <= linea0 < b for a, b in zonas)


def atribuir(bloques: list[BloqueFirma], *,
             texto_original: str) -> tuple[list[BloqueFirma], int]:
    """Pone a cada bloque su procedencia; el email ya lo trae puesto.

    **El bloque se identifica con el email que lo ANCLO en `localizar_bloques`,
    nunca con uno que se busque de nuevo aqui.** Medido el 2026-09-04: el texto de
    un bloque es una ventana de lineas alrededor de su ancla, y esa ventana puede
    contener MAS de una direccion -- la propia y la de una firma vecina, cuando dos
    firmas caen a menos de `_VENTANA_ATRAS`/`_VENTANA_ADELANTE` lineas de distancia.
    Volver a buscar en el texto no tiene forma de saber cual de las direcciones que
    aparecen era la que disparo ESTE bloque; el ancla si lo sabe, porque es la unica
    linea que se miro para crearlo. Una primera version de este arreglo cambio
    "primer match" por "ultimo match" y solo cerro la mitad del problema (el caso
    hacia atras); la otra mitad -- el espejo, dos firmas seguidas donde la ventana
    hacia atras de la PRIMERA alcanza tambien a la SEGUNDA -- seguia rota porque
    seguia siendo una busqueda en texto compartido.

    Sigue siendo cierto que el email nunca sale de la cabecera `From:` -- medido el
    2026-09-04: en 2 de los 6 .eml de W-02Q38C la firma del cuerpo pertenece a otra
    persona (un reenvio, y un bloque citado). Atribuir por cabecera escribiria el
    telefono de una persona en la ficha de otra, en el CRM del cliente. Por eso esta
    funcion **no recibe el remitente**: no es que decida ignorarlo, es que no lo
    tiene.

    Un bloque sin email (la rama defensiva: hoy todo bloque de `localizar_bloques`
    trae uno por construccion, pero un `BloqueFirma` puede construirse a mano sin
    el, o de otra via de deteccion futura) se descarta y se cuenta.
    """
    zonas = zonas_citadas(texto_original)
    atribuidos: list[BloqueFirma] = []
    sin_atribuir = 0
    for b in bloques:
        if not b.email:
            sin_atribuir += 1
            continue
        procedencia = (PROCEDENCIA_CITADO if _en_zona_citada(b.linea - 1, zonas)
                       else PROCEDENCIA_DIRECTO)
        atribuidos.append(BloqueFirma(
            texto=b.texto, email=b.email, linea=b.linea,
            fichero=b.fichero, procedencia=procedencia,
        ))
    return atribuidos, sin_atribuir


def extraer_bloques(texto: str, *,
                    fichero: str = "") -> tuple[list[BloqueFirma], int]:
    """Localizar + atribuir.

    Las zonas citadas se calculan sobre el texto ORIGINAL: despues de desmarcar ya no se
    distingue lo citado de lo escrito. `localizar_bloques` desmarca por su cuenta desde
    la Task 5, asi que aqui se le pasa el texto tal cual.
    """
    bloques = localizar_bloques(texto, fichero=fichero)
    return atribuir(bloques, texto_original=texto)


# ---------------------------------------------------------------------------
# Veredictos: «no lo se» y «no hay» no son lo mismo
#
# Un dato que no se pudo mirar NUNCA se convierte en un dato que no existe. Un .eml
# ilegible no autoriza a escribir que ese colaborador no tiene telefono.
# ---------------------------------------------------------------------------

VEREDICTO_ENCONTRADO = "ENCONTRADO"
#: Hay firma de esta persona y NO trae ese campo. Medido: una de las dos plantillas
#: corporativas no incluye movil. No significa «no tiene movil».
VEREDICTO_FIRMA_SIN_CAMPO = "FIRMA_SIN_CAMPO"
#: La persona aparece en el corpus y no se le encontro bloque de firma.
VEREDICTO_SIN_FIRMA = "SIN_FIRMA"
#: NOTA: NO hay `VEREDICTO_NO_ATRIBUIBLE`. El §6 del spec lo preveia, pero con el ancla
#: del bloque siendo el propio email, TODO bloque tiene email por construccion: seria una
#: constante que nada puede emitir. `atribuir` conserva la rama defensiva y su contador
#: como INVARIANTE, con un test que lo fija en 0. Si alguien anade una segunda via de
#: deteccion —bloques anclados solo en el marcador, como la firma institucional sin
#: direccion personal que se midio en un .eml de W-02Q38C— ese test se pondra rojo y le
#: dira que ahi si hace falta un veredicto de verdad.
#: El .eml no se pudo parsear o no tiene parte text/plain. SE DECLARA.
VEREDICTO_NO_LEIBLE = "NO_LEIBLE"
#: Dos valores distintos y ninguno decide. Se falla cerrado.
VEREDICTO_CONFLICTO = "CONFLICTO"

#: `Telf:` y `Tel. Fijo:` son FIJO. Se prueba movil primero para que `Móvil:` no caiga
#: en el patron del fijo: un cruce mete un fijo en el campo `movil`, que es el que la
#: UI del CRM muestra en el listado.
#:
#: La propiedad es que una etiqueta que NOMBRA el movil es un movil este donde este
#: dentro de la etiqueta (defecto medido 2026-09-04): `Teléfono móvil:` / `Telefono
#: movil:` / `Tel. móvil:` son etiquetas reales y frecuentes en firmas espanolas, y
#: antes de este arreglo `_RE_MOVIL` estaba anclada a inicio de linea con SOLO la
#: palabra movil como alternativa -- la linea empieza por "Teléfono", no por "móvil",
#: asi que _RE_MOVIL nunca llegaba a probarse y la linea entera caia en `_RE_FIJO`
#: (que si tiene `tel[ée]fono`/`tel\.` entre sus alternativas). El arreglo no es
#: "probar movil antes que fijo" -- eso ya se hacia y no bastaba, porque el ancla de
#: `_RE_MOVIL` le impedia ver la linea -- es admitir un prefijo `Teléfono`/`Tel.`
#: opcional ANTES de la palabra movil, para que la etiqueta compuesta entera quede
#: reconocida como movil.
#: `Tel:` y `Mob:` (Task 12, defecto medido 2026-09-05 sobre un correo real de
#: W-02Q38C): la firma trae esas dos abreviaturas cortas -- sin punto, sin "fono",
#: sin "vil"/"ile" -- y ninguna de las dos estaba en las listas de abajo. Esa
#: persona salia en el informe con FIRMA_SIN_CAMPO en movil Y en fijo, afirmando
#: una ausencia que la firma no tiene.
#:
#: Las dos se anaden AL FINAL de su alternancia y con los DOS PUNTOS obligatorios
#: (`tel\s*:` / `mob\s*:`), no sueltas como el resto de abreviaturas de esta lista.
#: Motivo: alternancia de regex prueba las opciones en ORDEN y se queda con la
#: PRIMERA que permite completar el resto del patron -- no con la mas larga. El
#: resto del patron (`\s*[:.]?\s*(.+?)\s*$`) es tan permisivo que casi cualquier
#: contenido tras la etiqueta lo completa, asi que si `tel`/`mob` fueran sueltas y
#: SIN dos puntos exigidos, tendrian que ir tras `telf`/`tel[ée]fono`/`tel\.`/
#: `mobile`/`m[óo]v\.?` para no robarles el match (p.ej. `tel` suelta ANTES de
#: `telf` en la lista dejaria `Telf:` leyendose como fijo="f: 931112233"). Puestas
#: al final ya no roban nada a esas -- se prueban primero y ganan porque son mas
#: especificas. Pero `tel`/`mob` sueltas siguen siendo el prefijo de palabras
#: normales ("telecomunicaciones", "mobiliario"...) y `.search()` se queda con la
#: PRIMERA linea del texto que case, asi que una linea de prosa asi ANTES de la
#: firma real robaria el match entero (el fallo callado seria peor que el de
#: partida: no "no reconocido", sino "reconocido en la linea equivocada"). Exigir
#: los dos puntos es justo lo medido en el corpus (`Tel:`, `Mob:`) y cierra ese
#: hueco sin tocar ninguna alternativa existente.
_RE_MOVIL = re.compile(
    r"(?im)^\s*\*?\s*(?:tel[ée]fono|tel\.)?\s*(?:m[óo]vil|mobile|m[óo]v\.?|mob\s*:)"
    r"\s*[:.]?\s*(.+?)\s*$")
_RE_FIJO = re.compile(
    r"(?im)^\s*\*?\s*(?:telf|tel\.?\s*fijo|tel[ée]fono|tel\.|phone|tel\s*:)"
    r"\s*[:.]?\s*(.+?)\s*$")

#: Una linea ENTERAMENTE en negrita. La primera es el nombre; el cargo es la siguiente
#: linea no vacia, en negrita o no (las dos plantillas medidas difieren en eso).
_RE_NEGRITA = re.compile(r"^\s*\*(.+?)\*\s*$")

#: Lo que una linea tras el nombre puede ser sin ser un cargo. LISTA NEGRA, no
#: blanca (Hallazgo D, revision tasks 7-8: ver docstring de `_cargo_de` para la
#: limitacion que eso implica).
_RE_NO_ES_CARGO = re.compile(
    r"(?i)engel\s*&?\s*v[öo]lkers"
    r"|ev\s+mmc|s\.?l\.?u|s\.?a\.?$"
    r"|@"
    r"|^\s*\*?\s*(?:telf|tel|tel[ée]fono|m[óo]vil|movil|mobile|mailto|fax)\b"
    r"|\d{4,}"                       # un CP o un numero largo: es direccion
    r"|^\s*\*?\s*(?:c/|calle|avinguda|avenida|passeig|plaza|pl\.|paseo)\b"
    r"|www\.|://"                    # una URL (Hallazgo D)
)


def _mayoritariamente_digitos_y_signos(linea: str) -> bool:
    """Un horario o un codigo: la linea tiene tantos o mas digitos que letras.

    Exclusion barata del Hallazgo D (revision tasks 7-8): no calcula una proporcion
    exacta sobre todos los caracteres de la linea, solo cuenta digitos contra
    letras -- un cargo real (todo letras, cero o muy pocos digitos) no la dispara;
    un horario ("Lu-Vi 9:00-18:00", 7 digitos contra 4 letras) o un codigo si.
    """
    letras = sum(c.isalpha() for c in linea)
    digitos = sum(c.isdigit() for c in linea)
    return digitos > 0 and digitos >= letras


_RE_EXTENSION = re.compile(r"(?i)\s*(?:/|\bext\b|\bextension\b|\bextensión\b).*$")

#: Lo que queda tras limpiar TIENE que SER un telefono, y no cualquier longitud
#: (Hallazgo A, revision tasks 7-8): un ESPANOL (sin `+` -- `normalize_es_phone` ya
#: le quito el `+34`/`0034` si lo traia) tiene que ser EXACTAMENTE 9 digitos, que es
#: lo que exige el CRM (`HTTP 400 movil is incorrect` con cualquier otra cosa). Antes
#: de este arreglo "solo digitos, cualquier longitud" colaba un fijo y un movil
#: pegados (13 digitos) o un movil truncado (7) como si fueran telefono valido, y
#: como el escritor al CRM se traga el error a proposito, el rechazo del CRM habria
#: fallado en SILENCIO. Un EXTRANJERO (`+` seguido de digitos: los que
#: `normalize_es_phone` conserva a proposito, `+33...` etc.) no se somete a los 9
#: digitos -- su longitud la decide su pais. Cualquier otra cosa -- una etiqueta que
#: se colo entera, una frase con un numero de atencion al cliente dentro, una
#: direccion con el numero del piso -- NO es un telefono aunque contenga digitos.
#: Ver `limpiar_telefono`.
_RE_TELEFONO_VALIDO = re.compile(r"^(?:\d{9}|\+\d+)$")


@dataclass(frozen=True)
class DatosFirma:
    """Lo que dice UN bloque de firma. Los campos vacios NO afirman ausencia.

    `campos_en_conflicto` (H-04, R1): nombres de campo ("movil"/"telefono") para
    los que ESTE MISMO bloque trae dos o mas valores validos y DISTINTOS -- p.ej.
    dos lineas `Móvil:` con numeros distintos en una sola firma. No hay
    informacion para elegir entre ellos: eso es incertidumbre, no un dato, y
    `consolidar` lo traduce al `VEREDICTO_CONFLICTO` que ya existe (nunca se
    inventa un veredicto nuevo). Vacio en el caso normal (cero o un valor).
    """
    email: str
    movil: str = ""
    telefono: str = ""
    cargo: str = ""
    procedencia: str = PROCEDENCIA_DIRECTO
    fichero: str = ""
    linea: int = 0
    campos_en_conflicto: frozenset[str] = frozenset()


def limpiar_telefono(valor: str) -> str:
    """El numero que hay en una linea de firma, listo para el CRM.

    `normalize_es_phone` no quita letras ni asteriscos, y los valores llegan sucios: la
    negrita HTML degrada a `*` en el text/plain, y la plantilla de Madrid pega la
    extension detras (`+34 912 345 678 / Ext. 1234`). La extension no es parte del
    numero, y el CRM exige 9 digitos o devuelve HTTP 400 (`[APER-14]`).

    **El valor limpio tiene que SER un telefono, no meramente contener un digito**
    (defecto medido 2026-09-04): la comprobacion final era `any(c.isdigit() for c in
    v)`, una guarda inerte que acepta cualquier cosa con un digito dentro --
    `"movil:612345678"` la pasaba entera, letras y dos puntos incluidos, como si
    fuera un telefono. Tras quitar extension/asteriscos/separadores y pasar por
    `normalize_es_phone`, lo que queda tiene que ser SOLO digitos, o un `+` seguido
    de SOLO digitos (los extranjeros que `normalize_es_phone` deja intactos a
    proposito) -- cualquier otra cosa devuelve cadena vacia.

    **Y un espanol tiene que ser EXACTAMENTE 9 digitos** (Hallazgo A, revision tasks
    7-8): "solo digitos" no es lo mismo que "es un telefono espanol" -- el CRM exige
    9 digitos y devuelve HTTP 400 con cualquier otra longitud, y como el escritor al
    CRM se traga el error a proposito, un valor de longitud equivocada habria
    fallado en silencio. Los extranjeros (`+` que sobrevive a `normalize_es_phone`
    porque no era `+34`/`0034`) quedan fuera de esta regla: su longitud la decide su
    pais. Es mejor no tener el telefono que escribir una cadena que el CRM va a
    rechazar en la ficha del cliente.
    """
    v = _RE_EXTENSION.sub("", valor or "")
    v = v.replace("*", "").replace("<", "").replace(">", "").strip()
    v = normalize_es_phone(v)
    return v if _RE_TELEFONO_VALIDO.match(v) else ""


def _cargo_de(lineas: list[str]) -> str:
    """El cargo, por POSICION: no tiene etiqueta en ninguna de las dos plantillas.

    Regla medida: la primera linea enteramente en negrita es el NOMBRE, y el cargo es
    la siguiente linea no vacia — en negrita en la plantilla de Madrid, sin negrita en
    la de Barcelona. Si esa linea es la razon social, una direccion, un telefono, un
    email, una URL o un horario/codigo, no hay cargo: **antes vacio que inventado**.

    **Esto es una lista NEGRA, nunca una blanca** (Hallazgo D, revision tasks 7-8,
    Minor): el conjunto de cargos reales es abierto -- no se puede enumerar "los
    cargos posibles" -- asi que `_RE_NO_ES_CARGO` y `_mayoritariamente_digitos_y_signos`
    solo excluyen lo que se reconoce barato y con seguridad (razon social, direccion,
    telefono, email, URL, horario/codigo). Cualquier OTRA linea que no sea un cargo y
    tampoco tenga ninguna de esas formas **pasa el filtro igual**: un lema comercial,
    un pais suelto ("España"), cualquier prosa que no encaje en la lista de arriba.
    Esta limitacion es real y no se corrige aqui -- perseguir el caso general es
    perseguir una lista blanca imposible. Es exactamente POR ESO que este campo **no
    se escribe en el CRM** (no existe ese campo en la ficha): el cargo solo alimenta
    un informe que una persona lee y confirma antes de que el dato vaya a ningun
    sitio.
    """
    for i, ln in enumerate(lineas):
        if not _RE_NEGRITA.match(ln):
            continue
        for siguiente in lineas[i + 1:]:
            if not siguiente.strip():
                continue
            if _RE_NO_ES_CARGO.search(siguiente) or _mayoritariamente_digitos_y_signos(siguiente):
                return ""
            m = _RE_NEGRITA.match(siguiente)
            return (m.group(1) if m else siguiente).strip()
        return ""
    return ""


def _valores_de_campo(patron: re.Pattern[str], texto: str) -> tuple[str, bool]:
    """Todos los valores VALIDOS de un campo (movil o fijo) dentro de `texto`.

    Hallazgo espejo H-04/H-07 (R1): `.search()` solo devuelve la PRIMERA
    coincidencia del patron, y eso es insuficiente por dos motivos distintos que
    comparten la misma cura:

    - **H-04**: si un bloque trae DOS lineas del mismo campo con valores
      DISTINTOS ("Móvil: 611111111" y "Móvil: 622222222"), la primera se
      quedaba con el partido antes de que `consolidar` pudiera enterarse de que
      habia una segunda. No hay forma de elegir entre dos igual de validos: eso
      es incertidumbre, y se declara (ver `campos_en_conflicto` de `DatosFirma`).
    - **H-07**: `_RE_FIJO` tambien casa con una etiqueta compuesta como "Teléfono
      móvil:" (por su alternativa `tel[ée]fono`) y captura un valor que
      `limpiar_telefono` RECHAZA ("móvil: 611111111" no es un telefono). Con
      `.search()`, ahi se acababa la busqueda -- la linea `Telf:` real que
      viniera despues nunca se llegaba a mirar. Recorrer TODAS las coincidencias
      y quedarse con la primera VALIDA (no la primera a secas) hace que un match
      invalido no tape uno valido que viene detras.

    Devuelve `(valor, en_conflicto)`: sin ningun valor valido, `("", False)`; con
    uno o mas repetidos del MISMO valor, `(ese valor, False)`; con dos o mas
    valores validos y DISTINTOS, `("", True)`.
    """
    vistos: list[str] = []
    for m in patron.finditer(texto):
        limpio = limpiar_telefono(m.group(1))
        if limpio and limpio not in vistos:
            vistos.append(limpio)
    if not vistos:
        return "", False
    if len(vistos) == 1:
        return vistos[0], False
    return "", True


def leer_campos(bloque: BloqueFirma) -> DatosFirma:
    """Los campos de UN bloque ya atribuido. No decide veredictos: eso es `consolidar`."""
    lineas = bloque.texto.splitlines()
    movil, conflicto_movil = _valores_de_campo(_RE_MOVIL, bloque.texto)
    telefono, conflicto_telefono = _valores_de_campo(_RE_FIJO, bloque.texto)
    conflictos = frozenset(
        campo for campo, en_conflicto in
        (("movil", conflicto_movil), ("telefono", conflicto_telefono)) if en_conflicto
    )
    return DatosFirma(
        email=bloque.email,
        movil=movil,
        telefono=telefono,
        cargo=_cargo_de(lineas),
        procedencia=bloque.procedencia,
        fichero=bloque.fichero,
        linea=bloque.linea,
        campos_en_conflicto=conflictos,
    )


@dataclass(frozen=True)
class Consolidado:
    """Lo que el corpus dice de UNA persona, con el veredicto de cada campo.

    Un campo vacio con veredicto `FIRMA_SIN_CAMPO` significa «hay firma y no lo trae»,
    que NO es «no lo tiene»: una de las dos plantillas corporativas medidas no incluye
    movil. Un campo vacio con `CONFLICTO` significa «hay dos y no se sabe cual».
    """
    email: str
    movil: str = ""
    telefono: str = ""
    cargo: str = ""
    veredicto_movil: str = VEREDICTO_FIRMA_SIN_CAMPO
    veredicto_telefono: str = VEREDICTO_FIRMA_SIN_CAMPO
    veredicto_cargo: str = VEREDICTO_FIRMA_SIN_CAMPO
    fuentes: tuple[str, ...] = ()


def _normalizar_para_comparar(valor: str) -> str:
    """La forma en la que dos valores cuentan como "el mismo dato" al decidir
    conflicto (Hallazgo B, revision tasks 7-8).

    SOLO para comparar -- `_elegir` no guarda esto en ningun sitio, solo lo usa para
    poblar `distintos`. El movil y el fijo llegan a `_elegir` ya normalizados por
    `limpiar_telefono` (siempre solo digitos, o `+` y digitos) asi que aplicar esto
    tambien a ellos no cambia nada; es el cargo, que no pasa por ninguna
    normalizacion antes de aqui, el que la necesita: dos informes del mismo cargo
    real con distinta capitalizacion o espaciado ("Asesora Inmobiliaria" /
    "asesora inmobiliaria", o con un espacio duplicado) son el MISMO dato, no un
    conflicto.
    """
    return " ".join(valor.split()).lower()


def _elegir(valores: list[tuple[str, str]]) -> tuple[str, str]:
    """El valor de un campo entre varios bloques, y su veredicto.

    `valores` son pares `(valor, procedencia)` ya filtrados de vacios, en el orden en
    que llegaron (el llamador los pasa del .eml mas antiguo al mas reciente).

    Jerarquia: un DIRECTO manda sobre un CITADO, porque el citado es mas antiguo y el
    consultor puede haber cambiado de numero. Entre dos del mismo nivel manda el
    ultimo. Si quedan dos distintos (una vez normalizados para comparar, ver
    `_normalizar_para_comparar`) que nada separa, **CONFLICTO y campo vacio**: un
    movil mal elegido acaba en la ficha del cliente, y fallar cerrado es la politica de
    este modulo desde el dedup del PR #272.

    **El valor que se propone es siempre el ORIGINAL sin normalizar** (el ultimo de
    los candidatos, por la regla de arriba) -- la normalizacion de
    `_normalizar_para_comparar` es solo para decidir SI hay conflicto, nunca para
    elegir QUE se propone.
    """
    if not valores:
        return "", VEREDICTO_FIRMA_SIN_CAMPO

    directos = [v for v, p in valores if p == PROCEDENCIA_DIRECTO]
    candidatos = directos or [v for v, _ in valores]
    distintos = {_normalizar_para_comparar(v) for v in candidatos}
    if len(distintos) > 1:
        return "", VEREDICTO_CONFLICTO
    return candidatos[-1], VEREDICTO_ENCONTRADO


def consolidar(firmas: Iterable[DatosFirma]) -> dict[str, Consolidado]:
    """Un `Consolidado` por persona, agrupando por el email de su firma.

    El orden de `firmas` es significativo: el llamador las pasa del .eml mas antiguo al
    mas reciente, y `_elegir` se queda con el ultimo cuando nada mas los separa.

    **Un conflicto DENTRO de un bloque manda sobre lo que `_elegir` decidiria**
    (H-04, R1): si algun `DatosFirma` del grupo trae el campo en su propio
    `campos_en_conflicto` (dos valores distintos en la MISMA firma, ya detectado
    por `leer_campos`), el campo se fuerza a `VEREDICTO_CONFLICTO` con valor
    vacio, sin importar lo que otros bloques del grupo digan: la incertidumbre
    de un bloque no se diluye porque otro bloque distinto este seguro.
    """
    por_email: dict[str, list[DatosFirma]] = {}
    for f in firmas:
        if not f.email:
            continue
        por_email.setdefault(f.email.lower(), []).append(f)

    salida: dict[str, Consolidado] = {}
    for email, grupo in por_email.items():
        movil, v_movil = _elegir([(f.movil, f.procedencia) for f in grupo if f.movil])
        tel, v_tel = _elegir([(f.telefono, f.procedencia) for f in grupo if f.telefono])
        cargo, v_cargo = _elegir([(f.cargo, f.procedencia) for f in grupo if f.cargo])
        if any("movil" in f.campos_en_conflicto for f in grupo):
            movil, v_movil = "", VEREDICTO_CONFLICTO
        if any("telefono" in f.campos_en_conflicto for f in grupo):
            tel, v_tel = "", VEREDICTO_CONFLICTO
        salida[email] = Consolidado(
            email=email, movil=movil, telefono=tel, cargo=cargo,
            veredicto_movil=v_movil, veredicto_telefono=v_tel, veredicto_cargo=v_cargo,
            fuentes=tuple(dict.fromkeys(f"{f.fichero}:{f.linea}" for f in grupo)),
        )
    return salida


@dataclass(frozen=True)
class ResultadoEml:
    """Lo que UN .eml dio, con la constancia de lo que no se pudo leer.

    `ilegible` con texto significa que el fichero no se pudo mirar. Eso **no** es que
    no haya firma: es que no se sabe. Se declara y sube al informe.
    """
    firmas: tuple[DatosFirma, ...] = ()
    emails_vistos: frozenset[str] = frozenset()
    sin_atribuir: int = 0
    ilegible: str = ""


def extraer_de_eml(path: Path) -> ResultadoEml:
    """Las firmas de un .eml, atribuidas por su propio contenido.

    **La cabecera `From:` no participa en la atribucion.** Se lee solo para
    `emails_vistos`, que alimenta la seccion de candidatos del informe: aparecer en un
    correo del expediente no te hace colaborador de ese expediente (medido el
    2026-09-04 sobre W-02Q38C: 7 direcciones @ev en 6 correos, 3 vinculadas).
    """
    try:
        msg = BytesParser(policy=policy.default).parse(path.open("rb"))
    except Exception as exc:  # noqa: BLE001 — un .eml corrupto se declara, no rompe
        return ResultadoEml(ilegible=f"{path}: no parsea ({exc!r})")

    if not msg.keys():
        # Medido (Task 9): BytesParser(policy.default) casi NUNCA lanza, ni con
        # basura sin ninguna forma de correo -- es deliberadamente permisivo (RFC
        # 5322 lo pide asi). Bytes sueltos sin una sola linea "Clave: Valor" los
        # vuelca ENTEROS como cuerpo (defecto MissingHeaderBodySeparatorDefect) en
        # vez de fallar, y el try/except de arriba nunca se dispara para este caso.
        # Sin ninguna cabecera reconocida no hay correo que leer -- la misma
        # situacion que un fichero vacio (que tampoco tiene ninguna).
        return ResultadoEml(ilegible=f"{path}: no parsea (sin cabeceras reconocibles)")

    try:
        parte = msg.get_body(preferencelist=("plain",))
        cuerpo = parte.get_content() if parte is not None else ""
    except Exception as exc:  # noqa: BLE001 — charset roto, base64 truncado...
        return ResultadoEml(ilegible=f"{path}: cuerpo ilegible ({exc!r})")

    if not cuerpo.strip():
        return ResultadoEml(ilegible=f"{path}: sin parte text/plain con contenido")

    cabeceras = " ".join(str(msg.get(h) or "") for h in ("From", "To", "Cc"))
    vistos = {m.group(0).lower()
              for m in _RE_EMAIL_COLAB.finditer(cabeceras + "\n" + cuerpo)}

    bloques, sin_atribuir = extraer_bloques(cuerpo, fichero=path.name)
    return ResultadoEml(
        firmas=tuple(leer_campos(b) for b in bloques),
        emails_vistos=frozenset(vistos),
        sin_atribuir=sin_atribuir,
    )


def extraer_de_directorio(
    raiz: Path,
) -> tuple[dict[str, Consolidado], frozenset[str], tuple[str, ...]]:
    """Recorre `raiz` en busca de `.eml` y consolida lo que digan sus firmas.

    Devuelve `(consolidados, emails_vistos, ilegibles)`. El recorrido va **ordenado**:
    `consolidar` se queda con el ultimo valor cuando nada mas lo separa, asi que un
    orden no determinista daria resultados distintos entre corridas.

    Un fichero ilegible no hunde el recorrido y **se lista**: «no pude mirar» y «no hay
    nada» tienen que verse distinto.
    """
    firmas: list[DatosFirma] = []
    vistos: set[str] = set()
    ilegibles: list[str] = []
    for path in sorted(Path(raiz).rglob("*.eml")):
        r = extraer_de_eml(path)
        if r.ilegible:
            ilegibles.append(r.ilegible)
            continue
        firmas.extend(r.firmas)
        vistos |= r.emails_vistos
    return consolidar(firmas), frozenset(vistos), tuple(ilegibles)
