from pathlib import Path
import pytest
from plugins.expedientes_xl.tiers import (
    Tier, TierViolation, Zonas, check_read, check_write, classify, es_backup,
    PROTOCOL_EDIT, PROTOCOL_APPEND,
)

Z = Zonas(rw_roots=(Path("G:/"),), ro_roots=(Path("H:/"),))

@pytest.mark.parametrize("ruta,tier", [
    (r"G:\CASOS\BaX\90_Notas personales\nota.md", Tier.PROHIBIDA),
    (r"G:\CASOS\BaX\90_NOTAS_PERSONALES\nota.md", Tier.PROHIBIDA),
    (r"G:\CASOS\BaX\00_Input\03_Email\m.eml", Tier.FORENSE),
    (r"G:\CASOS\BaX\00_Input\90_Notas personales\x", Tier.PROHIBIDA),  # Tier 0 gana
    (r"G:\Otros ordenadores\PC\doc.txt", Tier.FORENSE),
    (r"G:\Unidades compartidas\BACKUP\z.zip", Tier.FORENSE),
    (r"H:\Unidades compartidas\BACKUP MADRID\z", Tier.FORENSE),
    (r"G:\CASOS\BaX\01_Procesado\doc.md", Tier.WORKSPACE),
    (r"H:\Mi unidad\doc.pdf", Tier.WORKSPACE),
])
def test_classify(ruta, tier):
    assert classify(Z, Path(ruta)) is tier

def test_es_backup_distingue_de_00input():
    assert es_backup(Z, Path(r"G:\Otros ordenadores\PC\a")) is True
    assert es_backup(Z, Path(r"G:\CASOS\BaX\00_Input\a")) is False

def test_carveout_espeja_merge_exclusions():
    from core.config import MERGE_EXCLUSIONS  # el test SÍ puede importar core
    core_files = {e for e in MERGE_EXCLUSIONS if "/" not in e}
    assert set(PROTOCOL_EDIT) | set(PROTOCOL_APPEND) == core_files


def test_check_read_bloquea_tier0():
    with pytest.raises(TierViolation):
        check_read(Z, Path(r"G:\CASOS\BaX\90_Notas personales\n.md"))
    check_read(Z, Path(r"G:\CASOS\BaX\00_Input\d.pdf"))  # Tier 1 se lee


def test_check_write_ro_root():
    with pytest.raises(TierViolation, match="solo-lectura"):
        check_write(Z, Path(r"H:\Mi unidad\x.txt"), exists=False)


def test_check_write_00input_crear_nuevo_ok():
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\04_Manual\nuevo.pdf"), exists=False)


def test_check_write_00input_sobrescribir_rechazado():
    with pytest.raises(TierViolation):
        check_write(Z, Path(r"G:\CASOS\BaX\00_Input\04_Manual\viejo.pdf"), exists=True)


def test_check_write_carveout_protocolo():
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\_caso.md"), exists=True)          # edit
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\_intake_log.jsonl"), exists=True, append=True)
    check_write(Z, Path(r"G:\CASOS\BaX\00_Input\AUDITLOG_MERGE_x.jsonl"), exists=True, append=True)
    with pytest.raises(TierViolation):  # el log NO es editable, solo append
        check_write(Z, Path(r"G:\CASOS\BaX\00_Input\_intake_log.jsonl"), exists=True)


def test_check_write_backup_sin_carveout():
    with pytest.raises(TierViolation):
        check_write(Z, Path(r"G:\Otros ordenadores\PC\_caso.md"), exists=True)
    with pytest.raises(TierViolation):  # ni crear-nuevo en backup
        check_write(Z, Path(r"G:\Unidades compartidas\BACKUP\n.txt"), exists=False)


def test_check_write_workspace_permitido():
    # Tier 2 (WORKSPACE) bajo rw_root: escritura permitida, exista o no el destino
    check_write(Z, Path(r"G:\CASOS\BaX\01_Procesado\doc.md"), exists=True)
    check_write(Z, Path(r"G:\CASOS\BaX\01_Procesado\doc.md"), exists=False)


def test_check_write_bloquea_tier0():
    with pytest.raises(TierViolation):
        check_write(Z, Path(r"G:\CASOS\BaX\90_Notas personales\n.md"), exists=False)
