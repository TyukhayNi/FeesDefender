"""Inventario de archivos en `00_Input/`.

Genera `_inventory.json` con metadatos por archivo (tamaño, hash, mime básico,
fecha mtime, fuente) para alimentar las fases siguientes del pipeline.

Convención de fuentes: la fuente de cada fichero se resuelve con el contrato
único `intake_lotes.fuente_de` (MEJORAS #54 T11) — espejos (`01_Drive EV`,
`05_CRM`), lotes (`<AAAA-MM-DD>_<fuente>_<NN>/`) y cajones legacy resuelven a
valores canónicos (`drive_ev`, `crm`, `whatsapp`, `email`, `manual`,
`entrevista`). Los archivos sueltos en la raíz de `00_Input/`, o bajo una
carpeta de primer nivel no reconocida, se clasifican como `manual`.
"""

from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .config import caso_path
from .intake_control import es_fichero_de_protocolo
from .utils import file_sha256


@dataclass
class FileEntry:
    rel_path: str
    name: str
    ext: str
    size: int
    mtime: str
    mime: str | None
    sha256: str
    source: str  # 'sudespacho', 'drive', 'email', 'whatsapp', 'manual', ...


def _source_of(rel_parts: tuple[str, ...]) -> str:
    """Determina la fuente canónica a partir de la ruta relativa al 00_Input/.

    Delega en el contrato único ``intake_lotes.fuente_de`` (MEJORAS #54 T11):
    espejo → nombre canónico; lote → la fuente del nombre; cajón legacy →
    mapa canónico; raíz o cajón desconocido → 'manual'.
    """
    from .intake_lotes import fuente_de
    return fuente_de("/".join(rel_parts))


def _entry(root: Path, path: Path) -> FileEntry:
    rel_parts = path.relative_to(root).parts
    rel = path.relative_to(root).as_posix()
    mime, _ = mimetypes.guess_type(path.name)
    return FileEntry(
        rel_path=rel,
        name=path.name,
        ext=path.suffix.lower(),
        size=path.stat().st_size,
        mtime=datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        mime=mime,
        sha256=file_sha256(path),
        source=_source_of(rel_parts),
    )


def scan(case_id: str) -> Path:
    """Recorre 00_Input/, escribe _inventory.json y devuelve su ruta.

    **Entra todo lo que no es protocolo** (`MEJORAS #316`). Hasta el 2026-09-26 una lista
    blanca de extensiones «relevantes para el pipeline» decidía la población, y lo demás iba a
    `skipped`, que nadie leía: como el catálogo de la sala se construye con lo inventariado,
    en W-02Y2J6 siete notas de voz de WhatsApp, zips, vCards y un vídeo no llegaron a la sala
    de lectura, y en los inventarios reales tampoco un `.pptx`, un `.m4a` ni once documentos
    sin extensión. Qué sabe leer el extractor lo decide el extractor —salta con
    `ExtractionError` lo que no conoce, como ya hacía con las fotos—; qué es protocolo, el
    registro por ubicación. La extensión no decide qué es prueba.
    """
    from core.casos.case_locator import localizar
    input_dir = localizar(case_id) / "00_Input"
    if not input_dir.exists():
        raise FileNotFoundError("falta 00_Input en el caso")

    entries: list[FileEntry] = []

    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        # Protocolo por UBICACIÓN (MEJORAS #149): `_caso.md` y sus temporales `._caso.*`
        # están en el registro de la raíz; un homónimo dentro de un lote es documento.
        if es_fichero_de_protocolo(path.relative_to(input_dir).as_posix()):
            continue
        entries.append(_entry(input_dir, path))

    # Conteo por fuente — útil para observabilidad
    by_source: dict[str, int] = {}
    for e in entries:
        by_source[e.source] = by_source.get(e.source, 0) + 1

    payload = {
        "case_id": case_id,
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(entries),
        "by_source": by_source,
        "files": [asdict(e) for e in entries],
    }
    out = input_dir / "_inventory.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load(case_id: str) -> dict:
    from core.casos.case_locator import localizar
    inv = localizar(case_id) / "00_Input" / "_inventory.json"
    if not inv.exists():
        raise FileNotFoundError("inventario no generado para el caso")
    return json.loads(inv.read_text(encoding="utf-8"))
