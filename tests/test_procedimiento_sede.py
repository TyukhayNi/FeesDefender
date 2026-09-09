"""I0 e I3: la autoridad viene del resolver, y la raíz se identifica ANTES de juzgar rutas."""
import os
import pathlib
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


def test_los_dos_tags_conocidos_por_su_nombre_siguen_siendo_esos_dos():
    """**La trampa que haría inservible la pieza.** Un placeholder de Drive Stream (`G:`)
    también lleva `st_reparse_tag`, pero NO redirige la ruta: virtualiza el contenido.
    Vetar «cualquier tag» haría que la vista se negara a leer TODOS los casos reales.

    Esta lista son los dos que además se conocen por su nombre. **No son los únicos que
    vetan**, y decir lo contrario era el defecto que la R1 señaló (su H-08): la política
    real es el bit *Name Surrogate*, que es la propiedad —«este reparse point nombra otra
    entidad»— y no una enumeración. Lo comprueba
    `test_un_tag_con_el_bit_NAME_SURROGATE_veta_aunque_no_este_en_la_lista`.
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


# ------------------------------------------------------------- R1/H-07 y H-08

def test_raiz_autorizada_comprueba_la_cadena_ANTES_de_resolver(tmp_path, monkeypatch):
    """R1/H-07: el test del ancestro llamaba a `contener(enlace, ...)` directamente,
    mientras la secuencia de produccion `contener(raiz_autorizada(ws), ...)` ya habia
    borrado el enlace con `resolve()`. La comprobacion tiene que estar donde la ruta
    entra por primera vez."""
    real = tmp_path / "real"
    real.mkdir()
    llamadas = []
    original = sede._cadena_limpia

    def espia(p):
        llamadas.append(str(p))
        return original(p)

    monkeypatch.setattr(sede, "_cadena_limpia", espia)
    sede.raiz_autorizada(_WsFalso(real))
    assert llamadas, "`raiz_autorizada` no comprobo la cadena"


@pytest.mark.skipif(os.name != "nt", reason="las junctions son de Windows")
def test_raiz_autorizada_RECHAZA_una_raiz_alcanzada_por_junction(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    enlace = tmp_path / "via"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(enlace), str(real)],
                   check=True, capture_output=True)
    with pytest.raises(sede.SedeError) as exc:
        sede.raiz_autorizada(_WsFalso(enlace))
    assert "redirige" in str(exc.value).lower()


def test_un_tag_con_el_bit_NAME_SURROGATE_veta_aunque_no_este_en_la_lista(tmp_path,
                                                                         monkeypatch):
    """R1/H-08: «solo dos tags redirigen» era una enumeracion, no una clasificacion. El
    bit Name Surrogate es la propiedad que importa — significa que el reparse point nombra
    OTRA entidad — y un tag no enumerado no queda probado inocuo."""
    import stat as _stat
    TAG_RARO = 0xA000001D          # no esta en la lista, pero lleva el bit puesto
    assert TAG_RARO not in sede.TAGS_QUE_REDIRIGEN
    assert TAG_RARO & 0x20000000

    real = os.lstat

    class _Con:
        st_reparse_tag = TAG_RARO

        def __init__(self, st):
            self._st = st

        def __getattr__(self, n):
            return getattr(self._st, n)

    (tmp_path / "05_Procedimiento").mkdir()
    monkeypatch.setattr(sede.os, "lstat",
                        lambda p, *a, **k: _Con(real(p, *a, **k))
                        if not _stat.S_ISLNK(real(p, *a, **k).st_mode) else real(p))
    with pytest.raises(sede.SedeError):
        sede.contener(tmp_path, "05_Procedimiento")


def test_un_lstat_que_falla_por_PERMISOS_no_es_no_redirige(tmp_path, monkeypatch):
    """«No lo se» no es «no redirige». Antes cualquier OSError se tragaba como inocuo."""
    (tmp_path / "05_Procedimiento").mkdir()

    def lstat_roto(p, *a, **k):
        raise PermissionError(13, "Acceso denegado")

    monkeypatch.setattr(sede.os, "lstat", lstat_roto)
    with pytest.raises(sede.SedeError) as exc:
        sede.contener(tmp_path, "05_Procedimiento")
    assert "no lo sé" in str(exc.value).lower() or "no se pudo" in str(exc.value).lower()


def test_un_fichero_que_NO_existe_si_es_no_redirige(tmp_path):
    """El otro valor del instrumento: la ausencia no puede confundirse con el fallo."""
    p = sede.contener(tmp_path, "todavia_no_existe")
    assert p.name == "todavia_no_existe"


def test_agotar_la_cota_de_ancestros_falla_CERRADO(monkeypatch):
    """Una cadena que no se pudo recorrer entera no esta limpia, solo sin comprobar.
    Devolver True ahi era la tercera apertura silenciosa de H-08."""
    monkeypatch.setattr(sede, "_MAX_ANCESTROS", 1)
    monkeypatch.setattr(sede, "_redirige", lambda p: False)
    # una ruta con mas de un ancestro no cabe en la cota
    assert sede._cadena_limpia(pathlib.Path("C:/a/b/c")) is False


# ----------------------------------------------------------------- R1/H-05

def test_un_registro_de_workspaces_CORRUPTO_se_detecta_SIN_renombrarlo(tmp_path):
    """R1/H-05: `WorkspaceRegistry._leer` pone en cuarentena —renombra con `os.replace`—
    un JSON ilegible antes de lanzar. Para su modulo es correcto: preserva la evidencia.
    Pero significa que una LECTURA de esta mitad provoca una ESCRITURA, y esta mitad no
    escribe. Se mira antes, y el fichero tiene que quedar donde estaba."""
    (tmp_path / "W-SONDA.json").write_text("{{{ no soy json", encoding="utf-8")
    antes = sorted(p.name for p in tmp_path.iterdir())
    with pytest.raises(sede.SedeError) as exc:
        sede.registro_legible(tmp_path)
    assert "W-SONDA.json" in str(exc.value)
    assert sorted(p.name for p in tmp_path.iterdir()) == antes, (
        "el preflight movio el fichero: es justo lo que existe para evitar")
    assert not any(".corrupto." in p.name for p in tmp_path.iterdir())


def test_un_registro_con_forma_inesperada_tambien_se_detecta(tmp_path):
    """`_leer` tambien pone en cuarentena un JSON valido que no sea una lista."""
    (tmp_path / "W-SONDA.json").write_text('{"no": "soy una lista"}', encoding="utf-8")
    with pytest.raises(sede.SedeError) as exc:
        sede.registro_legible(tmp_path)
    assert "lista" in str(exc.value)


def test_un_registro_sano_pasa_y_los_lockfiles_no_estorban(tmp_path):
    """Solo `*.json`: los lockfiles de D2 viven en la misma raiz y no son entradas."""
    (tmp_path / "W-BUENO.json").write_text("[]", encoding="utf-8")
    (tmp_path / "W-BUENO.lock").write_text("no soy json y da igual", encoding="utf-8")
    sede.registro_legible(tmp_path)          # no lanza


def test_una_raiz_de_registro_que_no_existe_no_es_un_error(tmp_path):
    """Nunca haber prestado un caso es legitimo."""
    sede.registro_legible(tmp_path / "no_existe")
