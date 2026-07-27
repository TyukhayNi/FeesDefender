"""Registro de ocurrencias del CRM — identidad lógica de los documentos del pleito.

Pieza 2 de la vista procesal. Diseño:
``docs/superpowers/specs/2026-07-27-vista-procesal-05-procedimiento-design.md`` §2.1.

**Por qué existe y no se amplió `intake_manifest`.** El manifiesto de intake está
indexado por SHA-256, con ``primary_path`` + ``aliases``. Ese modelo **no puede
representar dos documentos distintos del CRM con el mismo contenido y la misma
ruta**, y ocurre en vivo: en el expediente 487 la ``TASA ORDINARIO`` se presentó
dos veces (``doc_id`` 39526 y 38060) compartiendo SHA y ``primary_path``, así que
no se crea alias y **ninguno de los dos IDs queda persistido**. Reescribir el
manifiesto se descartó por alcance: lo consumen el pull del CRM, el export de
correo, los atomizadores de email y WhatsApp y el intake de Drive E&V.

**Precedencia declarada: CRM > ocurrencias > manifiesto de intake.** El manifiesto
queda fuera de la ruta de confianza de la vista: sigue siendo índice de contenido
para el dedup y nada más.

**Regenerable, con un matiz.** El *snapshot vigente* se reconstruye re-ejecutando
el pull, que es idempotente. El **histórico no**: el listado del CRM devuelve una
sola foto por documento, así que las revisiones anteriores solo existen aquí.

**Los dos estados y por qué importan.** Una ocurrencia nace ``listada`` —enumerada
en el CRM— y pasa a ``materializada`` cuando el pull deposita su fichero. La
distinción no es cosmética: con intake acotado (``only_doc_ids``) el pull baja un
subconjunto, y si el registro se escribiera solo en el bucle de descarga,
coincidiría con ``pull_state.doc_ids`` **aunque hubiera documentos del CRM
invisibles** — la puerta de integridad sería vacía. Por eso ``registrar_listada``
se llama ANTES del filtro, sobre todo lo enumerado.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import caso_path
from .utils import now_iso

# Versión del esquema. Una desconocida es error, nunca «cero documentos».
VERSION: int = 1

_INPUT_SUBDIR = "00_Input"
_FILENAME = "_ocurrencias_crm.json"
REGISTRO_REL: str = f"{_INPUT_SUBDIR}/{_FILENAME}"

SOURCE_CRM: str = "crm"

# Estados de una revisión. `superseded` no es un estado que se pida: lo adquiere
# la revisión vigente cuando llega otra que la sustituye.
ESTADO_LISTADA: str = "listada"
ESTADO_MATERIALIZADA: str = "materializada"
ESTADO_SUPERSEDED: str = "superseded"


class RegistroInvalidoError(Exception):
    """El registro existe pero no cumple su contrato (ilegible, versión, esquema).

    Se lanza en vez de degradar a un registro vacío: un error de carga que se
    convierte en «cero documentos» hace que el diff de la vista procesal proponga
    borrar todo lo que había.
    """


class OcurrenciaDesconocidaError(Exception):
    """Se intentó materializar un ``doc_id`` que nadie había listado."""


def registro_path(case_id: str) -> Path:
    """Ruta absoluta del registro del caso. No crea el fichero."""
    return caso_path(case_id) / _INPUT_SUBDIR / _FILENAME


def clave(expediente_id: str | int, doc_id: str | int, *, source: str = SOURCE_CRM) -> str:
    """Clave lógica ``<source>:<expediente_id>:<doc_id>``.

    El ámbito por expediente es **parte de la clave**: un caso admite varios
    expedientes CRM y no deben mezclarse.
    """
    return f"{source}:{str(expediente_id).strip()}:{str(doc_id).strip()}"


class RegistroOcurrencias:
    """Registro de ocurrencias de un caso. I/O explícito: ``load()`` / ``save()``."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self.path = registro_path(case_id)
        self.ocurrencias: dict[str, dict[str, Any]] = {}
        self._dirty = False

    # --- carga / guardado -------------------------------------------------

    def load(self) -> None:
        """Lee el registro. Un fichero ausente es un registro vacío legítimo.

        Raises:
            RegistroInvalidoError: ilegible, versión desconocida, esquema roto.
        """
        if not self.path.is_file():
            self.ocurrencias = {}
            self._dirty = False
            return
        try:
            crudo = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            raise RegistroInvalidoError(
                f"{REGISTRO_REL} ilegible ({exc}). No se degrada a registro vacío: "
                f"eso haría que el diff propusiera borrar todo lo ya depositado."
            ) from exc
        if not isinstance(crudo, dict):
            raise RegistroInvalidoError(f"{REGISTRO_REL} debe ser un objeto JSON")

        version = crudo.get("version")
        if version != VERSION:
            raise RegistroInvalidoError(
                f"Versión desconocida en {REGISTRO_REL}: {version!r} (esperada {VERSION})"
            )

        ocurrencias = crudo.get("ocurrencias")
        if not isinstance(ocurrencias, dict):
            raise RegistroInvalidoError(f"`ocurrencias` de {REGISTRO_REL} debe ser un objeto")

        for k, oc in ocurrencias.items():
            if not isinstance(oc, dict):
                raise RegistroInvalidoError(f"Ocurrencia {k!r} no es un objeto")
            revs = oc.get("revisiones")
            if not isinstance(revs, list) or not revs:
                raise RegistroInvalidoError(
                    f"Ocurrencia {k!r} sin revisiones: toda ocurrencia tiene al menos una"
                )

        self.ocurrencias = ocurrencias
        self._dirty = False

    def save(self) -> Path:
        """Escribe el registro con temporal + ``os.replace`` (atómico)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.parent / f"._{_FILENAME}.{os.getpid()}.tmp"
        doc = {
            "version": VERSION,
            "generado": now_iso(),
            "ocurrencias": self.ocurrencias,
        }
        try:
            tmp.write_text(
                json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True),
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

    # --- registro ---------------------------------------------------------

    def registrar_listada(
        self,
        *,
        expediente_id: str | int,
        doc_id: str | int,
        filename: str | None,
        modified_at: str | None,
        id_carpeta: str | int | None,
        source: str = SOURCE_CRM,
    ) -> None:
        """Anota que el CRM enumera este documento. **Antes** de cualquier filtro.

        Idempotente: relistar con el mismo ``modified_at`` no crea revisión. Si la
        fecha cambia, la revisión vigente pasa a ``superseded`` —conservando su
        SHA— y se abre una nueva.

        ``modified_at`` e ``id_carpeta`` son nullable en el DTO del CRM
        (``GdocuDocInfo``): el contrato lo respeta.
        """
        k = clave(expediente_id, doc_id, source=source)
        oc = self.ocurrencias.get(k)
        nueva = {
            "estado": ESTADO_LISTADA,
            "filename": filename,
            "modified_at": modified_at,
            "id_carpeta": None if id_carpeta is None else str(id_carpeta),
            "path": None,
            "sha256": None,
            "registrada_en": now_iso(),
        }
        if oc is None:
            self.ocurrencias[k] = {
                "source": source,
                "expediente_id": str(expediente_id).strip(),
                "doc_id": str(doc_id).strip(),
                "revisiones": [nueva],
            }
            self._dirty = True
            return

        activa = oc["revisiones"][-1]
        if activa.get("modified_at") == modified_at:
            return  # misma foto del CRM: no-op
        activa["estado"] = ESTADO_SUPERSEDED
        oc["revisiones"].append(nueva)
        self._dirty = True

    def registrar_materializada(
        self,
        *,
        expediente_id: str | int,
        doc_id: str | int,
        path: str,
        sha256: str,
        source: str = SOURCE_CRM,
    ) -> None:
        """Anota que el fichero del documento está en disco, con su ruta y su SHA.

        Raises:
            OcurrenciaDesconocidaError: si nadie lo listó antes. Es el invariante
                que impide que el agujero de N2 vuelva por la puerta de atrás.
        """
        k = clave(expediente_id, doc_id, source=source)
        oc = self.ocurrencias.get(k)
        if oc is None:
            raise OcurrenciaDesconocidaError(
                f"{k} no está listada: `registrar_listada` va antes del filtro de "
                f"descarga, sobre TODO lo que el CRM enumera."
            )
        rel = str(path).replace("\\", "/").lstrip("/")
        activa = oc["revisiones"][-1]

        if activa["estado"] == ESTADO_LISTADA:
            activa.update(estado=ESTADO_MATERIALIZADA, path=rel, sha256=sha256,
                          registrada_en=now_iso())
            self._dirty = True
            return

        if activa.get("sha256") == sha256 and activa.get("path") == rel:
            return  # ya materializada con el mismo contenido: no-op

        # El contenido cambió sin que cambiara `modified_at` (el CRM puede
        # reemplazar el fichero): nueva revisión, la anterior se conserva.
        activa["estado"] = ESTADO_SUPERSEDED
        oc["revisiones"].append({
            "estado": ESTADO_MATERIALIZADA,
            "filename": activa.get("filename"),
            "modified_at": activa.get("modified_at"),
            "id_carpeta": activa.get("id_carpeta"),
            "path": rel,
            "sha256": sha256,
            "registrada_en": now_iso(),
        })
        self._dirty = True

    # --- consulta ---------------------------------------------------------

    def revisiones(self, expediente_id: str | int, doc_id: str | int,
                   *, source: str = SOURCE_CRM) -> list[dict[str, Any]]:
        """Todas las revisiones, en orden. La última es la vigente."""
        oc = self.ocurrencias.get(clave(expediente_id, doc_id, source=source))
        return list(oc["revisiones"]) if oc else []

    def activa(self, expediente_id: str | int, doc_id: str | int,
               *, source: str = SOURCE_CRM) -> dict[str, Any] | None:
        """Revisión vigente, o ``None`` si el documento no está registrado."""
        oc = self.ocurrencias.get(clave(expediente_id, doc_id, source=source))
        return oc["revisiones"][-1] if oc else None

    def resolver(self, expediente_id: str | int, doc_id: str | int,
                 *, source: str = SOURCE_CRM) -> tuple[str, str] | None:
        """``(sha256, path)`` de la revisión vigente si está materializada.

        ``None`` si el documento no existe o solo está **listada**: listada no
        significa disponible en disco, y la vista procesal no puede copiarla.
        """
        rev = self.activa(expediente_id, doc_id, source=source)
        if rev is None or rev["estado"] != ESTADO_MATERIALIZADA:
            return None
        return (rev["sha256"], rev["path"])

    def _por_expediente(self, expediente_id: str | int,
                        source: str) -> dict[str, dict[str, Any]]:
        exp = str(expediente_id).strip()
        return {
            oc["doc_id"]: oc["revisiones"][-1]
            for oc in self.ocurrencias.values()
            if oc.get("expediente_id") == exp and oc.get("source") == source
        }

    def listadas(self, expediente_id: str | int,
                 *, source: str = SOURCE_CRM) -> dict[str, dict[str, Any]]:
        """``doc_id → revisión vigente`` de **todo** lo que el CRM enumeró.

        Es el universo contra el que la puerta de integridad compara
        ``documents_total_crm``.
        """
        return self._por_expediente(expediente_id, source)

    def materializadas(self, expediente_id: str | int,
                       *, source: str = SOURCE_CRM) -> dict[str, dict[str, Any]]:
        """Subconjunto con fichero en disco."""
        return {
            d: r for d, r in self._por_expediente(expediente_id, source).items()
            if r["estado"] == ESTADO_MATERIALIZADA
        }

    def solo_listadas(self, expediente_id: str | int,
                      *, source: str = SOURCE_CRM) -> dict[str, dict[str, Any]]:
        """Enumeradas por el CRM y **no** descargadas. El hueco que N2 hacía invisible."""
        return {
            d: r for d, r in self._por_expediente(expediente_id, source).items()
            if r["estado"] == ESTADO_LISTADA
        }
