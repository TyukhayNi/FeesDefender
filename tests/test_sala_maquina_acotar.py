"""Acotar `apply` por documento: la capacidad que exige D1 (`MEJORAS #90`, PLAN (e)).

Los 17 candidatos del cribado están marcados `ok` en la cobertura del motor viejo y sus
sha ya viven en `_sala_maquina_state.json`: `apply` sin `--force` los salta y `reforzar`
no los recoge (solo mira `low`/`empty`). `--force` sí los procesaría, pero reprocesa el
caso entero (~1 h 40 en W-02VND1) y reescribe MD de documentos que hoy están bien.

El contrato de `--solo` es por tanto «force acotado»: procesa ESOS documentos aunque su
sha ya esté hecho, y **no toca nada más** — ni el MD de los demás, ni su fila de
cobertura, ni su sha en el estado. Los dos últimos son la parte no obvia: reusar la
semántica de `--force` (cobertura previa `[]` + estado autoritativo de la corrida)
borraría la cobertura del resto del caso y vaciaría el estado, con lo que la siguiente
corrida normal reprocesaría el caso entero en silencio.
"""
from __future__ import annotations

import json

import pytest

import scripts.sala_maquina as cli
from core import sala_maquina as sm


def _doc(rel: str, sha: str, *, skip: bool = False) -> sm.DocPlan:
    return sm.DocPlan(rel_path=rel, sha256=sha, ext=".pdf", ruta="pdf",
                      slug=f"{rel.split('/')[-1]}__{sha[:8]}", skip=skip)


def _cob(rel: str, sha: str, *, chars: int, estado: str = "ok") -> sm.DocCobertura:
    return sm.DocCobertura(slug=f"{rel.split('/')[-1]}__{sha[:8]}", rel_path=rel,
                           metodo="pypdf", estado=estado, chars=chars, sha256=sha)


# --- Núcleo puro: acotar_plan -------------------------------------------------

def test_acotar_desmarca_el_skip_del_documento_pedido():
    """El caso de D1: el sha ya está hecho, y aun así hay que reprocesarlo."""
    plan = [_doc("01_Drive EV/cuentas_2024.pdf", "a" * 64, skip=True),
            _doc("01_Drive EV/encargo.pdf", "b" * 64, skip=True)]

    out = sm.acotar_plan(plan, ["01_Drive EV/cuentas_2024.pdf"])

    pedido = [d for d in out if d.rel_path == "01_Drive EV/cuentas_2024.pdf"]
    assert len(pedido) == 1
    assert pedido[0].skip is False


def test_acotar_deja_saltados_los_no_pedidos():
    """Lo que distingue `--solo` de `--force`: el resto NO se reprocesa."""
    plan = [_doc("01_Drive EV/cuentas_2024.pdf", "a" * 64, skip=True),
            _doc("01_Drive EV/encargo.pdf", "b" * 64, skip=False)]

    out = sm.acotar_plan(plan, ["01_Drive EV/cuentas_2024.pdf"])

    otros = [d for d in out if d.rel_path == "01_Drive EV/encargo.pdf"]
    assert otros[0].skip is True, "un documento no pedido no puede entrar en la corrida"


def test_acotar_normaliza_separadores_de_windows():
    """El informe del detector y el shell de Windows escriben `\\`; el plan usa `/`."""
    plan = [_doc("01_Drive EV/cuentas_2024.pdf", "a" * 64, skip=True)]

    out = sm.acotar_plan(plan, ["01_Drive EV\\cuentas_2024.pdf"])

    assert out[0].skip is False


def test_acotar_revienta_si_una_ruta_no_existe_en_el_inventario():
    """Nunca una corrida vacía reportada como éxito (el bug de W-02ZIIF).

    Una errata en una de las 17 rutas tiene que parar la corrida, no producir un
    «0 documentos» que se lee como «ya estaba todo bien».
    """
    plan = [_doc("01_Drive EV/cuentas_2024.pdf", "a" * 64, skip=True)]

    with pytest.raises(ValueError) as exc:
        sm.acotar_plan(plan, ["01_Drive EV/cuentas_2023.pdf"])

    assert "cuentas_2023.pdf" in str(exc.value)


def test_acotar_sin_rutas_devuelve_el_plan_intacto():
    plan = [_doc("a.pdf", "a" * 64, skip=True), _doc("b.pdf", "b" * 64)]

    assert sm.acotar_plan(plan, []) == plan


def test_acotar_desmarca_todos_los_segmentos_de_un_bundle():
    """Un bundle multi-documento comparte `rel_path`: pedirlo trae todos sus segmentos."""
    plan = [_doc("01_Drive EV/bundle.pdf", "a" * 64, skip=True),
            _doc("01_Drive EV/bundle.pdf", "a" * 64, skip=True)]

    out = sm.acotar_plan(plan, ["01_Drive EV/bundle.pdf"])

    assert [d.skip for d in out] == [False, False]


# --- CLI: que el acotado no destruya el estado del resto del caso -------------

@pytest.fixture
def caso(tmp_path, monkeypatch):
    """Caso con DOS documentos ya procesados: cobertura y estado previos en disco."""
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    (case_dir / "00_Input" / "01_Drive EV").mkdir(parents=True)
    (case_dir / "00_Input" / "01_Drive EV" / "cuentas_2024.pdf").write_bytes(b"%PDF-1.4 viejo")
    (case_dir / "00_Input" / "01_Drive EV" / "encargo.pdf").write_bytes(b"%PDF-1.4 encargo")

    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)

    inv = sm.inventariar(case_dir)
    por_rel = {f["rel_path"].replace("\\", "/"): f["sha256"] for f in inv}
    sha_cuentas = por_rel["01_Drive EV/cuentas_2024.pdf"]
    sha_encargo = por_rel["01_Drive EV/encargo.pdf"]

    cli._guardar_estado(case_dir, {sha_cuentas, sha_encargo})
    cli._guardar_cobertura(case_dir, [
        _cob("01_Drive EV/cuentas_2024.pdf", sha_cuentas, chars=10_979),
        _cob("01_Drive EV/encargo.pdf", sha_encargo, chars=8_000),
    ])
    return case_dir, sha_cuentas, sha_encargo


def _estado_en_disco(case_dir) -> set[str]:
    f = sm._sala_maquina_dir(case_dir) / cli._STATE
    return set(json.loads(f.read_text(encoding="utf-8"))["procesados"])


def test_apply_solo_conserva_en_el_estado_el_sha_de_los_no_pedidos(caso, monkeypatch):
    """El defecto caro si `--solo` reusara la semántica de `--force`.

    Con `force`, `procesados = exitosos` (solo los de la corrida). Aplicado a un acotado
    de 1 documento, eso BORRA del estado los otros N-1 → la siguiente corrida normal
    reprocesa el caso entero (~1 h 40 en W-02VND1) sin que nadie lo haya pedido.
    """
    case_dir, sha_cuentas, sha_encargo = caso
    nueva = _cob("01_Drive EV/cuentas_2024.pdf", sha_cuentas, chars=65_076)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [nueva])

    cli.apply("W-TEST99", solo=["01_Drive EV/cuentas_2024.pdf"])

    assert sha_encargo in _estado_en_disco(case_dir), (
        "el acotado vació el estado del documento no pedido")


def test_apply_solo_conserva_la_cobertura_de_los_no_pedidos(caso, monkeypatch):
    """Con `force` la cobertura previa se descarta (`previa = []`): aquí no puede."""
    case_dir, sha_cuentas, sha_encargo = caso
    nueva = _cob("01_Drive EV/cuentas_2024.pdf", sha_cuentas, chars=65_076)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [nueva])

    cli.apply("W-TEST99", solo=["01_Drive EV/cuentas_2024.pdf"])

    cob = {c.rel_path: c for c in cli._cobertura_previa(case_dir)}
    assert "01_Drive EV/encargo.pdf" in cob, "el acotado perdió la fila del no pedido"
    assert cob["01_Drive EV/encargo.pdf"].chars == 8_000


def test_apply_solo_sustituye_la_fila_vieja_del_documento_reprocesado(caso, monkeypatch):
    """La medición de D1 sale de aquí: la fila nueva pisa la vieja, no se duplica."""
    case_dir, sha_cuentas, _ = caso
    nueva = _cob("01_Drive EV/cuentas_2024.pdf", sha_cuentas, chars=65_076)
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [nueva])

    cli.apply("W-TEST99", solo=["01_Drive EV/cuentas_2024.pdf"])

    filas = [c for c in cli._cobertura_previa(case_dir)
             if c.rel_path == "01_Drive EV/cuentas_2024.pdf"]
    assert len(filas) == 1
    assert filas[0].chars == 65_076


def test_apply_solo_manda_a_ejecutar_solo_el_documento_pedido(caso, monkeypatch):
    case_dir, sha_cuentas, _ = caso
    visto: list[list[sm.DocPlan]] = []

    def espia(cd, docs, **k):
        visto.append([d for d in docs if not d.skip])
        return []

    monkeypatch.setattr(cli.sm, "ejecutar", espia)

    cli.apply("W-TEST99", solo=["01_Drive EV/cuentas_2024.pdf"])

    assert [d.rel_path.replace("\\", "/") for d in visto[0]] == [
        "01_Drive EV/cuentas_2024.pdf"]


def test_apply_solo_y_force_juntos_es_error(caso, monkeypatch):
    """Dos formas de forzar con semánticas de estado incompatibles: no se combinan."""
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])

    with pytest.raises(cli.typer.Exit) as exc:
        cli.apply("W-TEST99", force=True, solo=["01_Drive EV/cuentas_2024.pdf"])

    assert exc.value.exit_code != 0


def test_apply_solo_con_ruta_inexistente_aborta_sin_procesar(caso, monkeypatch):
    """La errata para la corrida ANTES de OCR-izar nada."""
    llamado: list[int] = []
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: llamado.append(1) or [])

    with pytest.raises(cli.typer.Exit) as exc:
        cli.apply("W-TEST99", solo=["01_Drive EV/no_existe.pdf"])

    assert exc.value.exit_code != 0
    assert not llamado, "abortó DESPUÉS de arrancar el motor"
