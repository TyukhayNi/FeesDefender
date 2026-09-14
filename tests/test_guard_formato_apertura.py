"""El formato del fichero de apertura vive en DOS sitios: el RUNBOOK y el lector.

Este guard los ata. Sin el, (a) de P8 es una regla escrita que nada aplica: alguien
cambia el ejemplo de la prosa, el lector deja de entenderlo, y el aviso enmudece
justo cuando mas falta hace — que es el defecto que P8 existe para cerrar.
"""

from pathlib import Path

import scripts.session_close as sc

RUNBOOK = Path(__file__).resolve().parents[1] / "docs" / "RUNBOOK_APERTURA_EXPEDIENTE.md"
MARCADOR = "<!-- formato-fichero-apertura -->"


def _bloque_de_ejemplo() -> str:
    """El primer bloque cercado que sigue al marcador, sin las vallas ni la sangria."""
    texto = RUNBOOK.read_text(encoding="utf-8")
    assert texto.count(MARCADOR) == 1, f"{MARCADOR} debe aparecer exactamente una vez"
    tras = texto.split(MARCADOR, 1)[1]
    lineas = tras.splitlines()
    inicio = next(i for i, ln in enumerate(lineas) if ln.strip().startswith("```"))
    fin = next(i for i, ln in enumerate(lineas[inicio + 1:], inicio + 1)
               if ln.strip().startswith("```"))
    cuerpo = lineas[inicio + 1:fin]
    sangria = min((len(ln) - len(ln.lstrip()) for ln in cuerpo if ln.strip()), default=0)
    return "\n".join(ln[sangria:] for ln in cuerpo) + "\n"


def test_el_ejemplo_del_runbook_lo_entiende_el_lector(tmp_path):
    (tmp_path / "2026-09-14_W-02UDC1.md").write_text(_bloque_de_ejemplo(), encoding="utf-8")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert ilegibles == [], f"el RUNBOOK y el lector han divergido: {ilegibles}"
    assert len(pendientes) == 1
    _, caso, fecha = pendientes[0]
    assert caso and fecha


def test_el_runbook_nombra_los_tres_estados():
    # Un estado que el codigo acepta y el runbook no documenta es un estado que
    # nadie usara; uno que el runbook promete y el codigo no acepta es un fichero
    # que caera en «ilegible» sin que su autor entienda por que.
    texto = RUNBOOK.read_text(encoding="utf-8")
    for estado in sorted(sc._ESTADOS_APERTURA):
        assert f"`{estado}`" in texto, f"el RUNBOOK no documenta el estado {estado}"
