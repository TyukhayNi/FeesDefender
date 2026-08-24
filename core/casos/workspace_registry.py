"""Registro privado de workspaces locales (Fase 1, Task 5).

Responde a una sola pregunta: **¿qué copias locales de casos conoce esta máquina?**
No decide nada — eso es del resolver (Task 7). Guarda punteros, nunca contenido.

## Dónde vive, y por qué no lo decide esta pieza

La raíz se **inyecta** en el constructor. El default de producción
(`%LOCALAPPDATA%\\FeesDefender\\workspaces`) lo resuelve `raiz_por_defecto()`, que es
para los llamadores, no para la clase. Dos razones:

1. La barrera de test (`tests/_barrera.py`) cubre rclone y `subprocess`, **no** las
   escrituras al perfil del usuario. Si la clase se cayera a un default, un test que se
   olvidara de redirigirla escribiría en el `%LOCALAPPDATA%` real. Sin default no hay
   dónde caerse.
2. Es la misma disciplina que el §7 impone al resolver: reloj e identidad inyectados,
   pieza determinista.

Y no puede vivir bajo `CASOS_ROOT` ni bajo el repo. Bajo el catálogo, `list_cases()` lo
vería y un checkin lo subiría al Drive; bajo el repo, `git status` lo vería y acabaría
commiteado. Las dos se comprueban al construir.

## La forma: un fichero por W-code, con una lista dentro

`<w_code>.json`, y dentro una **lista** de entradas. Ni un JSON agregado ni un fichero
por entrada, y esto es contrato (R7/H7-04):

- **Un agregado pierde altas.** Dos procesos sobre W-codes distintos cargan el mismo
  estado y el último `os.replace` borra el alta del primero. La atomicidad del reemplazo
  no evita el *lost update*: lo hace invisible.
- **Un agregado rompe el mutex de D2.** El §24 de la spec de apertura fija un lockfile
  `O_CREAT|O_EXCL` con namespace **por W-code**, viviendo en esta raíz. Locks por W-code
  no se excluyen entre sí sobre un fichero único.
- **Un fichero por ENTRADA no serviría:** un checkout y un scratch del mismo caso deben
  poder coexistir para que el resolver pueda ver la ambigüedad y lanzar `AmbiguousCase`.
  Por eso el fichero es por W-code y contiene una lista.

## Falla cerrado

Un registro ilegible **no** es un registro vacío (R7/H7-02). `cargar()` lanza
`RegistryUnreadable` en vez de devolver `[]`, porque `[]` borra la diferencia entre «este
caso no tiene copia local» y «no puedo saber si la tiene» — y la segunda es la única
señal que impide autorizar `DRIVE_ACTIVE` sobre un caso que quizá está prestado. Los
bytes no se pierden: se renombran a `*.corrupto.<ts>` con el `ts` **inyectado**.
"""
from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import Literal

from .. import config
from . import workspace_model as wm
from .workspace_model import RegistryUnreadable, RutaYaRegistrada, SchemaNoSoportado

__all__ = [
    "SCHEMA_SOPORTADO",
    "WorkspaceEntry",
    "WorkspaceRegistry",
    "RegistryUnreadable",
    "RutaYaRegistrada",
    "SchemaNoSoportado",
    "raiz_por_defecto",
]

#: Versión del formato en disco. Un registro con otra versión no se adivina: se lanza.
SCHEMA_SOPORTADO = 1

_CAMPOS = ("case_id", "w_code", "canonical_ref", "local_path", "nonce",
           "maquina", "tipo", "ultima_validacion", "schema")


# Indirecciones para que el test pueda sustituirlas sin tocar `settings`, que es
# un frozen dataclass evaluado en el import.
def _casos_root() -> Path:
    return Path(config.settings.casos_root)


def _project_root() -> Path:
    return Path(config.settings.project_root)


def raiz_por_defecto() -> Path:
    """El hogar de producción. Para los llamadores; la clase no se cae aquí sola."""
    override = os.getenv("FEESDEFENDER_WORKSPACE_REGISTRY")
    if override:
        return Path(override)
    base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "FeesDefender" / "workspaces"


def _bajo(candidata: Path, raiz: Path) -> bool:
    c, r = os.path.normcase(str(candidata)), os.path.normcase(str(raiz))
    return c == r or c.startswith(r + os.sep)


@dataclasses.dataclass(frozen=True)
class WorkspaceEntry:
    """Un puntero a una copia local. Sin contenido del caso y sin secretos (§16)."""

    case_id: str
    w_code: str
    canonical_ref: str | None
    local_path: Path
    nonce: str
    maquina: str
    tipo: Literal["checkout", "scratch"]
    ultima_validacion: str
    schema: int = SCHEMA_SOPORTADO

    def a_json(self) -> dict:
        return {
            "case_id": self.case_id,
            "w_code": self.w_code,
            "canonical_ref": self.canonical_ref,
            "local_path": str(self.local_path),
            "nonce": self.nonce,
            "maquina": self.maquina,
            "tipo": self.tipo,
            "ultima_validacion": self.ultima_validacion,
            "schema": self.schema,
        }

    @classmethod
    def de_json(cls, crudo: dict) -> WorkspaceEntry:
        if crudo.get("schema") != SCHEMA_SOPORTADO:
            raise SchemaNoSoportado(
                w_code=crudo.get("w_code"),
                detalle=f"schema {crudo.get('schema')!r} != {SCHEMA_SOPORTADO}",
            )
        return cls(
            case_id=crudo["case_id"],
            w_code=crudo["w_code"],
            canonical_ref=crudo.get("canonical_ref"),
            local_path=Path(crudo["local_path"]),
            nonce=crudo["nonce"],
            maquina=crudo["maquina"],
            tipo=crudo["tipo"],
            ultima_validacion=crudo["ultima_validacion"],
            schema=crudo["schema"],
        )


class WorkspaceRegistry:
    """Las copias locales que esta máquina conoce. Guarda; no decide."""

    def __init__(self, raiz: Path, *, ahora: str) -> None:
        raiz = Path(raiz)
        for prohibida, motivo in ((_casos_root(), "CASOS_ROOT"),
                                  (_project_root(), "el repo")):
            if _bajo(raiz, prohibida):
                raise wm.WorkspaceUnderCatalogRoot(
                    detalle=f"el registro no puede vivir bajo {motivo}")
        self._raiz = raiz
        self._ahora = ahora

    # ---------------------------------------------------------------- lectura

    def _fichero(self, w_code: str) -> Path:
        return self._raiz / f"{w_code}.json"

    def _leer(self, fichero: Path) -> list[WorkspaceEntry]:
        try:
            crudo = json.loads(fichero.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._cuarentena(fichero)
            raise RegistryUnreadable(
                detalle=f"{fichero.name} ilegible: {type(exc).__name__}") from exc
        if not isinstance(crudo, list):
            self._cuarentena(fichero)
            raise RegistryUnreadable(detalle=f"{fichero.name} no contiene una lista")
        return [WorkspaceEntry.de_json(e) for e in crudo]

    def _cuarentena(self, fichero: Path) -> None:
        """Preserva los bytes. NO borra nunca: un registro ilegible es evidencia."""
        marca = self._ahora.replace(":", "-")
        destino = fichero.with_name(f"{fichero.name}.corrupto.{marca}")
        if not destino.exists():
            os.replace(fichero, destino)

    def cargar(self) -> list[WorkspaceEntry]:
        """Todas las entradas. Lanza si algo es ilegible: NO devuelve `[]`."""
        if not self._raiz.is_dir():
            return []
        entradas: list[WorkspaceEntry] = []
        # `*.json` a propósito: los lockfiles de D2 (`<w_code>.lock`) viven en esta
        # misma raíz y no son entradas ni candidatos a cuarentena.
        for fichero in sorted(self._raiz.glob("*.json")):
            entradas.extend(self._leer(fichero))
        return entradas

    def buscar(self, ref: wm.CaseRef) -> list[WorkspaceEntry]:
        """Todas las entradas que casan con `ref`. **Devuelve las dos si hay dos:**
        desambiguar es del resolver, y si el registro eligiera, el resolver no podría
        ni ver la ambigüedad."""
        if ref.w_code:
            fichero = self._fichero(ref.w_code)
            candidatas = self._leer(fichero) if fichero.is_file() else []
        else:
            candidatas = self.cargar()
        return [e for e in candidatas if self._casa(e, ref)]

    @staticmethod
    def _casa(entrada: WorkspaceEntry, ref: wm.CaseRef) -> bool:
        if ref.w_code and entrada.w_code != ref.w_code:
            return False
        if ref.case_id and entrada.case_id != ref.case_id:
            return False
        return bool(ref.w_code or ref.case_id)

    # --------------------------------------------------------------- escritura

    def _escribir(self, w_code: str, entradas: list[WorkspaceEntry]) -> None:
        """Temporal en el MISMO directorio + `os.replace`. Nunca in-place.

        El mismo directorio no es cosmético: `os.replace` solo es atómico dentro del
        mismo sistema de ficheros.
        """
        self._raiz.mkdir(parents=True, exist_ok=True)
        destino = self._fichero(w_code)
        if not entradas:
            destino.unlink(missing_ok=True)
            return
        cuerpo = json.dumps([e.a_json() for e in entradas], ensure_ascii=False, indent=2)
        tmp = destino.with_name(f".{destino.name}.tmp")
        tmp.write_text(cuerpo + "\n", encoding="utf-8")
        try:
            os.replace(tmp, destino)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    def alta(self, entrada: WorkspaceEntry) -> None:
        """Registra una copia local. Rechaza reusar una ruta de otro caso."""
        for otra in self.cargar():
            if (os.path.normcase(str(otra.local_path))
                    == os.path.normcase(str(entrada.local_path))
                    and otra.case_id != entrada.case_id):
                raise RutaYaRegistrada(
                    w_code=entrada.w_code,
                    detalle="esa carpeta ya es el workspace de otro caso")
        actuales = [e for e in self.buscar(wm.CaseRef(w_code=entrada.w_code))
                    if os.path.normcase(str(e.local_path))
                    != os.path.normcase(str(entrada.local_path))]
        self._escribir(entrada.w_code, actuales + [entrada])

    def baja(self, ref: wm.CaseRef) -> None:
        """Retira las entradas que casan. Idempotente: retirar dos veces no es error."""
        objetivo = ref.w_code
        if not objetivo:
            halladas = self.buscar(ref)
            if not halladas:
                return
            objetivo = halladas[0].w_code
        fichero = self._fichero(objetivo)
        if not fichero.is_file():
            return
        quedan = [e for e in self._leer(fichero) if not self._casa(e, ref)]
        self._escribir(objetivo, quedan)

    def revalidar(self, ref: wm.CaseRef, *, local_path: Path) -> None:
        """Sella la entrada con el `ahora` **inyectado**. Sin reloj propio."""
        halladas = self.buscar(ref)
        if not halladas:
            raise wm.LocalWorkspaceMissing(
                w_code=ref.w_code, detalle="no hay entrada que revalidar")
        w_code = halladas[0].w_code
        todas = self._leer(self._fichero(w_code))
        nuevas = [
            dataclasses.replace(e, ultima_validacion=self._ahora,
                                local_path=Path(local_path))
            if self._casa(e, ref) else e
            for e in todas
        ]
        self._escribir(w_code, nuevas)
