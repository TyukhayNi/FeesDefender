"""El catálogo de expedientes: qué existe en el canon, y qué dice el canon de ello.

Si el Drive del despacho es una biblioteca, esto es **su fichero**. Responde cuatro
preguntas y ninguna más:

| Pregunta | Método |
|---|---|
| ¿Dónde está este expediente? | `localizar(ref)` |
| ¿Qué dice el canon: disponible, prestado, en conflicto? | `estado_compartido(ref)` |
| ¿Esta ruta cae dentro de la biblioteca? | `bajo_catalogo(path)` |
| ¿Esto es un expediente, o el reflejo de uno? | `es_proyeccion_local(dir)` |

**Lo que NO hace**, y conviene que quede claro porque es la confusión fácil: no decide
sobre qué copia se trabaja —eso es el `CaseWorkspaceResolver`— ni sabe qué copias
locales tiene esta máquina —eso es el `WorkspaceRegistry`—. Solo lee el canon.

## El defecto que cierra: A-8

El §5.1 de la spec lo enuncia y aquí se midió antes de escribir nada:
`resolve_ref` recorría `list_cases()` y devolvía **el primero** cuyo `meta.id_go`
casaba. Con dos carpetas declarando `id_go: W-DUPLI` devolvía una de ellas sin aviso,
elegida por orden de escaneo — y renombrar una carpeta cambiaba la respuesta. El daño
no es cosmético: pides un expediente por W-code y el sistema trabaja sobre otro.

Ahora eso lanza `AmbiguousCase`. Y la puerta vieja, `case_locator.resolve_ref`, se
cierra también: era justamente la que elegía en silencio.

## Por qué la marca de proyección va en la misma pieza

Porque sin ella la regla de ambigüedad haría inusable el diseño. El §6.3 prevé que la
copia local lleve su propio `_caso.md` con el mismo W-code, así que habría
**deliberadamente** dos ficheros de identidad idénticos. `meta.proyeccion_local: true`
dice «esto es un reflejo, no lo cuentes», y `list_cases()` lo excluye. Regla y marca
son dos mitades de la misma decisión.
"""
from __future__ import annotations

import os
from pathlib import Path

from .. import config
from . import case_locator
from .workspace_model import AmbiguousCase, CaseRef, LocalWorkspaceMissing

__all__ = ["CaseCatalog", "MARCA_PROYECCION_LOCAL"]

#: Clave del frontmatter que marca una copia local como reflejo, no expediente.
MARCA_PROYECCION_LOCAL = "proyeccion_local"


class CaseCatalog:
    """Vista de solo lectura del repositorio canónico de expedientes."""

    # ------------------------------------------------------------- localizar

    def localizar(self, ref: CaseRef) -> Path:
        """La ruta del expediente. Estricta **siempre**.

        Lanza `LocalWorkspaceMissing` si no está y `AmbiguousCase` si hay más de
        una carpeta con la misma identidad. Nunca elige por orden de escaneo: esa
        elección silenciosa es el defecto A-8.
        """
        if ref.w_code:
            candidatas = self._por_w_code(ref.w_code)
            if len(candidatas) > 1:
                raise AmbiguousCase(
                    w_code=ref.w_code,
                    detalle=f"{len(candidatas)} carpetas del catalogo comparten "
                            f"esta identidad")
            if candidatas:
                return candidatas[0]
        if ref.case_id:
            hallada = case_locator.buscar(ref.case_id)
            if hallada is not None:
                return hallada
        raise LocalWorkspaceMissing(
            w_code=ref.w_code,
            detalle="el caso no esta en el catalogo")

    @staticmethod
    def _por_w_code(w_code: str) -> list[Path]:
        """Las carpetas del catálogo cuyo `meta.id_go` casa. Sin proyecciones.

        `list_cases()` ya excluye las proyecciones locales, así que lo que llegue
        aquí duplicado es una ambigüedad de verdad y no el reflejo esperado de un
        checkout.
        """
        objetivo = (w_code or "").strip().upper()
        halladas = []
        for case_dir in case_locator.list_cases():
            meta = case_locator.read_case_meta(case_dir)
            id_go = str(meta.get("id_go") or "").strip().upper()
            if id_go and id_go == objetivo:
                halladas.append(case_dir)
        return sorted(halladas)

    # -------------------------------------------------- el estado del canon

    def estado_compartido(self, ref: CaseRef) -> dict:
        """Qué dice el `_caso.md` **del canon** sobre el lock de este caso.

        Reutiliza el vocabulario que ya existe (`config.ESTADO_REPO_*`) y los
        lectores puros de `repository_checkout`. No inventa estados: tener dos
        vocabularios para el mismo hecho es como nacen las divergencias.

        Un `_caso.md` sin los campos de lock se lee como `disponible`, que es la
        retrocompatibilidad que el modelo ya declaraba.
        """
        from ..repository_checkout import estado_de_fm, leer_lock_de_fm

        case_dir = self.localizar(ref)
        fm = {"meta": case_locator.read_case_meta(case_dir)}
        estado = {"estado": estado_de_fm(fm)}
        estado.update(leer_lock_de_fm(fm))
        return estado

    # ------------------------------------------------------ la proyección

    @staticmethod
    def es_proyeccion_local(case_dir: Path) -> bool:
        """¿Es el reflejo de un expediente prestado, y no el expediente?"""
        meta = case_locator.read_case_meta(Path(case_dir))
        return bool(meta.get(MARCA_PROYECCION_LOCAL))

    # ------------------------------------------------------ la frontera

    @staticmethod
    def bajo_catalogo(path: Path) -> bool:
        """¿`path` cae dentro de `CASOS_ROOT`?

        Sirve para rechazar el destino de un checkout que viviría **dentro** de la
        propia biblioteca (§5.1): tendrías la copia de trabajo y el original
        mezclados, y el siguiente `list_cases()` los vería como dos expedientes.

        Compara por **componentes de ruta**, no por prefijo de cadena: `CASOS_x` no
        está bajo `CASOS` aunque su nombre empiece igual, y confundirlos daría por
        bueno un destino que está fuera.
        """
        raiz = Path(config.settings.casos_root)
        try:
            c = os.path.normcase(os.path.abspath(str(Path(path))))
            r = os.path.normcase(os.path.abspath(str(raiz)))
        except (OSError, ValueError):
            return False
        return c == r or c.startswith(r + os.sep)
