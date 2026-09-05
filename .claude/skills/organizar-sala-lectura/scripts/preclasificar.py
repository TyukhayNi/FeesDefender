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

import hashlib as _hashlib
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
_PREFIJO_FECHA_RE = _re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")
#: Centinela «sin fecha». Es una CADENA NO VACÍA a propósito —va en nombres canónicos y en
#: la columna `fecha` del manifiesto, y `email_export._fecha_iso` lo emite cuando la cabecera
#: `Date` falta—, así que es *truthy*: `if not fila["fecha"]` NUNCA detecta la ausencia.
#: Compara contra `SIN_FECHA` o usa `tiene_fecha` / `candidatos_sin_fecha` (MEJORAS #131:
#: un filtro con `not` dio 0 candidatos sobre 47 en W-02X1WJ y dejó sin ejecutar el paso
#: que consulta el espejo MD, en silencio y con apariencia de éxito).
SIN_FECHA = "0000-00-00"
_SIN_FECHA = SIN_FECHA   # alias interno histórico


# Nombre EXACTO del zip crudo que deposita whatsapp_intake.deposit_export
# (self-contained; el test test_nombre_export_crudo_sin_drift_con_core lo compara
# con la constante real core.whatsapp_intake._ORIGINAL_ZIP_NAME — sincronía a mano).
_NOMBRE_EXPORT_CRUDO_WHATSAPP = "_export_original.zip"


def emparejar_exports_whatsapp(rutas: list[str]) -> tuple[list[str], list[dict]]:
    """Separa los exports CRUDOS de WhatsApp de las rutas a clasificar. Un `.zip`
    es crudo SOLO si su basename es exactamente `_export_original.zip` (el que
    `whatsapp_intake.deposit_export` deja junto al `_chat.txt` extraído) Y en su
    MISMO directorio hay un `_chat.txt`: es el crudo del chat ya extraído y no
    debe tener fila propia (no tiene fecha ni espejo MD; darle una fabrica basura
    `0000-00-00`). Un `.zip` con OTRO nombre (documentación aportada) se conserva
    aunque comparta carpeta con un chat. Devuelve `(rutas_sin_crudos, crudos)`;
    cada crudo se anota `duplicado_de` su `_chat.txt` hermano (trazable, no
    borrado). Determinista, sin releer nada."""
    def _norm(r: str) -> str:
        return r.replace("\\", "/")

    def _dir(r: str) -> str:
        r = _norm(r)
        return r.rsplit("/", 1)[0] if "/" in r else ""

    def _base(r: str) -> str:
        return _norm(r).rsplit("/", 1)[-1].lower()

    chat_por_dir: dict[str, str] = {}
    for r in rutas:
        if _base(r) == "_chat.txt":
            chat_por_dir[_dir(r)] = r

    limpias: list[str] = []
    crudos: list[dict] = []
    for r in rutas:
        es_crudo = _base(r) == _NOMBRE_EXPORT_CRUDO_WHATSAPP
        hermano = chat_por_dir.get(_dir(r))
        if es_crudo and hermano:
            crudos.append({"ruta": r, "duplicado_de": hermano, "motivo": "export_crudo_whatsapp"})
        else:
            limpias.append(r)
    return limpias, crudos


def fecha_de_nombre(nombre: str) -> str:
    """Prefijo `AAAA-MM-DD` del nombre canónico de `email_export`, o `SIN_FECHA`
    (`0000-00-00`) si el nombre no lo lleva. NO valida que la fecha exista en el
    calendario: `0000-00-00` es un valor legítimo que emite `_fecha_iso` cuando la
    cabecera `Date` falta o no parsea.

    **El valor de «sin fecha» es una cadena no vacía y por tanto truthy.** Para saber
    si hay fecha usa `tiene_fecha(valor)`; para el Paso 1-bis.d de la skill usa
    `candidatos_sin_fecha(filas)`. No escribas `if not fecha` (MEJORAS #131).
    """
    base = nombre[:-4] if nombre.lower().endswith(".eml") else nombre
    m = _PREFIJO_FECHA_RE.match(base)
    return m.group(1) if m else SIN_FECHA


def tiene_fecha(valor: str | None) -> bool:
    """True si `valor` es un dato de fecha NO marcado como ausente ni incierto: no vacío,
    no `SIN_FECHA` (`0000-00-00`, también con sufijo) y sin la marca `(*)` de fecha
    aproximada que la skill escribe en el manifiesto. **No valida sintaxis ni calendario**
    (`2025-02-31` devuelve True, igual que `fecha_de_nombre` no lo valida): decide
    «¿hay una fecha cierta anotada?», no «¿es una fecha válida?». Es la forma de preguntar
    por la ausencia sin caer en la truthiness del centinela; la misma política, en negativo,
    la aplica `indices_desde_manifiesto._es_fecha_incierta`."""
    f = (valor or "").strip()
    return bool(f) and not f.startswith(SIN_FECHA) and "(*)" not in f


def candidatos_sin_fecha(filas: list[dict]) -> list[dict]:
    """Las filas que el Paso 1-bis.d de la skill debe consultar contra el espejo MD:
    binarios opacos (`_EXT_OPACAS`: PDF, imágenes incluida HEIF, hojas de cálculo, vídeo y
    algunos audios) cuya `fecha` no es cierta (`tiene_fecha`). Devuelve las filas mismas
    (no copias), en el orden recibido, para que quien las rellene lo haga en sitio.

    Acepta las filas de CUALQUIER etapa de la skill: las del Paso 1 (`ruta`, `nombre`,
    `sha256`), las del plan/manifiesto (`ruta_original`, `nombre_canonico`) y las de
    `layout_bundle_hilo` (`nombre_origen`). Una fila **sin ninguna** de esas claves lanza
    `ValueError`, y una tupla `(categoria, motivo)` de `clasificar_por_patron` lanza
    `TypeError`: quedarse callado y devolver 0 candidatos es exactamente el defecto de
    W-02X1WJ (MEJORAS #131; R1/H-01 lo reprodujo con el esquema del Paso 1).

    Existe porque el filtro escrito a mano en esa sesión —`not f["fecha"]`— devolvió 0
    candidatos de 47 y desactivó el paso en silencio. La pregunta vive aquí y la skill la
    llama en vez de reescribirla."""
    return [f for f in filas
            if _es_binario_opaco(f, estricto=True) and not tiene_fecha(f.get("fecha"))]


def _descripcion_hilo(nombre: str) -> str:
    """Descripción del nombre, SIN el prefijo de fecha y sin la extensión.
    `2025-03-20_oferta_calle_x.eml` -> `oferta_calle_x`."""
    base = nombre[:-4] if nombre.lower().endswith(".eml") else nombre
    m = _PREFIJO_FECHA_RE.match(base)
    return m.group(2) if m else base


def agrupar_por_hilo(rutas_eml: list[str]) -> dict[str, list[str]]:
    """Agrupa nombres de `.eml` por HILO. La clave es la **descripción** del
    nombre, IGNORANDO el prefijo de fecha: `core.email_export._slug_descripcion`
    ya elimina los prefijos `Re:`/`RV:`/`Fwd:` del asunto, así que todos los
    mensajes de un hilo comparten descripción y solo difieren en la fecha
    (`eml_filename` usa la fecha del propio mensaje). Agrupar por descripción es,
    por tanto, agrupar el hilo sin leer una sola cabecera RFC — gratis en los tres
    modos de acceso de la skill.

    Se conserva la protección del ítem 11 del backlog, ahora sobre descripciones:
    un `_N` final solo se recorta si la descripción sin ese sufijo existe DE VERDAD
    en el conjunto, así que una cifra del propio asunto
    (`oferta_vivienda_1_990_000`) no fabrica un hilo inexistente.

    Devuelve `{descripcion_hilo: [nombres_del_grupo]}`. Se clasifica un
    representante y su categoría se propaga al resto sin releerlos.

    LIMITACIONES (deliberadas, ver spec 2026-07-23 §5): un hilo cuyo ASUNTO cambió
    a mitad de conversación no se agrupa, y dos conversaciones distintas con el
    mismo asunto SÍ comparten grupo (sin guarda por salto temporal — decisión de
    Nikolai 2026-07-26). El threading riguroso por `References`/`In-Reply-To` es
    `MEJORAS #86`, no un prerrequisito."""
    descripciones = {_descripcion_hilo(n) for n in rutas_eml}
    grupos: dict[str, list[str]] = {}
    for nombre in rutas_eml:
        desc = _descripcion_hilo(nombre)
        m = _SUFIJO_HILO_RE.match(desc)
        clave = m.group(1) if (m and m.group(1) in descripciones) else desc
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
#: Extensiones «opacas» (sin texto propio: hay que leer el espejo MD o el binario). Las de
#: IMAGEN se mantienen alineadas con `core.sala_maquina._EXTS_IMAGEN` por un guard
#: (`test_131_las_imagenes_opacas_son_las_que_la_sala_de_maquina_convierte`): la R1 de
#: MEJORAS #131 midió que faltaba `heif`, que el repo sí convierte (`core/anon/imagen_a_pdf`).
_EXT_OPACAS = {
    "pdf", "jpg", "jpeg", "png", "gif", "tif", "tiff", "bmp", "heic", "heif", "webp",
    "xlsx", "xls", "mp4", "mov", "avi", "mkv", "m4a", "ogg", "opus",
}

#: Claves con las que una fila puede nombrar su fichero, según la etapa de la skill:
#: `nombre_canonico`/`ruta_original` (plan y manifiesto), `ruta`/`nombre` (la lista del
#: Paso 1 y las filas de `dedup_por_sha`), `nombre_origen` (`layout_bundle_hilo`).
_CLAVES_RUTA = ("nombre_canonico", "ruta_original", "ruta", "nombre", "nombre_origen")


def _ext(nombre: str) -> str:
    nombre = (nombre or "").rsplit("/", 1)[-1]
    return nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""


def _ruta_de_fila(fila: dict, *, estricto: bool) -> str:
    """El nombre/ruta con el que la fila identifica su fichero, sea de la etapa que sea.
    Con `estricto=True` una fila que no lleve NINGUNA clave conocida lanza `ValueError` en
    vez de tratarse en silencio como «no opaco» (R1/H-01 de MEJORAS #131: las filas del
    Paso 1 llevan `ruta`/`nombre`, no `ruta_original`, y el helper devolvía 0 candidatos)."""
    if not isinstance(fila, dict):
        raise TypeError(
            f"se esperaba una fila (dict) y llegó {type(fila).__name__}: `clasificar_por_patron` "
            "devuelve (categoria, motivo), no una fila — ensambla el dict antes")
    for k in _CLAVES_RUTA:
        v = fila.get(k)
        if v:
            return str(v)
    if estricto:
        raise ValueError(
            "fila sin ruta ni nombre (claves aceptadas: " + ", ".join(_CLAVES_RUTA) + "): no "
            f"se puede decidir si es binario opaco; claves presentes: {sorted(fila)}")
    return ""


def _es_binario_opaco(fila: dict, *, estricto: bool = False) -> bool:
    return _ext(_ruta_de_fila(fila, estricto=estricto)) in _EXT_OPACAS


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


def _hash_origen(nombre: str) -> str:
    """Discriminante corto y ESTABLE derivado solo del nombre de origen. Se usa en
    los anexos de un bundle para que su nombre canónico no dependa de su posición
    en el grupo: con un índice posicional, un mensaje que llegase después pero
    ordenase antes se llevaba el `_anexo_1` de otro YA COPIADO y lo sobrescribía."""
    return _hashlib.sha256(nombre.encode("utf-8")).hexdigest()[:6]


def layout_bundle_hilo(
    grupo: list[str],
    descripcion: str,
    *,
    con_adjuntos: frozenset[str] = frozenset(),
    carpeta_existente: str | None = None,
    plano_existente: bool = False,
) -> list[dict]:
    """Decide la FORMA DE COPIA de un grupo de hilo devuelto por
    :func:`agrupar_por_hilo`. Determinista y sin E/S: solo nombres y fechas.

    Reglas (spec 2026-07-23 §2.1/§2.3):
    - Bundle (subcarpeta fechada) si el grupo tiene ≥2 mensajes O alguno lleva
      adjuntos MIME; un mensaje solo y sin adjuntos queda PLANO (evita cientos de
      carpetas de un fichero).
    - El principal es el mensaje de fecha CIERTA más antigua; los `0000-00-00`
      nunca son principal salvo que TODO el grupo sea incierto (lo incierto va al
      final, misma convención que el índice). Empate -> orden alfabético.
    - **El nombre de cada anexo es función PURA de su propio fichero de origen**
      (su fecha + la descripción aprobada + `_hash_origen`), nunca de su posición
      en el grupo: añadir un mensaje no renumera ni pisa nada. `orden` sí es
      posicional, pero es metadato del manifiesto, no un nombre de fichero.
    - `parent_id` de un anexo = nombre PELADO de la carpeta.
    - `carpeta_existente`, si se pasa, se usa VERBATIM (el nombre del bundle se
      fija en la primera corrida y no se renombra nunca). Si NINGÚN miembro del
      grupo casa con la fecha de esa carpeta, el principal ya copiado no está en
      el grupo: entonces **nadie** recibe el rol de principal y todas las filas
      son anexos — adjudicarlo daría a un mensaje nuevo la ruta del principal ya
      copiado, sobrescribiéndolo.
    - `plano_existente=True` (el hilo ya se materializó PLANO en una corrida
      anterior): NO se abre carpeta. Si no, el bundle nacería sin principal dentro
      (el original se salta por sha y sigue fuera) y el hilo quedaría partido en
      dos sitios, con el anexo apareciendo como huérfano en el índice.

    `descripcion` llega ya aprobada (≤50 car., minúsculas, guiones bajos, sin
    PII): esta función no la deriva ni la sanea. Los nombres de origen se usan como
    llave, así que **deben ser únicos**: si se repiten, aborta (`ValueError`) en
    vez de perder un mensaje en silencio — dos lotes distintos pueden traer el
    mismo basename con sha distinto, porque `_ruta_unica` solo desambigua dentro
    de su propio lote.

    NO emite los adjuntos MIME de los mensajes: los nombra el procedimiento del
    `SKILL.md` con la misma regla (fecha propia + descripción + discriminante de su
    origen), bajo el mismo `parent_id`.
    """
    if len(set(grupo)) != len(grupo):
        repetidos = sorted({n for n in grupo if grupo.count(n) > 1})
        raise ValueError(
            "nombres de origen repetidos en el grupo de hilo "
            f"{repetidos!r}: no se puede resolver su fichero de origen ni darles "
            "nombre canónico distinto. Desambigua antes de llamar (p. ej. por lote).")

    def _clave(nombre: str):
        f = fecha_de_nombre(nombre)
        return (1 if f == _SIN_FECHA else 0, f, nombre)

    ordenados = sorted(grupo, key=_clave)
    if not ordenados:
        return []

    def _fila(nombre: str, *, rol: str, nombre_canonico: str, parent_id: str, orden: int) -> dict:
        return {
            "nombre_origen": nombre,
            "fecha": fecha_de_nombre(nombre),
            "rol": rol,
            "nombre_canonico": nombre_canonico,
            "parent_id": parent_id,
            "orden": orden,
        }

    if plano_existente:
        return [
            _fila(n, rol="principal", parent_id="", orden=i,
                  nombre_canonico=f"{fecha_de_nombre(n)}_{descripcion}_{_hash_origen(n)}.eml")
            for i, n in enumerate(ordenados)
        ]

    es_bundle = len(ordenados) >= 2 or any(n in con_adjuntos for n in ordenados)
    if not es_bundle:
        n = ordenados[0]
        return [_fila(n, rol="principal", parent_id="", orden=0,
                      nombre_canonico=f"{fecha_de_nombre(n)}_{descripcion}.eml")]

    if carpeta_existente:
        carpeta = carpeta_existente
        fecha_carpeta = fecha_de_nombre(carpeta_existente)
        candidatos = [n for n in ordenados if fecha_de_nombre(n) == fecha_carpeta]
        principal = candidatos[0] if candidatos else None
    else:
        principal = ordenados[0]
        carpeta = f"{fecha_de_nombre(principal)}_{descripcion}"

    filas: list[dict] = []
    orden = 0
    if principal is not None:
        filas.append(_fila(principal, rol="principal", parent_id="", orden=0,
                           nombre_canonico=f"{carpeta}/{carpeta}.eml"))
        orden = 1
    for n in ordenados:
        if n is principal or n == principal:
            continue
        fecha = fecha_de_nombre(n)
        filas.append(_fila(
            n, rol="anexo", parent_id=carpeta, orden=orden,
            nombre_canonico=f"{carpeta}/{fecha}_{descripcion}_{_hash_origen(n)}.eml"))
        orden += 1
    return filas
