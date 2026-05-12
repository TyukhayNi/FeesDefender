"""Tests de ``core.anon.deanonimizar._localizar_mapa`` — Hilo H3 SaRS1.

Cubre los 4 niveles de búsqueda del mapa de entidades:

  1. Legacy ``<doc>_mapa.json`` adyacente al .md (Anonimizador original
     de Expedientes Seguros — estructura plana).
  2. Legacy ``_para_IA`` ↔ ``_anonimizados`` (layout antiguo).
  3. Mapa de caso FeesDefender ``06_Anonimizado/_mapa_caso.json``.
  4. Fallback por frontmatter (``mapa_caso_path`` / ``mapa_entidades``).

Y un test de integración end-to-end: construir un mapa compartido, guardar
como ``_mapa_caso.json``, generar un .md anonimizado con etiquetas, llamar
``deanonimizar()``, verificar que el texto reconstruido contiene los valores
reales esperados.

Estos tests son rápidos (no cargan Presidio + spaCy) y no tocan red ni
ningún caso real. Operan íntegramente sobre ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.anon.deanonimizar import (
    _localizar_mapa,
    _mapa_desde_frontmatter,
    deanonimizar,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escribir_md(ruta: Path, frontmatter: dict | None = None, cuerpo: str = "") -> Path:
    """Escribe un .md mínimo con frontmatter YAML opcional."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if frontmatter:
        import yaml
        fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
        contenido = f"---\n{fm}\n---\n{cuerpo}"
    else:
        contenido = cuerpo
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _escribir_mapa(ruta: Path, mapa: dict[str, str]) -> Path:
    """Escribe un JSON con la clave ``mapa`` que es la que consume
    ``deanonimizar()``. Estructura compatible con
    ``MapaEntidades.exportar_json``."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generado": "2026-05-12T00:00:00",
        "mapa": mapa,                                   # etiqueta → valor real
        "mapa_directo": {v: k for k, v in mapa.items()},
        "contadores": {},
        "protegidos": [],
    }
    ruta.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


# ---------------------------------------------------------------------------
# Nivel 1 — legacy adyacente
# ---------------------------------------------------------------------------

def test_nivel1_legacy_mapa_adyacente(tmp_path: Path) -> None:
    """Regresión: si existe ``<base>_mapa.json`` junto al .md, se usa ese
    (independientemente de lo que haya más arriba en el árbol)."""
    md = _escribir_md(tmp_path / "doc1_anonimizado.md", cuerpo="[NOMBRE] firma.")
    mapa = _escribir_mapa(tmp_path / "doc1_mapa.json", {"[NOMBRE]": "Juan"})

    encontrado = _localizar_mapa(md, "doc1")

    assert encontrado == mapa


def test_nivel1_prioritario_sobre_caso(tmp_path: Path) -> None:
    """Si coexisten un mapa adyacente legacy y un ``_mapa_caso.json`` del
    caso, prevalece el adyacente (retrocompat estricta)."""
    anon_dir = tmp_path / "caso" / "06_Anonimizado"
    md = _escribir_md(anon_dir / "doc1.md", cuerpo="[NOMBRE] firma.")
    # Legacy adyacente
    legacy = _escribir_mapa(anon_dir / "doc1_mapa.json", {"[NOMBRE]": "Juan"})
    # Mapa de caso (debería ignorarse)
    _escribir_mapa(anon_dir / "_mapa_caso.json", {"[NOMBRE]": "Pedro"})

    encontrado = _localizar_mapa(md, "doc1")

    assert encontrado == legacy


# ---------------------------------------------------------------------------
# Nivel 2 — legacy `_para_IA` → `_anonimizados`
# ---------------------------------------------------------------------------

def test_nivel2_legacy_para_IA(tmp_path: Path) -> None:
    """Layout antiguo de Expedientes Seguros: el .md está en ``_para_IA/`` y
    el mapa en la carpeta hermana ``_anonimizados/``."""
    md = _escribir_md(tmp_path / "_para_IA" / "doc1_anonimizado.md")
    mapa = _escribir_mapa(
        tmp_path / "_anonimizados" / "doc1_mapa.json",
        {"[NOMBRE]": "Juan"},
    )

    encontrado = _localizar_mapa(md, "doc1")

    assert encontrado == mapa


# ---------------------------------------------------------------------------
# Nivel 3 — mapa de caso FeesDefender
# ---------------------------------------------------------------------------

def test_nivel3_mapa_caso_en_06_anonimizado(tmp_path: Path) -> None:
    """Sin mapa adyacente, ``_mapa_caso.json`` en el ancestro
    ``06_Anonimizado/`` se reconoce como mapa válido."""
    anon_dir = tmp_path / "casos" / "SaRS1" / "06_Anonimizado"
    md = _escribir_md(anon_dir / "demanda.md", cuerpo="[NOMBRE_1] firma.")
    mapa_caso = _escribir_mapa(
        anon_dir / "_mapa_caso.json",
        {"[NOMBRE_1]": "Juan García", "[DNI]": "12345678A"},
    )

    encontrado = _localizar_mapa(md, "demanda")

    assert encontrado == mapa_caso


def test_nivel3_mapa_caso_en_subcarpeta_no_se_propaga_por_descendientes_lejanos(
    tmp_path: Path,
) -> None:
    """``06_Anonimizado/`` solo debe matchear como ancestro **inmediato**
    en la cadena de parents. Si el .md está dentro de una subcarpeta del
    propio 06_Anonimizado, debe seguir funcionando (el ancestro existe)."""
    anon_dir = tmp_path / "casos" / "SaRS1" / "06_Anonimizado"
    md = _escribir_md(
        anon_dir / "subcarpeta" / "doc.md",
        cuerpo="[NOMBRE] firma.",
    )
    mapa_caso = _escribir_mapa(
        anon_dir / "_mapa_caso.json",
        {"[NOMBRE]": "Pedro"},
    )

    encontrado = _localizar_mapa(md, "doc")

    assert encontrado == mapa_caso


# ---------------------------------------------------------------------------
# Nivel 4 — fallback por frontmatter
# ---------------------------------------------------------------------------

def test_nivel4_frontmatter_mapa_caso_path_absoluto(tmp_path: Path) -> None:
    """Si el .md declara ``mapa_caso_path`` (absoluto) en el frontmatter,
    se usa tal cual aunque no esté en ningún árbol canónico."""
    mapa = _escribir_mapa(tmp_path / "mapa_arbitrario.json", {"[NOMBRE]": "Juan"})
    md = _escribir_md(
        tmp_path / "fuera_de_todo" / "doc.md",
        frontmatter={"mapa_caso_path": str(mapa)},
        cuerpo="[NOMBRE] firma.",
    )

    encontrado = _localizar_mapa(md, "doc")

    assert encontrado == mapa


def test_nivel4_frontmatter_mapa_entidades_alias(tmp_path: Path) -> None:
    """El alias ``mapa_entidades`` también se reconoce."""
    mapa = _escribir_mapa(tmp_path / "alias.json", {"[NOMBRE]": "Juan"})
    md = _escribir_md(
        tmp_path / "doc.md",
        frontmatter={"mapa_entidades": str(mapa)},
        cuerpo="[NOMBRE] firma.",
    )

    encontrado = _localizar_mapa(md, "doc")

    assert encontrado == mapa


def test_nivel4_frontmatter_path_relativo(tmp_path: Path) -> None:
    """Path relativo en el frontmatter se resuelve respecto al directorio
    del propio .md."""
    sub = tmp_path / "sub"
    sub.mkdir()
    mapa = _escribir_mapa(sub / "mi_mapa.json", {"[NOMBRE]": "Juan"})
    md = _escribir_md(
        sub / "doc.md",
        frontmatter={"mapa_caso_path": "mi_mapa.json"},
        cuerpo="[NOMBRE] firma.",
    )

    encontrado = _localizar_mapa(md, "doc")

    assert encontrado is not None
    assert encontrado.resolve() == mapa.resolve()


def test_helper_mapa_desde_frontmatter_devuelve_none_si_no_hay(tmp_path: Path) -> None:
    """El helper interno no propaga excepciones ni devuelve None inesperado:
    si no hay frontmatter, devuelve ``None`` limpiamente."""
    md = _escribir_md(tmp_path / "doc.md", cuerpo="texto plano")

    assert _mapa_desde_frontmatter(md) is None


# ---------------------------------------------------------------------------
# Resultado None — sin mapa accesible
# ---------------------------------------------------------------------------

def test_devuelve_none_sin_mapa(tmp_path: Path) -> None:
    """Comportamiento existente: si no hay mapa por ningún camino,
    devuelve ``None``."""
    md = _escribir_md(tmp_path / "doc.md", cuerpo="texto sin etiquetas")

    assert _localizar_mapa(md, "doc") is None


def test_devuelve_none_frontmatter_apunta_a_inexistente(tmp_path: Path) -> None:
    """Frontmatter declara un path que no existe en disco → ``None``."""
    md = _escribir_md(
        tmp_path / "doc.md",
        frontmatter={"mapa_caso_path": "/tmp/no_existe_99999.json"},
        cuerpo="texto",
    )

    assert _localizar_mapa(md, "doc") is None


# ---------------------------------------------------------------------------
# Integración end-to-end — anonimizar → guardar → deanonimizar → reconstruir
# ---------------------------------------------------------------------------

def test_integracion_round_trip_con_mapa_caso(tmp_path: Path) -> None:
    """Round-trip end-to-end usando el formato nuevo ``_mapa_caso.json``:

    1. Construir un mapa con entidades reales.
    2. Persistirlo en ``06_Anonimizado/_mapa_caso.json`` con la estructura
       que produce ``MapaEntidades.exportar_json``.
    3. Escribir un .md anonimizado en ``06_Anonimizado/`` que contiene
       solo las etiquetas (texto sintético, sin Presidio).
    4. Llamar ``deanonimizar(.md)`` y comprobar que el .md de salida
       contiene los valores reales.

    Este es el comportamiento que H3 desbloquea: previamente,
    ``_localizar_mapa`` no reconocía el ``_mapa_caso.json`` del caso y
    ``deanonimizar()`` fallaba con ``FileNotFoundError``.
    """
    anon_dir = tmp_path / "casos" / "SaRS1" / "06_Anonimizado"
    mapa_real = {
        "[NOMBRE_1]":     "Juan García López",
        "[NOMBRE_2]":     "María Pérez Ruiz",
        "[DNI]":          "12345678A",
        "[DIRECCION_1]":  "Calle Castelar 37, Santander",
    }
    _escribir_mapa(anon_dir / "_mapa_caso.json", mapa_real)

    cuerpo_anonimizado = (
        "Demanda interpuesta por [NOMBRE_1], con DNI [DNI], "
        "domiciliado en [DIRECCION_1], contra [NOMBRE_2]."
    )
    md_anon = _escribir_md(
        anon_dir / "demanda_anonimizado.md",
        frontmatter={
            "case_id":       "SaRS1",
            "tipo":          "documento_anonimizado",
            "fase":          "06_Anonimizado",
            "slug":          "demanda",
        },
        cuerpo=cuerpo_anonimizado,
    )

    ruta_salida = deanonimizar(md_anon)

    assert ruta_salida.exists()
    assert ruta_salida.name == "demanda_deanonimizado.md"
    texto_salida = ruta_salida.read_text(encoding="utf-8")

    # Todos los valores reales aparecen
    for valor_real in mapa_real.values():
        assert valor_real in texto_salida, f"no se reconstruyó: {valor_real}"

    # Ninguna etiqueta queda sin resolver
    for etiqueta in mapa_real:
        assert etiqueta not in texto_salida, f"etiqueta sin resolver: {etiqueta}"


def test_integracion_deanonimizar_falla_sin_mapa(tmp_path: Path) -> None:
    """Si el .md está dentro de ``06_Anonimizado/`` pero no hay ningún
    mapa accesible, ``deanonimizar()`` lanza ``FileNotFoundError`` (sin
    cambio respecto al comportamiento existente)."""
    anon_dir = tmp_path / "06_Anonimizado"
    md = _escribir_md(anon_dir / "doc.md", cuerpo="[NOMBRE] firma.")

    with pytest.raises(FileNotFoundError):
        deanonimizar(md)
