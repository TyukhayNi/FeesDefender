"""Modelo puro del workspace dual del expediente activo.

Responde una sola pregunta: **«¿dónde se trabaja y qué está permitido?»**. No
descarga documentos, no hace OCR, no toca disco, no lee el reloj y no resuelve
nada — resolver es del `CaseWorkspaceResolver` (Task 7).

Spec: `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md`
— §5.1 identidad, §5.2 modos, §5.3 el valor validado, §5.4 capacidades,
§10 los doce códigos de error, §16 los mensajes no llevan rutas locales.

**Por qué las capacidades son una tabla y no una cadena de `if`.** El §5.4 las
define como una matriz modo × capacidad. Escrita como `if` se convierte en lógica
que hay que leer para saber qué concede un modo, y en la que un caso nuevo se
olvida en silencio; escrita como dato, `CAPACIDADES_POR_MODO` se compara entera
contra la spec en un test y `test_la_matriz_cubre_todos_los_modos` impide que un
modo se quede sin fila.
"""
from __future__ import annotations

import dataclasses
from enum import StrEnum
from pathlib import Path


class WorkspaceMode(StrEnum):
    """Los cinco modos normativos del §5.2.

    Los dos `BLOCKED_*` son **resultados de resolución**, no workspaces
    utilizables por motores mutantes.
    """

    DRIVE_ACTIVE = "drive_active"
    LOCAL_CHECKOUT = "local_checkout"
    LOCAL_SCRATCH = "local_scratch"
    BLOCKED_FOREIGN_CHECKOUT = "blocked_foreign_checkout"
    BLOCKED_CONFLICT = "blocked_conflict"

    @property
    def es_bloqueado(self) -> bool:
        return self in _MODOS_BLOQUEADOS


class Capability(StrEnum):
    """Las ocho del §5.4.

    Los motores **no** deducen capacidades de una letra de unidad: las reciben
    del contexto, o los invoca un entrypoint que ya las verificó.
    """

    READ_CASE = "read_case"
    WRITE_CASE = "write_case"
    INGEST = "ingest"
    GENERATE_DERIVATIVES = "generate_derivatives"
    MUTATE_CANONICAL = "mutate_canonical"
    CHECKOUT = "checkout"
    CHECKIN = "checkin"
    PROMOTE = "promote"


_MODOS_BLOQUEADOS = frozenset({
    WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT,
    WorkspaceMode.BLOCKED_CONFLICT,
})

# La tabla del §5.4, como dato.
#
# `DRIVE_ACTIVE` concede `MUTATE_CANONICAL` porque la spec dice «según
# operación»: el modo lo permite y la operación concreta decide. Los dos modos
# locales lo niegan: es la invariante que impide que una copia prestada escriba
# en el canon antes del checkin o de la promoción.
#
# Los dos `BLOCKED_*` no conceden NADA, ni `READ_CASE`. **Es una decisión, no una
# lectura obvia**, y se declara aquí: el §5.4 dice «solo diagnóstico autorizado»,
# y esa autorización es un parámetro explícito del resolver (`diagnostico=True`),
# no una capacidad del modo. La alternativa —conceder `READ_CASE` a los
# bloqueados— haría que `permite(READ_CASE)` fuera cierto para un caso en
# conflicto, que es justo el estado en el que nadie debería leer sin saber que
# está en conflicto.
CAPACIDADES_POR_MODO: dict[WorkspaceMode, frozenset[Capability]] = {
    WorkspaceMode.DRIVE_ACTIVE: frozenset({
        Capability.READ_CASE,
        Capability.WRITE_CASE,
        Capability.INGEST,
        Capability.GENERATE_DERIVATIVES,
        Capability.MUTATE_CANONICAL,
        Capability.CHECKOUT,
    }),
    WorkspaceMode.LOCAL_CHECKOUT: frozenset({
        Capability.READ_CASE,
        Capability.WRITE_CASE,
        Capability.INGEST,
        Capability.GENERATE_DERIVATIVES,
        Capability.CHECKIN,
    }),
    WorkspaceMode.LOCAL_SCRATCH: frozenset({
        Capability.READ_CASE,
        Capability.WRITE_CASE,
        Capability.INGEST,
        Capability.GENERATE_DERIVATIVES,
        Capability.PROMOTE,
    }),
    WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT: frozenset(),
    WorkspaceMode.BLOCKED_CONFLICT: frozenset(),
}


# ---------------------------------------------------------------- §10 errores

class WorkspaceError(Exception):
    """Error estructurado del workspace. Cada interfaz lo presenta sin cambiar
    su significado (§10).

    **El mensaje nunca lleva la ruta local** (§16): se construye con W-code,
    código, titular, máquina y fecha. La ruta vive solo en el registro privado,
    y `detalle` se acepta pero **no** se reproduce en `str()` — está para que el
    llamante pueda pasar contexto sin que se filtre por el mensaje.
    """

    codigo: str = "WORKSPACE_ERROR"

    def __init__(
        self,
        *,
        w_code: str | None = None,
        titular: str | None = None,
        maquina: str | None = None,
        fecha: str | None = None,
        sin_efecto: bool = False,
        detalle: str | None = None,
    ) -> None:
        self.w_code = w_code
        self.titular = titular
        self.maquina = maquina
        self.fecha = fecha
        self.sin_efecto = sin_efecto
        # Deliberadamente NO se guarda `detalle` en el mensaje. Ver docstring.
        self.detalle = detalle
        super().__init__(self._mensaje())

    def _mensaje(self) -> str:
        partes = [f"[{self.codigo}]"]
        if self.w_code:
            partes.append(f"caso {self.w_code}")
        if self.titular:
            partes.append(f"titular {self.titular}")
        if self.maquina:
            partes.append(f"maquina {self.maquina}")
        if self.fecha:
            partes.append(f"desde {self.fecha}")
        if self.sin_efecto:
            # §10: el mensaje dice que no hubo efecto cuando así es, y no
            # sugiere reintentar contra Drive como atajo.
            partes.append("sin efecto: no se produjo ninguna escritura")
        return " — ".join(partes)


class CaseLocked(WorkspaceError):
    codigo = "CASE_LOCKED"


class LocalWorkspaceMissing(WorkspaceError):
    codigo = "LOCAL_WORKSPACE_MISSING"


class LockMismatch(WorkspaceError):
    codigo = "LOCK_MISMATCH"


class CaseConflict(WorkspaceError):
    codigo = "CASE_CONFLICT"


class AmbiguousCase(WorkspaceError):
    codigo = "AMBIGUOUS_CASE"


class RuntimeCannotAccessWorkspace(WorkspaceError):
    codigo = "RUNTIME_CANNOT_ACCESS_WORKSPACE"


class CapabilityDenied(WorkspaceError):
    codigo = "CAPABILITY_DENIED"


class CanonicalMutationDeferred(WorkspaceError):
    codigo = "CANONICAL_MUTATION_DEFERRED"


class LockNotMine(WorkspaceError):
    codigo = "LOCK_NOT_MINE"


class CheckoutCancelledElsewhere(WorkspaceError):
    codigo = "CHECKOUT_CANCELLED_ELSEWHERE"


class WorkspaceUnderCatalogRoot(WorkspaceError):
    codigo = "WORKSPACE_UNDER_CATALOG_ROOT"


class AuditBaselineMissing(WorkspaceError):
    codigo = "AUDIT_BASELINE_MISSING"


def errores_conocidos() -> tuple[type[WorkspaceError], ...]:
    """Las doce subclases del §10.

    Se enumeran explícitamente en vez de barrer `__subclasses__()`: así el test
    que compara contra los doce códigos de la spec muere si alguien añade una
    subclase sin código o retira una que la spec exige.
    """
    return (
        CaseLocked,
        LocalWorkspaceMissing,
        LockMismatch,
        CaseConflict,
        AmbiguousCase,
        RuntimeCannotAccessWorkspace,
        CapabilityDenied,
        CanonicalMutationDeferred,
        LockNotMine,
        CheckoutCancelledElsewhere,
        WorkspaceUnderCatalogRoot,
        AuditBaselineMissing,
    )


# --------------------------------------------------------------- §5.1 CaseRef

@dataclasses.dataclass(frozen=True)
class CaseRef:
    """Identidad estable del caso, independiente de su ruta (§5.1).

    El nombre de carpeta es una presentación y no basta como identidad; la
    referencia canónica de Drive tampoco, porque un caso sin publicar no la
    tiene. Hace falta `case_id` o `w_code`.
    """

    case_id: str | None = None
    w_code: str | None = None
    canonical_ref: str | None = None

    def __post_init__(self) -> None:
        # `object.__setattr__` porque el dataclass es frozen y la normalización
        # tiene que ocurrir en la construcción: si el W-code se normalizara en
        # el getter, dos `CaseRef` con la misma identidad podrían no ser iguales.
        if self.w_code is not None:
            object.__setattr__(self, "w_code", self.normalizar(self.w_code) or None)
        if self.case_id is not None:
            object.__setattr__(self, "case_id", self.case_id.strip() or None)
        if not (self.case_id or self.w_code):
            raise ValueError(
                "CaseRef exige case_id o w_code: una referencia canónica o un "
                "nombre de carpeta no son identidad (spec §5.1)"
            )

    @classmethod
    def normalizar(cls, w_code: str) -> str:
        """W-code canónico: sin espacios de borde y en mayúsculas."""
        return w_code.strip().upper()


# ---------------------------------------------------- §5.3 el valor validado

@dataclasses.dataclass(frozen=True)
class CaseWorkspace:
    """Valor validado e inmutable durante una operación (§5.3).

    No se almacena entre ejecuciones como autorización permanente: cada
    operación mutante lo vuelve a resolver, y una operación larga revalida antes
    de publicar efectos canónicos.

    `capabilities` **no** se acepta en el constructor: se deriva del modo por la
    tabla del §5.4. Si se pudiera inyectar, un llamador podría fabricarse un
    `blocked_*` con `MUTATE_CANONICAL` y el contrato entero dejaría de valer.
    """

    case_ref: CaseRef
    mode: WorkspaceMode
    working_root: Path | None
    canonical_ref: str | None
    checkout_user: str | None
    checkout_maquina: str | None
    checkout_nonce: str | None
    checkout_timestamp: str | None
    validado_en: str
    procedencia: str
    capabilities: frozenset[Capability] = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        modo = WorkspaceMode(self.mode)
        object.__setattr__(self, "mode", modo)
        object.__setattr__(self, "capabilities", CAPACIDADES_POR_MODO[modo])

        # §5.3: `working_root` existe «solo cuando el runtime puede acceder».
        # Las dos direcciones son incoherencias, y la segunda es la que se
        # olvida: un modo bloqueado con raíz de trabajo invita a que alguien la
        # use «solo para leer».
        if modo.es_bloqueado and self.working_root is not None:
            raise ValueError(
                f"[{self.mode}] un modo bloqueado no tiene raíz de trabajo: los "
                "modos blocked_* son resultados de resolución, no workspaces "
                "utilizables (spec §5.2)"
            )
        if not modo.es_bloqueado and self.working_root is None:
            raise ValueError(
                f"[{self.mode}] un modo utilizable exige working_root: sin raíz "
                "de trabajo ningún motor puede honrar la resolución (spec §5.3)"
            )

    @property
    def es_mutable(self) -> bool:
        return not self.mode.es_bloqueado

    def permite(self, cap: Capability) -> bool:
        return cap in self.capabilities

    def exigir(self, cap: Capability) -> None:
        """Lanza `CapabilityDenied` si el modo no concede `cap`."""
        if not self.permite(cap):
            raise CapabilityDenied(
                w_code=self.case_ref.w_code,
                detalle=f"{cap} no concedida en modo {self.mode}",
            )
        return None
