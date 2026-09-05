"""Ruta `ofimatica` de la sala de máquina (acción 10 del informe de Codex sobre el alta, `MEJORAS #61`).

Contrato bajo prueba:
- O1  `.doc`/`.odt`/`.ppt`/`.pptx` van a `ofimatica`; `.docx`/`.rtf` siguen en `nativo`.
- O2  `localizar_soffice` honra `FEESDEFENDER_SOFFICE` y devuelve `None` (no lanza) sin binario.
- O3  `convertir` verifica POR RESULTADO: un `soffice` que sale 0 sin escribir PDF es fallo.
- O4  `convertir` deja el PDF en `dst` cuando el conversor produce `<stem>.pdf` en `--outdir`.
- O5  `ejecutar`: PDF convertido con texto → persistido en `01_OCR/`, MD escrito, método `ofimatica`.
- O6  `ejecutar` sin LibreOffice → fila `sin_soporte` CON la causa («soffice») en la nota.
- O7  `ejecutar` con conversión fallida → `sin_soporte` con «conversión a PDF falló».
- O8  `ejecutar`: PDF convertido SIN capa de texto → baja a la escalera de OCR.
- O9  Los COMANDOS `plan` y `apply` cuentan `ofimatica` y avisan en alto si falta el conversor.
- O11 `preflight_manifiestos` mira también los bundles ofimáticos (R1/H-01).
- O12 `reforzar` selecciona un convertido dudoso (R1/H-02).
- O13 Si publicar el buscable falla, no queda un PDF mudo en `01_OCR/` (R1/H-03).
- O10 (slow) LibreOffice REAL convierte el `.doc` de fixtures y el MD contiene su texto.
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from core import ofimatica_a_pdf as ofi
from core import sala_maquina as sm
from core.anon.ocr import ResultadoEscalera
from core.utils import file_sha256

FIXTURE_DOC = Path(__file__).parent / "_fixtures" / "ofimatica" / "encargo_prueba.doc"
TEXTO_LARGO = ("Encargo de mediación firmado por el propietario. Honorarios de intermediación "
               "del cinco por ciento sobre el precio final de la operación. ")


def _pdf_con_texto(path: Path, texto: str = TEXTO_LARGO) -> None:
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, texto)
    c.showPage()
    c.save()


def _caso(tmp_path: Path, nombre: str = "encargo.doc") -> tuple[Path, Path, sm.DocPlan]:
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / nombre
    src.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64)   # firma OLE2 de un .doc
    sha = file_sha256(src)
    ext = Path(nombre).suffix
    d = sm.DocPlan(rel_path=f"01_Drive EV/{nombre}", sha256=sha, ext=ext,
                   ruta=sm.clasificar_ruta(ext), slug=f"encargo__{sha[:8]}")
    return case, src, d


def _soffice_falso(tmp_path: Path, cuerpo: str) -> Path:
    """Un `soffice` de mentira: script Python invocado con los mismos argumentos."""
    script = tmp_path / "soffice_falso.py"
    script.write_text(
        "import sys, os\n"
        "args = sys.argv[1:]\n"
        "outdir = args[args.index('--outdir') + 1]\n"
        "src = args[-1]\n"
        "stem = os.path.splitext(os.path.basename(src))[0]\n"
        + cuerpo, encoding="utf-8")
    if os.name == "nt":
        lanzador = tmp_path / "soffice_falso.cmd"
        lanzador.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="ascii")
    else:
        lanzador = tmp_path / "soffice_falso"
        lanzador.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="ascii")
        lanzador.chmod(lanzador.stat().st_mode | stat.S_IXUSR)
    return lanzador


# ── O1 ─────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ext", [".doc", ".DOC", ".dot", ".odt", ".ott", ".ppt", ".pps", ".pptx", ".odp"])
def test_o1_ofimatica_por_extension(ext):
    assert sm.clasificar_ruta(ext) == "ofimatica"


@pytest.mark.parametrize("ext,ruta", [(".docx", "nativo"), (".rtf", "nativo"), (".pdf", "pdf"),
                                      (".jpg", "imagen"), (".mp4", "sin_soporte")])
def test_o1_las_demas_rutas_no_cambian(ext, ruta):
    assert sm.clasificar_ruta(ext) == ruta


def test_o1_plan_enruta_un_doc_a_ofimatica(tmp_path):
    case, _src, d = _caso(tmp_path)
    inventario = sm.inventariar(case)
    p = sm.plan(inventario, set())
    assert [x.ruta for x in p] == ["ofimatica"]
    assert p[0].slug == d.slug


# ── O2 ─────────────────────────────────────────────────────────────────────────────────

def test_o2_localizar_honra_la_variable_y_no_inventa(tmp_path, monkeypatch):
    binario = tmp_path / "mi_soffice.exe"
    binario.write_bytes(b"x")
    monkeypatch.setenv(ofi.ENV_SOFFICE, str(binario))
    assert ofi.localizar_soffice() == binario
    # La variable apunta a algo que no existe: `None`, no el PATH ni la ruta de Windows.
    monkeypatch.setenv(ofi.ENV_SOFFICE, str(tmp_path / "no_existe.exe"))
    assert ofi.localizar_soffice() is None


def test_o2_sin_binario_devuelve_none_sin_lanzar(tmp_path, monkeypatch):
    monkeypatch.delenv(ofi.ENV_SOFFICE, raising=False)
    monkeypatch.setattr(ofi.shutil, "which", lambda *_a, **_k: None)
    monkeypatch.setattr(ofi, "_RUTAS_WINDOWS", (tmp_path / "nada" / "soffice.exe",))
    assert ofi.localizar_soffice() is None


# ── O3 / O4 ────────────────────────────────────────────────────────────────────────────

def test_o3_convertir_verifica_por_resultado_no_por_rc(tmp_path):
    """soffice sale 0 y no escribe nada (perfil bloqueado, filtro ausente): es FALLO."""
    falso = _soffice_falso(tmp_path, "print('convert ... -> nada'); sys.exit(0)\n")
    src = tmp_path / "carta.doc"
    src.write_bytes(b"doc")
    with pytest.raises(ofi.ConversionFallida, match="sin producir PDF"):
        ofi.convertir(src, tmp_path / "out" / "carta.pdf", soffice=falso)
    assert not (tmp_path / "out" / "carta.pdf").exists()


def test_o3_convertir_pdf_vacio_tambien_es_fallo(tmp_path):
    falso = _soffice_falso(tmp_path, "open(os.path.join(outdir, stem + '.pdf'), 'wb').close()\n")
    src = tmp_path / "carta.doc"
    src.write_bytes(b"doc")
    with pytest.raises(ofi.ConversionFallida):
        ofi.convertir(src, tmp_path / "carta.pdf", soffice=falso)


def test_o3_sin_conversor_lanza_no_disponible(tmp_path, monkeypatch):
    monkeypatch.setattr(ofi, "localizar_soffice", lambda: None)
    with pytest.raises(ofi.ConversorNoDisponible, match="soffice"):
        ofi.convertir(tmp_path / "x.doc", tmp_path / "x.pdf")


def test_o4_convertir_deja_el_pdf_en_destino(tmp_path):
    # Los asertos van ANTES de escribir: un soffice falso que escribiera y luego fallara
    # daría un PDF válido y `convertir` (que verifica por resultado) lo daría por bueno.
    falso = _soffice_falso(
        tmp_path,
        "assert any(a.startswith('-env:UserInstallation=file:') for a in args), args\n"
        "assert '--headless' in args\n"
        "open(os.path.join(outdir, stem + '.pdf'), 'wb').write(b'%PDF-1.4 convertido')\n")
    src = tmp_path / "carta.doc"
    src.write_bytes(b"doc")
    dst = tmp_path / "sala" / "carta__abc.pdf"
    assert ofi.convertir(src, dst, soffice=falso) == dst
    assert dst.read_bytes().startswith(b"%PDF-1.4 convertido")


# ── O5 / O6 / O7 / O8 ──────────────────────────────────────────────────────────────────

def _no_ocr(*_a, **_k):
    raise AssertionError("no debe OCR-izar un PDF convertido con capa de texto")


def test_o5_doc_convertido_con_texto_persiste_pdf_y_md(tmp_path, monkeypatch):
    case, _src, d = _caso(tmp_path)

    def _convertir(src, dst, **_k):
        _pdf_con_texto(Path(dst))
        return Path(dst)

    monkeypatch.setattr(sm, "convertir_ofimatica", _convertir)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _no_ocr)
    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")

    sm_dir = case / "01_Procesado" / "02_Sala de máquina"
    assert (sm_dir / "01_OCR" / f"{d.slug}.pdf").exists(), "el PDF buscable es la custodia"
    md = sm_dir / "03_MD" / f"{d.slug}.md"
    assert "Honorarios" in md.read_text(encoding="utf-8")
    assert len(cob) == 1
    assert cob[0].metodo == "ofimatica" and cob[0].estado == "ok" and cob[0].ocr is False
    assert "LibreOffice" in cob[0].nota and "01_OCR" in cob[0].nota


def test_o6_sin_libreoffice_la_fila_dice_por_que(tmp_path, monkeypatch):
    case, _src, d = _caso(tmp_path)

    def _sin_conversor(src, dst, **_k):
        raise ofi.ConversorNoDisponible("LibreOffice (soffice) no encontrado: instálalo")

    monkeypatch.setattr(sm, "convertir_ofimatica", _sin_conversor)
    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")
    assert cob[0].estado == "sin_soporte" and cob[0].metodo == "sin_soporte"
    assert "soffice" in cob[0].nota, "la causa tiene que leerse en _cobertura.md"
    assert "sin soporte para esta extensión" not in cob[0].nota
    # y nada se escribió como si hubiera ido bien (ni MD ni PDF; la carpeta 01_OCR la crea
    # el conversor, que aquí no llegó a correr)
    sm_dir = case / "01_Procesado" / "02_Sala de máquina"
    assert not (sm_dir / "03_MD").exists()
    assert not list((sm_dir / "01_OCR").glob("*")) if (sm_dir / "01_OCR").exists() else True


def test_o7_conversion_fallida_no_tumba_el_lote(tmp_path, monkeypatch):
    """UN lote, DOS documentos del mismo caso: el primero falla al convertir, el segundo debe
    procesarse igual (R1/H-05: la versión anterior usaba dos `ejecutar` independientes y un
    `return` tras el fallo sobrevivía)."""
    case, _src, d_mal = _caso(tmp_path)
    src2 = case / "00_Input" / "01_Drive EV" / "segundo.odt"
    src2.write_bytes(b"PK\x03\x04" + b"\x00" * 32)
    sha2 = file_sha256(src2)
    d_bien = sm.DocPlan(rel_path="01_Drive EV/segundo.odt", sha256=sha2, ext=".odt",
                        ruta=sm.clasificar_ruta(".odt"), slug=f"segundo__{sha2[:8]}")
    llamadas = []

    def _convertir(src, dst, **_k):
        llamadas.append(Path(src).name)
        if Path(src).suffix == ".doc":
            raise ofi.ConversionFallida("soffice terminó (rc=0) sin producir PDF")
        _pdf_con_texto(Path(dst))
        return Path(dst)

    monkeypatch.setattr(sm, "convertir_ofimatica", _convertir)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _no_ocr)
    cob = sm.ejecutar(case, [d_mal, d_bien], case_id="EV-2026-001")
    assert llamadas == ["encargo.doc", "segundo.odt"], "el segundo tiene que intentarse"
    por_slug = {c.slug: c for c in cob}
    assert por_slug[d_mal.slug].estado == "sin_soporte"
    assert "conversión a PDF falló" in por_slug[d_mal.slug].nota
    assert por_slug[d_bien.slug].estado == "ok" and por_slug[d_bien.slug].metodo == "ofimatica"
    sm_dir = case / "01_Procesado" / "02_Sala de máquina"
    assert (sm_dir / "01_OCR" / f"{d_bien.slug}.pdf").exists()
    assert not (sm_dir / "01_OCR" / f"{d_mal.slug}.pdf").exists()


def test_o8_doc_que_envuelve_un_escaneo_baja_a_la_escalera(tmp_path, monkeypatch):
    case, _src, d = _caso(tmp_path)

    def _convertir(src, dst, **_k):
        Path(dst).write_bytes(b"%PDF-1.4\n% sin capa de texto\n")
        return Path(dst)

    def _fake_ocr(entrada, salida, **_k):
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_bytes(b"%PDF buscable")
        return ResultadoEscalera(Path(salida), "redo")

    monkeypatch.setattr(sm, "convertir_ofimatica", _convertir)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _fake_ocr)
    # El convertido vive en 01_OCR y NO tiene texto; el buscable que deja la escalera (mismo
    # destino) sí. Se distingue por contenido, no por ruta.
    monkeypatch.setattr(sm, "_try_pypdf",
                        lambda p: TEXTO_LARGO * 2 if Path(p).read_bytes().startswith(b"%PDF buscable") else "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    monkeypatch.setattr(sm, "_paginas_ciegas", lambda p: [])
    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")
    assert cob[0].metodo == "ocr" and cob[0].ocr is True and cob[0].estado == "ok"
    assert "LibreOffice antes del OCR" in cob[0].nota
    assert (case / "01_Procesado" / "02_Sala de máquina" / "01_OCR" / f"{d.slug}.pdf").exists()


def test_o8b_si_la_escalera_falla_no_queda_un_pdf_mudo_en_01_ocr(tmp_path, monkeypatch):
    """El convertido sin texto se APARTA antes del OCR: si la escalera revienta, en `01_OCR/`
    no puede quedar un PDF sin capa de texto haciéndose pasar por buscable."""
    case, _src, d = _caso(tmp_path)

    def _convertir(src, dst, **_k):
        Path(dst).write_bytes(b"%PDF-1.4\n% sin capa de texto\n")
        return Path(dst)

    def _ocr_revienta(entrada, salida, **_k):
        raise RuntimeError("ocrmypdf ausente")

    monkeypatch.setattr(sm, "convertir_ofimatica", _convertir)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _ocr_revienta)
    monkeypatch.setattr(sm, "_try_pypdf", lambda p: "")
    monkeypatch.setattr(sm, "_pdf_num_paginas", lambda p: 1)
    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")
    assert cob[0].estado == "empty" and "OCR falló" in cob[0].nota
    assert not (case / "01_Procesado" / "02_Sala de máquina" / "01_OCR" / f"{d.slug}.pdf").exists()


# ── O9 ─────────────────────────────────────────────────────────────────────────────────

def test_o9_el_cli_cuenta_ofimatica_y_avisa_sin_conversor(tmp_path, monkeypatch, capsys):
    import scripts.sala_maquina as cli
    case, _src, d = _caso(tmp_path)
    monkeypatch.setattr(ofi, "localizar_soffice", lambda: None)
    n = cli._avisar_ofimatica_sin_conversor([d])
    err = capsys.readouterr().err
    assert n == 1 and "soffice" in err and ofi.ENV_SOFFICE in err
    # con conversor no hay ruido
    monkeypatch.setattr(ofi, "localizar_soffice", lambda: Path("soffice"))
    assert cli._avisar_ofimatica_sin_conversor([d]) == 0
    assert capsys.readouterr().err == ""
    # y sin documentos ofimáticos, tampoco (aunque falte el conversor)
    monkeypatch.setattr(ofi, "localizar_soffice", lambda: None)
    pdf = sm.DocPlan("a.pdf", "0" * 64, ".pdf", "pdf", "a__00000000")
    assert cli._avisar_ofimatica_sin_conversor([pdf]) == 0
    assert capsys.readouterr().err == "", "sin documentos ofimáticos no hay nada que avisar"


def _cablear_cli(monkeypatch, case):
    """Idiom del repo (tests/test_sala_maquina_generacion.py::_caso): se doblan las
    dependencias externas del CLI; las DOS ligaduras de `append_event`."""
    import scripts.sala_maquina as cli
    monkeypatch.setattr(cli, "caso_path", lambda cid: case)
    monkeypatch.setattr(cli, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(sm, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    monkeypatch.setattr(cli.case_locator, "resolve_ref", lambda ref: ref)
    return cli


def test_o9_los_comandos_plan_y_apply_avisan_sin_conversor(tmp_path, monkeypatch, capsys):
    """Son los COMANDOS los que deben avisar, no solo el helper: un `pass` en la llamada
    (M2 del revisor) tiene que ponerse rojo aquí."""
    case, _src, d = _caso(tmp_path)
    cli = _cablear_cli(monkeypatch, case)
    monkeypatch.setattr(ofi, "localizar_soffice", lambda: None)

    cli.plan("W-TEST99")
    out, err = capsys.readouterr()
    assert "ofimatica: 1" in out, out
    assert "soffice" in err and ofi.ENV_SOFFICE in err, err

    def _sin_conversor(src, dst, **_k):
        raise ofi.ConversorNoDisponible("LibreOffice (soffice) no encontrado")
    monkeypatch.setattr(sm, "convertir_ofimatica", _sin_conversor)
    cli.apply("W-TEST99")
    out, err = capsys.readouterr()
    assert "soffice" in err, "apply debe avisar ANTES de procesar"
    cob = cli._cobertura_previa(case)
    assert [c.estado for c in cob if c.slug == d.slug] == ["sin_soporte"]
    assert "soffice" in [c.nota for c in cob if c.slug == d.slug][0]


def test_o9_el_preview_lista_la_ruta_ofimatica():
    """Guard textual barato: el preview enumera las rutas a mano; una ruta nueva que no
    aparezca ahí saldría del recuento y `plan` diría menos documentos de los que `apply`
    procesará."""
    src = (Path(__file__).parent.parent / "scripts" / "sala_maquina.py").read_text(encoding="utf-8")
    assert '"ofimatica", "sin_soporte"' in src


# ── O11 / O12 / O13 (R1 de Codex: H-01, H-02, H-03) ─────────────────────────────────────

def test_o11_el_preflight_tambien_mira_los_bundles_ofimaticos(tmp_path):
    """R1/H-01: `preflight_manifiestos` solo miraba `pdf` e `imagen`; un manifiesto inválido
    (o una permutación de `pp`) en el bundle de un `.doc` se publicaba sin aviso."""
    from dataclasses import replace
    from core import split_documental as split
    case, _src, d = _caso(tmp_path)
    carpeta = sm.carpeta_bundle_de(case, d.slug)
    carpeta.mkdir(parents=True, exist_ok=True)
    split.escribir_manifiesto(carpeta, {
        "fuente": d.rel_path, "bundle_sha256": "a" * 64, "delimitadores": [],
        "segmentos": [{"seg": 1, "pp": "1-1", "tipo": "X", "role": "documento"}]})
    with pytest.raises(split.ManifestValidationError):
        sm.preflight_manifiestos(case, [d], [])
    # el mismo manifiesto con el documento saltado no bloquea nada (regla de skip intacta)
    sm.preflight_manifiestos(case, [replace(d, skip=True)], [])
    assert "ofimatica" in sm._RUTAS_CON_BUNDLE


def test_o12_reforzar_selecciona_un_convertido_dudoso(tmp_path, monkeypatch, capsys):
    """R1/H-02: `_REFORZABLES` no incluía `ofimatica`; un convertido `low` tenía PDF
    renderizable en 01_OCR y `reforzar` decía «0 documentos a reforzar»."""
    case, _src, d = _caso(tmp_path)
    cli = _cablear_cli(monkeypatch, case)
    assert "ofimatica" in cli._REFORZABLES
    cli._guardar_cobertura(case, [sm.DocCobertura(d.slug, d.rel_path, "ofimatica", "low", 40,
                                                   False, "gibberish", d.sha256)])
    monkeypatch.setattr(cli, "_exigir_vision_cableada", lambda: None)
    llegados = []

    def _ejecutar(case_dir, docs, **kw):
        llegados.extend(x.rel_path for x in docs)
        return []
    monkeypatch.setattr(sm, "ejecutar", _ejecutar)
    cli.reforzar("W-TEST99")
    assert llegados == [d.rel_path], capsys.readouterr().out


def test_o13_si_publicar_falla_no_queda_un_pdf_mudo_en_01_ocr(tmp_path, monkeypatch):
    """R1/H-03: se decide sobre el temporal y se publica DESPUÉS. Si publicar falla (un lector
    con el fichero abierto, WinError 32), en 01_OCR no queda nada y la fila dice `error`."""
    case, _src, d = _caso(tmp_path)

    def _convertir(src, dst, **_k):
        _pdf_con_texto(Path(dst))
        return Path(dst)

    def _move_bloqueado(*_a, **_k):
        raise PermissionError("[WinError 32] fichero bloqueado por otro proceso")

    monkeypatch.setattr(sm, "convertir_ofimatica", _convertir)
    monkeypatch.setattr(sm, "ocr_pdf_escalera", _no_ocr)
    monkeypatch.setattr(sm.shutil, "move", _move_bloqueado)
    cob = sm.ejecutar(case, [d], case_id="EV-2026-001")
    assert cob[0].metodo == "error" and cob[0].estado == "empty"
    ocr = case / "01_Procesado" / "02_Sala de máquina" / "01_OCR"
    assert not list(ocr.glob("*.pdf")) if ocr.exists() else True
    assert not (case / "01_Procesado" / "02_Sala de máquina" / "03_MD").exists()


# ── O10 (LibreOffice real) ─────────────────────────────────────────────────────────────

@pytest.mark.slow
def test_o10_libreoffice_real_convierte_el_doc_de_fixtures(tmp_path):
    if ofi.localizar_soffice() is None:
        pytest.skip("LibreOffice no instalado en esta máquina")
    case = tmp_path / "EV-2026-001"
    (case / "00_Input" / "01_Drive EV").mkdir(parents=True)
    src = case / "00_Input" / "01_Drive EV" / "encargo_prueba.doc"
    src.write_bytes(FIXTURE_DOC.read_bytes())
    p = sm.plan(sm.inventariar(case), set())
    assert p[0].ruta == "ofimatica"
    cob = sm.ejecutar(case, p, case_id="EV-2026-001")
    assert cob[0].estado in ("ok", "low"), cob[0]
    assert cob[0].metodo in ("ofimatica", "ocr")
    sm_dir = case / "01_Procesado" / "02_Sala de máquina"
    assert (sm_dir / "01_OCR" / f"{p[0].slug}.pdf").exists()
    md = (sm_dir / "03_MD" / f"{p[0].slug}.md").read_text(encoding="utf-8")
    assert "Hoja de encargo de prueba" in md
