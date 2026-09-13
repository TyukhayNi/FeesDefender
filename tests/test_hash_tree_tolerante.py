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


# ---------------------------------------------------------------------------
# 9. Los doce hallazgos de la R1 de Codex (2026-09-13), por frontera
#
# Acta: docs/superpowers/plans/2026-09-13-fila27-pieza-a-r1-adversarial-review.md
# Cuatro fronteras y no doce defectos sueltos — remediar el ejemplo en vez de la
# frontera es lo que costó cuatro rondas en el mutex de V1.
# ---------------------------------------------------------------------------

# --- Frontera A: comparar nombres de fichero por igualdad de CADENA ---------
# En Windows el sistema de ficheros no distingue caja, así que dos cadenas distintas
# pueden nombrar el mismo fichero. Comparar con `==` produce los dos errores simétricos:
# adoptar lo que no debe (H-01) y no reconocer lo que sí (H-09).

def test_r1_h01_un_candidato_YA_LISTADO_no_se_adopta_aunque_cambie_la_caja(tmp_path, monkeypatch):
    """H-01 (ALTO). `X.PDF` estaba listado; el montaje lo presenta como `x.pdf`. Con la
    comparación sensible a la caja, `x.pdf` parece un candidato nuevo y se adopta: el hash
    de OTRO documento acaba bajo dos claves, y el original se pierde **sin declararse**."""
    root = _arbol(tmp_path, {"x": b"ORIGINAL", "X.PDF": b"OTRO"})
    real = cli.file_sha256
    disparado: list[str] = []

    def doble(path: Path, *a, **kw):
        if path.name == "x" and not disparado:
            disparado.append("si")
            path.unlink()
            (root / "X.PDF").rename(root / "x.pdf")
            raise FileNotFoundError(2, "gone", str(path))
        return real(path, *a, **kw)

    monkeypatch.setattr(cli, "file_sha256", doble)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.renombrados == (), "adoptó un fichero que ya estaba listado"
    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/x"]
    # Y el otro documento se cuenta UNA vez, no dos con el mismo hash.
    assert len(arbol.hashes) == 1


def test_r1_h09_un_renombrado_que_solo_cambia_la_caja_SI_se_reconoce(tmp_path, monkeypatch):
    """H-09 (BAJO), la mitad simétrica: `Photo` va a `photo.jpg`. El documento está y es
    legible; con `==` quedaba declarado sin verificar por un detalle de mayúsculas."""
    root = _arbol(tmp_path, {"Photo": b"bytes"})
    _renombrar_al_abrir(monkeypatch, root / "Photo", [root / "photo.jpg"])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.renombrados == ((f"{PREFIJO}/Photo", f"{PREFIJO}/photo.jpg"),)
    assert f"{PREFIJO}/photo.jpg" in arbol.hashes
    assert arbol.sin_verificar == ()


def test_r1_h09b_un_renombrado_con_DOS_extensiones_tambien_se_reconoce(tmp_path, monkeypatch):
    """H-09 (BAJO), la otra mitad: `x` va a `x.tar.gz`. El criterio por `stem` falla —el
    stem es `x.tar`—, y el criterio correcto no es «el stem coincide» sino «el nombre
    efectivo empieza por el listado más un punto»."""
    root = _arbol(tmp_path, {"x": b"bytes"})
    _renombrar_al_abrir(monkeypatch, root / "x", [root / "x.tar.gz"])

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.renombrados == ((f"{PREFIJO}/x", f"{PREFIJO}/x.tar.gz"),)
    assert f"{PREFIJO}/x.tar.gz" in arbol.hashes


# --- Frontera B: la declaración viaja por caminos con salidas anticipadas ---
# Construir el dato y usarlo al final deja tantos agujeros como `return` haya en medio.

def test_r1_h02_el_evento_se_escribe_aunque_NO_haya_ni_un_depositable(tmp_path, monkeypatch):
    """H-02 (ALTO), y es el caso PEOR: el pull trae ficheros, ninguno se pudo leer, así que
    `plan.con_sha` queda vacío y el `append_event` no llegaba a ejecutarse. La única
    corrida que de verdad tenía algo que declarar era la única que no dejaba rastro."""
    monkeypatch.setattr(intake_log, "read_events", lambda *a, **k: [])
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    sv = (brain.FicheroSinVerificar(clave=f"{PREFIJO}/volatil", motivo="PermissionError"),)

    cli._intake_generico(case_dir, "W-TEST", "drive_ev", {}, base=PREFIJO,
                         dry_run=False, raiz_hashes=tmp_path, sin_verificar=sv)

    ev = intake_log.read_events_de(case_dir)
    assert len(ev) == 1, "sin depositables, la declaración no llegó al ledger"
    assert ev[0]["details"]["count"] == 0
    assert ev[0]["details"]["sin_verificar"] == [
        {"clave": f"{PREFIJO}/volatil", "motivo": "PermissionError"}]


def test_r1_h02b_sin_incidencias_y_sin_depositables_sigue_sin_escribir_evento(tmp_path, monkeypatch):
    """El simétrico, que impide remediar H-02 ensuciando el ledger: una corrida que no
    depositó nada y no tuvo incidencias no tiene nada que declarar."""
    monkeypatch.setattr(intake_log, "read_events", lambda *a, **k: [])
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    cli._intake_generico(case_dir, "W-TEST", "drive_ev", {}, base=PREFIJO,
                         dry_run=False, raiz_hashes=tmp_path)

    assert intake_log.read_events_de(case_dir) == []


def test_r1_h07_un_fallo_del_RECUENTO_no_borra_las_incidencias_ya_conocidas(tmp_path, monkeypatch):
    """H-07 (MEDIO). `etapa_drive` contaba el destino y retornaba desde el `except` antes
    de construir los pendientes: un error al contar se llevaba por delante una declaración
    que ya venía calculada en el resultado."""
    destino = tmp_path / "00_Input" / PREFIJO
    destino.mkdir(parents=True)
    (destino / "a.pdf").write_bytes(b"x")
    res = DriveIntakeResult(
        case_id="C", team_id="T", folder_id="F", target_dir=destino, files_after=1,
        skipped=False, rclone_returncode=0, errors=[],
        custodia_sin_verificar=(
            brain.FicheroSinVerificar(clave=f"{PREFIJO}/volatil", motivo="desaparecio"),))

    def explota(*a, **k):
        raise PermissionError(13, "Permission denied", str(destino))

    monkeypatch.setattr(cli, "es_fichero_de_protocolo", explota)

    r = cli.etapa_drive(None, tmp_path, folder_id="F", team_id="T",
                        intake=lambda *a, **k: res)

    assert r.estado == "hecha"
    assert [p.codigo for p in r.pendientes] == ["custodia_sin_verificar"]


def test_r1_h08_el_pull_FALLIDO_adjunta_la_declaracion_a_la_excepcion(tmp_path, monkeypatch):
    """H-08 (MEDIO). El evento del pull fallido sí guardaba claves y motivos, pero
    `exc.result` seguía vacío, así que `etapa_drive` devolvía un fallo genérico sin decir
    qué no se pudo leer. La declaración se calculaba y se tiraba a mitad de camino."""
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    destino = case_dir / "00_Input" / PREFIJO
    destino.mkdir()
    (destino / "volatil").write_bytes(b"y")
    _renombrar_al_abrir(monkeypatch, destino / "volatil", [])

    parcial = DriveIntakeResult(
        case_id="W-TEST", team_id="T", folder_id="F", target_dir=destino, files_after=1,
        skipped=False, rclone_returncode=3, errors=["rclone: exit 3"])

    def _pull(*a, **k):
        raise cli.intake_drive.DriveIntakeError(parcial)

    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev", _pull)

    class _Ident:
        case_id = "W-TEST"

    with pytest.raises(cli.intake_drive.DriveIntakeError) as exc:
        cli._intake_drive_ev(_Ident(), case_dir, "F", "T", dry_run=False)

    assert [f.clave for f in exc.value.result.custodia_sin_verificar] == [f"{PREFIJO}/volatil"]


def test_r1_h08b_la_etapa_declara_la_custodia_tambien_cuando_el_pull_FALLA(tmp_path):
    """La otra mitad de H-08: que el dato llegue a `exc.result` no sirve de nada si la
    etapa no lo lee. Un fallo de `rclone` y ficheros ilegibles son dos hechos distintos."""
    destino = tmp_path / "00_Input" / PREFIJO
    destino.mkdir(parents=True)
    parcial = DriveIntakeResult(
        case_id="C", team_id="T", folder_id="F", target_dir=destino, files_after=0,
        skipped=False, rclone_returncode=3, errors=["rclone: exit 3"],
        custodia_sin_verificar=(
            brain.FicheroSinVerificar(clave=f"{PREFIJO}/volatil", motivo="desaparecio"),))

    def _intake(*a, **k):
        raise cli.intake_drive.DriveIntakeError(parcial)

    r = cli.etapa_drive(None, tmp_path, folder_id="F", team_id="T", intake=_intake)

    assert r.estado == "fallo"
    assert [p.codigo for p in r.pendientes] == ["custodia_sin_verificar"]
    assert "volatil" in r.pendientes[0].detalle


# --- Frontera C: el recorrido afirma más de lo que mide --------------------

def test_r1_h03_la_carrera_en_el_STAT_posterior_no_tumba_la_etapa(tmp_path):
    """H-03 (ALTO). `_inventario_desde_hashes` recompone la ruta desde la clave y hace
    `stat()`: si el montaje renombra entre el hash y el stat, la misma carrera vuelve a
    matar la etapa dos líneas después. `MEJORAS #214` nombra esta función explícitamente —
    remediar solo `hash_tree_local` dejaba la cadena a medias."""
    (tmp_path / PREFIJO).mkdir()
    (tmp_path / PREFIJO / "a.pdf").write_bytes(b"x")
    hashes = {f"{PREFIJO}/a.pdf": "sha-de-a", f"{PREFIJO}/se-fue": "sha-de-b"}

    inventario, sin_verificar = cli._inventario_desde_hashes(tmp_path, PREFIJO, hashes)

    assert [i["relpath"] for i in inventario] == ["a.pdf"]
    assert [f.clave for f in sin_verificar] == [f"{PREFIJO}/se-fue"]
    assert sin_verificar[0].motivo


def test_r1_h03b_lo_que_el_stat_pierde_llega_al_evento(tmp_path, monkeypatch):
    """Y la costura: sin esto, H-03 quedaria tolerado pero seguiria sin declararse."""
    monkeypatch.setattr(intake_log, "read_events", lambda *a, **k: [])
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    cli._intake_generico(case_dir, "W-TEST", "drive_ev",
                         {f"{PREFIJO}/se-fue": "sha"}, base=PREFIJO,
                         dry_run=False, raiz_hashes=tmp_path)

    ev = intake_log.read_events_de(case_dir)
    assert len(ev) == 1
    assert [d["clave"] for d in ev[0]["details"]["sin_verificar"]] == [f"{PREFIJO}/se-fue"]


def test_r1_h03c_un_hueco_del_stat_NO_aborta_la_apertura_como_si_sobrara(tmp_path, monkeypatch):
    """Efecto del propio remedio de H-03, encontrado al construirlo y fijado aquí.

    Al desacoplar el inventario de los hashes, la clave que el `stat` no pudo medir dejaba
    de estar en el plan pero seguia llegando a `reconcile` dentro de `hashes`: salia como
    `extra`, `ok` pasaba a False y la apertura **abortaba entera**. Un hueco declarado no
    es un sobrante — es exactamente lo contrario, y confundirlos convierte el remedio en
    una via nueva de tumbar la etapa.

    Esto tambien acota la afirmacion del handoff §3.3 («`extras` es siempre vacio porque
    `reconcile` cuadra consigo mismo»): deja de serlo en cuanto el inventario y los hashes
    pueden diferir.
    """
    monkeypatch.setattr(intake_log, "read_events", lambda *a, **k: [])
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    (tmp_path / PREFIJO).mkdir()
    (tmp_path / PREFIJO / "esta.pdf").write_bytes(b"x")
    from core.utils import file_sha256

    # Un fichero medible y otro cuya ruta ya no existe: el segundo es el hueco.
    hashes = {f"{PREFIJO}/esta.pdf": file_sha256(tmp_path / PREFIJO / "esta.pdf"),
              f"{PREFIJO}/se-fue": "sha-de-algo-que-ya-no-esta"}

    cli._intake_generico(case_dir, "W-TEST", "drive_ev", hashes, base=PREFIJO,
                         dry_run=False, raiz_hashes=tmp_path)

    detalles = intake_log.read_events_de(case_dir)[0]["details"]
    assert detalles["count"] == 1
    assert [d["clave"] for d in detalles["sin_verificar"]] == [f"{PREFIJO}/se-fue"]


def test_r1_h04_una_raiz_que_NO_SE_PUDO_MIRAR_no_es_una_raiz_vacia(tmp_path, monkeypatch):
    """H-04 (MEDIO), y es la propia frontera de esta pieza en su PRIMERA línea: `is_dir()`
    devuelve False tanto si la carpeta no existe como si no se pudo averiguar. Lo segundo
    no es cero ficheros."""
    root = _arbol(tmp_path, {"a.pdf": b"x"})
    real_stat = os.stat

    def doble(path, *a, **kw):
        if str(path) == str(root):
            raise PermissionError(13, "Permission denied", str(path))
        return real_stat(path, *a, **kw)

    monkeypatch.setattr(os, "stat", doble)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.hashes == {}
    assert [f.clave for f in arbol.sin_verificar] == [PREFIJO]


def test_r1_h04b_una_raiz_que_es_un_FICHERO_se_declara(tmp_path):
    """La otra rama del mismo booleano: un `01_Drive EV` que resulto ser un fichero es un
    destino que no se pudo recorrer, no un destino vacio."""
    root = tmp_path / PREFIJO
    root.write_bytes(b"no soy una carpeta")

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert arbol.hashes == {}
    assert [f.clave for f in arbol.sin_verificar] == [PREFIJO]


def test_r1_h04c_una_raiz_que_de_verdad_NO_EXISTE_sigue_sin_declararse(tmp_path):
    """El simetrico que impide remediar H-04 convirtiendo toda ausencia en incidencia: el
    pull que no llego a crear la carpeta no tiene ficheros sin verificar, tiene cero."""
    arbol = cli.hash_tree_local(tmp_path / "no-existe", prefijo=PREFIJO)

    assert arbol.hashes == {} and arbol.sin_verificar == ()


def test_r1_h05_un_subdirectorio_ENLAZADO_se_declara_en_vez_de_desaparecer(tmp_path):
    """H-05 (MEDIO). `os.walk` no sigue enlaces de directorio, y no seguirlos es correcto
    —los ciclos son peores—. Lo que no es correcto es no decirlo: el subarbol entero
    quedaba fuera del inventario bajo una promesa de completitud."""
    root = _arbol(tmp_path, {"visible.pdf": b"x"})
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    (fuera / "doc.pdf").write_bytes(b"y")
    try:
        (root / "enlazado").symlink_to(fuera, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:      # Windows sin privilegio
        pytest.skip(f"este entorno no crea enlaces de directorio: {exc!r}")

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert f"{PREFIJO}/visible.pdf" in arbol.hashes
    assert [f.clave for f in arbol.sin_verificar] == [f"{PREFIJO}/enlazado"]
    assert "enlace" in arbol.sin_verificar[0].motivo.lower()


# --- Frontera D: oraculos de un solo elemento y expectativas de la salida ---

def test_r1_h10_las_incidencias_viajan_TODAS_no_solo_la_primera(tmp_path, monkeypatch):
    """H-10 (MEDIO), hallazgo contra el ARNES y no contra el codigo: el mutante
    `tuple(sin_verificar[:1])` sobrevivia a los 23 tests, porque todos los oraculos tenian
    exactamente una incidencia. Un inventario truncado afirma que lo demas si se midio."""
    root = _arbol(tmp_path, {"a.pdf": b"x", "b.pdf": b"y", "c.pdf": b"z"})
    real = cli.file_sha256

    def doble(path: Path, *a, **kw):
        if path.name in ("a.pdf", "b.pdf"):
            raise PermissionError(13, "Permission denied", str(path))
        return real(path, *a, **kw)

    monkeypatch.setattr(cli, "file_sha256", doble)

    arbol = cli.hash_tree_local(root, prefijo=PREFIJO)

    assert [f.clave for f in arbol.sin_verificar] == [
        f"{PREFIJO}/a.pdf", f"{PREFIJO}/b.pdf"]
    assert list(arbol.hashes) == [f"{PREFIJO}/c.pdf"]


def test_r1_h10b_las_DOS_incidencias_llegan_enteras_al_evento(tmp_path, monkeypatch):
    """El mismo mutante, un tramo mas adelante: truncar al pasar al ledger tambien pasaba."""
    monkeypatch.setattr(intake_log, "read_events", lambda *a, **k: [])
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    sv = (brain.FicheroSinVerificar(clave=f"{PREFIJO}/a", motivo="m1"),
          brain.FicheroSinVerificar(clave=f"{PREFIJO}/b", motivo="m2"))

    cli._intake_generico(case_dir, "W-TEST", "drive_ev", {}, base=PREFIJO,
                         dry_run=False, raiz_hashes=tmp_path, sin_verificar=sv)

    detalles = intake_log.read_events_de(case_dir)[0]["details"]
    assert detalles["sin_verificar"] == [
        {"clave": f"{PREFIJO}/a", "motivo": "m1"},
        {"clave": f"{PREFIJO}/b", "motivo": "m2"}]


def test_r1_h11_el_evento_del_pull_fallido_CONSERVA_el_motivo(tmp_path, monkeypatch):
    """H-11 (MEDIO), tambien contra el arnes. A18 sacaba el motivo esperado de la propia
    salida, asi que un mutante que escribiera `motivo=""` la satisfacia. El oraculo tiene
    que venir de la ENTRADA: aqui se fija el error y se comprueba que llega intacto."""
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)
    destino = case_dir / "00_Input" / PREFIJO
    destino.mkdir()
    (destino / "bloqueado.pdf").write_bytes(b"x")
    real = cli.file_sha256
    ERROR = PermissionError(13, "el motivo exacto que tiene que sobrevivir", "bloqueado.pdf")

    def doble(path: Path, *a, **kw):
        if path.name == "bloqueado.pdf":
            raise ERROR
        return real(path, *a, **kw)

    monkeypatch.setattr(cli, "file_sha256", doble)
    parcial = DriveIntakeResult(
        case_id="W-TEST", team_id="T", folder_id="F", target_dir=destino, files_after=1,
        skipped=False, rclone_returncode=3, errors=["rclone: exit 3"])

    def _pull(*a, **k):
        raise cli.intake_drive.DriveIntakeError(parcial)

    monkeypatch.setattr(cli.intake_drive, "pull_drive_ev", _pull)

    class _Ident:
        case_id = "W-TEST"

    with pytest.raises(cli.intake_drive.DriveIntakeError):
        cli._intake_drive_ev(_Ident(), case_dir, "F", "T", dry_run=False)

    ev = intake_log.read_events_de(case_dir)[0]
    assert ev["details"]["sin_verificar"][0]["motivo"] == repr(ERROR)


# --- H-12: el aviso al operador no puede afirmar un hash que no hubo -------

def test_r1_h12_el_aviso_no_afirma_haber_hasheado_lo_que_no_se_leyo(tmp_path, monkeypatch, capsys):
    """H-12 (BAJO). `renombrados` registra que el nombre cambio —un hecho—, pero el aviso
    decia «se hasheo bajo el nombre efectivo» aunque el reaparecido fuera ilegible o
    quedara excluido por protocolo. Dos lineas despues se declaraba lo contrario."""
    monkeypatch.setattr(intake_log, "read_events", lambda *a, **k: [])
    case_dir = tmp_path / "caso"
    (case_dir / "00_Input").mkdir(parents=True)

    cli._intake_generico(
        case_dir, "W-TEST", "drive_ev", {}, base=PREFIJO, dry_run=False,
        raiz_hashes=tmp_path,
        sin_verificar=(brain.FicheroSinVerificar(
            clave=f"{PREFIJO}/x.pdf", motivo="PermissionError"),),
        renombrados=((f"{PREFIJO}/x", f"{PREFIJO}/x.pdf"),))

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert "renombr" in texto.lower()
    assert "hashe" not in texto.lower(), "afirma un hash que no ocurrio"
