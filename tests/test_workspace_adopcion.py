"""Adopción explícita de checkouts anteriores al registro (Fase 1, Task 8b).

El §15 ordena que «los checkouts anteriores sin registro requieren `--case-dir` y una
operación explícita de adopción/verificación». El Task 7 construyó el lado negativo
—checkout propio sin entrada de registro → `LocalWorkspaceMissing`, «no se adopta
solo»— y **nadie construía el positivo**: el único rastro en el plan era el nombre del
evento `checkout_adoptado`. Sin esta pieza, en cuanto el Task 9 migre `sala_maquina`,
un checkout legacy queda **bloqueado sin vía de desbloqueo**: solo el error, no la puerta.

## Por qué la adopción es EXPLÍCITA, y no un arreglo automático

Medido antes de escribir nada: `MERGE_EXCLUSIONS` excluye `_caso.md` del checkout, y el
nonce se escribe **solo en el `_caso.md` del Drive** (`aplicar_lock_prestado(fm_drive,
…)`). Es decir: **el árbol local no lleva ni identidad ni nonce**.

Eso significa que la máquina **no puede probar** que esta carpeta local es la que el lock
vigente designa. Puede comprobar tres cosas —que es un checkout, que el lock del canon es
mío, y que el W-code del nombre casa— y ninguna de las tres es una prueba criptográfica.
La firma humana no es burocracia: es el único eslabón que puede cerrar esa cadena.

Esto se aparta de la letra del plan, que pedía comprobar que «la identidad del árbol
concuerda con `ref`». El árbol **no tiene** fichero de identidad, así que esa comprobación
no existe tal cual; en su lugar se comprueba el nombre y se **declara** lo que no se pudo
verificar.
"""
from __future__ import annotations

import importlib
import json
import textwrap

import pytest

AHORA = "2026-08-25T10:00:00Z"
YO = "nikolai"
ESTA = "ESTA-MAQUINA"
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


def _canon(root, *, estado="prestado", titular=YO, maquina=ESTA, nonce="n1"):
    d = root / CASO / "00_Input"
    d.mkdir(parents=True, exist_ok=True)
    meta = {"id_go": "W-TEST99", "estado_repositorio": estado}
    if titular:
        meta["checkout_user"] = titular
    if maquina:
        meta["checkout_maquina"] = maquina
    if nonce:
        meta["checkout_nonce"] = nonce
    meta["checkout_timestamp"] = AHORA
    cuerpo = "\n".join(f"  {k}: {v}" for k, v in meta.items())
    (d / "_caso.md").write_text(
        textwrap.dedent(f"---\nmeta:\n{cuerpo}\n---\n"), encoding="utf-8")
    return root / CASO


def _checkout_legacy(tmp_path, *, con_manifest=True, nombre=CASO):
    """Una copia local como la deja `repository_cli checkout`: SIN `_caso.md`."""
    local = tmp_path / "Desktop" / nombre
    (local / "00_Input").mkdir(parents=True)
    (local / "00_Input" / "un_doc.pdf").write_bytes(b"contenido")
    if con_manifest:
        (local / "MANIFEST_CHECKOUT.json").write_text(
            json.dumps({"generado": AHORA, "n_ficheros": 1,
                        "inventario": {"00_Input/un_doc.pdf": {"md5": "abc"}}}),
            encoding="utf-8")
    return local


def _registro(tmp_path):
    from core.casos.workspace_registry import WorkspaceRegistry
    return WorkspaceRegistry(tmp_path / "registro", ahora=AHORA)


# ==========================================================================
# `verificar_adopcion` — pura, sin efectos
# ==========================================================================

class TestVerificar:

    def test_un_checkout_legacy_valido_es_adoptable(self, root, tmp_path):
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root)
        local = _checkout_legacy(tmp_path)
        r = verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is True
        assert r.nonce == "n1", "el nonce sale del CANON: en local no existe"

    def test_sin_manifest_NO_es_adoptable(self, root, tmp_path):
        """Sin `MANIFEST_CHECKOUT.json` no hay prueba de que sea un checkout:
        podria ser cualquier carpeta con el nombre parecido."""
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root)
        local = _checkout_legacy(tmp_path, con_manifest=False)
        r = verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is False
        # «falta», no «ilegible»: son DOS guardas distintas y sin separarlas el
        # test pasaba aunque la de existencia desapareciera (lo cazo la mutacion).
        assert "falta" in r.motivo.lower()

    def test_un_manifest_ilegible_NO_es_adoptable(self, root, tmp_path):
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root)
        local = _checkout_legacy(tmp_path)
        (local / "MANIFEST_CHECKOUT.json").write_text("{roto", encoding="utf-8")
        r = verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is False

    @pytest.mark.parametrize("cuerpo", ['[]', '{"otra_cosa": 1}', '"una cadena"'])
    def test_un_manifest_con_JSON_valido_pero_sin_inventario_tampoco(
            self, root, tmp_path, cuerpo):
        """La otra guarda del manifest, aislada.

        Con `{roto` basta el `json.loads` para rechazarlo, asi que el test
        anterior pasaba aunque la comprobacion de FORMA desapareciera. Un JSON
        valido con la forma equivocada solo lo caza esa segunda guarda — y es el
        caso realista: un fichero truncado a la mitad rara vez sigue siendo JSON,
        pero uno de otra version del formato si.
        """
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root)
        local = _checkout_legacy(tmp_path)
        (local / "MANIFEST_CHECKOUT.json").write_text(cuerpo, encoding="utf-8")
        r = verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is False

    def test_un_lock_de_OTRA_maquina_NO_es_adoptable(self, root, tmp_path):
        """La comprobacion que de verdad autoriza: el canon dice que es mio."""
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root, titular="otro", maquina="OTRA")
        local = _checkout_legacy(tmp_path)
        r = verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is False
        assert "otra maquina" in r.motivo.lower() or "titular" in r.motivo.lower()

    def test_un_caso_DISPONIBLE_no_se_adopta(self, root, tmp_path):
        """Sin lock no hay checkout que adoptar: la copia local es un scratch.

        El canon lleva titular y maquina que SI casan, a proposito: con ellos a
        `None` el rechazo lo producia la guarda de propiedad y el test pasaba
        aunque la del estado desapareciera. Asi solo puede pararlo la del estado.
        """
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root, estado="disponible", titular=YO, maquina=ESTA, nonce="n1")
        local = _checkout_legacy(tmp_path)
        r = verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is False

    def test_el_nombre_de_la_carpeta_tiene_que_casar(self, root, tmp_path):
        """Unica senal de identidad disponible en el arbol local, y es debil —
        por eso la firma la pone una persona."""
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root)
        otro = _checkout_legacy(tmp_path, nombre="BaRS9 - Otro - (W-DISTIN) - Vuelta")
        r = verificar_adopcion(otro, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is False

    def test_declara_lo_que_NO_pudo_verificar(self, root, tmp_path):
        """La honestidad de la pieza: el nonce local no existe y hay que decirlo.

        `MERGE_EXCLUSIONS` excluye `_caso.md` del checkout y el nonce se escribe
        solo en el Drive, asi que NADA en el arbol local prueba que esta copia
        corresponda al lock vigente. Si la pieza callara eso, la firma humana
        seria un tramite en vez de una decision informada.
        """
        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root)
        local = _checkout_legacy(tmp_path)
        r = verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                               usuario=YO, maquina=ESTA, ahora=AHORA)
        assert r.ok is True
        assert r.sin_verificar, "no declaro lo que no pudo comprobar"
        assert any("nonce" in s.lower() for s in r.sin_verificar)

    def test_verificar_NO_escribe_nada(self, root, tmp_path):
        """Pieza pura de decision. Ni en el local, ni en el canon, ni en el registro."""
        import hashlib

        def huella(d):
            return {p.relative_to(d).as_posix():
                    ("d" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()[:12])
                    for p in sorted(d.rglob("*"))}

        from core.casos.workspace_adopcion import verificar_adopcion
        from core.casos.workspace_model import CaseRef
        _canon(root)
        local = _checkout_legacy(tmp_path)
        reg = _registro(tmp_path)
        antes = (huella(root), huella(local), len(reg.cargar()))
        verificar_adopcion(local, CaseRef(w_code="W-TEST99"),
                           usuario=YO, maquina=ESTA, ahora=AHORA)
        assert (huella(root), huella(local), len(reg.cargar())) == antes


# ==========================================================================
# `adoptar` — el ÚNICO escritor
# ==========================================================================

class TestAdoptar:

    def test_adoptar_registra_y_desbloquea_la_resolucion(self, root, tmp_path):
        """El punto entero del task: donde antes lanzaba, ahora resuelve."""
        from core.casos.case_catalog import CaseCatalog
        from core.casos.workspace_adopcion import adoptar
        from core.casos.workspace_model import (CaseRef, LocalWorkspaceMissing,
                                                WorkspaceMode)
        from core.casos.workspace_resolver import CaseWorkspaceResolver
        _canon(root)
        local = _checkout_legacy(tmp_path)
        reg = _registro(tmp_path)
        ref = CaseRef(w_code="W-TEST99")

        resolver = CaseWorkspaceResolver(CaseCatalog(), reg, usuario=YO,
                                         maquina=ESTA, ahora=AHORA)
        with pytest.raises(LocalWorkspaceMissing):
            resolver.resolver_por_identidad(ref, drive_accesible=True)

        adoptar(local, ref, registry=reg, usuario=YO, maquina=ESTA, ahora=AHORA)

        ws = resolver.resolver_por_identidad(ref, drive_accesible=True)
        assert ws.mode == WorkspaceMode.LOCAL_CHECKOUT
        assert ws.working_root == local

    def test_adoptar_emite_checkout_adoptado(self, root, tmp_path):
        from core.casos.workspace_adopcion import adoptar
        from core.casos.workspace_model import CaseRef
        from core.intake_log import read_events_de
        _canon(root)
        local = _checkout_legacy(tmp_path)
        adoptar(local, CaseRef(w_code="W-TEST99"), registry=_registro(tmp_path),
                usuario=YO, maquina=ESTA, ahora=AHORA)
        eventos = [e["event"] for e in read_events_de(local)]
        assert "checkout_adoptado" in eventos

    def test_el_evento_cae_en_el_LOCAL_no_en_el_canon(self, root, tmp_path):
        """B0-1 aplicado aqui: se adopta una copia local, el rastro va con ella."""
        from core.casos.workspace_adopcion import adoptar
        from core.casos.workspace_model import CaseRef
        from core.intake_log import read_events_de
        canon = _canon(root)
        local = _checkout_legacy(tmp_path)
        adoptar(local, CaseRef(w_code="W-TEST99"), registry=_registro(tmp_path),
                usuario=YO, maquina=ESTA, ahora=AHORA)
        assert read_events_de(local)
        assert not read_events_de(canon)

    def test_adoptar_NO_corre_si_verificar_dijo_que_no(self, root, tmp_path):
        """`adoptar` no re-decide: si la verificacion falla, no escribe."""
        from core.casos.workspace_adopcion import AdopcionRechazada, adoptar
        from core.casos.workspace_model import CaseRef
        _canon(root, titular="otro", maquina="OTRA")
        local = _checkout_legacy(tmp_path)
        reg = _registro(tmp_path)
        with pytest.raises(AdopcionRechazada):
            adoptar(local, CaseRef(w_code="W-TEST99"), registry=reg,
                    usuario=YO, maquina=ESTA, ahora=AHORA)
        assert reg.cargar() == []

    def test_adoptar_dos_veces_es_idempotente(self, root, tmp_path):
        """Ni duplica la entrada ni duplica el evento."""
        from core.casos.workspace_adopcion import adoptar
        from core.casos.workspace_model import CaseRef
        from core.intake_log import read_events_de
        _canon(root)
        local = _checkout_legacy(tmp_path)
        reg = _registro(tmp_path)
        ref = CaseRef(w_code="W-TEST99")
        adoptar(local, ref, registry=reg, usuario=YO, maquina=ESTA, ahora=AHORA)
        adoptar(local, ref, registry=reg, usuario=YO, maquina=ESTA, ahora=AHORA)
        assert len(reg.buscar(ref)) == 1
        adoptados = [e for e in read_events_de(local)
                     if e["event"] == "checkout_adoptado"]
        assert len(adoptados) == 1

    def test_la_entrada_registrada_lleva_el_nonce_del_CANON(self, root, tmp_path):
        """Adoptar es declarar «esta copia es la que ese lock designa». El nonce
        sale del canon porque en local no hay ninguno."""
        from core.casos.workspace_adopcion import adoptar
        from core.casos.workspace_model import CaseRef
        _canon(root, nonce="nonce-del-canon")
        local = _checkout_legacy(tmp_path)
        reg = _registro(tmp_path)
        ref = CaseRef(w_code="W-TEST99")
        adoptar(local, ref, registry=reg, usuario=YO, maquina=ESTA, ahora=AHORA)
        assert reg.buscar(ref)[0].nonce == "nonce-del-canon"
        assert reg.buscar(ref)[0].tipo == "checkout"


# ==========================================================================
# La puerta humana: `repository_cli adoptar`
# ==========================================================================
#
# El plan es explicito: «NUNCA implicita: adoptar es una decision del abogado
# sobre custodia, no un efecto colateral de correr un motor». De ahi que sea un
# subcomando y no un arreglo automatico dentro del resolver.


class TestSubcomandoAdoptar:

    def test_existe_el_subcomando(self):
        from scripts.repository_cli import build_parser
        args = build_parser().parse_args(["adoptar", "--case-dir", "X"])
        assert args.comando == "adoptar"
        assert args.case_dir == "X"

    def test_exige_case_dir(self):
        """§15: la adopcion pasa por `--case-dir`. Sin ruta no hay que adoptar."""
        from scripts.repository_cli import build_parser
        with pytest.raises(SystemExit):
            build_parser().parse_args(["adoptar"])

    def test_adopta_y_sale_cero(self, root, tmp_path, monkeypatch, capsys):
        from scripts import repository_cli as cli
        _canon(root)
        local = _checkout_legacy(tmp_path)
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: _registro(tmp_path))
        monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA))
        rc = cli.main(["adoptar", "--case-dir", str(local), "--w-code", "W-TEST99"])
        assert rc == 0
        salida = capsys.readouterr().out
        assert "adoptado" in salida.lower()

    def test_MUESTRA_lo_que_no_pudo_verificar(self, root, tmp_path, monkeypatch, capsys):
        """Lo que hace informada la firma. Si esto no se imprime, el subcomando
        pide una decision sin dar los datos para tomarla."""
        from scripts import repository_cli as cli
        _canon(root)
        local = _checkout_legacy(tmp_path)
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: _registro(tmp_path))
        monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA))
        cli.main(["adoptar", "--case-dir", str(local), "--w-code", "W-TEST99"])
        salida = capsys.readouterr().out
        assert "nonce" in salida.lower()

    def test_un_rechazo_sale_UNO_y_explica(self, root, tmp_path, monkeypatch, capsys):
        from scripts import repository_cli as cli
        _canon(root, titular="otro", maquina="OTRA")
        local = _checkout_legacy(tmp_path)
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: _registro(tmp_path))
        monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA))
        rc = cli.main(["adoptar", "--case-dir", str(local), "--w-code", "W-TEST99"])
        assert rc == 1
        assert "otro titular" in capsys.readouterr().out.lower()

    def test_el_rechazo_no_publica_la_ruta_local(self, root, tmp_path, monkeypatch, capsys):
        """§16, tambien en la salida de un CLI."""
        from scripts import repository_cli as cli
        _canon(root, titular="otro", maquina="OTRA")
        local = _checkout_legacy(tmp_path)
        monkeypatch.setattr(cli, "_registro_de_workspaces", lambda ahora: _registro(tmp_path))
        monkeypatch.setattr(cli, "_identidad_actor", lambda: (YO, ESTA))
        cli.main(["adoptar", "--case-dir", str(local), "--w-code", "W-TEST99"])
        assert str(tmp_path) not in capsys.readouterr().out
