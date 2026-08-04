"""Los `.zip` adjuntos dejan de ser invisibles (`MEJORAS #55.1`).

`router._EXT_OMITIDO` los excluía en bloque, y `clasificar_ruta(".zip")` los manda a
`sin_soporte` en la sala de máquina. En la muestra de `#87` eran **8 de 15** adjuntos
únicos: la mayoría del corpus de adjuntos, sin una línea de contenido.

**La advertencia de `#55.1`, y cómo se respeta.** Esa entrada avisa de que hacerlo mal es
peor que no hacerlo: si cinco correos traen cinco exports del mismo chat —«cada consultor
manda su copia»— y algo los funde, el mismo mensaje se cuenta cinco veces, y para una
cronología probatoria eso es veneno. Aquí **no se funde nada**: `adjuntos_contenido` produce
contenido POR ADJUNTO, no una cronología, así que el conteo quíntuple solo aparece si alguien
construye la línea de tiempo. Lo que se añade es que el solape sea **visible** —huella del
chat en el frontmatter y referencia cruzada entre exports del mismo caso—, que es lo que
`#55.1` dice que hoy no guarda nadie. La fusión se queda fuera, declarada.

**Enrutado por tipo de zip, no descompresión genérica** (la otra exigencia de `#55.1`): un
export de WhatsApp descomprimido a pelo deja el `_chat.txt` suelto y los media huérfanos,
perdiendo justo lo que `whatsapp_intake` sabe hacer. Se pregunta primero si trae un
`_chat.txt` parseable (`analyze`, read-only) y solo si no, descompresión acotada.

Datos SIEMPRE sintéticos: zips construidos en memoria, sin red y sin OCR real.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from core.adjuntos_contenido import router, zips


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, data in files.items():
            zf.writestr(nombre, data)
    return buf.getvalue()


_CHAT_A = (
    "8/1/24, 10:32 - Propietario: Buenos días, ¿hay ofertas?\n"
    "8/1/24, 10:35 - Consultor: Sí, dos. Te paso la hoja de encargo.\n"
    "9/1/24, 09:01 - Propietario: Recibida.\n"
).encode("utf-8")

_CHAT_B = (
    "3/2/24, 18:00 - Buscador: ¿Sigue disponible el piso?\n"
    "3/2/24, 18:04 - Consultor: Sí, agendamos visita.\n"
).encode("utf-8")


def _escribir(tmp_path: Path, nombre: str, data: bytes) -> Path:
    p = tmp_path / nombre
    p.write_bytes(data)
    return p


# ---------------------------------------------------------------------------
# El titular: un zip ya no sale "omitido"
# ---------------------------------------------------------------------------

def test_un_zip_ya_no_se_omite_en_bloque(tmp_path):
    ruta = _escribir(tmp_path, "chat.zip", _zip({"_chat.txt": _CHAT_A}))

    ext = router.extraer(ruta, "application/zip")

    assert ext.metodo != "omitido"
    assert ext.ok and ext.texto.strip()


# ---------------------------------------------------------------------------
# Export de WhatsApp
# ---------------------------------------------------------------------------

def test_un_export_de_whatsapp_se_detecta_y_trae_la_conversacion(tmp_path):
    ruta = _escribir(tmp_path, "WhatsApp Chat con Propietario.zip",
                     _zip({"_chat.txt": _CHAT_A, "IMG-001.jpg": b"\xff\xd8\xff datos"}))

    r = zips.extraer_zip(ruta)

    assert r.clase == "whatsapp"
    assert r.n_mensajes == 3
    assert "hoja de encargo" in r.texto
    assert r.huella                      # sin huella el solape es invisible
    assert "2024-01-08" in r.rango and "2024-01-09" in r.rango


def test_el_media_faltante_se_declara(tmp_path):
    """Un export «sin archivos» cita adjuntos que no vienen: eso es una laguna, y se dice."""
    chat = _CHAT_A + "9/1/24, 09:05 - Consultor: IMG-002.jpg (archivo adjunto)\n".encode("utf-8")
    ruta = _escribir(tmp_path, "chat.zip", _zip({"_chat.txt": chat}))

    r = zips.extraer_zip(ruta)

    assert "IMG-002.jpg" in r.media_faltante


def test_dos_exports_del_mismo_chat_comparten_huella(tmp_path):
    """La huella sale del PRIMER mensaje: un export posterior del mismo chat la repite."""
    a = _escribir(tmp_path, "export1.zip", _zip({"_chat.txt": _CHAT_A}))
    mas_largo = _CHAT_A + "10/1/24, 11:00 - Propietario: Firmo mañana.\n".encode("utf-8")
    b = _escribir(tmp_path, "export2.zip", _zip({"_chat.txt": mas_largo}))

    ra, rb = zips.extraer_zip(a), zips.extraer_zip(b)

    assert ra.huella == rb.huella
    assert (ra.n_mensajes, rb.n_mensajes) == (3, 4)   # y se ve cuál es más completo


def test_chats_distintos_no_comparten_huella(tmp_path):
    a = _escribir(tmp_path, "a.zip", _zip({"_chat.txt": _CHAT_A}))
    b = _escribir(tmp_path, "b.zip", _zip({"_chat.txt": _CHAT_B}))

    assert zips.extraer_zip(a).huella != zips.extraer_zip(b).huella


def test_el_router_propaga_la_huella(tmp_path):
    ruta = _escribir(tmp_path, "chat.zip", _zip({"_chat.txt": _CHAT_A}))

    ext = router.extraer(ruta, "application/zip")

    assert ext.metodo == "whatsapp_export"
    assert ext.chat_huella == zips.extraer_zip(ruta).huella


# ---------------------------------------------------------------------------
# Zip genérico: extracción acotada por el MISMO router
# ---------------------------------------------------------------------------

def test_un_zip_generico_extrae_sus_miembros_con_texto(tmp_path):
    ruta = _escribir(tmp_path, "anexos.zip", _zip({
        "clausula.txt": "Honorarios: 3 % más IVA.".encode("utf-8"),
        "nota.md": b"# Nota\n\nReconocimiento de deuda.",
    }))

    r = zips.extraer_zip(ruta)

    assert r.clase == "generico"
    nombres = {m.nombre for m in r.miembros}
    assert nombres == {"clausula.txt", "nota.md"}
    assert any("Honorarios: 3 %" in m.texto for m in r.miembros)


def test_el_texto_del_zip_generico_nombra_cada_miembro(tmp_path):
    """El lector tiene que poder atribuir cada trozo a su fichero dentro del zip."""
    ruta = _escribir(tmp_path, "anexos.zip", _zip({
        "clausula.txt": "Honorarios: 3 %.".encode("utf-8"),
        "otra.txt": "Segunda cláusula.".encode("utf-8"),
    }))

    r = zips.extraer_zip(ruta)

    assert "clausula.txt" in r.texto and "otra.txt" in r.texto
    assert "Segunda cláusula." in r.texto


def test_un_zip_dentro_de_un_zip_se_lista_pero_no_se_abre(tmp_path):
    """Profundidad 1, declarada. Sin tope, un zip malicioso es una bomba."""
    interior = _zip({"dentro.txt": b"secreto"})
    ruta = _escribir(tmp_path, "muñeca.zip", _zip({"interior.zip": interior,
                                                   "fuera.txt": b"visible"}))

    r = zips.extraer_zip(ruta)

    anidado = [m for m in r.miembros if m.nombre == "interior.zip"]
    assert anidado and anidado[0].texto == ""
    assert "no se abre" in anidado[0].nota.lower()
    assert "secreto" not in r.texto


def test_el_recorte_por_tope_de_miembros_se_declara(tmp_path, monkeypatch):
    """Nunca en silencio: un zip recortado sin avisar es contexto ausente y no declarado."""
    monkeypatch.setattr(zips, "MAX_MIEMBROS", 2)
    ruta = _escribir(tmp_path, "muchos.zip", _zip(
        {f"f{i}.txt": f"texto {i}".encode("utf-8") for i in range(5)}))

    r = zips.extraer_zip(ruta)

    assert len(r.miembros) == 2
    assert "5" in r.nota and "2" in r.nota


def test_un_miembro_demasiado_grande_se_declara_sin_leerlo(tmp_path, monkeypatch):
    monkeypatch.setattr(zips, "MAX_BYTES_MIEMBRO", 10)
    ruta = _escribir(tmp_path, "grande.zip", _zip({"enorme.txt": b"x" * 500}))

    r = zips.extraer_zip(ruta)

    m = r.miembros[0]
    assert m.texto == "" and "grande" in m.nota.lower()


# ---------------------------------------------------------------------------
# El solape, que es lo que hace seguro no fundir
# ---------------------------------------------------------------------------

def _sembrar(adj: Path, att_id: str, nombre_zip: str, data: bytes) -> str:
    """Adjunto + ficha, como los escribe `email_atomize._escribe_adjunto`."""
    base = f"2026-06-12_{Path(nombre_zip).stem}_{att_id}"
    (adj / f"{base}.zip").write_bytes(data)
    (adj / f"{base}.md").write_text(
        "# GENERADO por core.email_atomize — NO editar.\n\n"
        f"- att_id: {att_id}\n- nombre_original: {nombre_zip}\n"
        "- tipo: application/zip\n"
        f"- sha256: {att_id.lower() * 8}\n"
        "- primera_aparicion: 2026-06-12\n"
        "- mensajes: MSG-00001\n- etiquetas: []\n\n## Descripción\n\nx\n",
        encoding="utf-8")
    return base


def test_el_solape_entre_exports_del_mismo_chat_se_declara(tmp_path):
    """Dos adjuntos, el mismo chat: cada `.contenido.md` nombra al otro.

    No se funden —eso es lo que `#55.1` prohíbe—, pero callarlo sería el otro extremo: un
    LLM leyendo cinco copias creería tener cinco conversaciones distintas, y contaría cinco
    veces cada mensaje. Declararlo es lo que permite no fundir sin engañar al lector.
    """
    from core.adjuntos_contenido.pipeline import procesar_dir

    adj = tmp_path / "adjuntos"
    adj.mkdir()
    mas_largo = _CHAT_A + "10/1/24, 11:00 - Propietario: Firmo mañana.\n".encode("utf-8")
    b1 = _sembrar(adj, "ATT-00001", "chat-junio.zip", _zip({"_chat.txt": _CHAT_A}))
    b2 = _sembrar(adj, "ATT-00002", "chat-julio.zip", _zip({"_chat.txt": mas_largo}))

    procesar_dir(adj)

    md1 = (adj / f"{b1}.contenido.md").read_text(encoding="utf-8")
    md2 = (adj / f"{b2}.contenido.md").read_text(encoding="utf-8")
    assert "ATT-00002" in md1, "el primero no nombra al otro export del mismo chat"
    assert "ATT-00001" in md2
    # Y la huella viaja al frontmatter: es la llave por la que se detectó.
    assert "chat_huella: " in md1


def test_sin_otro_export_del_mismo_chat_no_se_inventa_solape(tmp_path):
    from core.adjuntos_contenido.pipeline import procesar_dir

    adj = tmp_path / "adjuntos"
    adj.mkdir()
    b1 = _sembrar(adj, "ATT-00001", "chat-a.zip", _zip({"_chat.txt": _CHAT_A}))
    _sembrar(adj, "ATT-00002", "chat-b.zip", _zip({"_chat.txt": _CHAT_B}))

    procesar_dir(adj)

    md1 = (adj / f"{b1}.contenido.md").read_text(encoding="utf-8")
    assert "ATT-00002" not in md1
    assert "chat_solape: ninguno" in md1


# ---------------------------------------------------------------------------
# Robustez
# ---------------------------------------------------------------------------

def test_un_zip_corrupto_no_lanza_y_dice_por_que(tmp_path):
    ruta = _escribir(tmp_path, "roto.zip", b"PK\x03\x04 esto no es un zip")

    ext = router.extraer(ruta, "application/zip")

    assert ext.metodo == "omitido" and ext.ok is True     # no aborta la corrida
    assert "zip" in ext.motivo.lower()


def test_el_emz_sigue_omitido(tmp_path):
    """`.emz` es un EMF comprimido —una imagen—, no un contenedor de documentos."""
    ruta = _escribir(tmp_path, "firma.emz", _zip({"x.emf": b"emf"}))

    ext = router.extraer(ruta, "image/x-emf")

    assert ext.metodo == "omitido"


def test_zip_slip_no_saca_ficheros_del_arbol(tmp_path):
    """`safe_zip_members` ya lo cubre; aquí se fija que el camino nuevo lo usa."""
    ruta = _escribir(tmp_path, "malicioso.zip",
                     _zip({"../../fuera.txt": b"no deberia salir",
                           "dentro.txt": b"legitimo"}))

    r = zips.extraer_zip(ruta)

    assert not (tmp_path.parent / "fuera.txt").exists()
    assert "legitimo" in r.texto
