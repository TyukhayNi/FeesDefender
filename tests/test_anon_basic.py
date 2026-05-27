"""Tests básicos del módulo anon/ — Fase 1.

Cubre la API en memoria sin tocar disco ni cargar Presidio:
    - Round-trip texto: anonimizar → deanonimizar → idéntico al original.
    - MapaEntidades: persistencia ida y vuelta (exportar/cargar JSON).
    - mapa_caso: rutas y carga/guardado en una carpeta de caso real.

Los tests que dependerían de Presidio + spaCy se aíslan o se marcan
como `@pytest.mark.slow`. Aquí trabajamos solo con las fases regex,
contextual y mayúsculas, que son determinísticas y rápidas.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pytest

from core.anon import (
    MapaEntidades,
    anonimizar_texto,
    cargar_mapa_caso,
    deanonimizar_texto,
    detectar_nombres_protegidos,
    guardar_mapa_caso,
    ruta_mapa_caso,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _logger_silencioso() -> logging.Logger:
    log = logging.getLogger("anon_test_silencioso")
    log.handlers.clear()
    log.addHandler(logging.NullHandler())
    log.setLevel(logging.CRITICAL)
    return log


def _anonimizar_sin_presidio(texto: str, mapa: MapaEntidades | None = None):
    """Aplica solo las fases determinísticas (sin Presidio).

    `anonimizar_texto` aplica las 4 fases. La fase 1 (Presidio) requiere
    spaCy + modelos ~1.5 GB; los tests rápidos la omiten saltándose
    directamente al pipeline contextual + regex + mayúsculas.
    """
    from core.anon.anonimizar import (
        anonimizar_mayusculas,
        anonimizar_por_contexto,
        aplicar_regex,
    )

    log = _logger_silencioso()
    if mapa is None:
        protegidos = detectar_nombres_protegidos(texto)
        mapa = MapaEntidades(protegidos=protegidos)
    texto = anonimizar_por_contexto(texto, mapa, log)
    texto = aplicar_regex(texto, mapa, log)
    texto = anonimizar_mayusculas(texto, mapa, log)
    return texto, mapa


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """Anonimizar → deanonimizar debe recuperar el texto original."""

    def test_roundtrip_dni_iban_email(self) -> None:
        original = (
            "Datos del demandante:\n"
            "DNI 12345678Z, IBAN ES91 2100 0418 4502 0005 1332,\n"
            "email contacto@ejemplo.com, teléfono +34 612 345 678."
        )
        anonimizado, mapa = _anonimizar_sin_presidio(original)

        # Las 4 piezas deben haberse sustituido
        assert "12345678Z" not in anonimizado
        assert "ES91" not in anonimizado
        assert "contacto@ejemplo.com" not in anonimizado
        assert "612 345 678" not in anonimizado

        # Round-trip
        recuperado = deanonimizar_texto(anonimizado, mapa.mapa_inverso)
        assert recuperado == original

    def test_roundtrip_partes_procesales(self) -> None:
        # Nota: el regex contextual ``_NOMBRE`` se compila con re.IGNORECASE
        # y permite hasta 3 palabras tras la inicial. Si dos partes procesales
        # quedan en líneas contiguas sin puntuación entre ellas, el match
        # puede engullir la primera palabra de la siguiente parte. En docs
        # reales (cédulas, oficis) las partes vienen separadas por punto,
        # formato que reproducimos aquí.
        original = (
            "Demandante: DON IVAN PETROV SOKOLOV.\n"
            "Demandado: DOÑA MARIA GARCIA LOPEZ."
        )
        anonimizado, mapa = _anonimizar_sin_presidio(original)

        # Los nombres de las partes ya no aparecen literales
        assert "IVAN PETROV SOKOLOV" not in anonimizado
        assert "MARIA GARCIA LOPEZ" not in anonimizado

        # Aparecen etiquetas entre corchetes
        assert "[" in anonimizado and "]" in anonimizado

        # Round-trip exacto: anonimizar → deanonimizar recupera el original
        recuperado = deanonimizar_texto(anonimizado, mapa.mapa_inverso)
        assert recuperado == original

    def test_variantes_cliente_a_etiqueta_unica(self) -> None:
        """§14: variantes OCR del cliente E&V se anonimizan todas a la misma
        etiqueta canónica, aunque el motor no las detecte por sí solo."""
        from core.anon.anonimizar import MapaEntidades, anonimizar_variantes_conocidas
        from core.config import VARIANTES_OCR_CLIENTE

        texto = (
            "Demanda de ENGEL & VÖLKERS SPAIN, S.L. contra el propietario. "
            "La mercantil Engel £ Vólkers actuó como mediadora; "
            "ENGEL 8 VÖLKERS gestionó la operación."
        )
        mapa = MapaEntidades()
        variantes = VARIANTES_OCR_CLIENTE["ENGEL_VOLKERS_SPAIN"]
        out = anonimizar_variantes_conocidas(texto, mapa, variantes, _logger_silencioso())

        # Ninguna variante sobrevive literal.
        assert "VÖLKERS" not in out and "Vólkers" not in out
        # Todas comparten una única etiqueta canónica [EMPRESA...].
        etiquetas = set(re.findall(r"\[EMPRESA(?:_\d+)?\]", out))
        assert len(etiquetas) == 1

    def test_email_ocr_arroba_corrompida(self) -> None:
        """§15: emails con '@' transcrito como Q/O por OCR deben anonimizarse."""
        original = (
            "Contacto: cubriaQdelriomiera.es y "
            "gutierrezOengelvoelkers.com. Texto normal con Oviedo y Quito."
        )
        anonimizado, _ = _anonimizar_sin_presidio(original)
        assert "cubriaQdelriomiera.es" not in anonimizado
        assert "gutierrezOengelvoelkers.com" not in anonimizado
        # No debe romper palabras corrientes con O/Q sin cola de dominio.
        assert "Oviedo" in anonimizado and "Quito" in anonimizado

    def test_nig_no_se_anonimiza_como_cuenta(self) -> None:
        """§19: el NIG (19 dígitos) es un identificador procesal público, no
        PII bancaria. No debe capturarse como [CUENTA]."""
        original = (
            "NIG: 3907542120260004548\n"
            "Cuenta de consignaciones: 12345678901234567890"
        )
        anonimizado, _ = _anonimizar_sin_presidio(original)
        # El NIG sobrevive literal; la cuenta de 20 dígitos sí se anonimiza.
        assert "3907542120260004548" in anonimizado
        assert "12345678901234567890" not in anonimizado

    def test_partes_comprimidas_sin_puntuacion(self) -> None:
        """§3+§4: en formato comprimido sin punto entre partes, anonimizar
        no debe engullir la palabra 'Demandado' de la línea siguiente."""
        original = (
            "Demandante: DON IVAN PETROV SOKOLOV\n"
            "Demandado: DOÑA MARIA GARCIA LOPEZ"
        )
        anonimizado, mapa = _anonimizar_sin_presidio(original)

        assert "IVAN PETROV SOKOLOV" not in anonimizado
        assert "MARIA GARCIA LOPEZ" not in anonimizado
        # La etiqueta estructural 'Demandado:' debe sobrevivir (no borrarse).
        assert "Demandado" in anonimizado
        # Round-trip exacto.
        recuperado = deanonimizar_texto(anonimizado, mapa.mapa_inverso)
        assert recuperado == original

    def test_procurador_no_se_anonimiza(self) -> None:
        """Los operadores jurídicos (procurador, magistrado, juez, LAJ, ...)
        están en la lista blanca del Anonimizador y NO se anonimizan por
        diseño: el ejercicio de funciones públicas/profesionales no es
        dato personal en sentido RGPD (art. 9 Ley 29/2021, doctrina AEPD).
        """
        original = (
            "Demandante: DON IVAN PETROV SOKOLOV.\n"
            "Procurador: DON JUAN MARTINEZ RUIZ."
        )
        anonimizado, mapa = _anonimizar_sin_presidio(original)

        # La parte sí se anonimiza
        assert "IVAN PETROV SOKOLOV" not in anonimizado
        # El procurador permanece literal — está protegido
        assert "JUAN MARTINEZ RUIZ" in anonimizado
        # Y aparece en el set de protegidos del mapa
        assert any("JUAN MARTINEZ RUIZ" in p for p in mapa.protegidos)


# ---------------------------------------------------------------------------
# MapaEntidades — extensión Fase 1 (init con dicts + cargar_json)
# ---------------------------------------------------------------------------

class TestMapaEntidades:
    def test_init_vacio(self) -> None:
        mapa = MapaEntidades()
        assert mapa.mapa == {}
        assert mapa.mapa_inverso == {}
        assert dict(mapa.contadores) == {}
        assert mapa.protegidos == set()

    def test_init_con_dicts(self) -> None:
        mapa = MapaEntidades(
            protegidos={"JUAN PEREZ"},
            mapa={"Pedro Lopez": "[NOMBRE]"},
            mapa_inverso={"[NOMBRE]": "Pedro Lopez"},
            contadores={"NOMBRE": 1, "DNI": 3},
        )
        assert mapa.contadores["NOMBRE"] == 1
        assert mapa.contadores["DNI"] == 3
        # Comportamiento defaultdict preservado
        assert mapa.contadores["NUEVO"] == 0
        assert "JUAN PEREZ" in mapa.protegidos

    def test_persistencia_json(self, tmp_path: Path) -> None:
        # Crear mapa con datos completos (mapa + contadores + protegidos)
        mapa = MapaEntidades(protegidos={"ILMO. SR. D. JOSE LOPEZ"})
        mapa.registrar_dato("12345678A", "DNI")
        mapa.registrar_dato("87654321B", "DNI")  # incrementa contador

        ruta = tmp_path / "_mapa.json"
        mapa.exportar_json(ruta)

        # Inspección directa: contadores y protegidos están en el JSON
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        assert "contadores" in datos
        assert datos["contadores"]["DNI"] == 2
        assert "protegidos" in datos
        assert "ILMO. SR. D. JOSE LOPEZ" in datos["protegidos"]

        # Round-trip por la API
        mapa2 = MapaEntidades.cargar_json(ruta)
        assert mapa2.contadores["DNI"] == 2
        assert "ILMO. SR. D. JOSE LOPEZ" in mapa2.protegidos
        assert mapa2.mapa == mapa.mapa
        assert mapa2.mapa_inverso == mapa.mapa_inverso

    def test_compatibilidad_json_antiguo(self, tmp_path: Path) -> None:
        """Tolera _mapa.json de versiones anteriores que solo tenían `mapa`."""
        antiguo = {
            "generado": "2026-05-07T10:00:00",
            "mapa": {"[NOMBRE]": "Ivan Petrov"},
        }
        ruta = tmp_path / "antiguo.json"
        ruta.write_text(json.dumps(antiguo, ensure_ascii=False), encoding="utf-8")

        mapa = MapaEntidades.cargar_json(ruta)
        assert mapa.mapa_inverso["[NOMBRE]"] == "Ivan Petrov"
        assert mapa.mapa["Ivan Petrov"] == "[NOMBRE]"


# ---------------------------------------------------------------------------
# mapa_caso.py — integración con case_manager
# ---------------------------------------------------------------------------

class TestMapaCaso:
    def test_ruta_y_persistencia(self, tmp_path: Path, monkeypatch) -> None:
        # Aislamos via monkeypatch del símbolo `caso_path` que mapa_caso.py
        # ya importó. Settings es frozen (no se puede modificar casos_root
        # directamente) — patchear el caller es suficiente.
        def _caso_path_test(case_id: str) -> Path:
            return tmp_path / case_id

        monkeypatch.setattr("core.anon.mapa_caso.caso_path", _caso_path_test)

        case_id = "EV-2099-001"

        # Carga inicial: mapa vacío (la subcarpeta aún no existe)
        mapa = cargar_mapa_caso(case_id)
        assert mapa.mapa == {}

        # Modificar y guardar — guardar_mapa_caso debe crear la subcarpeta
        mapa.registrar_dato("12345678A", "DNI")
        ruta = guardar_mapa_caso(case_id, mapa)
        assert ruta.exists()
        assert ruta == ruta_mapa_caso(case_id)
        assert ruta.parent.name == "06_Anonimizado"

        # Re-cargar y comprobar persistencia + contadores intactos
        mapa2 = cargar_mapa_caso(case_id)
        assert mapa2.mapa["12345678A"] == "[DNI]"
        assert mapa2.contadores["DNI"] == 1
