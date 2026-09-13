"""El recorrido de custodia tolera que el montaje renombre bajo los pies (`MEJORAS #214`).

**El fenómeno, medido el 2026-09-10 abriendo W-048U77.** El montaje de Google Drive for
Desktop *presenta* una extensión inferida del content-type para los ficheros que en Drive no
la llevan, y lo hace poco después de que `rclone` haya escrito el nombre pelado. La carpeta
de E&V traía **11 de 58 ficheros sin extensión**, que en ese Drive es lo normal (escaneos y
fotos de móvil). `hash_tree_local` **lista y luego abre**, así que moría con
`FileNotFoundError` sobre un fichero que está — y la etapa `drive` de V1 pasaba a `bloqueado`
con el pull ya hecho.

**La propiedad que estos tests contratan**, y que es lo que separa un remedio de un
«tragarse el error»: un fichero que no se pudo leer **no ha medido cero**. Ha quedado
**sin verificar**, y eso se dice — en el resultado, en el evento forense y en el estado de
la etapa. Un recorrido que devuelve `{}` sobre una carpeta irrecorrible está afirmando algo
falso sobre el expediente.

Diseño: `docs/superpowers/handoffs/handoff-2026-09-13-fila27-tipo-por-bytes.md` §3.

**El árbol es sintético y vive en `tmp_path`** (patrón de `test_guard_localizador.py`):
ningún test escribe en el árbol de producción. La carrera se monta parcheando `file_sha256`
para que renombre **en disco** y lance, que es exactamente lo que hace el montaje; la
relectura del directorio la hace el código real, no un doble.

**Lo que estos tests NO acreditan:** que el montaje real de Drive for Desktop se comporte
así. Eso solo se comprueba en una apertura real sobre `G:`, y hasta entonces queda declarado
como no verificado.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core import abrir_caso as brain
from core import apertura_v1 as av1
from core import intake_log
from core.intake_drive import DriveIntakeResult
from scripts import abrir_caso as cli

PREFIJO = "01_Drive EV"


# ---------------------------------------------------------------------------
# Árbol sintético y el doble que monta la carrera
# ---------------------------------------------------------------------------

def _arbol(tmp_path: Path, ficheros: dict[str, bytes]) -> Path:
    """Monta `<tmp_path>/01_Drive EV/...` y lo devuelve. Claves = rutas relativas posix."""
    root = tmp_path / PREFIJO
    for rel, data in ficheros.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


def _renombrar_al_abrir(monkeypatch, victima: Path, destinos: list[Path]):
    """Parchea `file_sha256` para que la PRIMERA lectura de `victima` la renombre en disco.

    Reproduce el montaje: el fichero existía cuando se listó y ya no está con ese nombre
    cuando se abre. Con `destinos` vacío el fichero se borra — el caso «desapareció de
    verdad». Con dos destinos, aparece por duplicado: ambigüedad.
    """
    real = cli.file_sha256
    disparado: list[Path] = []

    def doble(path: Path, *a, **kw):
        if path == victima and not disparado:
            disparado.append(path)
            data = path.read_bytes()
            path.unlink()
            for d in destinos:
                d.write_bytes(data)
            raise FileNotFoundError(2, "No such file or directory", str(path))
        return real(path, *a, **kw)

    monkeypatch.setattr(cli, "file_sha256", doble)
    return disparado


# ---------------------------------------------------------------------------
# 1. El fichero cambia de nombre entre el listado y la apertura
# ---------------------------------------------------------------------------

def test_a1_un_renombrado_se_hashea_bajo_su_clave_efectiva(tmp_path, monkeypatch):
    """El caso real: `rclone` escribe `NIE Pasaporte`, el montaje lo presenta como
    `NIE Pasaporte.jpg`. El contenido está; lo que cambió es el nombre."""
    root = _arbol(tmp_path, {"NIE Pasaporte": b"jpeg-bytes", "otro.pdf": b"pdf"})
    _renombrar_al_abrir(monkeypatch, root / "NIE Pasaporte",
                        [root / "NIE Pasaporte.jpg"])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert f"{PREFIJO}/NIE Pasaporte.jpg" in arbol.hashes
    assert f"{PREFIJO}/NIE Pasaporte" not in arbol.hashes
    assert arbol.sin_verificar == ()


def test_a2_el_renombrado_queda_anotado_con_las_dos_claves(tmp_path, monkeypatch):
    """No basta con hashearlo: la custodia tiene que poder decir que la clave listada y la
    efectiva no son la misma, o el ledger afirma un nombre que nadie vio."""
    root = _arbol(tmp_path, {"escaneo": b"bytes"})
    _renombrar_al_abrir(monkeypatch, root / "escaneo", [root / "escaneo.pdf"])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.renombrados == ((f"{PREFIJO}/escaneo", f"{PREFIJO}/escaneo.pdf"),)


def test_a3_el_hash_del_renombrado_es_el_del_CONTENIDO_no_el_de_otro_fichero(tmp_path, monkeypatch):
    """Control positivo del anterior: que la clave sea la nueva no prueba que los bytes
    hasheados sean los suyos. Un remedio que hasheara el vecino pasaría A1 y A2."""
    root = _arbol(tmp_path, {"escaneo": b"contenido-unico", "vecino.pdf": b"otra-cosa"})
    _renombrar_al_abrir(monkeypatch, root / "escaneo", [root / "escaneo.pdf"])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    from core.utils import file_sha256
    assert arbol.hashes[f"{PREFIJO}/escaneo.pdf"] == file_sha256(root / "escaneo.pdf")
    assert arbol.hashes[f"{PREFIJO}/escaneo.pdf"] != arbol.hashes[f"{PREFIJO}/vecino.pdf"]


def test_a4_el_candidato_tiene_que_ser_NUEVO_no_uno_que_ya_estaba_listado(tmp_path, monkeypatch):
    """`escaneo.pdf` ya existía por su cuenta y se listó: no es la reaparición de `escaneo`,
    es otro documento. Adoptarlo sería contar un fichero dos veces y perder el otro."""
    root = _arbol(tmp_path, {"escaneo": b"sin-extension", "escaneo.pdf": b"con-extension"})
    _renombrar_al_abrir(monkeypatch, root / "escaneo", [])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/escaneo"]
    assert arbol.renombrados == ()
    from core.utils import file_sha256
    assert arbol.hashes[f"{PREFIJO}/escaneo.pdf"] == file_sha256(root / "escaneo.pdf")


# ---------------------------------------------------------------------------
# 2. El fichero desaparece de verdad
# ---------------------------------------------------------------------------

def test_a5_un_fichero_que_desaparece_sale_DECLARADO_no_omitido(tmp_path, monkeypatch):
    """La mitad que impide que el remedio sea «tragarse el error». Sin este test, capturar
    el `FileNotFoundError` y seguir convierte un documento perdido en silencio."""
    root = _arbol(tmp_path, {"volatil": b"x", "estable.pdf": b"y"})
    _renombrar_al_abrir(monkeypatch, root / "volatil", [])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert f"{PREFIJO}/volatil" not in arbol.hashes
    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/volatil"]
    assert arbol.sin_verificar[0].motivo
    assert f"{PREFIJO}/estable.pdf" in arbol.hashes


def test_a6_un_error_de_lectura_que_no_es_ausencia_tambien_se_declara(tmp_path, monkeypatch):
    """`FileNotFoundError` es el caso medido, pero la propiedad es más ancha: cualquier
    `OSError` deja el fichero sin verificar. Un permiso denegado no ha medido cero."""
    root = _arbol(tmp_path, {"bloqueado.pdf": b"x"})
    real = cli.file_sha256

    def doble(path: Path, *a, **kw):
        if path.name == "bloqueado.pdf":
            raise PermissionError(13, "Permission denied", str(path))
        return real(path, *a, **kw)

    monkeypatch.setattr(cli, "file_sha256", doble)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.hashes == {}
    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/bloqueado.pdf"]
    assert "Permission" in arbol.sin_verificar[0].motivo


# ---------------------------------------------------------------------------
# 3. Dos candidatos: ambigüedad, no elegir uno
# ---------------------------------------------------------------------------

def test_a7_dos_candidatos_al_renombrado_son_ambiguedad_y_no_se_elige(tmp_path, monkeypatch):
    """Si el contenido reaparece bajo DOS nombres, cuál es el documento no lo sabe nadie.
    Elegir el primero por orden alfabético sería inventarse la custodia."""
    root = _arbol(tmp_path, {"escaneo": b"bytes"})
    _renombrar_al_abrir(monkeypatch, root / "escaneo",
                        [root / "escaneo.jpg", root / "escaneo.pdf"])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.renombrados == ()
    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/escaneo"]
    assert "ambig" in arbol.sin_verificar[0].motivo.lower()
    # Y no se cuela ninguno de los dos por la puerta de atrás.
    assert f"{PREFIJO}/escaneo.jpg" not in arbol.hashes
    assert f"{PREFIJO}/escaneo.pdf" not in arbol.hashes


# ---------------------------------------------------------------------------
# 4. Un directorio irrecorrible no son «cero ficheros»
# ---------------------------------------------------------------------------

def test_a8_un_directorio_irrecorrible_se_declara_y_no_cuenta_cero(tmp_path, monkeypatch):
    """`rglob` **suprime** los errores de recorrido: una carpeta que no se puede leer
    devuelve cero ficheros y nadie se entera. Es la clase H-04 que la R1 de
    `verificar_apertura` midió el 2026-09-11, un nivel más abajo.

    El `PermissionError` se inyecta en `os.scandir`, que es la primitiva que `os.walk`
    usa: lo que se prueba es el `onerror` real del recorrido, no un doble de `os.walk`.
    """
    root = _arbol(tmp_path, {"visible.pdf": b"x", "cerrada/dentro.pdf": b"y"})
    cerrada = root / "cerrada"
    real_scandir = os.scandir

    def doble(path=".", *a, **kw):
        if Path(path) == cerrada:
            raise PermissionError(13, "Permission denied", str(path))
        return real_scandir(path, *a, **kw)

    monkeypatch.setattr(os, "scandir", doble)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert f"{PREFIJO}/visible.pdf" in arbol.hashes
    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/cerrada"]
    assert "Permission" in arbol.sin_verificar[0].motivo


# ---------------------------------------------------------------------------
# 5. Lo que no cambia: el camino feliz y el protocolo por ubicación
# ---------------------------------------------------------------------------

def test_a9_sin_incidencias_el_resultado_es_el_de_siempre(tmp_path):
    """Regresión: el árbol sin sobresaltos sigue produciendo los mismos hashes, y las dos
    listas de incidencias salen vacías."""
    root = _arbol(tmp_path, {"a.pdf": b"uno", "sub/b.pdf": b"dos"})

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    from core.utils import file_sha256
    assert arbol.hashes == {
        f"{PREFIJO}/a.pdf": file_sha256(root / "a.pdf"),
        f"{PREFIJO}/sub/b.pdf": file_sha256(root / "sub" / "b.pdf"),
    }
    assert arbol.sin_verificar == () and arbol.renombrados == ()


def test_a10_una_raiz_que_no_existe_sigue_siendo_arbol_vacio(tmp_path):
    """El contrato de siempre (`test_custodia_destino_efectivo`): sin carpeta, sin plan.
    Eso NO es un `sin_verificar` — no hay nada que verificar."""
    arbol = cli.hash_tree_local(tmp_path / "no-existe", prefijo=PREFIJO)

    assert arbol.hashes == {} and arbol.sin_verificar == () and arbol.renombrados == ()


LOTE = "2026-09-01_email_01"


def test_a11_el_protocolo_se_decide_sobre_la_clave_EFECTIVA(tmp_path, monkeypatch):
    """`MEJORAS #149`: el protocolo es por UBICACIÓN, y la ubicación que cuenta es la
    EFECTIVA. Si el montaje renombra un fichero a algo que en esa carpeta es protocolo,
    adoptarlo por la clave vieja lo colaría en el ledger forense del cliente.

    **Se prueba sobre un prefijo de lote a propósito, y eso es el punto.** Con
    `01_Drive EV` el único protocolo es `.pulled`, y añadir una extensión nunca produce
    ese nombre: la guarda sería inerte, escrita y sin poder morder jamás. En un lote sí
    puede: `_manifiesto` → `_manifiesto.yaml` es exactamente el patrón del montaje
    —añadir la extensión del content-type— y cae de lleno en el protocolo del lote.
    """
    root = tmp_path / LOTE
    root.mkdir()
    (root / "_manifiesto").write_bytes(b"x")
    (root / "documento.pdf").write_bytes(b"y")
    _renombrar_al_abrir(monkeypatch, root / "_manifiesto", [root / "_manifiesto.yaml"])

    arbol = cli.hash_tree_local(root, prefijo=LOTE)

    # Se anota el renombrado —pasó— pero el fichero efectivo NO entra en el ledger.
    assert arbol.renombrados == ((f"{LOTE}/_manifiesto", f"{LOTE}/_manifiesto.yaml"),)
    assert f"{LOTE}/_manifiesto.yaml" not in arbol.hashes
    assert f"{LOTE}/_manifiesto" not in arbol.hashes
    assert list(arbol.hashes) == [f"{LOTE}/documento.pdf"]


def test_a11b_control_positivo_ese_mismo_renombrado_SIN_protocolo_si_entra(tmp_path, monkeypatch):
    """Sin esto, A11 pasaría igual si el remedio hubiera dejado de adoptar renombrados en
    general: el `not in` no distingue «lo excluyó el protocolo» de «no lo adoptó nunca»."""
    root = tmp_path / LOTE
    root.mkdir()
    (root / "escaneo").write_bytes(b"x")
    _renombrar_al_abrir(monkeypatch, root / "escaneo", [root / "escaneo.yaml"])

    arbol = cli.hash_tree_local(root, prefijo=LOTE)

    assert arbol.renombrados == ((f"{LOTE}/escaneo", f"{LOTE}/escaneo.yaml"),)
    assert f"{LOTE}/escaneo.yaml" in arbol.hashes


def test_a12_el_protocolo_de_la_ubicacion_sigue_fuera_del_ledger(tmp_path):
    """Regresión de `MEJORAS #149`, que el recorrido nuevo no puede perder."""
    root = _arbol(tmp_path, {".pulled": b"{}", "sub/_ficha_crm.yaml": b"de E&V"})

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert f"{PREFIJO}/.pulled" not in arbol.hashes
    assert f"{PREFIJO}/sub/_ficha_crm.yaml" in arbol.hashes


# ---------------------------------------------------------------------------
# 6. La declaración viaja: evento forense y estado de la etapa
# ---------------------------------------------------------------------------

def _plan_trivial(monkeypatch):
    """Neutraliza el cerebro: aquí se contrata el VIAJE de la declaración, no el plan."""
    class _Plan:
        depositables: list = []
        items: list = []
        con_sha: list = [{"path": "x", "sha256": "y"}]

    # El log se lee por `case_id` y resuelve contra el catalogo local, que en `tmp_path`
    # no conoce el caso. Aqui el plan no es el objeto de prueba: lo es el viaje.
    monkeypatch.setattr(intake_log, "read_events", lambda *a, **k: [])
    monkeypatch.setattr(brain, "plan_intake", lambda *a, **k: _Plan())
    monkeypatch.setattr(
        brain, "reconcile",
        lambda *a, **k: brain.Reconciliacion(ok=True, faltantes=(), mismatches=(), extras=()))


def test_a13_un_sin_verificar_llega_al_evento_forense(tmp_path, monkeypatch):
    """`count` cuenta solo lo VERIFICADO, así que sin esta lista el registro se lee como
    «todo cuadró» — que es justo la afirmación falsa que esta pieza viene a impedir."""
    _plan_trivial(monkeypatch)
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    sv = (brain.FicheroSinVerificar(clave=f"{PREFIJO}/volatil", motivo="desapareció"),)

    cli._intake_generico(case_dir, "W-TEST", "drive_ev", {}, base=PREFIJO,
                         dry_run=False, raiz_hashes=tmp_path,
                         sin_verificar=sv, renombrados=((f"{PREFIJO}/a", f"{PREFIJO}/a.pdf"),))

    ev = [e for e in intake_log.read_events_de(case_dir)
          if e["event"] == brain.FUENTE_A_EVENTO["drive_ev"]]
    assert len(ev) == 1
    detalles = ev[0]["details"]
    assert detalles["sin_verificar"] == [
        {"clave": f"{PREFIJO}/volatil", "motivo": "desapareció"}]
    assert detalles["renombrados"] == [[f"{PREFIJO}/a", f"{PREFIJO}/a.pdf"]]


def test_a14_sin_incidencias_el_evento_no_se_ensucia(tmp_path, monkeypatch):
    """El mutante simétrico: escribir `sin_verificar: []` en todos los eventos haría pasar
    A13 y llenaría el ledger de ruido. Las claves solo aparecen cuando hay algo que decir."""
    _plan_trivial(monkeypatch)
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    cli._intake_generico(case_dir, "W-TEST", "drive_ev", {}, base=PREFIJO,
                         dry_run=False, raiz_hashes=tmp_path)

    detalles = intake_log.read_events_de(case_dir)[0]["details"]
    assert "sin_verificar" not in detalles and "renombrados" not in detalles


def test_a15_un_sin_verificar_llega_al_Pendiente_de_la_etapa(tmp_path):
    """El otro extremo del viaje: V1 no puede decir «hecha, N documentos» sin más cuando
    hay ficheros que no se pudieron leer. **La etapa no se tumba** — se declara."""
    destino = tmp_path / "00_Input" / PREFIJO
    destino.mkdir(parents=True)
    (destino / "a.pdf").write_bytes(b"x")
    res = DriveIntakeResult(
        case_id="C", team_id="T", folder_id="F", target_dir=destino, files_after=1,
        skipped=False, rclone_returncode=0, errors=[],
        custodia_sin_verificar=(
            brain.FicheroSinVerificar(clave=f"{PREFIJO}/volatil", motivo="desapareció"),))

    r = cli.etapa_drive(None, tmp_path, folder_id="F", team_id="T",
                        intake=lambda *a, **k: res)

    assert r.estado == "hecha"
    assert [p.codigo for p in r.pendientes] == ["custodia_sin_verificar"]
    assert "volatil" in r.pendientes[0].detalle


def test_a16_sin_incidencias_la_etapa_no_inventa_pendientes(tmp_path):
    """Mutante simétrico de A15: emitir el `Pendiente` siempre haría pasar A15 y volvería
    inútil el aviso — un caso limpio pasaría a leerse como incompleto."""
    destino = tmp_path / "00_Input" / PREFIJO
    destino.mkdir(parents=True)
    (destino / "a.pdf").write_bytes(b"x")
    res = DriveIntakeResult(
        case_id="C", team_id="T", folder_id="F", target_dir=destino, files_after=1,
        skipped=False, rclone_returncode=0, errors=[])

    r = cli.etapa_drive(None, tmp_path, folder_id="F", team_id="T",
                        intake=lambda *a, **k: res)

    assert r.estado == "hecha" and r.pendientes == ()


def test_a17_el_pendiente_de_la_etapa_llega_al_estado_de_V1(tmp_path):
    """Un `Pendiente` que la etapa emite y el secuenciador tira por el camino no declara
    nada. Contrato de `av1`: los pendientes de las etapas se acumulan en el resultado."""
    pend = av1.Pendiente(codigo="custodia_sin_verificar", detalle="1 fichero")
    etapa = av1.Etapa("drive", lambda: av1.EtapaResultado(
        nombre="drive", estado="hecha", detalle="ok", pendientes=(pend,)))

    resultado = av1.secuenciar([etapa])

    assert pend in resultado.pendientes


# ---------------------------------------------------------------------------
# 7. El pull FALLIDO: los bytes parciales también se declaran
# ---------------------------------------------------------------------------

def test_a18_el_registro_del_pull_fallido_tambien_declara_lo_no_verificado(tmp_path, monkeypatch):
    """R15/H15-06 registra los bytes parciales de un `rclone` no cero. Ese recorrido corre
    sobre el MISMO montaje, así que tiene la misma carrera: si ahí se traga el fallo, la
    custodia del caso peor —el pull roto— es la que queda muda."""
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    destino = tmp_path / "00_Input" / PREFIJO
    destino.mkdir(parents=True)
    (destino / "parcial.pdf").write_bytes(b"x")
    (destino / "volatil").write_bytes(b"y")
    _renombrar_al_abrir(monkeypatch, destino / "volatil", [])

    parcial = DriveIntakeResult(
        case_id="W-TEST", team_id="T", folder_id="F", target_dir=destino, files_after=2,
        skipped=False, rclone_returncode=3, errors=["rclone: exit 3"])
    def _pull(*a, **k):
        raise cli.intake_drive.DriveIntakeError(parcial)

    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev", _pull)

    class _Ident:
        case_id = "W-TEST"

    with pytest.raises(cli.intake_drive.DriveIntakeError):
        cli._intake_drive_ev(_Ident(), case_dir, "F", "T", dry_run=False)

    ev = [e for e in intake_log.read_events_de(case_dir) if e["event"] == "pull_drive_ev"]
    assert len(ev) == 1 and ev[0]["details"]["status"] == "fallo"
    assert ev[0]["details"]["sin_verificar"] == [
        {"clave": f"{PREFIJO}/volatil", "motivo": ev[0]["details"]["sin_verificar"][0]["motivo"]}]
    assert ev[0]["details"]["count"] == 1


def test_a19_la_custodia_ADJUNTA_lo_no_verificado_al_resultado_que_devuelve(tmp_path, monkeypatch):
    """La costura entre A5 y A15, que ninguno de los dos cubre: A5 prueba que el recorrido
    lo declara, A15 que la etapa lo convierte en `Pendiente` **dándoselo ya puesto**. Si
    `_intake_drive_ev` no lo adjuntara al `DriveIntakeResult`, los dos seguirían verdes y
    la cadena estaría rota justo en medio — en producción, y en silencio.
    """
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    destino = case_dir / "00_Input" / PREFIJO
    destino.mkdir()
    (destino / "estable.pdf").write_bytes(b"x")
    (destino / "volatil").write_bytes(b"y")
    _renombrar_al_abrir(monkeypatch, destino / "volatil", [])
    _plan_trivial(monkeypatch)

    res_pull = DriveIntakeResult(
        case_id="W-TEST", team_id="T", folder_id="F", target_dir=destino, files_after=2,
        skipped=False, rclone_returncode=0, errors=[])
    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev", lambda *a, **k: res_pull)

    class _Ident:
        case_id = "W-TEST"

    res = cli._intake_drive_ev(_Ident(), case_dir, "F", "T", dry_run=False)

    assert [f.clave for f in res.custodia_sin_verificar] == [f"{PREFIJO}/volatil"]
    # Y el resto del resultado del pull sigue intacto: se adjunta, no se sustituye.
    assert res.target_dir == destino and res.rclone_returncode == 0


# ---------------------------------------------------------------------------
# 8. Las ramas de fallo del propio remedio
#
# Un remedio contra el «se tragó el error» que a su vez se trague un error en sus propias
# ramas de rescate habría movido el silencio de sitio, no lo habría quitado.
# ---------------------------------------------------------------------------

def test_a20_si_no_se_puede_releer_el_directorio_se_declara(tmp_path, monkeypatch):
    """La relectura tras el `FileNotFoundError` puede fallar ella misma. Si eso se
    tragase, el fichero saldría del recorrido sin hash y sin declaración."""
    root = _arbol(tmp_path, {"volatil": b"x"})
    _renombrar_al_abrir(monkeypatch, root / "volatil", [root / "volatil.pdf"])
    real_iterdir = Path.iterdir

    def sin_relectura(self):
        if self == root:
            raise PermissionError(13, "Permission denied", str(self))
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", sin_relectura)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/volatil"]
    assert "releer" in arbol.sin_verificar[0].motivo
    assert arbol.renombrados == ()


def test_a21_si_el_reaparecido_tampoco_se_deja_leer_se_declara_bajo_su_clave_efectiva(
        tmp_path, monkeypatch):
    """El fichero reapareció —el renombrado es un hecho y se anota— pero sus bytes no se
    pudieron leer. Declararlo bajo la clave VIEJA nombraría algo que en disco ya no está."""
    root = _arbol(tmp_path, {"volatil": b"x"})
    real = cli.file_sha256
    disparado: list[str] = []

    def doble(path: Path, *a, **kw):
        if path.name == "volatil" and not disparado:
            disparado.append("si")
            path.rename(root / "volatil.pdf")
            raise FileNotFoundError(2, "No such file or directory", str(path))
        if path.name == "volatil.pdf":
            raise PermissionError(13, "Permission denied", str(path))
        return real(path, *a, **kw)

    monkeypatch.setattr(cli, "file_sha256", doble)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.renombrados == ((f"{PREFIJO}/volatil", f"{PREFIJO}/volatil.pdf"),)
    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/volatil.pdf"]
    assert arbol.hashes == {}


def test_a22_si_la_RAIZ_entera_es_irrecorrible_se_declara_con_su_propia_clave(tmp_path, monkeypatch):
    """El caso peor del recorrido, y el que más se parece a «no hay nada»: la carpeta del
    pull entera ilegible. Tiene que salir declarada, y nombrada `01_Drive EV` — no
    `01_Drive EV/.`, que es lo que sale de un `relative_to` ingenuo."""
    root = _arbol(tmp_path, {"a.pdf": b"x"})
    real_scandir = os.scandir

    def doble(path=".", *a, **kw):
        if Path(path) == root:
            raise PermissionError(13, "Permission denied", str(path))
        return real_scandir(path, *a, **kw)

    monkeypatch.setattr(os, "scandir", doble)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.hashes == {}
    assert [f.clave for f in arbol.sin_verificar] == [PREFIJO]
