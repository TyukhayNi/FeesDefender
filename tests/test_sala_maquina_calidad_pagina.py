"""`ocr_quality` por página: romper la dilución del promedio (MEJORAS #90, (b)).

`ocr_quality` promedia sobre el documento entero, así que 4 páginas escaneadas
que no dieron ni un carácter se diluyen entre 36 páginas digitales densas y el
documento sale `ok` — fuera de la worklist de `_cobertura.md` y fuera del filtro
de `reforzar`. La señal por página es lo que lo rompe.

Discriminante: **página perdida** = ráster a página completa y menos texto del
que exige la densidad mínima. Una página en blanco legítima (sin ráster) no
cuenta: el reverso de un dúplex no es un fallo de OCR.
"""
from pathlib import Path

import pytest

from core import sala_maquina as sm
from core.pdf_paginas import PaginaPerfil

_RASTER = 1_900_000       # ≥ MIN_PX_RASTER
_TEXTO = "Estipulacion cuarta sobre honorarios de intermediacion inmobiliaria."


def _perfil(paginas: list[tuple[int, int]]) -> list[PaginaPerfil]:
    """`[(chars, raster_px), …]` → perfil numerado desde 1."""
    return [PaginaPerfil(numero=i, chars=c, raster_px=px)
            for i, (c, px) in enumerate(paginas, 1)]


def test_dos_escaneos_sin_texto_bajan_a_low_aunque_el_promedio_pase():
    # 36 páginas digitales densas + 4 escaneos que no dieron nada: el promedio
    # engaña, las 4 páginas no.
    perfil = _perfil([(1500, 0)] * 36 + [(3, _RASTER)] * 4)

    estado, motivo = sm.calidad_por_pagina(perfil)

    assert estado == "low"
    assert "4 de 40" in motivo


def test_paginas_en_blanco_sin_raster_no_bajan_la_calidad():
    perfil = _perfil([(1500, 0), (0, 0), (1500, 0), (0, 0)])

    estado, _ = sm.calidad_por_pagina(perfil)

    assert estado == ""


def test_una_foto_a_pagina_completa_no_es_un_documento_dudoso():
    # El camino `imagen` (jpg → pdf → OCR) produce exactamente esto. Marcarlo
    # `low` inundaría la worklist con DNIs y capturas — los falsos positivos que
    # ya se identificaron al medir el cribado del detector.
    perfil = _perfil([(12, _RASTER)])

    estado, _ = sm.calidad_por_pagina(perfil)

    assert estado == ""


def test_media_documento_perdido_baja_a_low_aunque_sea_una_sola_pagina():
    perfil = _perfil([(1200, 0), (5, _RASTER)])

    estado, motivo = sm.calidad_por_pagina(perfil)

    assert estado == "low" and "1 de 2" in motivo


def test_un_escaneo_perdido_en_un_documento_largo_no_dispara():
    perfil = _perfil([(1500, 0)] * 30 + [(4, _RASTER)])

    estado, _ = sm.calidad_por_pagina(perfil)

    assert estado == ""


def test_una_pagina_escaneada_con_texto_recuperado_no_cuenta_como_perdida():
    perfil = _perfil([(1500, 0)] * 3 + [(1200, _RASTER)] * 3)

    estado, _ = sm.calidad_por_pagina(perfil)

    assert estado == ""


def test_perfil_vacio_no_opina():
    """PDF ilegible para pypdf: sin perfil no hay señal, y no se inventa una."""
    assert sm.calidad_por_pagina([]) == ("", "")
