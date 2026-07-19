"""OCR por página (baja resolución) de los PDFs sin texto de un expediente.

Robusto frente al OOM de RapidOCR (MEJORAS #39): cada PDF se OCR-iza en un
SUBPROCESO aislado, de modo que un `std::bad_alloc` que mate el proceso solo
pierde ese documento y la corrida continúa. Reanudable: salta los PDFs que ya
tienen texto utilizable. Escribe `01_Procesado/raw_text/{slug}.txt`, regenera el
`.md` y actualiza `_extract_state.json` (método ``ocr_per_page``).

Uso:
  # Driver (sobre todos los PDFs sin texto del caso):
  python -m scripts.ocr_textless_pdfs run --case "BaRS1 - [inmueble] - (W-02VND1) - Vuelta"

  # Worker (interno, un solo PDF):
  python -m scripts.ocr_textless_pdfs worker "<pdf_abs>" "<out_txt_abs>"
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import caso_path  # noqa: E402
from core.utils import output_slug  # noqa: E402

UMBRAL_TEXTO = 50           # < chars no-blancos ⇒ "sin texto" (candidato a OCR)
TIMEOUT_POR_DOC_S = 1800    # 30 min/doc (escaneados de ~17 págs a ~40 s/pág)


def _nonspace(txt: str) -> int:
    return len("".join(txt.split()))


def _textless_pdfs(case_id: str) -> list[dict]:
    """PDFs del estado cuyo .txt actual tiene < UMBRAL_TEXTO chars no-blancos."""
    proc = caso_path(case_id) / "01_Procesado"
    rt = proc / "raw_text"
    state = json.loads((rt / "_extract_state.json").read_text(encoding="utf-8"))["files"]
    out = []
    for rel, v in state.items():
        if Path(rel).suffix.lower() != ".pdf":
            continue
        sha = v.get("source_sha256", "")
        txt = rt / f"{output_slug(rel, sha)}.txt"
        real = _nonspace(txt.read_text(encoding="utf-8", errors="replace")) if txt.exists() else 0
        if real < UMBRAL_TEXTO:
            out.append({"rel": rel, "sha": sha, "txt": txt})
    return out


def worker(pdf_path: str, out_txt: str) -> int:
    from core.ocr_per_page import ocr_pdf_per_page

    def _prog(i: int, chars: int) -> None:
        print(f"    pag {i+1}: {chars} chars", file=sys.stderr, flush=True)

    text = ocr_pdf_per_page(pdf_path, on_page=_prog)
    Path(out_txt).write_text(text, encoding="utf-8")
    print(f"OK {_nonspace(text)} chars", flush=True)
    return 0


def run(case_id: str) -> None:
    from core import markdown_generator
    from core.extractor import ExtractionResult

    case_dir = caso_path(case_id)
    input_dir = case_dir / "00_Input"
    rt = case_dir / "01_Procesado" / "raw_text"
    state_path = rt / "_extract_state.json"

    docs = _textless_pdfs(case_id)
    print(f"[OCR por-página] {len(docs)} PDFs sin texto en {case_id}", flush=True)
    t0 = time.time()
    ok = fail = 0
    for n, d in enumerate(docs, 1):
        rel, sha, out_txt = d["rel"], d["sha"], d["txt"]
        src = input_dir / rel
        print(f"\n[{n}/{len(docs)}] {rel}", flush=True)
        if not src.exists():
            print("    (fuente no encontrada, salto)", flush=True)
            fail += 1
            continue
        t = time.time()
        try:
            cp = subprocess.run(
                [sys.executable, "-m", "scripts.ocr_textless_pdfs", "worker",
                 str(src), str(out_txt)],
                cwd=str(ROOT), timeout=TIMEOUT_POR_DOC_S,
                encoding="utf-8", errors="replace",
                capture_output=True,
            )
        except subprocess.TimeoutExpired:
            print(f"    TIMEOUT (> {TIMEOUT_POR_DOC_S}s), salto", flush=True)
            fail += 1
            continue
        if cp.returncode != 0 or not out_txt.exists():
            print(f"    FALLO (exit {cp.returncode}) — probable OOM en una página; "
                  f"salto. stderr final: {(cp.stderr or '').strip()[-120:]}", flush=True)
            fail += 1
            continue

        text = out_txt.read_text(encoding="utf-8", errors="replace")
        chars = _nonspace(text)
        # Regenerar el .md y actualizar el estado.
        res = ExtractionResult(rel_path=rel, output_path=out_txt, chars=len(text),
                               method="ocr_per_page", skipped=False)
        markdown_generator.build(case_id, [res], force=True)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["files"][rel] = {"source_sha256": sha, "method": "ocr_per_page", "chars": len(text)}
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        ok += 1
        print(f"    OK {chars} chars en {time.time()-t:.0f}s "
              f"({cp.stdout.strip() if cp.stdout else ''})", flush=True)

    print(f"\nDONE: {ok} OK, {fail} fallidos, de {len(docs)} en {time.time()-t0:.0f}s", flush=True)


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "worker":
        raise SystemExit(worker(sys.argv[2], sys.argv[3]))
    if len(sys.argv) >= 3 and sys.argv[1] == "run" and sys.argv[2] == "--case":
        run(sys.argv[3])
        return
    print(__doc__)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
