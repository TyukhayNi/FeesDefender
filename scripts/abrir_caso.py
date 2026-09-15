"""CLI local: abrir un expediente E&V (alta + intake + CRM) en una pasada.

Orquestador fino sobre el cerebro puro core.abrir_caso. Único módulo con I/O.
El intake soporta varias fuentes vía --fuente (una por invocación; reentrante):
drive_ev (default, pull rclone), manual (carpeta o .zip), whatsapp (export .zip)
y email (export de etiqueta Gmail).

Para montar solo el esqueleto (sin intake ni CRM), usa `scripts/init_caso.py`.

Uso:
  python -m scripts.abrir_caso --w-code W-02Z2NR --ciudad Barcelona \\
      --tipo-caso VUELTA --codigo-caso BaRS11 --sufijo "Vuelta" \\
      --direccion "Passeig Marítim, 30 - Castelldefels (08860)" \\
      --folder-id <id> --team-id <shared-drive>
  python -m scripts.abrir_caso ... --fuente manual --src <carpeta|.zip>
  python -m scripts.abrir_caso ... --fuente whatsapp --src <.zip> --rol "03_Otros"
  python -m scripts.abrir_caso ... --fuente email --cuenta <gmail> --label <etiqueta>

Intake incremental (identidad desde _caso.md, sin repetir los 6 flags):
  python -m scripts.abrir_caso --case-id W-02Z2NR --fuente manual --src <carpeta|.zip>
  python -m scripts.abrir_caso --case-id W-02Z2NR --fuente email --cuenta <gmail> --label <etiqueta>
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from collections import namedtuple
import stat
import zipfile
from pathlib import Path

import typer

from core import abrir_caso as brain
from core.abrir_caso import FicheroSinVerificar
from core.intake_control import es_fichero_de_protocolo
from core import (
    alta_crm_politica, case_manager, config, email_export, intake_drive, intake_log,
    intake_manual, sudespacho_create, sudespacho_relations, whatsapp_intake,
)
from core import apertura_v1 as av1
from core import apertura_v1_estado as estado_v1
from core.casos import case_locator, mutex_sesion
from core.casos.workspace_model import CaseRef
from core.ciudades import CIUDADES
# `now_iso_utc` y NO `now_iso`: la primitiva del mutex rechaza a proposito un instante sin
# offset, porque un timestamp naive se lee en hora LOCAL y el lease se calcularia mal.
from core.utils import file_sha256, now_iso_utc

app = typer.Typer(add_completion=False, help="Abrir un expediente E&V en una pasada")

_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"

#: Nombres de las etapas de V1, en orden. Es tambien el vocabulario de `--hasta`.
ETAPAS_V1 = ("drive", "crm", "sala_maquina")
#: V2 AMPLIA V1 por la derecha: las tres primeras conservan nombre y orden, asi que un
#: `--hasta sala_maquina` de antes sigue parando donde paraba. `crm_ficha` NO esta:
#: llevar el YAML al CRM ejecuta los efectos materiales de la §8.1, que el spec situa
#: DESPUES de la sala de lectura y la viabilidad (R1/H-05).
ETAPAS_V2 = ETAPAS_V1 + ("crm_alta", "actuacion", "verificar")

#: Lo que `_alta_crm` hizo de verdad. Devolvia `None` en SEIS situaciones distintas, y
#: quien lo consumiera no podia distinguir «ya estaba vinculado» de «el POST dio timeout»
#: (R1/H-02). El modo `libre` ignora el retorno, asi que anadirlo no le cambia nada.
ResultadoAlta = namedtuple("ResultadoAlta", "estado exp_id detalle")
#: Vocabulario cerrado de `ResultadoAlta.estado`.
ESTADOS_ALTA = ("creado", "ya_vinculado", "declinado", "omitido",
                "fallo_post", "fallo_registro")
#: Vocabulario cerrado de `--crm`. Antes vivia implicito en el help del flag.
_CRM_MODOS = ("api", "skip")

#: Intentos que la sala de maquina da a un documento antes de saltarlo. Se lee del
#: motor y no se copia: un numero a mano aqui se pudre cuando alli cambie.
from core.sala_maquina import MAX_INTENTOS as SM_MAX_INTENTOS  # noqa: E402


class AbortarApertura(Exception):
    """El intake no puede seguir. **No termina el proceso: lo decide el entrypoint.**

    Existe por `MEJORAS #142`. Las funciones de intake lanzaban `typer.Exit` desde DENTRO
    del bloque de mutex, y eso rompe la propiedad que R12/H12-04 construyo: el `finally`
    de `case_mutex.tomado` **lanza** `MutexPerdido` si el bloque sale limpio y solo lo
    **anota** si hay una excepcion en vuelo. Con un `Exit` en vuelo la perdida de exclusion
    quedaba en una nota que Typer descarta al formatear la salida: invisible.

    Una excepcion de dominio no arregla eso por si sola —sigue estando en vuelo— y por eso
    el handler de `main` **imprime las notas** antes de traducirla a un codigo de salida.
    Lo que si arregla es que quien decide terminar el proceso vuelva a ser el entrypoint.
    """

    def __init__(self, codigo: int = 1):
        super().__init__(f"apertura abortada (codigo {codigo})")
        self.codigo = codigo


def hash_tree_local(root: Path, *, prefijo: str) -> brain.ArbolLocal:
    """SHA-256 recursivo de todos los ficheros bajo root, **declarando lo que no pudo leer**.

    Devuelve un `ArbolLocal`: `hashes` es el `{"<prefijo>/<relpath posix>": sha256hex}` de
    siempre; `sin_verificar` y `renombrados` son lo que antes se perdía. Si root no
    existe, todo vacío — no hay nada que verificar, y eso sí es un cero honesto.

    **Por qué no basta con listar y abrir** (`MEJORAS #214`, medido el 2026-09-10 en
    W-048U77). El montaje de Google Drive for Desktop *presenta* una extensión inferida
    del content-type para los ficheros que en Drive no la llevan, poco después de que
    `rclone` haya escrito el nombre pelado. Entre el listado y la apertura, `X` pasa a ser
    `X.jpg`: la función moría con `FileNotFoundError` sobre un fichero que está, y la
    etapa `drive` de V1 quedaba `bloqueado` con el pull ya hecho.

    Tres propiedades, y las tres son la misma:

    1. **La enumeración no se traga los errores.** `rglob` los **suprime**: una carpeta
       irrecorrible devuelve «cero ficheros» y nadie se entera. Es la clase H-04 que la
       R1 de `verificar_apertura` midió el 2026-09-11, un nivel más abajo. Con
       `os.walk(onerror=…)` cada directorio que no se deja recorrer sale declarado.
    2. **La lectura es tolerante por fichero.** Ante un `FileNotFoundError` se **relee el
       directorio** buscando el mismo nombre *más* una extensión, que es lo que hace el
       montaje. Exactamente un candidato nuevo → se hashea bajo su clave **efectiva** y
       se anota. Cero, o dos o más → `sin_verificar`: **la ambigüedad no se resuelve
       adivinando**.
    3. **Nada de lo enumerado falta en silencio.** Cualquier otro `OSError` deja también
       el fichero en `sin_verificar`. Un fichero que no se pudo leer **no ha medido cero**.

    **Qué mide exactamente, y qué no** (R1/H-06, corrección de la prosa anterior, que
    prometía una completitud que el recorrido no puede dar). Esto es **un recorrido, en un
    instante**: mide lo que la enumeración vio. Un fichero que aparezca en el destino
    *después* de que su directorio se enumerase no entra ni se declara — y el montaje
    puede crearlos, porque renombrar es crear uno y borrar otro. Lo que sí se garantiza es
    que **de lo enumerado, nada se pierde callando**. Una instantánea de un árbol que
    cambia mientras se recorre no existe; lo que existe es no mentir sobre cuál se tomó.
    La detección de sobrantes contra el censo remoto es de `verificar_apertura` C1.

    **Vive en `scripts/` y no en `core/` a propósito.** Parece que debería mudarse —la
    casa manda que la lógica viva en el core— y hoy lo impide un guard:
    `tests/test_abrir_caso_exit_bajo_mutex.py` recorre el AST de este módulo y exige que
    esta función esté en el cierre transitivo del bloque del mutex. **Mudarla no exige
    debilitar la propiedad** —la R1 señaló, con razón, que el guard podría ampliarse al
    módulo destino y exigir que la alcance e inspeccione, con su propio control positivo—;
    exige **rehacer el guard**, que es trabajo propio y no el de esta pieza. Los TIPOS sí
    están en `core.abrir_caso`, junto a `Reconciliacion`, porque son vocabulario de
    custodia.
    """
    out: dict[str, str] = {}
    sin_verificar: list[brain.FicheroSinVerificar] = []
    renombrados: list[tuple[str, str]] = []

    def _clave(p: Path) -> str:
        return f"{prefijo}/{p.relative_to(root).as_posix()}"

    # R1/H-04: `is_dir()` colapsa TRES cosas en un booleano — no existe, existe y no es
    # directorio, y no se pudo averiguar. Solo la primera es un cero honesto; las otras
    # dos son la misma frontera que esta función viene a cerrar, en su primera línea.
    try:
        es_dir = root.stat().st_mode
    except FileNotFoundError:
        return brain.ArbolLocal(hashes={})           # no hay nada que verificar
    except OSError as err:
        return brain.ArbolLocal(hashes={}, sin_verificar=(
            brain.FicheroSinVerificar(clave=prefijo, motivo=repr(err)),))
    if not stat.S_ISDIR(es_dir):
        return brain.ArbolLocal(hashes={}, sin_verificar=(
            brain.FicheroSinVerificar(
                clave=prefijo,
                motivo=f"NotADirectoryError: {str(root)!r} existe y no es un directorio"),))

    def _anotar_dir_ilegible(err: OSError) -> None:
        # `os.walk` llama aquí cuando `scandir` falla sobre un directorio. Sin esto el
        # subárbol entero desaparece del recorrido sin dejar rastro.
        #
        # La raíz se nombra por el prefijo y no `"<prefijo>/."`, que es lo que devuelve un
        # `relative_to` de la raíz consigo misma: el caso peor del recorrido —la carpeta
        # del pull entera ilegible— es justo el que tiene que leerse sin descifrar.
        ruta = Path(err.filename) if err.filename else root
        clave = prefijo if ruta == root else _clave(ruta)
        sin_verificar.append(brain.FicheroSinVerificar(clave=clave, motivo=repr(err)))

    for dirpath, dirnames, filenames in os.walk(root, onerror=_anotar_dir_ilegible):
        dirnames.sort()                          # recorrido determinista
        d = Path(dirpath)
        # R1/H-05: `os.walk` no sigue enlaces de directorio, y no seguirlos es lo correcto
        # (los ciclos son peores). Lo que no lo era es callarlo: el subárbol entero salía
        # del inventario bajo una promesa de completitud.
        for nombre_dir in list(dirnames):
            try:
                if (d / nombre_dir).is_symlink():
                    sin_verificar.append(brain.FicheroSinVerificar(
                        clave=_clave(d / nombre_dir),
                        motivo="enlace simbolico a directorio: no se recorre "
                               "(os.walk followlinks=False), y su contenido no se mide"))
            except OSError as err:               # ni siquiera se pudo preguntar
                sin_verificar.append(brain.FicheroSinVerificar(
                    clave=_clave(d / nombre_dir), motivo=repr(err)))
        # Claves del sistema de ficheros **normalizadas**, no POSIX: se comparan contra
        # `str(q)` de un `iterdir()`. En Windows el separador es `\` y el FS **no
        # distingue caja**, así que `X.PDF` y `x.pdf` nombran el mismo fichero — comparar
        # las cadenas crudas adoptaba como «reaparecido» un documento que ya estaba
        # listado (R1/H-01, ALTO: el hash de otro fichero acababa bajo dos claves).
        listadas = {os.path.normcase(str(d / n)) for n in filenames}
        for nombre in sorted(filenames):
            p = d / nombre
            clave = _clave(p)
            # Protocolo por UBICACIÓN (MEJORAS #149): con `prefijo="01_Drive EV"` solo
            # queda fuera `01_Drive EV/.pulled`. Un `_inventory.json` de E&V en esa
            # carpeta es un fichero del cliente y ENTRA en el ledger forense.
            if es_fichero_de_protocolo(clave):
                continue
            try:
                out[clave] = file_sha256(p)
            except FileNotFoundError as err:
                efectivo = _reaparecido(p, listadas)
                if efectivo is None:
                    sin_verificar.append(brain.FicheroSinVerificar(
                        clave=clave, motivo=repr(err)))
                    continue
                if isinstance(efectivo, str):    # ambigüedad: el motivo lo explica
                    sin_verificar.append(brain.FicheroSinVerificar(
                        clave=clave, motivo=efectivo))
                    continue
                clave_efectiva = _clave(efectivo)
                renombrados.append((clave, clave_efectiva))
                # El protocolo se decide sobre la clave EFECTIVA: si el montaje lo
                # rebautizó a algo que en esta carpeta es protocolo, adoptarlo lo
                # colaría en el ledger forense.
                if es_fichero_de_protocolo(clave_efectiva):
                    continue
                try:
                    out[clave_efectiva] = file_sha256(efectivo)
                except OSError as err2:
                    sin_verificar.append(brain.FicheroSinVerificar(
                        clave=clave_efectiva, motivo=repr(err2)))
            except OSError as err:
                sin_verificar.append(brain.FicheroSinVerificar(
                    clave=clave, motivo=repr(err)))

    return brain.ArbolLocal(
        hashes=out,
        sin_verificar=tuple(sin_verificar),
        renombrados=tuple(renombrados),
    )


def _reaparecido(p: Path, listadas: set[str]) -> Path | str | None:
    """¿El contenido de `p` reapareció bajo otro nombre? `Path` sí, `str` ambiguo, `None` no.

    El montaje añade una extensión al nombre **completo** (`X` → `X.jpg`), así que el
    candidato es un fichero cuyo nombre es el de `p` **más un punto y algo**, y que **no
    estaba en el listado original** de ese directorio: uno que ya se había listado es otro
    documento, y adoptarlo contaría un fichero dos veces perdiendo el otro.

    **Dos correcciones de la R1, y las dos son la misma frontera** —comparar nombres de
    fichero por igualdad de cadena en un sistema que no los identifica así:

    - `os.path.normcase` en las dos comparaciones. Windows no distingue caja, así que
      `Photo` → `photo.jpg` **es** un renombrado (H-09) y `X.PDF` ya listado **no es** un
      candidato aunque reaparezca como `x.pdf` (H-01, el caro: adoptarlo mete el hash de
      otro documento bajo dos claves y pierde el original en silencio).
    - `nombre + "."` como prefijo, no `q.stem == p.name`. El `stem` solo quita la **última**
      extensión, así que `x` → `x.tar.gz` no se reconocía (H-09). El prefijo es además lo
      que el fenómeno describe literalmente.

    Con dos o más candidatos **no se elige**. Cuál de los dos es el documento no lo sabe
    nadie, y resolverlo por orden alfabético sería inventarse la custodia.
    """
    try:
        hermanos = sorted(q for q in p.parent.iterdir() if q.is_file())
    except OSError as err:
        return f"no se pudo releer el directorio tras el renombrado: {err!r}"
    prefijo_nombre = os.path.normcase(p.name + ".")
    candidatos = [q for q in hermanos
                  if os.path.normcase(q.name).startswith(prefijo_nombre)
                  and os.path.normcase(str(q)) not in listadas]
    if not candidatos:
        return None
    if len(candidatos) > 1:
        return ("ambiguedad: el contenido reaparecio bajo "
                f"{len(candidatos)} nombres ({', '.join(q.name for q in candidatos)}); "
                "no se elige ninguno")
    return candidatos[0]


_FUENTES_CLI = ("drive_ev", "manual", "whatsapp", "email")
_MODOS = ("libre", "v1")
_FUENTES_V1 = ("drive_ev",)


def _inventario_desde_hashes(
    raiz: Path, base: str, hashes: dict[str, str],
) -> tuple[list[dict], tuple[FicheroSinVerificar, ...]]:
    """Inventario {relpath, sha256, size} a partir de {base/rel: sha}.

    `raiz` es la raíz **EFECTIVA** bajo la que viven las claves: el `00_Input` del destino
    que decidió el guard, que con un caso prestado es el de la bandeja.

    Antes recomponía `case_dir / "00_Input" / clave`, o sea la ruta **intencionada**
    (R14/H14-02, CRÍTICO). Con desvío eso es un `FileNotFoundError` o —peor— el tamaño de
    un fichero homónimo del canon, y entonces bytes, hash, manifiesto y evento dejan de
    describir el mismo destino. Eso no es cobertura pendiente: es una afirmación forense
    falsa, y por eso la ronda prohibió diferirlo.

    **Y tolera la misma carrera que `hash_tree_local`, porque es la misma** (R1/H-03).
    Este `stat()` vuelve a abrir el fichero por su nombre, un instante después de
    hashearlo: si el montaje lo renombra en medio, un `FileNotFoundError` aquí tumbaba la
    etapa igual que antes, dos líneas más abajo. `MEJORAS #214` nombra esta función
    explícitamente entre los cuatro recorridos-y-abre del camino de intake — remediar solo
    el primero deja los otros esperando su turno.

    Devuelve `(inventario, sin_verificar)`: lo que no se pudo medir sale de aquí
    **declarado**, no ausente.
    """
    inventario: list[dict] = []
    sin_verificar: list[FicheroSinVerificar] = []
    for k, v in hashes.items():
        try:
            size = (raiz / k).stat().st_size
        except OSError as err:
            sin_verificar.append(FicheroSinVerificar(clave=k, motivo=repr(err)))
            continue
        inventario.append({"relpath": k[len(base) + 1:], "sha256": v, "size": size})
    return inventario, tuple(sin_verificar)


def _intake_generico(
    case_dir: Path, case_id: str, fuente: str, hashes: dict[str, str], *, base: str,
    dry_run: bool, raiz_hashes: Path | None = None,
    sin_verificar: tuple[brain.FicheroSinVerificar, ...] = (),
    renombrados: tuple[tuple[str, str], ...] = (),
) -> None:
    """Camino de custodia orquestado (drive_ev, manual): plan → (dry-run) →
    reconcile → append_event. `hashes` cubre SOLO lo recién depositado.

    `base` es el cajón espejo (drive_ev) o el nombre del lote ya reservado
    (fuentes de entrega); la cadena de custodia toma la fuente de `fuente`,
    no del primer segmento de la ruta.

    `raiz_hashes` es la raíz **efectiva** bajo la que viven las claves de `hashes`
    (R14/H14-02). Su default es la canónica —el comportamiento de siempre— y cada
    llamador que pueda ser desviado por el guard pasa la suya. Es aditivo a propósito:
    la vía que no puede desviarse no tiene que enterarse de nada.

    **El evento se queda en el log CANÓNICO** aunque los bytes se desvíen, y eso es
    deliberado: `_intake_log.jsonl` es fila #13 del §25, clase protocolo, exenta del
    desvío. Es también donde el guard deja su propio `pendiente_checkin`, así que las dos
    mitades de la historia quedan en el mismo sitio y en orden.

    `sin_verificar` y `renombrados` vienen del recorrido de custodia (`ArbolLocal`) y
    **se declaran en voz alta y en el evento** (`MEJORAS #214`). No condicionan el éxito:
    los bytes ya están depositados y `reconcile` sigue decidiendo lo suyo. Lo que impiden
    es que el registro **mienta por omisión** — `count` cuenta solo lo verificado, así que
    sin esa lista un pull con ficheros ilegibles se lee como «todo cuadró».
    """
    inventario, sin_medir = _inventario_desde_hashes(
        raiz_hashes if raiz_hashes is not None else case_dir / "00_Input", base, hashes)
    # R1/H-03: lo que el `stat` no pudo medir se suma a lo que el recorrido no pudo leer.
    # Son dos tramos de la misma carrera y una sola lista de huecos.
    sin_verificar = tuple(sin_verificar) + sin_medir
    plan = brain.plan_intake(inventario, intake_log.read_events(case_id), fuente,
                             lote=None if fuente == "drive_ev" else base)
    if dry_run:
        typer.echo(f"[dry-run] {len(plan.depositables)} depositables, "
                   f"{len(plan.items) - len(plan.depositables)} omitidos")
        return
    n_dup = sum(1 for i in plan.items if i.dup)
    n_zero = sum(1 for i in plan.items if i.zero)
    typer.echo(f"Intake: {len(plan.depositables)} depositables, "
               f"{n_dup} duplicados omitidos, {n_zero} de 0 bytes omitidos")
    for viejo, nuevo in renombrados:
        # R1/H-12: el aviso dice lo que PASÓ —el destino renombró—, no lo que se hizo
        # después. El par se anota antes de intentar leer el candidato, así que afirmar
        # «se hasheó» era falso cuando el reaparecido resultaba ilegible o quedaba
        # excluido por protocolo: la línea siguiente lo desmentía.
        typer.echo(f"[aviso] el destino renombró {viejo!r} → {nuevo!r}; "
                   f"la custodia usa el nombre efectivo")
    if sin_verificar:
        # A stderr: no es un aviso decorativo. El expediente tiene ficheros de los que
        # esta corrida NO puede decir nada, y quien lea la salida tiene que verlo.
        typer.echo(f"[AVISO] {len(sin_verificar)} fichero(s) SIN VERIFICAR (no se pudieron "
                   f"leer); no han medido cero, no se han medido:", err=True)
        for f in sin_verificar:
            typer.echo(f"  - {f.clave}: {f.motivo}", err=True)
    # `reconcile` responde «¿lo depositado cuadra con el PLAN?», y el plan sale del
    # inventario. Un fichero cuyo `stat` falló no está en el plan, así que pasárselo en
    # `hashes` lo convertía en un `extra` **espurio** que abortaba la apertura entera —
    # tratando un hueco declarado como un sobrante. No es un sobrante: es justo lo que ya
    # va por su propia vía. Se le pasan los hashes de lo que sí se pudo medir.
    claves_sin_medir = {f.clave for f in sin_medir}
    hashes_medidos = ({k: v for k, v in hashes.items() if k not in claves_sin_medir}
                      if claves_sin_medir else hashes)
    rec = brain.reconcile(plan, hashes_medidos)
    if not rec.ok:
        typer.echo(f"[ERROR] Reconciliación falló: faltan={rec.faltantes} "
                   f"mismatch={rec.mismatches} extra={rec.extras}", err=True)
        raise AbortarApertura(1)   # MEJORAS #142: no se termina el proceso bajo el mutex
    # R1/H-02 (ALTO): el evento se escribía **solo** si había depositables, y eso dejaba
    # mudo justo el caso peor. Si ninguno de los ficheros del pull se pudo leer, `hashes`
    # viene vacío, el plan sale vacío y `con_sha` también: la única corrida que de verdad
    # tenía algo que declarar era la única que no dejaba rastro en el ledger. Lo mismo
    # pasaba si todo lo legible resultaba duplicado o de 0 bytes. Ahora la condición es
    # «hay algo que contar **o** algo que declarar».
    if plan.con_sha or sin_verificar or renombrados:
        # B0-1: `_intake_generico` ya tiene el `case_dir`, asi que el evento cae
        # junto a los documentos que acaba de ingerir.
        details = {"count": len(plan.con_sha), "files": plan.con_sha}
        # Las claves solo aparecen cuando hay algo que decir: escribir `[]` en todos los
        # eventos llenaría el ledger de ruido y volvería invisible el caso que importa.
        if sin_verificar:
            details["sin_verificar"] = [
                {"clave": f.clave, "motivo": f.motivo} for f in sin_verificar]
        if renombrados:
            details["renombrados"] = [list(par) for par in renombrados]
        intake_log.append_event(case_dir, brain.FUENTE_A_EVENTO[fuente], case_id=case_id,
                                details=details)


def _intake_drive_ev(ident, case_dir: Path, folder_id, team_id, *,
                     dry_run: bool,
                     force: bool = False) -> intake_drive.DriveIntakeResult:
    """Pull de Drive E&V + cadena de custodia sobre el destino EFECTIVO (R14/H14-02).

    **El dato que hacía barato el arreglo: `DriveIntakeResult` ya traía `target_dir`.**
    El destino que eligió el guard venía de vuelta en el resultado y este llamador lo
    tiraba para recomponer la ruta canónica a mano. No faltaba información: se descartaba.
    """
    try:
        res = intake_drive.pull_drive_ev(ident.case_id, folder_id, team_id, force=force)
    except intake_drive.DriveIntakeError as exc:
        # R15/H15-06: un `rclone` no cero puede haber copiado PARTE del árbol, y esos bytes
        # se quedan en el expediente. Antes la excepción subía sin que nada los inventariase,
        # así que quedaban depositados y **sin un solo evento** que dijera qué llegó ni que
        # la operación había fallado. Custodia partida en dos.
        #
        # Se emite `pull_drive_ev` con `status: fallo` —el vocabulario de `INTAKE_EVENTS` es
        # cerrado y no se añade un evento a la ligera; el patrón `status` ya lo usa
        # `contenido_adjuntos`— y se relanza. Registrar lo parcial NO es declararlo un
        # intake correcto: el status lo dice y el comando sigue fallando.
        parcial = getattr(exc, "result", None)
        destino = getattr(parcial, "target_dir", None)
        if destino is not None:
            # El recorrido tolerante también aquí, y no por simetría: este camino corre
            # sobre el MISMO montaje, así que tiene la MISMA carrera (`MEJORAS #214`). Si
            # aquí se tragara el fallo, la custodia que quedaría muda sería justo la del
            # caso peor —el pull roto—, que es donde más falta hace saber qué llegó.
            arbol = hash_tree_local(destino, prefijo=brain.SUBDIR_DRIVE_EV)
            details = {"status": "fallo", "count": len(arbol.hashes),
                       "files": [{"path": k, "sha256": v} for k, v in arbol.hashes.items()],
                       "rclone_returncode": getattr(parcial, "rclone_returncode", None)}
            if arbol.sin_verificar:
                details["sin_verificar"] = [
                    {"clave": f.clave, "motivo": f.motivo} for f in arbol.sin_verificar]
            if arbol.renombrados:
                details["renombrados"] = [list(par) for par in arbol.renombrados]
            intake_log.append_event(
                case_dir, "pull_drive_ev", case_id=ident.case_id, details=details)
            sufijo = (f" y {len(arbol.sin_verificar)} sin verificar"
                      if arbol.sin_verificar else "")
            typer.echo(
                f"[ERROR] el pull falló y quedaron {len(arbol.hashes)} ficheros "
                f"parciales{sufijo}; registrados en el log con status=fallo antes de "
                f"abortar", err=True)
            # R1/H-08: el evento guardaba claves y motivos, pero `exc.result` seguía
            # vacío y `etapa_drive` devolvía un fallo genérico. La declaración se
            # calculaba y se tiraba a mitad de camino. `DriveIntakeResult` es frozen, así
            # que la copia con el campo relleno se pone en la excepción que va a subir.
            exc.result = dataclasses.replace(
                parcial, custodia_sin_verificar=arbol.sin_verificar)
        raise

    subdir = brain.SUBDIR_DRIVE_EV
    # `target_dir` es `<algo>/00_Input/01_Drive EV`, así que su padre es la raíz bajo la
    # que resuelven las claves `01_Drive EV/...`. Con el caso disponible es el `00_Input`
    # del caso; con el caso prestado, el de la bandeja.
    arbol = hash_tree_local(res.target_dir, prefijo=subdir)
    _intake_generico(case_dir, ident.case_id, "drive_ev", arbol.hashes, base=subdir,
                     dry_run=dry_run, raiz_hashes=res.target_dir.parent,
                     sin_verificar=arbol.sin_verificar, renombrados=arbol.renombrados)
    # Lo devuelve para que el secuenciador de V1 pueda informar sin rodear esta funcion:
    # la custodia (hashes del destino EFECTIVO, reconciliacion y el registro de los bytes
    # parciales de un pull fallido) vive aqui, y un adaptador que la esquive la deroga.
    #
    # **Y viaja con lo que la custodia no pudo leer.** `DriveIntakeResult` es el canal que
    # ya existe entre esta funcion y `etapa_drive`; adjuntarlo aqui es lo que permite que
    # V1 lo convierta en un `Pendiente` en vez de que se pierda entre las dos.
    return dataclasses.replace(res, custodia_sin_verificar=arbol.sin_verificar)


def _inventario_local(src: Path) -> list[dict]:
    """Inventario {relpath, sha256, size} de un origen local (carpeta o .zip),
    SIN copiar. Usado por el dry-run de manual."""
    items: list[dict] = []
    if src.is_dir():
        for p in sorted(src.rglob("*")):
            if p.is_file():
                items.append({"relpath": p.relative_to(src).as_posix(),
                              "sha256": file_sha256(p), "size": p.stat().st_size})
    elif zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as zf:
            for m in zf.infolist():
                if m.is_dir():
                    continue
                data = zf.read(m)
                items.append({"relpath": m.filename,
                              "sha256": hashlib.sha256(data).hexdigest(), "size": m.file_size})
    else:
        raise FileNotFoundError(f"--src no es carpeta ni .zip: {src}")
    return items


def _depositar_manual(case_id: str, src: Path, lote: Path) -> list[str]:
    """Deposita el origen en el LOTE (vía intake_manual: guard+M9+manifiesto) y
    devuelve los relpath (posix) depositados en ESTA pasada."""
    if zipfile.is_zipfile(src):
        paths = intake_manual.extract_zip(case_id, src.read_bytes(), lote=lote)
        return [p.relative_to(lote).as_posix() for p in paths]
    if src.is_dir():
        depositados: list[str] = []
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(src).as_posix()
            intake_manual.save_file_en_lote(case_id, lote, rel, p.read_bytes())
            depositados.append(rel)
        return depositados
    raise FileNotFoundError(f"--src no es carpeta ni .zip: {src}")


def _intake_manual(ident, case_dir: Path, src_str: str, *, dry_run: bool) -> None:
    src = Path(src_str)
    if dry_run:
        try:
            inv = _inventario_local(src)
        except FileNotFoundError as exc:
            typer.echo(f"[ERROR] {exc}", err=True)
            raise AbortarApertura(1) from exc   # MEJORAS #142
        plan = brain.plan_intake(inv, intake_log.read_events(ident.case_id), "manual",
                                 lote="<fecha>_manual_NN")
        typer.echo(f"[dry-run] manual: {len(plan.depositables)} depositables, "
                   "se depositaría en un lote nuevo <fecha>_manual_NN (sin ejecutar)")
        return
    lote = intake_manual.abrir_lote_manual(ident.case_id, origen="abrir_caso_cli")
    try:
        rels = _depositar_manual(ident.case_id, src, lote)
    except FileNotFoundError as exc:
        typer.echo(f"[ERROR] {exc}", err=True)
        raise AbortarApertura(1) from exc   # MEJORAS #142
    hashes = {f"{lote.name}/{rel}": file_sha256(lote / rel) for rel in rels}
    # `lote` ya es el directorio EFECTIVO (`abrir_lote_manual` pasa por el guard), así que
    # los hashes de arriba siempre fueron correctos. Lo que no lo era es el inventario, que
    # resolvía contra la ruta canónica: la vía manual tenía el mismo defecto que #8, latente
    # y sin fila propia en el §25. Se cierra aquí porque es el MISMO arreglo.
    _intake_generico(case_dir, ident.case_id, "manual", hashes, base=lote.name,
                     dry_run=False, raiz_hashes=lote.parent)


def _intake_whatsapp(ident, src_str: str, rol: str, *, dry_run: bool) -> None:
    src = Path(src_str)
    if not src.is_file():
        typer.echo(f"[ERROR] --src no existe: {src}", err=True)
        raise AbortarApertura(1)   # MEJORAS #142
    if dry_run:
        typer.echo(f"[dry-run] whatsapp: se depositaría {src.name} en rol {rol} (sin ejecutar)")
        return
    res = whatsapp_intake.deposit_export(
        ident.case_id, rol, src.read_bytes(), zip_name=src.name)
    if getattr(res, "skipped_dedup", False):
        typer.echo("WhatsApp: export ya importado (dedup), nada nuevo")
    else:
        typer.echo(f"WhatsApp depositado en {getattr(res, 'chat_dir', '?')}")


def _intake_email(ident, case_dir: Path, cuenta: str, label: str, *, dry_run: bool,
                  extraer_adjuntos: bool = True) -> None:
    """Exporta la etiqueta Gmail del caso a un lote nuevo de ``00_Input``.

    ``extraer_adjuntos`` saca además cada adjunto como fichero suelto junto al
    ``.eml`` (que conserva los suyos embebidos, byte-fieles). Importa porque la sala
    de máquina lee ``00_Input``: sin extraer, un adjunto que llegue SOLO por correo
    —sin copia en el Drive— no se OCR-ea ni aparece en la sala de lectura
    (``MEJORAS #68.a``). El default no cambia: activarlo mueve la superficie de dedup
    de todo intake futuro, así que es decisión explícita de quien abre el caso.
    """
    if dry_run:
        extra = " (extrayendo adjuntos)" if extraer_adjuntos else ""
        typer.echo(f"[dry-run] email: se exportaría la etiqueta {label!r} de {cuenta} "
                   f"a un lote nuevo 00_Input/<fecha>_email_NN{extra} (sin ejecutar)")
        return
    dest = email_export.email_dest_dir(ident.case_id)     # reserva el lote (T8)
    email_export.export_label(cuenta, label, dest, case_id=ident.case_id,
                              extract_attachments=extraer_adjuntos)
    typer.echo(f"Email: etiqueta {label!r} exportada a {dest}")


def _validar_flags(fuente, *, folder_id, team_id, src, rol, cuenta, label) -> None:
    """Exige los flags propios de la fuente y rechaza los ajenos (fail-fast)."""
    requeridos = {
        "drive_ev": [],
        "manual": [("--src", src)],
        "whatsapp": [("--src", src), ("--rol", rol)],
        "email": [("--cuenta", cuenta), ("--label", label)],
    }[fuente]
    faltan = [n for n, v in requeridos if not v]
    if faltan:
        typer.echo(f"[ERROR] Fuente {fuente}: faltan flags {faltan}", err=True)
        raise AbortarApertura(1)

    ajenos = {
        "drive_ev": [("--src", src), ("--rol", rol), ("--cuenta", cuenta), ("--label", label)],
        "manual": [("--rol", rol), ("--cuenta", cuenta), ("--label", label),
                   ("--folder-id", folder_id), ("--team-id", team_id)],
        "whatsapp": [("--cuenta", cuenta), ("--label", label),
                     ("--folder-id", folder_id), ("--team-id", team_id)],
        "email": [("--src", src), ("--rol", rol),
                  ("--folder-id", folder_id), ("--team-id", team_id)],
    }[fuente]
    presentes = [n for n, v in ajenos if v]
    if presentes:
        typer.echo(f"[ERROR] Fuente {fuente}: flags ajenos a la fuente {presentes}", err=True)
        raise AbortarApertura(1)

    if fuente == "whatsapp" and rol not in config.WHATSAPP_SUBDIRS:
        typer.echo(f"[ERROR] rol inválido: {rol}. Válidos: {config.WHATSAPP_SUBDIRS}", err=True)
        raise AbortarApertura(1)


def _despachar_intake(fuente, ident, case_dir, *, folder_id, team_id, src, rol,
                      cuenta, label, dry_run, extraer_adjuntos=True):
    """Despacha el intake de UNA fuente. **Ya no valida flags**: eso corre antes del
    mutex (`MEJORAS #142`), porque fallar por un flag mal puesto no necesita el lock
    adquirido y hacerlo dentro convertia el fallo en un `Exit` bajo exclusion."""
    if fuente == "drive_ev":
        _intake_drive_ev(ident, case_dir, folder_id, team_id, dry_run=dry_run)
    elif fuente == "manual":
        _intake_manual(ident, case_dir, src, dry_run=dry_run)
    elif fuente == "whatsapp":
        _intake_whatsapp(ident, src, rol, dry_run=dry_run)
    elif fuente == "email":
        _intake_email(ident, case_dir, cuenta, label, dry_run=dry_run,
                      extraer_adjuntos=extraer_adjuntos)
    else:
        raise AbortarApertura(1)  # red de seguridad: _FUENTES_CLI ya filtra el valor


def etapa_drive(ident, case_dir: Path, *, folder_id, team_id, intake=None):
    """Etapa 1 de V1: materializar la carpeta de Drive E&V, con custodia.

    **Pasa por `_intake_drive_ev` y no por `pull_drive_ev`**: la custodia —hashes sobre el
    destino efectivo, reconciliacion, y registro de los bytes parciales de un pull
    fallido— vive ahi, y es el resultado de R14/H14-02 y R15/H15-06. Un adaptador que la
    rodea la deroga en silencio.

    **`force=True` siempre.** La tabla de riesgos de la spec llama al skip por `.pulled`
    «falso punto fijo»: en V1 la consulta remota se hace en cada ronda, y `rclone`
    transfiere solo lo que difiere.

    **La declaración de custodia se construye ANTES de cualquier `return`, y por eso.**
    La R1 encontró dos caminos que la tiraban —un fallo al contar el destino (H-07) y el
    pull fallido (H-08)— y los dos eran el mismo defecto de forma: el dato se calculaba al
    final de una función con cinco salidas. Una declaración que depende de por dónde se
    salga no es una declaración. Aquí se calcula primero y la llevan **todas** las ramas.
    """
    _intake = intake or _intake_drive_ev
    res = None
    try:
        res = _intake(ident, case_dir, folder_id, team_id, dry_run=False, force=True)
        fallo_detalle = None
    except Exception as exc:  # noqa: BLE001 — el estado de V1 es el producto, no la traza
        # Un `DriveIntakeError` trae el resultado PARCIAL con lo que la custodia no pudo
        # leer (R15/H15-06 + R1/H-08). Que el pull haya fallado y que haya ficheros
        # ilegibles son dos hechos, y el segundo se pierde si solo se mira el primero.
        res = getattr(exc, "result", None)
        fallo_detalle = f"{type(exc).__name__}: {exc}"

    pendientes = _pendientes_de_custodia(res)

    if fallo_detalle is not None:
        return av1.EtapaResultado(nombre="drive", estado="fallo",
                                  detalle=fallo_detalle, pendientes=pendientes)
    if res.errors or res.rclone_returncode != 0:
        return av1.EtapaResultado(
            nombre="drive", estado="fallo",
            detalle=f"rclone rc={res.rclone_returncode}; errores={res.errors}",
            pendientes=pendientes)
    if res.skipped:
        # Con `force=True` esto no deberia poder pasar. Si pasa, el marcador `.pulled`
        # volvio al camino y la ronda NO consulto Drive: decirlo `saltada` seria firmar
        # el falso punto fijo que la spec prohibe.
        return av1.EtapaResultado(
            nombre="drive", estado="fallo",
            detalle="la consulta remota no se hizo: el pull devolvio `skipped` pese a "
                    "pedirse con force=True",
            pendientes=pendientes)
    # `files_after` cuenta SOLO el primer nivel del destino (`core/intake_drive.py:120`),
    # y los documentos de un caso viven en subcarpetas. Reportarlo era decir «0 ficheros»
    # justo despues de depositar dos — medido en la corrida real sobre W-02Q38C el
    # 2026-09-03. Un proxy en vez de la cosa, otra vez.
    try:
        total = sum(
            1 for p in res.target_dir.rglob("*")
            if p.is_file() and not es_fichero_de_protocolo(
                f"{res.target_dir.name}/{p.relative_to(res.target_dir).as_posix()}"))
    except OSError as exc:
        return av1.EtapaResultado(
            nombre="drive", estado="hecha",
            detalle=f"consultado, pero no se pudo contar el destino: {exc}",
            pendientes=pendientes)
    return av1.EtapaResultado(
        nombre="drive", estado="hecha",
        detalle=f"consulta remota hecha; {total} documento(s) en el destino",
        pendientes=pendientes)


def _pendientes_de_custodia(res) -> tuple:
    """Lo que la custodia no pudo leer, como `Pendiente` de V1. Vacío si no hay nada.

    La etapa **no se tumba** por esto —los bytes están depositados— pero tampoco puede
    decir «hecha, N documentos» a secas: ese N cuenta solo lo verificado (`MEJORAS #214`).
    """
    sin_verificar = getattr(res, "custodia_sin_verificar", ()) or ()
    if not sin_verificar:
        return ()
    claves = ", ".join(f.clave for f in sin_verificar)
    return (av1.Pendiente(
        codigo="custodia_sin_verificar",
        detalle=f"{len(sin_verificar)} fichero(s) del destino no se pudieron leer y "
                f"quedan SIN VERIFICAR: {claves}. No han medido cero: no se han medido."),)


#: Vocabulario cerrado de ramas del CRM. `_ELEMENT_EXTRAJUDICIAL` ya existe arriba y lo
#: usa el alta: aqui se reutiliza, no se inventa.
_ELEMENT_JUDICIAL = "expedientes_judiciales"
ELEMENTS_CRM = frozenset({_ELEMENT_EXTRAJUDICIAL, _ELEMENT_JUDICIAL})


def traducir_pull_crm(res) -> tuple[str, str, tuple]:
    """`PullResultV2` -> (estado, detalle, pendientes). Tres ramas, las tres alcanzables.

    **Reescrita tras la R-B, y la leccion es el orden de las preguntas.** La version
    anterior leia `errors` primero y lo trataba como fatal. Pero el PRODUCTOR
    (`core/sync_sudespacho.pull_expediente_v2`) mete en `errors` el aviso de un gestor
    documental **vacio** —que no es un error— y ademas incrementa `documents_failed` en el
    mismo bloque que su `errors.append`. Resultado medido: las ramas de «vacio confirmado»
    y «documentos fallidos» eran INALCANZABLES, y un expediente sin documentos dejaba V1
    `bloqueado` sin correr el OCR.

    **Quien clasifica es el productor**, via `sync_sudespacho.es_gestor_vacio`: la forma en
    que codifica «vacio» es suya, y replicarla aqui la duplicaria.

    **Y un cambio de criterio propio:** unos documentos que no se descargan dejan el espejo
    del CRM incompleto. La version anterior seguia con un pendiente; para prueba documental
    de un litigio eso es peor que parar, asi que ahora **bloquea** y el operador re-corre.
    """
    from core import sync_sudespacho

    if getattr(res, "blocked_legacy_v1", False):
        return "fallo", "el expediente esta bloqueado por el legado v1", ()
    if sync_sudespacho.es_gestor_vacio(res):
        return ("saltada", "el gestor documental del expediente esta vacio",
                (av1.Pendiente(
                    codigo="crm_gestor_vacio",
                    detalle="El expediente existe en el CRM y su gestor documental no "
                            "tiene documentos. No es un fallo; es que no hay nada."),))
    errores = list(getattr(res, "errors", []) or [])
    if errores:
        return "fallo", f"el pull devolvio errores: {errores}", ()
    return "hecha", f"{getattr(res, 'documents_written', 0)} documento(s) escritos", ()


def etapa_crm(ident, case_dir: Path, *, leer_meta=None, pull=None):
    """Etapa 2 de V1: pull del expediente CRM ya registrado.

    **El `element` sale del `ExpedienteLink`, pertenece al vocabulario cerrado, y la rama
    judicial aborta.** El criterio 38 pide los dos cruces: el obvio —que un caso judicial
    no entre por la via extrajudicial— y el que produce el default de
    `core/sync_sudespacho.py:1356`, que es el inverso y el que nadie prueba.
    """
    from core import sync_sudespacho

    _leer = leer_meta or case_locator.read_case_meta
    _pull = pull or sync_sudespacho.pull_expediente_v2

    try:
        meta = _leer(case_dir)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="crm", estado="fallo",
                                  detalle=f"no se pudo leer _caso.md: {exc}")

    links = list(meta.get("sudespacho_expedientes") or [])
    if not links:
        return av1.EtapaResultado(
            nombre="crm", estado="saltada",
            detalle="sin expediente CRM registrado en _caso.md",
            pendientes=(av1.Pendiente(
                codigo="crm_sin_expediente",
                detalle="El caso no tiene expediente CRM vinculado, asi que no hay nada "
                        "que pullar. El alta CRM es de V2."),))

    # Las tres puertas de la rama se comprueban ANTES de pullar nada: con dos expedientes
    # vinculados, descubrir el segundo invalido a mitad dejaria el primero ya escrito.
    for link in links:
        el = link.get("element")
        if not el:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"el expediente {link.get('id')!r} no declara `element` en "
                        f"_caso.md. No se adivina: el default del pull es judicial.")
        if el not in ELEMENTS_CRM:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"`element` fuera del vocabulario: {el!r}; validos: "
                        f"{sorted(ELEMENTS_CRM)}")
        if el == _ELEMENT_JUDICIAL:
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"el expediente {link.get('id')!r} es de la rama judicial, que "
                        f"sigue bloqueada: V1 no tiene adaptador judicial verificado.")

    hechos, pendientes, vacios = [], [], 0
    for link in links:
        try:
            res = _pull(ident.case_id, str(link["id"]), element=link["element"])
        except Exception as exc:  # noqa: BLE001
            return av1.EtapaResultado(
                nombre="crm", estado="fallo",
                detalle=f"pull de {link['id']} fallo: {type(exc).__name__}: {exc}")
        estado, detalle, pend = traducir_pull_crm(res)
        if estado == "fallo":
            return av1.EtapaResultado(nombre="crm", estado="fallo",
                                      detalle=f"{link['id']}: {detalle}")
        if estado == "saltada":
            vacios += 1
        hechos.append(f"{link['id']} ({detalle})")
        pendientes.extend(pend)

    # `saltada` solo si TODOS lo fueron: un expediente vacio junto a otro con documentos
    # es una etapa hecha.
    estado = "saltada" if vacios == len(links) else "hecha"
    return av1.EtapaResultado(nombre="crm", estado=estado,
                              detalle="; ".join(hechos), pendientes=tuple(pendientes))


def etapa_sala_maquina(ident, *, correr=None):
    """Etapa 3 de V1: atomizacion del correo depositado + OCR y espejos MD.

    La maquina de estados es la del §24 D4: el motor NO cambia —el OCR sigue aunque la
    atomizacion falle, y eso no se regresa— y lo que cambia es el RESULTADO de V1, que si
    lo refleja.

    El import va dentro: `scripts/sala_maquina` arrastra el motor de OCR y el atomizador,
    y pagarlo en cada arranque del modo `libre` seria una regresion para sus llamadores.
    """
    def _correr():
        from scripts import sala_maquina
        return sala_maquina.apply(case_id=ident.case_id)

    try:
        res = (correr or _correr)()
    except typer.Exit as exc:
        codigo = getattr(exc, "exit_code", 0) or 0
        if codigo:
            return av1.EtapaResultado(
                nombre="sala_maquina", estado="fallo",
                detalle=f"la sala de maquina salio con codigo {codigo}")
        res = None
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="sala_maquina", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")

    status = getattr(res, "status_atomizacion", None)
    # `MEJORAS #144`: los documentos que el OCR no pudo procesar tienen que APARECER en
    # los pendientes. Antes se imprimian y nada mas, asi que el evento forense decia
    # «preparado con pendientes» enumerando pendientes ajenos a la documental.
    agotados = int(getattr(res, "documentos_agotados", 0) or 0)

    pendientes = []
    if agotados:
        pendientes.append(av1.Pendiente(
            codigo="ocr_documentos_agotados",
            detalle=f"{agotados} documento(s) llevan {SM_MAX_INTENTOS} intentos de "
                    f"procesado agotados y la sala de maquina los salta: su texto NO esta "
                    f"en el corpus. Hay que mirarlos a mano. Reintento: "
                    f"`sala_maquina apply --force`, o `--solo <ruta>`."))

    if status == "fallo":
        return av1.EtapaResultado(
            nombre="sala_maquina", estado="fallo",
            detalle="la atomizacion del correo fallo (§24 D4: bloquea el cierre de V1)",
            pendientes=tuple(pendientes))
    if status == "parcial":
        pendientes.append(av1.Pendiente(
            codigo="atomizacion_parcial",
            detalle="La atomizacion publico con errores o con poda omitida: "
                    "`01_Procesado/Emails` no esta completo. Ver el evento "
                    "`atomizado_email` en `_intake_log.jsonl`."))
        return av1.EtapaResultado(
            nombre="sala_maquina", estado="hecha",
            detalle="OCR hecho; atomizacion PARCIAL",
            pendientes=tuple(pendientes))
    base = ("OCR hecho; sin correo que atomizar" if status is None
            else "OCR hecho; atomizacion ok")
    if agotados:
        base += f"; {agotados} documento(s) con intentos agotados"
    return av1.EtapaResultado(nombre="sala_maquina", estado="hecha", detalle=base,
                              pendientes=tuple(pendientes))


def registrar_cierre_v1(case_dir: Path, ident, resultado) -> None:
    """Deja el estado de V1 en el log forense del caso.

    Es el unico rastro DURABLE de la corrida: la pantalla se pierde, el `.jsonl` no.
    """
    intake_log.append_event(
        case_dir, "apertura_v1_terminada", case_id=ident.case_id,
        details={
            "estado": resultado.estado,
            "parada": resultado.parada,
            "pendientes": [p.codigo for p in resultado.pendientes],
            "etapas": [{"nombre": e.nombre, "estado": e.estado}
                       for e in resultado.etapas],
        },
    )


def codigo_de_salida(estado: str) -> int:
    """`bloqueado` sale distinto de 0: quien invoque la secuencia tiene que poder
    distinguir «termino con pendientes» de «no termino»."""
    return 1 if estado == av1.EstadoV1.BLOQUEADO else 0


# --- Etapas de V2: el lazo del CRM ------------------------------------------
#: Las comprobaciones de `verificar_apertura` cuyo fallo SI es un fallo de V2. El resto
#: diagnostica fases ajenas —la sala de lectura y la viabilidad son V3— y viaja como
#: pendiente: avanzar a medias en algo fuera de alcance no puede bloquear el cierre del
#: lazo del CRM (R1/H-07). Los nombres salen de `verificar_apertura.IMPLEMENTADAS` y un
#: test comprueba que existen: si alguno no existiera, el conjunto se quedaria corto y
#: ningun fallo bloquearia nunca.
COMPROBACIONES_DE_V2 = frozenset({"crm_ficha", "crm_actuacion", "cuantia_coherente"})

#: Como se traduce cada desenlace del alta al vocabulario de etapas. `ya_vinculado` y
#: `declinado` son `saltada` —la etapa decidio, con razon declarada, que no habia nada
#: que hacer—; los dos fallos son `fallo`.
_ALTA_A_ETAPA = {
    "creado": "hecha",
    "ya_vinculado": "saltada",
    "declinado": "saltada",
    "omitido": "saltada",
    "fallo_post": "fallo",
    "fallo_registro": "fallo",
}

_PENDIENTE_NO_AUTORIZADO = av1.Pendiente(
    codigo="crm_no_autorizado",
    detalle="No se toco el CRM: la corrida no lo autorizo (--crm skip). Relanza con "
            "--crm api si quieres que esta etapa escriba.")


def etapa_crm_alta(ident, case_dir: Path, *, crm: str, alta=None) -> av1.EtapaResultado:
    """Etapa 4 (V2): alta del expediente en el CRM, si se autorizo y no la hay ya.

    **No reimplementa el alta**: invoca `_alta_crm`, que ya resuelve duplicados con
    `core.alta_crm_politica`, tags, telefono y evento. Lo que esta etapa aporta es
    traducir sus SEIS desenlaces sin colapsarlos — la rev. 1 del plan describia un
    timeout como «ya tiene expediente vinculado» (R1/H-02).
    """
    if crm != "api":
        return av1.EtapaResultado(
            nombre="crm_alta", estado="saltada",
            detalle="escritura al CRM no autorizada (--crm skip)",
            pendientes=(_PENDIENTE_NO_AUTORIZADO,))
    try:
        r = (alta or (lambda: _alta_crm(
            ident, cuantia=None, crm_mode=crm, yes=True)))()
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="crm_alta", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    detalle = {
        "creado": f"expediente CRM {r.exp_id}",
        "ya_vinculado": f"ya vinculado a {r.exp_id}; no se da de alta otro",
        "declinado": "alta declinada en el gate",
        "omitido": "alta omitida",
        "fallo_post": f"el alta no se pudo confirmar: {r.detalle}",
        "fallo_registro": (f"expediente {r.exp_id} CREADO en el CRM pero NO vinculado "
                           f"en local: {r.detalle}. NO reintentes el alta."),
    }[r.estado]
    return av1.EtapaResultado(nombre="crm_alta",
                              estado=_ALTA_A_ETAPA[r.estado], detalle=detalle)


def _recibo_path(case_dir: Path) -> Path:
    """Donde vive el recibo de la actuacion. **Durable a proposito.**

    Un `Recibo` en memoria muere con el proceso, que es justo el caso que el §5.2
    describe: sin persistirlo, relanzar crea una SEGUNDA actuacion (R1/H-03, que el
    revisor reprodujo con los ids 900 y 901).
    """
    return Path(case_dir) / "00_Input" / "_recibo_actuacion.json"


class ReciboIlegible(Exception):
    """El recibo EXISTE y no se pudo interpretar. **No es lo mismo que no tenerlo.**

    Un fichero ausente acredita que no hubo intento; uno corrupto no acredita nada —
    puede haber una actuacion creada cuyo recibo se estropeo—. Tratarlos igual daba
    permiso para crear una segunda (R2/H-02). Es la misma frontera que P8 cerro.
    """


def _leer_recibo(case_dir: Path):
    """El recibo guardado, o `None` si NO HAY. Si lo hay y no se interpreta, LEVANTA."""
    ruta = _recibo_path(case_dir)
    if not ruta.exists():
        return None
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReciboIlegible(f"{type(exc).__name__}: {exc}") from exc
    from core import sudespacho_actuaciones as sa
    try:
        return sa.Recibo(**crudo)
    except TypeError as exc:
        raise ReciboIlegible(f"no casa con el contrato de Recibo: {exc}") from exc


def _guardar_recibo(case_dir: Path, recibo) -> None:
    ruta = _recibo_path(case_dir)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(dataclasses.asdict(recibo), ensure_ascii=False, indent=2),
        encoding="utf-8")


#: Base del asunto de la actuacion de apertura. El PREFIJO no se escribe aqui: lo pone
#: `sudespacho_actuaciones.asunto_canonico` a partir de quien firma, porque ese prefijo
#: ES la tarifa (`SENIOR` 103,00 €/h, `ABOGADO` 77,00) y ponerlo a mano facturaria al
#: cliente la de otro (`[APER-72]`).
_ASUNTO_APERTURA = "APERTURA E ESTUDIO INICIAL CASO"


def _expediente_del_caso(case_dir: Path):
    """`(elemento, exp_id)` del expediente CRM vinculado, o `None` si no hay.

    Se lee del `_caso.md`, que es donde `register_expediente` lo deja. `None` no es un
    error: es un caso cuyo alta todavia no se ha hecho.
    """
    try:
        meta = case_locator.read_case_meta(case_dir)
    except Exception:  # noqa: BLE001
        return None
    for link in (meta.get("sudespacho_expedientes") or []):
        elemento, exp_id = link.get("element"), link.get("id")
        if elemento and exp_id:
            return str(elemento), str(exp_id)
    return None


class FichaIlegible(Exception):
    """El `_ficha_crm.yaml` EXISTE y no se pudo interpretar (R2/H-06).

    Misma frontera que `ReciboIlegible`: que no este es un estado normal —nadie la ha
    escrito aun—; que este y no se lea significa que alguien la escribio creyendo que
    servia, y devolver "" la hacia indistinguible de la ausencia.
    """


def _firmante_de(case_dir: Path) -> str:
    """`firmante:` de `_ficha_crm.yaml`; "" si NO HAY ficha o no declara el campo.

    Si la ficha existe y no se puede interpretar, **levanta** `FichaIlegible`.
    """
    from core import crm_ficha as cf
    ruta = Path(case_dir) / "00_Input" / "_ficha_crm.yaml"
    if not ruta.exists():
        return ""
    try:
        return cf.cargar_ficha_yaml(ruta).firmante or ""
    except Exception as exc:  # noqa: BLE001
        raise FichaIlegible(f"{type(exc).__name__}: {exc}") from exc


def etapa_actuacion(ident, case_dir: Path, *, crm: str, alta=None,
                    firmante=None) -> av1.EtapaResultado:
    """Etapa 5 (V2): la actuacion de apertura, con recibo reanudable y DURABLE.

    **El `firmante` no se infiere nunca.** El prefijo del asunto ES la tarifa —`SENIOR`
    factura 103,00 €/h y `ABOGADO` 77,00— y quien firma no es quien opera: Ana puede
    tramitar lo que firma Nikolai. Sin ese dato, `Pendiente`. Al CRM va el **username**
    (`Nikolai_Tyukhay`), no el nombre con espacios.

    **Los cuatro estados del recibo NO se colapsan** (R1/H-03): `verificada` es `hecha`;
    `incompleta` se reanuda pasando `desde`; `incierta` es `fallo` con su pendiente,
    porque no se sabe si el efecto ocurrio y declararlo hecho seria la mentira que el
    §5.2 existe para impedir.
    """
    if crm != "api":
        return av1.EtapaResultado(
            nombre="actuacion", estado="saltada",
            detalle="escritura al CRM no autorizada (--crm skip)",
            pendientes=(_PENDIENTE_NO_AUTORIZADO,))
    try:
        quien = firmante if firmante is not None else _firmante_de(case_dir)
    except FichaIlegible as exc:
        # R2/H-06: existe y no se puede leer. Presentarlo como «sin firmante» lo haria
        # indistinguible de no haberla escrito nunca.
        return av1.EtapaResultado(
            nombre="actuacion", estado="fallo",
            detalle=f"_ficha_crm.yaml existe pero no se pudo interpretar: {exc}",
            pendientes=(av1.Pendiente(
                codigo="ficha_crm_ilegible",
                detalle="Arregla el YAML de la ficha: alguien lo escribio y no se lee."),))
    if not quien:
        return av1.EtapaResultado(
            nombre="actuacion", estado="saltada",
            detalle="sin firmante declarado: la actuacion decide la tarifa",
            pendientes=(av1.Pendiente(
                codigo="actuacion_sin_firmante",
                detalle="Declara `firmante:` (username del CRM) en _ficha_crm.yaml. El "
                        "prefijo del asunto es la tarifa, asi que no se infiere del "
                        "operador."),))

    try:
        previo = _leer_recibo(case_dir)
    except ReciboIlegible as exc:
        # R2/H-02. Un recibo corrupto NO acredita que no hubiera escritura: puede haber
        # una actuacion creada cuyo recibo se estropeo. Fallar cerrado.
        return av1.EtapaResultado(
            nombre="actuacion", estado="fallo",
            detalle=f"hay un recibo de actuacion y no se puede interpretar ({exc}): "
                    f"no se crea otra sin mirar el expediente en el CRM",
            pendientes=(av1.Pendiente(
                codigo="actuacion_recibo_ilegible",
                detalle=f"Mira el expediente en el CRM y arregla o borra "
                        f"{_recibo_path(case_dir)}. Crear otra a ciegas duplicaria."),))

    # A QUE se cuelga la actuacion. Sin expediente vinculado no hay destino, y eso es
    # un pendiente —el alta puede venir en esta misma corrida o en otra—, no un fallo.
    destino = _expediente_del_caso(case_dir)
    if destino is None:
        return av1.EtapaResultado(
            nombre="actuacion", estado="saltada",
            detalle="el caso no tiene expediente CRM vinculado: no hay donde colgarla",
            pendientes=(av1.Pendiente(
                codigo="actuacion_sin_expediente",
                detalle="Da de alta el expediente (etapa `crm_alta`) y relanza "
                        "`--hasta actuacion`."),))
    elemento, exp_id = destino

    # **El atajo se comprueba AQUI, con el destino delante** (R2/H-04). Antes iba
    # arriba y no miraba a que expediente pertenecia el recibo: uno copiado de otro
    # caso daba por hecha una actuacion que aqui no existe. Un recibo de otro destino
    # no es un atajo: es una anomalia, y se declara.
    if previo is not None and previo.estado == "verificada":
        if str(getattr(previo, "exp_id", "")) == str(exp_id):
            return av1.EtapaResultado(
                nombre="actuacion", estado="saltada",
                detalle=f"ya hay actuacion verificada (id={previo.act_id}); no se crea otra")
        return av1.EtapaResultado(
            nombre="actuacion", estado="fallo",
            detalle=f"el recibo guardado es del expediente {previo.exp_id} y este caso "
                    f"apunta al {exp_id}: no acredita nada aqui",
            pendientes=(av1.Pendiente(
                codigo="actuacion_recibo_ajeno",
                detalle=f"Revisa {_recibo_path(case_dir)}: pertenece a otro expediente."),))

    def _alta_real(**kw):
        from core import sudespacho_actuaciones as sa
        # El asunto lo construye la funcion canonica, NO esta etapa: su prefijo es la
        # tarifa y copiarlo a mano factura al cliente la de otro (`[APER-72]`).
        return sa.alta_actuacion(
            elemento, exp_id, ident.case_id,
            asunto=sa.asunto_canonico(_ASUNTO_APERTURA, firmante=kw["firmante"]),
            **kw)

    try:
        recibo = (alta or _alta_real)(firmante=quien, desde=previo)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="actuacion", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")

    try:
        _guardar_recibo(case_dir, recibo)
    except OSError as exc:
        # El efecto remoto SI ocurrio; lo que fallo es poder reanudarlo.
        return av1.EtapaResultado(
            nombre="actuacion", estado="fallo",
            detalle=f"actuacion {recibo.act_id} creada pero su recibo no se pudo "
                    f"guardar ({exc}): un relanzamiento crearia otra.")

    if recibo.estado == "verificada":
        return av1.EtapaResultado(nombre="actuacion", estado="hecha",
                                  detalle=f"actuacion {recibo.act_id}, firma {quien}")
    if recibo.estado == "incierta":
        return av1.EtapaResultado(
            nombre="actuacion", estado="fallo",
            detalle=f"no se sabe si la actuacion se creo: {recibo.motivo}",
            pendientes=(av1.Pendiente(
                codigo="actuacion_incierta",
                detalle="Mira el expediente en el CRM antes de relanzar: el efecto pudo "
                        "ocurrir. El recibo queda guardado para reanudar."),))
    return av1.EtapaResultado(
        nombre="actuacion", estado="fallo",
        detalle=f"actuacion {recibo.estado} en el paso {recibo.paso}: {recibo.motivo}",
        pendientes=(av1.Pendiente(
            codigo=f"actuacion_{recibo.estado}",
            detalle="Relanza la etapa: el recibo guardado la reanuda sin crear otra."),))


def etapa_verificar(ident, case_dir: Path, *, crm: str = "api",
                    verificar=None) -> av1.EtapaResultado:
    """Etapa 6 (V2): el «OK» del EXPEDIENTE, no el del paso.

    Reutiliza `core.verificar_apertura.verificar`, que **ya existe**: la rev. 1 del plan
    proponia crear un agregador que llevaba ahi desde antes (R1/H-06).

    **Solo las comprobaciones de V2 deciden el estado.** Un `fallo` de la sala de lectura
    o de la viabilidad —fases de V3— viaja como pendiente y no bloquea: avanzar a medias
    en algo fuera de alcance no puede tumbar el lazo del CRM (R1/H-07). Y los CUATRO
    estados se traducen, `sin_implementar` incluido.
    """
    def _verificar_real(cd):
        from core import verificar_apertura as va
        # **Con fuentes REALES cuando la corrida autorizo el CRM** (R2/H-01). Sin
        # ellas `verificar` cae a `SinRed` y sus cinco comprobaciones de red salen en
        # `fallo`; como dos de las tres decisorias son de red, la etapa habria dado
        # `fallo` SIEMPRE y el bloqueo no habria significado nada. Con `skip` no hay
        # nada que consultar y no se sale: costaria tiempo y puede renovar tokens.
        fuentes = None
        if crm == "api":
            from core.verificar_apertura_fuentes import DeLaRed
            fuentes = DeLaRed()
        return va.verificar(cd, fuentes)

    try:
        informe = (verificar or _verificar_real)(case_dir)
    except Exception as exc:  # noqa: BLE001
        return av1.EtapaResultado(nombre="verificar", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")

    filas = list(getattr(informe, "resultados", ()) or ())
    # **Sin autorizacion no se escribio nada, asi que no se puede EXIGIR que este
    # escrito.** Con `--crm skip` las comprobaciones del CRM fallarian siempre y la
    # secuencia saldria `bloqueado` por no haber hecho lo que nadie le pidio. Siguen
    # viajando como pendiente: el diagnostico no se pierde, solo deja de bloquear.
    decisorias = COMPROBACIONES_DE_V2 if crm == "api" else frozenset()
    fallos_v2 = sorted(r.id for r in filas
                       if r.estado == "fallo" and r.id in decisorias)
    pendientes = tuple(
        av1.Pendiente(codigo=f"verificacion:{r.id}", detalle=(r.detalle or r.id))
        for r in filas
        if r.estado in ("pendiente", "sin_implementar", "fallo")
        and r.id not in fallos_v2)
    if fallos_v2:
        return av1.EtapaResultado(
            nombre="verificar", estado="fallo",
            detalle="comprobaciones de V2 en fallo: " + ", ".join(fallos_v2),
            pendientes=pendientes)
    return av1.EtapaResultado(nombre="verificar", estado="hecha",
                              detalle=f"{len(filas)} comprobaciones",
                              pendientes=pendientes)


def _etapas_v2(ident, case_dir, *, folder_id, team_id, crm):
    """Las seis etapas de V2, en el orden de `ETAPAS_V2`."""
    return [
        av1.Etapa("drive", lambda: etapa_drive(
            ident, case_dir, folder_id=folder_id, team_id=team_id)),
        av1.Etapa("crm", lambda: etapa_crm(ident, case_dir)),
        av1.Etapa("sala_maquina", lambda: etapa_sala_maquina(ident)),
        av1.Etapa("crm_alta", lambda: etapa_crm_alta(ident, case_dir, crm=crm)),
        av1.Etapa("actuacion", lambda: etapa_actuacion(ident, case_dir, crm=crm)),
        av1.Etapa("verificar", lambda: etapa_verificar(ident, case_dir, crm=crm)),
    ]


def secuencia_v1(ident, case_dir, *, folder_id, team_id, crm="skip", hasta=None,
                 etapas=None):
    """El orden completo de la secuencia: V1 (Drive -> CRM -> sala de maquina) + V2.

    La atomizacion del correo depositado va DENTRO de la tercera, que es donde el cableado
    de 2026-07-27 la puso; por eso el gotcha del runbook —atomizar y pull antes del OCR—
    se cumple por construccion y no por memoria del operador.

    `etapas` es el punto de inyeccion de los tests. En produccion se construyen aqui.
    """
    if etapas is None:
        etapas = _etapas_v2(ident, case_dir, folder_id=folder_id, team_id=team_id,
                            crm=crm)
    return av1.secuenciar(etapas, hasta=hasta)


def _informar_v1(resultado) -> None:
    """El informe en pantalla. Lo durable es el evento; esto es para el operador."""
    typer.echo("")
    typer.echo(f"=== Apertura V1: {resultado.estado} ===")
    for e in resultado.etapas:
        typer.echo(f"  [{e.estado:>7}] {e.nombre}: {e.detalle}")
    for n in resultado.no_ejecutadas:
        typer.echo(f"  [no corre] {n}")
    if resultado.parada:
        typer.echo(f"  (parada pedida tras la etapa {resultado.parada!r})")
    for p in resultado.pendientes:
        typer.echo(f"  PENDIENTE {p.codigo}: {p.detalle}")


def _verificar_expediente(case_dir: Path, w_code: str, *,
                          con_red: bool = True) -> None:
    """Corre `verificar_apertura` sobre el caso e imprime su informe.

    **No escribe en el EXPEDIENTE**, y la precision es de la R1 (H-06): el modulo es de
    solo lectura, pero salir a la red por `DeLaRed` puede renovar el token de rclone y
    **reescribir su fichero de configuracion**. Eso esta fuera del expediente y del repo,
    y lo documenta su propio productor en `core/intake_drive.py`; la promesa absoluta de
    «no escribe nada» era demasiado ancha.

    Import local a propósito: `verificar_apertura_fuentes` arrastra las dependencias de
    red, y este módulo se importa también para caminos que no salen a Internet.
    """
    from core import verificar_apertura as va

    fuentes = None
    if con_red:
        from core.verificar_apertura_fuentes import DeLaRed

        fuentes = DeLaRed()
    informe = va.verificar(case_dir, fuentes)
    typer.echo("")
    typer.echo("=== Verificacion del EXPEDIENTE (no del paso) ===")
    for r in informe.resultados:
        if r.estado == va.OK:
            continue                       # el informe completo, en el comando dedicado
        typer.echo(f"  [{r.estado:>15}] {r.titulo}")
        typer.echo(f"                    {r.detalle}")
    typer.echo(f"  {informe.resumen}")
    # El `case_id` se RECIBE, no se deduce del nombre de la carpeta: sacarlo de los
    # paréntesis funciona hasta el primer caso cuya carpeta no siga el patrón, y entonces
    # imprime una orden que no se puede copiar.
    # El **W-code**, no el `case_id` (R1/H-08): `ident.case_id` es el nombre completo
    # del caso —`BaRS3 - Calle de Prueba 1 (W-TEST01) - Vuelta`—, asi que la orden salia
    # con espacios y parentesis sin comillas y **no se podia copiar**. `Identidad` ya trae
    # `w_code` aparte; usarlo era gratis.
    typer.echo("  detalle completo: python -m scripts.verificar_apertura "
               f"--case-id {w_code} --con-red")


def _informar_v1_y_verificar(resultado, case_dir: Path, w_code: str) -> None:
    """Informa la ronda de V1 y, acto seguido, verifica el EXPEDIENTE (`MEJORAS #252`).

    **Por qué aquí y no como etapa.** `verificar_apertura` se construyó el 2026-09-11 y
    hasta el 2026-09-13 **no lo disparaba nadie**: ni V1, ni este CLI, ni el runbook. Una
    red que hay que acordarse de lanzar no atrapa nada, y la pieza existe precisamente
    porque «estar encima» no escala. Pero no puede ser una etapa: correría **bajo el
    mutex**, y ese módulo lo evita a propósito para poder usarse mientras otra cosa
    trabaja sobre el caso. Va donde solo se informa —fuera del bloque de exclusión— y
    **no toca el código de salida**: los bytes ya están depositados y el trabajo hecho.

    Y si la verificación misma revienta —token caducado, red caída—, se **dice** y se
    sigue. Un verificador que tumba lo que verifica es peor que no tenerlo; uno que se
    cae en silencio es peor todavía, porque deja creer que miró.
    """
    _informar_v1(resultado)
    try:
        _verificar_expediente(case_dir, w_code)
    except Exception as exc:  # noqa: BLE001 — informar no puede tumbar la apertura
        typer.echo("")
        typer.echo(f"[AVISO] no se pudo verificar el expediente: {exc}", err=True)
        typer.echo("        el estado del EXPEDIENTE queda SIN COMPROBAR (la apertura "
                   "sí terminó); repítelo con "
                   "`python -m scripts.verificar_apertura --case-id <W> --con-red`",
                   err=True)


def _alta_crm(
    ident: "brain.Identidad",
    *,
    cuantia: float | None,
    crm_mode: str,
    yes: bool,
    force: bool = False,
) -> ResultadoAlta:
    """5.9 alta CRM con gate + idempotencia (§8: no re-dar de alta si ya hay un
    extrajudicial registrado para este caso) + tolerancia a caída (§9)."""
    if crm_mode != "api":
        typer.echo("CRM omitido (--crm skip): referencia pendiente + TODO")
        return ResultadoAlta("omitido", None, "--crm skip")

    expedientes = case_manager.get_case_status(ident.case_id)["expedientes"]
    # La MISMA regla que el formulario (R1/H-08): cualquier expediente ya vinculado —de la
    # jurisdiccion que sea— cuenta como registrado. Antes solo se miraba el extrajudicial,
    # y un judicial vinculado desde la UI mandaba a la CLI al CRM, que abortaba pidiendo
    # «vincula el existente»: lo que ya estaba hecho.
    ya = alta_crm_politica.expediente_local_para_alta(expedientes, _ELEMENT_EXTRAJUDICIAL)
    if ya is not None:
        typer.echo(
            f"CRM ya registrado (element={ya.get('element')}, id={ya.get('id')}), "
            "no se re-da de alta"
        )
        return ResultadoAlta("ya_vinculado", str(ya.get("id") or ""),
                             f"element={ya.get('element')}")

    # El chequeo de arriba mira el `_caso.md` LOCAL. Si ese registro se perdio —o el
    # caso se abrio en otra maquina— el CRM puede tener ya el expediente y esto crearia
    # un duplicado en el CRM del cliente. Se pregunta al CRM.
    dup = sudespacho_relations.buscar_expedientes_duplicados(
        w_code=ident.w_code, direccion=ident.direccion,
    )

    # La regla (crear / vincular / bloquear) NO vive aqui: vive en
    # `core/alta_crm_politica.decidir`, que comparte con el formulario «Nuevo caso». Esta
    # funcion solo la traduce a la pantalla de la CLI. Las dos politicas que aplica, por
    # si alguien busca donde se decidieron:
    #   - **fallar cerrado** ante lo que no se pudo consultar (Nikolai, 2026-09-04; R1/H-02
    #     midio que antes se seguia adelante y la proteccion desaparecia justo cuando algo
    #     fallaba). `--force` es la salida explicita y deja escrito lo que no se miro.
    #   - **el W-code manda** sobre la incertidumbre: si ya esta en el CRM, se vincula y
    #     no se crea, se haya podido consultar el resto o no.
    decision = alta_crm_politica.decidir(dup, forzar=force)

    for aviso in decision.avisos:
        if aviso.startswith(alta_crm_politica.SIN_COMPROBAR):
            # El literal de siempre («SIN comprobar <criterio>»), no el prefijo del core:
            # la R1 (H-05) midio que el mensaje habia cambiado sin declararse.
            criterio = aviso[len(alta_crm_politica.SIN_COMPROBAR):]
            typer.echo(f"[AVISO] --force: se da de alta SIN comprobar {criterio}")
        else:
            typer.echo(f"[AVISO] posible expediente relacionado ({aviso}). "
                       "No bloquea: el mismo inmueble o la misma parte pueden tener varios.")

    if decision.accion == alta_crm_politica.BLOQUEAR:
        for nota in decision.sin_comprobar:
            typer.echo(f"  - sin comprobar: {nota}", err=True)
        typer.echo(
            "[ERROR] No se pudo comprobar si este expediente ya existe en el CRM, asi "
            "que no se da de alta: crearlo a ciegas puede duplicarlo. Reintenta cuando "
            "el CRM responda, o pasa --force si sabes que no existe.",
            err=True,
        )
        raise AbortarApertura(1)

    if decision.accion == alta_crm_politica.VINCULAR:
        donde = ", ".join(f"{el} #{i}" for el, i in decision.candidatos)
        typer.echo(
            f"[ERROR] El CRM ya tiene un expediente con el id GO {ident.w_code}: {donde}. "
            "No se da de alta otro. Si de verdad hacen falta dos, vincula el existente "
            "con `register_expediente` o crealo a mano en el CRM.",
            err=True,
        )
        # MEJORAS #142: `_alta_crm` corre BAJO el mutex, asi que no puede terminar el
        # proceso — un `typer.Exit` en vuelo hace que la perdida de exclusion quede en
        # una nota que Typer descarta. Lo caza el guard de
        # `tests/test_abrir_caso_exit_bajo_mutex.py`, que me cazo a mi al cablear esto.
        raise AbortarApertura(1)

    # `None` es «el flag no vino», y el DTO del CRM hace aritmetica con este valor
    # (`datos.cuantia + datos.costas + datos.intereses`): propagarlo reventaria un alta que
    # hoy funciona. La ausencia se traduce a `0.0` AQUI y a «no escribir la clave» en la
    # frontera local: son dos politicas distintas del mismo hecho (R1/H-04 de `#227`).
    payload = brain.crm_payload(ident, cuantia=0.0 if cuantia is None else cuantia)
    typer.echo(f"CRM -> alta extrajudicial ref={payload.referencia_cliente} "
               f"posicion={payload.posicion} tags={payload.tags} cuantia={payload.cuantia}")
    if not (yes or typer.confirm("¿Dar de alta en el CRM?")):
        typer.echo("CRM omitido (declinado por el usuario): referencia pendiente + TODO")
        return ResultadoAlta("declinado", None, "el operador declino el gate")

    # CUATRO desenlaces, no uno. Hasta el 2026-09-11 un solo `except` cubria el alta Y el
    # registro local, asi que un fallo del segundo imprimia «Alta CRM falló» con el alta
    # HECHA: el letrado reintentaba, el CRM ya tenia el expediente y el reintento era
    # esteril o duplicaba (`MEJORAS #227`, R1/H-05 del intento retirado). Y el cuarto
    # —escribir la cuantia en el indice— lo introduce esta pieza.
    try:
        exp_id = sudespacho_create.create_expediente(payload)
    except Exception as exc:
        typer.echo(
            f"[AVISO] Alta CRM falló ({exc!r}): Drive+intake ya completados, "
            "referencia_crm queda pendiente + TODO."
        )
        return ResultadoAlta("fallo_post", None, repr(exc))

    try:
        case_manager.register_expediente(ident.case_id, exp_id, _ELEMENT_EXTRAJUDICIAL)
    except Exception as exc:
        typer.echo(
            f"[AVISO] El alta en el CRM SI se hizo (id={exp_id}), lo que falló es "
            f"registrarla en `_caso.md` ({exc!r}). NO reintentes el alta: duplicarias el "
            f"expediente. Vincula el existente con `register_expediente({ident.case_id!r}, "
            f"{exp_id!r}, {_ELEMENT_EXTRAJUDICIAL!r})`."
        )
        return ResultadoAlta("fallo_registro", exp_id, repr(exc))
    typer.echo(f"OK CRM id={exp_id}")

    # La cuantia se conoce al leer el encargo, pero el alta va al final: por eso llega aqui
    # y no a `ensure_case`. Solo se escribe si el flag vino.
    if cuantia is None:
        return ResultadoAlta("creado", exp_id, "")
    try:
        informe = case_manager.update_meta(ident.case_id, cuantia=cuantia)
    except Exception as exc:
        typer.echo(
            f"[AVISO] El alta (id={exp_id}) y su registro local SI se hicieron; lo que falló "
            f"es escribir la cuantía en `_caso.md` ({exc!r}). Repetir el comando NO la "
            "repone —entra por la guarda de «CRM ya registrado» y retorna antes—: ponla a "
            "mano o con `case_manager.update_meta`."
        )
        return ResultadoAlta("creado", exp_id, "cuantia no escrita en _caso.md")
    # TRES estados, no dos (R2/H2-04): `!= "reescrito"` agrupaba «conservado» con «sin
    # tocar», y en el segundo NO se escribió ninguna clave — el mensaje decía «cuantía
    # escrita» seguido del motivo, que dice literalmente «no se escribe nada». Un aviso que
    # se contradice a sí mismo es peor que no avisar.
    if informe["cuerpo"] == "conservado":
        typer.echo(f"[AVISO] cuantía escrita en el frontmatter de `_caso.md`, "
                   f"pero NO en su cuerpo: {informe['motivo']}")
    elif informe["cuerpo"] == "sin tocar":
        typer.echo(f"[AVISO] la cuantía NO se ha escrito en `_caso.md`: "
                   f"{informe['motivo']}. La cuantía local sigue pendiente y no coincidirá "
                   f"con la del CRM; repásala a mano.")
    # El alta se hizo y se registró: los avisos de arriba son sobre la cuantía local, que
    # no cambia el desenlace del CRM.
    return ResultadoAlta("creado", exp_id, informe["cuerpo"])


def _autoderivar_drive_ev(
    *, folder_id, tipo_caso, team_id, codigo_caso, sufijo, direccion=None, w_code=None,
):
    """B5: en --fuente drive_ev, deriva los flags de identidad omitidos.

    - sufijo: puro, del tipo_caso (no necesita la Drive API).
    - team_id: driveId de la carpeta (--folder-id).
    - codigo_caso: nombre de la unidad compartida -> config.codigo_de_unidad.
    - direccion: prefijo del NOMBRE de la carpeta, con el W-code de delimitador
      (`MEJORAS #224`). Era el único de los seis sin fuente, y el 2026-09-10 se
      tecleó sin el acento que llevaba. El parser ya existía y ya lo consumía
      `streamlit_app.py`: lo que faltaba era que el CLI lo llamara.

    Los flags explícitos SIEMPRE ganan (solo se rellena lo que viene None).
    Degrada limpio: lo que no se pueda derivar queda None y lo caza el chequeo
    de flags de identidad con un error claro.
    """
    if sufijo is None and tipo_caso:
        sufijo = config.sufijo_de_tipo_caso(tipo_caso)
        typer.echo(f"[auto] --sufijo del tipo_caso: {sufijo!r}")

    if folder_id and (team_id is None or codigo_caso is None or direccion is None):
        info = intake_drive.get_drive_folder_info(folder_id)
        if info is None:
            typer.echo("[auto] No se pudo leer la carpeta de Drive (token/red); "
                       "pasa los flags que falten explícitos.")
            return team_id, codigo_caso, sufijo, direccion
        if team_id is None and info.drive_id:
            team_id = info.drive_id
            typer.echo(f"[auto] --team-id del driveId: {team_id}")
        if codigo_caso is None:
            drive_id_eff = team_id or info.drive_id
            unidad = intake_drive.get_shared_drive_name(drive_id_eff) if drive_id_eff else None
            derivado = config.codigo_de_unidad(unidad) if unidad else None
            if derivado:
                codigo_caso = derivado
                typer.echo(f"[auto] --codigo-caso de la unidad {unidad!r}: {codigo_caso}")
            else:
                typer.echo(f"[auto] No pude derivar --codigo-caso de la unidad {unidad!r}; "
                           "pásalo explícito.")
        if direccion is None:
            direccion = _direccion_de_la_carpeta(info.name, w_code)
    return team_id, codigo_caso, sufijo, direccion


def _direccion_de_la_carpeta(nombre_carpeta, w_code):
    """`MEJORAS #224` vía (a): la dirección, del nombre de la carpeta de E&V.

    Las carpetas se llaman ``<direccion> - <W-code> - <consultor captador>``, así que
    el W-code es el punto de corte exacto del prefijo. Devuelve None —y dice por
    qué— en los dos casos en que derivar sería adivinar:

    1. **El nombre no trae W-code.** Hay carpetas con nombre libre bajo
       ``PROPIEDADES/1. ACTIVAS``. Una derivación que adivine es peor que teclear.
    2. **El W-code del nombre no es el del caso.** El parser lo devuelve, así que
       comparar es gratis, y la comprobación vale lo que cuesta: el `case_id` se
       propaga a la carpeta del despacho, a `Referencia_Cliente` del CRM y a la
       etiqueta de Gmail, de modo que una dirección tomada de la carpeta de otro
       expediente queda estampada en los tres.

    No levanta error por sí misma: devolver None deja que la caza el chequeo de
    flags de identidad, igual que el resto de B5. Así esta pieza no puede bloquear
    ninguna invocación que hoy funcione.
    """
    derivada, w_carpeta = intake_drive.parse_ev_folder_name(nombre_carpeta or "")
    if not derivada:
        typer.echo(f"[auto] No pude derivar --direccion del nombre de la carpeta "
                   f"{nombre_carpeta!r}: no encuentro el W-code que delimita el "
                   "prefijo. Pásalo explícito.")
        return None
    # `CaseRef.normalizar` y no `.upper()`: el modelo ya define que un W-code canonico
    # va sin espacios de borde y en mayusculas. La R1 midio que con `--w-code " W-X "`
    # —un copia-pega con espacios— se acusaba una discrepancia FALSA y se obligaba a
    # teclear una direccion que era derivable, que es el mismo defecto que esta pieza
    # vino a cerrar, una vuelta mas abajo.
    from core.casos.workspace_model import CaseRef

    if (w_code and w_carpeta
            and CaseRef.normalizar(w_carpeta) != CaseRef.normalizar(str(w_code))):
        typer.echo(f"[auto] La carpeta {nombre_carpeta!r} declara {w_carpeta}, pero "
                   f"--w-code es {w_code}: no derivo --direccion de una carpeta que "
                   "dice ser de otro expediente. Pásalo explícito (y comprueba "
                   "--folder-id).")
        return None
    typer.echo(f"[auto] --direccion del nombre de la carpeta: {derivada!r}")
    return derivada


def _derivar_team_id(folder_id):
    """B5: driveId de la carpeta (= --team-id), o None si no se puede leer."""
    if not folder_id:
        return None
    info = intake_drive.get_drive_folder_info(folder_id)
    return info.drive_id if (info and info.drive_id) else None


def validar_modo(
    modo: str,
    *,
    crm: str | None,
    fuente: str,
    force: bool = False,
    dry_run: bool = False,
    folder_id: str | None = None,
    case_id: str | None = None,
    hasta: str | None = None,
) -> list[str]:
    """Errores que impiden ejecutar en `modo`. Lista vacía = admisible.

    Pura a propósito: la matriz de combinaciones se prueba sin arrancar el CLI ni
    tocar disco, y el orden —validar ANTES de cualquier efecto— queda demostrable.

    Los cuatro parámetros con default los añadió la remediación de R6: la puerta
    solo mirando `crm` y `fuente` admitía tres invocaciones que V1 prohíbe
    (H6-02, H6-03, H6-04). Llevan default para no regresar a los llamadores del
    modo `libre`, donde la función retorna antes de leerlos.
    """
    if modo not in _MODOS:
        return [f"Modo desconocido: {modo!r}. Válidos: {_MODOS}"]
    if modo == "libre":
        if hasta is not None:
            return ["--hasta solo existe en --modo v1: en `libre` no hay secuencia que "
                    "parar, y aceptarlo en silencio fingiria haberla parado."]
        return []
    errores: list[str] = []
    # HA-06 de la R-A. El vocabulario se valida AQUI y no dentro de `secuenciar`, que
    # corre despues de la identidad, del mutex y de `ensure_case`: en la rev. 1 un typo
    # abortaba con el esqueleto del caso ya creado.
    if hasta is not None and hasta not in ETAPAS_V2:
        errores.append(
            f"--hasta {hasta!r} no es una etapa; validas: {list(ETAPAS_V2)}")
    # La puerta del CRM NO desaparece con V2: cambia de forma. Antes prohibia escribir
    # («exige --crm skip») porque ninguna de las tres etapas lo hacia. Con `crm_alta` y
    # `actuacion` dentro, la garantia pasa a ser que la escritura se DECLARE: omitir el
    # flag no autoriza nada, porque su default es `api` y alcanzaria un POST de alta
    # (R1/H-01 — nombrar las etapas no acredita autorizacion).
    if crm is None:
        errores.append(
            "--modo v1 exige declarar --crm api|skip. Omitirlo no autoriza a escribir: "
            "con `crm_alta` y `actuacion` dentro de la secuencia, la ausencia del flag "
            "alcanzaria un POST de alta. Con `skip`, las etapas que escriben salen "
            "`saltada` con su pendiente."
        )
    elif crm not in _CRM_MODOS:
        errores.append(
            f"--crm solo admite {'|'.join(sorted(_CRM_MODOS))} (recibido: {crm!r}).")
    if fuente not in _FUENTES_V1:
        errores.append(
            f"--modo v1 solo admite --fuente {_FUENTES_V1[0]} (recibido: {fuente!r}). "
            "V1 no descubre ni exporta correo: `email` ejecuta email_export.export_label, "
            "que llama a Gmail. La atomización local de V1 actúa sobre correo YA depositado "
            "y la ejecuta la sala de máquina."
        )
    # H6-02 (CRÍTICO). Criterio 33 del §14, que el §21.4 mete en los 24 de V1:
    # «--force nunca crea una carpeta sombra». La política de colisión de la spec
    # admite --force SOLO para reutilizar el caso canónico ya resuelto por
    # --case-id; sin él, `resolver_identidad` esquiva `ColisionCaso` y compone un
    # case_id NUEVO para un W-code que ya existe.
    if force and case_id is None:
        errores.append(
            "--modo v1 no admite --force sin --case-id: con el W-code ya presente "
            "compondría un case_id nuevo y crearía una carpeta sombra, que el "
            "criterio 33 prohibe. El intake incremental entra por --case-id."
        )
    # H6-03. `_intake_drive_ev` llama a `pull_drive_ev` ANTES de consultar
    # dry_run, y el corte sale 0 antes del log de intake: una corrida con
    # efectos e incompleta etiquetada como V1. D3 hace al modo dueño del orden
    # COMPLETO, y el §13 exige que V1 termine en uno de sus tres estados.
    if dry_run:
        errores.append(
            "--modo v1 no admite --dry-run: en drive_ev el pull es real de todos "
            "modos y la corrida sale antes del log de intake, o sea con efectos y "
            "sin terminar en ninguno de los tres estados del contrato."
        )
    # H6-04. `_validar_flags` no exige nada para drive_ev, así que sin
    # --folder-id el pull recibe None DESPUÉS de que `pull_drive_ev` haya hecho
    # `target_dir.mkdir(...)`: se muta antes de detectar el dato que falta.
    # Se exige siempre en v1, no solo con drive_ev, porque drive_ev es su única
    # fuente y toda ejecución V1 materializa Drive E&V.
    if not folder_id:
        errores.append(
            "--modo v1 exige --folder-id: V1 materializa Drive E&V, y sin ese dato "
            "el pull recibe None después de crear el directorio destino."
        )
    return errores


@app.command()
def main(
    w_code: str | None = typer.Option(None, "--w-code"),
    ciudad: str | None = typer.Option(None, "--ciudad"),
    tipo_caso: str | None = typer.Option(None, "--tipo-caso"),
    codigo_caso: str | None = typer.Option(None, "--codigo-caso"),
    sufijo: str | None = typer.Option(None, "--sufijo"),
    direccion: str | None = typer.Option(None, "--direccion"),
    case_id: str | None = typer.Option(
        None, "--case-id",
        help="Intake incremental: resuelve identidad desde _caso.md (case_id o W-code). "
             "Excluyente con los 6 flags de identidad.",
    ),
    folder_id: str | None = typer.Option(None, "--folder-id"),
    team_id: str | None = typer.Option(None, "--team-id"),
    fuente: str = typer.Option("drive_ev", "--fuente", help="drive_ev|manual|whatsapp|email"),
    modo: str = typer.Option(
        "libre", "--modo",
        help="libre|v1. `v1` es el discriminante de la primera vertical (spec §24 D3): "
             "exige --crm skip y --fuente drive_ev, y valida antes de cualquier efecto."),
    hasta: str | None = typer.Option(
        None, "--hasta",
        help="v1: para DESPUES de esta etapa (drive|crm|sala_maquina). Para reanudar, "
             "relanza con --case-id (los 6 flags de identidad darian ColisionCaso): las "
             "etapas ya hechas se REPITEN, y son idempotentes (Drive vuelve a consultar y "
             "rclone transfiere solo lo que difiere; el pull del CRM se repite; la sala de "
             "maquina no reprocesa lo ya hecho)."),
    src: str | None = typer.Option(None, "--src", help="manual/whatsapp: carpeta o .zip"),
    rol: str | None = typer.Option(None, "--rol", help="whatsapp: rol_subdir"),
    cuenta: str | None = typer.Option(None, "--cuenta", help="email: cuenta gmail"),
    label: str | None = typer.Option(None, "--label", help="email: etiqueta"),
    extraer_adjuntos: bool = typer.Option(
        True, "--extraer-adjuntos/--no-extraer-adjuntos",
        help="email: saca cada adjunto como fichero suelto junto al .eml, para que la "
             "sala de máquina lo OCR-ee (un adjunto que llegue SOLO por correo, sin "
             "copia en el Drive, no se procesa sin esto). ACTIVO por defecto desde la "
             "acción 6b; los logotipos de firma se filtran y el .eml sigue siendo fiel"),
    cuantia: float | None = typer.Option(None, "--cuantia"),
    crm: str | None = typer.Option(
        None, "--crm",
        help="api|skip. OBLIGATORIO en --modo v1: ahi la secuencia incluye etapas "
             "que escriben en el CRM, y omitir el flag no las autoriza. En `libre` "
             "se resuelve a `api`, que era su default historico."),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "--yes", help="auto-confirma el gate CRM"),
) -> None:
    # Puerta del modo (spec §24 D3): se valida ANTES de la identidad, de ensure_case,
    # de todo intake y de toda lectura remota. El orden es la propiedad, no el mensaje.
    errores_modo = validar_modo(
        modo, crm=crm, fuente=fuente,
        force=force, dry_run=dry_run, folder_id=folder_id, case_id=case_id,
        hasta=hasta,
    )

    if errores_modo:
        for e in errores_modo:
            typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(code=1)

    # DESPUES de la puerta, y solo aqui: el modo `libre` conserva su default historico
    # (`api`). El secuenciado no llega con `None` —la puerta lo aborta—, asi que esta
    # linea no puede autorizar una escritura que nadie declaro (R1/H-01).
    if crm is None:
        crm = "api"

    if fuente not in _FUENTES_CLI:
        typer.echo(f"[ERROR] Fuente desconocida: {fuente}. Válidas: {_FUENTES_CLI}", err=True)
        raise typer.Exit(code=1)

    # 5.1 identidad — dos vías excluyentes: --case-id (intake incremental) o los 6 flags.
    flags_ident = [
        ("--w-code", w_code), ("--ciudad", ciudad), ("--tipo-caso", tipo_caso),
        ("--codigo-caso", codigo_caso), ("--sufijo", sufijo), ("--direccion", direccion),
    ]
    if case_id is not None:
        dados = [n for n, v in flags_ident if v is not None]
        if dados:
            typer.echo(f"[ERROR] --case-id es excluyente con los flags de identidad: {dados}", err=True)
            raise typer.Exit(code=1)
        resolved = case_locator.resolve_ref(case_id)
        # `buscar` y no `path_for`: un `--case-id` inexistente tiene que salir
        # por este mensaje, no por una traza. Medido antes de migrar.
        case_dir = case_locator.buscar(resolved)
        if case_dir is None or not (case_dir / "00_Input" / "_caso.md").is_file():
            typer.echo(f"[ERROR] Caso no encontrado para --case-id {case_id!r} "
                       f"(resuelto: {resolved!r})", err=True)
            raise typer.Exit(code=1)
        meta = case_locator.read_case_meta(case_dir)
        tipo_caso_eff, ciudad = meta.get("tipo_caso"), meta.get("ciudad")
        if not tipo_caso_eff or not ciudad:
            typer.echo("[ERROR] _caso.md sin tipo_caso/ciudad; usa los flags de identidad", err=True)
            raise typer.Exit(code=1)
        try:
            codigo_p, direccion_p, w_code_p, sufijo_p = brain.descomponer_case_id(resolved)
        except ValueError:
            typer.echo(
                "[ERROR] --case-id no soporta este formato de case_id "
                f"(usa los 6 flags de identidad): {resolved!r}", err=True,
            )
            raise typer.Exit(code=1)
        ident = brain.resolver_identidad(
            codigo=codigo_p, direccion=direccion_p, w_code=w_code_p, sufijo=sufijo_p,
            tipo_caso=tipo_caso_eff, nombres_existentes=[], force=True,
        )
        # Pin al nombre de carpeta YA VERIFICADO (`resolved`): el round-trip
        # componer(descomponer(...)) normaliza espacios/formato y podría no
        # coincidir byte a byte si la carpeta real no es perfectamente
        # canónica, desviando ensure_case/intake a una carpeta NUEVA (el bug
        # [APER-19] que esta feature previene).
        ident = dataclasses.replace(ident, case_id=resolved)
    else:
        if fuente == "drive_ev":
            team_id, codigo_caso, sufijo, direccion = _autoderivar_drive_ev(
                folder_id=folder_id, tipo_caso=tipo_caso,
                team_id=team_id, codigo_caso=codigo_caso, sufijo=sufijo,
                direccion=direccion, w_code=w_code,
            )
        flags_ident_eff = [
            ("--w-code", w_code), ("--ciudad", ciudad), ("--tipo-caso", tipo_caso),
            ("--codigo-caso", codigo_caso), ("--sufijo", sufijo), ("--direccion", direccion),
        ]
        faltan = [n for n, v in flags_ident_eff if v is None]
        if faltan:
            typer.echo(f"[ERROR] faltan flags de identidad {faltan} (o usa --case-id)", err=True)
            raise typer.Exit(code=1)
        if ciudad not in CIUDADES:
            typer.echo(f"[ERROR] Ciudad desconocida: {ciudad}", err=True)
            raise typer.Exit(code=1)
        nombres = [p.name for p in case_locator.list_cases(ciudad)]
        try:
            ident = brain.resolver_identidad(
                codigo=codigo_caso, direccion=direccion, w_code=w_code, sufijo=sufijo,
                tipo_caso=tipo_caso, nombres_existentes=nombres, force=force,
            )
        except brain.ColisionCaso as exc:
            typer.echo(f"[ERROR] {exc}", err=True)
            raise typer.Exit(code=1)
        # `ValueError` sale de `componer_case_id` (`MEJORAS #148`: una dirección con `/`
        # no puede ser una carpeta) y de un `--tipo-caso` desconocido. Sin este `except`
        # las dos salían en traceback, y la primera no salía en absoluto: la corrida
        # terminaba en 0 dejando el intake en una ruta sombra. Muerde ANTES de
        # `ensure_case`, así que no se crea esqueleto alguno.
        except ValueError as exc:
            typer.echo(f"[ERROR] Identidad del caso inválida: {exc}", err=True)
            raise typer.Exit(code=1)
        if ident.requiere_confirmacion and not force:
            typer.echo(f"[AVISO] El código {ident.codigo} ya existe: {ident.colisiones}")
            if not (yes or typer.confirm("¿Crear igualmente con este código?")):
                raise typer.Exit(code=1)

    if ciudad not in CIUDADES:
        typer.echo(f"[ERROR] Ciudad desconocida: {ciudad}", err=True)
        raise typer.Exit(code=1)

    # 5.1.b (B5) drive_ev necesita --team-id para el pull rclone. Se deriva del
    # --folder-id si se omitió — también en la vía --case-id (re-pull), que no
    # pasa por _autoderivar_drive_ev. Si aun así no se resuelve, error limpio
    # (evita el TypeError de rclone con team_id=None). En el camino feliz de 6
    # flags, _autoderivar_drive_ev ya lo fijó y este bloque no vuelve a llamar.
    if fuente == "drive_ev" and team_id is None:
        team_id = _derivar_team_id(folder_id)
        if team_id is not None:
            typer.echo(f"[auto] --team-id del driveId: {team_id}")
        else:
            typer.echo("[ERROR] --fuente drive_ev requiere --team-id: no se pudo "
                       "derivar de --folder-id (sin --folder-id o token/red); "
                       "pásalo explícito.", err=True)
            raise typer.Exit(code=1)

    # 5.2 — a partir de aquí, TODO va bajo el mutex del caso (Plan 3A, Task 5).
    #
    # Este es el punto en que el mutex de #247 empieza a proteger algo: hasta ahora
    # existía, estaba probado y no lo llamaba nadie. El bloque cubre el esqueleto, el
    # intake y el alta CRM, que es la secuencia que D3 pone bajo el dueño del modo.
    #
    # **En los dos modos, no solo en `v1`.** El dolor MEDIDO que justificó D2 es
    # «relanzar el pipeline sobre el mismo caso sin saber si la corrida anterior
    # terminó», y eso pasa en `libre`, que es el modo que se usa hoy. Adquirir solo en
    # `v1` habría dejado el mutex sin proteger nada real otra vez.
    #
    # El reloj va con offset EXPLÍCITO: `case_mutex` rechaza un instante naïve a
    # propósito, y `now_iso` —el mayoritario del repo, 43 usos frente a 5— lo es.
    from core.casos.workspace_model import CaseBusy, MutexPerdido

    # `resultado_v1` se calcula DENTRO del bloque y se consume FUERA (HA-07 de la R-A):
    # `case_mutex.tomado` LANZA `MutexPerdido` si el bloque sale limpio y solo lo ANOTA si
    # hay una excepcion en vuelo. Un `typer.Exit` dentro del `with` convertiria una perdida
    # de exclusion en una salida 0 con el aviso enterrado en una nota del traceback.
    # `MEJORAS #142`: la validacion de flags corre AQUI — fuera del mutex, porque fallar
    # por un flag mal puesto no necesita el lock adquirido y hacerlo dentro dejaba un
    # `typer.Exit` bajo exclusion, que es el defecto entero.
    #
    # **Y despues de resolver identidad, no antes.** Adelantarla del todo cambiaba el
    # diagnostico que ve el operador: con `--fuente manual` y sin flags de identidad, antes
    # decia «faltan los seis flags de identidad» y pasaba a decir solo «falta --src», que
    # es el problema menos fundamental de los dos. Lo midio la ronda de este diff (HD-04):
    # sacar la validacion del lock no autorizaba a reordenar lo que el operador lee.
    try:
        _validar_flags(fuente, folder_id=folder_id, team_id=team_id, src=src, rol=rol,
                       cuenta=cuenta, label=label)
    except AbortarApertura as exc:
        raise typer.Exit(code=exc.codigo) from exc

    resultado_v1 = None
    salida_dry_run = False
    try:
        with mutex_sesion.sostenido(CaseRef(w_code=ident.w_code) if ident.w_code
                                    else CaseRef(case_id=ident.case_id),
                                    ahora_fn=now_iso_utc) as sesion:
            # 5.2 esqueleto (idempotente; con --case-id el caso ya existe)
            case_manager.ensure_case(
                ident.case_id, titulo=ident.case_id, referencia_crm=ident.case_id,
                tipo_caso=ident.tipo_caso, ciudad=ciudad, direccion=ident.direccion,
                id_go=ident.w_code, modo=modo,
            )
            # `localizar` y no `path_for`: el esqueleto acaba de crearse, así que el caso DEBE
            # existir y su ausencia es un fallo, no un valor. Es lo que la clasificación firmada
            # del Task 6 decía para este sitio, y quedó como cabo suelto del 65º cierre; el
            # comportamiento no cambia —`path_for` ya es estricto por defecto— pero el nombre
            # ahora dice qué se espera, que es justo lo que un flag no permite auditar.
            case_dir = case_locator.localizar(ident.case_id)

            if modo == "v1":
                # El estado durable de la spec §11. Se abre ANTES de correr nada: si la
                # corrida muere, lo que queda en disco dice que empezo y no termino.
                previa = estado_v1.leer(case_dir)
                if previa is not None and previa.sin_cerrar():
                    typer.echo(
                        f"[AVISO] la ronda {previa.ronda_id!r} (iniciada "
                        f"{previa.iniciada}) no llego a cerrarse: esta corrida no da por "
                        f"buena su salida.", err=True)
                # Un solo reloj: `ronda_id` e `iniciada` eran dos lecturas y divergian.
                arranque = now_iso_utc()
                ronda = estado_v1.abrir(case_dir, ronda_id=arranque, ahora=arranque)
                resultado_v1 = secuencia_v1(ident, case_dir, folder_id=folder_id,
                                            team_id=team_id, crm=crm, hasta=hasta)
                # **revalidar -> publicar -> liberar**, en ese orden e indivisible.
                #
                # La rev. anterior publicaba FUERA del bloque «para no afirmar un exito
                # que la perdida del lease desmiente», y con eso escribia sin exclusion
                # ninguna: R-C midio la intercalacion `R1 abre / R1 libera / R2 abre / R1
                # cierra`, que deja el fichero con la ronda R1 y BORRA la evidencia de que
                # R2 sigue en curso (HC-02). El comentario de entonces decia, correcto,
                # que «escribir sin mutex es la violacion que el mutex existe para
                # impedir» — y el codigo hacia justo eso cuatro lineas mas abajo.
                #
                # Y `revalidar()` primero porque el gestor cede la sesion y no consultarla
                # deja que una perdida a mitad de una etapa larga pase inadvertida hasta la
                # salida, con dos escritores sobre el mismo expediente (HC-01).
                if not sesion.revalidar():
                    raise MutexPerdido(
                        w_code=getattr(sesion, "w_code", None) or "",
                        detalle="el mutex dejo de ser nuestro antes de publicar el "
                                "resultado: no se escribe nada")
                # El evento forense va PRIMERO (HC-03): el `.jsonl` es append-only y
                # autoritativo, y el `estado.json` es el marcador derivado. Al reves, un
                # append fallido dejaba el estado diciendo «terminada» sin rastro alguno.
                registrar_cierre_v1(case_dir, ident, resultado_v1)
                estado_v1.cerrar(
                    case_dir, ronda, estado=resultado_v1.estado,
                    etapas={e.nombre: e.estado for e in resultado_v1.etapas},
                    ahora=now_iso_utc())
            else:
                # 5.3-5.7 intake por fuente
                _despachar_intake(
                    fuente, ident, case_dir,
                    folder_id=folder_id, team_id=team_id, src=src, rol=rol,
                    cuenta=cuenta, label=label, dry_run=dry_run,
                    extraer_adjuntos=extraer_adjuntos,
                )
                if dry_run:
                    # **El peor de los nueve de `MEJORAS #142`.** Un `Exit(0)` es una
                    # terminacion CON EXITO disfrazada de excepcion, asi que el `finally`
                    # de `case_mutex.tomado` se limitaba a ANOTAR una perdida del lease
                    # sobre ella en vez de lanzarla: anotar una perdida de exclusion sobre
                    # un exito es exactamente la mentira que el mecanismo evita.
                    #
                    # Ahora se marca y se sale FUERA del bloque, con lo que un lease
                    # perdido vuelve a levantar `MutexPerdido` y el operador se entera.
                    typer.echo(
                        f"[dry-run] esqueleto en {case_dir}; se omiten log de intake y alta CRM")
                    salida_dry_run = True
                else:
                    _alta_crm(ident, cuantia=cuantia, crm_mode=crm, yes=yes,
                              force=force)
    except CaseBusy as exc:
        typer.echo(f"=== Apertura: {av1.EstadoV1.BLOQUEADO} ===", err=True)
        typer.echo(f"  otro proceso tiene este caso; espera y reintenta: {exc}", err=True)
        raise typer.Exit(code=codigo_de_salida(av1.EstadoV1.BLOQUEADO))
    except AbortarApertura as exc:
        # El mensaje ya lo imprimio quien aborto. Lo que se anade aqui es lo que Typer
        # descartaba: si el `finally` del mutex anoto una perdida de exclusion sobre esta
        # excepcion, esa nota es lo mas importante de la salida y hay que decirla en voz
        # alta en vez de dejarla en un traceback que nadie ve.
        for nota in getattr(exc, "__notes__", ()) or ():
            typer.echo(f"[AVISO] {nota}", err=True)
        raise typer.Exit(code=exc.codigo) from exc
    except MutexPerdido as exc:
        # NO es lo mismo que `CaseBusy` (R-B/L3-05): aqui puede haber trabajo a medias
        # escrito sin exclusion, y el operador tiene que revisar antes de reintentar.
        typer.echo(f"=== Apertura: {av1.EstadoV1.BLOQUEADO} ===", err=True)
        typer.echo(f"  se PERDIO la exclusion durante la operacion: {exc}", err=True)
        typer.echo("  puede haber trabajo a medias; revisa el caso antes de reintentar.",
                   err=True)
        raise typer.Exit(code=codigo_de_salida(av1.EstadoV1.BLOQUEADO))

    # El registro DURABLE se escribe aqui, fuera del bloque, y solo si el bloque salio
    # limpio (R-B/L3-01, confirmado por cuatro lentes). Dentro, una perdida del lease se
    # anota en vez de lanzarse, asi que el `.jsonl` y el `estado.json` quedaban afirmando
    # un exito que la pantalla desmentia.
    #
    # **Y si se perdio la exclusion no se escribe NADA**, ni siquiera un `bloqueado`:
    # escribir sin mutex es la violacion que el mutex existe para impedir. La ronda queda
    # ABIERTA en disco, y la corrida siguiente la ve `sin_cerrar()` y avisa — que es lo
    # que hace que ese aviso sea el mecanismo y no un adorno.
    # Fuera del bloque queda SOLO lo que no escribe: informar y salir. El `Exit` sigue
    # aqui porque dentro convertiria una perdida del lease en una nota sobre una salida
    # limpia (HA-07 de R-A) — pero ya no hay ninguna escritura a este lado.
    if salida_dry_run:
        raise typer.Exit(code=0)

    if resultado_v1 is not None:
        _informar_v1_y_verificar(resultado_v1, case_dir, ident.w_code)
        raise typer.Exit(code=codigo_de_salida(resultado_v1.estado))

    typer.echo(f"OK Caso abierto: {ident.case_id}")


if __name__ == "__main__":
    app()
