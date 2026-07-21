# Pre-clasificación mecánica de la sala de lectura — Plan de implementación

> **Para workers agénticos:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para ejecutar este plan tarea por tarea.

**Objetivo:** reducir el tiempo de `organizar-sala-lectura` (14 min medidos en W-02VUDR) dando al ejecutor (LLM) atajos deterministas ANTES de pedirle juicio: patrón de nombre de fichero (con "07. RECLAMACIONES" como DEFAULT, no como algo que demostrar), agrupación de `.eml` por hilo, dedup por sha256, texto ya extraído en el espejo MD, y subcarpeta CRM como etiqueta secundaria gratis — dejando el razonamiento del modelo solo para lo genuinamente ambiguo (bundles conversacionales sin parte identificable).

**Arquitectura:** dos helpers Python **self-contained** (sin `import core`, corren en Cowork igual que `manifiesto_a_catalogo.py`) bajo `.claude/skills/organizar-sala-lectura/scripts/`, invocados por la skill como paso 1-bis antes de la clasificación por LLM. Test anti-drift contra `core.config.TAXONOMIA_EV`.

**Tech stack:** Python 3.11+ self-contained, `pytest`, sin dependencias nuevas.

**Historial de revisión (sesión 2026-07-21, caso W-02VUDR):**
1. Versión inicial: patrones anclados con `^` — bug real, no casaban con nombres que llevan prefijo de fecha (`2025-04-08_requerimiento_pago...eml`), o sea, no capturaban NINGÚN correo.
2. Corrección de diseño: en un expediente de honorarios ya judicializado, el 72% de los documentos (98/137 en W-02VUDR) cae en "07. RECLAMACIONES" — tratarlo como una categoría a demostrar (como las otras 7) es gasto sin retorno. Se invierte la lógica: 6 patrones ESTRECHOS para 00/01/03/04/05/06 (los que sí discriminan), "07" es el DEFAULT cuando ninguno casa, "08" solo para bundles conversacionales sin parte identificable.
3. Se añade agrupación de `.eml` por HILO (mismo asunto+fecha, sufijo `_N` del motor de export) — mayor palanca que el patrón de nombre para el bloque de email (57 de 137 documentos).
4. Se añade `subcategoria_crm` — la subcarpeta del Gestor Documental (`civil/demanda/documentos/preliminares/documentacion_rgpd_lopd`) como etiqueta secundaria GRATIS (ya está en la ruta) para no perder navegabilidad dentro del cajón plano de "07. RECLAMACIONES".
5. Medido en vivo (mismo caso): la fase de COPIA+ÍNDICES (Paso 4-7) tardó **más que la de clasificación** (30+ min vs 14 min) — copiar es barato server-side, pero son ~130 llamadas secuenciales, cada una con su turno de modelo por medio. Task 1-3 solo optimizan la clasificación; se añade Task 4 para paralelizar también la copia, o la mejora medida se quedaría corta.
6. **Task 4 rediseñada (SUPERSEDE la versión "paralelizar entre subagentes").** Probado en vivo: `rclone copyto` sí hace copia server-side (confirmado: `Copied (server-side copy)`), pero el cliente OAuth COMPARTIDO de rclone (`project_number:202264815644`, el mismo para todos los usuarios de rclone del mundo) tiene cuota de "Queries per minute" tan ajustada que una sola copia de 94 KB tardó 110s por 6 reintentos `403 Quota exceeded`. Paralelizar entre subagentes NO resuelve esto — cada uno competiría por la MISMA cuota, podría empeorarlo. La solución de raíz (verificada: levanté un `rclone rcd` real y confirmé que el endpoint RC `operations/copyfile` y su parámetro `srcRemote` existen tal cual) es: (a) client OAuth PROPIO del despacho en `rclone config` (prerrequisito manual, cuenta de Google Cloud de Nikolai — no automatizable desde aquí), y (b) UN solo proceso `rclone rcd` persistente que reciba las copias+renombrados vía su RC API en vez de lanzar `rclone.exe`/`copy_path` una vez por fichero — así el "pacer" interno no se reinicia en cada llamada.
7. **Fusión con `HANDOFF_sala-lectura.md`** (benchmark de Cowork contra `vassal-litigator`, mismo día): se incorporan 3 mejoras — (a) plan persistido a fichero ANTES del gate (Task 3, Paso 4) — resuelve además la dependencia oculta de Task 4 con una lista `(origen,destino)` durable; (b) el gate único SIEMPRE-obligatorio pasa a CONDICIONAL — solo aparece si hay anomalías genuinas (Task 3, Paso 4), porque medido en vivo el letrado aprobó 150 filas "tal cual" sin decidir él los puntos ambiguos — ceremonia sin aporte real cuando la clasificación sale limpia; (c) fase verify con criterios duros (Task 5) — dos discrepancias de conteo reales en W-02VUDR pasaron el reporte final sin que nada las cazara, esto las habría detectado solo. Los otros 9 invariantes del handoff (no destructivo, idempotencia por sha256, estructura plana, etc.) ya los cumplía la skill — confirmados, no tocados.

## Restricciones globales

- Self-contained: cero `import core.*` en los scripts bajo `.claude/skills/` (deben correr en Cowork sin el repo Python).
- Determinista e idempotente — mismo input, mismo output, siempre.
- El LLM nunca pierde la última palabra: `clasificar_por_patron` es una PROPUESTA de alta confianza para 00/01/03/04/05/06 y un DEFAULT razonable para 07 — no un veredicto irrevocable; el letrado puede corregir cualquier fila del `_MANIFIESTO.md`.
- Test anti-drift obligatorio para cualquier constante duplicada de `core/`.

---

### Task 1: Pre-clasificador (patrón + default 07 + hilo de email + dedup sha256 + subcategoría CRM)

**Ficheros:**
- Crear: `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py`
- Test: `tests/test_preclasificar_sala_lectura.py`

**Interfaces:**
- Produce: `clasificar_por_patron(nombre: str, *, es_bundle_conversacional: bool = False) -> tuple[str, str]` — SIEMPRE devuelve `(categoria, motivo)`, nunca `None`.
- Produce: `dedup_por_sha(ficheros: list[dict]) -> tuple[list[dict], list[dict]]`.
- Produce: `agrupar_por_hilo(rutas_eml: list[str]) -> dict[str, list[str]]`.
- Produce: `subcategoria_crm(ruta: str) -> str | None`.

- [ ] **Paso 1: Escribir el test que falla**

```python
# tests/test_preclasificar_sala_lectura.py
from importlib import import_module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
preclasificar = import_module("preclasificar")


def test_clasifica_encargo_por_patron():
    cat, motivo = preclasificar.clasificar_por_patron("doc_02_encargo_y_poderes.pdf")
    assert cat == "01. ACTIVACIÓN"
    assert motivo == "doc_NN_encargo"


def test_clasifica_factura_por_patron():
    cat, _ = preclasificar.clasificar_por_patron("FACTURA 158 - 25-11-2025 - EV MMC SPAIN.pdf")
    assert cat == "05. FACTURACIÓN - FINANZAS"


def test_prefijo_de_fecha_no_rompe_el_patron():
    # bug de la v1: el ^ no casaba con nombres con fecha delante
    cat, _ = preclasificar.clasificar_por_patron("2025-04-08_requerimiento_pago_honorarios_s_r_vars5.eml")
    assert cat == "07. RECLAMACIONES"  # cae al default, correcto — "requerimiento_pago" no es de los 6 patrones estrechos


def test_nombre_generico_cae_al_default_reclamaciones():
    cat, motivo = preclasificar.clasificar_por_patron("2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes.eml")
    assert cat == "07. RECLAMACIONES"
    assert motivo == "default_reclamaciones"


def test_bundle_conversacional_sin_patron_va_a_pendiente():
    cat, motivo = preclasificar.clasificar_por_patron(
        "Chat de WhatsApp con Projecto Denia Aldebaran", es_bundle_conversacional=True)
    assert cat == "08. PENDIENTE DE CLASIFICAR"
    assert motivo == "requiere_identificar_parte"


def test_captura_screenshot_va_a_fotos():
    cat, _ = preclasificar.clasificar_por_patron("Screenshot_20250331_124123_WhatsAppBusiness.jpg")
    assert cat == "00. FOTOS"


def test_dedup_por_sha_agrupa_y_reporta_duplicados():
    ficheros = [
        {"ruta": "sudespacho_499/demanda/doc_02_encargo_y_poderes.pdf", "sha256": "aaa"},
        {"ruta": "sudespacho_602/demanda/doc_02_encargo_y_poderes.pdf", "sha256": "aaa"},
        {"ruta": "sudespacho_603/demanda/doc_02_encargo_y_poderes.pdf", "sha256": "aaa"},
        {"ruta": "01_Drive EV/OFERTA.PDF", "sha256": "bbb"},
    ]
    unicos, duplicados = preclasificar.dedup_por_sha(ficheros)
    assert len(unicos) == 2
    assert len(duplicados) == 2
    assert duplicados[0]["duplicado_de"] == "sudespacho_499/demanda/doc_02_encargo_y_poderes.pdf"


def test_agrupar_por_hilo_junta_variantes_del_mismo_dia_y_asunto():
    nombres = [
        "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes.eml",
        "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes_2.eml",
        "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes_3.eml",
        "2025-04-22_ubicacion_propietario_tonet.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert len(grupos) == 2
    clave_consulta = "2025-03-20_consulta_de_procedimiento_en_el_caso_salto_de_clientes"
    assert len(grupos[clave_consulta]) == 3


def test_subcategoria_crm_extrae_la_subcarpeta():
    assert preclasificar.subcategoria_crm("sudespacho_602/civil/auto_inadmite_diligencias_preliminares.pdf") == "civil"
    assert preclasificar.subcategoria_crm("01_Drive EV/OFERTA.PDF") is None
```

- [ ] **Paso 2: Confirmar que falla**

Run: `python -m pytest tests/test_preclasificar_sala_lectura.py -v`
Expected: `ModuleNotFoundError` (el módulo no existe todavía).

- [ ] **Paso 3: Implementación mínima**

```python
# .claude/skills/organizar-sala-lectura/scripts/preclasificar.py
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

import re

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
```

- [ ] **Paso 4: Confirmar que pasa**

Run: `python -m pytest tests/test_preclasificar_sala_lectura.py -v`
Expected: `9 passed`

- [ ] **Paso 5: Test anti-drift + commit**

```python
# añadir a tests/test_preclasificar_sala_lectura.py
def test_categorias_sin_drift():
    from core.config import TAXONOMIA_EV
    assert set(preclasificar._CATEGORIAS) == set(TAXONOMIA_EV)
```

```bash
git add .claude/skills/organizar-sala-lectura/scripts/preclasificar.py tests/test_preclasificar_sala_lectura.py
git commit -m "feat(sala-lectura): preclasificador con 07 por defecto, hilo de email, dedup sha256 y subcategoria CRM"
```

---

### Task 2: Lookup del espejo MD (texto ya extraído por sala de máquina)

**Ficheros:**
- Modificar: `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py`
- Test: `tests/test_preclasificar_sala_lectura.py`

**Interfaces:**
- Consume: `_cobertura.json` de `01_Procesado/02_Sala de máquina/` (campos `sha256`, `parent_sha256`, `slug`, `estado` — mismo esquema que `core.sala_maquina.DocCobertura`).
- Produce: `texto_espejo_md(sm_dir: Path, sha256_origen: str) -> str | None`.

- [ ] **Paso 1: Escribir el test que falla**

```python
def test_texto_espejo_md_encuentra_por_parent_sha256(tmp_path):
    sm_dir = tmp_path / "02_Sala de máquina"
    (sm_dir / "03_MD").mkdir(parents=True)
    (sm_dir / "03_MD" / "hoja_visita__a1b2c3d4.md").write_text(
        "---\nchars: 120\n---\nHoja de visita firmada el 31 de marzo de 2025.", encoding="utf-8")
    import json
    (sm_dir / "_cobertura.json").write_text(json.dumps([
        {"slug": "hoja_visita__a1b2c3d4", "sha256": "a1b2c3d4", "parent_sha256": "origen_sha_xyz", "estado": "ok"},
    ]), encoding="utf-8")
    texto = preclasificar.texto_espejo_md(sm_dir, "origen_sha_xyz")
    assert "31 de marzo de 2025" in texto


def test_texto_espejo_md_none_si_no_hay_cobertura(tmp_path):
    assert preclasificar.texto_espejo_md(tmp_path / "no_existe", "cualquier_sha") is None


def test_texto_espejo_md_none_si_estado_vacio(tmp_path):
    sm_dir = tmp_path / "02_Sala de máquina"
    sm_dir.mkdir()
    import json
    (sm_dir / "_cobertura.json").write_text(json.dumps([
        {"slug": "x__y", "sha256": "s1", "parent_sha256": "origen", "estado": "empty"},
    ]), encoding="utf-8")
    assert preclasificar.texto_espejo_md(sm_dir, "origen") is None
```

- [ ] **Paso 2: Confirmar que falla**

Run: `python -m pytest tests/test_preclasificar_sala_lectura.py -v -k espejo_md`
Expected: `AttributeError: module 'preclasificar' has no attribute 'texto_espejo_md'`

- [ ] **Paso 3: Implementación mínima**

```python
# añadir a .claude/skills/organizar-sala-lectura/scripts/preclasificar.py
import json
import re as _re
from pathlib import Path


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
```

- [ ] **Paso 4: Confirmar que pasa**

Run: `python -m pytest tests/test_preclasificar_sala_lectura.py -v`
Expected: `12 passed`

- [ ] **Paso 5: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/scripts/preclasificar.py tests/test_preclasificar_sala_lectura.py
git commit -m "feat(sala-lectura): lookup del espejo MD de sala de maquina para clasificar binarios"
```

---

### Task 3: Enganchar los helpers en el procedimiento de la skill

**Ficheros:**
- Modificar: `.claude/skills/organizar-sala-lectura/SKILL.md`

**Interfaces:**
- Consume: `clasificar_por_patron`, `dedup_por_sha`, `agrupar_por_hilo`, `subcategoria_crm`, `texto_espejo_md` (Task 1-2).

- [ ] **Paso 1: Insertar un Paso 1-bis en el procedimiento**, justo después del actual Paso 1 ("Lista TODO `00_Input/`... calcula sha256..."):

```markdown
1-bis. **Pre-clasifica mecánicamente antes de leer contenido.** Con la lista de
   `(ruta, sha256, nombre)` del Paso 1:
   a. `dedup_por_sha(ficheros)` → clasifica UNA sola vez cada sha256 único; los
      duplicados se anotan en el `_MANIFIESTO.md` como "duplicado, saltado" sin
      volver a leerlos.
   b. `agrupar_por_hilo(rutas_eml)` sobre los `.eml` únicos → clasifica solo un
      representante por hilo (el nombre sin sufijo `_N`) y propaga su categoría
      al resto del grupo sin volver a leerlos.
   c. `clasificar_por_patron(nombre, es_bundle_conversacional=...)` sobre cada
      único/representante restante → SIEMPRE devuelve una categoría (00-06 por
      patrón estrecho, 07 por defecto, u 08 si es un bundle de WhatsApp sin
      patrón). Pásalo por alto (verifica leyendo) solo cuando el motivo sea
      `default_reclamaciones` y el documento sea inusual o el letrado lo pida
      — no hace falta confirmar 07 sistemáticamente.
   d. Para los binarios opacos (PDF escaneado, imagen) que SÍ necesiten lectura
      real (bundles conversacionales, o para poner fecha real en vez de
      `0000-00-00`): prueba `texto_espejo_md(sm_dir, sha256)` — si
      `01_Procesado/02_Sala de máquina/` ya tiene el texto OCR, úsalo en vez de
      leer el binario o rendirte a `(*)`.
   e. `subcategoria_crm(ruta)` sobre cada documento con categoría "07.
      RECLAMACIONES" → si devuelve subcarpeta (`civil`/`demanda`/`documentos`/
      `preliminares`/`documentacion_rgpd_lopd`), guárdala en el
      `_MANIFIESTO.md` como columna informativa para sub-agrupar el `INDICE.md`
      dentro de "07. RECLAMACIONES" (ver Paso 5 actualizado abajo) — gratis,
      sin coste de clasificación.
   Si `01_Procesado/02_Sala de máquina/` no existe todavía, salta (d) y sigue
   igual — no es bloqueante, solo una ganancia si ya se corrió `organizar-sala-maquina`.
```

- [ ] **Paso 2: Actualizar el Paso 5 (índices) para sub-agrupar "07. RECLAMACIONES"**

```markdown
   - `INDICE.md` — agrupado por categoría, orden fecha DESCENDENTE. **Dentro de
     "07. RECLAMACIONES"**, si la mayoría de sus documentos tienen
     `subcategoria_crm` (Paso 1-bis.e), sub-agrupa por esa subcarpeta
     (`civil`/`demanda`/`documentos`/`preliminares`/`documentacion_rgpd_lopd`,
     y "correspondencia" para los `.eml` sin subcategoría CRM) antes de ordenar
     por fecha dentro de cada subgrupo — es la única categoría que lo necesita
     (concentra la mayoría de los documentos en expedientes judicializados).
```

- [ ] **Paso 3: Añadir gotcha de paralelización y checkout local**, en la sección "Gotchas":

```markdown
- **Casos grandes (>80 ficheros): reparte la clasificación por fuente en
  subagentes paralelos** (uno por `01_Drive EV`, uno por el lote de email, uno
  por cada expediente CRM) en vez de un único agente secuencial — el dedup por
  sha256 cruzado entre fuentes (Task 1) es la ÚNICA parte que necesita ver todo
  junto; hazla en un paso de fusión aparte, después de que cada subagente
  devuelva su clasificación local.
- **Caso en Drive con muchos ficheros fríos (no hidratados): considera
  `checkout-caso` a disco local antes de montar la sala.** `hash_tree`/
  `read_text` sobre `G:` paga latencia de red por fichero no cacheado; en local
  esa latencia desaparece. La copia server-side (`copy_path`/`cp`) es igual de
  eficiente en ambos sitios — la ganancia está en la LECTURA, no en la copia.
```

- [ ] **Paso 4: Persistir el plan antes del gate + invertir el gate (fusión con `HANDOFF_sala-lectura.md`, benchmark vs. `vassal-litigator`, 3.1)**

**Por qué:** hoy el gate (Paso 2.5) presenta la propuesta desde la MEMORIA de la conversación/agente — sin fichero, no hay forma de retomar una corrida interrumpida ni de que `Task 4` (copia vía `rclone rcd`) lea una lista `(origen, destino)` de un sitio durable en vez de memoria. Y medido en vivo en W-02VUDR: el letrado aprobó una propuesta de 150 filas "tal cual", sin decidir él los puntos ambiguos uno a uno — el gate SIEMPRE-obligatorio es más ceremonia que aporte real cuando la clasificación sale limpia.

Añadir al Paso 2 (antes del Paso 2.5 actual):

```markdown
2-bis. **Persiste la propuesta a fichero** en
   `01_Procesado/Sala lectura/_plan/plan-<AAAA-MM-DD-HHmm>.md` — la misma
   tabla que vas a mostrar en el Paso 2.5 (`sha256 | ruta_original |
   nombre_canonico | tipo | fecha | parte | parent_id` + categoría +
   `subcategoria_crm`), con cabecera `estado: propuesto`. Fuera de
   `Sala lectura/` propiamente dicha para que un re-pull o una re-corrida no
   lo pise ni lo reingiera (mismo motivo que "por qué la sala vive fuera de
   `00_Input`"). NO se borra tras ejecutar — pasa a `estado: ejecutado`
   (mismo razonamiento no-destructivo del resto de la skill).
```

Y reemplazar el Paso 2.5 actual (gate SIEMPRE) por un gate CONDICIONAL:

```markdown
2.5 (GATE — ahora condicional, no siempre). Si la propuesta NO tiene ninguna
   fila con motivo `requiere_identificar_parte` (bundle conversacional sin
   parte), ningún documento con W-code ajeno al caso, ningún casi-duplicado
   de hash distinto con mismo nombre, y ningún binario opaco SIN espejo MD
   disponible (ver Paso 3.3 más abajo) — **procede directo al Paso 4 sin
   esperar aprobación**, deja constancia en el plan persistido
   (`estado: auto-aprobado, sin anomalías`) para que quede trazado qué se
   decidió sin humano.
   Si SÍ hay alguna de esas señales, presenta la propuesta (tarjeta visual,
   como hasta ahora) y ESPERA — el gate sigue existiendo, pero solo cuando
   hay algo genuinamente ambiguo que decidir, no como trámite fijo.
```

- [ ] **Paso 5: Bandera visible de calidad de espejo en el gate (fusión 3.3 del handoff)**

Añadir a la lógica del Paso 1-bis.d (`texto_espejo_md`): si un binario opaco NO tiene espejo MD disponible (`01_Procesado/02_Sala de máquina/` no existe, o su fila en `_cobertura.json` no tiene `estado` ok/low), márcalo como señal para el gate condicional del Paso 4 arriba — es exactamente la categoría de "algo ambiguo" que debe forzar la aparición del gate, en vez de clasificarlo a ciegas por nombre y seguir en silencio.

- [ ] **Paso 6: Verificación manual** (no hay pytest para prosa de skill)

Ejecutar `organizar-sala-lectura` sobre un caso de prueba con: 3 documentos duplicados por sha256 entre carpetas distintas, 2 con nombre `doc_NN_*`/`FACTURA *`, 3 `.eml` del mismo hilo (mismo asunto, sufijo `_2`/`_3`), y 2 documentos de `sudespacho_NNN/civil/` sin patrón estrecho. Confirmar en el `_MANIFIESTO.md`/`INDICE.md` resultante que: (a) los duplicados aparecen una sola vez con nota "duplicado, saltado", (b) el hilo de 3 correos se clasifica una vez y se propaga, (c) los `doc_NN_*`/`FACTURA *` llevan la categoría del patrón sin lectura, (d) los 2 de `civil/` caen en "07. RECLAMACIONES" con `subcategoria_crm=civil` sin que el reporte diga haberlos leído, (e) sin anomalías → NO aparece el gate, el plan queda persistido con `estado: auto-aprobado, sin anomalías`.

- [ ] **Paso 7: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/SKILL.md
git commit -m "docs(sala-lectura): enganchar preclasificador (07 por defecto, hilo, subcategoria CRM), plan persistido, gate condicional, gotcha de paralelizacion y checkout local"
```

---

### Task 4 (v2 — SUPERSEDE la v1 "paralelizar entre subagentes"): copia+renombrado vía `rclone rcd`

**Disparador:** medido en W-02VUDR, la fase de copia+índices tardó más que la de clasificación (30+ min vs 14 min). La v1 de esta Task (repartir la copia entre subagentes) quedó descartada tras probar en real: `rclone copyto` SÍ hace copia server-side (confirmado: `Copied (server-side copy)`), pero el cliente OAuth **compartido** de rclone (`project_number:202264815644`, el mismo para todos los usuarios de rclone del mundo, no propio del despacho) tiene la cuota de "Queries per minute" tan saturada que una sola copia de 94 KB tardó **110s por 6 reintentos `403 Quota exceeded`**. Paralelizar entre subagentes no arregla esto — todos competirían por la MISMA cuota compartida, podría empeorarlo en vez de mejorarlo.

**Causa raíz (verificada, no solo por diagnóstico de terceros):** el "pacer" de rclone que gestiona el backoff de cuota vive en memoria del proceso — cada invocación nueva de `rclone.exe` lo reinicia desde cero. Levanté un `rclone rcd` (demonio persistente) real en esta sesión y confirmé que su RC API expone `operations/copyfile` con el parámetro `srcRemote` tal cual (`rclone rc operations/copyfile` sin argumentos devuelve `"Didn't find key \"srcRemote\" in input"` — el endpoint y el nombre de parámetro son reales, verificado por llamada directa, no por confianza en un LLM).

**PRERREQUISITO BLOQUEANTE — acción manual de Nikolai, no automatizable desde aquí:** configurar en `rclone config` un client OAuth **propio** del despacho (proyecto de Google Cloud propio, API de Drive habilitada, credenciales OAuth de escritorio) para el remote usado (`gdrive_tl`/`gdrive_ev`), en vez del cliente compartido por defecto de rclone. Sin esto, `rclone rcd` sigue compitiendo por la misma cuota global y el problema no desaparece, solo se reordena.

**Ficheros:**
- Crear: `.claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py`
- Test: `tests/test_copiar_manifiesto_rclone.py`
- Modificar: `.claude/skills/organizar-sala-lectura/SKILL.md` (Paso 4)

**Interfaces:**
- Consume: pares `(remote_relpath_origen, remote_relpath_destino)` derivados del `_MANIFIESTO.md` propuesto (Paso 3).
- Produce: `levantar_rcd_si_falta() -> subprocess.Popen | None`, `copiar_renombrar(remote, src_relpath, dst_relpath) -> dict`, `copiar_manifiesto(remote, pares) -> tuple[list[str], list[tuple[str, str]]]`.

- [ ] **Paso 1: Escribir el test que falla** (mockeando `urllib.request` — sin tocar rclone real ni red)

```python
# tests/test_copiar_manifiesto_rclone.py
from importlib import import_module
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
cmr = import_module("copiar_manifiesto_rclone")


def _mock_response(payload: bytes):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = payload
    return cm


def test_copiar_renombrar_envia_srcfs_srcremote_dstfs_dstremote():
    with patch("urllib.request.urlopen", return_value=_mock_response(b"{}")) as m:
        cmr.copiar_renombrar("gdrive_tl:", "a/origen.pdf", "b/destino.pdf")
        req = m.call_args[0][0]
        import json
        body = json.loads(req.data)
        assert body == {
            "srcFs": "gdrive_tl:", "srcRemote": "a/origen.pdf",
            "dstFs": "gdrive_tl:", "dstRemote": "b/destino.pdf",
        }


def test_copiar_manifiesto_no_aborta_si_uno_falla():
    def fake_urlopen(req, timeout=60):
        body = req.data.decode("utf-8")
        if "falla.pdf" in body:
            raise RuntimeError("500 error simulado")
        return _mock_response(b"{}")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ok, fallidos = cmr.copiar_manifiesto("gdrive_tl:", [
            ("a/ok1.pdf", "b/ok1.pdf"),
            ("a/falla.pdf", "b/falla.pdf"),
            ("a/ok2.pdf", "b/ok2.pdf"),
        ])
    assert ok == ["b/ok1.pdf", "b/ok2.pdf"]
    assert len(fallidos) == 1 and fallidos[0][0] == "b/falla.pdf"
```

- [ ] **Paso 2: Confirmar que falla**

Run: `python -m pytest tests/test_copiar_manifiesto_rclone.py -v`
Expected: `ModuleNotFoundError` (el módulo no existe todavía).

- [ ] **Paso 3: Implementación mínima**

```python
# .claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py
"""Copia+renombra en bloque vía `rclone rcd` (RC API), evitando el reinicio
del "pacer" de cuota que sufre `rclone.exe` invocado una vez por fichero
(sesión 2026-07-21, W-02VUDR: una sola copia server-side tardó 110s por 6
reintentos `403 Quota exceeded` del cliente OAuth COMPARTIDO de rclone).

PRERREQUISITO (bloqueante, manual): un client_id/client_secret OAuth PROPIO
del despacho configurado en `rclone config` para el remote usado — sin esto
este módulo solo reordena el problema, no lo resuelve (sigue compartiendo
cuota global).

Self-contained (stdlib únicamente, sin `requests` ni `core/`): habla con la
RC API de un `rclone rcd` ya levantado (o lo levanta como subproceso si no
detecta uno activo). Endpoint y parámetros verificados en vivo el
2026-07-21 contra rclone v1.73.5 — no son una suposición.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request

_RC_PORT = 15572
_RC_URL = f"http://localhost:{_RC_PORT}"


def _rc_activo() -> bool:
    try:
        urllib.request.urlopen(f"{_RC_URL}/core/pid", timeout=2)
        return True
    except Exception:
        return False


def levantar_rcd_si_falta() -> subprocess.Popen | None:
    """Arranca `rclone rcd` en background si no hay uno ya escuchando en
    `_RC_PORT`. Devuelve el `Popen` (para poder cerrarlo después) o `None` si
    ya había uno activo — no lo tocamos, puede ser de otra corrida."""
    if _rc_activo():
        return None
    proc = subprocess.Popen(
        ["rclone", "rcd", "--rc-no-auth", "--rc-addr", f"localhost:{_RC_PORT}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        if _rc_activo():
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("rclone rcd no respondió tras 10s")
    return proc


def copiar_renombrar(remote: str, src_relpath: str, dst_relpath: str) -> dict:
    """Una llamada `operations/copyfile` sobre el `rcd` ya levantado. `remote`
    es el nombre del remote rclone CON el `:` final (p. ej. `gdrive_tl:`);
    las rutas son relativas a ese remote. Lanza si rclone devuelve error — el
    llamador (`copiar_manifiesto`) decide si es fatal o solo esa fila."""
    body = json.dumps({
        "srcFs": remote, "srcRemote": src_relpath,
        "dstFs": remote, "dstRemote": dst_relpath,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{_RC_URL}/operations/copyfile", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def copiar_manifiesto(
    remote: str, pares: list[tuple[str, str]],
) -> tuple[list[str], list[tuple[str, str]]]:
    """`pares` = [(src_relpath, dst_relpath), ...] ya decididos por la
    clasificación (Paso 1-3 de la skill). Copia TODOS dentro del MISMO
    proceso `rcd` — el pacer se mantiene estable entre llamadas, a
    diferencia de invocar `rclone.exe` una vez por fichero. Devuelve
    `(ok, fallidos)`; un fallo individual NO aborta el resto."""
    ok: list[str] = []
    fallidos: list[tuple[str, str]] = []
    for src, dst in pares:
        try:
            copiar_renombrar(remote, src, dst)
            ok.append(dst)
        except Exception as exc:  # noqa: BLE001 — un fallo no aborta el resto
            fallidos.append((dst, str(exc)))
    return ok, fallidos
```

- [ ] **Paso 4: Confirmar que pasa**

Run: `python -m pytest tests/test_copiar_manifiesto_rclone.py -v`
Expected: `2 passed`

- [ ] **Paso 5: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py tests/test_copiar_manifiesto_rclone.py
git commit -m "feat(sala-lectura): copia+renombrado en bloque via rclone rcd (evita reinicio de pacer de cuota)"
```

- [ ] **Paso 6: Reescribir el Paso 4 del procedimiento de la skill**

Sustituir el actual Paso 4 ("(tras OK) Ejecuta de una pasada (PLANO): copia cada fichero...") por:

```markdown
4. **(tras OK, y SOLO si `rclone` tiene un client OAuth propio configurado —
   ver prerrequisito del Task 4 del plan de la skill; si no, copia
   secuencial como hasta ahora con `copy_path`/`cp`, más lenta pero sin
   prerrequisito) Copia+renombra en bloque vía `rclone rcd`:**
   `levantar_rcd_si_falta()` una vez, luego `copiar_manifiesto(remote, pares)`
   con TODAS las filas del `_MANIFIESTO.md` propuesto de una vez (no una
   llamada de shell por fichero) — el pacer de cuota se mantiene estable
   dentro del mismo proceso. Los documentos compuestos (bundles) copian
   primero su principal, luego sus anexos, todo dentro de la misma corrida.
   Los `fallidos` que devuelva se reintentan una vez (red inestable) y si
   siguen fallando se anotan en `_MANIFIESTO.md` como pendientes, igual que
   hoy con `ERROR_FILE_NOT_HYDRATED` — nunca se fuerza ni se fabrica un éxito.
```

- [ ] **Paso 7: Verificación manual** (necesita el client OAuth propio ya configurado — no es mockeable)

Sobre un caso de prueba con ≥10 ficheros de distintas subcarpetas de origen, medir el tiempo total de `copiar_manifiesto` y confirmar en los logs de rclone (`-vv` en el `rcd`) que NO aparece ningún `403 Quota exceeded` — si aparece, el client OAuth propio no está bien configurado, no es un fallo del script.

- [ ] **Paso 8: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/SKILL.md
git commit -m "docs(sala-lectura): Paso 4 usa copiar_manifiesto_rclone en vez de copy_path por fichero"
```

---

### Task 5: Fase verify post-copia con criterios duros (fusión `HANDOFF_sala-lectura.md`, 3.2)

**Disparador:** medido en W-02VUDR, dos discrepancias reales pasaron el Paso 7 (reporte) sin que nada las cazara automáticamente — el subagente anunció "6 a pendiente" y al ejecutar salieron 5; anunció "07→2 no copiados, 01→1" cuando era al revés. Ambas las detecté yo insistiendo por chat, no un gate. Una fase verify con criterios duros las habría cazado sola.

**Ficheros:**
- Crear: `.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py`
- Test: `tests/test_verificar_sala.py`
- Modificar: `.claude/skills/organizar-sala-lectura/SKILL.md` (nuevo Paso 6.5, entre índices y catálogo)

**Interfaces:**
- Consume: `_MANIFIESTO.md` (parseado con las mismas `_COLS` que `manifiesto_a_catalogo.py`) + el listado real de `01_Procesado/Sala lectura/`.
- Produce: `verificar(manifiesto_filas: list[dict], ficheros_en_disco: set[str]) -> list[str]` — lista de PROBLEMAS (vacía = todo bien); nunca "arregla" nada, solo detecta.

- [ ] **Paso 1: Escribir el test que falla**

```python
# tests/test_verificar_sala.py
from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"))
verificar_sala = import_module("verificar_sala")


def test_detecta_fila_sin_fichero_en_disco():
    filas = [{"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""}]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco=set())
    assert any("2025-01-01_doc.pdf" in p and "no existe en disco" in p for p in problemas)


def test_detecta_fichero_en_disco_sin_fila_en_manifiesto():
    filas = []
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={"2025-01-01_huerfano.pdf"})
    assert any("2025-01-01_huerfano.pdf" in p and "sin fila" in p for p in problemas)


def test_detecta_anexo_sin_parent_id_resoluble():
    filas = [
        {"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""},
        {"nombre_canonico": "2025-01-01_doc_anexo_1.pdf", "sha256": "b", "parent_id": "id-que-no-existe"},
    ]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={
        "2025-01-01_doc.pdf", "2025-01-01_doc_anexo_1.pdf"})
    assert any("parent_id" in p and "id-que-no-existe" in p for p in problemas)


def test_todo_correcto_no_da_problemas():
    filas = [{"nombre_canonico": "2025-01-01_doc.pdf", "sha256": "a", "parent_id": ""}]
    problemas = verificar_sala.verificar(filas, ficheros_en_disco={"2025-01-01_doc.pdf"})
    assert problemas == []
```

- [ ] **Paso 2: Confirmar que falla**

Run: `python -m pytest tests/test_verificar_sala.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Paso 3: Implementación mínima**

```python
# .claude/skills/organizar-sala-lectura/scripts/verificar_sala.py
"""Fase verify de `organizar-sala-lectura`: contrasta el `_MANIFIESTO.md`
contra lo REALMENTE copiado en disco, con criterios duros — no resume bonito,
lista problemas. Self-contained (sin `core/`), determinista.

Motivo (sesión 2026-07-21, W-02VUDR, fusión de `HANDOFF_sala-lectura.md`
§3.2): dos discrepancias reales de conteo pasaron el reporte final sin que
nada las detectara automáticamente. Esta fase es la red de seguridad.
"""
from __future__ import annotations


def verificar(manifiesto_filas: list[dict], ficheros_en_disco: set[str]) -> list[str]:
    """Nunca arregla nada — solo detecta. `manifiesto_filas` son dicts con
    al menos `nombre_canonico`, `sha256`, `parent_id`. Devuelve la lista de
    problemas (vacía si todo cuadra)."""
    problemas: list[str] = []
    nombres_manifiesto = {f["nombre_canonico"] for f in manifiesto_filas}

    for fila in manifiesto_filas:
        nombre = fila["nombre_canonico"]
        if nombre not in ficheros_en_disco:
            problemas.append(f"{nombre}: fila en manifiesto pero no existe en disco")

    for nombre in ficheros_en_disco:
        if nombre not in nombres_manifiesto:
            problemas.append(f"{nombre}: fichero en disco sin fila en el manifiesto")

    for fila in manifiesto_filas:
        parent = fila.get("parent_id") or ""
        if parent and parent not in nombres_manifiesto and parent not in {
            f.get("sha256") for f in manifiesto_filas
        }:
            problemas.append(
                f"{fila['nombre_canonico']}: parent_id {parent!r} no resuelve "
                f"a ningún documento del manifiesto (anexo huérfano)"
            )
    return problemas
```

- [ ] **Paso 4: Confirmar que pasa**

Run: `python -m pytest tests/test_verificar_sala.py -v`
Expected: `4 passed`

- [ ] **Paso 5: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/scripts/verificar_sala.py tests/test_verificar_sala.py
git commit -m "feat(sala-lectura): fase verify con criterios duros (manifiesto vs disco, anexos huerfanos)"
```

- [ ] **Paso 6: Enganchar en el procedimiento de la skill**

Añadir como nuevo Paso 6.5 (entre "escribir índices" y "derivar el catálogo"):

```markdown
6.5. **Verify — falla ruidosamente, no resumas bonito.** `verificar(filas,
   ficheros_en_disco)` sobre el `_MANIFIESTO.md` recién escrito. Si devuelve
   ALGÚN problema, NO sigas al Paso 7 con un reporte de éxito — lista los
   problemas primero, en el mismo nivel de visibilidad que el resto del
   reporte, y decide con el letrado si reintentar o dejarlos anotados
   explícitamente. Nunca "cuenta bien" un total que no cuadra con lo real.
```

- [ ] **Paso 7: Verificación manual**

Sobre el mismo caso de prueba de la Task 3, borrar a mano UN fichero ya copiado de `Sala lectura/` (simular una copia que falló a medias) y confirmar que `verificar()` lo detecta como "fila en manifiesto pero no existe en disco" — si no lo detecta, el engancha está mal.

- [ ] **Paso 8: Commit**

```bash
git add .claude/skills/organizar-sala-lectura/SKILL.md
git commit -m "docs(sala-lectura): Paso 6.5 verify obligatorio antes de reportar exito"
```

---

## Auto-revisión

**Cobertura:** patrón estrecho + 07 por defecto → Task 1. Hilo de email → Task 1 (`agrupar_por_hilo`). Río arriba (espejo MD) → Task 2. Dedup antes de clasificar → Task 1 (`dedup_por_sha`), enganchado en Task 3.1.a. Subcategoría CRM (navegabilidad dentro de 07) → Task 1 (`subcategoria_crm`) + Task 3.2. Paralelización de la CLASIFICACIÓN por fuente → Task 3.3. **Velocidad de la COPIA+ÍNDICES → Task 4 v2 (rclone rcd), NO paralelización entre subagentes (v1 descartada: todos competirían por la misma cuota compartida de rclone).** Local vs Drive → Task 3.3 (pendiente de medir aparte, variable independiente).

**Placeholders:** ninguno — código completo y ejecutable en Task 1-2, Task 4 y Task 5; Task 3 son inserciones de texto exactas.

**Consistencia de tipos:** `clasificar_por_patron` ahora devuelve tupla SIEMPRE (no `| None`) — reflejado en firma, docstring y los 3 tests que la ejercitan (default, patrón, pendiente).

**Bloqueo conocido:** Task 4 depende de un prerrequisito manual (client OAuth propio de rclone) fuera del alcance de este plan — sin él, el Paso 7 (verificación) no puede pasar limpio. No es un defecto del código, es una dependencia externa documentada explícitamente en la propia Task.

**Fusión con `HANDOFF_sala-lectura.md`:** plan persistido + gate condicional → Task 3, Paso 4-5 (sustituye el gate SIEMPRE-obligatorio; conserva el invariante "sin preguntas fichero a fichero" del handoff cambiando CUÁNDO aparece, no eliminándolo). Fase verify con criterios duros → Task 5 completa (código nuevo, no solo prosa). Umbrales OCR tabulados (3.3 del handoff) → ya cubierto por Task 2 (`texto_espejo_md`); la única pieza nueva (bandera visible en el gate si falta espejo) → Task 3, Paso 5.
