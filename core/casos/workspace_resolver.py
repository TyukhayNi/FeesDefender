"""El resolver: **¿sobre qué copia se trabaja, y qué está permitido en ella?**

Es la pregunta con la que arrancó todo el diseño dual, y hasta ahora la contestaba
cada módulo por su cuenta —o no la contestaba— mirando `CASOS_ROOT`. Aquí vive una
sola vez, implementando la matriz del **§7** de la spec.

Las otras tres piezas solo le dan datos:

| Pieza | Le dice |
|---|---|
| `CaseCatalog` | qué existe en el canon y qué dice el canon de ello |
| `WorkspaceRegistry` | qué copias locales conoce **esta** máquina |
| `CaseWorkspace` | el valor validado que devuelve, con sus capacidades |

## Puro y determinista, y eso se contrata

El reloj (`ahora`), el usuario y la máquina **se inyectan**. No es estética: un
resolver que llame a `datetime.now()` por dentro da un resultado distinto en cada
ejecución, y entonces ni se puede testear la matriz ni se puede razonar sobre qué
autorizó una operación pasada. La R7 (H7-11) señaló que enunciarlo no basta —un
constructor puede aceptar los tres y luego ignorarlos—, así que hay tests que
parchean los globales para que **lancen**.

## Bloquear lanzando, salvo que te pidan diagnóstico

Los caminos de bloqueo **lanzan** el error del §10. Un motor que va a escribir no
debe recibir un valor que parezca un workspace y no lo sea: eso es justo cómo se
escribe sobre un caso prestado sin enterarse.

La excepción es `diagnostico=True`, para el llamador que quiere **pintar** el estado
—una UI, un `status`— en vez de operar. Ahí devuelve el modo `BLOCKED_*`, que no
concede ninguna capacidad mutante.
"""
from __future__ import annotations

from pathlib import Path

from .case_catalog import CaseCatalog
from .workspace_model import (AmbiguousCase, CaseConflict, CaseLocked, CaseRef,
                              CaseWorkspace, LocalWorkspaceMissing, LockMismatch,
                              RuntimeCannotAccessWorkspace, WorkspaceMode,
                              WorkspaceUnderCatalogRoot)
from .workspace_registry import WorkspaceRegistry

__all__ = ["CaseWorkspaceResolver"]

_PROCEDENCIA_IDENTIDAD = "resolver_por_identidad"
_PROCEDENCIA_RUTA = "resolver_por_ruta"


class CaseWorkspaceResolver:
    """La matriz del §7 en una sola pieza. No descarga, no muta, solo decide."""

    def __init__(self, catalog: CaseCatalog, registry: WorkspaceRegistry, *,
                 usuario: str, maquina: str, ahora: str) -> None:
        self.catalog = catalog
        self.registry = registry
        self.usuario = usuario
        self.maquina = maquina
        self.ahora = ahora

    # ------------------------------------------------------------------ §7.2

    def resolver_por_identidad(self, ref: CaseRef, *, drive_accesible: bool,
                               diagnostico: bool = False) -> CaseWorkspace:
        """Resuelve por W-code o `case_id`, siguiendo el §7.2 paso por paso."""
        # (1) candidatos del registro privado, sin los que apuntan al canon.
        #
        # Esta segunda guarda la descarté una vez por «inerte»: el registro concreto ya
        # filtra al leer, así que ningún llamador de producción puede activarla. **R22
        # demostró que el argumento es falso** (H22-05): `registry` se INYECTA, y un
        # doble que devuelva una entrada canónica hace que el resolver anuncie
        # `local_checkout` con la raíz del canon. Una guarda que un test puede activar
        # con el seam publicado no es inerte — es la diferencia entre «nadie lo hace hoy»
        # y «no puede pasar».
        locales = self._sin_canonicos(self.registry.buscar(ref))

        # (2) el caso canónico, si el catálogo lo conoce.
        canonico: Path | None = None
        try:
            canonico = self.catalog.localizar(ref)
        except LocalWorkspaceMissing:
            canonico = None
        # `AmbiguousCase` del catálogo se propaga: dos carpetas con la misma
        # identidad no las desempata nadie aquí.

        # Un scratch que choca con un caso publicado exige `--case-dir`: el §7.2
        # lo dice al final, y es la misma regla que el catálogo aplica dentro.
        scratches = [e for e in locales if e.tipo == "scratch"]
        if canonico is not None and scratches:
            raise AmbiguousCase(
                w_code=ref.w_code,
                detalle="hay un scratch local y un caso publicado con esta "
                        "identidad; usa --case-dir")

        if canonico is None:
            return self._solo_local(ref, locales, diagnostico=diagnostico,
                                    drive_accesible=drive_accesible)

        # (3) Drive accesible: manda el estado compartido.
        if not drive_accesible:
            return self._offline(ref, locales, diagnostico=diagnostico)

        estado = self.catalog.estado_compartido(ref)
        situacion = estado.get("estado")

        # (8) el conflicto bloquea antes que nada.
        if situacion == "conflicto":
            return self._bloqueo(
                ref, WorkspaceMode.BLOCKED_CONFLICT, diagnostico,
                CaseConflict(w_code=ref.w_code,
                             detalle="el repositorio esta en conflicto"))

        # (4) disponible: se trabaja en el canon.
        if situacion != "prestado":
            return self._workspace(ref, WorkspaceMode.DRIVE_ACTIVE, canonico,
                                   _PROCEDENCIA_IDENTIDAD, estado)

        # (5-7) prestado: exige entrada local con MISMO titular, maquina y nonce.
        if estado.get("checkout_maquina") != self.maquina \
                or estado.get("checkout_user") != self.usuario:
            return self._bloqueo(
                ref, WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT, diagnostico,
                CaseLocked(w_code=ref.w_code,
                           titular=estado.get("checkout_user"),
                           maquina=estado.get("checkout_maquina"),
                           fecha=estado.get("checkout_timestamp"),
                           sin_efecto=True))

        propias = [e for e in locales if e.tipo == "checkout"]
        if not propias:
            # §15: un checkout que esta maquina no registro NO se adopta solo.
            raise LocalWorkspaceMissing(
                w_code=ref.w_code,
                detalle="el lock es de esta maquina pero no hay entrada local; "
                        "requiere adopcion explicita")
        if not any(e.nonce == estado.get("checkout_nonce") for e in propias):
            raise LockMismatch(
                w_code=ref.w_code,
                detalle="el nonce local no coincide con el del canon")

        entrada = next(e for e in propias if e.nonce == estado.get("checkout_nonce"))
        return self._workspace(ref, WorkspaceMode.LOCAL_CHECKOUT,
                               entrada.local_path, _PROCEDENCIA_IDENTIDAD, estado)

    # ------------------------------------------------------------------ §7.1

    def resolver_por_ruta(self, path: Path, *, drive_accesible: bool,
                          diagnostico: bool = False) -> CaseWorkspace:
        """Resuelve un `--case-dir` explícito, siguiendo el §7.1.

        «Tiene prioridad sobre la búsqueda, pero no sobre la seguridad»: las
        comprobaciones se hacen igual, y una ruta bajo el catálogo se rechaza.
        """
        path = Path(path)

        # (1) existe, y no está dentro de la biblioteca.
        if self.catalog.bajo_catalogo(path):
            raise WorkspaceUnderCatalogRoot(
                detalle="el destino no puede vivir bajo la raiz del catalogo")
        if not path.is_dir():
            raise LocalWorkspaceMissing(
                detalle="la ruta indicada en --case-dir no existe")

        # (2-3) identidad local: la da el registro, no el nombre de la carpeta.
        entrada = self._entrada_de_ruta(path)
        if entrada is None:
            # §7.1.7 — identidad y registro se contradicen.
            raise LocalWorkspaceMissing(
                detalle="esa ruta no esta registrada como workspace de ningun caso")

        ref = CaseRef(case_id=entrada.case_id, w_code=entrada.w_code)

        if entrada.tipo == "scratch":
            return self._workspace(ref, WorkspaceMode.LOCAL_SCRATCH, path,
                                   _PROCEDENCIA_RUTA, {})

        # (4-6) es checkout: con Drive accesible se verifica estado y nonce.
        if not drive_accesible:
            return self._workspace(ref, WorkspaceMode.LOCAL_CHECKOUT, path,
                                   _PROCEDENCIA_RUTA, {}, mutate_canonical=False)

        try:
            estado = self.catalog.estado_compartido(ref)
        except LocalWorkspaceMissing:
            # El canon no lo conoce: es un local sin publicar, no un checkout roto.
            return self._workspace(ref, WorkspaceMode.LOCAL_SCRATCH, path,
                                   _PROCEDENCIA_RUTA, {})

        if estado.get("estado") == "conflicto":
            return self._bloqueo(
                ref, WorkspaceMode.BLOCKED_CONFLICT, diagnostico,
                CaseConflict(w_code=ref.w_code,
                             detalle="el repositorio esta en conflicto"))
        if estado.get("estado") == "prestado" \
                and estado.get("checkout_maquina") != self.maquina:
            return self._bloqueo(
                ref, WorkspaceMode.BLOCKED_FOREIGN_CHECKOUT, diagnostico,
                CaseLocked(w_code=ref.w_code,
                           titular=estado.get("checkout_user"),
                           maquina=estado.get("checkout_maquina"),
                           fecha=estado.get("checkout_timestamp"),
                           sin_efecto=True))
        return self._workspace(ref, WorkspaceMode.LOCAL_CHECKOUT, path,
                               _PROCEDENCIA_RUTA, estado)

    # -------------------------------------------------------------- internos

    @staticmethod
    def _sin_canonicos(entradas):
        """Descarta candidatos cuya raíz cae dentro del catálogo (`MEJORAS #136`).

        El registro concreto ya los oculta al leer; esto cubre el **seam inyectado**, que
        es superficie publicada y no una hipótesis (R22/H22-05, con doble).
        """
        from .case_catalog import DENTRO, clasificar_bajo
        from .. import config
        raiz = Path(config.settings.casos_root)
        return [e for e in entradas
                if clasificar_bajo(Path(e.local_path), raiz) != DENTRO]

    def _entrada_de_ruta(self, path: Path):
        import os
        objetivo = os.path.normcase(os.path.abspath(str(path)))
        for e in self._sin_canonicos(self.registry.cargar()):
            if os.path.normcase(os.path.abspath(str(e.local_path))) == objetivo:
                return e
        return None

    def _solo_local(self, ref, locales, *, diagnostico, drive_accesible=True):
        """El catálogo no lo conoce: o es un scratch, o no hay nada.

        `drive_accesible` llega hasta aquí por la misma razón que existe en `_offline`:
        **sin Drive no se puede cerrar el ciclo**. Un checkout resuelto por esta rama
        con `CHECKIN` concedido anunciaría una capacidad que la red no permite ejercer
        — exactamente la «resta de capacidad inerte» que la prueba de mutación del
        Task 7 cazó en el otro camino, y que aquí no se veía porque hasta R8/H8-04
        ningún entrypoint llegaba a esta rama sin Drive.
        """
        if len(locales) > 1:
            raise AmbiguousCase(
                w_code=ref.w_code,
                detalle=f"{len(locales)} copias locales con esta identidad; "
                        "usa --case-dir")
        if not locales:
            raise LocalWorkspaceMissing(
                w_code=ref.w_code,
                detalle="ni el catalogo ni el registro conocen este caso")
        e = locales[0]
        modo = (WorkspaceMode.LOCAL_SCRATCH if e.tipo == "scratch"
                else WorkspaceMode.LOCAL_CHECKOUT)
        return self._workspace(ref, modo, e.local_path, _PROCEDENCIA_IDENTIDAD, {},
                               mutate_canonical=drive_accesible)

    def _offline(self, ref, locales, *, diagnostico):
        """§7.2.9-10 — sin Drive, solo vale un candidato local inequívoco."""
        verificados = [e for e in locales if e.tipo == "checkout"]
        if len(locales) > 1:
            raise AmbiguousCase(
                w_code=ref.w_code,
                detalle="Drive no accesible y hay mas de una copia local; "
                        "usa --case-dir")
        if not verificados:
            raise RuntimeCannotAccessWorkspace(
                w_code=ref.w_code,
                detalle="Drive no accesible y no hay checkout local verificado")
        return self._workspace(ref, WorkspaceMode.LOCAL_CHECKOUT,
                               verificados[0].local_path, _PROCEDENCIA_IDENTIDAD,
                               {}, mutate_canonical=False)

    def _bloqueo(self, ref, modo, diagnostico, error):
        """Lanza, salvo que el llamador haya pedido diagnóstico.

        Un motor que va a escribir no debe recibir un valor que parezca un
        workspace y no lo sea: así es como se escribe sobre un caso prestado sin
        enterarse. Solo quien va a **pintar** el estado pide `diagnostico=True`.
        """
        if not diagnostico:
            raise error
        return self._workspace(ref, modo, None, _PROCEDENCIA_IDENTIDAD, {})

    def _workspace(self, ref, modo, working_root, procedencia, estado,
                   *, mutate_canonical: bool = True) -> CaseWorkspace:
        # Las capacidades NO se inyectan —se derivan del modo—; lo unico que el
        # resolver puede hacer es RESTAR `MUTATE_CANONICAL` para el offline.
        return CaseWorkspace(
            case_ref=ref,
            mode=modo,
            working_root=Path(working_root) if working_root is not None else None,
            canonical_ref=None,
            checkout_user=estado.get("checkout_user"),
            checkout_maquina=estado.get("checkout_maquina"),
            checkout_nonce=estado.get("checkout_nonce"),
            checkout_timestamp=estado.get("checkout_timestamp"),
            mutate_canonical=mutate_canonical,
            validado_en=self.ahora,
            procedencia=procedencia,
        )
