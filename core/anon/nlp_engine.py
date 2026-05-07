"""Singleton de motores NLP para anonimización.

Carga lazy del `AnalyzerEngine` de Presidio con los tres modelos spaCy
(es / ca / en). En primera llamada inicializa (20-40 s); las siguientes
reutilizan el motor cargado en memoria.

Sin esto, el Anonimizador original cargaba los modelos en cada documento
(L.881-895 de `anonimizar.py`), añadiendo 30 s de overhead por documento.
"""

from __future__ import annotations

from threading import Lock

_engine_lock = Lock()
_analyzer = None  # type: ignore[var-annotated]


def get_analyzer():
    """Devuelve el `AnalyzerEngine` de Presidio (singleton, thread-safe).

    En primera llamada carga los modelos `es_core_news_lg`, `ca_core_news_sm`
    y `en_core_web_lg`. Coste: ~20-40 s la primera vez, ~0 ms en sucesivas.

    Lanza `ImportError` si Presidio o spaCy no están instalados.
    """
    global _analyzer
    if _analyzer is not None:
        return _analyzer

    with _engine_lock:
        if _analyzer is not None:  # double-checked locking
            return _analyzer

        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "es", "model_name": "es_core_news_lg"},
                {"lang_code": "ca", "model_name": "ca_core_news_sm"},
                {"lang_code": "en", "model_name": "en_core_web_lg"},
            ],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        _analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=["es", "ca", "en", "de"],
        )
        return _analyzer


def warmup() -> None:
    """Inicializa el motor en background.

    Llamar al arrancar Streamlit (en un `threading.Thread(daemon=True)`)
    para que la primera anonimización no espere los 30 s de carga.
    """
    get_analyzer()


def is_loaded() -> bool:
    """`True` si el singleton ya está cargado en memoria."""
    return _analyzer is not None
