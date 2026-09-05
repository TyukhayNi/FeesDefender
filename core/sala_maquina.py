"""Cerebro + orquestador de la Sala de máquina (skill organizar-sala-maquina).

Convierte el crudo de 00_Input/ en 01_Procesado/02_Sala de máquina/:
  01_OCR/     PDFs buscables (OCRmyPDF)   03_MD/  markdown legible   raw_text/  intermedio

NO usa pipeline.run() ni la rama Docling/30pp de extractor. OCR aguas arriba con
OCRmyPDF (sin tope de páginas); reutiliza solo los helpers deterministas sanos del
extractor. Ver docs/superpowers/specs/2026-07-09-organizar-sala-maquina-design.md.
"""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

from core.extractor import (
    _try_pypdf, _pdf_num_paginas, _texto_suficiente,
    _try_email, _try_rtf, _try_ics, _try_pandas_table, _try_docx, _read_text_file,
)
from core.anon.ocr import ocr_pdf_escalera
from core.anon.imagen_a_pdf import convertir as convertir_imagen
from core.ofimatica_a_pdf import (
    EXTS_OFIMATICA, ConversionFallida, ConversorNoDisponible,
    convertir as convertir_ofimatica,
)
from core import pdf_paginas
from core.utils import file_sha256, now_iso, output_slug, text_sha256, write_md
from core import split_documental as split
from core.intake_log import append_event
from core import config

_EXTS_IMAGEN = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".heif", ".webp", ".bmp", ".gif"}
_EXTS_NATIVO = {".eml", ".txt", ".md", ".rtf", ".ics", ".csv", ".xlsx", ".xls", ".docx", ".html", ".htm"}


#: Rutas cuyo producto es un PDF buscable que `_split_o_md` puede segmentar en bundle. Es la
#: lista que consulta `preflight_manifiestos`: una ruta nueva que segmente y no esté aquí
#: elude la validación de identidad/edición de su manifiesto (R1/H-01 de la acción 10).
_RUTAS_CON_BUNDLE = ("pdf", "imagen", "ofimatica")


def clasificar_ruta(ext: str) -> str:
    """Enruta por extensión: 'pdf' | 'imagen' | 'nativo' | 'ofimatica' | 'sin_soporte'.

    `ofimatica` (`.doc`, `.odt`, `.ppt`, …; `MEJORAS #61`) se convierte a PDF con
    LibreOffice y sigue por el camino PDF. `.docx`/`.rtf` NO: ya tienen extractor
    determinista propio en `nativo`, y cambiarles la ruta cambiaría el MD de casos hechos.
    """
    e = ext.lower()
    if e == ".pdf":
        return "pdf"
    if e in _EXTS_IMAGEN:
        return "imagen"
    if e in _EXTS_NATIVO:
        return "nativo"
    if e in EXTS_OFIMATICA:
        return "ofimatica"
    return "sin_soporte"


_MAGIC_BYTES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", ".pdf"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
)


def _sniff_ext_por_contenido(head: bytes) -> str | None:
    """Detecta la extensión real por firma mágica de bytes.

    Último recurso en inventariar() cuando el nombre no trae extensión
    reconocible (típico de capturas/fotos compartidas directo a Drive sin
    "Guardar como" — confirmado 2026-07-17, caso W-02TH0W: 'Señal 3000 €' y
    'DNI ... jpg' sin punto): el fichero es perfectamente legible, solo mal
    nombrado. Nunca lanza — None si no reconoce ninguna firma.
    """
    for magic, ext in _MAGIC_BYTES:
        if head.startswith(magic):
            return ext
    return None


_MIN_CHARS = 40                 # < esto para el documento entero = empty
_MIN_DENSIDAD = 40              # char/pág mínima (alineado con extractor._texto_suficiente)
_MAX_GIBBERISH = 0.40           # > 40% de tokens sin vocal = OCR ruidoso
_TOKEN_RE = re.compile(r"[^\W\d_]{2,}", re.UNICODE)   # tokens alfabéticos (incl. tildes/cirílico)
_VOCALES = set("aeiouáéíóúàèìòùüïAEIOUÁÉÍÓÚÀÈÌÒÙÜÏаэеёиоуыюяАЭЕЁИОУЫЮЯ")


def _ratio_gibberish(text: str) -> float:
    """Fracción de tokens alfabéticos (≥2 letras) que NO tienen ninguna vocal.

    Un OCR ruidoso produce tiras consonánticas ('xkq', 'brrr'); las palabras
    reales en spa/cat/rus casi siempre llevan vocal. 0.0 si no hay tokens.
    """
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return 1.0
    sin_vocal = sum(1 for t in tokens if not (set(t) & _VOCALES))
    return sin_vocal / len(tokens)


def ocr_quality(text: str, n_pags: int | None) -> tuple[str, str]:
    """Estado de calidad del texto extraído: ('ok'|'low'|'empty', motivo).

    Tres señales (spec §5.2): densidad char/pág, ratio de gibberish, léxico.
    No aborta: solo clasifica para la worklist de revisión humana.
    """
    t = (text or "").strip()
    if len(t) < _MIN_CHARS:
        return "empty", "sin texto o residual"
    gib = _ratio_gibberish(t)
    if gib > _MAX_GIBBERISH:
        return "low", f"gibberish {gib:.0%} (OCR ruidoso o idioma no soportado)"
    if n_pags and n_pags > 0 and (len(t) / n_pags) < _MIN_DENSIDAD:
        return "low", f"densidad baja ({len(t) // max(n_pags,1)} char/pág)"
    return "ok", ""


_MIN_PAGS_PERDIDAS = 2        # nº de páginas escaneadas mudas que ya obliga a revisar
_RATIO_PAGS_PERDIDAS = 0.5    # …o que sean al menos la mitad del documento


def calidad_por_pagina(perfil: list[pdf_paginas.PaginaPerfil]) -> tuple[str, str]:
    """Señal POR PÁGINA que rompe la dilución del promedio (`MEJORAS #90` (b)).

    `ocr_quality` promedia sobre el documento: 4 escaneos que no dieron ni un
    carácter se diluyen entre 36 páginas digitales densas y el documento sale
    `ok` — fuera de la worklist y fuera del filtro de `reforzar`.

    **Página perdida** = ráster a página completa Y menos texto del que exige la
    densidad mínima. Los dos términos importan: sin el ráster marcaríamos los
    reversos en blanco de un dúplex, que son legítimos; sin el umbral de texto
    marcaríamos cualquier escaneo bien OCR-izado.

    Devuelve ``("", "")`` cuando no hay señal — el llamador conserva entonces el
    veredicto de `ocr_quality`. Nunca sube la calidad: solo puede degradarla.
    """
    n = len(perfil)
    if n < 2:
        # Una sola página con ráster es el camino `imagen` (jpg → pdf → OCR): un
        # DNI o una captura. Marcarlo inundaría la worklist de falsos positivos,
        # los mismos que hubo que descartar al medir el cribado del detector.
        return "", ""
    perdidas = [p.numero for p in perfil
                if p.raster_px >= pdf_paginas.MIN_PX_RASTER and p.chars < _MIN_DENSIDAD]
    if not perdidas:
        return "", ""
    if len(perdidas) < _MIN_PAGS_PERDIDAS and (len(perdidas) / n) < _RATIO_PAGS_PERDIDAS:
        return "", ""
    pags = ", ".join(str(i) for i in perdidas[:12]) + ("…" if len(perdidas) > 12 else "")
    return "low", (f"{len(perdidas)} de {n} páginas escaneadas sin texto "
                   f"(págs. {pags}): revisar o reforzar")


_EXCLUIR_PREFIJOS = ("90_Notas personales/", "90_Notas personales\\")


@dataclass
class DocPlan:
    rel_path: str
    sha256: str
    ext: str
    ruta: str            # pdf | imagen | nativo | ofimatica | sin_soporte
    slug: str            # output_slug (slug__sha8)
    skip: bool = False
    #: `rel_path` del PRIMER fichero del inventario con el mismo `sha256` (MEJORAS #147, vía A):
    #: este es una copia byte-idéntica en otra carpeta. Se le da fila de custodia propia pero
    #: NO se procesa ni se le escribe espejo: el espejo único es el del primero.
    duplicado_de: str = ""


@dataclass
class DocCobertura:
    slug: str
    rel_path: str
    metodo: str          # pypdf | ocr | nativo | ofimatica | sin_soporte | error
    estado: str          # ok | low | empty | sin_soporte
    chars: int = 0
    ocr: bool = False
    nota: str = ""
    sha256: str = ""     # sha del origen: cadena de custodia (spec §7/§10) + estado idempotente
    parent_slug: str = ""    # slug del bundle si es un segmento (split); vacío si documento suelto
    parent_sha256: str = ""  # sha del fichero FÍSICO de origen; clave del estado idempotente por bundle
    role: str = "documento"  # role_in_bundle (documento | anexo | ...)
    paginas: str = ""        # rango de páginas en el bundle ("1-4"); vacío si no aplica
    tipo: str = ""           # tipo clasificado del documento lógico
    doc_id: str = ""         # identidad persistente del segmento; vacío = documento suelto
    #: Solo en filas `duplicado` (MEJORAS #147, vía A): slug del titular cuyo espejo sirve a
    #: esta copia (el del bundle si el titular se segmentó). Referencia ESTRUCTURADA, no
    #: texto en la nota: los consumidores que convierten filas en espejos la resuelven.
    alias_de: str = ""


#: Veces que se reintenta un documento que no se resuelve antes de dejarlo en paz.
#: Hasta el 2026-08-04 no había tope: el estado guardaba solo los ÉXITOS, así que un
#: documento que falla volvía a pagar OCR real en cada `apply`, indefinidamente
#: (~169 documentos en W-02VND1 — `MEJORAS #84`).
#:
#: Son 3 y no 2 a propósito. El tope tiene un footgun: si falta el motor de OCR
#: (`MEJORAS #91`: `apply` no lo comprueba antes de una corrida larga) fallan TODOS los
#: documentos y agotan TODOS el contador, y desde ahí el caso se procesaría «en verde»
#: saltándose el expediente entero. El margen extra, el recuento de agotados que `apply`
#: imprime en cada corrida y la vía de escape de `--force`/`--solo` son las tres
#: mitigaciones; el arreglo de fondo es el preflight del motor, que sigue pendiente.
MAX_INTENTOS = 3


def plan(inventario: list[dict], estado_previo: set[str],
         agotados: frozenset[str] = frozenset(), *,
         productores_previos: frozenset[str] = frozenset()) -> list[DocPlan]:
    """Puro: enruta cada fichero y marca skip si su sha ya fue procesado.

    Excluye 90_Notas personales/ (zona del abogado, invariante del proyecto).

    `agotados`: sha de documentos que ya gastaron :data:`MAX_INTENTOS` sin resolverse.
    Se saltan igual que los hechos, pero por un motivo distinto — el llamador es quien
    lo distingue y lo declara, porque saltarse algo en silencio es el defecto que este
    tope podría introducir si nadie lo cuenta.
    """
    out: list[DocPlan] = []
    for f in inventario:
        rel = f["rel_path"]
        if rel.startswith(_EXCLUIR_PREFIJOS):
            continue
        sha = f["sha256"]
        out.append(DocPlan(
            rel_path=rel,
            sha256=sha,
            ext=f["ext"],
            ruta=clasificar_ruta(f["ext"]),
            slug=output_slug(rel, sha),
            skip=sha in estado_previo or sha in agotados,
        ))
    _marcar_duplicados(out, productores_previos)
    return out


def _marcar_duplicados(docs: list[DocPlan], productores_previos: frozenset[str]) -> None:
    """MEJORAS #147, vía A: el mismo fichero (mismos bytes) en dos carpetas del cliente.

    Medido en W-02Q38C —`Certificado titularidad…` en `ARRAS/` y en `OFERTAS/…`—: dos OCR,
    dos espejos y el mismo hecho contado dos veces en el corpus que lee el LLM. Por cada
    `sha256` hay UN titular del espejo y los demás son procedencias (`duplicado_de`).

    Quién es el titular, en este orden (R1 de Codex, H-01 y H-06):
    1. **Quien ya tiene espejo lo conserva.** Toda procedencia que en la cobertura previa fue
       productora (`productores_previos`) sigue siéndolo: la titularidad es DURABLE y no la
       cambia una carpeta nueva que ordene antes. Dos productoras legadas (materializadas
       antes de esta regla) siguen siendo dos: no se retira una generación existente.
    2. Si nadie tiene espejo, el titular es la primera procedencia con una ruta que sabe
       extraer (`ruta != sin_soporte`): mismos bytes no es misma capacidad de extracción —un
       DOCX guardado sin extensión es `sin_soporte`, su copia `.docx` es `nativo`.
    3. Si ninguna sabe, el primero por ruta (orden `sorted`, determinista).
    """
    por_sha: dict[str, list[DocPlan]] = {}
    for d in docs:
        por_sha.setdefault(d.sha256, []).append(d)
    for grupo in por_sha.values():
        if len(grupo) < 2:
            continue
        productoras = [d for d in grupo if d.rel_path in productores_previos]
        if productoras:
            titular = productoras[0]
            fijas = {d.rel_path for d in productoras}
        else:
            titular = next((d for d in grupo if d.ruta != "sin_soporte"), grupo[0])
            fijas = {titular.rel_path}
        for d in grupo:
            if d.rel_path not in fijas:
                d.duplicado_de = titular.rel_path


NOTA_RECONSTRUIDA = "fila reconstruida del MD (sin _cobertura.json)"


def _frontmatter_md(md: Path) -> dict:
    """Frontmatter del MD **sin cargar el cuerpo**, que puede pesar cientos de KB.

    Mismo motivo que `detectar_ocr_ciego._frontmatter`: reconstruir el registro de un
    caso entero son ~170 ficheros, y sobre Drive el cuerpo es I/O que no se necesita.
    """
    import yaml

    lineas: list[str] = []
    with md.open("r", encoding="utf-8", errors="replace") as fh:
        if fh.readline().strip() != "---":
            return {}
        for linea in fh:
            if linea.strip() == "---":
                break
            lineas.append(linea)
    try:
        return yaml.safe_load("".join(lineas)) or {}
    except yaml.YAMLError:
        return {}


def reconstruir_cobertura_desde_md(sm_dir: Path) -> list[DocCobertura]:
    """Cobertura reconstruida del frontmatter de `03_MD/`, para casos sin `_cobertura.json`.

    Los casos procesados antes de que existiera ese fichero (#84) solo tienen la vista
    `_cobertura.md`, que `_escribir_cobertura_md` REESCRIBE en cada corrida. Sin esto,
    una corrida incremental fusiona contra vacío y reduce el registro al delta: en
    W-02XOR7 eran 169 filas → 2, en silencio (medido el 2026-07-30 ejecutando D1).

    La reconstrucción es honesta, no completa: `_escribir_md` persiste `source_path`,
    `extractor`, `chars`, `ocr` y `ocr_quality`, pero **no** el `sha256` del origen ni
    los campos de bundle (`parent_*`, `role`, `paginas`). Esas filas salen con sha vacío
    y `nota` que lo declara — preservar el registro no es inventar lo que no está. Una
    corrida `--force` posterior las sustituye por filas completas.
    """
    md_dir = sm_dir / "03_MD"
    if not md_dir.is_dir():
        return []
    out: list[DocCobertura] = []
    for md in sorted(md_dir.glob("*.md")):
        meta = _frontmatter_md(md)
        rel = meta.get("source_path")
        if not rel:
            continue                      # sin origen no hay fila de custodia que valga
        out.append(DocCobertura(
            slug=md.stem,
            rel_path=str(rel),
            metodo=str(meta.get("extractor", "")),
            estado=str(meta.get("ocr_quality", "")),
            chars=int(meta.get("chars") or 0),
            ocr=bool(meta.get("ocr")),
            nota=NOTA_RECONSTRUIDA,
        ))
    return out


def _norm_rel(rel: str) -> str:
    """`rel_path` comparable: el informe del detector y el shell de Windows dan `\\`."""
    return rel.replace("\\", "/")


def acotar_plan(plan: list[DocPlan], solo: list[str]) -> list[DocPlan]:
    """Acota la corrida a `solo` (rutas relativas de `00_Input`) forzando su reproceso.

    Es el «force acotado» que pide D1 (`MEJORAS #90`): los documentos pedidos entran
    aunque su sha ya esté en el estado, y **todo lo demás se marca `skip`**. Así el
    llamador conserva la semántica INCREMENTAL de cobertura y estado (fusionar / unir),
    que es la correcta aquí: un acotado no es autoritativo sobre el caso entero.

    Un `solo` que no case con ningún `rel_path` es un error, no una corrida vacía: sin
    esto, una errata en una de las 17 rutas daría «0 documentos» y se leería como «ya
    estaba todo bien» (el patrón del bug de W-02ZIIF).
    """
    if not solo:
        return plan
    pedidos = {_norm_rel(s) for s in solo}
    encontrados: set[str] = set()
    out: list[DocPlan] = []
    for d in plan:
        rel = _norm_rel(d.rel_path)
        if rel in pedidos:
            encontrados.add(rel)
            out.append(replace(d, skip=False))
        else:
            out.append(replace(d, skip=True))
    if faltan := sorted(pedidos - encontrados):
        raise ValueError(
            "rutas de --solo que no existen en el inventario de 00_Input: "
            + ", ".join(faltan))
    return out


def _celda(valor: str) -> str:
    """Sanea '|' para que no rompa el nº de columnas de una fila Markdown.

    Se sustituye por '/' en vez de escapar con '\\|': el escape depende de que
    el renderer de tablas Markdown lo respete, y cualquier parseo naive por
    '|' (incl. el de este propio módulo si algo relee `_cobertura.md`) seguiría
    contando una columna de más.
    """
    return str(valor).replace("|", "/")


def render_cobertura(cobertura: list[DocCobertura]) -> str:
    """Puro: Markdown de _cobertura.md. Dudosos (estado != ok) primero."""
    orden = {"empty": 0, "sin_soporte": 1, "low": 2, "ok": 3}
    filas = sorted(cobertura, key=lambda d: (orden.get(d.estado, 0), d.slug))
    lineas = [
        "<!-- GENERADO — NO EDITAR A MANO -->",
        "# Cobertura de la Sala de máquina",
        "",
        "| documento | origen | tipo | páginas | parent | método | estado | chars | ocr | nota |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for d in filas:
        lineas.append(
            f"| {_celda(d.slug)} | {_celda(d.rel_path)} | {_celda(d.tipo)} | {_celda(d.paginas)} | "
            f"{_celda(d.parent_slug)} | {d.metodo} | {d.estado} | {d.chars} | "
            f"{'sí' if d.ocr else '—'} | {_celda(d.nota)} |"
        )
    dudosos = [d for d in filas if d.estado != "ok"]
    lineas += ["", f"**{len(dudosos)} de {len(filas)} documentos requieren tu revisión.**", ""]
    return "\n".join(lineas) + "\n"


def _clave_cobertura(d: DocCobertura) -> tuple[str, str]:
    """Identidad de una fila de cobertura: `doc_id` si es segmento, `slug` si es suelto.

    El slug de un segmento cambia cuando cambia su TIPO (y cambiaba, antes, con sus
    bytes), así que indexar por slug dejaba DOS filas del mismo documento lógico. El
    documento suelto no tiene doc_id y conserva la clave de siempre.
    """
    return (d.rel_path, d.doc_id) if d.doc_id else (d.rel_path, d.slug)


def fusionar_cobertura(previa: list[DocCobertura], nueva: list[DocCobertura],
                       rel_paths_reprocesados: set[str] | None = None) -> list[DocCobertura]:
    """Une la cobertura previa con la de esta corrida: la nueva gana por identidad.

    Simétrico con el estado idempotente (`previo | nuevo`), pero conservando el
    registro COMPLETO en vez de solo el conjunto de shas: una corrida incremental
    procesa solo el delta, así que sin esta fusión `_cobertura.md` perdería las
    filas de las corridas anteriores (el bug de VALERO). Orden estable: las
    previas en su orden (con la versión nueva si se re-tocó ese documento), luego
    las nuevas no vistas.

    La clave la fija `_clave_cobertura` y cubre tres cosas: (a) dos ficheros
    byte-idénticos con el mismo nombre en carpetas distintas (mismo `slug`, porque
    `output_slug` = stem + sha8 descarta la carpeta; p. ej. el mismo encargo por
    Drive y como adjunto de correo) siguen siendo DOS filas de custodia porque su
    `rel_path` difiere; (b) los N documentos lógicos de un bundle multi-documento
    (mismo `rel_path`) son N filas y NO colapsan; y (c) un segmento se identifica por
    su `doc_id`, no por su slug, que cambia si cambia el TIPO.

    `rel_paths_reprocesados` (spec §6.1) hace la corrida **autoritativa** sobre lo que
    ha reprocesado: las filas previas de esos `rel_path` que ninguna fila nueva reclama
    se descartan. Cambiar la clave no bastaba —una fusión que solo sabe añadir no puede
    sustituir—, y sin esto sobrevivían la fila reconstruida del MD (`doc_id=""`) junto a
    la fresca del mismo segmento, y las N filas de un bundle que en el reproceso pasó a
    passthrough. El conjunto lo pone el llamador desde el PLAN y no desde las filas:
    cuando un documento falla, sus filas no existen. Omitirlo conserva el comportamiento
    aditivo de siempre, que es lo que quiere `reforzar`.
    """
    reprocesados = rel_paths_reprocesados or set()
    por_clave = {_clave_cobertura(d): d for d in nueva}
    vistos: set[tuple[str, str]] = set()
    out: list[DocCobertura] = []
    for d in previa:
        clave = _clave_cobertura(d)
        if clave not in por_clave and d.rel_path in reprocesados:
            continue          # generación anterior de un documento que esta corrida rehízo
        out.append(por_clave.get(clave, d))
        vistos.add(clave)
    for d in nueva:
        clave = _clave_cobertura(d)
        if clave not in vistos:
            out.append(d)
            vistos.add(clave)
    return out


def cobertura_a_dicts(cob: list[DocCobertura]) -> list[dict]:
    """Serializa la cobertura para `_cobertura.json` (dato persistible)."""
    return [asdict(d) for d in cob]


def cobertura_desde_dicts(ds: list[dict]) -> list[DocCobertura]:
    """Reconstruye la cobertura desde `_cobertura.json`, tolerante al esquema:

    ignora claves desconocidas (p. ej. campos de una versión futura) y deja que
    los opcionales ausentes tomen su default — leer un json de otra versión no
    debe reventar la corrida.
    """
    campos = {f.name for f in fields(DocCobertura)}
    return [DocCobertura(**{k: v for k, v in d.items() if k in campos}) for d in ds]


_ZONAS_VETADAS = ("00_Input", "90_Notas personales")


def destino_seguro(dst: Path, case_dir: Path) -> Path:
    """Devuelve dst si es un destino de escritura permitido; si no, ValueError.

    Invariante del proyecto (M5): jamás escribir en 00_Input/ ni en
    90_Notas personales/. Se comprueba por los componentes de la ruta relativa.
    """
    dst = Path(dst)
    try:
        partes = dst.relative_to(case_dir).parts
    except ValueError:
        raise ValueError(f"Destino fuera del caso: {dst}")
    if partes and partes[0] in _ZONAS_VETADAS:
        raise ValueError(f"Destino en zona vetada {partes[0]!r}: {dst}")
    return dst


def _sala_maquina_dir(case_dir: Path) -> Path:
    return case_dir / "01_Procesado" / "02_Sala de máquina"


def carpeta_bundle_de(case_dir: Path, slug: str) -> Path:
    """Carpeta de artefactos de un bundle. Un solo sitio que la componga."""
    return destino_seguro(_sala_maquina_dir(case_dir) / "02_Documentos" / slug, case_dir)


VERSIONES_ANTERIORES = "99_Versiones anteriores"

# Lo único que vive legítimamente en la carpeta de un bundle además de los PDF de sus
# segmentos: el índice que escribe `separar.generar_indice` (`indice.json` + su resumen
# `indice.txt`) y el manifiesto editable con su espejo. Un `.md` o un `.txt` que no sea
# de estos solo puede venir de una publicación sucia. La lista la comparten el filtro de
# publicación y el guard: si divergieran, uno publicaría lo que el otro marca en rojo.
_FICHEROS_DE_BUNDLE = ("indice.", "_segmentacion")


def _rutas_de(sm_dir: Path, carpeta_bundle: Path, slug: str) -> tuple[Path, Path, Path]:
    """Las TRES representaciones de un documento lógico: PDF, MD y raw_text."""
    return (carpeta_bundle / f"{slug}.pdf",
            sm_dir / "03_MD" / f"{slug}.md",
            sm_dir / "raw_text" / f"{slug}.txt")


def _rutas_staging(staging: Path, slug: str) -> tuple[Path, Path, Path]:
    """Las mismas tres, en el staging del bundle (juntas, para publicar por renames)."""
    return staging / f"{slug}.pdf", staging / f"{slug}.md", staging / f"{slug}.txt"


def _sello_reproceso() -> str:
    """`AAAA-MM-DD_HHMMSS`: dos reprocesos del mismo día no se pisan el archivo."""
    return now_iso()[:19].replace(":", "").replace("T", "_")


def publicar_segmentos(case_dir: Path, sm_dir: Path, carpeta_bundle: Path, *,
                       publicaciones: list[tuple[str, str]], retirados: list[str],
                       sello: str) -> list[str]:
    """Publica la generación nueva por renames, archivando la anterior COMO CONJUNTO (§7).

    Sacar el sha del nombre tiene un precio: el destino ya existe y `replace` sobrescribe,
    de modo que un fallo a media generación dejaría la fila de cobertura declarando un sha
    que ya no corresponde a esos bytes. Por eso las tres representaciones se escriben a
    `<bundle>/_staging/` y solo al final se mueven; y por eso la anterior se archiva antes
    de publicar nada: **si el archivado no puede completarse, no se publica ninguna**.

    Se archiva además **toda generación ajena al manifiesto** que quede en la carpeta: los
    slugs del esquema viejo (con sha) no son derivables del manifiesto, así que sin esto un
    `--force` sobre un bundle legacy publicaría los nombres nuevos y dejaría los viejos al
    lado — huérfanos sin fila, que el guard vería y abortaría, inutilizando la única vía de
    escape que la pieza A ofrece hasta que se desbloquee la pieza B.

    `publicaciones`: `(slug_nuevo, slug_previo)` — el previo solo cuando el TIPO cambió y
    el slug con él. `retirados`: slugs dados de baja, que se archivan sin republicar.
    """
    staging = carpeta_bundle / split.STAGING
    archivo = destino_seguro(Path(case_dir) / VERSIONES_ANTERIORES / f"reproceso_{sello}",
                             Path(case_dir))

    publicados = {slug for slug, _ in publicaciones}
    a_archivar: list[Path] = []
    for slug in [s for par in publicaciones for s in par if s] + list(retirados):
        a_archivar += [p for p in _rutas_de(sm_dir, carpeta_bundle, slug) if p.exists()]
    for pdf in sorted(carpeta_bundle.glob("*.pdf")):
        if pdf.stem not in publicados:
            a_archivar += [p for p in _rutas_de(sm_dir, carpeta_bundle, pdf.stem)
                           if p.exists()]
    archivados: list[str] = []
    if a_archivar:
        archivo.mkdir(parents=True, exist_ok=True)
        for p in dict.fromkeys(a_archivar):        # sin duplicados, orden estable
            p.replace(archivo / p.name)            # si falla, sube: no se publica NADA
            archivados.append(p.name)

    for slug_nuevo, _ in publicaciones:
        for origen, destino in zip(_rutas_staging(staging, slug_nuevo),
                                   _rutas_de(sm_dir, carpeta_bundle, slug_nuevo)):
            destino.parent.mkdir(parents=True, exist_ok=True)
            origen.replace(destino)

    # Del staging solo sale lo de ESTA generación: los slugs publicados (ya movidos
    # arriba) y el índice del bundle. Lo demás se archiva: el `rmtree` que limpia el
    # staging usa `ignore_errors=True` y en Windows puede no haber podido borrar un
    # residuo (sharing violation del cliente de Drive, un visor abierto), y publicarlo
    # sin filtrar lo colaría como si fuera de ahora.
    if staging.is_dir():
        for resto in sorted(staging.iterdir()):
            if not resto.is_file():
                continue
            if resto.stem in publicados or resto.name.startswith(_FICHEROS_DE_BUNDLE):
                resto.replace(carpeta_bundle / resto.name)
            else:
                archivo.mkdir(parents=True, exist_ok=True)
                resto.replace(archivo / resto.name)
                archivados.append(resto.name)
        shutil.rmtree(staging, ignore_errors=True)
    return archivados


def archivar_bundle_entero(case_dir: Path, sm_dir: Path, carpeta_bundle: Path, *,
                           sello: str) -> list[str]:
    """Retira la generación de un bundle que ha DEJADO de serlo (spec §7.1).

    Cuando un reproceso resuelve como passthrough —basta con que diez caracteres de ruido
    de OCR maten la hoja en blanco que separaba— la rama passthrough escribía su MD suelto
    y no tocaba nada más. Resultado: con `--force`, N PDF de segmento sin fila y el guard
    abortando en un bucle del que no se sale; sin `--force`, las N filas viejas conviviendo
    con la nueva, que es exactamente el defecto que esta pieza existe para eliminar.

    Aquí se archiva la carpeta entera —las tres representaciones de cada segmento, el
    índice y el propio manifiesto— y la carpeta se retira. El ledger se va con el
    manifiesto: no queda bundle a quien conservárselo, y si el documento vuelve a
    detectarse como tal, `reconciliar_manifiesto(None, …)` acuña desde cero.
    """
    carpeta_bundle = Path(carpeta_bundle)
    if not carpeta_bundle.is_dir():
        return []
    archivo = destino_seguro(Path(case_dir) / VERSIONES_ANTERIORES / f"reproceso_{sello}",
                             Path(case_dir))
    slugs = [p.stem for p in sorted(carpeta_bundle.glob("*.pdf"))]
    a_archivar = [p for s in slugs for p in _rutas_de(sm_dir, carpeta_bundle, s) if p.exists()]
    a_archivar += [p for p in sorted(carpeta_bundle.rglob("*")) if p.is_file()]
    archivados: list[str] = []
    if a_archivar:
        archivo.mkdir(parents=True, exist_ok=True)
        for p in dict.fromkeys(a_archivar):
            p.replace(archivo / p.name)
            archivados.append(p.name)
    shutil.rmtree(carpeta_bundle, ignore_errors=True)
    return archivados


def baseline_doc_ids(cobertura: list[DocCobertura], parent_slug: str) -> dict[str, str]:
    """Mapa `doc_id → pp` de la última materialización de ese bundle (spec §3.3)."""
    return {c.doc_id: c.paginas for c in cobertura
            if c.parent_slug == parent_slug and c.doc_id}


def verificar_integridad_bundles(case_dir: Path, cobertura: list[DocCobertura],
                                 parents: set[str]) -> list[str]:
    """Guard BIDIRECCIONAL sobre los bundles tocados por esta corrida (spec §7.3).

    No basta con recorrer las filas: en el fallo real no hay filas de segmento —`ejecutar`
    emite UNA fila de error con el slug del documento físico— y con `--force` además la
    cobertura previa va vacía. Un guard que solo mirase filas estaría ciego justo en el
    caso para el que se escribe. Por eso se mira en los dos sentidos:

    - fila → fichero: las tres representaciones existen y el sha del PDF casa con el
      declarado en la cobertura;
    - fichero → fila: todo `02_Documentos/<parent>/*.pdf` tiene fila, y la carpeta no
      contiene `.md` ni `.txt` (ahí no vive ninguna representación legítima, así que uno
      suelto solo puede venir de una publicación sucia).

    `parents` son los slugs de los documentos que la corrida procesó, y los pone el
    llamador desde el PLAN: derivarlos de las filas dejaría el alcance vacío justo cuando
    el bundle falla. El daño histórico censado —segmentos duplicados de antes de la
    identidad persistente— es de la pieza B; auditarlo aquí bloquearía dos casos reales
    mientras B siga bloqueada.
    """
    case_dir = Path(case_dir)
    sm_dir = _sala_maquina_dir(case_dir)
    con_fila = {c.slug for c in cobertura}
    fallos: list[str] = []
    for parent in sorted(parents):
        carpeta = sm_dir / "02_Documentos" / parent
        if not carpeta.is_dir():
            continue
        for c in cobertura:
            if c.parent_slug != parent or not c.doc_id:
                continue
            pdf, md, txt = _rutas_de(sm_dir, carpeta, c.slug)
            for etiqueta, p in (("PDF", pdf), ("MD", md), ("raw_text", txt)):
                if not p.exists():
                    fallos.append(f"{c.slug}: falta la representación {etiqueta} ({p})")
            if pdf.exists() and c.sha256 and file_sha256(pdf) != c.sha256:
                fallos.append(
                    f"{c.slug}: el sha del PDF no casa con el declarado en la cobertura")
        for pdf in sorted(carpeta.glob("*.pdf")):
            if pdf.stem not in con_fila:
                fallos.append(f"{pdf.name}: PDF de segmento sin fila en la cobertura")
        for suelto in sorted(list(carpeta.glob("*.md")) + list(carpeta.glob("*.txt"))):
            if suelto.name.startswith(_FICHEROS_DE_BUNDLE):
                continue          # índice y manifiesto sí viven aquí
            fallos.append(f"{suelto.name}: representación suelta en la carpeta del bundle "
                          f"(el MD va a 03_MD y el texto a raw_text)")
    return fallos


def preflight_manifiestos(case_dir: Path, docs: list[DocPlan],
                          cobertura_previa: list[DocCobertura], *,
                          force: bool = False) -> None:
    """Valida los manifiestos en juego ANTES de procesar el primer documento (spec §4).

    `validar_manifiesto` corre hoy dentro de `_split_o_md`, documento a documento, y
    `apply` solo persiste cobertura, estado y evento cuando `ejecutar` retorna: si el
    manifiesto inválido es el del segundo bundle, el primero ya publicó su generación.
    Aquí no se escribe nada —solo se leen JSON—, así que la corrida muere antes de tocar
    ningún artefacto de la Sala de máquina.

    Alcance declarado: se validan IDENTIDAD y EDICIÓN de los manifiestos ya en disco de
    los documentos que esta corrida va a procesar. Los rangos exigen el nº de páginas del
    buscable, que para un escaneado todavía no existe, y se siguen validando en
    `_split_o_md` con el total real. La reconciliación de `--force` tampoco es
    preflightable por lo mismo: la cubren el aislamiento por documento y el guard
    bidireccional.
    """
    case_dir = Path(case_dir)
    for d in docs:
        # Toda ruta que MATERIALIZA bundles pasa por aquí (R1/H-01 de la acción 10: la ruta
        # `ofimatica` también segmenta, y sin esto una permutación de `pp` en su manifiesto
        # se publicaba sin aviso).
        if d.skip or d.ruta not in _RUTAS_CON_BUNDLE:
            continue
        carpeta = carpeta_bundle_de(case_dir, d.slug)
        if not split.manifiesto_existe(carpeta):
            continue
        try:
            manifiesto = split.leer_manifiesto(carpeta)
        except json.JSONDecodeError as exc:
            # `leer_manifiesto` es un `json.loads` pelado y el JSON truncado es el fallo
            # más probable del único fichero que el letrado edita a mano. Sin esto
            # escapaba del `except` del CLI como traceback en vez de salida 2.
            raise split.ManifestValidationError(
                f"`_segmentacion.json` ilegible en {carpeta}: {exc}. Es un JSON editado a "
                f"mano: revísalo, o bórralo y deja que `apply` lo regenere.") from exc
        # Con --force el manifiesto en disco se RECONCILIA (no se consume tal cual), así
        # que un esquema viejo sin doc_id no bloquea: se le acuñan identidades nuevas.
        split.validar_identidad(manifiesto, exigir_doc_id=not force)
        if not force:
            split.validar_edicion(manifiesto, baseline_doc_ids(cobertura_previa, d.slug))


_NATIVO_EXTRACTORES = {
    ".eml": _try_email,
    ".rtf": _try_rtf,
    ".ics": _try_ics,
    ".csv": _try_pandas_table,
    ".xlsx": _try_pandas_table,
    ".xls": _try_pandas_table,
    ".docx": _try_docx,
}
_NATIVO_TEXTO_PLANO = {".txt", ".md", ".html", ".htm"}


def _extraer_nativo(src: Path, ext: str) -> str:
    """Texto de un fichero nativo, por extensión (helpers SANOS de extractor).

    Nunca la rama Docling/30pp de `extractor._extract_one` (spec §5.1) — solo los
    `_try_*` deterministas y `_read_text_file` para texto plano.
    """
    e = ext.lower()
    if e in _NATIVO_TEXTO_PLANO:
        return _read_text_file(src)
    fn = _NATIVO_EXTRACTORES.get(e)
    if fn is None:
        return ""
    return fn(src) or ""


_VISION_RENDER_SCALE = 2   # factor de render pypdfium2 → ~144 dpi (72·2), legible para visión


def _renderizar_paginas(pdf_path: Path):
    """Renderiza cada página de un PDF a imagen PIL (para el refuerzo `--vision`)."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        return [pagina.render(scale=_VISION_RENDER_SCALE).to_pil() for pagina in doc]
    finally:
        doc.close()


def _transcribir_vision(imgs) -> str:
    """Punto de inyección del refuerzo `--vision` (Claude). Sin llamada real aquí:

    quien active `--vision` debe monkeypatchear esta función (test) o cablearla al
    modelo (CLI/skill) — nunca se llama a ningún modelo desde este módulo (spec §5,
    D3: off por defecto, sin llamadas reales embebidas en el cerebro).
    """
    raise NotImplementedError(
        "Refuerzo de vision no cableado: monkeypatchear sala_maquina._transcribir_vision"
    )


# Marca del stub: quien lo reemplace (monkeypatch en test, o el cableado del flujo
# skill/sesión) instala una función SIN esta marca → vision_cableada() lo detecta.
_transcribir_vision._es_stub = True


def vision_cableada() -> bool:
    """`True` si `_transcribir_vision` está cableado (no es el stub por defecto).

    Gemelo del preflight de `--vision` en el CLI: permite avisar EN ALTO cuando se
    pide refuerzo por visión sin transcriptor, en vez del no-op silencioso que
    dejaba una nota 'refuerzo vision falló…' por documento (fallo de VALERO).
    """
    return not getattr(_transcribir_vision, "_es_stub", False)


def _reforzar_con_vision(pdf_path: Path, texto: str, estado: str, nota: str) -> tuple[str, str, str]:
    """Si `estado` es dudoso, intenta mejorar `texto` con transcripción de visión.

    Nunca lanza: un fallo de render o de transcripción deja el documento tal cual
    (con nota) — el refuerzo es un extra opcional, no debe tumbar el documento
    (aislamiento por documento, spec §9).
    """
    try:
        imgs = _renderizar_paginas(pdf_path)
        extra = (_transcribir_vision(imgs) or "").strip()
    except Exception as e:
        motivo = f"refuerzo vision falló: {e}"
        return texto, estado, f"{nota} · {motivo}" if nota else motivo
    if not extra:
        return texto, estado, nota
    nuevo_texto = f"{texto}\n\n{extra}".strip() if texto.strip() else extra
    nuevo_estado, nuevo_nota = ocr_quality(nuevo_texto, _pdf_num_paginas(pdf_path))
    if nuevo_estado == "ok":
        return nuevo_texto, nuevo_estado, nuevo_nota or "reforzado con vision"
    # sigue dudoso tras el refuerzo: deja constancia de que SÍ se intentó visión
    # (si no, la cobertura no distingue "no se intentó" de "se intentó y no bastó").
    sufijo = "reforzado con vision, sigue dudoso"
    return nuevo_texto, nuevo_estado, f"{nuevo_nota} · {sufijo}" if nuevo_nota else sufijo


def _aplicar_vision(fuente_render: Path, texto: str, estado: str, nota: str,
                    vision: bool) -> tuple[str, str, str]:
    """Gate ÚNICO del refuerzo `--vision`: refuerza solo si está activado y el
    documento salió dudoso (`low`/`empty`). Usado por AMBOS caminos (OCR y
    pypdf-digital) para no duplicar la condición.
    """
    if vision and estado in ("low", "empty"):
        return _reforzar_con_vision(fuente_render, texto, estado, nota)
    return texto, estado, nota


def _escribir_md(case_dir, case_id, slug, rel_path, texto, metodo, ocr, estado,
                 *, md_path: Path | None = None, raw_path: Path | None = None):
    """Escribe el MD y su `raw_text`. Con `md_path`/`raw_path` explícitos escribe al
    staging del bundle, para que la generación se publique entera o no se publique."""
    sm_dir = _sala_maquina_dir(case_dir)
    md_path = destino_seguro(md_path or sm_dir / "03_MD" / f"{slug}.md", case_dir)
    raw_path = destino_seguro(raw_path or sm_dir / "raw_text" / f"{slug}.txt", case_dir)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(texto, encoding="utf-8")
    meta = {
        "case_id": case_id, "tipo": "documento_procesado", "fase": "01_Procesado",
        "fecha": now_iso(), "source_path": rel_path, "extractor": metodo,
        "chars": len(texto), "ocr": ocr, "ocr_quality": estado,
        "text_sha256": text_sha256(texto),
    }
    write_md(md_path, meta, texto)


def _calidad(texto: str, pdf: Path) -> tuple[str, str]:
    """`ocr_quality` del documento + la señal POR PÁGINA que rompe la dilución.

    Solo puede degradar: si el promedio ya dice `low`/`empty`, no se perfila (ni
    se paga la pasada) porque el documento ya está en la worklist.
    """
    estado, nota = ocr_quality(texto, _pdf_num_paginas(pdf))
    if estado != "ok" or not pdf_paginas.tiene_rasteres(pdf):
        return estado, nota
    p_estado, p_nota = calidad_por_pagina(pdf_paginas.perfilar_paginas(pdf))
    return (p_estado, p_nota) if p_estado else (estado, nota)


def _paginas_ciegas(pdf: Path) -> list[int]:
    """Páginas con escaneo a página completa bajo una capa de texto de sello.

    Pasa antes el gate barato (`tiene_rasteres`, solo metadato) para no perfilar
    página a página el caso común: un PDF nativo, sin nada ciego que buscar.
    """
    if not pdf_paginas.tiene_rasteres(pdf):
        return []
    return pdf_paginas.paginas_ciegas(pdf_paginas.perfilar_paginas(pdf))


def _anotar(filas: list[DocCobertura], aviso: str) -> None:
    """Añade `aviso` a la nota de cada fila, preservando lo que ya hubiera."""
    if not aviso:
        return
    for f in filas:
        f.nota = f"{f.nota} · {aviso}" if f.nota else aviso


def _split_o_md(case_dir: Path, sm_dir: Path, case_id: str, d: DocPlan,
                buscable: Path, metodo_base: str, ocr: bool, vision: bool,
                force: bool = False) -> list[DocCobertura]:
    """Sobre el PDF buscable: si tiene ≥2 documentos lógicos, corta el bundle y
    genera un MD por documento; si no, MD único (passthrough = comportamiento
    previo al split). Devuelve las filas de cobertura (N si es bundle, 1 si no).

    El manifiesto es el gate editable por el letrado: se respeta el existente
    salvo `--force`, que lo regenera desde la detección (Task 14).
    """
    try:
        segmentos, blancos = split.detectar(buscable)
        split_err = ""
    except Exception as e:
        # No se pudo segmentar (PDF ilegible/corrupto/vacío para el detector): se
        # degrada a passthrough (un solo documento) en vez de perder el documento.
        # Preserva el comportamiento previo al split; la nota deja constancia.
        segmentos, blancos, split_err = None, None, str(e)

    if not segmentos or len(segmentos) <= 1:
        # passthrough: un solo documento lógico → MD único, como antes del split.
        # PERO si este documento YA fue un bundle, su generación anterior se retira aquí:
        # dejarla en disco dejaba los N PDF de segmento sin fila (con --force, guard en
        # rojo del que no se sale; sin --force, duplicación silenciosa). La cobertura la
        # resuelve la fusión autoritativa: la corrida manda sobre el rel_path que rehace.
        archivados = archivar_bundle_entero(case_dir, sm_dir,
                                            carpeta_bundle_de(case_dir, d.slug),
                                            sello=_sello_reproceso())
        texto = _try_pypdf(buscable) or ""
        estado, nota = _calidad(texto, buscable)
        texto, estado, nota = _aplicar_vision(buscable, texto, estado, nota, vision)
        if split_err:
            aviso = f"segmentación omitida ({split_err})"
            nota = f"{nota} · {aviso}" if nota else aviso
        if archivados:
            aviso = (f"ya no se detecta como bundle: {len(archivados)} artefactos de la "
                     f"generación anterior archivados en {VERSIONES_ANTERIORES}/")
            nota = f"{nota} · {aviso}" if nota else aviso
            try:
                # B0-1: el evento va donde estan los bytes, no a CASOS_ROOT.
                append_event(case_dir, "split_documental", case_id=case_id, details={
                    "bundle": d.rel_path, "bundle_sha256": d.sha256, "n_segmentos": 0,
                    "modo": "passthrough_retira_bundle", "archivados": archivados,
                })
            except Exception as exc:  # noqa: BLE001 — el trabajo ya está en disco
                nota = f"{nota} · evento split_documental no registrado: {exc}"
        _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, metodo_base, ocr, estado)
        tipo_pass = segmentos[0].tipo if segmentos else ""
        return [DocCobertura(d.slug, d.rel_path, metodo_base, estado, len(texto), ocr, nota,
                             d.sha256, parent_sha256=d.sha256, tipo=tipo_pass)]

    # split: manifiesto (editable) → reconciliar → materializar a staging → publicar.
    carpeta_bundle = carpeta_bundle_de(case_dir, d.slug)
    previo = (split.leer_manifiesto(carpeta_bundle)
              if split.manifiesto_existe(carpeta_bundle) else None)
    if previo is not None and not force:
        manifiesto, rec = previo, None
    else:
        # --force RECONCILIA en vez de sustituir: sin esto, el manifiesto nuevo perdería
        # las identidades y el reproceso volvería a renombrarlo todo (spec §5).
        rec = split.reconciliar_manifiesto(
            previo, split.construir_manifiesto(d.rel_path, d.sha256, segmentos, blancos))
        manifiesto = rec.manifiesto
    split.validar_manifiesto(manifiesto, _pdf_num_paginas(buscable) or 0)
    if rec is not None:
        split.escribir_manifiesto(carpeta_bundle, manifiesto)

    staging = carpeta_bundle / split.STAGING
    shutil.rmtree(staging, ignore_errors=True)     # restos de una corrida abortada
    doclogicos = split.materializar(buscable, manifiesto, carpeta_bundle,
                                    parent_slug=d.slug, parent_sha256=d.sha256,
                                    bundle_rel_path=d.rel_path, carpeta_salida=staging)
    tipos_previos = {e["doc_id"]: e["tipo"]
                     for e in (previo or {}).get("segmentos", []) if e.get("doc_id")}
    filas: list[DocCobertura] = []
    publicaciones: list[tuple[str, str]] = []
    for dl in doclogicos:
        seg_pdf = staging / f"{dl.slug}.pdf"
        texto = _try_pypdf(seg_pdf) or ""
        estado, nota = _calidad(texto, seg_pdf)
        texto, estado, nota = _aplicar_vision(seg_pdf, texto, estado, nota, vision)
        _escribir_md(case_dir, case_id, dl.slug, d.rel_path, texto, metodo_base, ocr, estado,
                     md_path=staging / f"{dl.slug}.md", raw_path=staging / f"{dl.slug}.txt")
        tipo_previo = tipos_previos.get(dl.doc_id)
        slug_previo = (split._slug_seg(d.slug, dl.doc_id, tipo_previo)
                       if tipo_previo and tipo_previo != dl.tipo else "")
        publicaciones.append((dl.slug, slug_previo))
        filas.append(DocCobertura(dl.slug, d.rel_path, metodo_base, estado, len(texto), ocr, nota,
                                  dl.seg_sha256, parent_slug=dl.parent_slug, parent_sha256=d.sha256,
                                  role=dl.role_in_bundle, paginas=dl.paginas, tipo=dl.tipo,
                                  doc_id=dl.doc_id))
    retirados = [split._slug_seg(d.slug, e["doc_id"], e["tipo"])
                 for e in (rec.retirados if rec else [])]
    archivados = publicar_segmentos(case_dir, sm_dir, carpeta_bundle,
                                    publicaciones=publicaciones, retirados=retirados,
                                    sello=_sello_reproceso())
    if rec and rec.legacy_sin_identidad:
        # Acuñar sobre entradas legacy es correcto, callarlo no. Va a la nota de cobertura
        # —la worklist que el letrado mira— y al evento, no solo a un log.
        _anotar(filas, f"identidades nuevas acuñadas sobre {len(rec.legacy_sin_identidad)} "
                       f"entradas del manifiesto anterior sin doc_id "
                       f"({', '.join(rec.legacy_sin_identidad)})")
    try:
        append_event(case_id, "split_documental", details={
            "bundle": d.rel_path, "bundle_sha256": d.sha256, "n_segmentos": len(doclogicos),
            "segmentos": [{"slug": dl.slug, "doc_id": dl.doc_id, "seg_sha256": dl.seg_sha256,
                           "tipo": dl.tipo, "paginas": dl.paginas} for dl in doclogicos],
            "delimitadores": manifiesto["delimitadores"],
            "archivados": archivados,
            "retirados": [e["doc_id"] for e in (rec.retirados if rec else [])],
            "legacy_sin_identidad": list(rec.legacy_sin_identidad) if rec else [],
        })
    except Exception as exc:  # noqa: BLE001 — el trabajo YA está publicado en disco
        # Sin esto la excepción sube a `ejecutar`, que emite UNA fila de error con el slug
        # del documento físico: los artefactos quedan en disco y la cobertura los niega.
        # El guard bidireccional abortaría después, con razón, por un fallo de log — y el
        # log vive en el Drive, así que un fichero bloqueado basta para provocarlo.
        _anotar(filas, f"evento split_documental no registrado: {exc}")
    return filas


def _ocr_y_extraer(case_dir: Path, sm_dir: Path, case_id: str, d: DocPlan,
                   entrada: Path, vision: bool, force: bool = False,
                   conservador: bool = False) -> list[DocCobertura]:
    """Escalera de OCR sobre `entrada` → PDF buscable en 01_OCR/ → split → MD.

    Compartido por el camino PDF escaneado y el camino imagen/`.heic` (ambos
    terminan en "aplícale OCR a un PDF"; solo cambia de dónde sale ese PDF).
    Devuelve una lista de cobertura (N filas si el buscable es un bundle
    multi-documento; 1 fila en passthrough o si el OCR falla).

    `conservador` viaja hasta `ocr_pdf_escalera`: lo activa el documento que YA
    trae capa de texto real y solo esconde páginas ciegas (`MEJORAS #90`).
    """
    ocr_out = destino_seguro(sm_dir / "01_OCR" / f"{d.slug}.pdf", case_dir)
    try:
        res = ocr_pdf_escalera(entrada, ocr_out, conservador=conservador)
        buscable = Path(res.ruta)
    except Exception as e:  # OCRError incl. cifrado/corrupto/firmado
        nota = f"OCR falló: {e}"
        if not vision:
            return [DocCobertura(d.slug, d.rel_path, "ocr", "empty", 0, True, nota, d.sha256,
                                 parent_sha256=d.sha256)]
        # OCRmyPDF rechazó el PDF, pero pypdfium2 (rasterizador más permisivo) puede
        # renderizarlo: intenta la visión sobre la entrada original. Es justo el doc
        # que `reforzar` existe para rescatar; sin esto la visión nunca se intentaba
        # aquí (se retornaba antes del gate de visión). El texto viene solo de la
        # visión → metodo "vision", sin artefacto de custodia en 01_OCR (ocr=False);
        # metodo "vision" queda fuera de los reforzables → no hay reintento en bucle.
        texto, estado, nota = _reforzar_con_vision(entrada, "", "empty", nota)
        if texto.strip():
            _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "vision", False, estado)
        return [DocCobertura(d.slug, d.rel_path, "vision", estado, len(texto), False, nota, d.sha256,
                             parent_sha256=d.sha256)]
    # Contrato de la escalera: si ningún peldaño regeneró el PDF, devuelve la
    # ENTRADA sin escribir ocr_out → no hay artefacto de custodia en 01_OCR/.
    persistido = buscable == ocr_out and ocr_out.exists()
    metodo, ocr = ("ocr", True) if persistido else ("pypdf", False)
    filas = _split_o_md(case_dir, sm_dir, case_id, d, buscable, metodo, ocr, vision, force)
    _anotar(filas, res.nota)
    if res.degradado:
        # Peldaño 3: quedó texto escondido bajo un ráster que no se pudo sacar.
        # El documento NO puede salir `ok`: `ok` lo deja fuera de la worklist de
        # `_cobertura.md` y fuera del filtro de `reforzar` — el silencio de #90.
        for f in filas:
            if f.estado == "ok":
                f.estado = "low"
        _anotar(filas, "escalera degradada: queda texto ciego sin recuperar")
    if not persistido:
        # No afirmamos una custodia que no existe: el texto sale de la capa previa;
        # se refleja como pypdf con nota explícita, preservada por documento lógico.
        # La redacción es neutra a propósito: "no se regeneró" cubre tanto el PDF
        # que ya traía OCR como la escalera que no consiguió recuperar nada, y el
        # motivo concreto ya viene en `res.nota`.
        _anotar(filas, "ningún peldaño regeneró el PDF; sin artefacto en 01_OCR")
    return filas


#: Método de la fila de custodia de una copia byte-idéntica (MEJORAS #147, vía A). No es un
#: método de extracción: dice «este fichero existe aquí y su espejo es el del titular».
METODO_DUPLICADO = "duplicado"


def _peor_estado(filas: list[DocCobertura]) -> str:
    """El estado que hereda la copia: el PEOR de las filas del titular, para que la copia no
    salga `ok` con un titular `empty` y se pierda de la worklist de `_cobertura.md`."""
    orden = {"empty": 0, "sin_soporte": 1, "low": 2, "ok": 3}
    return min((f.estado for f in filas), key=lambda e: orden.get(e, 0))


def _ruta_espejo(filas_titular: list[DocCobertura]) -> tuple[str, str]:
    """(slug del titular, ruta REAL de su espejo): `03_MD/<slug>.md` si es suelto; si es
    bundle, la carpeta del índice y el patrón de sus segmentos (R1/H-07: `03_MD/<parent>`
    no existe como fichero ni como carpeta)."""
    t = filas_titular[0]
    if t.parent_slug:
        return t.parent_slug, (f"02_Documentos/{t.parent_slug}/ y 03_MD/{t.parent_slug}__dNN_*.md "
                               f"({len(filas_titular)} documentos lógicos)")
    return t.slug, f"03_MD/{t.slug}.md"


def _anotar_procedencia(filas_titular: list[DocCobertura], rel_copia: str) -> None:
    """«también en <ruta>» en el titular, idempotente: reconciliar no duplica la nota."""
    aviso = f"también en {rel_copia} (mismo sha256)"
    for f in filas_titular:
        if aviso not in f.nota:
            f.nota = f"{f.nota} · {aviso}" if f.nota else aviso


def _fila_duplicado(d: DocPlan, filas_titular: list[DocCobertura]) -> DocCobertura:
    """Fila de custodia de una copia byte-idéntica, y anota en el titular la procedencia.

    La copia conserva su `rel_path` y su `sha256` (cadena de custodia: el fichero existe en
    esa carpeta), hereda el PEOR estado del titular, apunta al titular por `alias_de`
    (referencia estructurada) y NO tiene espejo propio: la nota dice dónde está el único.
    El titular gana «también en <ruta>» para que quien lea `_cobertura.md` sepa que el
    documento vive en N carpetas del cliente sin tener que buscarlo.
    """
    alias_de, espejo = _ruta_espejo(filas_titular)
    _anotar_procedencia(filas_titular, d.rel_path)
    return DocCobertura(
        d.slug, d.rel_path, METODO_DUPLICADO, _peor_estado(filas_titular), 0, False,
        f"copia byte-idéntica de {d.duplicado_de}: espejo único en {espejo}",
        d.sha256, alias_de=alias_de,
    )


def _alias_o_none(case_dir: Path, sm_dir: Path, d: DocPlan,
                  cobertura: list[DocCobertura]) -> DocCobertura | None:
    """La fila de alias de la copia `d`, o `None` si hay que procesarla como un documento.

    - Titular con filas en ESTA corrida: alias, salvo que el titular no haya sabido extraer
      nada (todas sus filas `sin_soporte`, R1/H-01): mismos bytes no es misma capacidad, y
      la copia con extensión reconocida puede aportar el texto.
    - Titular sin filas en esta corrida (`--solo <copia>`, `reforzar`, R1/H-05) pero con
      espejo YA en disco: alias provisional (estado `ok`, nota que lo dice); el estado real
      lo pone `reconciliar_alias` al fusionar con la cobertura previa, que sí conoce al
      titular. Así `--solo <copia>` no reescribe el espejo compartido ni crea un segundo.
    - Ni filas ni espejo: `None`.
    """
    filas_titular = [c for c in cobertura if c.rel_path == d.duplicado_de]
    if filas_titular:
        if all(c.metodo == "sin_soporte" for c in filas_titular):
            return None
        return _fila_duplicado(d, filas_titular)
    slug_t = output_slug(d.duplicado_de, d.sha256)
    if (sm_dir / "03_MD" / f"{slug_t}.md").exists():
        espejo = f"03_MD/{slug_t}.md"
    elif carpeta_bundle_de(case_dir, slug_t).is_dir():
        espejo = f"02_Documentos/{slug_t}/ y 03_MD/{slug_t}__dNN_*.md"
    else:
        return None
    return DocCobertura(
        d.slug, d.rel_path, METODO_DUPLICADO, "ok", 0, False,
        f"copia byte-idéntica de {d.duplicado_de}: espejo único en {espejo} (de una corrida "
        f"anterior; estado heredado al fusionar)", d.sha256, alias_de=slug_t,
    )


def reconciliar_alias(cob: list[DocCobertura]) -> list[DocCobertura]:
    """Tras fusionar cobertura previa y delta: los alias reflejan a su titular (R1/H-04).

    Reprocesar solo al titular (`--solo`, `reforzar`) sustituye sus filas por otras frescas
    —sin la nota «también en» y con otro estado— y deja a la copia con el estado viejo. Aquí
    se rehace la relación sobre la cobertura COMPLETA: por cada alias, el peor estado vigente
    de las filas productoras con su mismo `sha256`, `alias_de` al día, y la procedencia
    anotada de nuevo en el titular (idempotente). Un alias sin productoras se deja como está:
    no hay contra qué reconciliar y borrarlo sería perder custodia.
    """
    por_sha: dict[str, list[DocCobertura]] = {}
    for c in cob:
        if c.metodo != METODO_DUPLICADO:
            por_sha.setdefault(c.sha256, []).append(c)
    for c in cob:
        if c.metodo != METODO_DUPLICADO:
            continue
        titulares = por_sha.get(c.sha256, [])
        if not titulares:
            continue
        c.estado = _peor_estado(titulares)
        c.alias_de = titulares[0].parent_slug or titulares[0].slug
        _anotar_procedencia(titulares, c.rel_path)
    return cob


def _ofimatica_y_extraer(case_dir: Path, sm_dir: Path, case_id: str, d: DocPlan,
                         src: Path, vision: bool, force: bool = False) -> list[DocCobertura]:
    """`.doc`/`.odt`/`.ppt`… → PDF con LibreOffice → el mismo camino que un PDF de Drive.

    Acción 10 del informe de Codex sobre el alta (`MEJORAS #61`): hasta aquí un `.doc`
    salía `sin_soporte` sin PDF, sin MD y sin decir por qué. Ahora:

    - Si LibreOffice no está, la fila es `sin_soporte` **con la causa en la nota**: no es
      «sin soporte para esta extensión», es «falta el conversor», y eso se lee en
      `_cobertura.md`. Callarlo sería el mismo silencio que se viene a arreglar.
    - Si la conversión falla, ídem con el motivo (`conversión a PDF falló: …`), como hace
      la ruta imagen.
    - Si el PDF convertido trae capa de texto suficiente (el caso normal: un documento
      redactado), se **persiste en `01_OCR/`** como PDF buscable —custodia, igual que el
      producto de la escalera— y sigue por `_split_o_md` con método `ofimatica`.
    - Si no la trae (un `.doc` que solo envuelve un escaneo), baja a la escalera de OCR
      sobre el intermedio, que es la que sabe persistir y anotar su propio resultado.

    Aislamiento por documento: todo fallo se registra en la fila, nada aborta el lote.

    **Staging antes que publicación** (R1/H-03): el conversor escribe en un temporal, se
    decide sobre ese temporal, y solo el PDF que cumple el contrato de «buscable» se publica
    en `01_OCR/<slug>.pdf`. La primera versión publicaba primero y apartaba después, y un
    fallo al apartar (un lector con el fichero abierto, `WinError 32`) dejaba un PDF mudo en
    `01_OCR/` con la fila diciendo `error`. Esa publicación es una escritura nueva de este
    módulo y está DECLARADA en `tests/test_escritura_censo.py` (techo 88 → 91), no absorbida.
    """
    with tempfile.TemporaryDirectory() as tmp:
        intermedio = Path(tmp) / f"{d.slug}__ofimatica.pdf"
        try:
            convertir_ofimatica(src, intermedio)
        except ConversorNoDisponible as e:
            return [DocCobertura(d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False,
                                 f"sin convertir: {e}", d.sha256)]
        except ConversionFallida as e:
            return [DocCobertura(d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False,
                                 f"conversión a PDF falló: {e}", d.sha256)]
        texto = _try_pypdf(intermedio) or ""
        npags = _pdf_num_paginas(intermedio)
        digital = bool(texto.strip()) and _texto_suficiente(texto, npags)
        if not (digital and not _paginas_ciegas(intermedio)):
            # Sin capa de texto suficiente (un .doc que envuelve un escaneo): la escalera de
            # OCR publica ella su propio buscable en 01_OCR y anota su resultado.
            filas = _ocr_y_extraer(case_dir, sm_dir, case_id, d, intermedio, vision, force,
                                   conservador=digital)
            _anotar(filas, f"convertido de {d.ext} con LibreOffice antes del OCR")
            return filas
        # Digital: se publica el buscable (custodia, como el producto de la escalera) y sigue
        # por el split. Si publicar falla, no hay nada a medias en 01_OCR: el PDF sigue en tmp.
        buscable = destino_seguro(sm_dir / "01_OCR" / f"{d.slug}.pdf", case_dir)
        buscable.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(intermedio), str(buscable))
    filas = _split_o_md(case_dir, sm_dir, case_id, d, buscable, "ofimatica", False,
                        vision, force)
    _anotar(filas, f"convertido de {d.ext} con LibreOffice; PDF buscable en 01_OCR")
    return filas


@dataclass
class TextoPdf:
    """Texto de un PDF con la etiqueta de cómo salió y de si es fiable."""
    texto: str
    metodo: str          # pypdf | ocr | sin_texto
    estado: str          # ok | low | empty
    nota: str = ""
    ocr: bool = False


def texto_de_pdf(pdf: Path, *, ocr_salida: Path | None = None) -> TextoPdf:
    """«Dame el mejor texto de este PDF», con la etiqueta de calidad puesta.

    Es el motor de la sala de máquina expuesto **sin sus artefactos**: mismo enrutado,
    misma escalera, mismos discriminantes, misma `ocr_quality`, pero sin escribir MD ni
    hacer split. Existe para que el camino de los adjuntos de correo deje de tener su
    propio motor (`MEJORAS #87`): hasta el 2026-08-04 un adjunto bajaba por
    `extractor._extract_one` —pypdf, y Docling solo si ≤30 páginas—, así que un escaneado
    largo daba **cero texto** y un escaneado con pie de LexNET salía por pypdf con el
    cuerpo perdido y etiqueta `alta`.

    Vive aquí, y no en un módulo nuevo, a propósito: la escalera, el discriminante de
    página ciega y `ocr_quality` ya viven aquí. Un módulo aparte habría creado una
    TERCERA superficie en vez de unificar dos.

    Enrutado, idéntico al de `ejecutar`:
      1. Capa de texto suficiente y **sin** páginas ciegas → `pypdf`, sin pagar OCR.
      2. Capa de texto suficiente **con** páginas ciegas → escalera en modo
         **conservador** (`MEJORAS #90`): no reescribe las páginas digitales.
      3. Sin capa suficiente (escaneado) → escalera completa, **sin tope de páginas**.

    `ocr_salida`: si se indica, ahí queda el PDF buscable (artefacto de custodia). Si no,
    va a un temporal y se descarta — el llamador de adjuntos no tiene dónde guardarlo, y
    afirmar una custodia que no existe sería peor que no tenerla.
    """
    texto = _try_pypdf(pdf) or ""
    npags = _pdf_num_paginas(pdf)
    ciegas = _paginas_ciegas(pdf)
    digital = bool(texto.strip()) and _texto_suficiente(texto, npags)

    if digital and not ciegas:
        estado, nota = ocr_quality(texto, npags)
        return TextoPdf(texto, "pypdf", estado, nota, False)

    with tempfile.TemporaryDirectory() as tmp:
        destino = Path(ocr_salida) if ocr_salida else Path(tmp) / f"{pdf.stem}__ocr.pdf"
        try:
            res = ocr_pdf_escalera(pdf, destino, conservador=digital)
        except Exception as e:  # noqa: BLE001 — cifrado, corrupto, firmado…
            # No se tira el residuo: un sello de registro es poco, pero es lo que hay, y
            # el motivo viaja para que el lector sepa que está viendo un resto.
            estado, nota = ocr_quality(texto, npags)
            motivo = f"OCR falló: {e}" + (f"; {nota}" if nota else "")
            return TextoPdf(texto, "pypdf" if texto.strip() else "sin_texto",
                            estado, motivo, False)

        buscable = Path(res.ruta)
        persistido = buscable == destino and destino.exists()
        texto_ocr = (_try_pypdf(buscable) or "") if persistido else ""
        final = texto_ocr if texto_ocr.strip() else texto
        estado, nota = ocr_quality(final, npags)

        if persistido:
            # `#90` (b): la señal por página rompe la dilución del promedio — 4 escaneos
            # mudos entre 36 páginas densas salen `ok` sin esto. Nunca sube la calidad.
            try:
                estado_pag, nota_pag = calidad_por_pagina(
                    pdf_paginas.perfilar_paginas(buscable))
            except Exception:  # noqa: BLE001 — la señal es un extra, no un requisito
                estado_pag, nota_pag = "", ""
            if estado_pag == "low":
                estado, nota = "low", nota_pag if not nota else f"{nota}; {nota_pag}"

        if res.degradado and estado == "ok":
            estado = "low"
        for extra in (res.nota, "escalera degradada: queda texto ciego sin recuperar"
                      if res.degradado else ""):
            if extra:
                nota = f"{nota}; {extra}" if nota else extra

        if not final.strip():
            return TextoPdf("", "sin_texto", "empty", nota or "sin texto recuperable", False)
        return TextoPdf(final, "ocr" if persistido else "pypdf", estado, nota, persistido)


def ejecutar(case_dir: Path, docs: list[DocPlan], *, case_id: str,
             vision: bool = False, force: bool = False,
             on_documento: "Callable[[DocPlan, int, list[DocCobertura]], None] | None" = None,
             ) -> list[DocCobertura]:
    """Recorre el plan escribiendo 01_OCR/, raw_text/, 03_MD/. Devuelve cobertura.

    `on_documento(doc, ms, filas)`: gancho de instrumentación, llamado tras CADA
    documento con lo que tardó y las filas que produjo. Existe porque nadie había medido
    dónde se va el tiempo del montaje, y sin ese reparto no se puede decidir si
    paralelizar el OCR compra algo: `ocr_pdf` no pasa `jobs`, así que ocrmypdf ya
    paraleliza por página con todos los núcleos, y el paralelismo externo puede ser un
    salto o ser nada según el reparto de páginas del caso. El gancho no altera el
    resultado: si es `None` no se mide.

    Rutas (spec §5): PDF con capa de texto → pypdf sin OCR; PDF escaneado o
    imagen/`.heic` → `imagen_a_pdf` (si aplica) → OCRmyPDF → PDF buscable
    persistido en 01_OCR/ → texto; nativo (`.eml`/`.docx`/`.txt`/...) → helpers
    deterministas de `extractor`, sin tocar 01_OCR/. `--vision` (opcional, off
    por defecto) refuerza `low`/`empty` renderizando páginas con pypdfium2.

    (`docs`, no `plan`: evita tapar la función pública `plan()` del módulo.)
    """
    case_dir = Path(case_dir)
    sm_dir = _sala_maquina_dir(case_dir)
    cobertura: list[DocCobertura] = []

    # Los titulares antes que sus copias: el alias se construye sobre las filas del titular
    # en esta corrida, y el inventario ordenado puede traer la copia primero (`A/encargo`
    # sin extensión antes que `B/encargo.docx`). Orden estable: entre titulares, el de siempre.
    for d in sorted(docs, key=lambda x: bool(x.duplicado_de)):
        if d.skip:
            continue
        if d.duplicado_de:
            fila = _alias_o_none(case_dir, sm_dir, d, cobertura)
            if fila is not None:
                cobertura.append(fila)
                if on_documento is not None:
                    on_documento(d, 0, cobertura[-1:])
                continue
            # Sin espejo del titular (ni en esta corrida ni en disco), o titular sin
            # capacidad de extracción: la copia se procesa como un documento más. Nunca se
            # colapsa contra algo que no existe.
        _n_antes = len(cobertura)
        _t0 = time.perf_counter()
        # spec §9: aislar el fallo por documento. Un error en uno (lock ~$ de
        # Office, disco lleno, PDF corrupto que revienta pypdf) se registra en
        # cobertura y NO aborta el lote — así apply() siempre llega a escribir
        # _cobertura.md, el estado y el evento de log.
        try:
            src = case_dir / "00_Input" / d.rel_path
            if d.ruta == "pdf":
                texto = _try_pypdf(src) or ""
                npags = _pdf_num_paginas(src)
                if texto and _texto_suficiente(texto, npags):
                    # OJO: "tiene capa de texto" no es "tiene TODO su texto". Un
                    # escaneo con el pie de firma de LexNET ronda 228 char/pág —
                    # 5,7× el umbral— y pasa por digital con el cuerpo perdido
                    # (`MEJORAS #90`). Si esconde páginas ciegas baja a la
                    # escalera en modo conservador: peldaño 2, que aísla y
                    # re-OCR-iza SOLO esas páginas y no reescribe las digitales.
                    if _paginas_ciegas(src):
                        cobertura.extend(_ocr_y_extraer(case_dir, sm_dir, case_id, d, src,
                                                        vision, force, conservador=True))
                        continue
                    # PDF digital (ya buscable): el split va sobre el propio PDF → MD por doc lógico
                    cobertura.extend(_split_o_md(case_dir, sm_dir, case_id, d, src, "pypdf", False, vision, force))
                    continue
                # escaneado → OCRmyPDF (sin tope de páginas) → split → MD
                cobertura.extend(_ocr_y_extraer(case_dir, sm_dir, case_id, d, src, vision, force))
            elif d.ruta == "imagen":
                # imagen/.heic → PDF intermedio (no persistido: solo el buscable
                # tras OCR va a 01_OCR/, spec §5) → mismo camino OCR que un escaneado.
                with tempfile.TemporaryDirectory() as tmp:
                    intermedio = Path(tmp) / f"{d.slug}__imagen.pdf"
                    try:
                        convertir_imagen(src, intermedio)
                    except Exception as e:  # Pillow/pillow-heif ausente, imagen corrupta...
                        cobertura.append(DocCobertura(
                            d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False,
                            f"conversión a PDF falló: {e}", d.sha256))
                        continue
                    cobertura.extend(_ocr_y_extraer(case_dir, sm_dir, case_id, d, intermedio, vision, force))
            elif d.ruta == "ofimatica":
                cobertura.extend(_ofimatica_y_extraer(case_dir, sm_dir, case_id, d, src, vision, force))
            elif d.ruta == "nativo":
                texto = _extraer_nativo(src, d.ext) or ""
                estado, nota = ocr_quality(texto, None)
                _escribir_md(case_dir, case_id, d.slug, d.rel_path, texto, "nativo", False, estado)
                cobertura.append(DocCobertura(d.slug, d.rel_path, "nativo", estado, len(texto), False, nota, d.sha256))
            else:
                cobertura.append(DocCobertura(d.slug, d.rel_path, "sin_soporte", "sin_soporte", 0, False, "sin soporte para esta extensión", d.sha256))
        except Exception as e:  # cualquier fallo del documento: no tumbar el lote
            cobertura.append(DocCobertura(d.slug, d.rel_path, "error", "empty", 0, False, f"fallo al procesar: {e}", d.sha256))
        finally:
            # `finally` y no al final del `try`: un documento que revienta también
            # cuesta tiempo, y es justo el que interesa medir (el que se reintenta).
            if on_documento is not None:
                ms = int((time.perf_counter() - _t0) * 1000)
                on_documento(d, ms, cobertura[_n_antes:])
    return cobertura


def _es_control(rel: str) -> bool:
    """True si `rel` (ruta RELATIVA a `00_Input/`) es protocolo y NO documento del caso.

    Delega en el registro por UBICACIÓN (`core/intake_control.py`, MEJORAS #149). Hasta el
    2026-09-05 preguntaba por el basename contra `config.INTAKE_CONTROL_FILES` mas una
    copia local: lo declarado se excluia a cualquier profundidad (un adjunto homonimo
    desaparecia del inventario probatorio) y lo no declarado —`_intake_hashes.json`,
    `<lote>/_manifiesto.yaml`— salia en `_cobertura` como `sin_soporte` (medido en
    W-02JSVZ). Cubre los temporales de escritura atomica de la raiz: un huerfano de
    `mkstemp` no puede acabar en el inventario de prueba porque el proceso muriera en mal
    momento.
    """
    from .intake_control import es_fichero_de_protocolo
    return es_fichero_de_protocolo(rel)


def inventariar(case_dir: Path) -> list[dict]:
    """Lista 00_Input/ (recursivo) con sha256 y ext. Ignora ficheros de control.

    NO excluye 90_Notas personales aquí (lo hace plan(), único punto de verdad),
    pero sí los ficheros de control del intake.

    Hashea TODO: es la forma correcta para un llamador sin estado (un script puntual,
    un test). Quien re-corra sobre el mismo caso debe usar
    :func:`inventariar_cacheado`, que es donde está el ahorro.
    """
    return inventariar_cacheado(case_dir, cache={})[0]


def inventariar_cacheado(case_dir: Path,
                         cache: dict[str, list]) -> tuple[list[dict], dict[str, list]]:
    """Como :func:`inventariar`, reutilizando el sha de los ficheros no tocados.

    `cache` mapea `rel_path -> [size, mtime_ns, sha256, ext]`. Se devuelve la caché
    **nueva**, ya podada de lo que no existe (sin poda, un caso grande la engorda sin
    techo a cada renombrado). No muta la que se le pasa.

    **Validez por `(size, mtime_ns)`, y falla al lado seguro.** Cualquier discrepancia
    —incluido un mtime que cambió sin que cambiara el contenido, que es lo que hace Drive
    for Desktop al rehidratar— provoca rehash: se paga el hash y sale el mismo sha. El
    error inverso (dar por bueno el sha porque el mtime no se movió cuando el contenido
    sí) sería corrupción de la cadena de custodia, y por eso la clave incluye el tamaño.

    **Por qué no se lee `00_Input/_intake_hashes.json`** (que es lo que sugería
    `MEJORAS #48`): el manifiesto M9 está indexado **sha → rutas**, no ruta → sha; no
    guarda `size` ni `mtime`, así que no hay con qué validar su hash; y está incompleto
    —`core/intake_drive.py` no registra en él—. Serviría para deduplicar, no para saber
    si el fichero de disco sigue siendo el que se hasheó.
    """
    root = Path(case_dir) / "00_Input"
    out: list[dict] = []
    nueva: dict[str, list] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if _es_control(rel):          # por ubicacion: `rel` se calcula ANTES de filtrar
            continue
        try:
            st = p.stat()
        except OSError:      # desapareció entre el rglob y el stat
            continue
        previa = cache.get(rel)
        if previa is not None and len(previa) == 4 \
                and previa[0] == st.st_size and previa[1] == st.st_mtime_ns:
            sha, ext = previa[2], previa[3]
        else:
            ext = p.suffix.lower()
            if clasificar_ruta(ext) == "sin_soporte":
                with p.open("rb") as fh:
                    head = fh.read(16)
                detectada = _sniff_ext_por_contenido(head)
                if detectada is not None:
                    ext = detectada
            sha = file_sha256(p)
        nueva[rel] = [st.st_size, st.st_mtime_ns, sha, ext]
        out.append({"rel_path": rel, "sha256": sha, "ext": ext})
    return out, nueva
