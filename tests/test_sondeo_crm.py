"""Tests del helper de los sondeos de solo lectura (`scripts/_sondeo_crm.py`).

Sin red y sin escribir en el árbol de producción: lo único que toca disco usa `tmp_path`.

Lo que se prueba aquí es **lo que hace las cuentas** y **lo que distingue estados**, que es
donde estos sondeos pueden mentir en silencio:

- `distribucion_copias` cuenta CUENTAS por Message-ID, no filas, y recorta los bordes de la
  muestra (sin eso subestima).
- `filas_mail_por_uid` devuelve `None` cuando no pudo preguntar, que **no** es `[]`.
- `control_positivo` es la línea que separa «medí cero» de «mi instrumento da cero».
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._sondeo_crm import (  # noqa: E402
    _checkout_principal, control_positivo, distribucion_copias, filas_mail_por_uid,
    resolver_env,
)


# ---------------------------------------------------------------------------
# distribucion_copias
# ---------------------------------------------------------------------------

class TestDistribucionCopias:
    def test_cuenta_CUENTAS_no_filas(self):
        """Dos filas de la MISMA cuenta son una sola copia."""
        pares = [("borde-ini", "1"),
                 ("u", "20"), ("u", "20"),
                 ("borde-fin", "1")]
        dist, interior = distribucion_copias(pares)
        assert interior == ["u"]
        assert dist == {1: 1}, "dos filas de la misma cuenta no son dos copias"

    def test_agrupa_las_copias_del_mismo_uid(self):
        pares = [("a", "1"),
                 ("u", "11"), ("u", "13"), ("u", "15"),
                 ("z", "1")]
        dist, interior = distribucion_copias(pares)
        assert interior == ["u"] and dist == {3: 1}

    def test_recorta_los_dos_bordes_de_la_muestra(self):
        """El primero y el último se descartan: sus copias pueden caer fuera."""
        pares = [("primero", "1"), ("medio", "2"), ("ultimo", "3")]
        _, interior = distribucion_copias(pares)
        assert interior == ["medio"], "hay que descartar primero y último, no solo uno"

    def test_no_recorta_cuando_no_hay_interior(self):
        """Con 1 o 2 uids no se recorta: recortar dejaría la muestra vacía."""
        for pares in ([("solo", "1")], [("a", "1"), ("b", "2")]):
            _, interior = distribucion_copias(pares)
            assert len(interior) == len(pares), "con <=2 uids no se recorta nada"

    def test_se_puede_desactivar_el_recorte(self):
        pares = [("a", "1"), ("b", "2"), ("c", "3")]
        _, interior = distribucion_copias(pares, recortar_bordes=False)
        assert interior == ["a", "b", "c"]

    def test_ignora_uid_vacio(self):
        """Las filas cuyo `uid` no es un Message-ID existen (medido: `uid=1908692`) y las
        que vienen vacías no deben contarse como un Message-ID más."""
        pares = [("a", "1"), ("", "9"), ("u", "20"), ("", "9"), ("z", "1")]
        _, interior = distribucion_copias(pares)
        assert "" not in interior and interior == ["u"]

    def test_muestra_vacia_no_estalla(self):
        dist, interior = distribucion_copias([])
        assert interior == [] and dist == {}


# ---------------------------------------------------------------------------
# control_positivo
# ---------------------------------------------------------------------------

class TestControlPositivo:
    def test_falso_si_todo_viene_vacio(self):
        assert control_positivo([set(), set(), {}]) is False

    def test_verdadero_con_un_solo_no_vacio(self):
        assert control_positivo([set(), {("expedientes_judiciales", 683)}]) is True

    def test_falso_sobre_nada_observado(self):
        """Cero observaciones tampoco acredita el instrumento."""
        assert control_positivo([]) is False


# ---------------------------------------------------------------------------
# filas_mail_por_uid — la distinción que no puede colapsar
# ---------------------------------------------------------------------------

class _Respuesta:
    def __init__(self, status: int, payload=None):
        self.status_code = status
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


class _Transporte:
    """Doble de red mínimo. Guarda los params para poder afirmar sobre la petición."""

    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.params = None

    def get(self, ruta, params=None):
        self.ruta, self.params = ruta, params
        return self.respuesta


def _payload(*filas):
    return {"hydra:member": [
        {"id": f["id"], "values": [
            {"property": {"name": k}, "value": v} for k, v in f.items() if k != "id"
        ]} for f in filas
    ]}


class TestFilasMailPorUid:
    def test_no_200_devuelve_None_no_lista_vacia(self):
        """`None` = «no pude preguntar»; `[]` = «no hay». Colapsarlos convierte un fallo de
        lectura en la conclusión tranquilizadora de que el correo no está indexado."""
        t = _Transporte(_Respuesta(500))
        assert filas_mail_por_uid(t, "<a@b>") is None

    def test_200_sin_filas_devuelve_lista_vacia(self):
        t = _Transporte(_Respuesta(200, {"hydra:member": []}))
        assert filas_mail_por_uid(t, "<a@b>") == []

    def test_anade_los_angulos_al_filtrar(self):
        """El CRM guarda el `uid` con `<>`; sin ellos el filtro no casa."""
        t = _Transporte(_Respuesta(200, {"hydra:member": []}))
        filas_mail_por_uid(t, "a@b")
        valores = [v for k, v in t.params if k.endswith("[value]")]
        assert "<a@b>" in valores, f"el filtro fue con {valores}, sin ángulos"

    def test_no_duplica_los_angulos_si_ya_estan(self):
        t = _Transporte(_Respuesta(200, {"hydra:member": []}))
        filas_mail_por_uid(t, "<a@b>")
        valores = [v for k, v in t.params if k.endswith("[value]")]
        assert "<a@b>" in valores and "<<a@b>>" not in valores


# ---------------------------------------------------------------------------
# resolver_env — y que DIGA de dónde cargó
# ---------------------------------------------------------------------------

class TestResolverEnv:
    def test_prefiere_el_env_del_propio_arbol(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text("X=1\n", encoding="utf-8")
        monkeypatch.setattr("scripts._sondeo_crm._checkout_principal", lambda _r: None)
        env = resolver_env(tmp_path)
        assert env.cargado == tmp_path / ".env"

    def test_cae_al_checkout_principal_cuando_el_worktree_no_tiene(self, tmp_path, monkeypatch):
        """El caso real: un worktree no tiene `.env` porque está gitignored."""
        worktree, principal = tmp_path / "wt", tmp_path / "main"
        worktree.mkdir(); principal.mkdir()
        (principal / ".env").write_text("X=1\n", encoding="utf-8")
        monkeypatch.setattr("scripts._sondeo_crm._checkout_principal", lambda _r: principal)
        env = resolver_env(worktree)
        assert env.cargado == principal / ".env"

    def test_sin_ninguno_dice_donde_busco(self, tmp_path, monkeypatch):
        """Un cargador que no dice dónde miró no distingue «no había» de «no pude mirar»."""
        worktree, principal = tmp_path / "wt", tmp_path / "main"
        worktree.mkdir(); principal.mkdir()
        monkeypatch.setattr("scripts._sondeo_crm._checkout_principal", lambda _r: principal)
        env = resolver_env(worktree)
        assert env.cargado is None
        assert str(worktree) in env.descripcion and str(principal) in env.descripcion

    def test_la_descripcion_del_exito_nombra_la_ruta(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text("X=1\n", encoding="utf-8")
        monkeypatch.setattr("scripts._sondeo_crm._checkout_principal", lambda _r: None)
        assert str(tmp_path) in resolver_env(tmp_path).descripcion


# ---------------------------------------------------------------------------
# _checkout_principal — lo que de verdad arregla el problema del worktree
# ---------------------------------------------------------------------------

class _Salida:
    def __init__(self, returncode=0, stdout=""):
        self.returncode, self.stdout = returncode, stdout


class TestCheckoutPrincipal:
    """Los tests de `resolver_env` sustituyen esta función, así que sin estos no la
    cubriría nada: estaría probando el arreglo del worktree con el arreglo apagado."""

    def _falso_git(self, monkeypatch, salida):
        monkeypatch.setattr("scripts._sondeo_crm.subprocess.run",
                            lambda *a, **k: salida)

    def test_devuelve_el_primer_arbol_del_listado(self, monkeypatch, tmp_path):
        principal = tmp_path / "main"
        self._falso_git(monkeypatch, _Salida(
            0, f"worktree {principal}\nHEAD abc\nbranch refs/heads/main\n\n"
               f"worktree {tmp_path / 'wt'}\nHEAD def\n"))
        assert _checkout_principal(tmp_path / "wt") == principal

    def test_None_si_este_arbol_YA_es_el_principal(self, monkeypatch, tmp_path):
        """Si no, se cargaría dos veces el mismo `.env` y el mensaje mentiría."""
        self._falso_git(monkeypatch, _Salida(0, f"worktree {tmp_path}\nHEAD abc\n"))
        assert _checkout_principal(tmp_path) is None

    def test_None_si_git_falla(self, monkeypatch, tmp_path):
        self._falso_git(monkeypatch, _Salida(128, ""))
        assert _checkout_principal(tmp_path) is None

    def test_None_si_el_listado_no_empieza_por_worktree(self, monkeypatch, tmp_path):
        self._falso_git(monkeypatch, _Salida(0, "basura\n"))
        assert _checkout_principal(tmp_path) is None

    def test_None_si_el_listado_viene_vacio(self, monkeypatch, tmp_path):
        self._falso_git(monkeypatch, _Salida(0, ""))
        assert _checkout_principal(tmp_path) is None

    def test_None_si_git_no_esta(self, monkeypatch, tmp_path):
        """`OSError` es el caso de «no hay git en el PATH», y no debe propagarse: un
        sondeo tiene que poder decir «no encontré .env», no estallar."""
        def estalla(*a, **k):
            raise OSError("no such file: git")
        monkeypatch.setattr("scripts._sondeo_crm.subprocess.run", estalla)
        assert _checkout_principal(tmp_path) is None

    def test_None_si_la_ruta_del_listado_no_se_puede_resolver(self, monkeypatch, tmp_path):
        """`Path.resolve` puede lanzar `OSError` (ruta inválida, unidad ausente). Tampoco
        se propaga: se degrada a «no hay principal»."""
        self._falso_git(monkeypatch, _Salida(0, "worktree Z:\\\\no\\\\existe\nHEAD abc\n"))
        real = Path.resolve

        def resolve_que_estalla(self, *a, **k):
            raise OSError("unidad no disponible")

        monkeypatch.setattr(Path, "resolve", resolve_que_estalla)
        try:
            assert _checkout_principal(tmp_path) is None
        finally:
            monkeypatch.setattr(Path, "resolve", real)


# ---------------------------------------------------------------------------
# cliente_rest — que cierre, incluso si el cuerpo estalla
# ---------------------------------------------------------------------------

class TestClienteRest:
    def _instalar_falso(self, monkeypatch, registro):
        """Sustituye `SudespachoClient` en su módulo: `cliente_rest` lo importa dentro."""
        import core.sync_sudespacho as ss

        class FalsoCliente:
            def __init__(self):
                self._client = "cliente-httpx"

            def __exit__(self, *a):
                registro.append("cerrado")

        monkeypatch.setattr(ss, "SudespachoClient", FalsoCliente)

    def test_cede_el_cliente_interno_y_cierra(self, monkeypatch):
        from scripts._sondeo_crm import cliente_rest

        registro: list[str] = []
        self._instalar_falso(monkeypatch, registro)
        with cliente_rest() as t:
            assert t == "cliente-httpx"
        assert registro == ["cerrado"]

    def test_cierra_aunque_el_cuerpo_estalle(self, monkeypatch):
        """Sin esto, un sondeo que falla a mitad deja la conexión abierta."""
        from scripts._sondeo_crm import cliente_rest

        registro: list[str] = []
        self._instalar_falso(monkeypatch, registro)
        with pytest.raises(RuntimeError):
            with cliente_rest():
                raise RuntimeError("fallo a mitad del sondeo")
        assert registro == ["cerrado"], "el cliente tiene que cerrarse en el camino infeliz"


# ---------------------------------------------------------------------------
# Guarda: los sondeos son de SOLO LECTURA
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("modulo", ["sondeo_copias_mail", "sondeo_join_gmail_crm"])
def test_los_sondeos_no_contienen_ninguna_escritura(modulo):
    """Ningún `.post`, `.put`, `.delete` ni `.patch` en el fuente de los sondeos.

    Es un guard de forma, no de comportamiento: no prueba que no escriban, prueba que
    nadie ha metido una escritura sin darse cuenta. Si algún día un sondeo necesita
    escribir, deja de ser un sondeo y este test debe ponerse rojo para forzar la
    conversación.
    """
    fuente = (ROOT / "scripts" / f"{modulo}.py").read_text(encoding="utf-8")
    prohibidos = [v for v in (".post(", ".put(", ".delete(", ".patch(") if v in fuente]
    assert not prohibidos, f"{modulo} contiene {prohibidos}: los sondeos son de solo lectura"
