"""Pre-clasifica documentos por patrón de nombre + dedup por sha256 + agrupación
por hilo de email, ANTES de que el LLM lea contenido. Determinista, idempotente.
Self-contained (corre en Cowork sin `core/`) — mismo patrón que
`manifiesto_a_catalogo.py`.

Diseño invertido (sesión 2026-07-21, caso W-02VUDR): en un expediente de honorarios
ya judicializado, "07. RECLAMACIONES" es el DEFAULT — la mayoría de los documentos
no son ni activación ni ofertas ni arras ni facturación ni PBC ni fotos, y forzarlos
a demostrar "07" leyendo contenido es gasto sin retorno. Los 6 patrones estrechos
(00/01/03/04/05/06) son los que de verdad discriminan; lo que no casa con ninguno
cae en "07" sin necesidad de confirmarlo, EXCEPTO los bundles conversacionales
(WhatsApp) donde la categoría depende de qué PARTE es — eso sigue necesitando
juicio real y va a "08. PENDIENTE DE CLASIFICAR" si no se puede determinar.

El test anti-drift `tests/test_preclasificar_sala_lectura.py::test_categorias_sin_drift`
compara `_CATEGORIAS` contra `core.config.TAXONOMIA_EV` — mantener ambos en sincronía a mano.
"""
from __future__ import annotations

import json
import re as _re
from pathlib import Path

re = _re  # Backward compatibility for existing code

_CATEGORIAS = (
    "00. FOTOS", "01. ACTIVACIÓN", "03. OFERTAS", "04. ARRAS - ARRENDAMIENTOS",
    "05. FACTURACIÓN - FINANZAS", "06. PBC", "07. RECLAMACIONES",
    "08. PENDIENTE DE CLASIFICAR",
)
_DEFAULT = "07. RECLAMACIONES"
_PENDIENTE = "08. PENDIENTE DE CLASIFICAR"

# Los 6 patrones ESTRECHOS que de verdad discriminan. SIN `^` — el nombre puede
# llevar prefijo de fecha ("AAAA-MM-DD_..."); `.search` busca el token en
# cualquier posición, no solo al principio.
_PATRONES: tuple[tuple[re.Pattern, str, str], ...] = (
    (re.compile(r"screenshot|captura", re.I), "00. FOTOS", "captura_foto"),
    (re.compile(r"doc_\d+_encargo", re.I), "01. ACTIVACIÓN", "doc_NN_encargo"),
    (re.compile(
        r"doc_\d+_(nota_simple|dni)|nota[ _]simple|datos[ _]catastro|"
        r"consulta[ _]descriptiva|ficha[ _](propiedad|propietario)", re.I),
     "01. ACTIVACIÓN", "activacion_vendedor"),
    (re.compile(
        r"doc_\d+_(oferta|comunicacion_oferta|hoja_de_visita)|\boferta\b|"
        r"hoja[ _]de[ _]visita|ficha[ _]comprador", re.I),
     "03. OFERTAS", "oferta_comprador"),
    (re.compile(r"doc_\d+_justificante_reserva|\barras\b", re.I),
     "04. ARRAS - ARRENDAMIENTOS", "arras"),
    (re.compile(r"^(fra|factura)[ _]|\bminuta\b|tasacion_costas|provis(ion)?_fondos", re.I),
     "05. FACTURACIÓN - FINANZAS", "factura_minuta"),
    (re.compile(r"anexo[s]?[ _]?[12][^0-9]", re.I), "06. PBC", "anexo_pbc_1_2"),
)


def clasificar_por_patron(nombre: str, *, es_bundle_conversacional: bool = False) -> tuple[str, str]:
    """SIEMPRE devuelve `(categoria, motivo)` — nunca `None`. Prueba los 6
    patrones estrechos primero; si ninguno casa y `es_bundle_conversacional` es
    `True` (WhatsApp — la categoría depende de qué parte es, no del nombre),
    cae a "08. PENDIENTE DE CLASIFICAR"; si no, cae a "07. RECLAMACIONES" por
    defecto (es el caso normal en un expediente ya judicializado)."""
    for patron, categoria, etiqueta in _PATRONES:
        if patron.search(nombre):
            return categoria, etiqueta
    if es_bundle_conversacional:
        return _PENDIENTE, "requiere_identificar_parte"
    return _DEFAULT, "default_reclamaciones"


def dedup_por_sha(ficheros: list[dict]) -> tuple[list[dict], list[dict]]:
    """Agrupa `ficheros` (`{"ruta", "sha256"}`) por sha256; el primero visto por
    cada hash es el único, el resto son duplicados con `duplicado_de` apuntando
    a la ruta del único. Preserva el orden de entrada."""
    vistos: dict[str, str] = {}
    unicos: list[dict] = []
    duplicados: list[dict] = []
    for f in ficheros:
        sha = f["sha256"]
        if sha not in vistos:
            vistos[sha] = f["ruta"]
            unicos.append(f)
        else:
            duplicados.append({**f, "duplicado_de": vistos[sha]})
    return unicos, duplicados


_SUFIJO_HILO_RE = re.compile(r"^(.*)_(\d+)$")


def agrupar_por_hilo(rutas_eml: list[str]) -> dict[str, list[str]]:
    """Agrupa nombres de `.eml` por HILO: el motor de export
    (`core.email_export`) numera con sufijo `_N` los mensajes de mismo
    asunto+fecha exportados en la misma corrida. La clave de hilo es el nombre
    sin ese sufijo. Devuelve `{clave_hilo: [nombres_del_grupo]}` — clasifica
    solo un representante del grupo (p. ej. el más corto/sin sufijo) y propaga
    su categoría al resto sin volver a leerlos. Heurística de nombre, no de
    `Message-ID`/`References` reales — proxy barato, no sustituto de un
    threading riguroso si algún día hace falta."""
    grupos: dict[str, list[str]] = {}
    for nombre in rutas_eml:
        base = nombre[:-4] if nombre.lower().endswith(".eml") else nombre
        m = _SUFIJO_HILO_RE.match(base)
        clave = m.group(1) if m else base
        grupos.setdefault(clave, []).append(nombre)
    return grupos


def subcategoria_crm(ruta: str) -> str | None:
    """Extrae la subcarpeta del Gestor Documental CRM
    (`sudespacho_<id>/<subcarpeta>/...`) como etiqueta secundaria — GRATIS (ya
    está en la ruta, cero lectura). `None` si la ruta no viene de un
    expediente CRM. Uso: sub-agrupar "07. RECLAMACIONES" en el `INDICE.md` sin
    coste de clasificación adicional."""
    m = re.search(r"sudespacho_\d+/([a-z_]+)/", ruta.replace("\\", "/"), re.I)
    return m.group(1) if m else None


def texto_espejo_md(sm_dir: Path, sha256_origen: str) -> str | None:
    """Busca en `_cobertura.json` de `sm_dir` (02_Sala de máquina) la fila cuyo
    `parent_sha256` (o `sha256` si no hay split) sea `sha256_origen` y estado sea
    ok/low, y devuelve el CUERPO (sin frontmatter) de su `03_MD/{slug}.md`.
    `None` si no hay cobertura, no hay match, o el estado es empty/sin_soporte
    (no hay texto útil que ofrecer)."""
    cobertura_path = Path(sm_dir) / "_cobertura.json"
    if not cobertura_path.exists():
        return None
    filas = json.loads(cobertura_path.read_text(encoding="utf-8"))
    for fila in filas:
        origen = fila.get("parent_sha256") or fila.get("sha256")
        if origen == sha256_origen and fila.get("estado") in ("ok", "low"):
            md_path = Path(sm_dir) / "03_MD" / f"{fila['slug']}.md"
            if not md_path.exists():
                return None
            texto = md_path.read_text(encoding="utf-8")
            return _re.sub(r"^---.*?---\n", "", texto, count=1, flags=_re.DOTALL)
    return None


_WCODE_RE = re.compile(r"W-[0-9A-Z]{5,6}", re.I)
_EXT_OPACAS = {
    "pdf", "jpg", "jpeg", "png", "gif", "tif", "tiff", "bmp", "heic", "webp",
    "xlsx", "xls", "mp4", "mov", "avi", "mkv", "m4a", "ogg", "opus",
}


def _ext(nombre: str) -> str:
    nombre = (nombre or "").rsplit("/", 1)[-1]
    return nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""


def _es_binario_opaco(fila: dict) -> bool:
    return _ext(fila.get("nombre_canonico") or fila.get("ruta_original") or "") in _EXT_OPACAS


def senales_gate(
    filas: list[dict],
    wcode_caso: str,
    cobertura_filas: list[dict] | None = None,
) -> list[str]:
    """Señales deterministas para el gate condicional (Paso 2.5). Lista VACÍA →
    auto-aprueba (sin anomalías); NO vacía → presenta la propuesta y espera OK.
    `filas`: dicts con `ruta_original`, `nombre_canonico`, `sha256`, `motivo`
    (de `clasificar_por_patron`). `wcode_caso`: el W-code propio del caso (las
    señales saltan para cualquier OTRO). `cobertura_filas`: filas de
    `_cobertura.json` de sala de máquina para saber qué sha256 tienen espejo MD
    (None = no hay sala de máquina → todo binario opaco es señal)."""
    señales: list[str] = []
    propio = (wcode_caso or "").upper()

    # (a) W-code ajeno en nombre o ruta -> excluir, nunca copiar.
    for f in filas:
        texto = f"{f.get('ruta_original', '')} {f.get('nombre_canonico', '')}"
        for m in _WCODE_RE.findall(texto):
            if m.upper() != propio:
                ref = f.get("ruta_original") or f.get("nombre_canonico")
                señales.append(f"W-code ajeno {m!r} en {ref} — excluir, nunca copiar")

    # (b) mismo nombre de origen con sha256 distinto (casi-duplicado).
    por_nombre: dict[str, set[str]] = {}
    for f in filas:
        base = (f.get("ruta_original") or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
        if not base:
            continue
        por_nombre.setdefault(base, set()).add(f.get("sha256") or "")
    for base, shas in por_nombre.items():
        distintos = {s for s in shas if s}
        if len(distintos) > 1:
            señales.append(
                f"casi-duplicado: mismo nombre de origen {base!r} con {len(distintos)} sha256 distintos")

    # (c) binarios opacos sin espejo MD (cruzando por parent_sha256 or sha256).
    con_espejo: set[str] = set()
    for c in (cobertura_filas or []):
        if c.get("estado") in ("ok", "low"):
            con_espejo.add(c.get("parent_sha256") or c.get("sha256"))
    for f in filas:
        if _es_binario_opaco(f) and (f.get("sha256") not in con_espejo):
            ref = f.get("nombre_canonico") or f.get("ruta_original")
            señales.append(f"binario opaco sin espejo MD: {ref} — clasificado a ciegas por nombre")

    # (d) pass-through de requiere_identificar_parte (bundle sin parte).
    for f in filas:
        if f.get("motivo") == "requiere_identificar_parte":
            ref = f.get("nombre_canonico") or f.get("ruta_original")
            señales.append(f"bundle conversacional sin parte identificable: {ref} — requiere_identificar_parte")

    return señales
