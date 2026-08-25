"""Arnés contractual de la matriz del §14.1, en los cuatro planos del §3.2-bis.

**Qué es:** las nueve filas de la matriz mínima por entrypoint mutante, escritas
**una vez como datos**, más el aparato que las siembra, ejecuta y juzga. Cualquier
entrypoint migrado al workspace dual las consume con un adaptador de tres líneas.
Hoy lo hace `scripts.sala_maquina` (`tests/test_workspace_matriz_contractual.py`);
en la Fase 3, la vertical de correo.

**Por qué no vive en cada componente.** La matriz reescrita a mano en cada
consumidor deja de ser un contrato y pasa a ser nueve tests parecidos que divergen.
Peor: cada copia decide por su cuenta qué significa «cero bytes», y el §3.2-bis
existe precisamente porque ese significado se había estado eligiendo a la baja.

---

## Los cuatro planos, y por qué el canon EXCLUYE la copia de trabajo

El §3.2-bis dice que «cero escritura» se evalúa en cuatro planos y que un componente
no puede declararla cubriendo solo el primero:

| # | Plano | Aquí es |
|---|---|---|
| 1 | Árbol del caso | `hash_arbol(raiz_trabajo)` — ficheros **y directorios** |
| 2 | Almacenamiento canónico | `hash_arbol(casos_root, excluir=raiz_trabajo)` |
| 3 | Servicios externos | el contador del doble |
| 4 | Estado local | registro privado + sentinels |

La exclusión del plano 2 no es un atajo: es lo que hace que los cuatro planos sean
**separables**, y sin separabilidad la prueba de mutación no puede existir. Con el
canon definido como «todo `CASOS_ROOT`», en el modo `drive_active` el árbol del caso
está *dentro* del canon, así que un mutante del plano 1 mataría también al 2 y el
Step 3 del Task 10 se cerraría con un mutante que no prueba lo suyo — exactamente el
modo de fallo que R7/H7-07 castigó.

Definido como «el canon **alrededor** de la copia en la que se trabaja», el plano 2
dice justo lo que el criterio de salida (2) de la Fase 1 exige: *ninguna ruta del
código crea un directorio bajo `CASOS_ROOT` para una identidad que el catálogo no
conoce*. Las carpetas fantasma viven ahí y en ningún otro sitio.

---

## Tres desviaciones respecto del Task 10 tal como estaba escrito

Las tres son del mismo tipo que R7 encontró siete veces: **una interfaz que nombra
una propiedad que su propia firma no puede expresar.** Se declaran aquí y se
adjudican en el §13 del plan.

1. **`invocar` recibe `CaseRef | Path`, no `CaseWorkspace | Path`.** Tres de las nueve
   filas —«registro local ausente», «nonce divergente» y «runtime sin acceso»— se
   resuelven con excepciones que el resolver lanza **incondicionalmente**, sin rama
   de `diagnostico`: no existe ningún `CaseWorkspace` que las represente. Con la
   firma original esas tres filas eran indatables. `CaseRef` es además lo que un
   entrypoint necesita de verdad: **la identidad, para volver a resolver él mismo.**
   Un adaptador que se creyera el workspace que le pasa el arnés no probaría nada,
   porque la autorización la habría hecho el arnés.

2. **`assert_sin_efectos` gana el plano 4.** La firma del plan
   —`(antes, despues, *, log_antes, log_despues, llamadas_externas)`— se conserva
   **literal**, y el plano 4 entra donde le corresponde: dentro de `antes`/`despues`,
   que no son hashes de un árbol sino instantáneas `Planos` de los tres planos de
   estado. Sin eso la función prometía cuatro planos y solo podía comprobar dos.

3. **La fila 8 exige que el entrypoint pueda estar sin Drive.** `sala_maquina` pasaba
   `drive_accesible=True` **literal**, así que toda la rama offline del §7.2.9-10 era
   código muerto en producción y la fila era inducible solo mintiendo. Se cierra con
   una costura real (`_drive_accesible`), no con un doble.

## Y la que NO se remedia: la cobertura ausente se declara

`no_aplicables` existe porque un entrypoint puede no poder inducir una fila —y
callarlo sería la versión de test de «un revisor que no corre no refuta». Lleva
motivo obligatorio, y `assert_matriz_completa` exige que el consumidor **fije el
conjunto exacto**: como el techo de `test_guard_localizador`, solo puede encoger sin
que alguien lo cambie a propósito.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib
import os
import textwrap
from enum import StrEnum
from pathlib import Path
from typing import Callable

__all__ = [
    "ESCENARIOS", "Escenario", "Esperado", "Mundo", "Planos", "Semilla",
    "ServicioExterno", "assert_matriz_completa", "assert_sin_efectos",
    "assert_solo_escribe_en", "hash_arbol", "matriz_para",
]

# Nombres de los planos. Se usan LITERALES en los mensajes de fallo porque la
# prueba de mutación del Step 3 comprueba que cada mutante muere POR SU PLANO, y
# eso solo se puede afirmar si el mensaje lo dice.
PLANO_ARBOL = "plano 1 (árbol del caso)"
PLANO_CANON = "plano 2 (almacenamiento canónico)"
PLANO_EXTERNOS = "plano 3 (servicios externos)"
PLANO_ESTADO_LOCAL = "plano 4 (estado local)"
PLANO_LOG = "plano 1-2 (rastro de auditoría)"

PLANOS = (PLANO_ARBOL, PLANO_CANON, PLANO_EXTERNOS, PLANO_ESTADO_LOCAL)


# ------------------------------------------------------------------ instantánea

def hash_arbol(root: Path, *, excluir: Path | None = None) -> dict[str, str]:
    """Huella de un árbol: ficheros **y directorios**, relativos a `root`.

    Los directorios cuentan porque el §3.2-bis los cuenta: una carpeta fantasma
    vacía no tiene ni un byte dentro y es exactamente el defecto que la Fase 1
    existe para cerrar. Una huella que solo mirara ficheros la declararía inocua.
    """
    root = Path(root)
    if not root.exists():
        return {}
    fuera = None
    if excluir is not None:
        fuera = os.path.normcase(os.path.abspath(str(excluir)))
    huella: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if fuera is not None:
            abs_p = os.path.normcase(os.path.abspath(str(p)))
            if abs_p == fuera or abs_p.startswith(fuera + os.sep):
                continue
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            huella[rel] = "<dir>"
        else:
            huella[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return huella


@dataclasses.dataclass(frozen=True)
class Planos:
    """Los tres planos de ESTADO del §3.2-bis. El cuarto (externos) es un contador.

    Se separa así porque el contador no es una foto de disco: se mide durante la
    ventana, no antes y después.
    """

    arbol: dict[str, str]
    canon: dict[str, str]
    estado_local: dict[str, str]


def _diferencias(antes: dict[str, str], despues: dict[str, str]) -> str:
    nuevas = sorted(set(despues) - set(antes))
    idas = sorted(set(antes) - set(despues))
    cambiadas = sorted(k for k in set(antes) & set(despues) if antes[k] != despues[k])
    trozos = []
    if nuevas:
        trozos.append(f"creadas: {nuevas[:8]}")
    if idas:
        trozos.append(f"borradas: {idas[:8]}")
    if cambiadas:
        trozos.append(f"modificadas: {cambiadas[:8]}")
    return "; ".join(trozos) or "(sin diferencias)"


def assert_sin_efectos(antes: Planos, despues: Planos, *,
                       log_antes: list, log_despues: list,
                       llamadas_externas: int) -> None:
    """Cero efectos en los CUATRO planos. Cada plano falla con su nombre dentro.

    El orden de comprobación es deliberado —árbol, canon, externos, estado local—
    pero cada aserto es independiente: un mutante del plano 3 no puede morir por el
    aserto del plano 1, porque el del 1 no lo ve.
    """
    assert antes.arbol == despues.arbol, (
        f"{PLANO_ARBOL}: el árbol del caso cambió. "
        f"{_diferencias(antes.arbol, despues.arbol)}")
    assert antes.canon == despues.canon, (
        f"{PLANO_CANON}: el almacenamiento canónico cambió alrededor de la copia "
        f"de trabajo. {_diferencias(antes.canon, despues.canon)}")
    assert llamadas_externas == 0, (
        f"{PLANO_EXTERNOS}: {llamadas_externas} llamada(s) al servicio externo; "
        f"«cero escritura» exige cero llamadas mutantes")
    assert antes.estado_local == despues.estado_local, (
        f"{PLANO_ESTADO_LOCAL}: el registro privado o un sentinel cambió. "
        f"{_diferencias(antes.estado_local, despues.estado_local)}")
    assert list(log_antes) == list(log_despues), (
        f"{PLANO_LOG}: se emitió un evento de auditoría. "
        f"antes={len(log_antes)} después={len(log_despues)}")


def assert_solo_escribe_en(plano: str, antes: Planos, despues: Planos, *,
                           log_antes: list, log_despues: list,
                           llamadas_externas: int) -> None:
    """El otro lado de la matriz: «escribe SOLO en X».

    Las filas 1, 2 y 4 del §14.1 no piden quietud, piden **puntería**. Y la puntería
    es la mitad que de verdad cuesta: «escribe solo en local» falla cuando además
    toca el canon, no cuando no escribe.
    """
    assert plano == PLANO_ARBOL, f"plano no soportado: {plano!r}"
    # El canon PRIMERO, y el orden es deliberado. Cuando un entrypoint escribe en el
    # sitio equivocado los dos asertos son ciertos a la vez —«la copia no cambió» y
    # «el canon sí»—, y el que informa de lo que pasó es el segundo. Medido con el
    # mutante que deja de consultar el catálogo: con el orden inverso, el fallo se
    # leía «el motor no llegó a correr», que es justo lo que NO ocurrió.
    assert antes.canon == despues.canon, (
        f"{PLANO_CANON}: escribió FUERA de la copia de trabajo. "
        f"{_diferencias(antes.canon, despues.canon)}")
    assert antes.arbol != despues.arbol, (
        f"{PLANO_ARBOL}: se esperaba escritura en la copia de trabajo y el árbol "
        f"quedó idéntico — el motor no llegó a correr")
    assert llamadas_externas == 0, (
        f"{PLANO_EXTERNOS}: {llamadas_externas} llamada(s) externas no declaradas")
    assert antes.estado_local == despues.estado_local, (
        f"{PLANO_ESTADO_LOCAL}: el registro privado o un sentinel cambió. "
        f"{_diferencias(antes.estado_local, despues.estado_local)}")
    assert len(log_despues) >= len(log_antes), (
        f"{PLANO_LOG}: el rastro de auditoría ENCOGIÓ")


# -------------------------------------------------------------- doble externo

class ServicioExterno:
    """Doble que cuenta, produce un efecto observable y **falla en el instante dado**.

    Los tres rasgos son el remedio de R7/H7-08, y ninguno es decorativo:

    - **cuenta** — sin contador, el plano 3 no se puede afirmar ni negar;
    - **efecto observable antes de fallar** — un doble que falla sin haber hecho nada
      no distingue «reintento seguro» de «no hizo nada»; el reintento solo es
      interesante sobre un estado a medias;
    - **instante de fallo como dato** — con `falla_en=1` se prueba *cero publicación*
      y con `falla_en=2`, *una única publicación estable*. Son las dos ramas que la
      fila 9 del §14.1 ofrece («o…, o…»), y probar una sola deja la otra sin contrato.
      Las **dos** se corren: `ESCENARIOS` declara `variantes_de_fallo=((1, 0), (2, 1))`.
      Este párrafo describió durante un rato las dos ramas mientras el escenario solo
      llevaba la primera — o sea, nombrar la propiedad y llamarlo contrato, en el mismo
      texto que advierte contra eso. La segunda rama es además la que más vale: es la
      única donde un reintento **puede** duplicar una publicación que ya existía.
    """

    def __init__(self, *, falla_en: int | None = None,
                 efecto: Callable[[int], None] | None = None,
                 devuelve: Callable[[], object] | None = None) -> None:
        self.falla_en = falla_en
        self.efecto = efecto
        self.devuelve = devuelve
        self.llamadas = 0

    def __call__(self, *args, **kwargs):
        self.llamadas += 1
        if self.efecto is not None:
            self.efecto(self.llamadas)
        if self.falla_en is not None and self.llamadas >= self.falla_en:
            raise RuntimeError(f"servicio externo caído (llamada {self.llamadas})")
        return self.devuelve() if self.devuelve is not None else []


# ------------------------------------------------------------------ el mundo

@dataclasses.dataclass(frozen=True)
class Semilla:
    """Lo que devuelve el sembrado: a quién invocar y dónde mirar el plano 1."""

    objetivo: object                 #: `CaseRef` (identidad) o `Path` (`--case-dir`)
    raiz_trabajo: Path               #: la copia sobre la que el entrypoint operaría


class Mundo:
    """Un `CASOS_ROOT`, un registro privado y una identidad. Nada más.

    **Restaura `core.config` al salir**, y eso no es higiene opcional: el 65º cierre
    midió que una fixture que recarga `core.config` al entrar y no al salir deja el
    módulo apuntando al `tmp_path` de ese test para todo lo que corra después. Con la
    semilla 777 eso costó ocho fallos en un PR que iba a mergearse. Cada pieza nueva
    que consulte el catálogo pisa esa misma mina, y esta es una.

    El registro privado se redirige por **variable de entorno**
    (`FEESDEFENDER_WORKSPACE_REGISTRY`, que `raiz_por_defecto()` ya honra) y no
    parcheando una costura del entrypoint. Es deliberado: así el arnés no sabe nada
    del consumidor, y lo que se ejercita es el camino de producción.
    """

    W_CODE = "W-MTZ01"
    CASE_ID = f"BaRS0 - Matriz contractual - ({W_CODE}) - Honorarios"
    AHORA = "2026-08-25T12:00:00Z"

    def __init__(self, base: Path, monkeypatch, *, usuario: str, maquina: str) -> None:
        self.usuario = usuario
        self.maquina = maquina
        self.base = base
        self.casos_root = base / "CASOS"
        self.casos_root.mkdir(parents=True)
        self.raiz_registro = base / "registro"
        self.sentinels: dict[str, str] = {}
        self.monkeypatch = monkeypatch

        monkeypatch.setenv("CASOS_ROOT", str(self.casos_root))
        monkeypatch.setenv("FEESDEFENDER_WORKSPACE_REGISTRY", str(self.raiz_registro))
        monkeypatch.delenv("FEESDEFENDER_OFFLINE", raising=False)
        from core import config as cfg
        importlib.reload(cfg)
        self._cfg = cfg

    def cerrar(self) -> None:
        """Devuelve `core.config` al `CASOS_ROOT` real. Llamar SIEMPRE en `finally`."""
        self.monkeypatch.undo()
        importlib.reload(self._cfg)

    # ------------------------------------------------------------- sembrado

    def registro(self):
        from core.casos.workspace_registry import WorkspaceRegistry
        return WorkspaceRegistry(self.raiz_registro, ahora=self.AHORA)

    def sembrar_canon(self, *, estado: str = "disponible", titular: str | None = None,
                      maquina: str | None = None, nonce: str | None = None) -> Path:
        """El expediente en el canon, con el estado de lock que diga el escenario."""
        case_dir = self.casos_root / self.CASE_ID
        entrada = case_dir / "00_Input"
        entrada.mkdir(parents=True, exist_ok=True)
        meta = {"id_go": self.W_CODE, "estado_repositorio": estado}
        for clave, valor in (("checkout_user", titular),
                             ("checkout_maquina", maquina),
                             ("checkout_nonce", nonce)):
            if valor:
                meta[clave] = valor
        if estado == "prestado":
            meta["checkout_timestamp"] = self.AHORA
        cuerpo = "\n".join(f"  {k}: {v}" for k, v in meta.items())
        (entrada / "_caso.md").write_text(
            textwrap.dedent(f"---\nmeta:\n{cuerpo}\n---\n"), encoding="utf-8")
        (entrada / "documento.txt").write_text("contenido\n", encoding="utf-8")
        return case_dir

    def sembrar_local(self, *, tipo: str, nonce: str, nombre: str = "Desktop") -> Path:
        """Una copia local registrada. FUERA de `CASOS_ROOT`, como manda el §5.1."""
        from core.casos.workspace_registry import SCHEMA_SOPORTADO, WorkspaceEntry
        local = self.base / nombre / self.CASE_ID
        (local / "00_Input").mkdir(parents=True, exist_ok=True)
        (local / "00_Input" / "documento.txt").write_text("contenido\n",
                                                          encoding="utf-8")
        self.registro().alta(WorkspaceEntry(
            case_id=self.CASE_ID, w_code=self.W_CODE, canonical_ref=None,
            local_path=local, nonce=nonce, maquina=self.maquina, tipo=tipo,
            ultima_validacion=self.AHORA, schema=SCHEMA_SOPORTADO))
        return local

    def ref(self):
        from core.casos.workspace_model import CaseRef
        return CaseRef(case_id=self.CASE_ID, w_code=self.W_CODE)

    # ---------------------------------------------------------- observación

    def planos(self, raiz_trabajo: Path) -> Planos:
        estado_local = {f"registro/{k}": v
                        for k, v in hash_arbol(self.raiz_registro).items()}
        estado_local.update({f"sentinel/{k}": str(v)
                             for k, v in self.sentinels.items()})
        return Planos(
            arbol=hash_arbol(raiz_trabajo),
            canon=hash_arbol(self.casos_root, excluir=raiz_trabajo),
            estado_local=estado_local,
        )

    @staticmethod
    def log(case_dir: Path) -> list:
        from core.intake_log import read_events_de
        return read_events_de(Path(case_dir))


# --------------------------------------------------------------- escenarios

class Esperado(StrEnum):
    ESCRIBE_EN_LA_COPIA = "escribe_en_la_copia"
    CERO_EFECTOS = "cero_efectos"
    IDEMPOTENTE = "idempotente"


@dataclasses.dataclass(frozen=True)
class Escenario:
    id: str
    fila: str                                   #: el texto literal del §14.1
    sembrar: Callable[["Mundo"], Semilla]
    esperado: Esperado
    #: Filas bloqueadas: el código del §10 que el contrato exige, literal.
    #:
    #: Sin él, el juez solo comprobaba `codigo != 0` y **cualquier** aborto controlado
    #: pasaba por bueno — R8/H8-01 lo midió sustituyendo el adaptador por un
    #: `typer.Exit(99)` y la fila siguió verde. Un montaje que cae por la guarda
    #: equivocada conservaba en verde la fila que dice aislar otra, que es exactamente
    #: mi modo de fallo dominante: el escenario más fácil de montar, no el que aísla.
    codigo_error: str = ""
    #: Solo la fila 9: pares `(instante de fallo, publicaciones que el contrato admite)`.
    #: El instante es DATO del escenario, y son **dos** variantes y no una porque el
    #: §14.1 ofrece dos ramas —«reintento seguro **o** aborto idempotente»— y probar
    #: una sola deja la otra sin contrato. Con `(1, 0)` el doble cae en la primera
    #: llamada y se exige **cero publicación**; con `(2, 1)`, la primera invocación
    #: llega a publicar y la segunda cae, así que se exige **una única publicación
    #: estable** — que es la rama donde de verdad se ve si el reintento duplica.
    variantes_de_fallo: tuple[tuple[int, int], ...] = ()


def _sembrar_drive_disponible(m: Mundo) -> Semilla:
    canon = m.sembrar_canon(estado="disponible")
    return Semilla(objetivo=m.ref(), raiz_trabajo=canon)


def _sembrar_checkout_propio(m: Mundo) -> Semilla:
    m.sembrar_canon(estado="prestado", titular=m.usuario, maquina=m.maquina,
                    nonce="n1")
    local = m.sembrar_local(tipo="checkout", nonce="n1")
    return Semilla(objetivo=m.ref(), raiz_trabajo=local)


def _sembrar_checkout_ajeno(m: Mundo) -> Semilla:
    canon = m.sembrar_canon(estado="prestado", titular="otro.abogado",
                            maquina="OTRA-MAQUINA", nonce="n9")
    return Semilla(objetivo=m.ref(), raiz_trabajo=canon)


def _sembrar_scratch_local(m: Mundo) -> Semilla:
    scratch = m.sembrar_local(tipo="scratch", nonce="s1")
    return Semilla(objetivo=scratch, raiz_trabajo=scratch)


def _sembrar_conflicto(m: Mundo) -> Semilla:
    canon = m.sembrar_canon(estado="conflicto")
    return Semilla(objetivo=m.ref(), raiz_trabajo=canon)


def _sembrar_registro_ausente(m: Mundo) -> Semilla:
    # El canon dice que lo tengo YO, en ESTA máquina — y el registro está vacío.
    # §15: un checkout que esta máquina no registró no se adopta solo. Lo que la
    # fila prueba es el «sin fallback»: que no se caiga al canon «porque es mío».
    canon = m.sembrar_canon(estado="prestado", titular=m.usuario,
                            maquina=m.maquina, nonce="n1")
    return Semilla(objetivo=m.ref(), raiz_trabajo=canon)


def _sembrar_nonce_divergente(m: Mundo) -> Semilla:
    m.sembrar_canon(estado="prestado", titular=m.usuario, maquina=m.maquina,
                    nonce="n-canon")
    local = m.sembrar_local(tipo="checkout", nonce="n-local")
    return Semilla(objetivo=m.ref(), raiz_trabajo=local)


def _sembrar_runtime_sin_acceso(m: Mundo) -> Semilla:
    # Sin Drive y sin checkout local verificado: §7.2.9-10 no tiene sobre qué caer.
    canon = m.sembrar_canon(estado="disponible")
    m.monkeypatch.setenv("FEESDEFENDER_OFFLINE", "1")
    return Semilla(objetivo=m.ref(), raiz_trabajo=canon)


def _sembrar_servicio_externo(m: Mundo) -> Semilla:
    canon = m.sembrar_canon(estado="disponible")
    return Semilla(objetivo=m.ref(), raiz_trabajo=canon)


#: Las NUEVE filas del §14.1, como datos. El orden es el de la spec.
ESCENARIOS: tuple[Escenario, ...] = (
    Escenario("drive_disponible", "Drive disponible → escribe solo en Drive",
              _sembrar_drive_disponible, Esperado.ESCRIBE_EN_LA_COPIA),
    Escenario("checkout_propio", "Checkout propio → escribe solo en local",
              _sembrar_checkout_propio, Esperado.ESCRIBE_EN_LA_COPIA),
    Escenario("checkout_ajeno", "Checkout ajeno → cero bytes nuevos o modificados",
              _sembrar_checkout_ajeno, Esperado.CERO_EFECTOS,
              codigo_error="CASE_LOCKED"),
    Escenario("scratch_local", "Scratch local → escribe solo en scratch",
              _sembrar_scratch_local, Esperado.ESCRIBE_EN_LA_COPIA),
    Escenario("conflicto", "Conflicto → cero mutación",
              _sembrar_conflicto, Esperado.CERO_EFECTOS,
              codigo_error="CASE_CONFLICT"),
    Escenario("registro_local_ausente", "Registro local ausente → error, sin fallback",
              _sembrar_registro_ausente, Esperado.CERO_EFECTOS,
              codigo_error="LOCAL_WORKSPACE_MISSING"),
    Escenario("nonce_divergente", "Nonce divergente → error, local conservado",
              _sembrar_nonce_divergente, Esperado.CERO_EFECTOS,
              codigo_error="LOCK_MISMATCH"),
    Escenario("runtime_sin_acceso", "Runtime sin acceso → error, Drive intacto",
              _sembrar_runtime_sin_acceso, Esperado.CERO_EFECTOS,
              codigo_error="RUNTIME_CANNOT_ACCESS_WORKSPACE"),
    Escenario("servicio_externo_falla",
              "Servicio externo falla → reintento seguro o aborto idempotente",
              _sembrar_servicio_externo, Esperado.IDEMPOTENTE,
              variantes_de_fallo=((1, 0), (2, 1))),
)


# ------------------------------------------------------------------- el arnés

def matriz_para(invocar: Callable[[object], int], *,
                mundo: Callable[[str], Mundo],
                servicio: Callable[[Mundo, ServicioExterno], None] | None = None,
                contador_externo: Callable[[Mundo], ServicioExterno] | None = None,
                sin_superficie_externa: str = "",
                escenarios: tuple[Escenario, ...] = ESCENARIOS,
                no_aplicables: dict[str, str] | None = None) -> dict[str, str]:
    """Corre la matriz contra `invocar` y devuelve el informe `{id: veredicto}`.

    `invocar` recibe la identidad (`CaseRef`) o la ruta explícita (`Path`) y **vuelve
    a resolver por su cuenta**: el arnés no le entrega autorización, porque entonces
    estaría probándose a sí mismo. Devuelve el código de salida.

    Los dos ganchos del plano 3 son distintos y no se pueden fundir:

    - `contador_externo` instala un doble **que solo cuenta** sobre la superficie
      mutante del entrypoint, y se usa en las filas de efecto: es lo que da contenido
      al «ninguna llamada mutante a CRM, Gmail o Drive» del §3.2-bis.
    - `servicio` instala el doble **que falla**, y solo lo usa la fila 9. Ahí el
      contador NO se cablea aparte, y no es un olvido: en esa fila la superficie
      externa **es** el doble que falla, y su contador ya se asierta
      (`doble.llamadas == llamadas_1 * 2`). Instalar dos dobles sobre la misma costura
      dejaría al segundo pisando al primero. R8/H8-02 vio el parámetro recibido y sin
      usar y tenía razón en que sobraba: se retiró, no se cableó por cumplir.

    Y si el entrypoint no tiene superficie externa mutante, hay que **decirlo**:
    `sin_superficie_externa` exige el motivo por escrito. Sin esa exigencia, el
    `assert llamadas == 0` del plano 3 sería cierto por vacío en todos los
    consumidores y nadie se enteraría — que es la forma de test de dar por refutado
    lo que nadie miró.
    """
    no_aplicables = dict(no_aplicables or {})
    for clave, motivo in no_aplicables.items():
        if not (motivo or "").strip():
            raise ValueError(
                f"la fila {clave!r} se declara no aplicable sin motivo: la cobertura "
                f"ausente se declara, no se calla")
    if contador_externo is None and not (sin_superficie_externa or "").strip():
        raise ValueError(
            "el plano 3 exige o un `contador_externo` sobre la superficie mutante del "
            "entrypoint, o `sin_superficie_externa=<motivo>` por escrito. Un contador "
            "que nadie cablea vale cero siempre y no prueba nada")
    informe: dict[str, str] = {}
    for esc in escenarios:
        if esc.id in no_aplicables:
            continue
        if esc.esperado is Esperado.IDEMPOTENTE:
            informe[esc.id] = _correr_idempotencia(esc, invocar, mundo, servicio)
        else:
            informe[esc.id] = _correr_efectos(esc, invocar, mundo, contador_externo)
    return informe


def _correr_efectos(esc: Escenario, invocar, mundo, contador_externo) -> str:
    m = mundo(esc.id)
    try:
        semilla = esc.sembrar(m)
        doble = contador_externo(m) if contador_externo else ServicioExterno()
        antes = m.planos(semilla.raiz_trabajo)
        log_antes = m.log(semilla.raiz_trabajo)
        codigo, error, err = _ejecutar(invocar, semilla.objetivo)
        despues = m.planos(semilla.raiz_trabajo)
        log_despues = m.log(semilla.raiz_trabajo)
        if esc.esperado is Esperado.CERO_EFECTOS:
            assert codigo != 0, (
                f"[{esc.id}] {esc.fila}: el entrypoint terminó con éxito ({codigo}) "
                f"donde el contrato exige un error")
            assert error is None, (
                f"[{esc.id}] {esc.fila}: abortó, pero con una excepción NO controlada "
                f"({type(error).__name__}: {error}). Un bloqueo del contrato se "
                f"presenta con su código del §10, no con una traza")
            _exigir_codigo_del_10(esc, err)
            assert_sin_efectos(antes, despues, log_antes=log_antes,
                               log_despues=log_despues,
                               llamadas_externas=doble.llamadas)
            marca = "" if contador_externo else " (plano 3 sin superficie declarada)"
            return (f"cero efectos en los 4 planos; salida {codigo}; "
                    f"{esc.codigo_error}{marca}")
        assert codigo == 0, (
            f"[{esc.id}] {esc.fila}: el entrypoint abortó ({codigo}) donde el "
            f"contrato exige que escriba en la copia de trabajo"
            + (f" — {type(error).__name__}: {error}" if error else ""))
        assert_solo_escribe_en(PLANO_ARBOL, antes, despues, log_antes=log_antes,
                               log_despues=log_despues,
                               llamadas_externas=doble.llamadas)
        return "escribió solo en la copia de trabajo"
    finally:
        m.cerrar()


def _exigir_codigo_del_10(esc: Escenario, err: str) -> None:
    """La fila abortó **por su motivo**, no por cualquier guarda que salga con != 0.

    Se lee del `stderr` capturado porque es lo que ve el operador: el §10 dice que cada
    interfaz presenta el error «sin cambiar su significado», así que el código impreso ES
    el contrato observable. Y si el adaptador no imprime nada, **falla**: un canal vacío
    haría vacua esta comprobación, que es justo el defecto que viene a cerrar.
    """
    assert esc.codigo_error, (
        f"[{esc.id}] la fila espera un aborto y no declara `codigo_error`: sin él, "
        f"cualquier salida != 0 pasa por buena (R8/H8-01)")
    assert err.strip(), (
        f"[{esc.id}] el entrypoint abortó sin escribir NADA en stderr, así que no hay "
        f"forma de saber por qué guarda salió. El §10 exige que el error se presente")
    assert esc.codigo_error in err, (
        f"[{esc.id}] {esc.fila}: abortó por el motivo EQUIVOCADO. Se esperaba "
        f"{esc.codigo_error} y stderr dice: {err.strip()[:300]}")


def _correr_idempotencia(esc: Escenario, invocar, mundo, servicio) -> str:
    """La fila 9, con las cuatro piezas que R7/H7-08 exigió.

    Doble que falla **después** de un efecto observable, instante de fallo como dato,
    contador de llamadas y **segunda invocación**. Sin la segunda no se prueba
    «reintento seguro o aborto idempotente», que es lo que la fila promete.
    """
    if servicio is None:
        raise ValueError(
            "la fila 'servicio_externo_falla' exige el cableado `servicio=`: sin "
            "doble no se induce el fallo y la fila queda decorativa (R7/H7-08)")
    if not esc.variantes_de_fallo:
        raise ValueError(
            f"la fila {esc.id!r} es IDEMPOTENTE y no declara `variantes_de_fallo`: "
            f"sin instante de fallo no hay nada que inducir")
    veredictos = [
        _una_variante(esc, invocar, mundo, servicio, falla_en, admitidas)
        for falla_en, admitidas in esc.variantes_de_fallo
    ]
    return " | ".join(veredictos)


def _una_variante(esc: Escenario, invocar, mundo, servicio, falla_en: int,
                  admitidas: int) -> str:
    m = mundo(f"{esc.id}_falla_en_{falla_en}")
    try:
        semilla = esc.sembrar(m)
        efectos: list[Path] = []

        def _efecto(n: int) -> None:
            marca = Path(semilla.raiz_trabajo) / "_efecto_observable.txt"
            marca.write_text("el servicio externo llegó a producir salida\n",
                             encoding="utf-8")
            efectos.append(marca)

        doble = ServicioExterno(falla_en=falla_en, efecto=_efecto)
        servicio(m, doble)

        # BASELINE antes del primer intento. R8/H8-02: sin él, esta fila solo
        # comparaba el árbol ENTRE los dos intentos, así que un entrypoint que mutara
        # el canon o el registro **en las dos** invocaciones por igual quedaba verde y
        # rotulado «aborto idempotente». Dos mutantes del revisor pasaron así.
        base = m.planos(semilla.raiz_trabajo)

        codigo_1, error_1, _err1 = _ejecutar(invocar, semilla.objetivo)
        tras_primera = hash_arbol(semilla.raiz_trabajo)
        planos_1 = m.planos(semilla.raiz_trabajo)
        publicaciones_1 = len(m.log(semilla.raiz_trabajo))
        llamadas_1 = doble.llamadas

        codigo_2, error_2, _err2 = _ejecutar(invocar, semilla.objetivo)
        tras_segunda = hash_arbol(semilla.raiz_trabajo)
        planos_2 = m.planos(semilla.raiz_trabajo)
        publicaciones_2 = len(m.log(semilla.raiz_trabajo))

        # El fallo externo se PROPAGA. Un entrypoint que se lo traga y devuelve 0
        # informa de un éxito que no ocurrió, y sin este aserto pasaba por idempotente.
        for i, (codigo, err_i) in enumerate(((codigo_1, error_1),
                                             (codigo_2, error_2)), start=1):
            if i >= falla_en:
                assert codigo != 0, (
                    f"[{esc.id}/falla_en={falla_en}] la invocación {i} devolvió "
                    f"ÉXITO ({codigo}) pese a que el servicio externo cayó: un fallo "
                    f"tragado es peor que un fallo")
            else:
                assert codigo == 0, (
                    f"[{esc.id}/falla_en={falla_en}] la invocación {i} abortó "
                    f"({codigo}) antes de que el servicio externo llegara a caer"
                    + (f" — {type(err_i).__name__}: {err_i}" if err_i else ""))

        # Los planos 2 y 4 se comparan contra el BASELINE, no entre intentos: un
        # reintento sobre un canon ya contaminado sería «estable» y estaría mal.
        assert base.canon == planos_1.canon == planos_2.canon, (
            f"[{esc.id}/falla_en={falla_en}] {PLANO_CANON}: el fallo externo o su "
            f"reintento tocaron el canon. "
            f"{_diferencias(base.canon, planos_2.canon)}")
        assert base.estado_local == planos_1.estado_local == planos_2.estado_local, (
            f"[{esc.id}/falla_en={falla_en}] {PLANO_ESTADO_LOCAL}: el registro o un "
            f"sentinel cambió durante el fallo o el reintento. "
            f"{_diferencias(base.estado_local, planos_2.estado_local)}")

        assert llamadas_1 >= 1, (
            f"[{esc.id}] el doble NUNCA se llamó: el fallo externo no se indujo, "
            f"así que esta fila no prueba nada (R7/H7-08)")
        assert efectos, (
            f"[{esc.id}] el doble falló SIN efecto observable previo: sobre un "
            f"estado limpio, «reintento seguro» no se distingue de «no hizo nada»")
        assert doble.llamadas == llamadas_1 * 2, (
            f"[{esc.id}] {PLANO_EXTERNOS}: la segunda invocación hizo "
            f"{doble.llamadas - llamadas_1} llamada(s) frente a {llamadas_1} de la "
            f"primera; un reintento no amplifica el tráfico externo")
        assert publicaciones_1 == admitidas, (
            f"[{esc.id}/falla_en={falla_en}] tras la primera invocación hubo "
            f"{publicaciones_1} publicación(es) y el contrato admite {admitidas}")
        assert publicaciones_2 == publicaciones_1, (
            f"[{esc.id}] la segunda invocación publicó de nuevo "
            f"({publicaciones_1} → {publicaciones_2}): no es idempotente")
        assert tras_segunda == tras_primera, (
            f"[{esc.id}] {PLANO_ARBOL}: el reintento dejó un árbol distinto. "
            f"{_diferencias(tras_primera, tras_segunda)}")
        return (f"falla_en={falla_en}: {publicaciones_1} publicación(es) estable(s), "
                f"{doble.llamadas} llamadas, árbol idéntico entre reintentos")
    finally:
        m.cerrar()


def _ejecutar(invocar, objetivo) -> tuple[int, BaseException | None, str]:
    """Ejecuta el adaptador y normaliza la salida a `(codigo, error)`.

    `typer.Exit` es la forma que tiene un CLI de este repo de decir «he abortado», y
    los tests lo invocan como función. Se traduce aquí para que el contrato hable de
    **códigos de salida**, que es lo que un operador ve, y no de excepciones.

    Una excepción **no controlada** también es un código de salida —el 1 con traza que
    ve el operador— y se conserva para poder decirlo en el mensaje de fallo. Tragarla
    sin más convertiría un `AttributeError` en un «abortó, correcto» silencioso.
    """
    import contextlib
    import io as _io

    import typer

    err = _io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            codigo = invocar(objetivo)
    except typer.Exit as exc:
        return int(exc.exit_code or 0), None, err.getvalue()
    except SystemExit as exc:                      # pragma: no cover - defensivo
        return int(exc.code or 0), None, err.getvalue()
    except Exception as exc:                       # noqa: BLE001
        return 1, exc, err.getvalue()
    return int(codigo or 0), None, err.getvalue()


def assert_matriz_completa(informe: dict[str, str], *,
                           no_aplicables: dict[str, str] | None = None) -> None:
    """Las nueve filas, o una declaración explícita de por qué no.

    El aserto de igualdad de conjuntos es la mitad importante: un informe con ocho
    veredictos verdes y una fila que nadie corrió se lee exactamente igual que uno
    completo si solo se mira que no haya rojos.
    """
    no_aplicables = dict(no_aplicables or {})
    esperadas = {e.id for e in ESCENARIOS}
    cubiertas = set(informe) | set(no_aplicables)
    assert cubiertas == esperadas, (
        f"la matriz del §14.1 tiene {len(esperadas)} filas y se cubrieron "
        f"{len(cubiertas)}. Sin cubrir: {sorted(esperadas - cubiertas)}. "
        f"Sobrantes: {sorted(cubiertas - esperadas)}")
    assert not (set(informe) & set(no_aplicables)), (
        "una fila no puede estar a la vez corrida y declarada no aplicable")
    for clave, veredicto in informe.items():
        assert (veredicto or "").strip(), f"la fila {clave!r} no dejó veredicto"
