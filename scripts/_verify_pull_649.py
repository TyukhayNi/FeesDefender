"""Verificación de cierre Fase 0: descarga REST de TODOS los docs del exp. 649.

Usa el flujo real download_document_rest (post-fix downloadUri) contra un
directorio temporal y reporta éxitos/fallos + validación de bytes.
"""
from __future__ import annotations
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import core.config  # noqa: E402,F401
from core.sync_sudespacho import SudespachoClient  # noqa: E402
from core.utils import slugify  # noqa: E402

EXP = "649"
ELEM = "expedientes_judiciales"

c = SudespachoClient()
docs = c.list_gdocu_docs_rest(EXP, element=ELEM)
print(f"Docs listados: {len(docs)}")
tmp = Path(tempfile.mkdtemp(prefix="verify_649_"))
ok = fail = 0
for d in docs:
    stem = slugify(Path(d.filename).stem) or f"doc_{d.doc_id}"
    ext = Path(d.filename).suffix or ".bin"
    dest = tmp / f"{d.doc_id}_{stem}{ext}"
    try:
        c.download_document_rest(d.doc_id, EXP, dest, element=ELEM)
        n = dest.stat().st_size
        size_note = ""
        if d.size is not None:
            size_note = "  size OK" if n == d.size else f"  !! size {n}!={d.size}"
        print(f"  OK  {d.doc_id:>6}  {n:>9} bytes{size_note}  {d.filename[:50]}")
        ok += 1
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {d.doc_id:>6}  {exc}")
        fail += 1
print(f"\nRESULTADO: {ok} OK / {fail} FAIL  de {len(docs)} documentos")
print(f"(tmp: {tmp})")
c.__exit__(None, None, None)
raise SystemExit(1 if fail else 0)
