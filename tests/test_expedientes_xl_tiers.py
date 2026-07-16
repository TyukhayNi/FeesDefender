from pathlib import Path
import pytest
from plugins.expedientes_xl.tiers import (
    Tier, Zonas, classify, es_backup, PROTOCOL_EDIT, PROTOCOL_APPEND,
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
