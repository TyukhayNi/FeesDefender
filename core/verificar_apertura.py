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
from typing import Any, Callable

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


# --- Las comprobaciones -------------------------------------------------------------


def _sin_red(id_: str, titulo: str, motivo: str) -> Resultado:
    return Resultado(id=id_, titulo=titulo, estado=SIN_IMPLEMENTAR,
                     detalle=f"no construida en esta entrega: {motivo}")


def c1_censo_remoto(case_dir: Path) -> Resultado:
    return _sin_red("censo_remoto", "Censo remoto contra local (01_Drive EV)",
                    "necesita `rclone lsf` contra el Drive de E&V")


def c2_hash_contra_drive(case_dir: Path) -> Resultado:
    return _sin_red("hash_drive", "Hash local contra el sha256Checksum de Drive",
                    "necesita la Drive API (`MEJORAS #225`)")


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


def c6_ficha_y_relaciones_crm(case_dir: Path) -> Resultado:
    return _sin_red("crm_ficha", "Ficha y relaciones del CRM, releídas por API",
                    "necesita el CRM (`MEJORAS #239`)")


def c7_actuacion_asociada(case_dir: Path) -> Resultado:
    return _sin_red("crm_actuacion", "Actuación asociada, por el lado del expediente",
                    "necesita el CRM (`MEJORAS #209`)")


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


def c9_cuantia_coherente(case_dir: Path) -> Resultado:
    return _sin_red("cuantia_coherente", "Cuantía de `_caso.md` igual a la del CRM",
                    "necesita el CRM (`MEJORAS #227`)")


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
IMPLEMENTADAS: tuple[str, ...] = ("cobertura_vs_catalogo", "artefactos_sala",
                                  "viabilidad_completa", "wcodes_ajenos")


def verificar(case_dir: Path | str) -> Informe:
    """Corre las nueve comprobaciones sobre un expediente. No escribe nada.

    Una comprobación que revienta no tumba el informe: se convierte en `fallo` con la
    excepción como detalle. Un verificador que muere a mitad deja al operador sin las
    ocho que sí podía dar, y sin saber cuál murió.
    """
    case_dir = Path(case_dir)
    resultados = []
    for fn in COMPROBACIONES:
        try:
            resultados.append(fn(case_dir))
        except _ColisionDeTipo as exc:
            resultados.append(Resultado(
                id=_id_de(fn), titulo=_id_de(fn), estado=FALLO,
                detalle=f"estructura inválida del expediente: {exc}"))
        except Exception as exc:                           # noqa: BLE001
            resultados.append(Resultado(
                id=_id_de(fn), titulo=_id_de(fn), estado=FALLO,
                detalle=f"la comprobación reventó: {exc!r}"))
    return Informe(case_dir=str(case_dir), resultados=resultados)


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
