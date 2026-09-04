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

_RE_CITA = re.compile(r"(?m)^\s*>+\s?")

_RE_MARCADOR = re.compile(
    r"(?im)^\s*(?:--\s*|enviado desde mi.*|sent from my.*|obtener outlook.*|get outlook.*)$"
)

_RE_EMAIL_COLAB = re.compile(
    r"[\w.+-]+@" + DOMINIO_COLABORADOR.replace(".", r"\."), re.IGNORECASE
)

#: Que convierte una direccion en una FIRMA. Sin al menos una de estas, una direccion
#: suelta en un texto produciria una «firma» inventada de quien solo se menciona.
_RE_CORROBORA = re.compile(
    r"(?im)engel\s*&?\s*v[öo]lkers"
    r"|ev\s+mmc\s+spain"
    r"|^\s*\*?\s*(?:telf|tel[ée]fono|tel\.|m[óo]vil|movil|mobile)\b"
)


def desmarcar(texto: str) -> str:
    """Quita las marcas de cita `>` del principio de cada linea.

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

    Un mismo correo puede dar varios bloques para la misma persona (la plantilla de
    Barcelona repite la direccion al final); `consolidar` los une.
    """
    lineas = texto.splitlines()
    marcadores = [i for i, ln in enumerate(lineas) if _RE_MARCADOR.match(ln)]

    bloques: list[BloqueFirma] = []
    for i, linea in enumerate(lineas):
        if not _RE_EMAIL_COLAB.search(linea):
            continue

        # El marcador mas cercano por encima aprieta el limite superior; si no hay,
        # se usa una ventana fija. Sin limite se arrastraria el correo entero.
        previos = [m for m in marcadores if m < i]
        inicio = max(previos[-1], i - _VENTANA_ATRAS) if previos else max(0, i - _VENTANA_ATRAS)
        fin = min(len(lineas), i + 1 + _VENTANA_ADELANTE)
        cuerpo = "\n".join(lineas[inicio:fin])

        if not _RE_CORROBORA.search(cuerpo):
            continue
        bloques.append(BloqueFirma(texto=cuerpo, linea=inicio + 1, fichero=fichero))
    return bloques
