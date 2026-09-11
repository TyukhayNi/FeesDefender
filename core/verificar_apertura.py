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

## Los cuatro estados, y por qué son cuatro y no tres

`ok` · `pendiente` · `fallo` son los del diseño. `pendiente` **no** es `fallo`: un
expediente a medias tiene que poder verificarse sin que el informe grite — si «aún no
hay sala de lectura» saliera en rojo, el rojo dejaría de significar algo.

El cuarto, `sin_implementar`, lo añadió la construcción y es deliberado. Cinco de las
nueve comprobaciones necesitan red (rclone o el CRM) y no se han construido en esta
entrega. Podrían haberse dejado fuera de la lista, y entonces el informe diría «9 de 9
correctas» habiendo mirado 4 — que es **exactamente el modo de fallo que esta pieza
existe para cerrar**, cometido por la pieza misma. Así que las nueve se enumeran siempre,
y el resumen dice cuántas se han comprobado de verdad.

Y por eso `sin_implementar` no cuenta como verificación: un instrumento que solo puede
devolver un valor no mide nada.
"""
from __future__ import annotations

import dataclasses
import json
import re
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


def _sala_maquina(case_dir: Path) -> Path:
    return case_dir / _PROCESADO / _SALA_MAQUINA


def _sala_lectura(case_dir: Path) -> Path:
    return case_dir / _PROCESADO / _SALA_LECTURA


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


def c3_cobertura_vs_catalogo(case_dir: Path) -> Resultado:
    """Filas de `_cobertura.json` menos hijos de bundle = entradas del catálogo.

    `[APER-60]`, con la corrección del 102º: los **hijos de bundle** no son entradas del
    catálogo —el catálogo indexa documentos lógicos— así que restarlos es lo que hace
    comparable a los dos lados. Sin esa resta, un caso con un solo PDF segmentado en
    veinte piezas parecería tener veinte documentos sin catalogar.
    """
    titulo = "Cobertura de la sala de máquina contra el catálogo documental"
    cob_path = _sala_maquina(case_dir) / "_cobertura.json"
    cat_path = case_dir / _PROCESADO / _CATALOGO
    if not cob_path.is_file():
        return Resultado("cobertura_vs_catalogo", titulo, PENDIENTE,
                         "no hay `_cobertura.json`: la sala de máquina no ha corrido")
    if not cat_path.is_file():
        return Resultado("cobertura_vs_catalogo", titulo, PENDIENTE,
                         "no hay catálogo: la sala de lectura no se ha montado")

    filas = _leer_json_lista(cob_path)
    if filas is None:
        return Resultado("cobertura_vs_catalogo", titulo, FALLO,
                         f"`{cob_path.name}` ilegible o con otra forma")
    entradas = _leer_yaml_lista(cat_path)
    if entradas is None:
        return Resultado("cobertura_vs_catalogo", titulo, FALLO,
                         f"`{cat_path.name}` ilegible o con otra forma")

    logicos = [f for f in filas if not str(f.get("parent_slug") or "").strip()]
    ev = {"filas_cobertura": len(filas), "hijos_de_bundle": len(filas) - len(logicos),
          "documentos_logicos": len(logicos), "entradas_catalogo": len(entradas)}
    if len(logicos) == len(entradas):
        return Resultado("cobertura_vs_catalogo", titulo, OK,
                         f"{len(logicos)} documentos lógicos y {len(entradas)} "
                         "entradas del catálogo", ev)
    return Resultado(
        "cobertura_vs_catalogo", titulo, FALLO,
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
    sala = _sala_lectura(case_dir)
    if not sala.is_dir():
        return Resultado("artefactos_sala", titulo, PENDIENTE,
                         "no hay `Sala lectura`: no se ha montado")
    # El catálogo vive en `01_Procesado/`, no dentro de la sala.
    ubicacion = {n: (case_dir / _PROCESADO / n if n == _CATALOGO else sala / n)
                 for n in _ARTEFACTOS_SALA}
    faltan = sorted(n for n, p in ubicacion.items() if not p.is_file())
    vacios = sorted(n for n, p in ubicacion.items()
                    if p.is_file() and p.stat().st_size == 0)
    ev = {"presentes": sorted(set(_ARTEFACTOS_SALA) - set(faltan)),
          "faltan": faltan, "vacios": vacios}
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


def c5_viabilidad_completa(case_dir: Path, *, filas_esperadas: int = 88) -> Resultado:
    """Las 88 preguntas con respuesta **o** marca de pendiente.

    Es el defecto que cerró la pieza P5, mirado desde fuera: el generador podía dejar
    filas en blanco y decir «OK». Aquí se cuenta la columna, que es lo que el letrado
    tuvo que hacer a mano el 2026-09-10.
    """
    titulo = "Las 88 filas del informe de viabilidad, marcadas"
    analisis = case_dir / "02_Analisis"
    informes = sorted(analisis.glob("Informe viabilidad*.xlsx")) if analisis.is_dir() else []
    if not informes:
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         "no hay informe de viabilidad en `02_Analisis`")
    try:
        import openpyxl
    except ImportError:                                    # pragma: no cover
        return Resultado("viabilidad_completa", titulo, SIN_IMPLEMENTAR,
                         "no construida aquí: falta openpyxl en este entorno")

    # El más reciente: una apertura puede dejar el del pre-relleno y el firmado.
    informe = max(informes, key=lambda p: p.stat().st_mtime)
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
        con_id, sin_marca = 0, []
        for fila in ws.iter_rows(min_row=5, max_col=13):
            idq = fila[2].value if len(fila) > 2 else None      # C
            if not idq:
                continue
            con_id += 1
            respuesta = fila[8].value if len(fila) > 8 else None   # I
            pendiente = fila[12].value if len(fila) > 12 else None  # M
            if _vacio(pendiente) and _vacio(respuesta):
                sin_marca.append(str(idq).strip())
    finally:
        wb.close()

    ev = {"fichero": informe.name, "preguntas": con_id,
          "sin_marcar": len(sin_marca), "ejemplos": sorted(sin_marca)[:8]}
    if sin_marca:
        return Resultado("viabilidad_completa", titulo, FALLO,
                         f"{len(sin_marca)} de {con_id} preguntas sin respuesta ni "
                         "marca de pendiente", ev)
    if con_id != filas_esperadas:
        # No es un fallo del expediente: es que la plantilla cambió de cuestionario. Se
        # dice, porque el «88» de todas partes deja de ser cierto en silencio.
        return Resultado("viabilidad_completa", titulo, PENDIENTE,
                         f"todas marcadas, pero son {con_id} preguntas y no "
                         f"{filas_esperadas}: la plantilla cambió", ev)
    return Resultado("viabilidad_completa", titulo, OK,
                     f"las {con_id} preguntas con respuesta o marca", ev)


def c6_ficha_y_relaciones_crm(case_dir: Path) -> Resultado:
    return _sin_red("crm_ficha", "Ficha y relaciones del CRM, releídas por API",
                    "necesita el CRM (`MEJORAS #239`)")


def c7_actuacion_asociada(case_dir: Path) -> Resultado:
    return _sin_red("crm_actuacion", "Actuación asociada, por el lado del expediente",
                    "necesita el CRM (`MEJORAS #209`)")


_RE_WCODE = re.compile(r"\bW-[A-Z0-9]{5,8}\b")


def c8_sin_wcodes_ajenos(case_dir: Path) -> Resultado:
    """Cero W-codes de otros expedientes en los espejos `03_MD` (`MEJORAS #235`).

    El barrido de documental ajena mira NOMBRES de fichero, así que un W-code que va
    **dentro** del documento le es invisible. Aquí se mira el texto, que es donde el
    documento dice de sí mismo a qué caso pertenece.

    El W-code propio sale del nombre de la carpeta del caso: si no se puede determinar,
    la comprobación queda `pendiente` en vez de comparar contra nada — un barrido sin
    referencia diría «todos ajenos».
    """
    titulo = "Cero W-codes ajenos en los espejos MD"
    propio = _wcode_del_caso(case_dir)
    md_dir = _sala_maquina(case_dir) / "03_MD"
    if not md_dir.is_dir():
        return Resultado("wcodes_ajenos", titulo, PENDIENTE,
                         "no hay `03_MD`: la sala de máquina no ha corrido")
    if not propio:
        return Resultado("wcodes_ajenos", titulo, PENDIENTE,
                         "no se puede determinar el W-code del caso desde el nombre "
                         "de su carpeta: sin referencia no hay ajeno que valga")

    ajenos: dict[str, list[str]] = {}
    leidos = 0
    for md in sorted(md_dir.glob("*.md")):
        try:
            texto = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        leidos += 1
        for w in sorted(set(_RE_WCODE.findall(texto.upper())) - {propio}):
            ajenos.setdefault(w, []).append(md.name)

    ev = {"propio": propio, "espejos_leidos": leidos,
          "ajenos": {w: sorted(f)[:5] for w, f in sorted(ajenos.items())}}
    if ajenos:
        return Resultado("wcodes_ajenos", titulo, FALLO,
                         f"{len(ajenos)} W-code(s) ajeno(s) en {leidos} espejos: "
                         f"{', '.join(sorted(ajenos))}", ev)
    return Resultado("wcodes_ajenos", titulo, OK,
                     f"ninguno en {leidos} espejos", ev)


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
        except Exception as exc:                           # noqa: BLE001
            resultados.append(Resultado(
                id=getattr(fn, "__name__", "?"), titulo=getattr(fn, "__name__", "?"),
                estado=FALLO, detalle=f"la comprobación reventó: {exc!r}"))
    return Informe(case_dir=str(case_dir), resultados=resultados)


# --- Lectores tolerantes ------------------------------------------------------------


def _vacio(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _leer_json_lista(p: Path) -> list[dict] | None:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    # Deliberadamente SIN tolerancia a volcados envueltos en una clave (`{"cobertura":
    # [...]}`): no se ha visto ninguno, y una rama que nadie ha visto es una rama que
    # nadie prueba. Si aparece, se añade con el volcado real que la motive delante.
    return [x for x in d if isinstance(x, dict)] if isinstance(d, list) else None


def _leer_yaml_lista(p: Path) -> list[dict] | None:
    import yaml

    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError, UnicodeDecodeError):
        return None
    if d is None:
        return []
    return [x for x in d if isinstance(x, dict)] if isinstance(d, list) else None


def _wcode_del_caso(case_dir: Path) -> str | None:
    """El W-code del `case_id`, que va entre paréntesis en el nombre de la carpeta."""
    m = _RE_WCODE.search(case_dir.name.upper())
    return m.group(0) if m else None
