"""B5 — auto-derivación de identidad desde --folder-id (funciones puras)."""
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
