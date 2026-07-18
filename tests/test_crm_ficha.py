from pathlib import Path

import pytest

from core.crm_ficha import FichaCRMInput, cargar_ficha_yaml
from core.sudespacho_relations import NuevoClienteContrario, NuevoColaborador


def _escribir(path: Path, texto: str) -> Path:
    path.write_text(texto, encoding="utf-8")
    return path


def test_cargar_ficha_yaml_completo(tmp_path):
    y = _escribir(tmp_path / "_ficha_crm.yaml", """
cliente_propio: EV_MMC_SPAIN
contrario:
  nombre: JUAN
  apellido1: PEREZ
  apellido2: GOMEZ
  nif: 00000000T
  email: juan@example.invalid
  movil: "+34 600 111 222"
  direccion: Calle Falsa 1
  poblacion: Barcelona
colaboradores:
  - nombre: ANA CONSULTORA
    email: ana@engelvoelkers.example
    movil: "600 333 444"
    telefono: "934 000 111"
notas_html: "<p>Reclamación de honorarios (Vuelta).</p>"
""")
    ficha = cargar_ficha_yaml(y)
    assert isinstance(ficha, FichaCRMInput)
    assert ficha.cliente_propio == "EV_MMC_SPAIN"
    assert isinstance(ficha.contrario, NuevoClienteContrario)
    assert ficha.contrario.apellido1 == "PEREZ"
    assert ficha.contrario.movil == "600111222"          # normalizado por el DTO (B3)
    assert len(ficha.colaboradores) == 1
    assert isinstance(ficha.colaboradores[0], NuevoColaborador)
    assert ficha.colaboradores[0].telefono == "934000111"  # normalizado
    assert "honorarios" in ficha.notas_html


def test_cargar_ficha_yaml_contrario_opcional(tmp_path):
    y = _escribir(tmp_path / "_ficha_crm.yaml",
                  "colaboradores: []\nnotas_html: hola\n")
    ficha = cargar_ficha_yaml(y)
    assert ficha.contrario is None
    assert ficha.colaboradores == []
    assert ficha.cliente_propio == "EV_MMC_SPAIN"   # default


def test_cargar_ficha_yaml_no_existe_lanza(tmp_path):
    with pytest.raises(FileNotFoundError):
        cargar_ficha_yaml(tmp_path / "no.yaml")


def test_cargar_ficha_yaml_contrario_sin_nombre_lanza(tmp_path):
    y = _escribir(tmp_path / "_ficha_crm.yaml", "contrario:\n  nif: X\n")
    with pytest.raises(ValueError):
        cargar_ficha_yaml(y)
