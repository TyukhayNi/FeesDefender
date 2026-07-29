from __future__ import annotations

import hashlib
import json
from email.message import EmailMessage
from pathlib import Path

from core.email_atomize import pipeline as P

# --- Fixtures del corpus -----------------------------------------------------------------
# Forma MEDIDA sobre el corpus real (`_PRUEBA_98_VaRS3`, 2026-07-29): `S3 Q S Q S3`. Es decir,
# trozos de firma / cita / firma / cita / firma, y NINGUN trozo de autor entre las citas.
#
# Dos cosas que NO son adorno:
#  1. Las direcciones van como `&lt;x@y&gt;`. Con angulos literales, HTMLParser las trata como
#     etiqueta y desaparecen del texto -> la guarda G5 no veria <addr>, no se afirmaria ningun
#     remitente y el test seria vacuo.
#  2. La cabecera va DENTRO del cuerpo citado. En los casos reales el anclaje de la cita es la
#     propia firma (`_pending_parts` recoge cualquier texto), asi que no sirve para atribuir:
#     la unica via es `_cabecera_head` -> `_parse_label` sobre el cuerpo.

_F3 = ('<div class="gmail_signature"><div>Un saludo</div>'
       '<div>Nombre Sintetico</div><div>Engel y Voelkers</div></div>')
_F1 = '<div class="gmail_signature"><div>Un saludo</div></div>'

_CAB_ANA = ('De: Ana Uno &lt;ana@example.invalid&gt;<br>'
            'Enviado: viernes, 4 de julio de 2025 9:00<br>'
            'Para: dest@example.invalid<br>Asunto: Oferta<br><br>')
_CAB_BEA = ('De: Bea Dos &lt;bea@example.invalid&gt;<br>'
            'Enviado: jueves, 3 de julio de 2025 18:30<br>'
            'Para: dest@example.invalid<br>Asunto: Oferta<br><br>')

_HTML_FIRMA_ENTRE_CITAS = (
    _F3
    + f'<blockquote>{_CAB_ANA}CUERPO-DE-ANA con texto suficiente para no colapsar</blockquote>'
    + _F1
    + f'<blockquote>{_CAB_BEA}CUERPO-DE-BEA con texto suficiente para no colapsar</blockquote>'
    + _F3)

# Intercalada REAL: la forma medida de los 2 portadores sin firma (`A6 Q A3 Q A20`).
_HTML_INTERCALADA_REAL = ('<div>Respondo abajo</div><blockquote>cita uno</blockquote>'
                          '<div>Esto no lo aceptamos</div><blockquote>cita dos</blockquote>')


def _eml(mid: str, subject: str, *, fecha: str, html: str | None = None,
         texto: str = "cuerpo del portador", de: str = "car@example.invalid") -> bytes:
    """Un .eml minimo y DETERMINISTA. Con *html*, multipart/alternative texto+HTML.

    `set_boundary` no es cosmetico: sin el, la stdlib genera una frontera MIME ALEATORIA en
    cada `as_bytes()`, el sha256 del raw cambia, y ese sha entra en el frontmatter de la ficha
    (`render.py:46`), en `corpus.jsonl` y en `_registro.json` -> el golden seria inestable y
    la suite fallaria en falso. Medido: 4 serializaciones, 4 sha distintos sin esta linea, 1
    con ella.
    """
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = subject
    m["Date"] = fecha
    m["From"] = de
    m["To"] = "dest@example.invalid"
    m.set_content(texto)
    if html is not None:
        m.add_alternative(f"<html><body>{html}</body></html>", subtype="html")
        m.set_boundary(f"=====FRONTERA-FIJA-{subject.replace(' ', '-')}=====")
    return m.as_bytes()


def _corpus(src: Path) -> None:
    """Tres portadores: sin HTML, con intercalada REAL, y con firma entre citas."""
    src.mkdir(parents=True, exist_ok=True)
    (src / "2025-07-01_a.eml").write_bytes(
        _eml("<a@example.invalid>", "Sin html", fecha="Tue, 1 Jul 2025 10:00:00 +0200"))
    (src / "2025-07-02_b.eml").write_bytes(
        _eml("<b@example.invalid>", "Intercalada real",
             fecha="Wed, 2 Jul 2025 10:00:00 +0200", html=_HTML_INTERCALADA_REAL))
    (src / "2025-07-05_c.eml").write_bytes(
        _eml("<c@example.invalid>", "Firma entre citas",
             fecha="Sat, 5 Jul 2025 10:00:00 +0200", html=_HTML_FIRMA_ENTRE_CITAS))


def _frontmatter(txt: str) -> str:
    """El primer bloque `---` del .md. `render_md` concatena frontmatter y cuerpo, asi que
    buscar `capa: A` en todo el documento clasificaria como A una ficha de Capa B que citara
    un frontmatter en su cuerpo."""
    partes = txt.split("---\n", 2)
    return partes[1] if len(partes) > 2 else ""


def _capa(txt: str) -> str:
    for l in _frontmatter(txt).splitlines():
        if l.startswith("capa:"):
            return l.split(":", 1)[1].strip()
    return ""


def _hashes_capa_a(out: Path) -> dict[str, str]:
    """{nombre del .md: sha256} de las fichas cuyo FRONTMATTER dice `capa: A`."""
    res: dict[str, str] = {}
    for p in sorted((out / "mensajes").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        if _capa(txt) == "A":
            res[p.name] = hashlib.sha256(txt.encode("utf-8")).hexdigest()
    return res


# --- Test 5 del contrato: Capa A byte-identica contra un golden previo -------------------

# GOLDEN capturado con el motor ANTERIOR al arreglo de la firma (rama claude/sandwich-firma,
# base c442236). Si este dict cambia, una ficha de Capa A se ha movido: es un FALLO, no un
# golden a actualizar.
GOLDEN_CAPA_A: dict[str, str] = {
    "2025-07-01_1000_sin_html_MSG-00001.md": "9387cdd3e76e7a9375db07d41ce39798748256b9af7d49b83862ab780d48cf55",
    "2025-07-02_1000_intercalada_real_MSG-00002.md": "12bbd47d33e2eea78b55e97e07516c62b46102d392b777c4a32ba24dea385fc1",
    "2025-07-05_1000_firma_entre_citas_MSG-00003.md": "21251d2da221cfdd350b714e23ac8448ae0bbc239f1f4b5bb77380d26b5af887",
}


def test_capa_a_byte_identica_contra_golden(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    _corpus(src)
    P.atomize_dir(src, out)
    actual = _hashes_capa_a(out)
    assert actual == GOLDEN_CAPA_A, (
        "Capa A movida. Hashes actuales (pega en GOLDEN_CAPA_A SOLO si estas ANTES del "
        f"arreglo):\n{actual}")


# --- Test 6 del contrato: la traza se emite una vez, para el portador correcto -----------

def test_traza_firma_excluida_una_vez_y_sin_intercalada_no_segmentada(tmp_path):
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    _corpus(src)
    P.atomize_dir(src, out)
    cola = (out / "_revision" / "cola.md").read_text(encoding="utf-8")
    filas = [l for l in cola.splitlines() if l.startswith("| MSG-")]

    # Los MSG-id se resuelven desde el registro, NO desde la fila encontrada: derivarlos de la
    # propia traza dejaba pasar el mutante intercambiado (traza para b, `no_seg` para c), que es
    # exactamente el defecto que este test existe para matar.
    # TRAMPA: los Message-ID se guardan SIN los angulos (`.strip("<>")`) -> la llave del registro
    # es "c@example.invalid", nunca "<c@example.invalid>".
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    msg_b = reg["mensajes"]["b@example.invalid"]["id"]
    msg_c = reg["mensajes"]["c@example.invalid"]["id"]

    trazas = [l for l in filas if "firma_excluida_del_veto" in l]
    assert len(trazas) == 1, f"la traza debe emitirse UNA vez; filas: {filas}"
    assert "| info |" in trazas[0]
    assert "trozos_firma=7" in trazas[0]   # 3 + 1 + 3 lineas de firma en _HTML_FIRMA_ENTRE_CITAS
    assert trazas[0].split("|")[1].strip() == msg_c, (
        f"la traza es de OTRO portador: se esperaba {msg_c}; fila: {trazas[0]}")

    # El portador arreglado (c) deja de declararse sin segmentar; el de intercalada REAL (b)
    # sigue declarandose, porque su veto es correcto. Se fija la lista EXACTA.
    no_seg = [l.split("|")[1].strip() for l in filas if "intercalada_no_segmentada" in l]
    assert no_seg == [msg_b], (
        f"intercalada_no_segmentada debe ser exactamente [{msg_b}]; es {no_seg}")


# --- Test 4 del contrato: remitente <-> cuerpo, contra el motor real ---------------------

def test_firma_excluida_empareja_cada_remitente_con_su_cuerpo(tmp_path):
    """El portador `c.eml` cita a Ana y a Bea. Tras excluir la firma del veto, la Capa B produce
    DOS fichas y cada una debe llevar el cuerpo de SU autor. La revision adversarial construyo
    el adversario contrario (remitente literal + cuerpo de otro): esto lo mata.

    El emparejamiento es la asercion DURA: no se relaja nunca. El numero de fichas esta medido
    (2), y si el motor diera otro numero hay que entender por que antes de tocar nada."""
    src, out = tmp_path / "03_Email", tmp_path / "Emails"
    _corpus(src)
    P.atomize_dir(src, out)

    fichas = {}
    for p in sorted((out / "mensajes").glob("*.md")):
        txt = p.read_text(encoding="utf-8")
        if _capa(txt) == "B":
            de = next(l.split(":", 1)[1].strip() for l in _frontmatter(txt).splitlines()
                      if l.startswith("de:"))
            fichas[de] = txt

    # DURO: cada remitente con su cuerpo, en las dos direcciones.
    for de, marca_propia, marca_ajena in (
            ("ana@example.invalid", "CUERPO-DE-ANA", "CUERPO-DE-BEA"),
            ("bea@example.invalid", "CUERPO-DE-BEA", "CUERPO-DE-ANA")):
        assert de in fichas, f"falta la ficha B de {de}; hay: {sorted(fichas)}"
        assert marca_propia in fichas[de], f"la ficha de {de} no lleva su propio cuerpo"
        assert marca_ajena not in fichas[de], f"MISATRIBUCION: la ficha de {de} lleva {marca_ajena}"

    # Medido: exactamente estas dos, ninguna mas.
    assert set(fichas) == {"ana@example.invalid", "bea@example.invalid"}, (
        f"fichas B inesperadas: {sorted(fichas)}")

    # Y la PROCEDENCIA tambien: las dos se reconstruyeron del portador `c`, no de otro. Sin esto,
    # una procedencia equivocada pasaria el test (hallazgo de la revision adversarial).
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    msg_c = reg["mensajes"]["c@example.invalid"]["id"]
    for de, txt in fichas.items():
        assert f"reconstruido_de: {msg_c}" in _frontmatter(txt), (
            f"la ficha de {de} dice venir de otro portador; se esperaba {msg_c}")
