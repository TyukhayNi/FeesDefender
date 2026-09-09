"""I0 e I3: la autoridad viene del resolver, y la raíz se identifica ANTES de juzgar rutas."""
import os
import subprocess

import pytest

from core.casos.workspace_model import Capability
from core.procedimiento import sede


class _WsFalso:
    """Doble mínimo de `CaseWorkspace`: lo que `sede` consume y nada más.

    Se usa un doble y no un `CaseWorkspace` real porque el real DERIVA `capabilities`
    del modo y no las acepta en el constructor — es su garantía, y fabricar un modo
    concreto aquí probaría el resolver, no la sede.
    """

    def __init__(self, working_root, caps=(Capability.READ_CASE,)):
        self.working_root = working_root
        self.capabilities = frozenset(caps)
        self.exigidas = []

    def exigir(self, cap):
        self.exigidas.append(cap)
        if cap not in self.capabilities:
            from core.casos.workspace_model import CapabilityDenied
            # `WorkspaceError.__init__` es SOLO de keywords y el mensaje nunca lleva la
            # ruta local (su §16). Un `CapabilityDenied("texto")` revienta con TypeError.
            raise CapabilityDenied(detalle=f"falta {cap}")


def test_la_raiz_sale_del_workspace_y_EXIGE_read_case(tmp_path):
    ws = _WsFalso(tmp_path)
    r = sede.raiz_autorizada(ws)
    assert r == tmp_path.resolve()
    assert Capability.READ_CASE in ws.exigidas, (
        "la raíz se entregó sin exigir la capacidad: la autorización sería decorativa")


def test_un_workspace_SIN_read_case_no_recibe_raiz(tmp_path):
    ws = _WsFalso(tmp_path, caps=())
    with pytest.raises(sede.SedeError) as exc:
        sede.raiz_autorizada(ws)
    assert "read_case" in str(exc.value).lower()


def test_un_workspace_sin_raiz_de_trabajo_es_SedeError():
    """Los modos bloqueados (`blocked_foreign_checkout`) traen `working_root=None`.
    Devolver `None` haría que el llamador construyera rutas contra la cwd."""
    with pytest.raises(sede.SedeError):
        sede.raiz_autorizada(_WsFalso(None))


def test_contener_construye_desde_la_raiz_y_no_desde_la_ruta(tmp_path):
    (tmp_path / "05_Procedimiento").mkdir()
    p = sede.contener(tmp_path, "05_Procedimiento")
    assert p == (tmp_path / "05_Procedimiento").resolve()


@pytest.mark.parametrize("parte", [
    "..", "../fuera", "05_Procedimiento/../..", "/abs", "C:/otra", r"\\servidor\share",
    # Este último es el que DISTINGUE la guarda léxica de la de contención: resuelve
    # DENTRO de la raíz, así que el `relative_to` final lo aprueba. Medido el 2026-09-09:
    # sin la guarda léxica, los otros seis los caza igualmente la contención o el test de
    # ruta absoluta, así que el mutante que la quita SOBREVIVÍA — y sobrevivió. Se rechaza
    # porque un `..` en medio permite atravesar un componente que el bucle ya aprobó y
    # volver a entrar, y el mapa no tiene por qué poder expresar eso.
    "05_Procedimiento/../05_Procedimiento",
])
def test_contener_rechaza_lo_que_sale_de_la_raiz(tmp_path, parte):
    (tmp_path / "05_Procedimiento").mkdir(exist_ok=True)
    with pytest.raises(sede.SedeError):
        sede.contener(tmp_path, parte)


def test_solo_se_vetan_los_dos_tags_que_REDIRIGEN():
    """**La trampa que haría inservible la pieza.** Un placeholder de Drive Stream (`G:`)
    también lleva `st_reparse_tag`, pero NO redirige la ruta: virtualiza el contenido.
    Vetar «cualquier tag» haría que la vista se negara a leer TODOS los casos reales,
    que es donde viven. Solo se vetan *junction* y *symlink*.
    """
    import stat as _stat
    assert sede.TAGS_QUE_REDIRIGEN == frozenset({
        getattr(_stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
        getattr(_stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
    })
    # un tag de nube no está en el set y por tanto no veta
    assert 0x9000001A not in sede.TAGS_QUE_REDIRIGEN


def test_un_tag_de_NUBE_no_veta_la_ruta(tmp_path, monkeypatch):
    """La consecuencia de la propiedad de arriba, no solo su constante.

    El test del set pasaba igual con `_redirige` mutado a «cualquier tag != 0»: comprobaba
    la lista y no el comportamiento. Aquí se simula el `st_reparse_tag` de un placeholder
    de nube —no se puede crear uno de verdad en `tmp_path`— y se exige que NO vete. Si
    vetara, la vista no podría leer un solo expediente de `G:`.
    """
    import os as _os
    import stat as _stat

    TAG_NUBE = 0x9000001A                     # IO_REPARSE_TAG_CLOUD, familia de Drive/OneDrive
    real = _os.lstat

    class _StatConTag:
        def __init__(self, st):
            self._st = st

        def __getattr__(self, nombre):
            return getattr(self._st, nombre)

        st_reparse_tag = TAG_NUBE

    def lstat_con_nube(p, *a, **k):
        st = real(p, *a, **k)
        return _StatConTag(st) if not _stat.S_ISLNK(st.st_mode) else st

    (tmp_path / "05_Procedimiento").mkdir()
    monkeypatch.setattr(sede.os, "lstat", lstat_con_nube)
    assert sede.contener(tmp_path, "05_Procedimiento").name == "05_Procedimiento"


@pytest.mark.skipif(os.name != "nt", reason="las junctions son de Windows")
def test_una_JUNCTION_en_la_cadena_veta_la_ruta(tmp_path):
    """El defecto que el revisor reprodujo: si `05_Procedimiento` es una junction al
    crudo, una comprobación que resuelva AMBOS lados se aprueba a sí misma."""
    destino = tmp_path / "crudo"
    destino.mkdir()
    enlace = tmp_path / "05_Procedimiento"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(destino)],
                   check=True, capture_output=True)
    with pytest.raises(sede.SedeError) as exc:
        sede.contener(tmp_path, "05_Procedimiento")
    assert "redirige" in str(exc.value).lower()


@pytest.mark.skipif(os.name != "nt", reason="las junctions son de Windows")
def test_una_junction_en_un_ANCESTRO_tambien_veta(tmp_path):
    """`is_symlink()` sobre la hoja no ve un reparse point en un directorio padre."""
    real = tmp_path / "real"
    (real / "05_Procedimiento").mkdir(parents=True)
    enlace = tmp_path / "via"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(real)],
                   check=True, capture_output=True)
    with pytest.raises(sede.SedeError):
        sede.contener(enlace, "05_Procedimiento")
