"""Las cinco carpetas de fase de `05_Procedimiento`. Un solo sitio que las nombre.

Set CERRADO: el mapa del letrado se valida contra esta tupla y `registrar_outputs` la
replica para que un escrito generado se registre en su fase (spec §7).

Los rótulos de la 2.ª y la 4.ª los fija este módulo, derivados de la tabla de bloques del
spec §11.1 («Oposición al monitorio + documentos», «Contestación + documentos»). Van SIN
tilde por coherencia con `02_Analisis` y `99_Sin categoria` del repo.
"""
from __future__ import annotations

#: En orden de lectura del pleito. El prefijo numérico es parte del nombre.
CARPETAS_FASE: tuple[str, ...] = (
    "01_Monitorio - Demanda y documentos",
    "02_Monitorio - Oposicion y documentos",
    "03_Ordinario - Demanda y documentos",
    "04_Ordinario - Contestacion y documentos",
    "05_Otros escritos",
)

#: El cajón que recoge lo procesal que no es un escrito rector con sus documentos. Es lo
#: que hace cumplible la exigencia de que nada quede sin asignar (spec §11.1).
CARPETA_OTROS: str = "05_Otros escritos"

#: Las cuatro primeras llevan escrito rector: el borrador les propone `orden: "00"` cuando
#: el nombre del CRM no trae número de documento. La quinta usa la fecha del lote.
CARPETAS_CON_RECTOR: tuple[str, ...] = CARPETAS_FASE[:4]

_SET = frozenset(CARPETAS_FASE)


def es_carpeta_fase(nombre: str) -> bool:
    """`True` solo para una de las cinco, con su grafía exacta.

    No normaliza: un rótulo aproximado es un error del mapa que hay que ver, no algo que
    adivinar. La comparación `casefold` del spec §3.1 es para detectar COLISIONES entre
    destinos, no para aceptar variantes del nombre de la carpeta.
    """
    return nombre in _SET
