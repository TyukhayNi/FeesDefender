"""Tests de core.intake_utils."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from core.intake_utils import (
    decode_base64url,
    safe_zip_extract,
    safe_zip_members,
    sanitize_filename,
)


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilenameFile:
    def test_chars_prohibidos_reemplazados_por_guion(self):
        assert sanitize_filename('test:file*name?.pdf') == "test_file_name_.pdf"

    def test_string_limpio_intacto(self):
        nombre = "2026-06-12 - Auto - nombramiento.pdf"
        assert sanitize_filename(nombre) == nombre

    def test_control_chars_eliminados(self):
        assert sanitize_filename("doc\x00\x1fname.pdf") == "doc__name.pdf"

    def test_puntos_extremos_eliminados(self):
        assert sanitize_filename("...doc.pdf...") == "doc.pdf"

    def test_vacio_devuelve_fallback(self):
        assert sanitize_filename("", fallback="archivo") == "archivo"
        # tres dos puntos → tres underscores (no se colapsan)
        assert sanitize_filename(":::") == "___"

    def test_slash_reemplazado(self):
        assert sanitize_filename("a/b\\c") == "a_b_c"


class TestSanitizeFilenameFolder:
    def test_dotdot_reemplazado(self):
        # ".." (dos dots) se reemplaza por UN underscore
        assert sanitize_filename("chat..backup", mode="folder") == "chat_backup"

    def test_chars_prohibidos_reemplazados(self):
        assert sanitize_filename("mi:chat?", mode="folder") == "mi_chat_"

    def test_zip_extension_no_afecta(self):
        # mode="folder" no hace strip de .zip — eso es responsabilidad del caller
        result = sanitize_filename("WhatsApp Chat.zip", mode="folder")
        assert result == "WhatsApp Chat.zip"


class TestSanitizeFilenameSegment:
    def test_chars_prohibidos_reemplazados_por_espacio(self):
        out = sanitize_filename('BaRS1 - "Vuelta" / Test', mode="segment")
        assert ":" not in out and "/" not in out and '"' not in out

    def test_acentos_preservados(self):
        assert sanitize_filename("Nº 12 - José", mode="segment") == "Nº 12 - José"

    def test_string_limpio_intacto(self):
        s = "BaRS1 - [inmueble] (W-02VND1)"
        assert sanitize_filename(s, mode="segment") == s


# ---------------------------------------------------------------------------
# decode_base64url
# ---------------------------------------------------------------------------


class TestDecodeBase64url:
    def test_decodifica_str(self):
        import base64
        texto = "Hola mundo"
        encoded = base64.urlsafe_b64encode(texto.encode()).decode().rstrip("=")
        assert decode_base64url(encoded) == texto

    def test_decodifica_bytes(self):
        import base64
        data = b"\x00\x01\x02\xff"
        encoded = base64.urlsafe_b64encode(data).decode().rstrip("=")
        assert decode_base64url(encoded, as_bytes=True) == data

    def test_padding_tolerante(self):
        # Sin ningún '=' al final debe funcionar igual
        import base64
        texto = "test"
        encoded = base64.urlsafe_b64encode(texto.encode()).decode()
        sin_pad = encoded.rstrip("=")
        assert decode_base64url(sin_pad) == texto

    def test_vacio_devuelve_vacio(self):
        assert decode_base64url("") == ""
        assert decode_base64url("", as_bytes=True) == b""


# ---------------------------------------------------------------------------
# safe_zip_members
# ---------------------------------------------------------------------------


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


class TestSafeZipMembers:
    def test_extrae_ficheros_normales(self):
        content = _make_zip({"_chat.txt": b"hola", "foto.jpg": b"\xff\xd8"})
        members = safe_zip_members(content)
        assert set(members) == {"_chat.txt", "foto.jpg"}
        assert members["_chat.txt"] == b"hola"

    def test_ignora_directorios(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.mkdir("subdir")
            zf.writestr("subdir/foto.jpg", b"\xff")
        members = safe_zip_members(buf.getvalue())
        assert "foto.jpg" in members
        assert "subdir/" not in members

    def test_ignora_path_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../evil.py", b"malware")
            zf.writestr("ok.txt", b"safe")
        members = safe_zip_members(buf.getvalue())
        assert "evil.py" not in members and "../evil.py" not in members
        assert "ok.txt" in members

    def test_nombre_base_sin_subdirectorio(self):
        content = _make_zip({"sub/nested/doc.pdf": b"%PDF"})
        members = safe_zip_members(content)
        assert "doc.pdf" in members


# ---------------------------------------------------------------------------
# safe_zip_extract
# ---------------------------------------------------------------------------


class TestSafeZipExtract:
    def test_extrae_preservando_estructura(self, tmp_path):
        content = _make_zip({"a/b.txt": b"hola", "c.txt": b"mundo"})
        extracted = safe_zip_extract(content, tmp_path)
        assert (tmp_path / "a" / "b.txt").read_bytes() == b"hola"
        assert (tmp_path / "c.txt").read_bytes() == b"mundo"
        assert len(extracted) == 2

    def test_rechaza_path_traversal(self, tmp_path):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../evil.py", b"malo")
            zf.writestr("ok.txt", b"bueno")
        extracted = safe_zip_extract(buf.getvalue(), tmp_path)
        assert not (tmp_path.parent / "evil.py").exists()
        assert (tmp_path / "ok.txt").exists()
        assert len(extracted) == 1

    def test_idempotente(self, tmp_path):
        content = _make_zip({"doc.txt": b"contenido"})
        e1 = safe_zip_extract(content, tmp_path)
        e2 = safe_zip_extract(content, tmp_path)
        assert len(e1) == len(e2) == 1
        assert (tmp_path / "doc.txt").read_bytes() == b"contenido"
