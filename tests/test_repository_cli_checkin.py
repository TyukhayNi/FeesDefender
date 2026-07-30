"""Task 4 de la Fase 0: caracterización de `cmd_checkin`. Fija lo que HACE HOY.

**Red de seguridad, no especificación.** Se escribió ANTES de enhebrar el `Entorno`
(Task 1B) y con el frontal sin tocar, inyectando por `monkeypatch` de módulo. **La
Task 1B migró el montaje a `entorno=` inyectado y ni un solo aserto cambió**: lo único
que se tocó dentro de un `assert` fue la línea de llamada (`cmd_checkin(args,
entorno=…)`), no el valor comparado. Ese es el resultado que hacía de esta red la
condición para permitirse el refactor.

`cmd_checkin` no duerme ni usa nonce —eso es del checkout—, así que el `Entorno` de
prueba solo necesita fijar aquí el `work_dir` y el `usuario`.

Este es el camino que decide **pérdida de datos**: propaga borrados moviendo al
`--backup-dir`, veta grupos indivisibles, integra la bandeja del guard de escritura y
clasifica el semáforo. De ahí que casi todos los asertos vengan en pares —código de
salida **y** estado del Drive—: un código correcto sobre un Drive mutado de más sería
exactamente el fallo que esta red existe para cazar.

**Si algo de aquí falla, es un bug vivo que no conocíamos: para y repórtalo.** No se
arregla nada en la Fase 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest

from tests._barrera import REMOTO_SINTETICO as REMOTO
from tests._dobles import FakeRclone

CASO_MD_CUERPO = "# Caso W-TEST99\n\nDatos canónicos que NO se deben perder.\n"
CASE_ID = "BaRS9 - Prueba - (W-TEST99) - Vuelta"

#: Un evento previo en el log del Drive: así se comprueba que el `case_checkin` se
#: **añade** y no reemplaza el historial (defecto 2 de #156).
LOG_PREVIO = b'{"event":"upload_manual"}\n'

#: Miembros del único grupo indivisible de `GRUPOS_MERGE` (N6). Se nombran aquí porque
#: el veto solo se puede provocar con rutas de un grupo real.
MAPA = "05_Procedimiento/_mapa_procesal.yaml"
OCURRENCIAS = "00_Input/_ocurrencias_crm.json"


# ---------------------------------------------------------------------------
# Montaje (helpers LOCALES: el plan no quiere un módulo compartido todavía)
# ---------------------------------------------------------------------------

def caso_md(estado: str = "prestado", **lock) -> bytes:
    from core.utils import build_frontmatter
    meta = {"id_go": "W-TEST99", "tipo_caso": "VUELTA", "ciudad": "Barcelona",
            "estado_repositorio": estado, "checkout_user": "tester",
            "checkout_nonce": "abcdef0123456789"}
    meta.update(lock)
    return (build_frontmatter({"meta": meta}) + "\n" + CASO_MD_CUERPO).encode("utf-8")


def meta_de(data: bytes, tmp_path: Path) -> dict:
    from core.utils import read_md
    p = tmp_path / "_leido.md"
    p.write_bytes(data)
    fm, _ = read_md(p)
    return (fm or {}).get("meta") or {}


def drive_de(contenido: dict[str, bytes], *, estado: str = "prestado") -> dict[str, bytes]:
    """Drive del caso: el protocolo (lock tomado + log con historia) y el contenido."""
    drive = {"00_Input/_caso.md": caso_md(estado),
             "00_Input/_intake_log.jsonl": LOG_PREVIO}
    drive.update(contenido)
    return drive


def montar_local(tmp_path: Path, contenido: dict[str, bytes], *,
                 base: dict[str, bytes] | None) -> Path:
    """Árbol local del caso más el `MANIFEST_CHECKOUT.json` con el baseline B.

    `base=None` monta un checkin **sin** manifest: `_leer_manifest` devuelve `{}` y el
    merge degrada a 2 vías. `base={}` es distinto en intención pero equivalente en
    efecto, y por eso se pasa siempre explícito.
    """
    raiz = tmp_path / "local"
    raiz.mkdir(parents=True, exist_ok=True)
    for rel, data in contenido.items():
        p = raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    if base is not None:
        inv = {rel: {"hash": hashlib.md5(d).hexdigest(), "size": len(d)}
               for rel, d in base.items()}
        (raiz / "MANIFEST_CHECKOUT.json").write_text(
            json.dumps({"generado": "2026-07-29T10:00:00Z",
                        "n_ficheros": len(inv), "inventario": inv}),
            encoding="utf-8")
    return raiz


@pytest.fixture
def cli(tmp_path):
    """El frontal, con su directorio de trabajo ya creado.

    Desde la Task 1B **ya no hay `monkeypatch` de módulo**: la inyección entra por el
    puerto `entorno=` (ver `_entorno`). El work_dir sigue siendo `tmp_path / "work"`
    a propósito, para que los asertos que lo nombran no cambien de valor: lo que
    cambia es el montaje, no lo que se comprueba.
    """
    from scripts import repository_cli
    (tmp_path / "work").mkdir(exist_ok=True)
    return repository_cli


def _entorno(cli, fake, tmp_path):
    """`Entorno` determinista con el doble dentro. `usuario` fija el actor por defecto."""
    from tests._dobles import entorno_de_prueba
    return entorno_de_prueba(cli, fake, work_dir=tmp_path / "work", usuario="tester")


def args_checkin(local: Path, **kw) -> argparse.Namespace:
    base = dict(case_id=CASE_ID, local=str(local), remote_path="", folder_id=None,
                remote="r", team_drive="T", user="tester", dry_run=False,
                wcode="W-TEST99", yes=True)
    base.update(kw)
    return argparse.Namespace(**base)


def _correr(cli, tmp_path, drive, local, **kw):
    """Monta el doble, lo inyecta por el `Entorno` y ejecuta el checkin."""
    fake = FakeRclone(drive, raiz_local=tmp_path)
    rc_ = cli.cmd_checkin(args_checkin(local, **kw), entorno=_entorno(cli, fake, tmp_path))
    return rc_, fake


def _subs(fake) -> list[str]:
    return [c[1] for c in fake.cmds]


def _unico(fake, sub: str) -> list[str]:
    cmds = [c for c in fake.cmds if c[1] == sub]
    assert len(cmds) == 1, f"se esperaba UN {sub}, hubo {len(cmds)}: {_subs(fake)}"
    return cmds[0]


def _files_from_de(cmd: list[str]) -> str:
    assert "--files-from" in cmd, f"el comando no acota por lista: {cmd}"
    return cmd[cmd.index("--files-from") + 1]


def _lista_de(cmd: list[str]) -> list[str]:
    return sorted(Path(_files_from_de(cmd)).read_text(encoding="utf-8").split())


def pushes_de_caso_md(fake) -> list[list[str]]:
    return [c for c in fake.cmds
            if c[1] == "copyto" and c[3].endswith("00_Input/_caso.md")]


def auditlog_subido(fake) -> str:
    """Nombre del AUDITLOG que de verdad se subió como evidencia (CP9).

    Sirve para atar `ultimo_checkin_auditlog` al fichero que llegó, sin depender del
    reloj: el frontal advierte él mismo de que ese campo podía apuntar a un fichero
    inexistente.
    """
    nombres = [c[3].rsplit("/", 1)[-1] for c in fake.cmds
               if c[1] == "copyto" and "07_AI cowork" in c[3]]
    auditlogs = [n for n in nombres if n.startswith("AUDITLOG_MERGE_")]
    assert len(auditlogs) == 1, f"se esperaba UN auditlog subido, no {nombres}"
    return auditlogs[0]


def eventos_del_log(drive: dict[str, bytes]) -> list[dict]:
    texto = drive["00_Input/_intake_log.jsonl"].decode("utf-8")
    return [json.loads(ln) for ln in texto.splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# 1-2. Abortos antes de tocar nada
# ---------------------------------------------------------------------------

def test_ruta_local_inexistente_aborta_con_2_y_cero_comandos(cli, tmp_path):
    """Sale ANTES de pedir el directorio de trabajo: ni un solo comando rclone."""
    drive = drive_de({"00_Input/doc.pdf": b"contenido"})
    antes = dict(drive)
    fake = FakeRclone(drive, raiz_local=tmp_path)

    rc_ = cli.cmd_checkin(args_checkin(tmp_path / "no-existe"),
                          entorno=_entorno(cli, fake, tmp_path))

    assert rc_ == 2
    assert fake.cmds == [], "cero comandos: ni el inventario del Drive se pide"
    assert drive == antes
    assert not (tmp_path / "work" / "DELTA_PREVIO.md").exists(), \
        "tampoco se llega a planificar"


@pytest.mark.parametrize("stdout, frase", [
    ("[", "no es JSON válido"),
    ("[]", "Inventario vacío"),
], ids=["json_truncado", "inventario_vacio"])
def test_inventario_de_drive_invalido_aborta_con_1(cli, tmp_path, capsys,
                                                   stdout, frase):
    """Hallazgo 3 del piloto: se valida por CONTENIDO, no por código de salida.

    Los dos casos vienen con **rc 0** a propósito: rclone contra una unidad sin acceso
    termina en éxito con salida vacía o truncada, y es justo ahí donde un checkin que
    solo mirara el `returncode` planificaría un merge contra un inventario fantasma —y
    borraría en Drive todo lo que «no aparece».
    """
    drive = drive_de({"00_Input/doc.pdf": b"contenido"})
    antes = dict(drive)
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"contenido"},
                         base={"00_Input/doc.pdf": b"contenido"})
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("lsjson", 1): (0, stdout, "")})

    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))

    assert rc_ == 1
    assert frase in capsys.readouterr().out
    assert drive == antes
    assert _subs(fake) == ["lsjson"], "se abandona en el inventario"


# ---------------------------------------------------------------------------
# 3-4. Los dos frenos previos: dry-run y gate humano de los borrados
# ---------------------------------------------------------------------------

def test_dry_run_escribe_el_delta_en_el_work_dir_y_no_toca_nada(cli, tmp_path):
    drive = drive_de({"00_Input/doc.pdf": b"DRIVE viejo"})
    antes = dict(drive)
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL nuevo"},
                         base={"00_Input/doc.pdf": b"DRIVE viejo"})

    rc_, fake = _correr(cli, tmp_path, drive, local, dry_run=True)

    assert rc_ == 0
    delta = tmp_path / "work" / "DELTA_PREVIO.md"
    assert delta.exists(), "el DELTA va al work_dir INYECTADO"
    assert "Copiar (local→Drive): 1" in delta.read_text(encoding="utf-8")
    assert not (local / "DELTA_PREVIO.md").exists(), \
        "y NO a la carpeta del caso: contaminaría el inventario del próximo checkin"
    assert drive == antes, "un dry-run que sube sería el peor de los bugs"
    assert _subs(fake) == ["lsjson"]


def test_borrados_sin_yes_devuelven_3_sin_tocar_el_drive(cli, tmp_path, capsys):
    """Gate humano del CP3: un borrado propuesto no se ejecuta sin `--yes`."""
    drive = drive_de({"00_Input/doc.pdf": b"contenido"})
    antes = dict(drive)
    local = montar_local(tmp_path, {}, base={"00_Input/doc.pdf": b"contenido"})

    rc_, fake = _correr(cli, tmp_path, drive, local, yes=False)

    assert rc_ == 3
    assert drive == antes
    assert _subs(fake) == ["lsjson"], "ni copy ni moveto antes de la confirmación"
    assert "relanza con --yes para confirmar" in capsys.readouterr().out
    delta = (tmp_path / "work" / "DELTA_PREVIO.md").read_text(encoding="utf-8")
    assert "Borrados propuestos" in delta and "00_Input/doc.pdf" in delta, \
        "el operador tiene que poder ver QUÉ se iba a borrar"


# ---------------------------------------------------------------------------
# 5-6. El plan por fichero se honra: la misma lista, y lo preservado no sube
# ---------------------------------------------------------------------------

def test_el_copy_y_el_check_usan_la_misma_lista_files_from(cli, tmp_path):
    """Verificar una lista distinta de la subida daría un verde sin cobertura.

    Es lo que hace de `verificacion_limpia` una prueba y no un adorno: la lista es
    autoritativa para las dos operaciones o el `check` mide otra cosa.
    """
    drive = drive_de({"00_Input/viejo.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/viejo.pdf": b"LOCAL",
                                    "00_Input/nuevo.pdf": b"NUEVO"},
                         base={"00_Input/viejo.pdf": b"BASE"})

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0
    copy, check = _unico(fake, "copy"), _unico(fake, "check")
    assert _files_from_de(copy) == _files_from_de(check), "la MISMA lista, no una copia"
    assert _lista_de(copy) == ["00_Input/nuevo.pdf", "00_Input/viejo.pdf"]
    assert "--one-way" in check, "el check ignora los extras del destino"


def test_preserve_drive_no_se_sube(cli, tmp_path):
    """Caso 3 de la tabla: solo cambió Drive. El local NO lo pisa.

    Con un `copy` en marcha a la vez, que es donde una copia en bloque haría el daño:
    subiría la versión local del fichero que el plan mandó preservar.
    """
    drive = drive_de({"00_Input/solo_drive.pdf": b"DRIVE cambio",
                      "00_Input/solo_local.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/solo_drive.pdf": b"BASE",
                                    "00_Input/solo_local.pdf": b"LOCAL cambio"},
                         base={"00_Input/solo_drive.pdf": b"BASE",
                               "00_Input/solo_local.pdf": b"BASE"})

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0
    assert drive["00_Input/solo_drive.pdf"] == b"DRIVE cambio", \
        "el Drive conserva su versión: el checkin no la auto-resuelve"
    assert drive["00_Input/solo_local.pdf"] == b"LOCAL cambio"
    assert _lista_de(_unico(fake, "copy")) == ["00_Input/solo_local.pdf"], \
        "el preservado no entra en la lista de subida"


# ---------------------------------------------------------------------------
# 7-8. Los dos amarillos que NO liberan el lock
# ---------------------------------------------------------------------------

def test_conflicto_escribe_el_estado_y_no_libera_el_lock(cli, tmp_path, capsys):
    """CP7: estado `conflicto` en el Drive, local conservado, lock intacto.

    Se caracteriza también que el AMARILLO **sale con 0**: el frontal reserva el 1 para
    el rojo. Es lo de hoy, y por eso el aserto va con el estado del lock al lado — el
    código de salida por sí solo no distingue este final de un cierre limpio.
    """
    drive = drive_de({"00_Input/doc.pdf": b"DRIVE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})

    rc_, fake = _correr(cli, tmp_path, drive, local)
    salida = capsys.readouterr().out

    assert rc_ == 0
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "conflicto"
    assert meta["checkout_user"] == "tester", "el lock no se limpia"
    assert "ultimo_checkin_timestamp" not in meta, "no hubo checkin que cerrar"
    assert meta["id_go"] == "W-TEST99", "marcar el estado no degrada el _caso.md"
    assert drive["00_Input/doc.pdf"] == b"DRIVE", "el conflicto no se resuelve solo"
    assert eventos_del_log(drive) == [{"event": "upload_manual"}], \
        "no se registra un case_checkin que no ocurrió"
    assert "NO se libera el lock" in salida
    assert _subs(fake) == ["lsjson", "copyto", "copyto"], \
        "inventario, pull del _caso.md y push del estado: nada más"


def test_veto_de_grupo_no_libera_el_lock_ni_sube_al_grupo(cli, tmp_path, capsys):
    """N6c: sin conflictos, pero un grupo indivisible quedó descuadrado.

    El miembro que iba a subir se queda en tierra, y el checkin no escribe **nada** en
    el Drive: sin conflicto no hay estado que marcar. Salir verde aquí liberaría el lock
    con la mitad del grupo sin subir, que es el caso silencioso que motivó el veto.
    """
    drive = drive_de({MAPA: b"BASE mapa", OCURRENCIAS: b"DRIVE ocurrencias"})
    antes = dict(drive)
    local = montar_local(tmp_path, {MAPA: b"LOCAL mapa", OCURRENCIAS: b"BASE ocurrencias"},
                         base={MAPA: b"BASE mapa", OCURRENCIAS: b"BASE ocurrencias"})

    rc_, fake = _correr(cli, tmp_path, drive, local)
    salida = capsys.readouterr().out

    assert rc_ == 0
    assert drive == antes, "el grupo sube junto o no sube: el Drive queda como estaba"
    assert not pushes_de_caso_md(fake), "sin conflicto no se escribe el _caso.md"
    assert _subs(fake) == ["lsjson"], "un veto cuesta UNA operación de Drive"
    assert "grupo indivisible" in salida
    assert "NO se libera el lock" in salida


# ---------------------------------------------------------------------------
# 9. El rojo: un copy fallido no puede propagar borrados
# ---------------------------------------------------------------------------

def test_copy_fallido_no_propaga_los_borrados(cli, tmp_path, capsys):
    """Borrar sobre un merge incompleto es la pérdida de datos que no se recupera.

    El fallo se guioniza con `resultados` y no con `fallos_sub`: este último aplana todo
    a rc 3, y aquí interesa un rc de copia realista sin que el doble mute el Drive.
    """
    drive = drive_de({"00_Input/borrado.pdf": b"sigue aqui"})
    local = montar_local(tmp_path, {"00_Input/nuevo.pdf": b"NUEVO"},
                         base={"00_Input/borrado.pdf": b"sigue aqui"})
    fake = FakeRclone(drive, raiz_local=tmp_path,
                      resultados={("copy", 1): (1, "", "boom")})

    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))
    salida = capsys.readouterr().out

    assert rc_ == 1
    assert drive["00_Input/borrado.pdf"] == b"sigue aqui", "el borrado NO se propaga"
    assert "00_Input/nuevo.pdf" not in drive
    assert _subs(fake) == ["lsjson", "copy"], "ni moveto ni check tras un copy fallido"
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "prestado"
    assert "ultimo_checkin_timestamp" not in meta
    assert "NO se borra nada" in salida


# ---------------------------------------------------------------------------
# 10. El camino verde, con su orden dentro
# ---------------------------------------------------------------------------

def test_camino_verde_libera_el_lock_con_ultimo_checkin(cli, tmp_path, capsys):
    """Cierre completo del ciclo, y el ORDEN de las operaciones como tramo de su traza.

    El orden se fija **dentro** de este test, marcado `# contrato temporal (A-2)`, para
    que la Fase 2 tenga un único sitio que actualizar cuando lo cambie.
    """
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})

    rc_, fake = _correr(cli, tmp_path, drive, local)
    salida = capsys.readouterr().out

    assert rc_ == 0
    # contrato temporal (A-2): inventario → copy → check → evidencia (AUDITLOG y log
    # del check) → pull del log → push del log → lsjson de la bandeja → pull del
    # _caso.md → push del lock liberado.
    assert _subs(fake) == ["lsjson", "copy", "check", "copyto", "copyto",
                           "copyto", "copyto", "lsjson", "copyto", "copyto"]

    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "disponible"
    assert meta["checkout_user"] is None and meta["checkout_nonce"] is None, \
        "el lock se limpia, no solo se cambia el estado"
    assert meta["ultimo_checkin_timestamp"], "la marca del checkin no puede ir vacía"
    assert meta["ultimo_checkin_auditlog"] == auditlog_subido(fake), \
        "el puntero del lock apunta al AUDITLOG que de verdad llegó al Drive"
    assert meta["id_go"] == "W-TEST99", "liberar no degrada el _caso.md a un stub"
    assert drive["00_Input/doc.pdf"] == b"LOCAL", "y los bytes del merge están arriba"
    # Frase completa y con espacios: el nombre de este test viaja dentro de `tmp_path`,
    # que el frontal imprime, así que un aserto sobre `"verde"` o `"lock"` a secas lo
    # cumpliría la propia ruta. Es además la línea exacta que el PR #160 protegió.
    assert "AUDITLOG subido, case_checkin registrado, lock liberado" in salida


def test_el_evento_case_checkin_lleva_el_resumen_del_plan(cli, tmp_path):
    """El evento forense se AÑADE al log y resume el plan por tipo de acción."""
    drive = drive_de({"00_Input/preservado.pdf": b"DRIVE cambio",
                      "00_Input/borrado.pdf": b"a la papelera"})
    local = montar_local(tmp_path, {"00_Input/preservado.pdf": b"BASE",
                                    "00_Input/nuevo.pdf": b"NUEVO"},
                         base={"00_Input/preservado.pdf": b"BASE",
                               "00_Input/borrado.pdf": b"a la papelera"})

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0
    eventos = eventos_del_log(drive)
    assert eventos[0] == {"event": "upload_manual"}, "el historial previo sobrevive"
    assert len(eventos) == 2
    evento = eventos[-1]
    assert evento["event"] == "case_checkin"
    assert evento["actor"] == "tester"
    assert evento["case_id"] == CASE_ID
    d = evento["details"]
    assert (d["copiados"], d["preservados"], d["borrados"]) == (1, 1, 1)
    assert d["resultado"] == "verde"
    assert d["auditlog"] == auditlog_subido(fake)
    # `conflictos` va cableado a 0 en la llamada del camino verde. Hoy no es observable
    # como defecto —el verde exige cero conflictos— pero sí lo sería si algún día el
    # verde admitiera alguno; queda dicho aquí y no en un aserto que no puede fallar.
    assert d["conflictos"] == 0


def test_el_borrado_va_al_backup_dir_no_a_la_nada(cli, tmp_path):
    """CP6: `rclone copy` no borra; el borrado se **mueve** al `--backup-dir` (D2).

    Es lo que hace el borrado recuperable, así que la caracterización tiene que mirar
    dónde acabó el fichero, no solo que desapareció de su ruta.
    """
    drive = drive_de({"00_Input/borrado.pdf": b"a la papelera"})
    local = montar_local(tmp_path, {"00_Input/nuevo.pdf": b"NUEVO"},
                         base={"00_Input/borrado.pdf": b"a la papelera"})

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0
    assert "00_Input/borrado.pdf" not in drive
    respaldos = {k: v for k, v in drive.items() if k.startswith("_merge_backups/")}
    assert list(respaldos.values()) == [b"a la papelera"], \
        "el borrado queda recuperable bajo _merge_backups/"
    assert list(respaldos)[0].endswith("/00_Input/borrado.pdf"), \
        "y con su jerarquía, para poder devolverlo a su sitio"
    mv = _unico(fake, "moveto")
    assert mv[2] == f"{REMOTO}00_Input/borrado.pdf"
    assert mv[3].startswith(f"{REMOTO}_merge_backups/W-TEST99_")


# ---------------------------------------------------------------------------
# 11-13. La bandeja del guard de escritura (CP10)
# ---------------------------------------------------------------------------

def test_la_bandeja_se_integra_y_se_vacia(cli, tmp_path, capsys):
    """Lo que el pipeline escribió durante el préstamo vuelve a su ruta original."""
    bandeja = "_pendiente_checkin/pipeline/01_Procesado/informe.md"
    drive = drive_de({"00_Input/doc.pdf": b"igual", bandeja: b"escrito en el prestamo"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"igual"},
                         base={"00_Input/doc.pdf": b"igual"})

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0
    assert drive["01_Procesado/informe.md"] == b"escrito en el prestamo"
    assert bandeja not in drive, "la bandeja se vacía al integrarla"
    assert "rmdirs" in _subs(fake), "y se limpian sus directorios"
    assert "bandeja integrada" in capsys.readouterr().out
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "disponible"


def test_colision_en_la_bandeja_va_a_reingesta_sin_sobrescribir(cli, tmp_path,
                                                                capsys):
    """La bandeja NUNCA pisa lo recién mergeado: se renombra a `_reingesta_*`.

    `MEJORAS #101` está abierto precisamente porque después **nadie reconcilia** ese
    `_reingesta_`. Lo que se caracteriza aquí es que no sobrescribe, no que el ciclo
    quede cerrado.
    """
    bandeja = "_pendiente_checkin/pipeline/00_Input/doc.pdf"
    drive = drive_de({"00_Input/doc.pdf": b"el mergeado", bandeja: b"el de la bandeja"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"el mergeado"},
                         base={"00_Input/doc.pdf": b"el mergeado"})

    rc_, fake = _correr(cli, tmp_path, drive, local)

    assert rc_ == 0
    assert drive["00_Input/doc.pdf"] == b"el mergeado", "no se pisa lo mergeado"
    assert drive["00_Input/_reingesta_doc.pdf"] == b"el de la bandeja"
    assert bandeja not in drive
    assert "como _reingesta_ (colisión, sin sobrescribir)" in capsys.readouterr().out


def test_bandeja_ilegible_no_libera_el_lock_ni_deja_contenido_integrado(
        cli, tmp_path, capsys):
    """Caracterización VERDE del 8º defecto: un listado ilegible no es una bandeja vacía.

    Lo cerró el PR #160, así que aquí no hay `xfail`. Complementa a
    `test_bandeja_ilegible_no_libera_el_lock` de `tests/test_repository_cli_guard_pull.py`,
    que fija el código de salida y el estado; esto añade lo que le falta: que el
    contenido sigue **sin integrar** y que el lock no recibió los campos de cierre.
    """
    bandeja = "_pendiente_checkin/pipeline/00_Input/nuevo.pdf"
    drive = drive_de({"00_Input/doc.pdf": b"igual", bandeja: b"sin integrar"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"igual"},
                         base={"00_Input/doc.pdf": b"igual"})
    # El 1er lsjson es el inventario del CP1; el 2º, el de la bandeja (CP10).
    fake = FakeRclone(drive, raiz_local=tmp_path, fallos_sub={"lsjson": [2]})

    rc_ = cli.cmd_checkin(args_checkin(local), entorno=_entorno(cli, fake, tmp_path))

    assert rc_ == 4
    assert _subs(fake).count("lsjson") == 2, "falló el listado de la bandeja, no el CP1"
    meta = meta_de(drive["00_Input/_caso.md"], tmp_path)
    assert meta["estado_repositorio"] == "prestado"
    assert "ultimo_checkin_timestamp" not in meta
    assert drive[bandeja] == b"sin integrar", "sigue en la bandeja"
    assert "00_Input/nuevo.pdf" not in drive, "y no se integró a medias"
    assert "lock liberado" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# El entrypoint público
# ---------------------------------------------------------------------------

def test_smoke_del_parser_publico(cli, tmp_path):
    """Sin esto, el `Namespace` a mano podría divergir del que produce la CLI real."""
    drive = drive_de({"00_Input/doc.pdf": b"BASE"})
    local = montar_local(tmp_path, {"00_Input/doc.pdf": b"LOCAL"},
                         base={"00_Input/doc.pdf": b"BASE"})
    fake = FakeRclone(drive, raiz_local=tmp_path)

    args = cli.build_parser().parse_args([
        "checkin", CASE_ID, "--local", str(local), "--remote-path", "",
        "--remote", "r", "--team-drive", "T", "--user", "tester",
        "--wcode", "W-TEST99", "--yes",
    ])

    assert cli.cmd_checkin(args, entorno=_entorno(cli, fake, tmp_path)) == 0
    assert meta_de(drive["00_Input/_caso.md"], tmp_path)["estado_repositorio"] == "disponible"
    assert drive["00_Input/doc.pdf"] == b"LOCAL"
