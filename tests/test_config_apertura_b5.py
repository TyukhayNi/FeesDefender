"""B5 — auto-derivación de identidad desde --folder-id (funciones puras)."""
import pytest

from core import config


class TestSufijoDeTipoCaso:
    def test_vuelta(self):
        assert config.sufijo_de_tipo_caso("VUELTA") == "Vuelta"

    def test_negativa_escritura(self):
        assert config.sufijo_de_tipo_caso("NEGATIVA_ESCRITURA") == "Negativa escritura"

    def test_lau_20_preserva_acronimo(self):
        # El fallback title-case degradaría a "Lau 20"; el mapa especial lo evita.
        assert config.sufijo_de_tipo_caso("LAU_20") == "LAU 20"

    def test_bad_debt_fallback(self):
        assert config.sufijo_de_tipo_caso("BAD_DEBT") == "Bad debt"

    def test_todos_los_tipos_dan_sufijo_valido(self):
        for tipo in config.TIPOS_CASO_ALL:
            suf = config.sufijo_de_tipo_caso(tipo)
            assert suf and "_" not in suf and suf[0].isupper()


class TestCodigoDeUnidad:
    @pytest.mark.parametrize("nombre,esperado", [
        ("Barcelona - S3 ", "BaRS3"),          # espacio final real
        ("Barcelona - S3", "BaRS3"),
        ("Barcelona - S1", "BaRS1"),
        ("Barcelona - S12", "BaRS12"),
        ("Barcelona - PD1", "BaPD1"),
        ("Barcelona Rentals - R1", "BaRR1"),
        ("Barcelona Rentals - R10", "BaRR10"),
        ("Bilbao - S2", "BiRS2"),
        ("Madrid - S15", "MaRS15"),
        ("Madrid - R1", "MaRR1"),
        ("Madrid - PD2", "MaPD2"),
        ("San Sebastian - S1", "SSRS1"),
        ("San Sebastian - R1", "SSRR1"),
        ("Santander - S1", "SaRS1"),
        ("Valencia - S5", "VaRS5"),
        ("Valencia - R3", "VaRR3"),
        ("Valencia - PD1", "VaPD1"),
    ])
    def test_derivables(self, nombre, esperado):
        assert config.codigo_de_unidad(nombre) == esperado

    @pytest.mark.parametrize("nombre", [
        "Sevilla - S1 / S6",        # ambigua
        "BCN - PD10",               # abreviatura fuera del mapa
        "BCN Comm - Agencia",       # comercial no numerada
        "Valencia - Commercial ",   # comercial (sufijo no operativo)
        "Madrid - R1 Inactivas",    # sufijo no operativo
        "Madrid - R1_1",            # sufijo no operativo
        "Lisboa - S1",              # Portugal, fuera del mapa
        "San Sebastian de los Reyes - S1",
        "Sevilla la Nueva - S1",
        "Madrid Digitalizacion - S1",
        "BACKUP MADRID",            # sin " - "
        "NIKOLAI",                  # sin " - " ni ciudad
        "_Team_Example_S0",         # sin " - "
        "MMC Barcelona Juridico",   # sin " - "
        "Barcelona - ",             # sufijo vacío
        "Barcelona -",              # sin " - " (falta espacio)
        "- S3",                     # sin ciudad
        "",                         # vacío
    ])
    def test_no_derivables_devuelven_none(self, nombre):
        assert config.codigo_de_unidad(nombre) is None
