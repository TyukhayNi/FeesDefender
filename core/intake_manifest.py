"""Manifest de hashes de intake — dedup cross-source SHA-256 (M9).

Resuelve el problema de un mismo documento que entra al caso por varias
fuentes (Drive E&V, email, manual, CRM): se persiste **una sola copia
física**, y las demás apariciones quedan registradas como aliases lógicos.

Path: ``<case_dir>/00_Input/_intake_hashes.json``.

Schema (cerrado por M9):

.. code-block:: json

    {
      "<sha256_hex>": {
        "primary_path": "01_Drive EV/contrato.pdf",
        "aliases": [
          {
            "path": "05_CRM/Civil/.../Demanda/contrato.pdf",
            "source": "crm",
            "expediente_id": "657",
            "added_at": "2026-05-08T10:00:00"
          }
        ]
      }
    }

Todos los paths son **relativos a** ``00_Input/`` (forward slash, D11). Esto
desacopla el manifest del path absoluto del proyecto y permite mover la
carpeta del caso sin invalidarlo.

Decisiones cerradas (memoria persistente: ``project_intake_estructura_v2.md``):

- M9-Q1: manifest en fichero separado, recuperable desde ``_inventory.json``
  si se pierde.
- M9-Q2: chequeo durante pull, antes de escribir cada doc.
- M9-Q3: skip físico del duplicado + registro de alias. ``by_carpeta`` del
  pull state (D8) cuenta los aliases aunque el fichero físico esté en otra
  rama.
- M9-Q4: reconciliación al inicio del pull — si el ``primary_path`` no
  existe en disco, se promueve al primer alias presente.
- M9-Q5: scope solo ``00_Input/``. La fase de anonimizado queda fuera.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .config import caso_path
from .utils import now_iso


_MANIFEST_FILENAME = "_intake_hashes.json"
_INPUT_SUBDIR = "00_Input"
_HASH_CHUNK_SIZE = 65536  # 64 KiB — buen equilibrio entre throughput y memoria


# ---------------------------------------------------------------------------
# Helpers de hashing
# ---------------------------------------------------------------------------

def compute_sha256_bytes(data: bytes) -> str:
    """Devuelve el SHA-256 (hex) de un blob en memoria."""
    return hashlib.sha256(data).hexdigest()


def compute_sha256(path: Path) -> str:
    """Devuelve el SHA-256 (hex) de un fichero leído por chunks.

    Usa lectura de 64 KiB para no cargar archivos grandes en memoria.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_HASH_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Paths y normalización
# ---------------------------------------------------------------------------

def manifest_path(case_id: str) -> Path:
    """Ruta absoluta al manifest del caso. No crea el archivo."""
    return caso_path(case_id) / _INPUT_SUBDIR / _MANIFEST_FILENAME


def _to_relative(case_id: str, path: Path | str) -> str:
    """Convierte un path absoluto a relativo a ``00_Input/`` con separador "/".

    Si ``path`` ya es relativo (str), lo normaliza a forward slash.
    """
    if isinstance(path, str):
        return path.replace("\\", "/").lstrip("/")
    input_root = caso_path(case_id) / _INPUT_SUBDIR
    try:
        rel = Path(path).resolve().relative_to(input_root.resolve())
    except ValueError:
        # Si no está bajo 00_Input/, usamos el path tal cual (responsabilidad del caller)
        rel = Path(path)
    return rel.as_posix()


def _to_absolute(case_id: str, relative: str) -> Path:
    """Convierte un path relativo del manifest a Path absoluto bajo 00_Input/."""
    return caso_path(case_id) / _INPUT_SUBDIR / relative


# ---------------------------------------------------------------------------
# Wrapper principal
# ---------------------------------------------------------------------------

class IntakeManifest:
    """Wrapper sobre el manifest M9 con persistencia explícita.

    Uso típico (durante un pull):

    .. code-block:: python

        with IntakeManifest(case_id) as manifest:
            manifest.reconcile()
            for doc in docs_to_pull:
                sha = compute_sha256_bytes(doc_bytes)
                action, primary_rel = manifest.register(
                    sha,
                    relative_path="05_CRM/Civil/.../Demanda/contrato.pdf",
                    source="crm",
                    expediente_id="657",
                )
                if action == "write":
                    # Es un hash nuevo, hay que escribir el fichero físico.
                    write_to(case_root / "00_Input" / primary_rel, doc_bytes)
                elif action == "skip":
                    # Hash ya presente en `primary_rel`. No escribir físico.
                    # Si la rama lógica destino del pull difiere del primary_rel,
                    # se ha registrado como alias automáticamente.
                    intake_log.append_event(
                        case_id, "dedup_skipped",
                        details={"sha256": sha, "primary": primary_rel, ...},
                    )

    Persistencia: ``save()`` se invoca automáticamente en ``__exit__`` si hay
    cambios y no ha habido excepción. También se puede invocar manualmente.
    """

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self.path = manifest_path(case_id)
        self.data: dict[str, dict[str, Any]] = {}
        self._dirty = False
        self._loaded = False

    # --- ciclo de vida --------------------------------------------------

    def __enter__(self) -> "IntakeManifest":
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._dirty and exc_type is None:
            self.save()

    def load(self) -> None:
        """Carga el manifest desde disco. Si no existe, queda vacío."""
        if self.path.exists():
            try:
                raw = self.path.read_text(encoding="utf-8")
                parsed = json.loads(raw) if raw.strip() else {}
                self.data = parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, OSError):
                # Manifest corrupto: empezar vacío, dejar que reconcile() recupere
                self.data = {}
        else:
            self.data = {}
        self._dirty = False
        self._loaded = True

    def save(self) -> Path:
        """Escribe el manifest a disco con escritura atómica (temp + os.replace).

        Marca ``_dirty = False`` tras escritura exitosa.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Temp en el mismo directorio para que os.replace sea atómico.
        tmp = self.path.parent / f"._intake_hashes.{os.getpid()}.tmp"
        try:
            tmp.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise
        self._dirty = False
        return self.path

    # --- operaciones públicas ------------------------------------------

    def reconcile(self) -> int:
        """Reconciliación al inicio del pull (M9-Q4).

        Para cada entry, comprueba que ``primary_path`` existe en disco. Si
        no, intenta promover el primer alias cuyo fichero esté presente.
        Si tampoco hay alias presente, el entry se conserva (el siguiente
        pull podría re-descargar el doc y completarlo).

        Returns:
            Número de entries promocionados.
        """
        promoted = 0
        for sha, entry in self.data.items():
            primary = entry.get("primary_path", "")
            if primary and _to_absolute(self.case_id, primary).exists():
                continue
            aliases = entry.get("aliases") or []
            if not isinstance(aliases, list):
                continue
            new_primary_alias: dict[str, Any] | None = None
            for alias in aliases:
                if not isinstance(alias, dict):
                    continue
                alias_rel = alias.get("path", "")
                if alias_rel and _to_absolute(self.case_id, alias_rel).exists():
                    new_primary_alias = alias
                    break
            if new_primary_alias is not None:
                # El alias promocionado deja de ser alias.
                entry["primary_path"] = new_primary_alias.get("path", "")
                entry["aliases"] = [
                    a for a in aliases
                    if a is not new_primary_alias
                ]
                promoted += 1
                self._dirty = True
        return promoted

    def register(
        self,
        sha256: str,
        relative_path: str,
        *,
        source: str,
        **alias_details: Any,
    ) -> tuple[str, str]:
        """Registra un hash y decide si hay que escribir el fichero físico (M9-Q3).

        Args:
            sha256: hash hex del contenido.
            relative_path: path relativo a ``00_Input/`` (forward slash) donde
                el caller PRETENDE escribir el doc.
            source: origen lógico del doc (``"crm"``, ``"drive_ev"``, ``"email"``,
                ``"whatsapp"``, ``"manual"``, ``"entrevista"``, ``"migration"``).
            **alias_details: datos extra que persisten en el alias (por
                ejemplo ``expediente_id``). ``added_at`` se inyecta automáticamente.

        Returns:
            Tupla ``(action, primary_relative_path)``:

            - ``("write", relative_path)`` — hash nuevo. El caller debe
              escribir el fichero físico en ``00_Input/<relative_path>``.
            - ``("skip", existing_primary)`` — el hash ya está presente en
              ``existing_primary``. El caller NO debe escribir el fichero
              físico. Si ``relative_path != existing_primary`` y no estaba
              registrado todavía, se ha añadido como alias (auto).

        Raises:
            ValueError: si ``sha256`` está vacío o ``relative_path`` está vacío.
        """
        if not sha256:
            raise ValueError("sha256 requerido")
        if not relative_path:
            raise ValueError("relative_path requerido")
        # Normalización mínima — el caller debería pasar paths POSIX, pero
        # toleramos backslash por si el caller construyó con os.path.join.
        rel = relative_path.replace("\\", "/").lstrip("/")

        entry = self.data.get(sha256)
        if entry is None:
            self.data[sha256] = {
                "primary_path": rel,
                "aliases": [],
            }
            self._dirty = True
            return ("write", rel)

        primary = entry.get("primary_path", "")
        if rel == primary:
            # Misma ubicación lógica — no-op, no hay alias que añadir.
            return ("skip", primary)

        # Comprobar si ya estaba como alias
        aliases = entry.setdefault("aliases", [])
        existing_paths = {a.get("path") for a in aliases if isinstance(a, dict)}
        if rel not in existing_paths:
            new_alias: dict[str, Any] = {
                "path": rel,
                "source": source,
                "added_at": now_iso(),
            }
            new_alias.update(alias_details)
            aliases.append(new_alias)
            self._dirty = True
        return ("skip", primary)

    # --- introspección -------------------------------------------------

    def lookup(self, sha256: str) -> dict[str, Any] | None:
        """Devuelve el entry para un hash, o None si no existe.

        Devuelve una **referencia viva** al dict interno — mutarlo afecta al
        manifest. Usar copia defensiva si se necesita inmutabilidad.
        """
        return self.data.get(sha256)

    def all_paths(self) -> set[str]:
        """Devuelve todos los paths registrados (primary + aliases) como set.

        Útil para auditoría y para el inventario `_inventory.json`.
        """
        paths: set[str] = set()
        for entry in self.data.values():
            primary = entry.get("primary_path")
            if isinstance(primary, str) and primary:
                paths.add(primary)
            for alias in entry.get("aliases") or []:
                if isinstance(alias, dict):
                    p = alias.get("path")
                    if isinstance(p, str) and p:
                        paths.add(p)
        return paths
