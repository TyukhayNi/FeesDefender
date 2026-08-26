"""La cadena de custodia sigue el destino EFECTIVO — Plan 3A, Task 6, fila #8.

R14/H14-02 lo marcó CRÍTICO y **prohibió diferirlo a 3C**, con razón: no es cobertura
aplazada, es una afirmación forense falsa. `pull_drive_ev` deposita en el destino que
devuelve el guard —la bandeja `_pendiente_checkin/` si el caso está prestado— y
`_intake_drive_ev` hashea `case_dir / "00_Input" / subdir` **en duro**.

Medido antes de arreglarlo, los dos modos de fallo:

- si la ruta canónica **no existe**, `hash_tree_local` devuelve `{}`, el plan sale vacío y
  **no se emite ningún evento**: los bytes se depositan y la custodia no los registra;
- si **sí existe** con bytes de un pull anterior, se hashean **esos** y el evento los
  atribuye a este pull.

Y lo que hace el defecto barato de arreglar: `DriveIntakeResult` **ya trae `target_dir`**,
el destino efectivo. El llamador lo tenía delante y recomputaba la ruta intencionada.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

W = "W-CUSTO1"
CASE_ID = f"Ba001 - Calle Falsa 3 - ({W}) - honorarios"


def monta_caso(root, estado="disponible"):
    d = root / CASE_ID
    (d / "00_Input").mkdir(parents=True)
    io.open(d / "00_Input" / "_caso.md", "w", encoding="utf-8", newline="\n").write(
        "\n".join(["---", "meta:", f"  id_go: {W}",
                   f"  estado_repositorio: {estado}", "---", ""]))
    return d


def ident_de():
    """Una `Identidad` completa: el dataclass no tiene defaults, y son once campos."""
    from core.abrir_caso import Identidad
    return Identidad(
        codigo="Ba001", direccion="Calle Falsa 3", w_code=W, sufijo="honorarios",
        case_id=CASE_ID, posicion="propietario", tipo_caso="honorarios_impagados",
        w_code_duplicado=False, codigo_duplicado=False, requiere_confirmacion=False,
        colisiones=(),
    )


def _pull_falso(destino: Path, nombre: str, contenido: bytes):
    """Sustituye a `pull_drive_ev`: deposita un fichero y devuelve su destino REAL.

    No se toca rclone: lo que esta fila contrata es qué se hashea **después** del pull,
    y para eso el pull solo tiene que decir dónde dejó los bytes.
    """
    from core.intake_drive import DriveIntakeResult

    def _fake(case_id, folder_id, team_id, *, force=False):
        destino.mkdir(parents=True, exist_ok=True)
        (destino / nombre).write_bytes(contenido)
        return DriveIntakeResult(
            case_id=case_id, team_id=team_id, folder_id=folder_id,
            target_dir=destino, files_after=1, skipped=False,
        )
    return _fake


def _eventos(case_dir: Path) -> list[dict]:
    import json
    log = case_dir / "00_Input" / "_intake_log.jsonl"
    if not log.exists():
        return []
    return [json.loads(l) for l in io.open(log, encoding="utf-8") if l.strip()]



def _rutas(evento: dict) -> list[str]:
    """Las rutas de `details.files`, que es una lista de {path, sha256} y no de cadenas."""
    return [f["path"] if isinstance(f, dict) else str(f)
            for f in evento["details"]["files"]]


# --------------------------------------------------------------------------- F1

def test_f1_con_desvio_se_hashean_los_bytes_depositados(tmp_casos_root, monkeypatch):
    """F1 — el hash sigue a los bytes, no a la intención."""
    from core import intake_drive
    from scripts import abrir_caso as cli

    case_dir = monta_caso(tmp_casos_root, estado="prestado")
    bandeja = (case_dir / "_pendiente_checkin" / "drive_ev" / "00_Input"
               / intake_drive._DRIVE_EV_INPUT_SUBDIR)
    monkeypatch.setattr(intake_drive, "pull_drive_ev",
                        _pull_falso(bandeja, "escritura.pdf", b"bytes de la bandeja"))

    ident = ident_de()
    cli._intake_drive_ev(ident, case_dir, "FID", "TID", dry_run=False)

    evs = [e for e in _eventos(case_dir) if e["event"] == "pull_drive_ev"]
    assert evs, ("no se emitió evento de intake: con el desvío, los bytes se depositaron "
                 "y la custodia no los registró — el modo de fallo que midió R14")
    rutas = _rutas(evs[-1])
    assert any("escritura.pdf" in r for r in rutas), (
        f"el evento no nombra el fichero depositado: {rutas}")


# --------------------------------------------------------------------------- F2

def test_f2_no_se_atribuyen_al_pull_bytes_viejos_del_canon(tmp_casos_root, monkeypatch):
    """F2 — el otro modo de fallo, y el peor: hashear el cajón equivocado y AFIRMARLO.

    La ruta canónica lleva un fichero de un pull anterior. Si la cadena mirase ahí, el
    evento de **este** pull describiría un documento que este pull no trajo.
    """
    from core import intake_drive
    from scripts import abrir_caso as cli

    case_dir = monta_caso(tmp_casos_root, estado="prestado")
    canonico = case_dir / "00_Input" / intake_drive._DRIVE_EV_INPUT_SUBDIR
    canonico.mkdir(parents=True)
    (canonico / "viejo.pdf").write_bytes(b"de un pull anterior")

    bandeja = (case_dir / "_pendiente_checkin" / "drive_ev" / "00_Input"
               / intake_drive._DRIVE_EV_INPUT_SUBDIR)
    monkeypatch.setattr(intake_drive, "pull_drive_ev",
                        _pull_falso(bandeja, "nuevo.pdf", b"recien traido"))

    ident = ident_de()
    cli._intake_drive_ev(ident, case_dir, "FID", "TID", dry_run=False)

    evs = [e for e in _eventos(case_dir) if e["event"] == "pull_drive_ev"]
    assert evs
    ficheros = " ".join(_rutas(evs[-1]))
    assert "nuevo.pdf" in ficheros
    assert "viejo.pdf" not in ficheros, (
        "el evento atribuye a este pull un documento del canon que este pull no trajo")


# --------------------------------------------------------------------------- F3

def test_f3_sin_desvio_no_cambia_nada(tmp_casos_root, monkeypatch):
    """F3 — el control de no regresión: con el caso disponible, todo igual que antes."""
    from core import intake_drive
    from scripts import abrir_caso as cli

    case_dir = monta_caso(tmp_casos_root, estado="disponible")
    canonico = case_dir / "00_Input" / intake_drive._DRIVE_EV_INPUT_SUBDIR
    monkeypatch.setattr(intake_drive, "pull_drive_ev",
                        _pull_falso(canonico, "normal.pdf", b"camino feliz"))

    ident = ident_de()
    cli._intake_drive_ev(ident, case_dir, "FID", "TID", dry_run=False)

    evs = [e for e in _eventos(case_dir) if e["event"] == "pull_drive_ev"]
    assert evs and any("normal.pdf" in r for r in _rutas(evs[-1]))


# --------------------------------------------------------------------------- F4

def test_f4_el_inventario_resuelve_contra_la_raiz_efectiva(tmp_casos_root):
    """F4 — la pieza pura, aislada del pull.

    `_inventario_desde_hashes` calculaba el tamaño con `case_dir / "00_Input" / clave`,
    o sea reconstruía la ruta **intencionada**. Con los bytes en la bandeja eso es un
    `FileNotFoundError` o, peor, el tamaño de otro fichero.
    """
    from scripts import abrir_caso as cli

    case_dir = monta_caso(tmp_casos_root, estado="prestado")
    raiz = case_dir / "_pendiente_checkin" / "drive_ev" / "00_Input"
    (raiz / "01_Drive EV").mkdir(parents=True)
    (raiz / "01_Drive EV" / "x.pdf").write_bytes(b"12345")

    inv = cli._inventario_desde_hashes(raiz, "01_Drive EV",
                                       {"01_Drive EV/x.pdf": "deadbeef"})
    assert inv == [{"relpath": "x.pdf", "sha256": "deadbeef", "size": 5}]
