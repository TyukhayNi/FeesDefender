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

__all__ = ["CaseCatalog", "MARCA_PROYECCION_LOCAL", "bajo_catalogo", "clasificar_bajo",
           "DENTRO", "FUERA", "INDETERMINADO"]

#: Clave del frontmatter que marca una copia local como reflejo, no expediente.
MARCA_PROYECCION_LOCAL = "proyeccion_local"

#: Los tres resultados de `clasificar_bajo`. **Son tres y no dos**, y ésa es la
#: corrección que R22/H22-04 obligó a hacer: colapsarlos en un booleano obliga a
#: elegir una polaridad, y los consumidores tienen polaridades OPUESTAS.
#:
#: Quien **autoriza** una escritura debe leer «no lo sé» como «no». Quien **lee** el
#: registro no puede: ahí «no lo sé» tratado como «dentro» hacía **desaparecer** una
#: entrada legítima, y con ella los bytes en la siguiente reescritura. Un booleano no
#: puede servir a los dos, y la primera versión de este arreglo lo intentó.
DENTRO = "dentro"
FUERA = "fuera"
INDETERMINADO = "indeterminado"

#: Cuántos ancestros se recorren buscando identidad física. Un tope explícito, porque
#: un ciclo de reparse points haría infinito el ascenso.
_MAX_ANCESTROS = 64


def _sin_prefijo_extendido(s: str) -> str:
    r"""Quita el espacio de nombres extendido de Windows (`\\?\`, `\\?\UNC\`).

    R22/H22-01, medido: `\\?\C:\…\CASOS\Caso` y `C:\…\CASOS\Caso` son **el mismo
    directorio** (`os.path.samefile` → `True`) y la comparación de cadenas los daba
    distintos, así que la forma extendida se clasificaba **fuera** del catálogo.
    """
    if s.startswith("\\\\?\\UNC\\"):
        return "\\\\" + s[8:]
    if s.startswith("\\\\?\\"):
        return s[4:]
    return s


def _componentes(p) -> tuple[str, ...]:
    """Los componentes normalizados de `p` como ruta absoluta.

    Se compara por **componentes**, no por prefijo de cadena, y eso arregla dos cosas a
    la vez: `CASOS_x` deja de estar «bajo» `CASOS` (falso positivo), y un catálogo
    configurado en la **raíz de un volumen** reconoce a sus descendientes — con `C:\\` el
    viejo `r + os.sep` buscaba el prefijo `c:\\\\`, que no casa con nada (R22/H22-06).
    """
    s = _sin_prefijo_extendido(str(Path(p)))
    return tuple(os.path.normcase(x) for x in Path(os.path.abspath(s)).parts)


def _dentro_fisicamente(candidata: Path, raiz: Path):
    """¿`candidata` está físicamente bajo `raiz`? `None` = no se pudo determinar.

    Sube por los ancestros comparando **identidad de directorio** (`os.path.samestat`),
    no cadenas. Es lo único que cierra a la vez la *junction*, el alias 8.3, el nombre
    Volume GUID y la ruta UNC: todas escriben el mismo directorio de forma distinta, y
    el sistema de ficheros sí sabe que es el mismo.

    Se asciende porque la pregunta es de **contención**, no de igualdad, y porque la ruta
    por la que se pregunta puede no existir todavía —el caso normal al autorizar un
    destino—: se compara desde el primer ancestro que sí existe.
    """
    try:
        st_raiz = os.stat(raiz)
    except OSError:
        # Si la raíz no existe, nada puede estar físicamente dentro de ella. No es
        # fallo abierto: es que la pregunta física no tiene sujeto.
        return False
    p = Path(os.path.abspath(_sin_prefijo_extendido(str(candidata))))
    for _ in range(_MAX_ANCESTROS):
        try:
            if os.path.samestat(os.stat(p), st_raiz):
                return True
        except FileNotFoundError:
            pass                       # ese ancestro no existe: se sigue subiendo
        except OSError:
            return None                # permisos, dispositivo: NO se puede determinar
        if p.parent == p:
            return False
        p = p.parent
    return None


def clasificar_bajo(path, raiz) -> str:
    """`DENTRO` / `FUERA` / `INDETERMINADO`. **La única definición, para todos.**

    Vive aquí, a nivel de módulo y con la raíz como parámetro, para que la frontera que
    escribe en el registro pueda usarla sin arrastrar `CaseCatalog` — y para que no haya
    una segunda definición que diverja. Cuando la hubo, divergió: el constructor del
    registro comparaba con su propio `_bajo` sin `abspath` ni identidad física, y admitía
    una raíz que por una *junction* caía dentro del catálogo (R22/H22-03).
    """
    try:
        c, r = _componentes(path), _componentes(raiz)
    except (OSError, ValueError):
        return INDETERMINADO
    if len(c) >= len(r) and c[:len(r)] == r:
        return DENTRO
    try:
        fisico = _dentro_fisicamente(Path(path), Path(raiz))
    except (OSError, ValueError, RuntimeError):
        return INDETERMINADO
    if fisico is None:
        return INDETERMINADO
    return DENTRO if fisico else FUERA


def bajo_catalogo(path: Path) -> bool:
    """¿`path` cae dentro de `CASOS_ROOT`? **Para quien AUTORIZA, y falla CERRADO.**

    `INDETERMINADO` cuenta como `DENTRO`: «no puedo saber dónde cae» no es «cae fuera».
    Es la polaridad correcta para autorizar una escritura, y **la equivocada para leer**
    — por eso quien lee el registro usa `clasificar_bajo` y distingue los tres estados.

    `MEJORAS #136` midió lo que costaba no tener esto donde se escribe: `adoptar`
    aceptaba la ruta del canon y desde ahí el intake escribía sobre el expediente
    prestado **sin desviar**.
    """
    return clasificar_bajo(path, Path(config.settings.casos_root)) != FUERA


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
        """Delega en :func:`bajo_catalogo`. **La lógica ya no vive aquí.**

        Se conserva el método porque `resolver_por_ruta` y sus tests lo llaman por este
        nombre; lo que se retira es que la definición estuviera colgada de una clase que
        la frontera de escritura no puede importar sin arrastrarla entera. Dos copias de
        «¿está bajo el catálogo?» es como nacen las divergencias, y `MEJORAS #136` es lo
        que cuesta tenerla en un solo lector.
        """
        return bajo_catalogo(path)
