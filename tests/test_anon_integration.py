"""Tests de integración de la fachada ``core.anon.api`` — Fase 3.

Cubre:
- ``anonimizar_documento`` sobre un solo doc, con mapa nuevo y compartido.
- ``anonimizar_caso`` con varios docs: mapa compartido entre ellos,
  generación de outputs en ``06_Anonimizado/``, log en ``07_AI cowork/``.
- Idempotencia: política SALTAR no reprocesa si el hash no cambió.
- Política REPROCESAR fuerza nueva ejecución.
- Errores graciosos: PDF sin texto → alerta ``OCR_REQUERIDO``.
- Frontmatter YAML estilo FeesDefender bien formado.

No requiere PDFs reales: mockea ``extraer_texto`` para inyectar contenido
sintético. La extracción real se cubre en el roadmap de Fase 4 (smoke
test contra fixture PDF generado on-the-fly).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.anon import (
    MapaEntidades,
    anonimizar_caso,
    anonimizar_documento,
)
from core.utils import read_md

# Carga el motor NLP real (Presidio + spaCy). Lento; solo con --runslow.
pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def caso_aislado(tmp_path: Path, monkeypatch):
    """Aísla un caso ``EV-2099-001`` en ``tmp_path``.

    Patches:
      - ``core.anon.api.caso_path`` y ``core.anon.mapa_caso.caso_path``
        para que apunten al tmp_path en lugar del ``CASOS_ROOT`` real.
    """
    case_id = "EV-2099-001"

    def _caso_path_test(cid: str) -> Path:
        return tmp_path / cid

    monkeypatch.setattr("core.anon.api.caso_path", _caso_path_test)
    monkeypatch.setattr("core.anon.mapa_caso.caso_path", _caso_path_test)

    # Crear estructura mínima del caso
    case_dir = tmp_path / case_id
    (case_dir / "00_Input").mkdir(parents=True)
    (case_dir / "06_Anonimizado").mkdir()
    (case_dir / "07_AI cowork").mkdir()

    yield case_id, case_dir


@pytest.fixture
def mock_extractor(monkeypatch):
    """Reemplaza ``extraer_texto`` por un mapa fichero → texto sintético.

    Devuelve un dict mutable que el test puede ir poblando con el contenido
    sintético de cada fichero antes de llamar a ``anonimizar_documento``.
    """
    contenidos: dict[str, str] = {}

    def _extraer(ruta, log):
        nombre = Path(ruta).name
        if nombre not in contenidos:
            raise FileNotFoundError(f"Test no inyectó contenido para {nombre}")
        return contenidos[nombre]

    monkeypatch.setattr("core.anon.api.extraer_texto", _extraer)
    return contenidos


# ---------------------------------------------------------------------------
# anonimizar_documento — pieza atómica
# ---------------------------------------------------------------------------

class TestAnonimizarDocumento:
    def test_genera_md_con_frontmatter(self, caso_aislado, mock_extractor):
        case_id, case_dir = caso_aislado
        pdf = case_dir / "00_Input" / "demanda.pdf"
        pdf.write_bytes(b"placeholder")

        mock_extractor["demanda.pdf"] = (
            "Demandante: DON IVAN PETROV.\n"
            "DNI 12345678A.\n"
            "Email: contacto@ejemplo.com.\n"
            "IBAN ES91 2100 0418 4502 0005 1332."
        )

        mapa = MapaEntidades()
        res = anonimizar_documento(case_id, pdf, mapa_caso=mapa)

        assert res["ok"] is True
        assert res["skipped"] is False
        assert res["error"] is None
        assert res["ruta_md"] is not None
        assert res["ruta_md"].exists()

        # Frontmatter YAML completo
        meta, body = read_md(res["ruta_md"])
        assert meta["case_id"] == case_id
        assert meta["fase"] == "06_Anonimizado"
        assert meta["tipo"] == "documento_anonimizado"
        assert meta["origen"] == "demanda.pdf"
        assert "origen_sha256" in meta
        assert len(meta["origen_sha256"]) == 64  # SHA-256 hex
        assert meta["n_entidades"] >= 3  # DNI + IBAN + EMAIL al menos

        # Datos personales sustituidos
        assert "12345678A" not in body
        assert "contacto@ejemplo.com" not in body
        assert "ES91" not in body

    def test_idempotencia_skip(self, caso_aislado, mock_extractor):
        """Segunda ejecución sin cambios → skipped=True."""
        case_id, case_dir = caso_aislado
        pdf = case_dir / "00_Input" / "doc.pdf"
        pdf.write_bytes(b"contenido v1")
        mock_extractor["doc.pdf"] = "DNI 11111111A."

        # Primera ejecución
        res1 = anonimizar_documento(case_id, pdf, mapa_caso=MapaEntidades())
        assert res1["ok"] and not res1["skipped"]

        # Segunda ejecución sobre el mismo fichero (mismo hash)
        res2 = anonimizar_documento(case_id, pdf, mapa_caso=MapaEntidades())
        assert res2["ok"] and res2["skipped"] is True

    def test_reprocesar_ignora_skip(self, caso_aislado, mock_extractor):
        case_id, case_dir = caso_aislado
        pdf = case_dir / "00_Input" / "doc.pdf"
        pdf.write_bytes(b"v1")
        mock_extractor["doc.pdf"] = "DNI 22222222B."

        # Primera ejecución
        anonimizar_documento(case_id, pdf, mapa_caso=MapaEntidades())

        # REPROCESAR: ignora idempotencia
        res = anonimizar_documento(
            case_id, pdf, mapa_caso=MapaEntidades(), politica="REPROCESAR"
        )
        assert res["ok"] and res["skipped"] is False

    def test_extension_no_procesable(self, caso_aislado):
        case_id, case_dir = caso_aislado
        img = case_dir / "00_Input" / "foto.jpg"
        img.write_bytes(b"fake jpg")
        res = anonimizar_documento(case_id, img)
        assert res["ok"] is False
        assert "Extensión" in res["error"]

    def test_documento_no_existe(self, caso_aislado):
        case_id, _ = caso_aislado
        res = anonimizar_documento(case_id, Path("/no/existe.pdf"))
        assert res["ok"] is False
        assert "No existe" in res["error"]

    def test_pdf_sin_texto_devuelve_alerta(self, caso_aislado, mock_extractor, monkeypatch):
        from core.anon.exceptions import PDFSinTextoError

        case_id, case_dir = caso_aislado
        pdf = case_dir / "00_Input" / "escaneo.pdf"
        pdf.write_bytes(b"pdf escaneado")

        # Mock que simula un PDF sin capa de texto
        def _extraer_falla(ruta, log):
            raise PDFSinTextoError("PDF sin capa de texto suficiente")

        monkeypatch.setattr("core.anon.api.extraer_texto", _extraer_falla)

        res = anonimizar_documento(case_id, pdf)
        assert res["ok"] is False
        assert "OCR_REQUERIDO" in res["alertas"]
        assert res["ruta_md"] is None


# ---------------------------------------------------------------------------
# anonimizar_caso — pipeline completo
# ---------------------------------------------------------------------------

class TestAnonimizarCaso:
    def test_caso_con_tres_documentos(self, caso_aislado, mock_extractor):
        case_id, case_dir = caso_aislado

        # 3 PDFs en 00_Input/, mismo nombre repetido entre docs para validar
        # mapa compartido (Ivan Petrov aparece en 2 documentos)
        for nombre, contenido in [
            ("demanda.pdf",     "Demandante: DON IVAN PETROV.\nDNI 11111111A."),
            ("contestacion.pdf", "Demandado: DOÑA MARIA GARCIA.\nDNI 22222222B.\nMencion a Ivan Petrov."),
            ("anexo.pdf",       "IBAN ES91 2100 0418 4502 0005 1332."),
        ]:
            pdf = case_dir / "00_Input" / nombre
            pdf.write_bytes(b"placeholder " + nombre.encode())
            mock_extractor[nombre] = contenido

        res = anonimizar_caso(case_id)

        assert res["case_id"] == case_id
        assert res["n_documentos"] == 3
        assert res["n_procesados"] == 3
        assert res["n_skipped"] == 0
        assert res["n_errores"] == 0

        # Outputs en 06_Anonimizado/
        outputs = sorted((case_dir / "06_Anonimizado").glob("*.md"))
        assert len(outputs) == 3

        # Mapa compartido persistido
        assert res["mapa_caso_path"].exists()
        assert res["mapa_caso_path"].name == "_mapa_caso.json"

        # Log en 07_AI cowork/_anonimizador_log.md
        assert res["log_path"].exists()
        assert res["log_path"].name == "_anonimizador_log.md"
        log_text = res["log_path"].read_text(encoding="utf-8")
        assert "Documentos detectados: **3**" in log_text
        assert "demanda.pdf" in log_text

    def test_segunda_ejecucion_skipea(self, caso_aislado, mock_extractor):
        case_id, case_dir = caso_aislado
        pdf = case_dir / "00_Input" / "doc.pdf"
        pdf.write_bytes(b"v1")
        mock_extractor["doc.pdf"] = "DNI 11111111A."

        # Primera ejecución
        res1 = anonimizar_caso(case_id)
        assert res1["n_procesados"] == 1
        assert res1["n_skipped"] == 0

        # Segunda ejecución sobre el mismo input
        res2 = anonimizar_caso(case_id)
        assert res2["n_procesados"] == 0
        assert res2["n_skipped"] == 1

    def test_ignora_archivos_auxiliares(self, caso_aislado, mock_extractor):
        """Los ficheros que empiezan por _ no se anonimizan."""
        case_id, case_dir = caso_aislado
        pdf = case_dir / "00_Input" / "demanda.pdf"
        pdf.write_bytes(b"v1")
        mock_extractor["demanda.pdf"] = "DNI 33333333C."

        # Auxiliar que NO debe procesarse
        (case_dir / "00_Input" / "_caso.md").write_text("# meta", encoding="utf-8")
        (case_dir / "00_Input" / "_inventory.json").write_text("{}", encoding="utf-8")

        res = anonimizar_caso(case_id)
        assert res["n_documentos"] == 1
        assert res["n_procesados"] == 1

    def test_subcarpeta_auxiliar_se_ignora(self, caso_aislado, mock_extractor):
        """Subcarpetas que empiezan por _ tampoco se procesan."""
        case_id, case_dir = caso_aislado
        # PDF dentro de una subcarpeta legítima
        sub_legit = case_dir / "00_Input" / "01_Drive EV"
        sub_legit.mkdir()
        pdf_legit = sub_legit / "doc.pdf"
        pdf_legit.write_bytes(b"v1")
        mock_extractor["doc.pdf"] = "DNI 11111111A."

        # PDF dentro de una subcarpeta auxiliar (no debe procesarse)
        sub_aux = case_dir / "00_Input" / "_borradores"
        sub_aux.mkdir()
        (sub_aux / "draft.pdf").write_bytes(b"v1")

        res = anonimizar_caso(case_id)
        assert res["n_documentos"] == 1
        assert res["n_procesados"] == 1

    def test_caso_sin_documentos(self, caso_aislado):
        case_id, _ = caso_aislado
        res = anonimizar_caso(case_id)
        assert res["n_documentos"] == 0
        assert res["n_procesados"] == 0
        assert res["n_errores"] == 0
        # El log se crea aunque no haya docs (dejamos rastro de ejecución)
        assert res["log_path"].exists()


# ---------------------------------------------------------------------------
# Mapa compartido: el documento 2 hereda etiquetas del documento 1
# ---------------------------------------------------------------------------

class TestMapaCompartido:
    def test_misma_persona_misma_etiqueta(self, caso_aislado, mock_extractor):
        """Si "Ivan Petrov" aparece en 2 documentos, debe llevar la misma
        etiqueta en ambos (clave del mapa compartido por caso).
        """
        case_id, case_dir = caso_aislado

        for nombre, contenido in [
            ("doc1.pdf", "DNI 12121212A."),
            ("doc2.pdf", "DNI 12121212A.\nDNI 99999999X."),
        ]:
            (case_dir / "00_Input" / nombre).write_bytes(b"v1")
            mock_extractor[nombre] = contenido

        res = anonimizar_caso(case_id)
        assert res["n_procesados"] == 2

        # Inspeccionar mapa: 12121212A tiene una sola etiqueta, 99999999X otra
        import json
        datos = json.loads(res["mapa_caso_path"].read_text(encoding="utf-8"))
        directo = datos.get("mapa_directo") or {}

        assert "12121212A" in directo
        assert "99999999X" in directo
        # Las dos etiquetas son distintas
        assert directo["12121212A"] != directo["99999999X"]
        # Y el contador refleja 2 DNIs distintos
        assert datos["contadores"]["DNI"] == 2


# ---------------------------------------------------------------------------
# Colisión de slug: dos orígenes distintos que normalizan al mismo nombre
# ---------------------------------------------------------------------------

class TestColisionSlug:
    """Regresión del bug: dos documentos de 00_Input/ que producen el mismo
    slug (acentos/puntuación normalizados por ``slugify``, o el mismo stem con
    distinta extensión) escribían en el MISMO .md y el segundo sobrescribía al
    primero silenciosamente. La desambiguación debe ser determinista.
    """

    # "Demanda 1ª" y "Demanda 1a" → ambos slug "demanda_1a" (ª → a).
    NOMBRE_A = "Demanda 1ª.pdf"
    NOMBRE_B = "Demanda 1a.pdf"
    SLUG = "demanda_1a"

    def _preparar(self, case_dir, mock_extractor):
        a = case_dir / "00_Input" / self.NOMBRE_A
        b = case_dir / "00_Input" / self.NOMBRE_B
        a.write_bytes(b"contenido A")
        b.write_bytes(b"contenido B")
        mock_extractor[self.NOMBRE_A] = "DNI 11111111A."
        mock_extractor[self.NOMBRE_B] = "DNI 22222222B."
        return a, b

    def test_dos_origenes_mismo_slug_no_se_pisan(self, caso_aislado, mock_extractor):
        case_id, case_dir = caso_aislado
        a, b = self._preparar(case_dir, mock_extractor)

        mapa = MapaEntidades()
        res_a = anonimizar_documento(case_id, a, mapa_caso=mapa)
        res_b = anonimizar_documento(case_id, b, mapa_caso=mapa)

        assert res_a["ok"] and res_b["ok"]
        # El segundo NO sobrescribe al primero: dos .md distintos coexisten.
        assert res_a["ruta_md"] != res_b["ruta_md"]
        assert res_a["ruta_md"].exists()
        assert res_b["ruta_md"].exists()

        # El primero conserva el slug base; el segundo lleva sufijo desambiguador.
        assert res_a["ruta_md"].name == f"{self.SLUG}.md"
        assert res_b["ruta_md"].name.startswith(f"{self.SLUG}-")
        assert res_b["ruta_md"].name.endswith(".md")

        # Cada .md apunta a su propio origen (no se cruzó el contenido).
        meta_a, _ = read_md(res_a["ruta_md"])
        meta_b, _ = read_md(res_b["ruta_md"])
        assert meta_a["origen"] == self.NOMBRE_A
        assert meta_b["origen"] == self.NOMBRE_B

        # Exactamente 2 salidas en 06_Anonimizado/.
        outputs = sorted((case_dir / "06_Anonimizado").glob("*.md"))
        assert len(outputs) == 2

    def test_nombre_estable_entre_ejecuciones(self, caso_aislado, mock_extractor):
        """Mismo origen → mismo nombre en re-runs (no rompe idempotencia)."""
        case_id, case_dir = caso_aislado
        a, b = self._preparar(case_dir, mock_extractor)

        mapa = MapaEntidades()
        nombre_a1 = anonimizar_documento(case_id, a, mapa_caso=mapa)["ruta_md"].name
        nombre_b1 = anonimizar_documento(case_id, b, mapa_caso=mapa)["ruta_md"].name

        # Reproceso forzado: los nombres deben ser idénticos (deterministas).
        nombre_a2 = anonimizar_documento(
            case_id, a, mapa_caso=mapa, politica="REPROCESAR"
        )["ruta_md"].name
        nombre_b2 = anonimizar_documento(
            case_id, b, mapa_caso=mapa, politica="REPROCESAR"
        )["ruta_md"].name

        assert nombre_a1 == nombre_a2
        assert nombre_b1 == nombre_b2
        # No proliferan ficheros: siguen siendo exactamente 2.
        outputs = sorted((case_dir / "06_Anonimizado").glob("*.md"))
        assert len(outputs) == 2

    def test_idempotencia_skip_sobre_fichero_desambiguado(self, caso_aislado, mock_extractor):
        """El .md con sufijo también es idempotente bajo SALTAR."""
        case_id, case_dir = caso_aislado
        a, b = self._preparar(case_dir, mock_extractor)

        mapa = MapaEntidades()
        anonimizar_documento(case_id, a, mapa_caso=mapa)
        r1 = anonimizar_documento(case_id, b, mapa_caso=mapa)
        assert not r1["skipped"]

        # Segunda pasada sobre B (política SALTAR por defecto): se salta y
        # devuelve el MISMO fichero desambiguado.
        r2 = anonimizar_documento(case_id, b, mapa_caso=mapa)
        assert r2["skipped"] is True
        assert r2["ruta_md"].name == r1["ruta_md"].name
