"""Los consumidores de `mensajes/*.md` no confunden un historial con una ficha (`MEJORAS #105`).

Estos tests existen porque el *mutation testing* los pidió: al retirar el filtro de los dos
consumidores reales **no moría ningún test**, o sea que los arreglos estaban sin cubrir. El coste
de compartir directorio y sufijo con las fichas se declaró en el §5.3-bis de la spec, y esto es
la red que impide que vuelva a morder.
"""
from __future__ import annotations

from pathlib import Path

from core.email_atomize.render import es_ficha_md


def test_es_ficha_md_distingue_la_ficha_del_historial():
    """El helper canónico: un único sitio que decide qué es una ficha. Cuando se añada un tercer
    artefacto a `mensajes/`, este es el único predicado que hay que tocar."""
    assert es_ficha_md(Path("2026-07-28_1000_asunto_MSG-00001.md")) is True
    assert es_ficha_md(Path("2026-07-28_1000_asunto_MSG-00001.historial.md")) is False
    assert es_ficha_md(Path("corpus.jsonl")) is False


def test_crosslink_no_toca_el_historial(tmp_casos_root, monkeypatch):
    """El consumidor más peligroso de los dos, y el que el informe adversarial NO vio.

    `linker.crosslink` inyecta `[[...]]` en el cuerpo y reescribe el fichero con
    `build_frontmatter`. Sobre un historial eso (1) contaminaría su bloque VERBATIM, que es su
    única razón de existir, (2) le añadiría un frontmatter que nunca tuvo, y (3) lo dejaría en
    churn perpetuo: el atomizador lo reescribe, el linker lo vuelve a contaminar. Y `rglob` sobre
    `01_Procesado` SÍ alcanza `Emails/mensajes/`.
    """
    from core import linker

    caso = tmp_casos_root / "BaXX1 - Prueba - (W-TEST99) - Vuelta"
    mensajes = caso / "01_Procesado" / "Emails" / "mensajes"
    mensajes.mkdir(parents=True)

    # Dos fichas cuyos stems son enlazables (>= 5 caracteres) y una de ellas se nombra en la otra.
    ficha_a = mensajes / "2026-07-28_1000_acuerdo-transaccional_MSG-00001.md"
    ficha_b = mensajes / "2026-07-28_1100_respuesta-al-acuerdo_MSG-00002.md"
    ficha_a.write_text("---\nmsg_id: MSG-00001\ncapa: A\n---\n\nCuerpo de la primera.\n",
                       encoding="utf-8")
    ficha_b.write_text(
        "---\nmsg_id: MSG-00002\ncapa: A\n---\n\n"
        "Veanse 2026-07-28_1000_acuerdo-transaccional_MSG-00001 y su historial.\n",
        encoding="utf-8")

    # El historial: sin frontmatter, y su verbatim NOMBRA a la otra ficha, que es justo lo que el
    # linker convertiria en un enlace si lo procesara.
    hist = mensajes / "2026-07-28_1100_respuesta-al-acuerdo_MSG-00002.historial.md"
    hist.write_text(
        "<!-- GENERADO por core.email_atomize — NO editar a mano. -->\n"
        "# Historial citado de MSG-00002 — SIN ATRIBUIR\n\n"
        "## Texto retirado (verbatim)\n\n"
        "```text\n"
        "De: Otro <otro@example.invalid>\n"
        "Se adjunta 2026-07-28_1000_acuerdo-transaccional_MSG-00001 para su revision.\n"
        "```\n",
        encoding="utf-8")
    antes = hist.read_bytes()

    linker.crosslink(caso.name)

    assert hist.read_bytes() == antes, (
        "el linker ha reescrito el historial: su bloque verbatim ya no es verbatim")
    # Y el stem del historial tampoco entra como destino de enlace en las fichas.
    assert ".historial" not in ficha_b.read_text(encoding="utf-8")
