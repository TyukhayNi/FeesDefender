"""Tests para core.casos.case_locator — Fase 1 subdivisión por ciudades."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def root(tmp_path, monkeypatch):
    """CASOS_ROOT aislado en tmp_path."""
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    yield r


# ---------------------------------------------------------------------------
# path_for — layout flat (legacy)
# ---------------------------------------------------------------------------

class TestPathForFlat:
    def test_caso_existente(self, root):
        from core.casos.case_locator import path_for
        (root / "BaRR3 - Roser").mkdir()
        assert path_for("BaRR3 - Roser") == root / "BaRR3 - Roser"

    def test_caso_inexistente_devuelve_flat(self, root):
        from core.casos.case_locator import path_for
        result = path_for("NO-EXISTE")
        assert result == root / "NO-EXISTE"
        assert not result.exists()

    def test_ignora_carpeta_sistema(self, root):
        from core.casos.case_locator import path_for
        (root / "_PLANTILLA").mkdir()
        result = path_for("_PLANTILLA")
        assert result == root / "_PLANTILLA"


# ---------------------------------------------------------------------------
# path_for — layout por ciudades
# ---------------------------------------------------------------------------

class TestPathForCiudad:
    def test_caso_en_barcelona(self, root):
        from core.casos.case_locator import path_for
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert path_for("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"

    def test_caso_en_sin_clasificar(self, root):
        from core.casos.case_locator import path_for
        (root / "_Sin clasificar" / "CASO-X").mkdir(parents=True)
        assert path_for("CASO-X") == root / "_Sin clasificar" / "CASO-X"

    def test_flat_tiene_prioridad_sobre_ciudad(self, root):
        from core.casos.case_locator import path_for
        (root / "BaRR3 - Roser").mkdir()
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert path_for("BaRR3 - Roser") == root / "BaRR3 - Roser"


# ---------------------------------------------------------------------------
# path_for_ciudad
# ---------------------------------------------------------------------------

class TestPathForCiudadExplicita:
    def test_compone_ruta(self, root):
        from core.casos.case_locator import path_for_ciudad
        result = path_for_ciudad("BaRR3 - Roser", "Barcelona")
        assert result == root / "Barcelona" / "BaRR3 - Roser"
        assert not result.exists()

    def test_sin_clasificar(self, root):
        from core.casos.case_locator import path_for_ciudad
        result = path_for_ciudad("CASO-X", "_Sin clasificar")
        assert result == root / "_Sin clasificar" / "CASO-X"


# ---------------------------------------------------------------------------
# list_cases
# ---------------------------------------------------------------------------

class TestListCases:
    def test_flat_solo(self, root):
        from core.casos.case_locator import list_cases
        (root / "BaRR3 - Roser").mkdir()
        (root / "MaRS2 - Puerto Rico").mkdir()
        (root / "_PLANTILLA").mkdir()
        result = [p.name for p in list_cases()]
        assert result == ["BaRR3 - Roser", "MaRS2 - Puerto Rico"]

    def test_ciudad_solo(self, root):
        from core.casos.case_locator import list_cases
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        (root / "Madrid" / "MaRS2 - Puerto Rico").mkdir(parents=True)
        result = [p.name for p in list_cases()]
        assert result == ["BaRR3 - Roser", "MaRS2 - Puerto Rico"]

    def test_mixto_flat_y_ciudad(self, root):
        from core.casos.case_locator import list_cases
        (root / "SaRS1 - Castelar").mkdir()
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        result = [p.name for p in list_cases()]
        assert "BaRR3 - Roser" in result
        assert "SaRS1 - Castelar" in result

    def test_sin_duplicados(self, root):
        from core.casos.case_locator import list_cases
        (root / "BaRR3 - Roser").mkdir()
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        names = [p.name for p in list_cases()]
        assert names.count("BaRR3 - Roser") == 1

    def test_filtro_por_ciudad(self, root):
        from core.casos.case_locator import list_cases
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        (root / "Madrid" / "MaRS2 - Puerto Rico").mkdir(parents=True)
        result = [p.name for p in list_cases(ciudad="Barcelona")]
        assert result == ["BaRR3 - Roser"]

    def test_filtro_ciudad_inexistente(self, root):
        from core.casos.case_locator import list_cases
        result = list(list_cases(ciudad="Bilbao"))
        assert result == []

    def test_root_inexistente(self, root, monkeypatch):
        import shutil
        shutil.rmtree(root)
        from core.casos.case_locator import list_cases
        result = list(list_cases())
        assert result == []

    def test_no_incluye_carpetas_ciudad_como_caso(self, root):
        from core.casos.case_locator import list_cases
        (root / "Barcelona").mkdir()
        (root / "Madrid").mkdir()
        (root / "SaRS1 - Castelar").mkdir()
        names = [p.name for p in list_cases()]
        assert "Barcelona" not in names
        assert "Madrid" not in names
        assert "SaRS1 - Castelar" in names


# ---------------------------------------------------------------------------
# all_cities_present
# ---------------------------------------------------------------------------

class TestAllCitiesPresent:
    def test_vacio(self, root):
        from core.casos.case_locator import all_cities_present
        assert all_cities_present() == []

    def test_con_ciudades(self, root):
        from core.casos.case_locator import all_cities_present
        (root / "Barcelona" / "BaRR3").mkdir(parents=True)
        (root / "Madrid" / "MaRS2").mkdir(parents=True)
        (root / "Sevilla").mkdir()
        result = all_cities_present()
        assert "Barcelona" in result
        assert "Madrid" in result
        assert "Sevilla" not in result

    def test_sin_clasificar(self, root):
        from core.casos.case_locator import all_cities_present
        (root / "_Sin clasificar" / "CASO-X").mkdir(parents=True)
        assert "_Sin clasificar" in all_cities_present()


# ---------------------------------------------------------------------------
# move_to_city — Fase 3
# ---------------------------------------------------------------------------

class TestMoveToCity:
    def test_mover_flat_a_ciudad(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("BaRR3 - Roser")
        dest = move_to_city("BaRR3 - Roser", "Barcelona",
                            "reasignación correcta", "nikolai")
        assert dest == root / "Barcelona" / "BaRR3 - Roser"
        assert dest.is_dir()
        assert not (root / "BaRR3 - Roser").exists()

    def test_mover_entre_ciudades(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("CASO-X", ciudad="Madrid")
        dest = move_to_city("CASO-X", "Barcelona",
                            "reubicación del caso", "nikolai")
        assert dest == root / "Barcelona" / "CASO-X"
        assert not (root / "Madrid" / "CASO-X").exists()

    def test_actualiza_metadata_ciudad(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        import yaml
        ensure_case("BaRR3 - Roser", ciudad="Sevilla")
        move_to_city("BaRR3 - Roser", "Barcelona",
                     "corrección de ciudad", "nikolai")
        index = root / "Barcelona" / "BaRR3 - Roser" / "00_Input" / "_caso.md"
        text = index.read_text(encoding="utf-8")
        _, fm_raw, _ = text.split("---", 2)
        fm = yaml.safe_load(fm_raw)
        assert fm["ciudad"] == "Barcelona"

    def test_escribe_audit_log(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        import json
        ensure_case("BaRR3 - Roser")
        move_to_city("BaRR3 - Roser", "Barcelona",
                     "reasignación correcta", "nikolai")
        log = root / "_audit" / "relocations.jsonl"
        assert log.exists()
        entry = json.loads(log.read_text(encoding="utf-8").strip())
        assert entry["operacion"] == "reasignar_ciudad"
        assert entry["ciudad_destino"] == "Barcelona"
        assert entry["usuario"] == "nikolai"

    def test_motivo_corto_rechazado(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("BaRR3 - Roser")
        with pytest.raises(ValueError, match="10 caracteres"):
            move_to_city("BaRR3 - Roser", "Barcelona", "corto", "nikolai")

    def test_caso_inexistente(self, root):
        from core.casos.case_locator import move_to_city
        with pytest.raises(FileNotFoundError):
            move_to_city("NO-EXISTE", "Barcelona",
                         "motivo suficiente", "nikolai")

    def test_rollback_si_falla_metadata(self, root, monkeypatch):
        from core.case_manager import ensure_case
        from core.casos import case_locator
        ensure_case("BaRR3 - Roser")
        original = case_locator._update_ciudad_metadata
        def _boom(*a, **kw):
            raise OSError("simulación de fallo")
        monkeypatch.setattr(case_locator, "_update_ciudad_metadata", _boom)
        with pytest.raises(OSError):
            case_locator.move_to_city("BaRR3 - Roser", "Barcelona",
                                      "motivo suficiente", "nikolai")
        assert (root / "BaRR3 - Roser").is_dir()
        assert not (root / "Barcelona" / "BaRR3 - Roser").exists()

    def test_mismo_destino_noop(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import move_to_city
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        dest = move_to_city("BaRR3 - Roser", "Barcelona",
                            "ya estaba aquí", "nikolai")
        assert dest == root / "Barcelona" / "BaRR3 - Roser"
        assert dest.is_dir()


# ---------------------------------------------------------------------------
# Fase 2 — campo ciudad en ensure_case
# ---------------------------------------------------------------------------

class TestEnsureCaseConCiudad:
    def test_caso_nuevo_con_ciudad_crea_bajo_ciudad(self, root):
        from core.case_manager import ensure_case
        path = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert path == root / "Barcelona" / "BaRR3 - Roser"
        assert path.is_dir()
        assert (path / "00_Input" / "_caso.md").exists()

    def test_caso_nuevo_sin_ciudad_crea_flat(self, root):
        from core.case_manager import ensure_case
        path = ensure_case("BaRR3 - Roser")
        assert path == root / "BaRR3 - Roser"
        assert path.is_dir()

    def test_ciudad_persistida_en_frontmatter(self, root):
        from core.case_manager import ensure_case
        import yaml
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        index = root / "Barcelona" / "BaRR3 - Roser" / "00_Input" / "_caso.md"
        text = index.read_text(encoding="utf-8")
        _, fm_raw, _ = text.split("---", 2)
        fm = yaml.safe_load(fm_raw)
        assert fm["ciudad"] == "Barcelona"
        assert fm["meta"]["ciudad"] == "Barcelona"

    def test_caso_existente_no_se_mueve(self, root):
        from core.case_manager import ensure_case
        path1 = ensure_case("BaRR3 - Roser")
        assert path1 == root / "BaRR3 - Roser"
        path2 = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert path2 == root / "BaRR3 - Roser"
        assert not (root / "Barcelona" / "BaRR3 - Roser").exists()

    def test_caso_existente_actualiza_ciudad_en_metadata(self, root):
        from core.case_manager import ensure_case
        import yaml
        ensure_case("BaRR3 - Roser")
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        index = root / "BaRR3 - Roser" / "00_Input" / "_caso.md"
        text = index.read_text(encoding="utf-8")
        _, fm_raw, _ = text.split("---", 2)
        fm = yaml.safe_load(fm_raw)
        assert fm["ciudad"] == "Barcelona"
        assert fm["meta"]["ciudad"] == "Barcelona"

    def test_locator_encuentra_caso_en_ciudad(self, root):
        from core.case_manager import ensure_case
        from core.casos.case_locator import path_for
        ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert path_for("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"

    def test_idempotencia_con_ciudad(self, root):
        from core.case_manager import ensure_case
        p1 = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        p2 = ensure_case("BaRR3 - Roser", ciudad="Barcelona")
        assert p1 == p2

    def test_caso_nuevo_ciudad_sin_clasificar(self, root):
        from core.case_manager import ensure_case
        path = ensure_case("CASO-X", ciudad="_Sin clasificar")
        assert path == root / "_Sin clasificar" / "CASO-X"
        assert path.is_dir()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAppendAuditLog:
    def test_crea_directorio_y_fichero(self, root):
        from core.casos.case_locator import append_audit_log
        import json
        append_audit_log({"operacion": "test", "case_id": "X"})
        log = root / "_audit" / "relocations.jsonl"
        assert log.exists()
        entry = json.loads(log.read_text(encoding="utf-8").strip())
        assert entry["operacion"] == "test"
        assert "ts" in entry

    def test_append_no_sobrescribe(self, root):
        from core.casos.case_locator import append_audit_log
        append_audit_log({"operacion": "a"})
        append_audit_log({"operacion": "b"})
        log = root / "_audit" / "relocations.jsonl"
        lines = log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Integración con caso_path de config.py
# ---------------------------------------------------------------------------

class TestCasoPathDelegaAlLocator:
    def test_flat(self, root):
        from core.config import caso_path
        (root / "BaRR3 - Roser").mkdir()
        assert caso_path("BaRR3 - Roser") == root / "BaRR3 - Roser"

    def test_ciudad(self, root):
        from core.config import caso_path
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert caso_path("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"


# ---------------------------------------------------------------------------
# Integración con list_cases de case_manager.py
# ---------------------------------------------------------------------------

class TestCaseManagerListCases:
    def test_flat(self, root):
        from core.case_manager import list_cases
        (root / "BaRR3 - Roser").mkdir()
        (root / "_PLANTILLA").mkdir()
        assert list_cases() == ["BaRR3 - Roser"]

    def test_ciudad(self, root):
        from core.case_manager import list_cases
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert list_cases() == ["BaRR3 - Roser"]


# ---------------------------------------------------------------------------
# read_case_meta — Fase 2 B2
# ---------------------------------------------------------------------------

class TestReadCaseMeta:
    def test_read_case_meta_devuelve_meta(self, tmp_path):
        from core.casos.case_locator import read_case_meta
        case_dir = tmp_path / "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
        (case_dir / "00_Input").mkdir(parents=True)
        (case_dir / "00_Input" / "_caso.md").write_text(
            "---\n"
            "ciudad: Barcelona\n"
            "meta:\n"
            "  tipo_caso: VUELTA\n"
            "  ciudad: Barcelona\n"
            "  direccion: Falsa 1\n"
            "  id_go: W-000AAA\n"
            "---\n\n# Caso\n",
            encoding="utf-8",
        )
        meta = read_case_meta(case_dir)
        assert meta["tipo_caso"] == "VUELTA"
        assert meta["ciudad"] == "Barcelona"
        assert meta["id_go"] == "W-000AAA"

    def test_read_case_meta_sin_fichero_devuelve_vacio(self, tmp_path):
        from core.casos.case_locator import read_case_meta
        assert read_case_meta(tmp_path / "no-existe") == {}

    def test_read_case_meta_encoding_corrupto_devuelve_vacio(self, tmp_path):
        """Regresión: no-UTF8 debe devolver {} en lugar de lanzar UnicodeDecodeError."""
        from core.casos.case_locator import read_case_meta
        case_dir = tmp_path / "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
        (case_dir / "00_Input").mkdir(parents=True)
        # Frontmatter con un byte cp1252 (0xf1 = 'ñ' en latin-1), inválido en UTF-8
        (case_dir / "00_Input" / "_caso.md").write_bytes(
            b"---\nmeta:\n  ciudad: Barcelona\n  direcci\xf1n: X\n---\n"
        )
        result = read_case_meta(case_dir)
        assert result == {}

    def test_read_case_meta_yaml_corrupto_devuelve_vacio(self, tmp_path):
        """Regresión: frontmatter YAML malformado debe devolver {} en lugar de lanzar YAMLError."""
        from core.casos.case_locator import read_case_meta
        case_dir = tmp_path / "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
        (case_dir / "00_Input").mkdir(parents=True)
        # YAML inválido: lista sin cerrar
        (case_dir / "00_Input" / "_caso.md").write_text(
            "---\nmeta:\n  - [unterminated\n---\n",
            encoding="utf-8",
        )
        result = read_case_meta(case_dir)
        assert result == {}


# ---------------------------------------------------------------------------
# resolve_ref — Fase 2 B2
# ---------------------------------------------------------------------------

class TestResolveRef:
    def test_resolve_ref_encoding_corrupto_no_lanza(self, root):
        """Regresión: _id_go_of con no-UTF8 vía resolve_ref no debe lanzar."""
        from core.casos.case_locator import resolve_ref
        case_dir = root / "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
        (case_dir / "00_Input").mkdir(parents=True)
        # Frontmatter con byte cp1252 inválido en UTF-8
        (case_dir / "00_Input" / "_caso.md").write_bytes(
            b"---\nmeta:\n  id_go: W-000AAA\n  direcci\xf1n: X\n---\n"
        )
        # resolve_ref no debe lanzar; si no encuentra por id_go (por el error), devuelve ref tal cual
        result = resolve_ref("W-000AAA")
        assert result == "W-000AAA"

    def test_resolve_ref_yaml_corrupto_no_lanza(self, root):
        """Regresión: _id_go_of con YAML malformado vía resolve_ref no debe lanzar."""
        from core.casos.case_locator import resolve_ref
        case_dir = root / "BaRS11 - Falsa 1 (W-000AAA) - Vuelta"
        (case_dir / "00_Input").mkdir(parents=True)
        # YAML inválido pero encoding UTF-8 válido
        (case_dir / "00_Input" / "_caso.md").write_text(
            "---\nmeta:\n  id_go: W-000AAA\n  - [unterminated\n---\n",
            encoding="utf-8",
        )
        # resolve_ref no debe lanzar
        result = resolve_ref("W-000AAA")
        assert result == "W-000AAA"


# ---------------------------------------------------------------------------
# Las TRES intenciones (Fase 1, Task 6) — R7/H7-01
#
# El booleano `strict` metia tres intenciones en dos valores, y por eso el plan
# quedo atrapado eligiendo entre romper el alta y conservar el expediente
# fantasma. Se separan por NOMBRE, que es lo que las hace auditables:
#
#   localizar()       lo que debe existir        -> LANZA si falta
#   buscar()          preguntar si existe        -> devuelve None
#   destino_de_alta() nombrar destino de un alta -> su caso normal es que falte
#
# Esta tanda es ADITIVA a proposito: `path_for` no cambia de comportamiento
# todavia. El default se invierte al final de la migracion, cuando ya no queden
# llamadores apoyados en el fallback — medido: invertirlo hoy rompe 377 tests en
# 42 ficheros, y la causa raiz es que `ensure_case` usa el fallback para CREAR.
# ---------------------------------------------------------------------------


def _arbol(root) -> dict[str, str]:
    """Huella del arbol, para probar que localizar/buscar no crean nada."""
    return {p.relative_to(root).as_posix(): ("d" if p.is_dir() else "f")
            for p in sorted(root.rglob("*"))}


class TestLocalizar:
    def test_caso_flat_existente(self, root):
        from core.casos.case_locator import localizar
        (root / "BaRR3 - Roser").mkdir()
        assert localizar("BaRR3 - Roser") == root / "BaRR3 - Roser"

    def test_caso_en_ciudad(self, root):
        from core.casos.case_locator import localizar
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert localizar("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"

    def test_caso_ausente_LANZA(self, root):
        """El nucleo del criterio de salida (2): no se devuelve una ruta inventada."""
        from core.casos.case_locator import localizar
        from core.casos.workspace_model import LocalWorkspaceMissing
        with pytest.raises(LocalWorkspaceMissing):
            localizar("NO-EXISTE")

    def test_el_error_no_lleva_la_ruta_local(self, root):
        """§16: el mensaje cita W-code y codigo, nunca la ruta."""
        from core.casos.case_locator import localizar
        from core.casos.workspace_model import LocalWorkspaceMissing
        with pytest.raises(LocalWorkspaceMissing) as exc:
            localizar("NO-EXISTE")
        assert str(root) not in str(exc.value)

    def test_no_crea_nada_al_lanzar(self, root):
        from core.casos.case_locator import localizar
        from core.casos.workspace_model import LocalWorkspaceMissing
        antes = _arbol(root)
        with pytest.raises(LocalWorkspaceMissing):
            localizar("NO-EXISTE")
        assert _arbol(root) == antes


class TestBuscar:
    def test_caso_existente_devuelve_la_ruta(self, root):
        from core.casos.case_locator import buscar
        (root / "BaRR3 - Roser").mkdir()
        assert buscar("BaRR3 - Roser") == root / "BaRR3 - Roser"

    def test_caso_en_ciudad(self, root):
        from core.casos.case_locator import buscar
        (root / "Barcelona" / "CASO-X").mkdir(parents=True)
        assert buscar("CASO-X") == root / "Barcelona" / "CASO-X"

    def test_caso_ausente_devuelve_None(self, root):
        """La tercera API: los 27 detectores de ausencia con rama elegante.

        Sin ella, migrarlos a `localizar()` cambiaria un error legible por una
        traza — medido sobre `abrir_caso --case-id` inexistente.
        """
        from core.casos.case_locator import buscar
        assert buscar("NO-EXISTE") is None

    def test_no_crea_nada(self, root):
        from core.casos.case_locator import buscar
        antes = _arbol(root)
        assert buscar("NO-EXISTE") is None
        assert _arbol(root) == antes


class TestDestinoDeAlta:
    def test_caso_nuevo_devuelve_la_ruta_flat(self, root):
        from core.casos.case_locator import destino_de_alta
        assert destino_de_alta("NUEVO") == root / "NUEVO"

    def test_nombrar_no_es_crear(self, root):
        """Devuelve la ruta y NO la materializa: crear es del llamador."""
        from core.casos.case_locator import destino_de_alta
        antes = _arbol(root)
        d = destino_de_alta("NUEVO")
        assert not d.exists()
        assert _arbol(root) == antes

    def test_caso_YA_EXISTENTE_devuelve_SU_ubicacion_no_la_flat(self, root):
        """La regla que impide la carpeta sombra.

        Si `destino_de_alta` devolviera siempre la ruta flat, un alta sobre un
        caso que ya vive en su ciudad crearia un duplicado plano al lado — que es
        exactamente el defecto CRITICO que R6 encontro en el `--force` del
        `--modo v1` (una sombra con el W-code duplicado).
        """
        from core.casos.case_locator import destino_de_alta
        (root / "Barcelona" / "BaRR3 - Roser").mkdir(parents=True)
        assert destino_de_alta("BaRR3 - Roser") == root / "Barcelona" / "BaRR3 - Roser"


class TestLasTresSonCoherentes:
    def test_sobre_un_caso_existente_las_tres_coinciden(self, root):
        from core.casos.case_locator import buscar, destino_de_alta, localizar
        (root / "Barcelona" / "CASO-X").mkdir(parents=True)
        esperada = root / "Barcelona" / "CASO-X"
        assert localizar("CASO-X") == esperada
        assert buscar("CASO-X") == esperada
        assert destino_de_alta("CASO-X") == esperada

    def test_sobre_un_caso_ausente_las_tres_DIFIEREN(self, root):
        """Es el punto entero del cambio: la ausencia deja de tener una sola
        respuesta, porque las tres preguntas eran distintas desde el principio."""
        from core.casos.case_locator import buscar, destino_de_alta, localizar
        from core.casos.workspace_model import LocalWorkspaceMissing
        with pytest.raises(LocalWorkspaceMissing):
            localizar("NO-EXISTE")
        assert buscar("NO-EXISTE") is None
        assert destino_de_alta("NO-EXISTE") == root / "NO-EXISTE"


class TestAditividad:
    def test_path_for_NO_cambia_todavia(self, root):
        """Esta tanda es aditiva: invertir el default hoy rompe 377 tests en 42
        ficheros (medido), y la causa raiz es que `ensure_case` crea por el
        fallback. El default se invierte cuando ya no quede quien se apoye en el."""
        from core.casos.case_locator import path_for
        assert path_for("NO-EXISTE") == root / "NO-EXISTE"

    def test_caso_path_NO_cambia_todavia(self, root):
        from core.config import caso_path
        assert caso_path("NO-EXISTE") == root / "NO-EXISTE"


# ---------------------------------------------------------------------------
# El alta pasa por la puerta explicita (Task 6, paso 2)
# ---------------------------------------------------------------------------

class TestEnsureCasePasaPorLaPuertaExplicita:
    def test_el_alta_de_un_caso_nuevo_sigue_funcionando(self, root):
        """Regresion: invertir la puerta no puede romper crear un caso."""
        from core.case_manager import ensure_case
        ensure_case("BaRS9 - Prueba - (W-TEST99) - Vuelta", tipo_caso="BAD_DEBT")
        assert (root / "BaRS9 - Prueba - (W-TEST99) - Vuelta" / "00_Input").is_dir()

    def test_el_alta_va_por_destino_de_alta_y_no_por_localizar(self, root, monkeypatch):
        """El mutante que el plan exige, fijado como test.

        Si `ensure_case` llamara a `localizar()`, el alta de un caso NUEVO
        lanzaria — que es precisamente el empate del que R7 saco al plan. Se
        comprueba por observacion directa: `destino_de_alta` se invoca.
        """
        from core.casos import case_locator
        vistos: list[str] = []
        real = case_locator.destino_de_alta
        monkeypatch.setattr(case_locator, "destino_de_alta",
                            lambda cid: vistos.append(cid) or real(cid))

        from core.case_manager import ensure_case
        ensure_case("BaRS9 - Prueba - (W-TEST99) - Vuelta", tipo_caso="BAD_DEBT")

        assert vistos == ["BaRS9 - Prueba - (W-TEST99) - Vuelta"], (
            "`ensure_case` no paso por `destino_de_alta`: la puerta de alta "
            "sigue siendo implicita")

    def test_el_alta_sobre_un_caso_que_ya_vive_en_su_ciudad_NO_crea_sombra(self, root):
        """El defecto CRITICO de R6, aqui como regresion del alta.

        Si el alta resolviera a la ruta flat, un caso que ya vive en su ciudad
        recibiria un duplicado plano al lado, con el mismo W-code.
        """
        from core.case_manager import ensure_case
        ciudad = root / "Barcelona" / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
        ciudad.mkdir(parents=True)
        ensure_case("BaRS9 - Prueba - (W-TEST99) - Vuelta", tipo_caso="BAD_DEBT")
        assert (ciudad / "00_Input").is_dir()
        assert not (root / "BaRS9 - Prueba - (W-TEST99) - Vuelta").exists(), (
            "se fabrico una carpeta sombra plana junto al caso real")
