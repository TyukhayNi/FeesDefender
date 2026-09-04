"""Leer la firma de un correo: quien firma, con que telefono y con que cargo.

NO conoce el CRM. Devuelve lo que dice el correo, con la constancia de lo que no pudo
leer; quien decide que hacer con eso es `scripts/crm_colaboradores_firmas.py`.

Verdad de campo que fija el diseno, medida el 2026-09-04 sobre los 6 `.eml` de W-02Q38C:

- **Solo 3 de 6 traen marcador de firma.** Anclar el localizador en el marcador pierde la
  mitad en silencio. Lo que aparece en los 6 bloques es una **linea con la direccion
  corporativa**, asi que el ancla es esa y el marcador solo aprieta el limite superior.
- **La firma del cuerpo NO es la del `From:`.** En 2 de los 6 pertenece a otra persona
  (un reenvio, y un bloque citado). Por eso la atribucion sale del email de DENTRO del
  bloque, y un bloque sin email no se atribuye a nadie.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

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
        if not _RE_EMAIL_COLAB.search(linea):
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
        bloques.append(BloqueFirma(texto=cuerpo, linea=inicio + 1, fichero=fichero))
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
    """Pone a cada bloque el email de QUIEN FIRMA, y su procedencia.

    **El email sale de DENTRO del bloque, nunca de la cabecera `From:`.** Medido el
    2026-09-04: en 2 de los 6 .eml de W-02Q38C la firma del cuerpo pertenece a otra
    persona (un reenvio, y un bloque citado). Atribuir por cabecera escribiria el
    telefono de una persona en la ficha de otra, en el CRM del cliente.

    Por eso esta funcion **no recibe el remitente**: no es que decida ignorarlo, es que
    no lo tiene. Un bloque sin email dentro se descarta y se cuenta.
    """
    zonas = zonas_citadas(texto_original)
    atribuidos: list[BloqueFirma] = []
    sin_atribuir = 0
    for b in bloques:
        # El ULTIMO email del bloque, no el primero: cuando dos firmas quedan
        # pegadas, la ventana hacia atras de la segunda (_VENTANA_ATRAS) puede
        # arrastrar el email de la PRIMERA sin que la propia haya salido todavia
        # de la ventana. El disparador de cada bloque esta a una distancia FIJA
        # del final de su ventana (`_VENTANA_ADELANTE`), nunca del principio, asi
        # que buscar el primero le atribuiria a Berta el email de Ana con solo
        # que sus firmas fueran consecutivas -- justo el patron que corrobora
        # `test_dos_firmas_distintas_en_un_correo_se_separan`. La plantilla de
        # Barcelona repite su propio email al final del bloque (ver
        # `localizar_bloques`), asi que el ultimo sigue siendo el correcto
        # incluso sin overlap con otra firma.
        coincidencias = list(_RE_EMAIL_COLAB.finditer(b.texto))
        if not coincidencias:
            sin_atribuir += 1
            continue
        m = coincidencias[-1]
        procedencia = (PROCEDENCIA_CITADO if _en_zona_citada(b.linea - 1, zonas)
                       else PROCEDENCIA_DIRECTO)
        atribuidos.append(BloqueFirma(
            texto=b.texto, email=m.group(0).lower(), linea=b.linea,
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
