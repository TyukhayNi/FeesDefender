"""Un checkin que no puede cerrar el ciclo no registra que lo cerró (`MEJORAS #93-B`, A-2c).

## Los dos defectos, que son uno

`cmd_checkin` registra el evento forense `case_checkin` **antes** de comprobar si la
transición de estado es legal. Cuando no lo es, CP11 revienta con `TransicionInvalida`
después de haber subido, verificado, registrado el evento e integrado la bandeja. De ahí
salen dos síntomas que parecían independientes:

- **A-2c** — un checkin reentrante deja **dos** `case_checkin` en el log forense para un
  solo checkin real. El registro de custodia narra un ciclo que no ocurrió.
- **`MEJORAS #93-B`** — el usuario recibe un **traceback** después de que todo el trabajo
  haya salido bien. Medido en vivo el 2026-07-27 sobre `W-02VND1`: `rclone check` dio
  **0 diferencias / 431 ficheros coincidentes** y el evento quedó escrito con
  `resultado=verde`; el checkin **había funcionado**, y aun así hubo que completar CP11 a
  mano invocando `aplicar_lock_liberado` + `_push_caso_md` desde Python.

## Por qué el remedio no es el que proponía la entrada de MEJORAS

`#93-B` pedía tratar `disponible → disponible` como un no-op idempotente **en CP11** y
salir en VERDE. Eso arregla el traceback y **empeora A-2c**: el evento ya se registró, así
que el segundo checkin pasaría de morir ruidosamente a duplicar la traza en silencio. El
orden es el defecto, no la excepción.

Aquí la transición se valida **antes** del evento y antes de la bandeja: si el ciclo no se
puede cerrar, no se registra nada y no se toca nada.

## Y las dos salidas no son la misma cosa

Un `disponible` con marca de checkin previo es **reentrancia**: no hay nada que hacer y se
dice así, en verde. Un `disponible` **sin** esa marca es una anomalía —el lock nunca se
escribió (`#93-A`) o alguien lo liberó por fuera— y ahí el silencio sería peor que el
traceback: sale con 4 y lo nombra. Colapsar las dos en «verde» convertiría la comprobación
en decoración.
"""
from __future__ import annotations

import pytest

from tests._dobles import FakeRclone
from tests.test_repository_cli_checkin import (LOG_PREVIO, args_checkin, caso_md, cli,
                                               eventos_del_log, meta_de, montar_local,
                                               _entorno, _subs)

__all__ = ["cli"]        # la fixture importada, para que pytest la resuelva aquí


def _drive_prestado() -> dict[str, bytes]:
    return {"00_Input/_caso.md": caso_md("prestado"),
            "00_Input/_intake_log.jsonl": LOG_PREVIO,
            "00_Input/doc.pdf": b"BASE"}


def _local(tmp_path):
    return montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                        base={"00_Input/doc.pdf": b"BASE"})


def _checkins(drive: dict[str, bytes]) -> list[dict]:
    return [e for e in eventos_del_log(drive) if e.get("event") == "case_checkin"]


class TestCheckinReentrante:
    """Correrlo dos veces no puede dejar dos ciclos en el registro de custodia."""

    def _dos_veces(self, cli, tmp_path):
        drive, local = _drive_prestado(), _local(tmp_path)
        fake1 = FakeRclone(drive, raiz_local=tmp_path)
        rc1 = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake1, tmp_path))
        if rc1 != 0:
            raise RuntimeError(f"precondición: el primer checkin debía cerrar (rc={rc1})")
        fake2 = FakeRclone(drive, raiz_local=tmp_path)
        rc2 = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake2, tmp_path))
        return drive, rc1, rc2, fake2

    def test_deja_UN_solo_evento_case_checkin(self, cli, tmp_path):
        drive, _rc1, _rc2, _fake = self._dos_veces(cli, tmp_path)
        assert len(_checkins(drive)) == 1, (
            f"el log forense tiene {len(_checkins(drive))} eventos `case_checkin` para "
            f"un solo checkin real (A-2c)")

    def test_no_revienta_con_traceback(self, cli, tmp_path):
        """`#93-B`: el segundo checkin termina, no explota."""
        _drive, _rc1, rc2, _fake = self._dos_veces(cli, tmp_path)
        assert rc2 == 0, (
            f"un checkin reentrante sobre un caso ya cerrado no es un error: "
            f"no hay nada que hacer y hay que decirlo, no reventar (rc={rc2})")

    def test_lo_dice_en_castellano(self, cli, tmp_path, capsys):
        self._dos_veces(cli, tmp_path)
        salida = capsys.readouterr().out
        assert "ya" in salida.lower() and "cerrad" in salida.lower(), (
            f"el mensaje no dice que el ciclo ya estaba cerrado:\n{salida[-400:]}")

    def test_no_toca_el_drive_en_la_segunda_pasada(self, cli, tmp_path):
        """Nada que cerrar es nada que escribir: ni lock, ni log, ni bandeja."""
        drive, _rc1, _rc2, fake2 = self._dos_veces(cli, tmp_path)
        assert "check" not in _subs(fake2), (
            f"la segunda pasada volvió a verificar y subir: {_subs(fake2)}")
        meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
        assert meta["estado_repositorio"] == "disponible"


class TestDisponibleSinMarcaDeCheckin:
    """La anomalía: el Drive no lo da por prestado y tampoco consta cerrado.

    Es el escenario real de `#93-B` —el checkout no llegó a escribir el lock (`#93-A`)—
    y no se puede tratar como reentrancia: nadie cerró nada, así que callar sería peor
    que el traceback que este arreglo retira.
    """

    def test_sale_con_4_y_sin_registrar_el_evento(self, cli, tmp_path):
        drive = {"00_Input/_caso.md": caso_md("disponible", checkout_user=None,
                                              checkout_nonce=None),
                 "00_Input/_intake_log.jsonl": LOG_PREVIO,
                 "00_Input/doc.pdf": b"BASE"}
        fake = FakeRclone(drive, raiz_local=tmp_path)
        rc_ = cli.cmd_checkin(args_checkin(_local(tmp_path)),
                              entorno=_entorno(cli, fake, tmp_path))
        assert rc_ == 4, f"se esperaba 4 (ciclo no cerrable), dio {rc_}"
        assert _checkins(drive) == [], (
            "registró un `case_checkin` de un ciclo que no pudo cerrar")

    def test_el_mensaje_nombra_la_anomalia(self, cli, tmp_path, capsys):
        drive = {"00_Input/_caso.md": caso_md("disponible", checkout_user=None,
                                              checkout_nonce=None),
                 "00_Input/_intake_log.jsonl": LOG_PREVIO,
                 "00_Input/doc.pdf": b"BASE"}
        fake = FakeRclone(drive, raiz_local=tmp_path)
        cli.cmd_checkin(args_checkin(_local(tmp_path)),
                        entorno=_entorno(cli, fake, tmp_path))
        salida = capsys.readouterr().out
        assert "no consta prestado" in salida.lower(), (
            f"el mensaje no distingue la anomalía de la reentrancia:\n{salida[-400:]}")


def test_el_camino_verde_sigue_cerrando(cli, tmp_path):
    """Control negativo. Sin él, «no cerrar nunca» pasaría todo lo de arriba."""
    drive, local = _drive_prestado(), _local(tmp_path)
    fake = FakeRclone(drive, raiz_local=tmp_path)
    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))
    assert rc_ == 0
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "disponible"
    assert len(_checkins(drive)) == 1, "el camino verde tiene que registrar SU evento"
