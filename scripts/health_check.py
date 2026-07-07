"""CLI: comprueba que el entorno tiene todas las dependencias del módulo
``core/anon/`` operativas (Python + sistema + modelos NLP).

Uso:
  python -m scripts.health_check
  python -m scripts.health_check --verbose

Salida: lista de checks (✓/✗). Exit code 1 si falta algo crítico.

Ampliación de ``_herramientas/verificar_entorno.py`` original con:
  - Ghostscript (requerido por ocrmypdf con --optimize 1).
  - Smoke test del singleton Presidio (carga real de los modelos).
  - Comprobación de los 3 modelos spaCy descargados.
"""

from __future__ import annotations

import subprocess
from importlib import import_module

import typer

app = typer.Typer(
    add_completion=False,
    help="Health check del entorno del Anonimizador absorbido en FeesDefender.",
)


_PYTHON_DEPS = [
    # Core FeesDefender (debería estar siempre)
    ("yaml",         "pyyaml"),
    ("slugify",      "python-slugify"),
    ("httpx",        "httpx"),
    # Extracción y manipulación de PDF
    ("pypdf",        "pypdf"),
    ("docx",         "python-docx"),
    ("pdfminer",     "pdfminer.six"),
    # NLP / anonimización
    ("spacy",        "spacy"),
    ("presidio_analyzer",   "presidio-analyzer"),
    ("presidio_anonymizer", "presidio-anonymizer"),
    # OCR e imagen
    ("ocrmypdf",     "ocrmypdf"),
    ("PIL",          "Pillow"),
]

_SPACY_MODELS = ["es_core_news_lg", "ca_core_news_sm", "en_core_web_lg"]

_SYSTEM_BINARIES = [
    # (binario, comando para verificar versión, nota si falla)
    ("tesseract",  ["tesseract", "--version"],  "Tesseract 5.x con paquetes spa, cat, rus"),
    ("ocrmypdf",   ["python", "-m", "ocrmypdf", "--version"], "Wrapper Python ocrmypdf"),
    ("gswin64c",   ["gswin64c", "--version"],   "Ghostscript (requerido por ocrmypdf --optimize)"),
]

_TESSERACT_LANGS_REQUERIDOS = {"spa", "cat", "rus"}


def _ok(msg: str) -> None:
    typer.echo(typer.style("  ✓ ", fg=typer.colors.GREEN, bold=True) + msg)


def _ko(msg: str) -> None:
    typer.echo(typer.style("  ✗ ", fg=typer.colors.RED, bold=True) + msg, err=True)


def _info(msg: str) -> None:
    typer.echo(typer.style("  · ", fg=typer.colors.YELLOW) + msg)


def _check_python_deps(verbose: bool) -> int:
    typer.echo(typer.style("\n[1] Dependencias Python", bold=True))
    errors = 0
    for mod, pkg in _PYTHON_DEPS:
        try:
            m = import_module(mod)
            v = getattr(m, "__version__", "?")
            _ok(f"{pkg:<25} (v{v})")
        except ImportError:
            _ko(f"{pkg:<25} NO instalado — `pip install {pkg}`")
            errors += 1
    return errors


def _check_spacy_models(verbose: bool) -> int:
    typer.echo(typer.style("\n[2] Modelos spaCy", bold=True))
    try:
        import spacy
    except ImportError:
        _ko("spacy no está instalado — saltando comprobación de modelos")
        return 1

    errors = 0
    for nombre in _SPACY_MODELS:
        try:
            spacy.load(nombre)
            _ok(f"{nombre} cargable")
        except (OSError, ImportError):
            _ko(f"{nombre} NO descargado — `python -m spacy download {nombre}`")
            errors += 1
    return errors


def _check_system_binaries(verbose: bool) -> int:
    typer.echo(typer.style("\n[3] Binarios del sistema", bold=True))
    errors = 0
    for nombre, cmd, nota in _SYSTEM_BINARIES:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            primera_linea = (r.stdout or r.stderr).splitlines()[0] if (r.stdout or r.stderr) else "?"
            _ok(f"{nombre:<12} → {primera_linea[:80]}")
        except FileNotFoundError:
            _ko(f"{nombre:<12} NO encontrado en PATH — {nota}")
            errors += 1
        except subprocess.TimeoutExpired:
            _ko(f"{nombre:<12} timeout (10s)")
            errors += 1
    return errors


def _check_tesseract_langs(verbose: bool) -> int:
    typer.echo(typer.style("\n[4] Paquetes de idioma de Tesseract", bold=True))
    try:
        r = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True, text=True, timeout=10,
        )
        langs_disponibles = set(
            line.strip() for line in r.stdout.splitlines() if line.strip()
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _ko("No se pudo ejecutar `tesseract --list-langs`")
        return 1

    errors = 0
    for lang in _TESSERACT_LANGS_REQUERIDOS:
        if lang in langs_disponibles:
            _ok(f"{lang:<5} disponible")
        else:
            _ko(f"{lang:<5} NO instalado — descargar de tesseract-ocr/tessdata")
            errors += 1
    return errors


def _check_presidio_smoke(verbose: bool) -> int:
    typer.echo(typer.style("\n[5] Smoke test del singleton Presidio", bold=True))
    try:
        from core.anon.nlp_engine import get_analyzer
    except ImportError as e:
        _ko(f"No se puede importar core.anon.nlp_engine: {e}")
        return 1

    try:
        _info("Cargando modelos (puede tardar 20-40 s la primera vez)...")
        analyzer = get_analyzer()
        # Análisis trivial para confirmar que el motor está operativo
        resultados = analyzer.analyze(
            text="Don Pedro Lopez con DNI 12345678A.",  # leak-guard:allow (DNI sintético de prueba)
            language="es",
            score_threshold=0.35,
        )
        _ok(f"AnalyzerEngine operativo — {len(resultados)} entidad(es) en texto de prueba")
        return 0
    except Exception as e:
        _ko(f"Presidio falló al cargar: {type(e).__name__}: {e}")
        return 1


@app.command()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v",
                                  help="Imprime versiones detalladas y salida completa."),
    skip_smoke: bool = typer.Option(False, "--skip-smoke",
                                     help="Omite el smoke test de Presidio (más rápido, no carga modelos)."),
) -> None:
    """Comprueba el entorno completo del módulo de anonimización."""
    typer.echo(typer.style(
        "FeesDefender · Health check del módulo core/anon/",
        bold=True, fg=typer.colors.CYAN,
    ))

    errores = 0
    errores += _check_python_deps(verbose)
    errores += _check_spacy_models(verbose)
    errores += _check_system_binaries(verbose)
    errores += _check_tesseract_langs(verbose)
    if not skip_smoke:
        errores += _check_presidio_smoke(verbose)

    typer.echo("")
    if errores == 0:
        typer.echo(typer.style("✅ Entorno OK. Todo listo para anonimizar.", fg=typer.colors.GREEN, bold=True))
    else:
        typer.echo(typer.style(
            f"❌ {errores} problema(s) detectado(s). Revisa docs/INSTALACION_ANONIMIZADOR.md.",
            fg=typer.colors.RED, bold=True,
        ))
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
