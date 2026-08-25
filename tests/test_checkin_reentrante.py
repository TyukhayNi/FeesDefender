"""Un checkin que no puede cerrar el ciclo no toca nada (`MEJORAS #93-B`, A-2c, R9).

## Los defectos, que son uno

`cmd_checkin` comprobaba la legalidad de la transición de estado **al final** (CP11), o
sea después de inventariar, copiar, verificar, subir evidencia, registrar el evento
forense e integrar la bandeja. De ese único error de sitio salían tres síntomas:

- **`MEJORAS #93-B`** — un **traceback** con todo el trabajo ya bien hecho. Medido en vivo
  el 2026-07-27 sobre `W-02VND1`: `rclone check` dio **0 diferencias / 431 ficheros
  coincidentes**, y aun así hubo que completar CP11 a mano desde Python.
- **A-2c** — un checkin reentrante dejaba **dos** `case_checkin` en el log forense para un
  solo ciclo real. El registro de custodia narraba algo que no ocurrió.
- **R9/H9-02, el que no habíamos visto y es el peor** — la reentrancia se detectaba tan
  tarde que el segundo checkin llegaba a **subir trabajo nuevo al canon sin lock**:
  `plan_merge` clasifica como `COPY_LOCAL` cualquier fichero local que no esté ni en el
  baseline ni en el Drive (caso 7). Después devolvía 0 diciendo «nada que hacer». Una
  copia ya cerrada quedaba convertida de hecho en una vía autorizada de mutar el canon.

## El remedio, y los dos que se descartaron

Se comprueba **al entrar** (CP0-bis), antes de inventariar. Cuesta una operación de
lectura y hace que el aborto sea de verdad «sin efectos».

Se descartó el remedio que proponía `MEJORAS #93-B` —no-op idempotente en CP11, salir en
verde—: arreglaba el traceback y **empeoraba A-2c**, porque el evento ya estaría escrito.
Y se descartó un primer intento propio que validaba a media corrida: cerraba A-2c pero
dejaba viva H9-02 y **ensanchaba** la ventana de sobrescritura del frontmatter (H9-03).

## Los códigos, que no son decorativos

`0` reentrancia (ya cerrado, nada que hacer) · `2` anomalía detectada al entrar —«abortado
sin efectos», que es lo que la tabla del módulo define— · `4` solo si el estado cambia
**durante** la corrida, cuando ya hay trabajo hecho y el lock queda indeterminado.
"""
from __future__ import annotations

import copy

import pytest

from tests._dobles import FakeRclone
from tests.test_repository_cli_checkin import (LOG_PREVIO, args_checkin, caso_md, cli,
                                               eventos_del_log, meta_de, montar_local,
                                               _entorno, _subs)

__all__ = ["cli"]        # la fixture importada, para que pytest la resuelva aquí

#: Subcomandos que siempre mutan el destino remoto.
_SIEMPRE_MUTANTES = ("copy", "moveto", "delete", "rmdirs")


def escrituras_al_drive(fake) -> list[str]:
    """Operaciones que ESCRIBEN en el remote. No basta con mirar el subcomando.

    `copyto` sirve para las dos direcciones en este frontal —el pull del `_caso.md` y del
    log también es un `copyto`—, así que un aserto por nombre de subcomando daría por
    mutante una lectura. Lo que distingue es el **destino**: si empieza por el remote,
    escribe.
    """
    from tests._barrera import REMOTO_SINTETICO
    prefijo = REMOTO_SINTETICO.split(",")[0] + ","
    escrituras = []
    for c in fake.cmds:
        sub, destino = c[1], (c[3] if len(c) > 3 else "")
        if sub in _SIEMPRE_MUTANTES:
            escrituras.append(f"{sub} → {destino}")
        elif sub == "copyto" and str(destino).startswith(prefijo):
            escrituras.append(f"{sub} → {destino}")
    return escrituras


def _drive_prestado() -> dict[str, bytes]:
    return {"00_Input/_caso.md": caso_md("prestado"),
            "00_Input/_intake_log.jsonl": LOG_PREVIO,
            "00_Input/doc.pdf": b"BASE"}


def _local(tmp_path):
    return montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                        base={"00_Input/doc.pdf": b"BASE"})


def _checkins(drive: dict[str, bytes]) -> list[dict]:
    return [e for e in eventos_del_log(drive) if e.get("event") == "case_checkin"]


def _cerrar_una_vez(cli, tmp_path):
    """Primer checkin, verde. Devuelve `(drive, local)` con el ciclo ya cerrado."""
    drive, local = _drive_prestado(), _local(tmp_path)
    fake = FakeRclone(drive, raiz_local=tmp_path)
    rc1 = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))
    if rc1 != 0:
        raise RuntimeError(f"precondición: el primer checkin debía cerrar (rc={rc1})")
    return drive, local


class TestCheckinReentrante:
    """Correrlo dos veces no puede dejar dos ciclos ni mutar el canon."""

    def test_deja_UN_solo_evento_case_checkin(self, cli, tmp_path):
        drive, local = _cerrar_una_vez(cli, tmp_path)
        fake2 = FakeRclone(drive, raiz_local=tmp_path)
        cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake2, tmp_path))
        assert len(_checkins(drive)) == 1, (
            f"el log forense tiene {len(_checkins(drive))} eventos `case_checkin` para "
            f"un solo checkin real (A-2c)")

    def test_sale_con_0_y_sin_traceback(self, cli, tmp_path):
        drive, local = _cerrar_una_vez(cli, tmp_path)
        fake2 = FakeRclone(drive, raiz_local=tmp_path)
        rc2 = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake2, tmp_path))
        assert rc2 == 0, (
            f"un checkin reentrante sobre un caso ya cerrado no es un error: no hay "
            f"nada que hacer y hay que decirlo, no reventar (rc={rc2})")

    def test_el_DRIVE_queda_byte_a_byte_igual(self, cli, tmp_path):
        """R9/H9-07: el test anterior solo miraba que no apareciera la palabra `check`.

        Eso certificaba una propiedad mucho más débil que la que su docstring prometía
        —«ni lock, ni log, ni bandeja»— y dejaba pasar, por ejemplo, la subida de
        evidencia de CP9. Aquí se compara el Drive entero antes y después.
        """
        drive, local = _cerrar_una_vez(cli, tmp_path)
        antes = copy.deepcopy(drive)
        fake2 = FakeRclone(drive, raiz_local=tmp_path)
        cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake2, tmp_path))
        assert drive == antes, (
            f"la segunda pasada mutó el Drive. Nuevas/cambiadas: "
            f"{sorted(set(drive) ^ set(antes)) or [k for k in drive if drive[k] != antes.get(k)]}")

    def test_no_ejecuta_NINGUNA_operacion_mutante(self, cli, tmp_path):
        drive, local = _cerrar_una_vez(cli, tmp_path)
        fake2 = FakeRclone(drive, raiz_local=tmp_path)
        cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake2, tmp_path))
        assert escrituras_al_drive(fake2) == [], (
            f"un aborto «sin efectos» escribió en el Drive: "
            f"{escrituras_al_drive(fake2)} (traza: {_subs(fake2)})")

    def test_TRABAJO_NUEVO_tras_el_cierre_NO_sube_al_canon(self, cli, tmp_path):
        """R9/H9-02, el hallazgo crítico. Este es el test que faltaba.

        Tras cerrar, aparece en la copia local un fichero que no está ni en el baseline
        ni en el Drive. `plan_merge` lo clasifica `COPY_LOCAL`, así que un checkin que
        detectara la reentrancia tarde lo **subiría al canon sin lock** y después
        devolvería 0 diciendo «nada que hacer».
        """
        drive, local = _cerrar_una_vez(cli, tmp_path)
        (local / "00_Input" / "post_cierre.pdf").write_bytes(b"TRABAJO NUEVO SIN LOCK")
        antes = copy.deepcopy(drive)

        fake2 = FakeRclone(drive, raiz_local=tmp_path)
        rc2 = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake2, tmp_path))

        assert "00_Input/post_cierre.pdf" not in drive, (
            "se subió trabajo nuevo al canon SIN lock, sobre un caso ya cerrado")
        assert drive == antes, "el Drive cambió en una pasada que dice no hacer nada"
        assert rc2 == 0 and len(_checkins(drive)) == 1


class TestDisponibleSinMarcaDeCierre:
    """La anomalía: ni prestado, ni cerrado. No es reentrancia y no puede callarse."""

    def _drive_anomalo(self) -> dict[str, bytes]:
        return {"00_Input/_caso.md": caso_md("disponible", checkout_user=None,
                                             checkout_nonce=None),
                "00_Input/_intake_log.jsonl": LOG_PREVIO,
                "00_Input/doc.pdf": b"BASE"}

    def test_sale_con_2_sin_efectos(self, cli, tmp_path):
        """`2` y no `4`: la tabla del módulo define 4 como «lock conservado, estado
        indeterminado, recuperación necesaria», y aquí no hay lock ni indeterminación
        (R9/H9-05)."""
        drive = self._drive_anomalo()
        antes = copy.deepcopy(drive)
        fake = FakeRclone(drive, raiz_local=tmp_path)
        rc_ = cli.cmd_checkin(args_checkin(_local(tmp_path)),
                              entorno=_entorno(cli, fake, tmp_path))
        assert rc_ == 2, f"se esperaba 2 (abortado sin efectos), dio {rc_}"
        assert drive == antes, "abortó «sin efectos» y mutó el Drive"
        assert _checkins(drive) == []

    def test_aborta_ANTES_de_la_primera_ESCRITURA(self, cli, tmp_path):
        """R9/H9-08: fijar CUÁNDO ocurre, no solo el código.

        Sin esto, una implementación que comprobara el estado después de copiar y
        verificar seguiría dando 2 y pasaría el test de arriba.

        El contrato es «antes de la primera escritura», no «antes de todo»: el
        inventario (`lsjson`) y el plan corren primero, porque son lecturas y porque
        comprobar al entrar añadía una operación a **todos** los caminos, incluidos los
        que ya abortaban sin tocar nada. Lo que no puede haber es un `copy`, un `check`
        ni ningún `copyto` cuyo destino sea el remote.
        """
        drive = self._drive_anomalo()
        fake = FakeRclone(drive, raiz_local=tmp_path)
        cli.cmd_checkin(args_checkin(_local(tmp_path)),
                        entorno=_entorno(cli, fake, tmp_path))
        usados = _subs(fake)
        assert "copy" not in usados and "check" not in usados, (
            f"llegó a copiar o verificar antes de comprobar si había ciclo: {usados}")
        assert escrituras_al_drive(fake) == [], f"y escribió: {escrituras_al_drive(fake)}"

    def test_el_mensaje_nombra_la_anomalia(self, cli, tmp_path, capsys):
        drive = self._drive_anomalo()
        fake = FakeRclone(drive, raiz_local=tmp_path)
        cli.cmd_checkin(args_checkin(_local(tmp_path)),
                        entorno=_entorno(cli, fake, tmp_path))
        salida = capsys.readouterr().out.lower()
        assert "no consta prestado" in salida, f"no distingue la anomalía: {salida[-400:]}"
        assert "no se ha tocado nada" in salida, "no dice que abortó sin efectos"


class TestEstadoCorrupto:
    """R9/H9-04: la marca de cierre es histórica y no prueba el estado actual."""

    def test_un_estado_desconocido_con_marca_vieja_NO_es_reentrancia(self, cli, tmp_path):
        drive = {"00_Input/_caso.md": caso_md("corrupto", checkout_user=None,
                                              checkout_nonce=None,
                                              ultimo_checkin_timestamp="2026-01-01T00:00:00Z"),
                 "00_Input/_intake_log.jsonl": LOG_PREVIO,
                 "00_Input/doc.pdf": b"BASE"}
        fake = FakeRclone(drive, raiz_local=tmp_path)
        rc_ = cli.cmd_checkin(args_checkin(_local(tmp_path)),
                              entorno=_entorno(cli, fake, tmp_path))
        assert rc_ == 2, (
            f"un `estado_repositorio` desconocido con una marca de cierre vieja salió "
            f"con {rc_}: está roto, no cerrado")

    def test_un_meta_no_dict_no_revienta(self, cli, tmp_path):
        """`estado_de_fm` tolera un `meta` no-dict; el diagnóstico no puede ser menos
        tolerante, o reaparece el traceback tardío que este cambio retira."""
        from core.utils import build_frontmatter
        roto = (build_frontmatter({"meta": "corrupto"}) + "\n# cuerpo\n").encode("utf-8")
        drive = {"00_Input/_caso.md": roto,
                 "00_Input/_intake_log.jsonl": LOG_PREVIO,
                 "00_Input/doc.pdf": b"BASE"}
        fake = FakeRclone(drive, raiz_local=tmp_path)
        rc_ = cli.cmd_checkin(args_checkin(_local(tmp_path)),
                              entorno=_entorno(cli, fake, tmp_path))
        assert rc_ in (0, 1, 2, 4), f"reventó en vez de diagnosticar (rc={rc_})"


def test_el_camino_verde_sigue_cerrando(cli, tmp_path):
    """Control negativo. Sin él, «no cerrar nunca» pasaría todo lo de arriba."""
    drive, local = _drive_prestado(), _local(tmp_path)
    fake = FakeRclone(drive, raiz_local=tmp_path)
    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))
    assert rc_ == 0
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "disponible"
    assert len(_checkins(drive)) == 1, "el camino verde tiene que registrar SU evento"
    assert drive["00_Input/doc.pdf"] == b"LOCAL", "y subir los bytes del local"
