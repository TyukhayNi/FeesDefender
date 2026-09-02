"""**Dónde** puede estar la raíz de trabajo de un workspace. Una propiedad, sin identidad.

Un modo local escribe **fuera** del catálogo; `drive_active`, **dentro**. Eso es todo lo que
esta pieza decide, y se contesta con `(modo, raíz, raíz del catálogo)`.

## Por qué está sola en un módulo

`CaseWorkspace.__post_init__` exige que un modo utilizable traiga raíz, pero **no** que la
raíz case con el modo. Y `CaseWorkspace` es un valor **público**: cualquiera puede construir
un `LOCAL_CHECKOUT` apuntando al canon y quedarse con el bypass del guard de desvío que los
modos locales tienen concedido (`MEJORAS #96`). La comprobación vive donde se concede el
bypass, no donde se construye el valor.

**Estaba mezclada con la regla de identidad, y esa mezcla costó cuatro rondas.** La versión
anterior preguntaba «¿la raíz es *el* canon de *este* caso?», que necesita saber qué caso es
y por tanto necesita `CaseCatalog.localizar`. Con eso, ubicación e identidad compartían
función y `canon_dir`, y **cada arreglo de una rompía la otra**:

- R25/H25-03 pidió la invariante; la primera versión la escribió contra `settings.casos_root`
  y **rompió dos tests legítimos**, porque el catálogo resuelve por otra fuente.
- R26/H26-01 midió que la segunda versión —ya contra el canon resuelto— dejaba pasar un
  workspace local del caso A apuntando al canon de **B**: preguntaba por *este* caso, no por
  el catálogo.

Enunciada como pertenencia al catálogo, la pregunta **no necesita identidad ninguna**, y
los dos casos que R26 encontró dejan de ser excepciones: son la misma frontera.

## Lo que esta pieza NO decide

Que la raíz de un `drive_active` sea **el expediente correcto** es identidad, y vive en
`escritura._identidad_de_workspace`. Aquí solo se contesta «dentro o fuera».

## Falla cerrado, en los dos modos

`INDETERMINADO` se rechaza tanto en local como en `drive_active`. No son dos reglas con
polaridades opuestas: es una sola —«hay que poder demostrarlo»— y por eso un solo módulo.
"""
from __future__ import annotations

from pathlib import Path

__all__ = ["UbicacionIncoherente", "exigir_coherente"]


class UbicacionIncoherente(ValueError):
    """La raíz de trabajo no case con el modo del workspace.

    Hereda de `ValueError` a propósito: los llamadores que ya trataban el `ValueError` de
    la versión acoplada siguen funcionando, y el tipo propio permite distinguirla de los
    demás errores de argumento cuando hace falta.
    """


def exigir_coherente(workspace) -> None:
    """Lanza `UbicacionIncoherente` si la raíz no case con el modo. No devuelve nada.

    No devuelve un booleano **a propósito**: un `bool` invita a que el llamador decida qué
    hacer con él, y lo que hay que hacer es no seguir. Es la misma polaridad que el resto
    de la costura — autorizar o lanzar, nunca informar y confiar.
    """
    from .case_catalog import DENTRO, FUERA, clasificar_bajo, raiz_del_catalogo
    from .workspace_model import WorkspaceMode

    modo = WorkspaceMode(workspace.mode)
    if modo.es_bloqueado or workspace.working_root is None:
        raise ValueError(
            "un workspace bloqueado no autoriza ninguna escritura y no tiene raiz de "
            "trabajo; el llamador debe tratar el bloqueo, no pasarlo aqui")

    donde = clasificar_bajo(Path(workspace.working_root), raiz_del_catalogo())

    if modo is WorkspaceMode.DRIVE_ACTIVE:
        if donde != DENTRO:
            raise UbicacionIncoherente(
                "un workspace `drive_active` tiene que estar DENTRO del catalogo: esta "
                "raiz cae fuera —o no se puede demostrar que no— y concederia capacidad "
                "canonica sobre algo que no es el canon")
        return

    if donde != FUERA:
        raise UbicacionIncoherente(
            "un workspace local tiene que estar FUERA del catalogo: esta raiz cae dentro "
            "—o no se puede demostrar que no—, y saltaria el guard de desvio sobre un "
            "expediente canonico")
