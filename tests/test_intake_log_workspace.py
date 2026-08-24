"""B0-1: la auditoría escribe donde están los bytes (Fase 1, Task 8).

El plan llama a este task «la tarea más importante», y la razón es concreta: con
`--case-dir` los documentos van a la copia local y el evento de custodia iba a
`CASOS_ROOT`. Custodia partida en dos, y en un expediente probatorio eso no es un
detalle de fontanería.

## Los dos defectos que cierra

**El fantasma.** `append_event` hacía `path.parent.mkdir(parents=True)`, así que
auditar un caso inexistente **fabricaba el expediente entero** —con nombre de W-code,
en la unidad compartida—. Crear un expediente es trabajo de la apertura, no de la
auditoría; ahora lanza `LocalWorkspaceMissing`.

**El split brain.** `append_event(case_id, ...)` resolvía siempre por `CASOS_ROOT`,
así que no había forma de decirle «el evento va aquí, junto a los bytes». Ahora acepta
un `CaseWorkspace` o un `Path` ya resuelto.

## El camino legacy, y por qué ya no es peligroso

Se conserva `append_event("W-XXXX", ...)` para los llamadores que aún no tienen el
`case_dir` — el plan lo contempla expresamente. Lo que cambia es que desde el paso 5
del Task 6 `caso_path` es **estricto**: el camino legacy ya no puede materializar nada,
porque resolver un caso ausente lanza. Sigue siendo `legacy_unresolved` en cuanto a
elegir la copia, pero dejó de ser una fábrica de fantasmas.
"""
from __future__ import annotations

import hashlib
import importlib

import pytest

CASO = "BaRS9 - Prueba - (W-TEST99) - Vuelta"


@pytest.fixture
def root(tmp_path, monkeypatch):
    r = tmp_path / "CASOS"
    r.mkdir()
    monkeypatch.setenv("CASOS_ROOT", str(r))
    from core import config as cfg
    importlib.reload(cfg)
    from core.casos import case_locator
    monkeypatch.setattr(case_locator, "_root", lambda: r)
    yield r


def _huella(raiz) -> dict[str, str]:
    """Huella del árbol: qué hay y con qué contenido. Para probar «cero efectos»."""
    out = {}
    for p in sorted(raiz.rglob("*")):
        rel = p.relative_to(raiz).as_posix()
        out[rel] = ("d" if p.is_dir()
                    else hashlib.sha256(p.read_bytes()).hexdigest()[:16])
    return out


def _arbol(base, nombre=CASO):
    d = base / nombre / "00_Input"
    d.mkdir(parents=True, exist_ok=True)
    return base / nombre


# ==========================================================================
# El fantasma: auditar no crea expedientes
# ==========================================================================

class TestNoFabricaExpedientes:

    def test_append_event_NO_crea_la_raiz_del_caso(self, root, tmp_path):
        """B0-1 en una línea: `mkdir(parents=True)` fabricaba el árbol entero."""
        from core.casos.workspace_model import LocalWorkspaceMissing
        from core.intake_log import append_event
        destino = tmp_path / "caso_que_no_existe"
        with pytest.raises(LocalWorkspaceMissing):
            append_event(destino, "upload_manual", details={}, case_id="W-TEST99")
        assert not destino.exists()

    def test_tampoco_si_falta_solo_00_Input(self, root, tmp_path):
        """Una carpeta suelta no es un expediente: sin `00_Input` no hay dónde auditar."""
        from core.casos.workspace_model import LocalWorkspaceMissing
        from core.intake_log import append_event
        destino = tmp_path / "media-carpeta"
        destino.mkdir()
        antes = _huella(destino)
        with pytest.raises(LocalWorkspaceMissing):
            append_event(destino, "upload_manual", details={}, case_id="W-TEST99")
        assert _huella(destino) == antes

    def test_el_camino_legacy_por_case_id_tampoco_fabrica_nada(self, root):
        """Desde el paso 5 del Task 6, `caso_path` es estricto: no hay fantasma.

        Este era el defecto caro — un `append_event` sobre un W-code mal escrito
        dejaba una carpeta con ese nombre en la unidad COMPARTIDA.
        """
        from core.casos.workspace_model import LocalWorkspaceMissing
        from core.intake_log import append_event
        antes = _huella(root)
        with pytest.raises(LocalWorkspaceMissing) as exc:
            append_event("W-NOEXISTE", "upload_manual", details={})
        assert _huella(root) == antes
        # Y que lo pare `localizar`, no la guarda de `00_Input`. Hay DOS guardas
        # —defensa en profundidad, y esta bien que la haya— pero sin distinguirlas
        # el test pasaba aunque el camino legacy dejara de ser estricto. Solo
        # `localizar` sabe el W-code, asi que su presencia identifica al autor.
        assert "W-NOEXISTE" in str(exc.value)


# ==========================================================================
# El split brain: el evento cae junto a los bytes
# ==========================================================================

class TestElEventoCaeJuntoALosBytes:

    def test_con_un_Path_escribe_ahi_y_NO_en_casos_root(self, root, tmp_path):
        """El corazón del task. Si alguien reintroduce `caso_path` aquí, muere."""
        from core.intake_log import append_event
        _arbol(root)                                   # el canon, como sentinel
        antes = _huella(root)

        scratch = _arbol(tmp_path / "fuera")
        destino = append_event(scratch, "upload_manual", details={},
                               case_id="W-TEST99")

        assert scratch in destino.parents, "el log no cayo junto a los bytes"
        assert destino.read_text(encoding="utf-8").strip()
        assert _huella(root) == antes, "el canon se toco: la custodia sigue partida"

    def test_con_un_CaseWorkspace_usa_su_working_root(self, root, tmp_path):
        """La vía normal: lo que devuelve el resolver se pasa tal cual."""
        from core.casos.workspace_model import (CaseRef, CaseWorkspace,
                                                WorkspaceMode)
        from core.intake_log import append_event
        scratch = _arbol(tmp_path / "fuera")
        ws = CaseWorkspace(
            case_ref=CaseRef(w_code="W-TEST99", case_id=CASO),
            mode=WorkspaceMode.LOCAL_SCRATCH, working_root=scratch,
            canonical_ref=None, checkout_user=None, checkout_maquina=None,
            checkout_nonce=None, checkout_timestamp=None,
            validado_en="2026-08-24T12:00:00Z", procedencia="test")
        destino = append_event(ws, "upload_manual", details={})
        assert scratch in destino.parents

    def test_del_workspace_sale_tambien_el_case_id_del_registro(self, root, tmp_path):
        """El `case_id` del evento sale del workspace: no hay que repetirlo."""
        import json
        from core.casos.workspace_model import (CaseRef, CaseWorkspace,
                                                WorkspaceMode)
        from core.intake_log import append_event
        scratch = _arbol(tmp_path / "fuera")
        ws = CaseWorkspace(
            case_ref=CaseRef(w_code="W-TEST99", case_id=CASO),
            mode=WorkspaceMode.LOCAL_SCRATCH, working_root=scratch,
            canonical_ref=None, checkout_user=None, checkout_maquina=None,
            checkout_nonce=None, checkout_timestamp=None,
            validado_en="2026-08-24T12:00:00Z", procedencia="test")
        destino = append_event(ws, "upload_manual", details={})
        registro = json.loads(destino.read_text(encoding="utf-8").splitlines()[0])
        assert registro["case_id"] == CASO

    def test_el_camino_legacy_sigue_escribiendo_en_el_canon(self, root):
        """Regresión: los llamadores sin `case_dir` siguen funcionando."""
        from core.intake_log import append_event
        caso = _arbol(root)
        destino = append_event(CASO, "upload_manual", details={})
        assert destino == caso / "00_Input" / "_intake_log.jsonl"


# ==========================================================================
# `log_path(case_id)` se retira
# ==========================================================================

class TestLogPathSeRetira:

    def test_log_path_ya_no_existe(self, root):
        """Se RETIRA, no se deprecia (R7/H7-01): dejarlo vivo conserva la via
        que parte la custodia en dos, que es el defecto que este task cierra."""
        import core.intake_log as il
        assert not hasattr(il, "log_path")

    def test_log_path_de_es_la_via_nueva(self, root, tmp_path):
        from core.intake_log import log_path_de
        scratch = _arbol(tmp_path / "fuera")
        assert log_path_de(scratch) == scratch / "00_Input" / "_intake_log.jsonl"

    def test_log_path_de_no_crea_nada(self, root, tmp_path):
        """Sobre un arbol SIN `00_Input`, que es donde se nota.

        Con el arbol ya montado, un `mkdir(exist_ok=True)` dentro de `log_path_de`
        seria un no-op y el test pasaria igual — lo cazo la mutacion.
        """
        from core.intake_log import log_path_de
        pelado = tmp_path / "pelado"
        pelado.mkdir()
        antes = _huella(pelado)
        log_path_de(pelado)
        assert _huella(pelado) == antes, "`log_path_de` creo algo: solo debe computar"
        assert not (pelado / "00_Input").exists()

    def test_read_events_de_lee_lo_que_append_event_escribio(self, root, tmp_path):
        """La simetria del task, contratada.

        Sin ella la migracion queda a medias: se puede escribir junto a los bytes
        pero recuperarlo exige pasar por el catalogo — y con `--case-dir` el
        catalogo NO conoce esa copia, asi que lo recien escrito era ilegible.
        """
        from core.intake_log import append_event, read_events_de
        scratch = _arbol(tmp_path / "fuera")
        append_event(scratch, "upload_manual", details={"n": 1}, case_id="W-TEST99")
        eventos = read_events_de(scratch)
        assert [e["event"] for e in eventos] == ["upload_manual"]
        assert eventos[0]["details"] == {"n": 1}

    def test_read_events_de_de_un_arbol_sin_log_devuelve_vacio(self, root, tmp_path):
        from core.intake_log import read_events_de
        assert read_events_de(_arbol(tmp_path / "fuera")) == []

    def test_read_events_conserva_su_firma(self, root):
        """Es un LECTOR: no fabrica nada, así que no causaba el B0-1. Cambiarle la
        firma tocaría 46 sitios de test para no cerrar ningún defecto."""
        from core.intake_log import read_events
        _arbol(root)
        assert read_events(CASO) == []
        assert read_events("W-NOEXISTE") == []


# ==========================================================================
# El vocabulario: 28 -> 33, con el doble aserto
# ==========================================================================

class TestVocabulario:

    NUEVOS = {"scratch_creado", "scratch_promovido", "checkout_adoptado",
              "conflicto_resuelto", "checkout_cancelado_unilateral"}

    def test_son_treinta_y_tres(self, root):
        from core.intake_log import INTAKE_EVENTS
        assert len(INTAKE_EVENTS) == 33

    def test_los_veintiocho_de_antes_SIGUEN_estando(self, root):
        """El doble aserto que impide cuadrar la cifra por resta (R7/H7-06).

        El plan decia «27 -> 32» con 28 eventos ya en el repo. Un
        `assert len(...) == 32` habria forzado a BORRAR un evento historico para
        cuadrar — y en un log forense retirar vocabulario rompe la lectura de lo
        ya escrito.
        """
        from core.intake_log import INTAKE_EVENTS
        nuevos = set(self.NUEVOS)
        antiguos = set(INTAKE_EVENTS) - nuevos
        assert len(antiguos) == 28
        assert nuevos < set(INTAKE_EVENTS)

    def test_pendiente_checkin_se_conserva(self, root):
        """Lectura historica: su EMISION se retira en la Fase 2, no su nombre."""
        from core.intake_log import INTAKE_EVENTS
        assert "pendiente_checkin" in INTAKE_EVENTS

    def test_un_evento_desconocido_sigue_lanzando(self, root, tmp_path):
        from core.intake_log import append_event
        scratch = _arbol(tmp_path / "fuera")
        with pytest.raises(ValueError):
            append_event(scratch, "evento_inventado", details={})

    @pytest.mark.parametrize("evento", sorted(NUEVOS))
    def test_los_cinco_nuevos_se_pueden_emitir(self, root, tmp_path, evento):
        from core.intake_log import append_event
        scratch = _arbol(tmp_path / "fuera")
        assert append_event(scratch, evento, details={}, case_id="W-TEST99").exists()
