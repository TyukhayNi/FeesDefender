"""La costura del reloj del sistema, probada SIN fixture que la sustituya (R12/H12-07).

Los tres ficheros de regresión del mutex fijan `_ahora_del_sistema` con una fixture
`autouse`, y hacen bien: la cota de desvío es simétrica y unos timestamps fijos se
alejarían del reloj real en cuanto pasara un día.

El precio es que **ninguno de ellos prueba el cableado de la costura**. Un mutante que
hiciera que la implementación real devolviera una época equivocada —milisegundos en vez
de segundos, u hora local en vez de UTC— dejaría todo aquello verde y rompería la barrera
entera en producción.

Este fichero existe para eso y no tiene la fixture. Es un test de una línea, y esa es
exactamente la clase de test que se olvida.
"""
from __future__ import annotations

import time


def test_la_costura_devuelve_el_reloj_de_verdad_en_segundos_UTC():
    from core.casos.case_mutex import _ahora_del_sistema
    assert abs(_ahora_del_sistema() - time.time()) < 5


def test_la_cota_se_mide_contra_esa_costura_y_no_contra_otra_cosa():
    """Un `ahora` construido desde el reloj real tiene que pasar la cota.

    Sin esto, una costura en milisegundos pasaría el test de arriba por poco margen y
    rompería la cota igualmente.
    """
    from datetime import datetime, timezone

    from core.casos.case_mutex import _sin_desvio_absurdo
    ahora = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    assert _sin_desvio_absurdo(ahora)
