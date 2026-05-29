"""Tests de la revisión de código del módulo anon/ (2026-05-30).

Cada test fija una corrección concreta de la revisión para que no se
reintroduzca el fallo. Trabajan sin Presidio (rápidos, determinísticos).
"""

from __future__ import annotations

import json
import logging

import pytest

from core.anon import MapaEntidades, deanonimizar_texto, detectar_nombres_protegidos
from core.anon.anonimizar import (
    anonimizar_variantes_conocidas,
    esta_protegido,
)
from core.anon.deanonimizar import deanonimizar
from core.anon.exceptions import AnonError


def _log() -> logging.Logger:
    log = logging.getLogger("anon_fixes_test")
    log.handlers.clear()
    log.addHandler(logging.NullHandler())
    log.setLevel(logging.CRITICAL)
    return log


def _anon_sin_presidio(texto: str, mapa: MapaEntidades | None = None):
    from core.anon.anonimizar import (
        anonimizar_mayusculas,
        anonimizar_por_contexto,
        aplicar_regex,
    )

    log = _log()
    if mapa is None:
        mapa = MapaEntidades(protegidos=detectar_nombres_protegidos(texto))
    texto = anonimizar_por_contexto(texto, mapa, log)
    texto = aplicar_regex(texto, mapa, log)
    texto = anonimizar_mayusculas(texto, mapa, log)
    return texto, mapa


# ---------------------------------------------------------------------------
# #1 — esta_protegido: solo coincidencia EXACTA (no subcadena)
# ---------------------------------------------------------------------------

class TestProtegidoExacto:
    def test_coincidencia_exacta(self) -> None:
        assert esta_protegido("ELENA HORNOS", {"ELENA HORNOS"})

    def test_insensible_mayusculas_y_espacios(self) -> None:
        assert esta_protegido("elena   hornos", {"ELENA HORNOS"})

    def test_parte_que_contiene_al_operador_NO_se_protege(self) -> None:
        # El bug: "ELENA HORNOS GARCIA" (una parte) contenía el nombre del
        # operador "ELENA HORNOS" y quedaba sin anonimizar (fuga de PII).
        assert not esta_protegido("ELENA HORNOS GARCIA", {"ELENA HORNOS"})

    def test_fragmento_parcial_del_operador_NO_se_protege(self) -> None:
        # Antes "ELENA" (subcadena del operador) se daba por protegido; si fuera
        # una parte distinta, se filtraba. Ahora se anonimiza (sobre-redacción
        # inocua del operador a cambio de no filtrar nunca una parte).
        assert not esta_protegido("ELENA", {"ELENA HORNOS"})


# ---------------------------------------------------------------------------
# #2 — registrar: NO fusiona personas distintas; round-trip exacto
# ---------------------------------------------------------------------------

class TestRegistrarSinFusion:
    def test_nombres_con_prefijo_comun_reciben_etiquetas_distintas(self) -> None:
        mapa = MapaEntidades()
        e1 = mapa.registrar("MARIA GARCIA", "actor")
        e2 = mapa.registrar("MARIA GARCIA LOPEZ", "demandado")
        assert e1.startswith("[") and e2.startswith("[")
        assert e1 != e2, "dos personas distintas no deben compartir etiqueta"

    def test_roundtrip_exacto_sin_sobrescritura_de_mapa_inverso(self) -> None:
        mapa = MapaEntidades()
        e1 = mapa.registrar("MARIA GARCIA", "actor")
        e2 = mapa.registrar("MARIA GARCIA LOPEZ", "demandado")
        restaurado = deanonimizar_texto(f"{e1} y {e2}", mapa.mapa_inverso)
        # Antes la aparición corta se restituía con el nombre largo (inventado).
        assert restaurado == "MARIA GARCIA y MARIA GARCIA LOPEZ"

    def test_misma_forma_exacta_reusa_etiqueta(self) -> None:
        mapa = MapaEntidades()
        e1 = mapa.registrar("PEDRO SANZ", "actor")
        e2 = mapa.registrar("PEDRO SANZ", "actor")
        assert e1 == e2


# ---------------------------------------------------------------------------
# #7 — email partido por salto de línea (OCR a dos columnas)
# ---------------------------------------------------------------------------

class TestEmailPartido:
    def test_email_con_salto_de_linea_se_anonimiza(self) -> None:
        texto, _ = _anon_sin_presidio("Contacto: juan.perez@\ngmail.com fin")
        assert "juan.perez" not in texto
        assert "gmail.com" not in texto
        assert "[EMAIL" in texto

    def test_email_normal_sigue_anonimizandose(self) -> None:
        texto, _ = _anon_sin_presidio("Mail: ana@dominio.es .")
        assert "ana@dominio.es" not in texto
        assert "[EMAIL" in texto


# ---------------------------------------------------------------------------
# #8 — variantes del cliente con límite de palabra
# ---------------------------------------------------------------------------

class TestVariantesLimitePalabra:
    def test_variante_corta_no_corrompe_palabra_mayor(self) -> None:
        mapa = MapaEntidades()
        out = anonimizar_variantes_conocidas("La BARROCA y la ROCA.", mapa, ["ROCA"], _log())
        assert "BARROCA" in out, "no debe reescribir el interior de BARROCA"
        assert " ROCA" not in out, "la variante suelta sí debe anonimizarse"


# ---------------------------------------------------------------------------
# #10 — deanonimizar no entrega ficheros falsamente 'deanonimizados'
# ---------------------------------------------------------------------------

class TestDeanonimizarMapaIncompleto:
    def test_mapa_vacio_con_etiquetas_lanza_error(self, tmp_path) -> None:
        md = tmp_path / "doc.md"
        md.write_text(
            "> **Documento anonimizado** | x\n\nHola [NOMBRE].\n", encoding="utf-8"
        )
        # JSON sin clave 'mapa' (caso truncado/perdido).
        (tmp_path / "doc_mapa.json").write_text(
            json.dumps({"generado": "x"}), encoding="utf-8"
        )
        with pytest.raises(AnonError):
            deanonimizar(md)

    def test_documento_sin_etiquetas_se_deanonimiza_ok(self, tmp_path) -> None:
        md = tmp_path / "doc2.md"
        md.write_text(
            "> **Documento anonimizado** | x\n\nTexto sin datos personales.\n",
            encoding="utf-8",
        )
        (tmp_path / "doc2_mapa.json").write_text(
            json.dumps({"mapa": {}}), encoding="utf-8"
        )
        salida = deanonimizar(md)
        assert salida.exists()
