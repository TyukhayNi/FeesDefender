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
from dataclasses import dataclass

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

_RE_EMAIL_COLAB = re.compile(
    r"[\w.+-]+@" + DOMINIO_COLABORADOR.replace(".", r"\."), re.IGNORECASE
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
#: Los separadores INTERNOS de la marca son `[ \t]*` y no `\s*`: `\s*` se comeria un
#: salto de linea y dejaria corroborar "ENGEL" y "VOLKERS" en lineas distintas
#: separadas por una linea en blanco (que no tiene forma de firma real; hallazgo D,
#: R2). El precio deliberado de este cierre: una marca partida en dos lineas por el
#: ajuste de longitud del cliente de correo deja de reconocerse. Es el intercambio
#: correcto -- se prefiere perder una firma legitima a inventar una. NO "arreglar" esto
#: volviendo a `\s*`.
_RE_CORROBORA = re.compile(
    r"(?im)^\s*\*?\s*engel[ \t]*&?[ \t]*v[öo]lkers\s*\*?\s*$"
    r"|^\s*\*?\s*ev\s+mmc\s+spain\s*,?\s*"
    r"(?:s\.?\s*l\.?\s*u\.?|s\.?\s*l\.?|s\.?\s*a\.?)?\.?\s*\*?\s*$"
    r"|^\s*\*?\s*(?:telf|tel[ée]fono|tel\.\s*fijo|m[óo]vil|movil|mobile)\b"
    r"[ \t]*:?[ \t]*"
    r"[0-9+()*<>.\- \t]+"
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


def localizar_bloques(texto: str, *, fichero: str = "") -> list[BloqueFirma]:
    """Los bloques que parecen una firma, uno por linea con direccion corroborada.

    Desmarca el texto ANTES de buscar (Hallazgo A, R2 -- regresion del arreglo de R1):
    las anclas de `_RE_CORROBORA` exigen inicio de linea, y no pueden depender de si
    el llamador ya le paso el texto desmarcado o no. `desmarcar` es idempotente (un
    texto sin `>` no cambia), asi que un llamador que ya desmarco no sufre nada -- y
    esto es lo que permite localizar una firma CITADA linea a linea (un reenvio con
    `>` en cada linea), que es justo uno de los dos escenarios que motivan el modulo
    entero (ver docstring de cabecera).

    Un mismo correo puede dar varios bloques para la misma persona (la plantilla de
    Barcelona repite la direccion al final); `consolidar` los une.
    """
    texto = desmarcar(texto)
    lineas = texto.splitlines()
    marcadores = [i for i, ln in enumerate(lineas) if _RE_MARCADOR.match(ln)]

    bloques: list[BloqueFirma] = []
    for i, linea in enumerate(lineas):
        m_ancla = _RE_EMAIL_COLAB.search(linea)
        if not m_ancla:
            continue

        # El marcador mas cercano por encima aprieta el limite superior; si no hay,
        # se usa una ventana fija. Sin limite se arrastraria el correo entero.
        # El candidato del marcador es la linea DESPUES de el (H-04): la propia linea
        # del marcador ("-- ") no es parte de la firma.
        previos = [m for m in marcadores if m < i]
        candidato_marcador = previos[-1] + 1 if previos else 0
        inicio = max(candidato_marcador, i - _VENTANA_ATRAS)
        fin = min(len(lineas), i + 1 + _VENTANA_ADELANTE)
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
        bloques.append(BloqueFirma(
            texto=cuerpo, email=m_ancla.group(0).lower(), linea=inicio + 1, fichero=fichero,
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
    indice de linea (ver su docstring). `localizar_bloques` calcula `linea` con
    `texto.splitlines()` sobre el texto DESMARCADO, pero la diferencia entre los dos
    metodos de contar es solo el segmento vacio final cuando el texto termina en salto
    de linea -- un indice que ninguna linea de firma real puede ocupar (una cadena
    vacia nunca corrobora ni contiene un email). Para toda linea de contenido real el
    indice es identico en `split("\\n")` y en `splitlines()`, asi que usar `split("\\n")`
    aqui mantiene el cruce alineado con el `linea` de un bloque sin heredar el
    desajuste que `splitlines()` introduciria justo en ese ultimo segmento.
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
_RE_MOVIL = re.compile(
    r"(?im)^\s*\*?\s*(?:m[óo]vil|mobile|m[óo]v\.?)\s*[:.]?\s*(.+?)\s*$")
_RE_FIJO = re.compile(
    r"(?im)^\s*\*?\s*(?:telf|tel\.?\s*fijo|tel[ée]fono|tel\.|phone)\s*[:.]?\s*(.+?)\s*$")

#: Una linea ENTERAMENTE en negrita. La primera es el nombre; el cargo es la siguiente
#: linea no vacia, en negrita o no (las dos plantillas medidas difieren en eso).
_RE_NEGRITA = re.compile(r"^\s*\*(.+?)\*\s*$")

#: Lo que una linea tras el nombre puede ser sin ser un cargo.
_RE_NO_ES_CARGO = re.compile(
    r"(?i)engel\s*&?\s*v[öo]lkers"
    r"|ev\s+mmc|s\.?l\.?u|s\.?a\.?$"
    r"|@"
    r"|^\s*\*?\s*(?:telf|tel|tel[ée]fono|m[óo]vil|movil|mobile|mailto|fax)\b"
    r"|\d{4,}"                       # un CP o un numero largo: es direccion
    r"|^\s*\*?\s*(?:c/|calle|avinguda|avenida|passeig|plaza|pl\.|paseo)\b"
)

_RE_EXTENSION = re.compile(r"(?i)\s*(?:/|\bext\b|\bextension\b|\bextensión\b).*$")


@dataclass(frozen=True)
class DatosFirma:
    """Lo que dice UN bloque de firma. Los campos vacios NO afirman ausencia."""
    email: str
    movil: str = ""
    telefono: str = ""
    cargo: str = ""
    procedencia: str = PROCEDENCIA_DIRECTO
    fichero: str = ""
    linea: int = 0


def limpiar_telefono(valor: str) -> str:
    """El numero que hay en una linea de firma, listo para el CRM.

    `normalize_es_phone` no quita letras ni asteriscos, y los valores llegan sucios: la
    negrita HTML degrada a `*` en el text/plain, y la plantilla de Madrid pega la
    extension detras (`+34 912 345 678 / Ext. 1234`). La extension no es parte del
    numero, y el CRM exige 9 digitos o devuelve HTTP 400 (`[APER-14]`).
    """
    v = _RE_EXTENSION.sub("", valor or "")
    v = v.replace("*", "").replace("<", "").replace(">", "").strip()
    v = normalize_es_phone(v)
    # Un valor sin ningun digito no es un telefono, es basura del parseo.
    return v if any(c.isdigit() for c in v) else ""


def _cargo_de(lineas: list[str]) -> str:
    """El cargo, por POSICION: no tiene etiqueta en ninguna de las dos plantillas.

    Regla medida: la primera linea enteramente en negrita es el NOMBRE, y el cargo es
    la siguiente linea no vacia — en negrita en la plantilla de Madrid, sin negrita en
    la de Barcelona. Si esa linea es la razon social, una direccion, un telefono o un
    email, no hay cargo: **antes vacio que inventado**.
    """
    for i, ln in enumerate(lineas):
        if not _RE_NEGRITA.match(ln):
            continue
        for siguiente in lineas[i + 1:]:
            if not siguiente.strip():
                continue
            if _RE_NO_ES_CARGO.search(siguiente):
                return ""
            m = _RE_NEGRITA.match(siguiente)
            return (m.group(1) if m else siguiente).strip()
        return ""
    return ""


def leer_campos(bloque: BloqueFirma) -> DatosFirma:
    """Los campos de UN bloque ya atribuido. No decide veredictos: eso es `consolidar`."""
    lineas = bloque.texto.splitlines()
    m_movil = _RE_MOVIL.search(bloque.texto)
    # Un `Móvil:` no puede caer en el patron del fijo: se resta del texto antes.
    texto_sin_movil = _RE_MOVIL.sub("", bloque.texto)
    m_fijo = _RE_FIJO.search(texto_sin_movil)
    return DatosFirma(
        email=bloque.email,
        movil=limpiar_telefono(m_movil.group(1)) if m_movil else "",
        telefono=limpiar_telefono(m_fijo.group(1)) if m_fijo else "",
        cargo=_cargo_de(lineas),
        procedencia=bloque.procedencia,
        fichero=bloque.fichero,
        linea=bloque.linea,
    )
