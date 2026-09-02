"""La verja de tests del cierre distingue «no pude medir» de «medí y salió mal».

**Por qué existe (`MEJORAS #140`, medido el 2026-09-02).** `python -m
scripts.session_close` desde un worktree resuelve al Python del sistema —los
worktrees no tienen `.venv` propio— y ese intérprete no puede importar las
dependencias del proyecto. pytest devolvía **97 errores de colección** (el
primero, `ModuleNotFoundError: No module named 'yaml'`) y `session_close` los
presentaba como **«[X] Tests fallando - commit abortado»**. La suite estaba
verde: con el intérprete del venv, 3.737 recogidos y 0 fallos.

Falla en la dirección segura —rojo falso, no verde falso—, pero manda a
diagnosticar una rotura inexistente y, peor, enseña a ignorar esta verja por
creerla averiada. Es la misma regla que el despacho aplica a la revisión
adversarial: **quien no corre no refuta, deja SIN VERIFICAR.**
"""

from __future__ import annotations

import sys

import pytest

from scripts import session_close as sc


class TestLaSonda:
    """`deps_que_faltan` mide si ESTE intérprete puede importar lo que la suite pide."""

    def test_con_el_interprete_del_venv_no_falta_ninguna(self):
        """Si esta suite está corriendo, sus propias dependencias están.

        Es la mitad que impide que la sonda sea inerte: si devolviera siempre
        una lista no vacía, la verja bloquearía todos los cierres.
        """
        assert sc.deps_que_faltan() == []

    def test_declara_la_que_no_se_puede_importar(self):
        assert sc.deps_que_faltan(("modulo_que_no_existe_jamas",)) == [
            "modulo_que_no_existe_jamas"]

    def test_un_paquete_padre_ausente_cuenta_como_ausente(self):
        """`find_spec` LANZA en vez de devolver None si falta el padre.

        Sin capturar esa excepción la sonda revienta con un traceback en vez de
        declarar la dependencia ausente — y el cierre se cae por la razón
        equivocada.
        """
        assert sc.deps_que_faltan(("modulo_que_no_existe_jamas.hijo",)) == [
            "modulo_que_no_existe_jamas.hijo"]

    def test_mezcla_presentes_y_ausentes_y_solo_devuelve_las_ausentes(self):
        assert sc.deps_que_faltan(("sys", "no_existe_esto", "json")) == ["no_existe_esto"]


class TestLaVerja:
    """Sin dependencias, `main` no mide y lo dice: salida 2, y pytest no corre."""

    @pytest.fixture
    def pytest_espia(self, monkeypatch):
        """Registra los subprocesos de session_close; deja pasar los de git.

        `main` consulta git (`_anon_tocado`) para decidir el modo, así que el
        primer subproceso legítimo NO es pytest. El espía devuelve un resultado
        vacío para git —sin tocar el repo— y **corta con una excepción** en
        cualquier otro, que es la señal de que llegó a lanzar la suite.
        """
        llamadas: list[list[str]] = []

        class _Vacio:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run(cmd, *a, **kw):
            llamadas.append(list(cmd))
            if list(cmd)[:1] == ["git"]:
                return _Vacio()
            raise AssertionError(f"llego a lanzar la suite: {cmd}")

        monkeypatch.setattr(sc.subprocess, "run", _fake_run)
        return llamadas

    def test_sale_con_codigo_2_no_con_1(self, monkeypatch, pytest_espia):
        """2 = no pude medir. 1 = medí y salió mal. Confundirlos es el defecto.

        Si esto pasara a 1, el mensaje sería indistinguible de una suite roja y
        el cierre volvería a mandar a buscar una rotura inexistente.
        """
        monkeypatch.setattr(sc, "deps_que_faltan", lambda *a, **k: ["yaml"])
        with pytest.raises(SystemExit) as exc:
            sc.main()
        assert exc.value.code == 2, (
            f"salió con {exc.value.code}; 1 significaría «tests rojos», que es "
            "justo la confusión que este arreglo elimina")

    def test_no_lanza_NINGUN_subproceso_cuando_no_puede_medir(
            self, monkeypatch, pytest_espia):
        """La verja va antes de TODO: ni pytest, ni la consulta a git del modo.

        Contrato deliberadamente más fuerte que «no invoca pytest»: si no se
        puede medir, no se hace nada en absoluto.
        """
        monkeypatch.setattr(sc, "deps_que_faltan", lambda *a, **k: ["yaml"])
        with pytest.raises(SystemExit):
            sc.main()
        assert pytest_espia == [], (
            f"no debía lanzar nada y lanzó: {pytest_espia}")

    def test_el_mensaje_no_culpa_a_los_tests_y_nombra_el_interprete(
            self, monkeypatch, pytest_espia, capsys):
        """El texto es la mitad útil del arreglo: dice qué pasó y cómo salir."""
        monkeypatch.setattr(sc, "deps_que_faltan", lambda *a, **k: ["yaml", "dotenv"])
        with pytest.raises(SystemExit):
            sc.main()
        salida = capsys.readouterr().out
        assert "NO SE HA MEDIDO NADA" in salida
        assert "yaml" in salida and "dotenv" in salida
        assert sys.executable in salida, "debe nombrar el intérprete culpable"
        assert ".venv" in salida, "debe decir cuál usar"
        assert "Tests fallando" not in salida, (
            "no puede reutilizarse el mensaje que culpa a los tests")

    def test_con_las_dependencias_presentes_la_verja_no_dispara(
            self, monkeypatch, pytest_espia):
        """La otra mitad: con todo instalado, la verja deja pasar y pytest corre.

        Sin este test, una verja que disparase SIEMPRE seguiría en verde en los
        de arriba y bloquearía todos los cierres.
        """
        monkeypatch.setattr(sc, "deps_que_faltan", lambda *a, **k: [])
        with pytest.raises(AssertionError, match="llego a lanzar la suite"):
            sc.main()
        lanzo_pytest = [c for c in pytest_espia if "pytest" in c]
        assert lanzo_pytest, f"no llegó a pytest; solo lanzó: {pytest_espia}"
