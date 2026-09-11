"""`verificar_apertura` — el «OK» del EXPEDIENTE, no el del paso.

Diseño: `docs/superpowers/plans/2026-09-11-apertura-menos-decisiones.md` §5 (pieza P2 de
la fila #28 de `PLAN.md`).

**El defecto que cierra no es de una herramienta, es de todas.** Cada una declara el
resultado de *su paso* y ninguna el del expediente. El handoff del 2026-09-10 contó ocho
falsos «OK» en un solo día: `organizar` diciendo «sala organizada» con 2 de los 4
artefactos escritos (`MEJORAS #221`), `render_informe` diciendo «OK» con 51 de 88 filas
sin marcar, `apply_label` devolviendo éxito sin aplicar la etiqueta (`#237`), el pull
declarando «hecho» con hashes falsos (`#225`), `ensure_contrario_vinculado` diciendo
«existente» con el id de otro deudor (`#239`). Mientras nadie cierre el lazo sobre el
expediente, el verificador es el letrado, y eso es «estar encima».

**La regla que gobierna todas las comprobaciones: verificar por resultado, nunca por
status.** Ninguna se apoya en el código de salida de la herramienta que produjo el
artefacto. Todas leen el artefacto.

**Solo lectura.** Este módulo no escribe, no repara y no pide el mutex. Un verificador
que arregla lo que encuentra deja de poder decir qué encontró.

## Los cuatro estados

`ok` · `pendiente` · `fallo` son los del diseño. `pendiente` **no** es `fallo`: un
expediente a medias tiene que poder verificarse sin que el informe grite — si «aún no
hay sala de lectura» saliera en rojo, el rojo dejaría de significar algo.

El cuarto, `sin_implementar`, es deliberado. Cinco comprobaciones necesitan red y no se
han construido. Dejarlas fuera de la lista haría que el informe dijera «9 de 9» habiendo
mirado 4 — **el modo de fallo que esta pieza cierra, cometido por la pieza**. Se
enumeran siempre, y `sin_implementar` no cuenta como comprobada: un instrumento que solo
puede devolver un valor no mide nada.

## La regla que la R1 me obligó a escribir

**No poder mirar NO es «no hay nada que ver».** La primera versión trataba cada
imposibilidad como ausencia benigna: un espejo que no se podía leer salía como «ninguno
ajeno»; una lista con entradas corruptas se filtraba en silencio y el conteo cuadraba;
un `01_Procesado` que era un fichero en vez de una carpeta se leía como «la sala aún no
ha corrido». Los tres devolvían verde sobre expedientes rotos.

Ahora toda imposibilidad de leer, toda forma inválida y toda colisión de tipo son
**`fallo`**, con el motivo. `pendiente` queda reservado para la ausencia legítima: el
productor todavía no ha corrido.
"""
from __future__ import annotations

import dataclasses
import json
import re
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:                                     # pragma: no cover
    from core.verificar_apertura_fuentes import Fuentes

# --- Vocabulario ------------------------------------------------------------------

OK = "ok"
PENDIENTE = "pendiente"
FALLO = "fallo"
SIN_IMPLEMENTAR = "sin_implementar"

#: Los estados que SÍ son el resultado de haber mirado. `sin_implementar` queda fuera a
#: propósito: es la declaración de un hueco, no una medición.
ESTADOS_MEDIDOS: frozenset[str] = frozenset({OK, PENDIENTE, FALLO})
ESTADOS: frozenset[str] = ESTADOS_MEDIDOS | {SIN_IMPLEMENTAR}


@dataclasses.dataclass(frozen=True)
class Resultado:
    """El veredicto de una comprobación, con la evidencia que lo sostiene.

    `evidencia` lleva los números que hacen el veredicto reproducible a mano. Un
    `fallo` sin los conteos que lo produjeron obliga a repetir el trabajo para saber
    qué pasó.
    """
    id: str
    titulo: str
    estado: str
    detalle: str
    evidencia: dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS:
            raise ValueError(f"estado {self.estado!r} fuera de {sorted(ESTADOS)}")


@dataclasses.dataclass(frozen=True)
class Informe:
    case_dir: str
    resultados: list[Resultado]

    @property
    def fallos(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado == FALLO]

    @property
    def comprobadas(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado in ESTADOS_MEDIDOS]

    @property
    def resumen(self) -> str:
        n_ok = sum(1 for r in self.resultados if r.estado == OK)
        n_pend = sum(1 for r in self.resultados if r.estado == PENDIENTE)
        return (f"{len(self.comprobadas)} de {len(self.resultados)} comprobaciones "
                f"ejecutadas — {n_ok} ok, {n_pend} pendiente(s), "
                f"{len(self.fallos)} fallo(s)")


# --- Rutas canónicas del expediente -------------------------------------------------
#
# Se componen aquí en vez de importarlas de sus dueños porque este módulo NO debe poder
# escribir: importar `sala_maquina` para una ruta arrastra su motor entero.

_PROCESADO = "01_Procesado"
_SALA_MAQUINA = "02_Sala de máquina"
_SALA_LECTURA = "Sala lectura"
_CATALOGO = "indice_documental.yaml"
_ARTEFACTOS_SALA = ("INDICE.md", "CRONOLOGIA.md", "_MANIFIESTO.md", _CATALOGO)


class _ColisionDeTipo(Exception):
    """Una ruta estructural existe pero no es lo que tiene que ser.

    `MEJORAS`/R1 H-06: con `01_Procesado` ocupado por un FICHERO, la primera versión
    informaba «la sala no ha corrido» y salía en verde. No es que falte una etapa: es
    que la etapa **no puede** correr, y eso es un fallo del expediente.
    """


def _dir_estructural(p: Path, etiqueta: str) -> Path | None:
    """La ruta si es un directorio, `None` si no existe, y revienta si colisiona."""
    if p.is_dir():
        return p
    if p.exists():
        raise _ColisionDeTipo(f"`{etiqueta}` existe y NO es un directorio: {p.name}")
    return None


def _sala_maquina(case_dir: Path) -> Path | None:
    proc = _dir_estructural(case_dir / _PROCESADO, _PROCESADO)
    return _dir_estructural(proc / _SALA_MAQUINA, _SALA_MAQUINA) if proc else None


def _de_red(fn: Callable) -> Callable:
    """Marca una comprobación como dependiente de `Fuentes`."""
    fn._necesita_fuentes = True                            # type: ignore[attr-defined]
    return fn


# --- Las comprobaciones -------------------------------------------------------------


# El título dice «cuántos», no «cuáles», y eso es deliberado (R1 H-03). La cobertura
# identifica por `slug` y el catálogo por `id_doc`: **no comparten clave**, así que
# comparar conjuntos exigiría una correspondencia que los datos no llevan. Lo que esta
# comprobación acredita es cardinalidad, y el nombre no puede prometer más de lo que
# mide — que es el defecto que toda esta pieza persigue. Comparar por identidad queda
# en el inventario de lo no cubierto, con su gate.
_T_C3 = "Cuántos documentos lógicos hay en la cobertura y cuántas entradas en el catálogo"


def c3_cobertura_vs_catalogo(case_dir: Path) -> Resultado:
    """Filas de `_cobertura.json` menos hijos de bundle, contra entradas del catálogo.

    `[APER-60]`, con la corrección del 102º: los **hijos de bundle** no son entradas del
    catálogo —el catálogo indexa documentos lógicos— así que restarlos es lo que hace
    comparables los dos lados. Sin esa resta, un caso con un PDF segmentado en veinte
    piezas parecería tener veinte documentos sin catalogar.

    **Un hijo solo cuenta como hijo si su padre existe** (R1 H-02). Antes bastaba
    cualquier valor verdadero en `parent_slug` —un número, un slug inexistente, el suyo
    propio— para descontar un documento del conteo, de modo que un documento podía
    desaparecer del catálogo y el verificador bendecirlo.
    """
    cob_path = _ruta_cobertura(case_dir)
    cat_path = case_dir / _PROCESADO / _CATALOGO
    if cob_path is None or not cob_path.is_file():
        return Resultado("cobertura_vs_catalogo", _T_C3, PENDIENTE,
                         "no hay `_cobertura.json`: la sala de máquina no ha corrido")
    if not cat_path.is_file():
        if cat_path.exists():
            return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                             f"`{_CATALOGO}` existe y no es un fichero")
        return Resultado("cobertura_vs_catalogo", _T_C3, PENDIENTE,
                         "no hay catálogo: la sala de lectura no se ha montado")

    filas, err = _leer_lista_de_mapas(cob_path, json.loads)
    if err:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         f"`{cob_path.name}`: {err}")
    entradas, err = _leer_lista_de_mapas(cat_path, _yaml_load)
    if err:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         f"`{cat_path.name}`: {err}")

    slugs = {str(f.get("slug") or "").strip() for f in filas}
    slugs.discard("")
    huerfanos, logicos = [], []
    for f in filas:
        padre = f.get("parent_slug")
        if padre is None or (isinstance(padre, str) and not padre.strip()):
            logicos.append(f)
            continue
        if not isinstance(padre, str):
            huerfanos.append(f"{f.get('slug')!r}: parent_slug no es texto ({padre!r})")
            continue
        padre = padre.strip()
        if padre == str(f.get("slug") or "").strip():
            huerfanos.append(f"{f.get('slug')!r}: se declara hijo de sí mismo")
        elif padre not in slugs:
            huerfanos.append(f"{f.get('slug')!r}: padre {padre!r} no está en la cobertura")

    ev = {"filas_cobertura": len(filas), "hijos_de_bundle": len(filas) - len(logicos) - len(huerfanos),
          "documentos_logicos": len(logicos), "entradas_catalogo": len(entradas),
          "huerfanos": huerfanos[:8]}
    if huerfanos:
        return Resultado("cobertura_vs_catalogo", _T_C3, FALLO,
                         f"{len(huerfanos)} fila(s) con `parent_slug` que no apunta a "
                         f"un bundle real: {'; '.join(huerfanos[:3])}", ev)
    if len(logicos) == len(entradas):
        return Resultado("cobertura_vs_catalogo", _T_C3, OK,
                         f"{len(logicos)} documentos lógicos y {len(entradas)} "
                         "entradas del catálogo (solo cardinalidad)", ev)
    return Resultado(
        "cobertura_vs_catalogo", _T_C3, FALLO,
        f"{len(logicos)} documentos lógicos en la cobertura contra "
        f"{len(entradas)} entradas del catálogo: faltan "
        f"{abs(len(logicos) - len(entradas))}", ev)


def c4_artefactos_de_la_sala(case_dir: Path) -> Resultado:
    """Los cuatro artefactos que la sala de lectura contrata (`MEJORAS #221`).

    El CLI decía «Sala de lectura organizada» habiendo escrito **dos de los cuatro**. Lo
    que lo hace caro no es que falten: es que el operador lee «organizada» y no vuelve a
    mirar. Esta comprobación es el lector que sí mira.
    """
    titulo = "Los cuatro artefactos de la sala de lectura"
    proc = _dir_estructural(case_dir / _PROCESADO, _PROCESADO)
    sala = _dir_estructural(proc / _SALA_LECTURA, _SALA_LECTURA) if proc else None
    if sala is None:
        return Resultado("artefactos_sala", titulo, PENDIENTE,
                         "no hay `Sala lectura`: no se ha montado")
    # El catálogo vive en `01_Procesado/`, no dentro de la sala.
    ubicacion = {n: (proc / n if n == _CATALOGO else sala / n) for n in _ARTEFACTOS_SALA}
    faltan = sorted(n for n, p in ubicacion.items() if not p.is_file())
    no_ficheros = sorted(n for n, p in ubicacion.items() if p.exists() and not p.is_file())
    vacios = sorted(n for n, p in ubicacion.items()
                    if p.is_file() and p.stat().st_size == 0)
    ev = {"presentes": sorted(set(_ARTEFACTOS_SALA) - set(faltan)),
          "faltan": faltan, "vacios": vacios, "no_ficheros": no_ficheros}
    if no_ficheros:
        return Resultado("artefactos_sala", titulo, FALLO,
                         f"existen pero NO son ficheros: {', '.join(no_ficheros)}", ev)
    if faltan:
        return Resultado("artefactos_sala", titulo, FALLO,
                         f"faltan {len(faltan)} de {len(_ARTEFACTOS_SALA)}: "
                         f"{', '.join(faltan)}", ev)
    if vacios:
        # Un fichero de cero bytes cuenta como ausente: existe para `is_file()` y no
        # dice nada. Distinguirlo importa porque el modo de fallo es el mismo.
        return Resultado("artefactos_sala", titulo, FALLO,
                         f"presentes pero VACÍOS: {', '.join(vacios)}", ev)
    return Resultado("artefactos_sala", titulo, OK,
                     f"los {len(_ARTEFACTOS_SALA)} presentes y con contenido", ev)


#: El dominio que el generador escribe en la columna M, y el único que la hoja acepta.
#: `si` sin tilde entra como equivalencia de grafía, igual que en `render_informe`.
_MARCAS_VALIDAS = frozenset({"sí", "si", "no"})


def c5_viabilidad_completa(case_dir: Path, *, filas_esperadas: int = 88) -> Resultado:
    """Las 88 preguntas, con identidad única y con respuesta **o** marca del dominio.

    Es el defecto que cerró la pieza P5, mirado desde fuera: el generador podía dejar
    filas en blanco y decir «OK».

    **Contar no-vacíos no basta** (R1 H-04): una hoja con las 88 marcas a `basura`, o con
    la misma pregunta repetida 88 veces, pasaba en verde. Ahora se exige que la marca
    esté en el dominio y que los identificadores sean únicos — «las 88 preguntas» es una
    afirmación sobre identidades, no sobre filas.
    """
    titulo = "Las 88 preguntas del informe de viabilidad, marcadas"
    analisis = case_dir / "02_Analisis"
    if analisis.exists() and not analisis.is_dir():
        return Resultado("viabilidad_completa", titulo, FALLO,
                         "`02_Analisis` existe y no es un directorio")
    informes = sorted(analisis.glob("Informe viabilidad*.xlsx")) if analisis.is_dir() else []
    if not informes:
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         "no hay informe de viabilidad en `02_Analisis`")
    try:
        import openpyxl
    except ImportError:                                    # pragma: no cover
        return Resultado("viabilidad_completa", titulo, SIN_IMPLEMENTAR,
                         "no construida aquí: falta openpyxl en este entorno")

    # El más reciente: una apertura deja el del pre-relleno y el firmado. Un EMPATE de
    # mtime no se resuelve por orden alfabético (R1 H-11): sin regla de vigencia, elegir
    # es adivinar, y adivinar puede ocultar el informe malo detrás del bueno.
    mas_nuevo = max(p.stat().st_mtime for p in informes)
    candidatos = [p for p in informes if p.stat().st_mtime == mas_nuevo]
    if len(candidatos) > 1:
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         f"{len(candidatos)} informes con la misma fecha de "
                         "modificación: no hay regla que diga cuál es el vigente",
                         {"empatados": sorted(p.name for p in candidatos)})
    informe = candidatos[0]
    try:
        wb = openpyxl.load_workbook(informe, read_only=True, data_only=True)
    except Exception as exc:                               # noqa: BLE001
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"`{informe.name}` no se puede abrir: {exc!r}")
    try:
        if "PREGUNTAS" not in wb.sheetnames:
            return Resultado("viabilidad_completa", titulo, FALLO,
                             f"`{informe.name}` no tiene hoja PREGUNTAS")
        ws = wb["PREGUNTAS"]
        ids, sin_marca, marca_invalida = [], [], []
        for fila in ws.iter_rows(min_row=5, max_col=13):
            idq = fila[2].value if len(fila) > 2 else None      # C
            if _vacio(idq):
                continue
            idq = str(idq).strip()
            ids.append(idq)
            respuesta = fila[8].value if len(fila) > 8 else None    # I
            pendiente = fila[12].value if len(fila) > 12 else None  # M
            if not _vacio(pendiente):
                if str(pendiente).strip().lower() not in _MARCAS_VALIDAS:
                    marca_invalida.append(f"{idq}={pendiente!r}")
            elif _vacio(respuesta):
                sin_marca.append(idq)
    finally:
        wb.close()

    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    ev = {"fichero": informe.name, "filas_con_id": len(ids), "preguntas_distintas": len(set(ids)),
          "sin_marcar": len(sin_marca), "marcas_invalidas": marca_invalida[:8],
          "ids_repetidos": repetidos[:8], "ejemplos_sin_marcar": sorted(sin_marca)[:8]}
    if repetidos:
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"{len(repetidos)} identificador(es) de pregunta repetidos: "
                         f"{', '.join(repetidos[:5])}", ev)
    if marca_invalida:
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"{len(marca_invalida)} marca(s) fuera del dominio "
                         f"{sorted(_MARCAS_VALIDAS)}: {', '.join(marca_invalida[:3])}", ev)
    if sin_marca:
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"{len(sin_marca)} de {len(ids)} preguntas sin respuesta ni "
                         "marca de pendiente", ev)
    if len(ids) != filas_esperadas:
        # No es un fallo del expediente: es que la plantilla cambió de cuestionario. Se
        # dice, porque el «88» de todas partes deja de ser cierto en silencio.
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         f"todas marcadas, pero son {len(ids)} preguntas y no "
                         f"{filas_esperadas}: la plantilla cambió", ev)
    return Resultado("viabilidad_completa", titulo, OK,
                     f"las {len(ids)} preguntas de `{informe.name}` con respuesta o "
                     "marca válida", ev)


_RE_WCODE = re.compile(r"\bW-[A-Z0-9]{5,8}\b")
#: El W-code del caso va **entre paréntesis** en el nombre de la carpeta
#: (`<codigo> - <direccion> (<W-code>) - <sufijo>`). Buscar la primera aparición en
#: cualquier posición elegía mal en `Relacionado W-04AAAA - Caso (W-TEST01)`, y el ajeno
#: quedaba exento del barrido (R1 H-09).
_RE_WCODE_PROPIO = re.compile(r"\((W-[A-Z0-9]{5,8})\)")
#: Guiones que la extracción de texto mete en lugar del ASCII: si no se normalizan, un
#: `W‐04AAAA` con U+2010 es invisible para el barrido (R1 H-10).
_GUIONES = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")


def c8_sin_wcodes_ajenos(case_dir: Path) -> Resultado:
    """Cero W-codes de otros expedientes en los espejos `03_MD` (`MEJORAS #235`).

    El barrido de documental ajena mira NOMBRES de fichero, así que un W-code que va
    **dentro** del documento le es invisible. Aquí se mira el texto.

    **Un espejo que no se puede leer es `fallo`, no «ninguno ajeno»** (R1 H-05). La
    primera versión hacía `continue` ante un `OSError` y devolvía «ninguno en 0 espejos»
    en verde: no haber podido mirar se presentaba como prueba de que no había nada. Es
    el falso verde más caro que puede tener un verificador, y estaba en la única línea
    que la cobertura del diff no cubría.
    """
    titulo = "Cero W-codes ajenos en los espejos MD"
    sm = _sala_maquina(case_dir)
    md_dir = _dir_estructural(sm / "03_MD", "03_MD") if sm else None
    if md_dir is None:
        return Resultado("wcodes_ajenos", titulo, PENDIENTE,
                         "no hay `03_MD`: la sala de máquina no ha corrido")
    propio, ambiguo = _wcode_del_caso(case_dir)
    if ambiguo:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"el nombre de la carpeta declara {len(ambiguo)} W-codes entre "
                         f"paréntesis ({', '.join(ambiguo)}): identidad ambigua",
                         {"candidatos": ambiguo})
    if not propio:
        return Resultado("wcodes_ajenos", titulo, PENDIENTE,
                         "no se puede determinar el W-code del caso desde el nombre "
                         "de su carpeta: sin referencia no hay ajeno que valga")

    try:
        espejos = sorted(p for p in md_dir.rglob("*.md") if p.is_file())
    except OSError as exc:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"no se puede listar `03_MD`: {exc!r}")

    ajenos: dict[str, list[str]] = {}
    ilegibles: list[str] = []
    for md in espejos:
        try:
            texto = md.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            ilegibles.append(f"{md.name} ({type(exc).__name__})")
            continue
        for w in sorted(set(_RE_WCODE.findall(_normalizar(texto))) - {propio}):
            ajenos.setdefault(w, []).append(md.name)

    ev = {"propio": propio, "espejos_leidos": len(espejos) - len(ilegibles),
          "ilegibles": ilegibles[:8],
          "ajenos": {w: sorted(f)[:5] for w, f in sorted(ajenos.items())}}
    if ilegibles:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"{len(ilegibles)} espejo(s) que NO se pueden leer: no se "
                         f"puede afirmar que no haya W-codes ajenos ({ilegibles[0]})", ev)
    if ajenos:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"{len(ajenos)} W-code(s) ajeno(s) en {len(espejos)} espejos: "
                         f"{', '.join(sorted(ajenos))}", ev)
    return Resultado("wcodes_ajenos", titulo, OK,
                     f"ninguno en {len(espejos)} espejos", ev)


# --- Las cinco de red ---------------------------------------------------------------
#
# Todas comparten la misma disciplina: preguntan al **contexto** —no al puerto— y
# traducen «no se pudo consultar» a `fallo`. Ninguna aprueba por no haber podido
# preguntar.
#
# **Una sola foto, y por qué importa.** El contexto consulta cada fuente UNA vez y
# reparte el resultado. La primera versión dejaba que C1 y C2 pidieran el censo por
# separado, y la R1 lo midió: con dos respuestas distintas —un fichero aparece en la
# segunda y no en la primera— C1 validaba una foto y C2 declaraba contrastada la otra,
# y el informe salía **9 ok / 0 fallos** sobre un expediente al que le faltaba un
# documento. Un verificador que mira dos veces no está mirando: está promediando.


class _Contexto:
    """Las fuentes, consultadas una vez y repartidas. No decide nada."""

    def __init__(self, case_dir: Path, fuentes: "Fuentes") -> None:
        self.case_dir = Path(case_dir)
        self._f = fuentes
        self._censo: Any = _NO_PEDIDO
        self._exps: dict[tuple[str, str], Any] = {}

    def censo(self):
        if self._censo is _NO_PEDIDO:
            team_id, folder_id = _ids_drive(self.case_dir)
            self._censo = (self._f.censo_drive(team_id, folder_id)
                           if folder_id else _SIN_IDS)
        return self._censo

    def expediente(self, exp_id: str, element: str):
        clave = (exp_id, element)
        if clave not in self._exps:
            self._exps[clave] = self._f.expediente_crm(exp_id, element)
        return self._exps[clave]


_NO_PEDIDO = object()
_SIN_IDS = object()


def _ids_drive(case_dir: Path) -> tuple[str, str]:
    fm, _ = _frontmatter(case_dir)
    meta = fm.get("meta") if isinstance(fm.get("meta"), dict) else {}
    return (str(meta.get("drive_ev_team_id") or ""),
            str(meta.get("drive_ev_folder_id") or ""))


def _expedientes_registrados(case_dir: Path) -> tuple[list[tuple[str, str]], str]:
    """`([(exp_id, element), ...], error)`.

    **Todos**, no el primero. La R1 midió que con dos expedientes registrados —uno
    válido y uno inexistente— las tres comprobaciones del CRM preguntaban tres veces por
    el primero y **ninguna** por el segundo: el informe aprobaba una apertura con un
    expediente fantasma dentro (H-08).

    Una lista corrupta devuelve `error`, no lista vacía: «no se puede leer lo que hay»
    y «no hay nada» son cosas distintas (H-03).
    """
    fm, err = _frontmatter(case_dir)
    if err:
        return [], err
    exps = fm.get("sudespacho_expedientes")
    if exps is None:
        return [], ""
    if not isinstance(exps, list):
        return [], f"`sudespacho_expedientes` no es una lista sino {type(exps).__name__}"
    fuera: list[tuple[str, str]] = []
    malas = 0
    for e in exps:
        if not isinstance(e, dict) or not str(e.get("id") or "").strip():
            malas += 1
            continue
        fuera.append((str(e["id"]).strip(), str(e.get("element") or "").strip()))
    if malas:
        return fuera, (f"{malas} entrada(s) de `sudespacho_expedientes` sin `id` "
                       "utilizable: la lista está corrupta")
    return fuera, ""


#: Lo ÚNICO que el pull deposita en la RAÍZ de `01_Drive EV` y no es documento. La
#: primera versión excluía cuatro nombres a cualquier profundidad y todo lo que
#: empezara por punto — y la R1 midió que así un `.documento.pdf` real, presente en los
#: dos lados, salía como faltante, y que un `sub/.pulled` con contenido ajeno se
#: colaba. El propio productor dice que fuera de la raíz esos nombres pueden ser
#: documentos de E&V (H-06).
_PROTOCOLO_RAIZ = frozenset({".pulled"})


def _locales_de_drive_ev(case_dir: Path) -> tuple[list[str], str]:
    """`(rutas, error)`. Un error NO es una lista vacía."""
    raiz = case_dir / "00_Input" / "01_Drive EV"
    if not raiz.exists():
        return [], ""
    if not raiz.is_dir():
        return [], "`00_Input/01_Drive EV` existe y no es un directorio"
    out: list[str] = []
    try:
        for p in sorted(raiz.rglob("*")):
            rel = p.relative_to(raiz).as_posix()
            if p.is_symlink():
                # Sigue el enlace y podría estar fuera del expediente: `is_file()` y la
                # apertura lo siguen, mientras `relative_to` mira solo el nombre. Un
                # enlace a un fichero de fuera pasaba por copia local (H-05).
                return [], f"`{rel}` es un enlace simbólico: no acredita una copia local"
            if not p.is_file():
                continue
            if rel in _PROTOCOLO_RAIZ:
                continue
            out.append(rel)
    except OSError as exc:
        # `rglob` suprime errores de enumeración: sin este control, un directorio que
        # no se puede recorrer devolvía «cero ficheros» y el censo salía en verde (H-04).
        return [], f"no se puede recorrer `01_Drive EV`: {type(exc).__name__}"
    return out, ""


@_de_red
def c1_censo_remoto(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """Lo que el remoto declara contra lo que hay en `01_Drive EV`.

    `[APER-65]`: en una apertura del 2026-09-10, 11 de 58 ficheros llegaron renombrados
    por el montaje y el pull los re-copió en cada ronda, dejando 7 duplicados. El censo
    independiente es lo que lo destapó, a mano.

    Se comparan **multiconjuntos** y no conjuntos: dos objetos remotos con el mismo
    nombre son dos ficheros, y el `set` de la primera versión los fundía en uno (H-01).
    """
    titulo = "Censo remoto de E&V contra los ficheros locales"
    locales, err = _locales_de_drive_ev(case_dir)
    if err:
        return Resultado("censo_remoto", titulo, FALLO, err)
    raiz = case_dir / "00_Input" / "01_Drive EV"
    if not raiz.exists():
        return Resultado("censo_remoto", titulo, PENDIENTE,
                         "no hay `00_Input/01_Drive EV`: el pull no ha corrido")
    censo = ctx.censo()
    if censo is _SIN_IDS:
        return Resultado("censo_remoto", titulo, PENDIENTE,
                         "`_caso.md` no registra la carpeta de E&V")
    if censo is None:
        return Resultado("censo_remoto", titulo, FALLO,
                         "no se pudo consultar el remoto (token, red o permisos): no "
                         "se puede afirmar que el pull esté completo")
    if not censo.completo:
        return Resultado("censo_remoto", titulo, FALLO,
                         "el remoto declara su propia enumeración INCOMPLETA: el censo "
                         "no sirve para comparar")

    from collections import Counter

    c_remoto, c_local = Counter(f.ruta for f in censo.ficheros), Counter(locales)
    faltan = sorted((c_remoto - c_local).elements())
    sobran = sorted((c_local - c_remoto).elements())
    ev = {"remoto": sum(c_remoto.values()), "local": sum(c_local.values()),
          "faltan_en_local": faltan[:8], "sobran_en_local": sobran[:8]}
    if faltan or sobran:
        return Resultado("censo_remoto", titulo, FALLO,
                         f"{len(faltan)} fichero(s) del remoto que no están en local y "
                         f"{len(sobran)} en local que no están en el remoto", ev)
    return Resultado("censo_remoto", titulo, OK,
                     f"los {sum(c_remoto.values())} ficheros del remoto están en local, "
                     "y ninguno de más", ev)


@_de_red
def c2_hash_contra_drive(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """El sha256 local contra el `sha256Checksum` que declara Drive (`MEJORAS #225`).

    El pull guardaba los documentos **rellenados con ceros** a múltiplo de 512, así que
    su sha256 dejaba de ser el del original. Mismo nombre y mismo tamaño aparente; solo
    el hash los distingue.

    Se cuenta lo **contrastado**, no lo disponible. La primera versión informaba «los N
    ficheros coinciden» usando el número de hashes que el remoto publicaba, de modo que
    con cero ficheros locales decía `ok` sin haber abierto ninguno (H-02).
    """
    titulo = "Hash local contra el sha256Checksum que declara Drive"
    raiz = case_dir / "00_Input" / "01_Drive EV"
    locales, err = _locales_de_drive_ev(case_dir)
    if err:
        return Resultado("hash_drive", titulo, FALLO, err)
    if not raiz.exists():
        return Resultado("hash_drive", titulo, PENDIENTE,
                         "no hay `00_Input/01_Drive EV`: el pull no ha corrido")
    censo = ctx.censo()
    if censo is _SIN_IDS:
        return Resultado("hash_drive", titulo, PENDIENTE,
                         "`_caso.md` no registra la carpeta de E&V")
    if censo is None:
        return Resultado("hash_drive", titulo, FALLO,
                         "no se pudo consultar el remoto: no se puede acreditar "
                         "ningún hash")

    con_hash = {f.ruta: f.sha256 for f in censo.ficheros if f.sha256}
    contrastados, discrepan, ilegibles = 0, [], []
    for rel in locales:
        esperado = con_hash.get(rel)
        if not esperado:
            continue
        try:
            real = _sha256(raiz / rel)
        except OSError as exc:
            ilegibles.append(f"{rel} ({type(exc).__name__})")
            continue
        contrastados += 1
        if real.lower() != esperado.lower():
            discrepan.append(rel)
    sin_contrastar = len(locales) - contrastados - len(ilegibles)
    ev = {"locales": len(locales), "contrastados": contrastados,
          "sin_hash_remoto": sin_contrastar, "discrepan": discrepan[:8],
          "ilegibles": ilegibles[:8]}
    if ilegibles:
        return Resultado("hash_drive", titulo, FALLO,
                         f"{len(ilegibles)} fichero(s) local(es) que no se pueden "
                         f"leer: {ilegibles[0]}", ev)
    if discrepan:
        return Resultado("hash_drive", titulo, FALLO,
                         f"{len(discrepan)} fichero(s) cuyo sha256 NO es el que Drive "
                         f"declara: {', '.join(discrepan[:3])}", ev)
    if contrastados == 0:
        return Resultado("hash_drive", titulo, PENDIENTE,
                         f"ninguno de los {len(locales)} ficheros locales tiene hash "
                         "en Drive con el que contrastar", ev)
    if sin_contrastar:
        return Resultado("hash_drive", titulo, PENDIENTE,
                         f"{contrastados} de {len(locales)} contrastados y coinciden; "
                         f"los otros {sin_contrastar} no tienen hash en Drive y quedan "
                         "SIN comprobar", ev)
    return Resultado("hash_drive", titulo, OK,
                     f"los {contrastados} ficheros contrastados coinciden con el hash "
                     "de Drive", ev)


def _cada_expediente(case_dir: Path, ctx: "_Contexto", ident: str, titulo: str):
    """Resuelve la parte común de C6/C7/C9: los expedientes y sus fichas.

    Devuelve `(fichas, resultado_de_corte)`. Si hay corte, la comprobación lo devuelve
    tal cual: no hay nada que comparar.
    """
    exps, err = _expedientes_registrados(case_dir)
    if err:
        return None, Resultado(ident, titulo, FALLO, err)
    if not exps:
        return None, Resultado(ident, titulo, PENDIENTE,
                               "`_caso.md` no registra ningún expediente del CRM: el "
                               "alta no se ha hecho")
    fichas = []
    for exp_id, element in exps:
        ficha = ctx.expediente(exp_id, element)
        if ficha is None:
            return None, Resultado(ident, titulo, FALLO,
                                   f"no se pudo consultar el CRM para el expediente "
                                   f"{exp_id}: no se puede acreditar nada de él")
        fichas.append((exp_id, element, ficha))
    ausentes = [e for e, _, f in fichas if not f.encontrado]
    if ausentes:
        return None, Resultado(ident, titulo, FALLO,
                               f"el CRM no encuentra {len(ausentes)} expediente(s) que "
                               f"`_caso.md` registra: {', '.join(ausentes)}",
                               {"ausentes": ausentes})
    return fichas, None


@_de_red
def c6_ficha_y_relaciones_crm(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """La ficha del CRM, releída por API — no el status del alta (`MEJORAS #239`).

    `ensure_contrario_vinculado` devolvía «existente» con el id de **otro** deudor que
    compartía correo, y el alta decía OK.

    Se exigen **partes**, no «alguna relación». La primera versión contaba todos los
    bloques, de modo que un expediente con una actuación y **cero partes vinculadas**
    pasaba en verde (H-07) — y una actuación no es una parte: es trabajo.
    """
    titulo = "Ficha y relaciones del CRM, releídas por API"
    fichas, corte = _cada_expediente(case_dir, ctx, "crm_ficha", titulo)
    if corte:
        return corte

    sin_leer, sin_partes, detalle = [], [], {}
    for exp_id, _el, f in fichas:
        partes = f.partes
        if partes is None:
            sin_leer.append(exp_id)
        elif not partes:
            sin_partes.append(exp_id)
        else:
            detalle[exp_id] = partes
    ev = {"expedientes": [e for e, _, _ in fichas], "partes": detalle}
    if sin_leer:
        return Resultado("crm_ficha", titulo, FALLO,
                         f"no se pudieron leer las relaciones de {', '.join(sin_leer)}: "
                         "no se puede afirmar que tengan partes", ev)
    if sin_partes:
        return Resultado("crm_ficha", titulo, FALLO,
                         f"{len(sin_partes)} expediente(s) sin NINGUNA parte vinculada: "
                         f"{', '.join(sin_partes)}", ev)
    total = sum(sum(p.values()) for p in detalle.values())
    return Resultado("crm_ficha", titulo, OK,
                     f"{len(fichas)} expediente(s) con {total} parte(s) vinculada(s)", ev)


@_de_red
def c7_actuacion_asociada(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """Una actuación asociada, leída **por el lado del expediente** (`MEJORAS #209`).

    El matiz del lado no es retórico: preguntar al elemento «actuaciones» por las suyas
    devuelve las del despacho. `actuaciones` es **hijo** de `extrajudiciales` y de
    `expedientes_judiciales` (atlas), así que aparece en `related_register` — y eso sí
    acredita la asociación.
    """
    titulo = "Actuación asociada, por el lado del expediente"
    fichas, corte = _cada_expediente(case_dir, ctx, "crm_actuacion", titulo)
    if corte:
        return corte

    sin_leer, sin_actuacion, cuenta = [], [], {}
    for exp_id, _el, f in fichas:
        act = f.actuaciones
        if act is None:
            sin_leer.append(exp_id)
        elif not act:
            sin_actuacion.append(exp_id)
        else:
            cuenta[exp_id] = len(act)
    ev = {"actuaciones": cuenta}
    if sin_leer:
        return Resultado("crm_actuacion", titulo, FALLO,
                         f"no se pudieron leer las relaciones de {', '.join(sin_leer)}",
                         ev)
    if sin_actuacion:
        return Resultado("crm_actuacion", titulo, FALLO,
                         f"{len(sin_actuacion)} expediente(s) sin ninguna actuación "
                         f"asociada: {', '.join(sin_actuacion)}. La apertura no quedó "
                         "registrada como trabajo", ev)
    return Resultado("crm_actuacion", titulo, OK,
                     f"{sum(cuenta.values())} actuación(es) asociada(s)", ev)


@_de_red
def c9_cuantia_coherente(case_dir: Path, ctx: "_Contexto") -> Resultado:
    """La cuantía de `_caso.md` y la del CRM, dos hogares del mismo hecho.

    `MEJORAS #227`: la cuantía se conoce al leer el encargo, así que el alta va al final
    y el dato llegaba al CRM y no al índice local.

    La conversión es **estricta** (ver `_a_numero`). La permisiva de la primera versión
    dejaba pasar `NaN` como coincidencia —porque `abs(nan - x) > 0.005` es falso— y
    confundía «no hay cuantía» con «la cuantía no se puede leer» (H-09).
    """
    titulo = "Cuantía de `_caso.md` igual a la del CRM"
    fichas, corte = _cada_expediente(case_dir, ctx, "cuantia_coherente", titulo)
    if corte:
        return corte

    fm, err = _frontmatter(case_dir)
    if err:
        return Resultado("cuantia_coherente", titulo, FALLO, err)
    meta = fm.get("meta") if isinstance(fm.get("meta"), dict) else {}
    local_crudo = meta.get("cuantia")
    n_local, err_local = _a_numero(local_crudo)
    if err_local:
        return Resultado("cuantia_coherente", titulo, FALLO,
                         f"la cuantía de `_caso.md` no es un número: {err_local}")

    problemas, ev = [], {"local": n_local, "expedientes": {}}
    for exp_id, _el, f in fichas:
        n_crm, err_crm = _a_numero(f.cuantia)
        ev["expedientes"][exp_id] = {"crm_declarada": f.cuantia not in (None, ""),
                                     "legible": not err_crm}
        if err_crm:
            problemas.append(f"{exp_id}: la cuantía del CRM no es un número ({err_crm})")
        elif n_local is None and n_crm is None:
            continue
        elif n_local is None:
            problemas.append(f"{exp_id}: el CRM tiene cuantía y `_caso.md` dice "
                             "«pendiente». El dato existe y el índice local miente")
        elif n_crm is None:
            problemas.append(f"{exp_id}: `_caso.md` tiene cuantía y el CRM no")
        elif abs(n_local - n_crm) > 0.005:
            # Medio céntimo: el alta mandaba la cuantía como entero y los céntimos se
            # perdían (`MEJORAS #218`); por debajo de eso es el redondeo conocido.
            problemas.append(f"{exp_id}: la cuantía local y la del CRM no coinciden")
    if problemas:
        return Resultado("cuantia_coherente", titulo, FALLO, "; ".join(problemas[:3]), ev)
    if n_local is None:
        return Resultado("cuantia_coherente", titulo, PENDIENTE,
                         "ni `_caso.md` ni el CRM declaran cuantía", ev)
    return Resultado("cuantia_coherente", titulo, OK,
                     "la cuantía local coincide con la del CRM", ev)


def _a_numero(v: Any) -> tuple[float | None, str]:
    """`(numero, error)`. `(None, "")` = ausente. Estricta a propósito.

    Tres cosas que la versión permisiva hacía mal (H-09):

    - `float("NaN")` pasaba, y **cualquier** comparación con NaN es falsa, así que
      `abs(nan - x) > 0.005` daba «coinciden». Un `NaN` en el CRM aprobaba el caso.
    - `1e309` se convierte a infinito y `inf - inf` es NaN: mismo final.
    - Un valor **ilegible** (`'roto'`, `'1.234,56'`) devolvía `None`, igual que la
      ausencia, y el informe decía «ninguno declara cuantía» sobre dos que sí lo hacían.
    """
    import math

    if v is None or (isinstance(v, str) and not v.strip()):
        return None, ""
    if isinstance(v, bool):
        return None, f"{v!r} es un booleano"
    if isinstance(v, (int, float)):
        n = float(v)
    else:
        s = str(v).strip().replace(" ", "")
        # Separador decimal: solo se acepta una forma no ambigua. `1.234,56` y
        # `1,234.56` significan lo mismo con convenciones opuestas, y adivinar cuál usa
        # el emisor es inventarse un dato de dinero.
        if "," in s and "." in s:
            return None, f"{v!r} usa dos separadores: es ambiguo"
        s = s.replace(",", ".")
        try:
            n = float(s)
        except ValueError:
            return None, f"{v!r} no es un número"
    if math.isnan(n) or math.isinf(n):
        return None, f"{v!r} no es un número finito"
    return n, ""


def _sha256(p: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with p.open("rb") as f:
        for trozo in iter(lambda: f.read(1024 * 1024), b""):
            h.update(trozo)
    return h.hexdigest()


def _frontmatter(case_dir: Path) -> tuple[dict, str]:
    """`(frontmatter, error)`. Un error NO es un frontmatter vacío.

    La primera versión devolvía `{}` ante cualquier problema —fichero ilegible, YAML
    roto, raíz que no es un mapa—, así que un `_caso.md` corrupto se leía como «el alta
    no se ha hecho» y las cinco de red salían `pendiente` con exit 0 (H-03). Es la misma
    frontera que la ronda anterior cerró en los lectores locales.
    """
    index = case_dir / "00_Input" / "_caso.md"
    if not index.exists():
        return {}, ""
    if not index.is_file():
        return {}, "`00_Input/_caso.md` existe y no es un fichero"
    try:
        texto = index.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {}, f"`_caso.md` no se puede leer: {type(exc).__name__}"
    if not texto.startswith("---"):
        return {}, "`_caso.md` no empieza por el delimitador del frontmatter"
    try:
        import yaml

        d = yaml.safe_load(texto.split("---", 2)[1])
    except Exception as exc:                               # noqa: BLE001
        return {}, f"el frontmatter de `_caso.md` no es YAML válido ({type(exc).__name__})"
    if d is None:
        return {}, ""
    if not isinstance(d, dict):
        return {}, f"el frontmatter de `_caso.md` no es un mapa sino {type(d).__name__}"
    return d, ""


#: Las nueve, en el orden del diseño. La lista se recorre SIEMPRE entera: un informe que
#: enumera solo lo que sabe mirar es el falso «OK» que esta pieza viene a cerrar.
COMPROBACIONES: tuple[Callable[[Path], Resultado], ...] = (
    c1_censo_remoto,
    c2_hash_contra_drive,
    c3_cobertura_vs_catalogo,
    c4_artefactos_de_la_sala,
    c5_viabilidad_completa,
    c6_ficha_y_relaciones_crm,
    c7_actuacion_asociada,
    c8_sin_wcodes_ajenos,
    c9_cuantia_coherente,
)

#: Los ids de las comprobaciones que SÍ miran el expediente. La guarda de los tests lo
#: usa para exigir que cada una tenga un caso que la ponga en `fallo` — y lo exige
#: EJECUTÁNDOLO, no leyendo el fichero de tests.
IMPLEMENTADAS: tuple[str, ...] = (
    "censo_remoto", "hash_drive", "cobertura_vs_catalogo", "artefactos_sala",
    "viabilidad_completa", "crm_ficha", "crm_actuacion", "wcodes_ajenos",
    "cuantia_coherente")


def verificar(case_dir: Path | str, fuentes: "Fuentes | None" = None) -> Informe:
    """Corre las nueve comprobaciones sobre un expediente. No escribe nada.

    Una comprobación que revienta no tumba el informe: se convierte en `fallo` con la
    excepción como detalle. Un verificador que muere a mitad deja al operador sin las
    ocho que sí podía dar, y sin saber cuál murió.
    """
    case_dir = Path(case_dir)
    # El default es el puerto CERRADO, no uno que consulte: un verificador cuyo modo
    # por defecto fuera «no preguntar y aprobar» sería peor que no tenerlo. Con
    # `SinRed`, las cinco de red salen en `fallo` diciendo que no se pudo consultar.
    if fuentes is None:
        from core.verificar_apertura_fuentes import SinRed

        fuentes = SinRed()
    # UNA consulta por fuente, repartida. Dos comprobaciones que preguntan por separado
    # pueden recibir dos fotos distintas y aprobar entre las dos un expediente al que le
    # falta un documento — medido (R1, H-02).
    ctx = _Contexto(case_dir, fuentes)
    resultados = []
    for fn in COMPROBACIONES:
        try:
            resultados.append(_llamar(fn, case_dir, ctx))
        except _ColisionDeTipo as exc:
            resultados.append(Resultado(
                id=_id_de(fn), titulo=_id_de(fn), estado=FALLO,
                detalle=f"estructura inválida del expediente: {exc}"))
        except Exception as exc:                           # noqa: BLE001
            resultados.append(Resultado(
                id=_id_de(fn), titulo=_id_de(fn), estado=FALLO,
                detalle=f"la comprobación reventó: {exc!r}"))
    return Informe(case_dir=str(case_dir), resultados=resultados)


def _llamar(fn: Callable, case_dir: Path, ctx: "_Contexto") -> Resultado:
    """Las locales toman solo `case_dir`; las de red, también `fuentes`.

    Se decide por una **marca explícita** (`@_de_red`) y no contando parámetros con
    `inspect`. La primera versión contaba, y `c5_viabilidad_completa` tiene un
    keyword-only con default (`filas_esperadas`): recibió el objeto de fuentes en su
    sitio y reventó, lo que el informe presentó como un `fallo` del expediente. Contar
    parámetros es una heurística sobre la forma, igual que buscar una cadena en un
    fichero de tests — y falla igual.
    """
    if getattr(fn, "_necesita_fuentes", False):
        return fn(case_dir, ctx)
    return fn(case_dir)


def _id_de(fn: Callable) -> str:
    """`c3_cobertura_vs_catalogo` -> `cobertura_vs_catalogo`, para que una comprobación
    que revienta conserve su identidad en el informe."""
    nombre = getattr(fn, "__name__", "?")
    return nombre.split("_", 1)[1] if re.match(r"^c\d+_", nombre) else nombre


# --- Lectores, estrictos a propósito ------------------------------------------------


def _vacio(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not str(v).strip())


def _yaml_load(texto: str) -> Any:
    import yaml

    return yaml.safe_load(texto)


def _leer_lista_de_mapas(p: Path, parse: Callable[[str], Any]) -> tuple[list[dict], str]:
    """`(filas, "")` o `([], motivo)`. **Nunca descarta en silencio** (R1 H-01).

    La primera versión filtraba con `[x for x in d if isinstance(x, dict)]`: una lista
    con basura se convertía en una lista más corta —o vacía— y el conteo podía cuadrar
    con el otro lado. Un fichero corrupto salía en verde. Ahora una entrada que no es un
    mapa es una **forma inválida**, y se dice cuántas y cuáles.
    """
    try:
        d = parse(p.read_text(encoding="utf-8"))
    except Exception as exc:                               # noqa: BLE001
        return [], f"ilegible ({type(exc).__name__})"
    if d is None:
        return [], ""
    if not isinstance(d, list):
        return [], f"no es una lista sino {type(d).__name__}"
    malas = [i for i, x in enumerate(d) if not isinstance(x, dict)]
    if malas:
        return [], (f"{len(malas)} de {len(d)} entradas no son mapas "
                    f"(posiciones {malas[:5]}): forma inválida, no se cuenta")
    return list(d), ""


def _ruta_cobertura(case_dir: Path) -> Path | None:
    sm = _sala_maquina(case_dir)
    return (sm / "_cobertura.json") if sm else None


def _normalizar(texto: str) -> str:
    """Mayúsculas, guiones Unicode a ASCII y saltos de línea unidos dentro de un código.

    La extracción de texto de un PDF parte identificadores por maquetación: un
    `W-\\n04AAAA` es el mismo W-code y era invisible (R1 H-10).
    """
    t = unicodedata.normalize("NFC", texto).upper().translate(_GUIONES)
    return re.sub(r"(W-)[\s ]+(?=[A-Z0-9])", r"\1", t)


def _wcode_del_caso(case_dir: Path) -> tuple[str | None, list[str]]:
    """`(w_code, [])`, o `(None, candidatos)` si el nombre declara más de uno.

    Se toma el que va **entre paréntesis**, que es donde lo pone el compositor del
    `case_id`. Si no hay ninguno entre paréntesis, se admite uno suelto — pero solo si
    es el único del nombre: elegir entre varios por posición es adivinar (R1 H-09).
    """
    nombre = _normalizar(case_dir.name)
    entre_parentesis = _RE_WCODE_PROPIO.findall(nombre)
    if len(entre_parentesis) == 1:
        return entre_parentesis[0], []
    if len(entre_parentesis) > 1:
        return None, sorted(set(entre_parentesis))
    sueltos = sorted(set(_RE_WCODE.findall(nombre)))
    if len(sueltos) == 1:
        return sueltos[0], []
    return None, sueltos if len(sueltos) > 1 else []
