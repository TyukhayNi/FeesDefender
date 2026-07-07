"""Tests del server MCP email_export_mcp.

TDD: tests escritos ANTES de la implementación.
Patrón: inyección de dependencias en build_server para aislar de core/ y red.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("mcp")  # el server importa mcp.server.fastmcp; skip si no está

from plugins.email_export_mcp import server as srv


# ---------------------------------------------------------------------------
# Fake report
# ---------------------------------------------------------------------------

@dataclass
class _FakeReport:
    account: str = "test@engelvoelkers.com"
    label: str = "TestLabel"
    label_id: str | None = "Label_123"
    total_in_label: int = 5
    written: int = 3
    skipped: int = 2
    attachments: int = 1
    files: list = field(default_factory=lambda: ["a.eml", "b.eml", "c.eml"])
    errors: list = field(default_factory=list)
    intake_logged: bool = True

    def resumen(self) -> str:
        return (
            f"etiqueta {self.label!r} ({self.account}): {self.total_in_label} mensajes; "
            f"{self.written} escritos, {self.skipped} ya presentes, "
            f"{self.attachments} adjuntos extraídos, {len(self.errors)} errores"
        )


def _make_mocks(tmp_path: Path, fake_report: _FakeReport | None = None, case_id: str = "CaseX"):
    """Devuelve (mock_resolve_ref, mock_email_dest_dir, mock_export_label, dest_dir)."""
    if fake_report is None:
        fake_report = _FakeReport()
    dest_dir = tmp_path / "00_Input" / "03_Email"

    mock_resolve = MagicMock(return_value=case_id)
    mock_dest = MagicMock(return_value=dest_dir)
    mock_export = MagicMock(return_value=fake_report)

    return mock_resolve, mock_dest, mock_export, dest_dir


def _build(tmp_path: Path, fake_report=None, case_id="CaseX"):
    mr, md, me, _ = _make_mocks(tmp_path, fake_report, case_id)
    return srv.build_server(_resolve_ref=mr, _email_dest_dir=md, _export_label=me), mr, md, me


# ---------------------------------------------------------------------------
# 1. Registro de tools
# ---------------------------------------------------------------------------

def test_server_registra_tool_export_label_emails(tmp_path):
    mcp, *_ = _build(tmp_path)
    tools = asyncio.run(mcp.list_tools())
    nombres = {t.name for t in tools}
    assert "export_label_emails" in nombres


# ---------------------------------------------------------------------------
# 2. Mapeo de parámetros a export_label
# ---------------------------------------------------------------------------

def test_export_label_emails_pasa_parametros_correctamente(tmp_path):
    """La tool resuelve ref→case_id, calcula dest_dir y llama a export_label
    con todos los parámetros mapeados."""
    fake_case_id = "BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta"
    fake_report = _FakeReport()
    dest_dir = tmp_path / "00_Input" / "03_Email"

    mock_resolve = MagicMock(return_value=fake_case_id)
    mock_dest = MagicMock(return_value=dest_dir)
    mock_export = MagicMock(return_value=fake_report)

    mcp = srv.build_server(_resolve_ref=mock_resolve, _email_dest_dir=mock_dest, _export_label=mock_export)

    async def _call():
        return await mcp.call_tool(
            "export_label_emails",
            {
                "ref": "W-02VND1",
                "account": "nikolai@engelvoelkers.com",
                "label": "01. CONTING/BaRS1",
                "extraer_adjuntos": True,
                "workers": 4,
                "force": True,
            },
        )

    asyncio.run(_call())

    mock_resolve.assert_called_once_with("W-02VND1")
    mock_dest.assert_called_once_with(fake_case_id)
    mock_export.assert_called_once_with(
        "nikolai@engelvoelkers.com",
        "01. CONTING/BaRS1",
        dest_dir,
        case_id=fake_case_id,
        extract_attachments=True,
        max_workers=4,
        force=True,
    )


# ---------------------------------------------------------------------------
# 3. Serialización del informe
# ---------------------------------------------------------------------------

def test_export_label_emails_devuelve_informe_serializado(tmp_path):
    """El resultado incluye resumen con written, label y destino."""
    fake_report = _FakeReport(written=7, label="EtiquetaX")
    dest_dir = tmp_path / "00_Input" / "03_Email"

    mcp = srv.build_server(
        _resolve_ref=MagicMock(return_value="CaseX"),
        _email_dest_dir=MagicMock(return_value=dest_dir),
        _export_label=MagicMock(return_value=fake_report),
    )

    async def _call():
        return await mcp.call_tool(
            "export_label_emails",
            {"ref": "W-99", "account": "test@engelvoelkers.com", "label": "EtiquetaX"},
        )

    result = asyncio.run(_call())
    text = result[0].text if hasattr(result[0], "text") else str(result[0])
    assert "7" in text           # written
    assert "EtiquetaX" in text
    assert "destino" in text


# ---------------------------------------------------------------------------
# 4. Propagación de errores de resolve_ref
# ---------------------------------------------------------------------------

def test_export_label_emails_propaga_error_ref_no_encontrada(tmp_path):
    """Si resolve_ref lanza ValueError, la tool lo relanza sin silenciarlo."""
    mcp = srv.build_server(
        _resolve_ref=MagicMock(side_effect=ValueError("ref no encontrada: W-XXXXX")),
        _email_dest_dir=MagicMock(),
        _export_label=MagicMock(),
    )

    async def _call():
        return await mcp.call_tool(
            "export_label_emails",
            {"ref": "W-XXXXX", "account": "test@engelvoelkers.com", "label": "Test"},
        )

    with pytest.raises(Exception, match="ref no encontrada"):
        asyncio.run(_call())


# ---------------------------------------------------------------------------
# 5. Parámetros opcionales con defaults
# ---------------------------------------------------------------------------

def test_export_label_emails_defaults_opcionales(tmp_path):
    """extraer_adjuntos/workers/force usan sus defaults cuando no se pasan."""
    dest_dir = tmp_path / "dest"
    mock_export = MagicMock(return_value=_FakeReport())

    mcp = srv.build_server(
        _resolve_ref=MagicMock(return_value="CaseX"),
        _email_dest_dir=MagicMock(return_value=dest_dir),
        _export_label=mock_export,
    )

    async def _call():
        return await mcp.call_tool(
            "export_label_emails",
            {"ref": "W-99999", "account": "test@engelvoelkers.com", "label": "L"},
        )

    asyncio.run(_call())

    _, kwargs = mock_export.call_args
    assert kwargs["extract_attachments"] is False
    assert kwargs["max_workers"] == 8
    assert kwargs["force"] is False


# ---------------------------------------------------------------------------
# 6. Informe con errores parciales se serializa sin explotar
# ---------------------------------------------------------------------------

def test_export_label_emails_informe_con_errores(tmp_path):
    """Cuando hay errores parciales, se incluyen en el output (sin excepción)."""
    fake_report = _FakeReport(
        written=1,
        errors=["msg001: timeout", "msg002: decode error"],
        intake_logged=False,
    )
    dest_dir = tmp_path / "dest"

    mcp = srv.build_server(
        _resolve_ref=MagicMock(return_value="CaseX"),
        _email_dest_dir=MagicMock(return_value=dest_dir),
        _export_label=MagicMock(return_value=fake_report),
    )

    async def _call():
        return await mcp.call_tool(
            "export_label_emails",
            {"ref": "W-1", "account": "test@engelvoelkers.com", "label": "L"},
        )

    result = asyncio.run(_call())
    text = result[0].text if hasattr(result[0], "text") else str(result[0])
    assert "errores" in text
    assert "timeout" in text
