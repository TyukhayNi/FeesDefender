# Robustez y velocidad de `organizar-sala-lectura` (ítems 9-16) — Plan de implementación (TDD)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** cerrar los 8 ítems de prioridad MEDIA/BAJA (9-16) del backlog `2026-07-21-robustez-velocidad-sala-lectura.md`, que quedaron fuera de la tanda de prioridad alta (v1.11, PR #116): dos bugs deterministas de `preclasificar`, parseo estricto del manifiesto, fecha aproximada limpia en el catálogo, Modo 3 degradado con `md5:`, progreso durable/reanudable de la copia, ciclo de vida del `rcd` + timeout, lectura del representante de hilo `.eml`, y telemetría de fases.

**Architecture:** misma que la tanda alta — helpers Python **self-contained** (cero `import core.*`) bajo `.claude/skills/organizar-sala-lectura/scripts/`, invocados por la skill como pasos deterministas; ediciones de prosa en `SKILL.md`; un único campo opcional nuevo en `core.catalogo_documental.CatalogEntry`. Cada helper endurecido lo cubre un test; los cambios de política de lectura y la telemetría son prosa de `SKILL.md`.

**Tech Stack:** Python 3.11+ (stdlib; `yaml` solo en `manifiesto_a_catalogo.py`, que ya lo usa), `pytest`, sin dependencias nuevas.

## Global Constraints

- **Self-contained:** cero `import core.*` en los scripts bajo `.claude/skills/organizar-sala-lectura/scripts/` (deben correr en Cowork sin el repo Python). `manifiesto_parser.py` es **stdlib puro** (sin `yaml`).
- **Determinista e idempotente:** mismo input → mismo output, siempre. Ninguna aleatoriedad en la lógica. `time.sleep`/`time.monotonic` sí están permitidos en estos scripts Python (no son scripts de Workflow) — el patrón ya existe en `levantar_rcd_si_falta`.
- **No destructivo:** ningún helper mueve/borra el crudo ni la sala; `verificar()` **solo detecta, nunca arregla**. La copia nunca fabrica un éxito.
- **No romper lo ya cerrado (v1.11, PR #116):** `senales_gate`, `validar_pares`, `verificar()` (colisión + homogéneos + parent_id + fecha 0000), la CLI de `verificar_sala.py`, `precheck_rclone.py`, `manifiesto_parser.parse_manifiesto`, `indices_desde_manifiesto.py` y las columnas `categoria`/`subcategoria_crm` YA están en el código — estas tareas **añaden encima**, no las rehacen.
- **Test anti-drift obligatorio** para cualquier constante/campo duplicado de `core/` (patrón `test_campos_coinciden_con_CatalogEntry`, `test_categorias_sin_drift`, `test_fuente_skill_sin_drift_con_core`).
- **`main` protegida:** el trabajo va en rama + PR (nunca commit directo); el PR debe pasar `leak-scan`. CI **no** corre pytest → correr la suite **en local** antes de mergear (`python -m pytest -q`), sobre todo por los guards de docs.
- **Conteo de pytest SIEMPRE por `--junit-xml`** en este Windows (el resumen por tubería no se captura fiable). Para RED/GREEN de un test concreto, `-v` de ese test basta; para el conteo total, `--junit-xml`.
- **Entorno:** Windows + PowerShell; venv en la **raíz compartida** `C:\Users\tnm33\Dev\FeesDefender\.venv` (este worktree no tiene `.venv` propio). Ejecutar con `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest ...` **desde el worktree**. UTF-8 sin BOM en todo fichero.
- **Versión:** este trabajo estrena la **1.12** de la skill. El frontmatter y la primera entrada del `CHANGELOG.md` deben quedar en `1.12` y el guard `tests/test_sala_lectura_version_changelog.py` lo verifica. Tras editar, re-empaquetar con `scripts/package_skill.py`; el re-import del `.skill` en Cowork queda como paso manual fuera de este plan.

---

### Task 1: `agrupar_por_hilo` — sufijo `_N` de hilo solo si la base existe (ítem 11.2)

**Por qué:** `agrupar_por_hilo` trata cualquier `_<dígitos>` final como sufijo de hilo. Un `.eml` cuyo asunto lleva una cifra (`..._1_990_000.eml`) se fusiona con un hilo inexistente. `email_export._ruta_unica` numera el primer mensaje SIN sufijo y los siguientes `_2`, `_3`… (nunca `_0`/`_1`), así que un hilo real SIEMPRE tiene su base sin sufijo presente; exigir que la base exista elimina el falso positivo sin perder ninguna agrupación real.

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py` (`agrupar_por_hilo`)
- Test: `tests/test_preclasificar_sala_lectura.py`

**Interfaces:**
- Modifies (sin cambio de firma): `agrupar_por_hilo(rutas_eml: list[str]) -> dict[str, list[str]]`. Ahora un nombre `X_N` solo se agrupa bajo `X` si `X` (o `X.eml`) está en el conjunto; si no, `X_N` es su propia clave.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# añadir a tests/test_preclasificar_sala_lectura.py
def test_agrupar_por_hilo_no_fusiona_por_cifra_en_el_asunto():
    # ".._1_990_000" NO es un sufijo de hilo: no existe la base ".._1_990" en el conjunto.
    nombres = [
        "2025-05-10_oferta_vivienda_1_990_000.eml",
        "2025-06-01_otra_cosa.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert set(grupos) == {"2025-05-10_oferta_vivienda_1_990_000", "2025-06-01_otra_cosa"}
    assert grupos["2025-05-10_oferta_vivienda_1_990_000"] == ["2025-05-10_oferta_vivienda_1_990_000.eml"]


def test_agrupar_por_hilo_agrupa_solo_si_la_base_existe():
    # Hay base sin sufijo -> _2/_3 se agrupan bajo ella (caso real de email_export).
    nombres = [
        "2025-03-20_consulta.eml",
        "2025-03-20_consulta_2.eml",
        "2025-03-20_consulta_3.eml",
    ]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert len(grupos) == 1
    assert len(grupos["2025-03-20_consulta"]) == 3


def test_agrupar_por_hilo_sin_base_no_fusiona():
    # _2 y _3 SIN el base -> no se puede afirmar que sean un hilo: cada uno su clave.
    nombres = ["2025-03-20_consulta_2.eml", "2025-03-20_consulta_3.eml"]
    grupos = preclasificar.agrupar_por_hilo(nombres)
    assert len(grupos) == 2
```

- [ ] **Step 2: Confirmar que fallan**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_preclasificar_sala_lectura.py -v -k "agrupar_por_hilo"`
Expected: `test_agrupar_por_hilo_no_fusiona_por_cifra_en_el_asunto` y `test_agrupar_por_hilo_sin_base_no_fusiona` FALLAN (hoy fusionan por la cifra / por el sufijo sin base); `test_agrupar_por_hilo_agrupa_solo_si_la_base_existe` y el existente `..._junta_variantes...` PASAN.

- [ ] **Step 3: Reescribir `agrupar_por_hilo` (dos pasadas)**

Sustituir la función (líneas ~90-105) por:

```python
def agrupar_por_hilo(rutas_eml: list[str]) -> dict[str, list[str]]:
    """Agrupa nombres de `.eml` por HILO: el motor de export (`core.email_export`)
    escribe el PRIMER mensaje de un asunto+fecha sin sufijo y numera los
    siguientes `_2`, `_3`… (`_ruta_unica`; nunca `_0`/`_1`). La clave de hilo es
    el nombre sin ese sufijo, pero SOLO se agrupa `X_N` bajo `X` si `X` está de
    verdad en el conjunto — así una cifra del propio asunto (`..._1_990_000.eml`)
    no fabrica un hilo inexistente. Devuelve `{clave_hilo: [nombres_del_grupo]}`;
    clasifica un representante y propaga su categoría al resto sin releerlos.
    Heurística de nombre, no de `Message-ID`/`References` — proxy barato, no
    sustituto de un threading riguroso si algún día hace falta."""
    def _base(nombre: str) -> str:
        return nombre[:-4] if nombre.lower().endswith(".eml") else nombre

    bases_presentes = {_base(n) for n in rutas_eml}
    grupos: dict[str, list[str]] = {}
    for nombre in rutas_eml:
        base = _base(nombre)
        m = _SUFIJO_HILO_RE.match(base)
        # Solo es sufijo de hilo si el nombre pelado (sin `_N`) existe como .eml
        # propio en el conjunto; si no, el `_N` es parte del asunto (p. ej. cifra).
        clave = m.group(1) if (m and m.group(1) in bases_presentes) else base
        grupos.setdefault(clave, []).append(nombre)
    return grupos
```

- [ ] **Step 4: Confirmar que pasan (nuevos + regresión de preclasificar)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_preclasificar_sala_lectura.py -v`
Expected: PASS de los 3 nuevos y de todos los previos (incl. `test_agrupar_por_hilo_junta_variantes_del_mismo_dia_y_asunto` y `test_categorias_sin_drift`).

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/preclasificar.py" tests/test_preclasificar_sala_lectura.py
git commit -m "fix(sala-lectura): agrupar_por_hilo no fusiona por una cifra del asunto (base debe existir)"
```

---

### Task 2: `emparejar_exports_whatsapp` — el zip crudo no genera fila propia (ítem 11.1)

**Por qué:** `whatsapp_intake.deposit_export` deposita el zip original como `_export_original.zip` **junto** al `_chat.txt` extraído y su `media/` (constante `_ORIGINAL_ZIP_NAME`). Ese zip es el crudo del que ya salió todo lo procesable; darle fila propia en la sala fabricó 5 filas basura `0000-00-00` en W-02VUDR (un zip no tiene fecha ni espejo MD, así que el verify tampoco lo caza). Marcarlo duplicado de su `_chat.txt` lo excluye de la sala sin perder trazabilidad (queda anotado, no borrado).

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/preclasificar.py` (`emparejar_exports_whatsapp`)
- Test: `tests/test_preclasificar_sala_lectura.py`

**Interfaces:**
- Produces: `emparejar_exports_whatsapp(rutas: list[str]) -> tuple[list[str], list[dict]]` — devuelve `(rutas_sin_crudos, crudos)`. `crudos` = `[{"ruta": <zip>, "duplicado_de": <_chat.txt hermano>, "motivo": "export_crudo_whatsapp"}]`. Un `.zip` es crudo SOLO si su basename es exactamente `_export_original.zip` (constante `core.whatsapp_intake._ORIGINAL_ZIP_NAME`, duplicada self-contained) **Y** en su MISMO directorio hay un `_chat.txt` — así un `.zip` legítimo de documentación aportada NO se excluye por error (hallazgo de la revisión adversarial). Se aplica ANTES de `dedup_por_sha`/`clasificar_por_patron`.
- Produces: `_NOMBRE_EXPORT_CRUDO_WHATSAPP = "_export_original.zip"` (constante nombrada para el test anti-drift).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# añadir a tests/test_preclasificar_sala_lectura.py
def test_emparejar_exports_whatsapp_marca_el_zip_crudo_como_duplicado():
    rutas = [
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_chat.txt",
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/media/IMG-0001.jpg",
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_export_original.zip",
    ]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_export_original.zip" not in limpias
    assert len(crudos) == 1
    assert crudos[0]["motivo"] == "export_crudo_whatsapp"
    assert crudos[0]["duplicado_de"].endswith("Chat con Tonet/_chat.txt")


def test_emparejar_exports_whatsapp_conserva_zip_sin_chat_hermano():
    # Un .zip suelto (Manual) SIN _chat.txt hermano NO es un export crudo -> se conserva.
    rutas = ["04_Manual/documentacion_aportada.zip", "04_Manual/otro.pdf"]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert "04_Manual/documentacion_aportada.zip" in limpias
    assert crudos == []


def test_emparejar_exports_whatsapp_sin_zip_no_toca_nada():
    rutas = ["01_Drive EV/a.pdf", "03_Email/corr.eml"]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert limpias == rutas
    assert crudos == []


def test_emparejar_exports_whatsapp_conserva_zip_no_original_junto_a_chat():
    # Un .zip que NO es _export_original.zip, aunque comparta carpeta con un
    # _chat.txt, es documentación legítima aportada: se conserva (hallazgo de la
    # revisión adversarial — el matcher no debe ser un `.endswith('.zip')` genérico).
    rutas = [
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/_chat.txt",
        "2026-07-21_whatsapp_01/propietario/Chat con Tonet/adjuntos_aportados.zip",
    ]
    limpias, crudos = preclasificar.emparejar_exports_whatsapp(rutas)
    assert "2026-07-21_whatsapp_01/propietario/Chat con Tonet/adjuntos_aportados.zip" in limpias
    assert crudos == []


def test_nombre_export_crudo_sin_drift_con_core():
    from core.whatsapp_intake import _ORIGINAL_ZIP_NAME
    assert preclasificar._NOMBRE_EXPORT_CRUDO_WHATSAPP == _ORIGINAL_ZIP_NAME
```

- [ ] **Step 2: Confirmar que fallan**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_preclasificar_sala_lectura.py -v -k "emparejar_exports_whatsapp"`
Expected: `AttributeError: module 'preclasificar' has no attribute 'emparejar_exports_whatsapp'`.

- [ ] **Step 3: Implementar `emparejar_exports_whatsapp`**

Añadir a `preclasificar.py` (tras `dedup_por_sha`):

```python
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
```

- [ ] **Step 4: Confirmar que pasan (nuevos + regresión)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_preclasificar_sala_lectura.py -v`
Expected: PASS de los 3 nuevos y de todos los previos.

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/preclasificar.py" tests/test_preclasificar_sala_lectura.py
git commit -m "feat(sala-lectura): emparejar_exports_whatsapp excluye el zip crudo (_export_original.zip)"
```

---

### Task 3: Parseo estricto del manifiesto + `sha_valido` (admite `md5:`) (ítems 12 y 13-código)

**Por qué:** hoy `parse_manifiesto` hace `continue` en silencio ante una fila con nº de celdas != cabecera — el documento existe en la sala pero desaparece de la SSOT máquina sin aviso (ítem 12). Y el Modo 3 puro-nube no puede calcular sha256 de un binario grande (descargar 1,1 GB es incumplible): debe admitir `md5:<hash>` en la columna sha256, que la primera sesión con filesystem completa (ítem 13). Ambos tocan la validación del manifiesto, así que van juntos.

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_parser.py` (`parse_manifiesto` gana `estricto=`; nueva `sha_valido`)
- Modify: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py` (`derivar` estricto + valida sha)
- Modify: `.claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py` (`derivar` estricto)
- Modify: `.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py` (`main` estricto)
- Test: `tests/test_manifiesto_parser.py`, `tests/test_manifiesto_a_catalogo.py`

**Interfaces:**
- Modifies: `parse_manifiesto(texto: str, *, estricto: bool = False) -> list[dict]`. Con `estricto=True`, lanza `ValueError` (listando nº de línea + contenido) si una línea candidata (empieza por `|`, no cabecera, no separador) tiene un nº de celdas distinto del nº de columnas. `estricto=False` (default) = comportamiento actual, no rompe a nadie.
- Produces: `sha_valido(valor: str) -> bool` — `True` para `[0-9a-f]{64}`, `md5:[0-9a-f]{32}`, o cadena vacía (placeholder tolerado); `False` en otro caso.
- Consumes: los tres consumidores (`manifiesto_a_catalogo`, `indices_desde_manifiesto`, `verificar_sala`) llaman `parse_manifiesto(..., estricto=True)`. `manifiesto_a_catalogo.derivar` además valida `sha_valido` por fila.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# añadir a tests/test_manifiesto_parser.py
import pytest

_MANIF_MALFORMADO = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| aaaa | 01_Drive EV/ok.pdf | 2024-04-26_ok.pdf | pdf | 2024-04-26 | propietario |  |
| falta_columnas | 01_Drive EV/mala.pdf | 2024-05-01_mala.pdf |
"""


def test_estricto_lanza_si_hay_fila_malformada():
    with pytest.raises(ValueError, match="fila.*malformada|columnas"):
        mp.parse_manifiesto(_MANIF_MALFORMADO, estricto=True)


def test_estricto_ok_si_todas_las_filas_cuadran():
    filas = mp.parse_manifiesto(_MANIF_7COL, estricto=True)
    assert len(filas) == 2


def test_no_estricto_sigue_siendo_tolerante():
    # Sin estricto, la fila mala se salta en silencio (comportamiento heredado).
    filas = mp.parse_manifiesto(_MANIF_MALFORMADO)
    assert len(filas) == 1


def test_sha_valido_acepta_sha256_md5_y_vacio():
    assert mp.sha_valido("a" * 64)
    assert mp.sha_valido("md5:" + "b" * 32)
    assert mp.sha_valido("")
    assert not mp.sha_valido("aaaa")
    assert not mp.sha_valido("md5:zzzz")
```

```python
# añadir a tests/test_manifiesto_a_catalogo.py
import pytest

_MANIF_MD5 = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| md5:%s | 06_Entrevistas/video.mp4 | 2025-01-01_video.mp4 | mp4 | 2025-01-01 | propietario |  |
""" % ("c" * 32)

_MANIF_SHA_MALO = """<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| noesunhash | 01_Drive EV/x.pdf | 2025-01-01_x.pdf | pdf | 2025-01-01 | propietario |  |
"""


def test_derivar_acepta_md5_prefijado(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF_MD5, encoding="utf-8")
    out = mod.derivar(tmp_path / "_MANIFIESTO.md", tmp_path / "indice_documental.yaml")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data[0]["hash"] == "md5:" + "c" * 32


def test_derivar_aborta_si_sha_invalido(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF_SHA_MALO, encoding="utf-8")
    with pytest.raises(ValueError, match="sha256|hash"):
        mod.derivar(tmp_path / "_MANIFIESTO.md", tmp_path / "indice_documental.yaml")
```

Y actualizar los fixtures de `tests/test_manifiesto_a_catalogo.py` que usan sha de juguete a sha256 de 64 hex (ahora `derivar` valida): en `_MANIF` cambiar `aaaa`→`"a"*64` y `bbbb`→`"b"*64`; en `_MANIF_CAT` cambiar `aaaa`→`"a"*64`. Ajustar las aserciones que buscan por hash: `test_deriva_catalogo_yaml` pasa a `{d["hash"]: d}["a"*64]` (usa una variable local `sha_a = "a"*64`).

```python
# tests/test_manifiesto_a_catalogo.py — fixtures actualizados
_SHA_A = "a" * 64
_SHA_B = "b" * 64
_MANIF = f"""<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| {_SHA_A} | 01_Drive EV/Catastro.pdf | 2024-04-26_catastro.pdf | 08. PENDIENTE DE CLASIFICAR | 2024-04-26 | propietario |  |
| {_SHA_B} | 04_Manual/RESPUESTA_RESOLUCION.pdf | 2025-07-22_requerimiento.pdf | 07. RECLAMACIONES | 2025-07-22 | propietario |  |
"""
_MANIF_CAT = f"""<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id | categoria | subcategoria_crm |
|---|---|---|---|---|---|---|---|---|
| {_SHA_A} | sudespacho_1/civil/x.pdf | 2025-01-01_x.pdf | pdf | 2025-01-01 | propietario |  | 07. RECLAMACIONES | civil |
"""
```

En `test_deriva_catalogo_yaml`, sustituir `{d["hash"]: d}["aaaa"]` por `{d["hash"]: d}[_SHA_A]`.

- [ ] **Step 2: Confirmar que fallan**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_parser.py tests/test_manifiesto_a_catalogo.py -v`
Expected — RED genuinos que FALLAN hoy: `test_estricto_lanza_si_hay_fila_malformada` (hoy no lanza), `test_sha_valido_...` (`AttributeError: no attribute 'sha_valido'`), y `test_derivar_aborta_si_sha_invalido` (hoy `derivar` NO valida el sha → no aborta). **NOTA (revisión adversarial):** `test_derivar_acepta_md5_prefijado` YA PASA hoy — `derivar` asigna el `hash` sin validar, así que un `md5:` ya se emite tal cual; NO es un RED, es un test de **no-regresión** que garantiza que la validación nueva no rompe el `md5:` legítimo. `test_no_estricto_sigue_siendo_tolerante` también pasa hoy (comportamiento heredado). Es correcto que estos dos ya pasen.

- [ ] **Step 3: `parse_manifiesto` gana `estricto=` + `sha_valido`**

En `manifiesto_parser.py`, tras `COLS_CANON`, añadir `import re` al principio del módulo y:

```python
import re

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MD5_RE = re.compile(r"^md5:[0-9a-f]{32}$")


def sha_valido(valor: str) -> bool:
    """`True` si el valor de la columna sha256 es un sha256 real (64 hex), un
    `md5:<32 hex>` (Modo 3 degradado, ítem 13), o vacío (placeholder tolerado)."""
    v = (valor or "").strip()
    return v == "" or bool(_SHA256_RE.match(v)) or bool(_MD5_RE.match(v))
```

Y reescribir `parse_manifiesto` para aceptar `estricto`:

```python
def parse_manifiesto(texto: str, *, estricto: bool = False) -> list[dict]:
    """Una fila-dict por fila de datos. Claves de la cabecera (o `COLS_CANON`).
    Con `estricto=True`, una línea candidata (empieza por `|`, no cabecera, no
    separador) cuyo nº de celdas != nº de columnas lanza `ValueError` (ítem 12:
    ninguna fila desaparece del catálogo en silencio). Sin `estricto` (default)
    esas filas se saltan — comportamiento heredado, no rompe manifiestos viejos."""
    cols: list[str] | None = None
    filas: list[dict] = []
    rechazadas: list[str] = []
    for i, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if not s.startswith("|"):
            continue
        celdas = [c.strip() for c in s.strip("|").split("|")]
        if _es_separador(celdas):
            continue
        if celdas and celdas[0] == "sha256":
            cols = celdas
            continue
        if cols is None:
            cols = COLS_CANON
        if len(celdas) != len(cols):
            rechazadas.append(f"  línea {i}: {len(celdas)} celdas, se esperaban {len(cols)}: {s}")
            continue
        filas.append(dict(zip(cols, celdas)))
    if estricto and rechazadas:
        raise ValueError(
            "fila(s) malformada(s) en el _MANIFIESTO.md (nº de columnas incorrecto) — "
            "se perderían del catálogo en silencio:\n" + "\n".join(rechazadas))
    return filas
```

- [ ] **Step 4: `manifiesto_a_catalogo.derivar` — estricto + valida sha**

En `manifiesto_a_catalogo.py`, en `derivar`, cambiar la primera línea y añadir la validación de sha por fila:

```python
def derivar(manifiesto: Path, salida: Path) -> Path:
    filas = manifiesto_parser.parse_manifiesto(
        Path(manifiesto).read_text(encoding="utf-8"), estricto=True)
    malos = [f["sha256"] for f in filas if not manifiesto_parser.sha_valido(f.get("sha256", ""))]
    if malos:
        raise ValueError(
            "sha256 inválido en el _MANIFIESTO.md (ni sha256 de 64 hex, ni md5:<32 hex>, "
            "ni vacío): " + ", ".join(repr(m) for m in malos[:5]))
    entradas = []
    # ... (resto sin cambios)
```

- [ ] **Step 5: `indices_desde_manifiesto` y `verificar_sala` — estricto en su parseo**

En `indices_desde_manifiesto.py::derivar`, cambiar:

```python
    filas = manifiesto_parser.parse_manifiesto(
        Path(manifiesto).read_text(encoding="utf-8"), estricto=True)
```

En `verificar_sala.py::main`, cambiar la línea de parseo y capturar el error como un problema (exit 1, no traceback):

```python
    try:
        filas = manifiesto_parser.parse_manifiesto(
            manif.read_text(encoding="utf-8"), estricto=True)
    except ValueError as exc:
        print(str(exc))
        return 1
```

- [ ] **Step 6: Confirmar que pasa todo (nuevos + regresión de los 4 scripts)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_parser.py tests/test_manifiesto_a_catalogo.py tests/test_indices_desde_manifiesto.py tests/test_verificar_sala_cli.py -v`
Expected: PASS de todos. En particular `test_main_exit_1_cuando_falta_fichero` (verify CLI, fixture de 7 columnas bien formadas con `aaaa`) sigue devolviendo 1 por fichero faltante — el estricto valida COLUMNAS, no el valor del sha, así que `aaaa` no lo dispara.

- [ ] **Step 7: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/manifiesto_parser.py" ".claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py" ".claude/skills/organizar-sala-lectura/scripts/indices_desde_manifiesto.py" ".claude/skills/organizar-sala-lectura/scripts/verificar_sala.py" tests/test_manifiesto_parser.py tests/test_manifiesto_a_catalogo.py
git commit -m "feat(sala-lectura): parseo estricto del manifiesto + sha_valido (admite md5: para Modo 3)"
```

---

### Task 4: `fecha_aproximada` — sacar el marcador `(*)` del valor de fecha (ítem 15)

**Por qué:** el catálogo YAML lleva hoy fechas no parseables por máquina (`"2024-06-06(*)"` real): el `(*)` marca "fecha aproximada" pero contamina el valor. Hay que emitir `fecha_doc` limpia + un flag booleano `fecha_aproximada`.

**Files:**
- Modify: `core/catalogo_documental.py:32-53` (campo opcional `fecha_aproximada` en `CatalogEntry`)
- Modify: `.claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py` (`CAMPOS_EMITIDOS` + `derivar`)
- Modify: `.claude/skills/organizar-sala-lectura/scripts/verificar_sala.py` (normalizar `(*)` en el chequeo de fecha)
- Test: `tests/test_manifiesto_a_catalogo.py`

**Interfaces:**
- Produces: `CatalogEntry.fecha_aproximada: bool | None = None`; el catálogo YAML emite `fecha_doc` sin `(*)` y `fecha_aproximada: true|false`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# añadir a tests/test_manifiesto_a_catalogo.py
_MANIF_APROX = f"""<!-- GENERADO — NO EDITAR A MANO -->
| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |
|---|---|---|---|---|---|---|
| {"d" * 64} | 01_Drive EV/foto.jpg | 2024-06-06_foto.jpg | jpg | 2024-06-06(*) | propietario |  |
| {"e" * 64} | 01_Drive EV/acta.pdf | 2025-01-02_acta.pdf | pdf | 2025-01-02 | propietario |  |
"""


def test_derivar_saca_el_marcador_aproximado_de_la_fecha(tmp_path):
    mod = _load()
    (tmp_path / "_MANIFIESTO.md").write_text(_MANIF_APROX, encoding="utf-8")
    out = mod.derivar(tmp_path / "_MANIFIESTO.md", tmp_path / "indice_documental.yaml")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    aprox = {d["hash"]: d for d in data}["d" * 64]
    exacta = {d["hash"]: d for d in data}["e" * 64]
    assert aprox["fecha_doc"] == "2024-06-06"
    assert aprox["fecha_aproximada"] is True
    assert exacta["fecha_doc"] == "2025-01-02"
    assert exacta["fecha_aproximada"] is False
```

- [ ] **Step 2: Confirmar que falla**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_a_catalogo.py -v -k "aproximad"`
Expected: `KeyError: 'fecha_aproximada'` / `fecha_doc == "2024-06-06(*)"`.

- [ ] **Step 3: Campo en `CatalogEntry`**

En `core/catalogo_documental.py`, tras `subcategoria_crm`:

```python
    categoria: str | None = None          # categoría E&V (por la que se construyó la sala)
    subcategoria_crm: str | None = None   # subcarpeta del Gestor Documental CRM (etiqueta secundaria)
    fecha_aproximada: bool | None = None   # True si la fecha viene del mtime/nombre (marcada (*) en los índices)
```

- [ ] **Step 4: Emitir `fecha_doc` limpia + flag desde el helper**

En `manifiesto_a_catalogo.py`, extender `CAMPOS_EMITIDOS` con `"fecha_aproximada"` y, en `derivar`, derivar ambos del valor de fecha:

```python
CAMPOS_EMITIDOS = [
    "id_doc", "ruta_relativa", "nombre_original", "tipo_documental", "fecha_doc",
    "parte", "fuente", "estado", "hash", "parent_id", "nombre_canonico",
    "categoria", "subcategoria_crm", "fecha_aproximada",
]
```

Dentro del bucle de `derivar`, sustituir la línea `"fecha_doc": f["fecha"] or None,` por el cálculo, y añadir el flag:

```python
        fecha_cruda = f["fecha"] or ""
        aproximada = "(*)" in fecha_cruda
        fecha_limpia = fecha_cruda.replace("(*)", "").strip()
        entradas.append({
            "id_doc": sha[:12] if sha else rel,
            "ruta_relativa": rel,
            "nombre_original": rel.replace("\\", "/").rsplit("/", 1)[-1],
            "tipo_documental": f["tipo"] or None,
            "fecha_doc": fecha_limpia or None,
            "parte": f["parte"] or None,
            "fuente": _fuente(rel),
            "estado": "original",
            "hash": sha,
            "parent_id": f["parent_id"] or None,
            "nombre_canonico": f["nombre_canonico"] or None,
            "categoria": f.get("categoria") or None,
            "subcategoria_crm": f.get("subcategoria_crm") or None,
            "fecha_aproximada": aproximada,
        })
```

- [ ] **Step 5: `verificar_sala` normaliza `(*)` en el chequeo de fecha**

En `verificar_sala.py::verificar`, el chequeo `if fila.get("fecha") != "0000-00-00": continue` debe ignorar un eventual `(*)`. Sustituir por:

```python
        if (fila.get("fecha") or "").replace("(*)", "").strip() != "0000-00-00":
            continue
```

- [ ] **Step 6: Confirmar que pasa (incl. anti-drift de campos)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_manifiesto_a_catalogo.py tests/test_verificar_sala.py tests/test_verificar_sala_cli.py -v`
Expected: PASS incluyendo `test_campos_coinciden_con_CatalogEntry` (`fecha_aproximada` ∈ `CatalogEntry`).

- [ ] **Step 7: Commit**

```bash
git add core/catalogo_documental.py ".claude/skills/organizar-sala-lectura/scripts/manifiesto_a_catalogo.py" ".claude/skills/organizar-sala-lectura/scripts/verificar_sala.py" tests/test_manifiesto_a_catalogo.py
git commit -m "feat(sala-lectura): fecha_aproximada separa el marcador (*) del valor de fecha en el catalogo"
```

---

### Task 5: Progreso durable por fila + reanudación de la copia (ítem 9)

**Por qué:** el `_MANIFIESTO.md` (única llave del skip incremental) se escribe DESPUÉS de copiar todo (Paso 5, tras el Paso 4). Una corrida que muere a mitad del Paso 4 deja N ficheros copiados y CERO registro — la re-corrida los vuelve a copiar. Un log JSONL append por fila permite reanudar solo lo pendiente.

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py` (`copiar_manifiesto` + `_cargar_progreso`/`_anota_progreso`)
- Test: `tests/test_copiar_manifiesto_rclone.py`

**Interfaces:**
- Modifies: `copiar_manifiesto(remote, pares, *, progreso_path=None) -> tuple[list[str], list[tuple[str, str]]]`. Si `progreso_path` se da: (a) al arrancar, los `dst` ya registrados `ok` se cuentan como copiados y se saltan (reanudación); (b) cada fila completada/fallida se anexa como línea JSON a `progreso_path` (`{"dst":..., "estado":"ok"|"fallido", "error":...}`). Sin `progreso_path`, comportamiento idéntico al actual.
- Produces: `_cargar_progreso(path) -> set[str]` (dst con estado ok), `_anota_progreso(path, dst, estado, error="") -> None`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# añadir a tests/test_copiar_manifiesto_rclone.py
import json as _json


def test_copiar_manifiesto_escribe_progreso_jsonl(tmp_path):
    prog = tmp_path / "copia.jsonl"
    with patch("urllib.request.urlopen", return_value=_mock_response(b"{}")):
        ok, fallidos = cmr.copiar_manifiesto(
            "gdrive_tl:", [("a/x.pdf", "b/x.pdf"), ("a/y.pdf", "b/y.pdf")], progreso_path=prog)
    assert ok == ["b/x.pdf", "b/y.pdf"]
    lineas = [_json.loads(l) for l in prog.read_text(encoding="utf-8").splitlines()]
    assert [l["dst"] for l in lineas] == ["b/x.pdf", "b/y.pdf"]
    assert all(l["estado"] == "ok" for l in lineas)


def test_copiar_manifiesto_reanuda_salta_los_ya_ok(tmp_path):
    prog = tmp_path / "copia.jsonl"
    prog.write_text(_json.dumps({"dst": "b/x.pdf", "estado": "ok"}) + "\n", encoding="utf-8")
    llamadas = []

    def fake_urlopen(req, timeout=60):
        llamadas.append(req.data.decode("utf-8"))
        return _mock_response(b"{}")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ok, fallidos = cmr.copiar_manifiesto(
            "gdrive_tl:", [("a/x.pdf", "b/x.pdf"), ("a/y.pdf", "b/y.pdf")], progreso_path=prog)
    assert ok == ["b/x.pdf", "b/y.pdf"]           # x.pdf cuenta como ok (reanudado)
    assert all("x.pdf" not in c for c in llamadas)  # pero NO se volvió a copiar
    assert any("y.pdf" in c for c in llamadas)
```

- [ ] **Step 2: Confirmar que fallan**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_copiar_manifiesto_rclone.py -v -k "progreso or reanuda"`
Expected: `TypeError: copiar_manifiesto() got an unexpected keyword argument 'progreso_path'`.

- [ ] **Step 3: Añadir progreso durable + reanudación**

Añadir `import json` ya está; añadir los helpers y extender `copiar_manifiesto`:

```python
def _cargar_progreso(path) -> set[str]:
    """`dst` ya copiados OK según el log JSONL (reanudación). Tolerante a un log
    ausente o a líneas corruptas (una corrida muerta puede dejar media línea)."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return set()
    ok: set[str] = set()
    for linea in p.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            reg = json.loads(linea)
        except ValueError:
            continue
        if reg.get("estado") == "ok" and reg.get("dst"):
            ok.add(reg["dst"])
    return ok


def _anota_progreso(path, dst: str, estado: str, error: str = "") -> None:
    reg = {"dst": dst, "estado": estado}
    if error:
        reg["error"] = error
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")


def copiar_manifiesto(
    remote: str, pares: list[tuple[str, str]], *, progreso_path=None,
) -> tuple[list[str], list[tuple[str, str]]]:
    """`pares` = [(src_relpath, dst_relpath), ...] ya decididos por la
    clasificación (Paso 1-3 de la skill). Copia TODOS dentro del MISMO proceso
    `rcd` — el pacer se mantiene estable entre llamadas. Devuelve `(ok, fallidos)`;
    un fallo individual NO aborta el resto.

    Con `progreso_path`, escribe un log JSONL append por fila y REANUDA: los `dst`
    ya `ok` en un log previo se cuentan como copiados y se saltan (ítem 9 — una
    corrida muerta a mitad no re-copia lo ya hecho)."""
    validar_pares(pares)
    ya_ok = _cargar_progreso(progreso_path) if progreso_path else set()
    ok: list[str] = []
    fallidos: list[tuple[str, str]] = []
    for src, dst in pares:
        if dst in ya_ok:
            ok.append(dst)
            continue
        try:
            copiar_renombrar(remote, src, dst)
            ok.append(dst)
            if progreso_path:
                _anota_progreso(progreso_path, dst, "ok")
        except Exception as exc:  # noqa: BLE001 — un fallo no aborta el resto
            fallidos.append((dst, str(exc)))
            if progreso_path:
                _anota_progreso(progreso_path, dst, "fallido", str(exc))
    return ok, fallidos
```

- [ ] **Step 4: Confirmar que pasan (nuevos + regresión de copia)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_copiar_manifiesto_rclone.py -v`
Expected: PASS de los 2 nuevos y de los 5 previos (los previos no pasan `progreso_path` → `ya_ok` vacío, comportamiento idéntico).

- [ ] **Step 5: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py" tests/test_copiar_manifiesto_rclone.py
git commit -m "feat(sala-lectura): copiar_manifiesto con progreso JSONL durable + reanudacion (item 9)"
```

---

### Task 6: Timeout parametrizable + async opcional + ciclo de vida del `rcd` (ítem 14)

**Por qué:** `copiar_renombrar` tiene `timeout=60` fijo → una copia server-side grande legítima (>60s; en W-02VUDR un fichero de 1,1 GB) se cuenta como FALLIDA y reintroduce el síntoma de "fichero pendiente" que motivó todo el backlog. Y `copiar_manifiesto` no cierra el `rcd`: si lo arrancó `levantar_rcd_si_falta`, queda un proceso huérfano en `:15572`. Se parametriza el timeout, se añade una ruta async con polling para copias grandes, y `copiar_manifiesto` gestiona el ciclo de vida del `rcd` (cierra solo el que arrancó).

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py` (`copiar_renombrar`, `esperar_job`, `copiar_manifiesto`)
- Test: `tests/test_copiar_manifiesto_rclone.py`

**Interfaces:**
- Modifies: `copiar_renombrar(remote, src, dst, *, timeout: float = 60, async_: bool = False) -> dict`. Con `async_=True`, el body lleva `"_async": True` y la respuesta trae `{"jobid": N}`.
- Produces: `esperar_job(jobid, *, timeout_total: float = 1800, intervalo: float = 2.0) -> dict` — polling `POST job/status` hasta `finished`; lanza si el job falla o si supera `timeout_total`.
- Modifies: `copiar_manifiesto(remote, pares, *, progreso_path=None, gestionar_rcd: bool = True, timeout: float = 60, usar_async: bool = False) -> tuple[list[str], list[tuple[str, str]]]`. Con `gestionar_rcd=True` (default) arranca el `rcd` si falta y lo cierra al terminar SOLO si lo arrancó esta llamada (no toca un `rcd` ajeno).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# añadir a tests/test_copiar_manifiesto_rclone.py
def test_copiar_renombrar_respeta_timeout_parametrizable():
    capturado = {}

    def fake_urlopen(req, timeout=60):
        capturado["timeout"] = timeout
        return _mock_response(b"{}")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        cmr.copiar_renombrar("gdrive_tl:", "a/x.pdf", "b/x.pdf", timeout=900)
    assert capturado["timeout"] == 900


def test_copiar_renombrar_async_manda_flag_y_devuelve_jobid():
    with patch("urllib.request.urlopen", return_value=_mock_response(b'{"jobid": 7}')) as m:
        r = cmr.copiar_renombrar("gdrive_tl:", "a/x.pdf", "b/x.pdf", async_=True)
        import json
        assert json.loads(m.call_args[0][0].data)["_async"] is True
        assert r["jobid"] == 7


def test_esperar_job_hace_polling_hasta_finished():
    respuestas = [b'{"finished": false}', b'{"finished": true, "success": true}']
    with patch("urllib.request.urlopen", side_effect=[_mock_response(x) for x in respuestas]):
        with patch("time.sleep"):
            estado = cmr.esperar_job(7, intervalo=0)
    assert estado["finished"] is True and estado["success"] is True


def test_esperar_job_lanza_si_el_job_falla():
    with patch("urllib.request.urlopen", return_value=_mock_response(b'{"finished": true, "success": false, "error": "boom"}')):
        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="boom"):
                cmr.esperar_job(7, intervalo=0)


def test_copiar_manifiesto_cierra_el_rcd_que_arranco():
    proc = MagicMock()
    with patch.object(cmr, "levantar_rcd_si_falta", return_value=proc):
        with patch("urllib.request.urlopen", return_value=_mock_response(b"{}")):
            cmr.copiar_manifiesto("gdrive_tl:", [("a/x.pdf", "b/x.pdf")])
    proc.terminate.assert_called_once()


def test_copiar_manifiesto_no_toca_un_rcd_ajeno():
    with patch.object(cmr, "levantar_rcd_si_falta", return_value=None):
        with patch("urllib.request.urlopen", return_value=_mock_response(b"{}")):
            ok, _ = cmr.copiar_manifiesto("gdrive_tl:", [("a/x.pdf", "b/x.pdf")])
    assert ok == ["b/x.pdf"]  # sin Popen que cerrar, no revienta
```

- [ ] **Step 2: Confirmar que fallan**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_copiar_manifiesto_rclone.py -v -k "timeout or async or esperar_job or rcd"`
Expected: FAIL (`copiar_renombrar` no acepta `timeout`/`async_`; no existe `esperar_job`; `copiar_manifiesto` no cierra el `rcd`).

- [ ] **Step 3: Parametrizar `copiar_renombrar` + `esperar_job`**

Sustituir `copiar_renombrar` por la versión parametrizable y añadir `esperar_job` justo debajo:

```python
def copiar_renombrar(
    remote: str, src_relpath: str, dst_relpath: str, *,
    timeout: float = 60, async_: bool = False,
) -> dict:
    """Una llamada `operations/copyfile` sobre el `rcd` ya levantado. `remote`
    lleva el `:` final (p. ej. `gdrive_tl:`); las rutas son relativas a ese
    remote. `timeout` en segundos (parametrizable: una copia grande legítima
    tarda >60s y no debe contarse como fallida — ítem 14). Con `async_=True`,
    rclone encola el job y devuelve `{"jobid": N}` (usa `esperar_job`)."""
    payload = {
        "srcFs": remote, "srcRemote": src_relpath,
        "dstFs": remote, "dstRemote": dst_relpath,
    }
    if async_:
        payload["_async"] = True
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_RC_URL}/operations/copyfile", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def esperar_job(jobid, *, timeout_total: float = 1800, intervalo: float = 2.0) -> dict:
    """Polling `POST job/status` hasta `finished`. Lanza `RuntimeError` si el job
    acabó sin éxito, o `TimeoutError` si supera `timeout_total`. Para copias
    grandes lanzadas con `copiar_renombrar(..., async_=True)`."""
    inicio = time.monotonic()
    while True:
        body = json.dumps({"jobid": jobid}).encode("utf-8")
        req = urllib.request.Request(
            f"{_RC_URL}/job/status", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            estado = json.loads(resp.read())
        if estado.get("finished"):
            if not estado.get("success", False):
                raise RuntimeError(f"job {jobid} falló: {estado.get('error', 'sin detalle')}")
            return estado
        if time.monotonic() - inicio > timeout_total:
            raise TimeoutError(f"job {jobid} no terminó en {timeout_total}s")
        time.sleep(intervalo)
```

- [ ] **Step 4: `copiar_manifiesto` — timeout/async por fila + ciclo de vida del `rcd`**

Extender la firma y el cuerpo (sobre la versión de la Task 5):

```python
def copiar_manifiesto(
    remote: str, pares: list[tuple[str, str]], *, progreso_path=None,
    gestionar_rcd: bool = True, timeout: float = 60, usar_async: bool = False,
) -> tuple[list[str], list[tuple[str, str]]]:
    """... (docstring de la Task 5) ...

    Con `gestionar_rcd=True` (default) arranca el `rcd` si falta y lo cierra al
    terminar SOLO si lo arrancó esta llamada (ítem 14 — no deja un `rcd`
    huérfano en :15572, ni toca uno ajeno). `usar_async=True` encola cada copia
    y espera su job (para copias grandes); `timeout` es el tope síncrono por
    llamada cuando no se usa async."""
    validar_pares(pares)
    ya_ok = _cargar_progreso(progreso_path) if progreso_path else set()
    ok: list[str] = []
    fallidos: list[tuple[str, str]] = []
    proc = levantar_rcd_si_falta() if gestionar_rcd else None
    try:
        for src, dst in pares:
            if dst in ya_ok:
                ok.append(dst)
                continue
            try:
                if usar_async:
                    r = copiar_renombrar(remote, src, dst, timeout=timeout, async_=True)
                    esperar_job(r.get("jobid"))
                else:
                    copiar_renombrar(remote, src, dst, timeout=timeout)
                ok.append(dst)
                if progreso_path:
                    _anota_progreso(progreso_path, dst, "ok")
            except Exception as exc:  # noqa: BLE001 — un fallo no aborta el resto
                fallidos.append((dst, str(exc)))
                if progreso_path:
                    _anota_progreso(progreso_path, dst, "fallido", str(exc))
    finally:
        if proc is not None:
            proc.terminate()
    return ok, fallidos
```

- [ ] **Step 5: Confirmar que pasa todo (nuevos + regresión completa de copia)**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_copiar_manifiesto_rclone.py -v`
Expected: PASS de los 6 nuevos y de los 7 previos. Nota: los previos mockean `urllib.request.urlopen`; con `gestionar_rcd=True`, `levantar_rcd_si_falta` llama `_rc_activo` (que ve el mock y devuelve `True` → no arranca nada → `proc=None` → nada que cerrar), así que su resultado no cambia; y `test_..._aborta_..._colision` sigue con `urlopen` no llamado porque `validar_pares` lanza ANTES de `levantar_rcd_si_falta`.

- [ ] **Step 6: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/scripts/copiar_manifiesto_rclone.py" tests/test_copiar_manifiesto_rclone.py
git commit -m "feat(sala-lectura): timeout parametrizable + async opcional + cierre del rcd propio (item 14)"
```

---

### Task 7: `SKILL.md` — prosa de los ítems 9, 10, 13 y 16 + wiring de los helpers

**Por qué:** los helpers de las Tasks 1-6 no cambian la conducta de la skill hasta que su procedimiento los invoca; y los ítems 10 (representante de hilo) y 16 (telemetría) son cambios de política/reporte que viven solo en prosa.

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md` (Paso 1-bis, Paso 2-bis, Paso 4, Paso 7, § Re-aplicación, Gotchas)

- [ ] **Step 1: Paso 1-bis.a — excluir el export crudo de WhatsApp** (ítem 11.1, wiring)

En el Paso 1-bis, antes de la viñeta `a.` (dedup), insertar una viñeta nueva:

```markdown
   a0. `emparejar_exports_whatsapp(rutas)` → aparta los `.zip` crudos de WhatsApp
      (`_export_original.zip` que `whatsapp_intake` deja junto al `_chat.txt`): se
      anotan `duplicado_de` su chat y **no reciben fila propia** (no tienen fecha
      ni espejo MD; darles una fabrica basura `0000-00-00`). Trabaja sobre las
      rutas ya limpias en los pasos siguientes.
```

- [ ] **Step 2: Paso 1-bis.c — leer siempre el representante de hilo `.eml` que cae al 07** (ítem 10)

Reemplazar la viñeta `c.` del Paso 1-bis por:

```markdown
   c. `clasificar_por_patron(nombre, es_bundle_conversacional=...)` sobre cada
      único/representante restante → SIEMPRE devuelve una categoría (00-06 por
      patrón estrecho, 07 por defecto, u 08 si es un bundle de WhatsApp sin
      patrón). **Excepción de calidad para correo:** para cada HILO de `.eml`
      cuyo representante caiga a `07. RECLAMACIONES` con motivo
      `default_reclamaciones`, **lee el representante del hilo antes de fijar la
      categoría** (UNA lectura por hilo, no por mensaje — `agrupar_por_hilo` ya
      colapsó el hilo a un representante) y propaga la categoría que determines al
      resto del grupo. Motivo (W-02VUDR): ~12 correos de correspondencia con el
      propietario (prueba nuclear de activación) se degradaron de `01. ACTIVACIÓN`
      a `07` por no leerlos; ~30 lecturas baratas recuperan la calidad conservando
      casi toda la ganancia de velocidad. Para el resto (documentos que no son
      `.eml`, o `.eml` que casan un patrón estrecho) NO hace falta confirmar `07`
      sistemáticamente.
```

- [ ] **Step 3: Paso 4 — copia por lote reanudable, timeout/async, cierre del `rcd`, y `md5:` en Modo 3** (ítems 9, 14, 13-prosa, wiring)

Reemplazar el bloque `- **exit 0** ...` del Paso 4 por:

```markdown
   - **exit 0** (client OAuth propio del despacho) → ruta PRIMARIA `rclone rcd`:
     `copiar_manifiesto(remote, pares, progreso_path="01_Procesado/Sala lectura/_plan/copia-<AAAA-MM-DD-HHmm>.jsonl", usar_async=True)`
     con TODAS las filas del **plan persistido en el Paso 2-bis**. `copiar_manifiesto`
     **gestiona el `rcd` por sí solo** (lo arranca si falta y lo cierra al terminar
     si lo arrancó — no dejes un `rcd` huérfano en `:15572` ni lo levantes a mano);
     **aborta antes de tocar Drive** (`validar_pares`) si hay destinos duplicados
     (colisión de `nombre_canonico` sin resolver → vuelve al Paso 2, desambigua con
     `_2`/`_3`); escribe un **log JSONL de progreso** por fila, de modo que una
     corrida interrumpida se **reanuda** sin re-copiar lo ya hecho (ver
     "Corrida interrumpida"). `usar_async=True` no cuenta una copia grande legítima
     (>60s) como fallida.
```

Y ampliar el bloque `- **exit != 0** ...` con la nota de `md5:` para Modo 3:

```markdown
   - **exit != 0** (client compartido, o `rclone` no disponible) → copia
     secuencial server-side con `copy_path`/`cp` (más lenta, sin prerrequisito).
   - **Modo 3 (nube pura) — binario grande sin filesystem:** si NO puedes calcular
     el sha256 de un binario grande (descargar los bytes es incumplible), admite en
     su fila del `_MANIFIESTO.md` un `md5:<hash>` (el `md5` lo da la API del
     conector gratis) en la columna sha256; la PRIMERA sesión con filesystem lo
     recalcula a sha256 real. El verify (`--hash`) salta las filas `md5:` (no puede
     contrastar sha), y el catálogo las acepta (`sha_valido`).
```

- [ ] **Step 4: § Re-aplicación — párrafo "Corrida interrumpida"** (ítem 9, prosa)

Al final de la sección "Re-aplicación", añadir:

```markdown
- **Corrida interrumpida (Paso 4 a medias).** Si la copia muere antes del Paso 5,
  el `_MANIFIESTO.md` aún no existe, pero el **log JSONL** `_plan/copia-<fecha>.jsonl`
  registró cada fila `ok`/`fallido`. Para reanudar: vuelve a llamar
  `copiar_manifiesto(remote, pares, progreso_path=<el mismo jsonl>)` con el MISMO
  plan persistido (`_plan/plan-<fecha>.md`) — los `dst` ya `ok` se saltan y solo se
  copia lo pendiente. No borres el jsonl entre reintentos (es la llave de la
  reanudación); pasa a `estado: ejecutado` cuando el Paso 5 escriba el manifiesto.
```

- [ ] **Step 5: Paso 2-bis y Paso 7 — telemetría de fases** (ítem 16, prosa)

En el Paso 2-bis, tras la descripción del plan persistido, añadir:

```markdown
   Añade al pie del plan una sección **`## Telemetría de fases`** con una línea por
   fase (`clasificación`, `copia`, `índices`, `verify`) en formato
   `- <fase>: inicio <ISO-8601> · fin <ISO-8601>`; el ejecutor rellena los sellos
   de tiempo al entrar/salir de cada fase. Es prosa del plan, sin código.
```

En el Paso 7 (Reporta), añadir al final:

```markdown
   Incluye la **telemetría de fases** del plan persistido (duración de
   clasificación / copia / índices / verify) — es lo que por fin permite medir el
   A/B de velocidad limpio entre corridas (las dos pasadas de W-02VUDR quedaron sin
   medir por falta de estos sellos).
```

- [ ] **Step 6: Verificación manual del `SKILL.md`**

Re-leer el `SKILL.md` confirmando que: (a) el Paso 1-bis tiene la viñeta `a0` (exports crudos) y la excepción de lectura de hilos `.eml` en `c`; (b) el Paso 4 llama `copiar_manifiesto(..., progreso_path=..., usar_async=True)`, menciona la gestión del `rcd` y el `md5:` de Modo 3; (c) la § Re-aplicación tiene "Corrida interrumpida"; (d) Paso 2-bis y Paso 7 mencionan la telemetría de fases. `check_skills` se corre en la Task 8 (el aviso de CHANGELOG es esperado hasta entonces).

- [ ] **Step 7: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/SKILL.md"
git commit -m "docs(sala-lectura): wiring de exports crudos, lectura de hilos eml, copia reanudable/async, md5 Modo 3, telemetria"
```

---

### Task 8: Versión 1.12 + entrada de CHANGELOG + guard verde + re-empaquetar

**Por qué:** el guard `tests/test_sala_lectura_version_changelog.py` (v1.11) exige que frontmatter y CHANGELOG coincidan; este trabajo estrena la 1.12.

**Files:**
- Modify: `.claude/skills/organizar-sala-lectura/CHANGELOG.md` (entrada `1.12`)
- Modify: `.claude/skills/organizar-sala-lectura/SKILL.md` (frontmatter `version: "1.12"`)
- Modify: `dist/skills/organizar-sala-lectura.skill` (re-empaquetado)

- [ ] **Step 1: Confirmar que el guard falla antes del bump**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_sala_lectura_version_changelog.py -v`
Expected: FAIL tras añadir la entrada `1.12` al CHANGELOG y antes de tocar el frontmatter (`frontmatter=1.11 != changelog=1.12`). (Si se hace en el orden inverso, el guard lo caza igual.)

- [ ] **Step 2: Añadir la entrada `1.12` al CHANGELOG**

Al principio de `CHANGELOG.md`, tras `# Changelog — organizar-sala-lectura`:

```markdown
## 1.12 — 2026-07-22
- **`agrupar_por_hilo` no fusiona por una cifra del asunto.** Un `.eml` con una
  cifra final (`..._1_990_000.eml`) ya no se agrupa con un hilo inexistente: `_N`
  solo es sufijo de hilo si la base sin sufijo existe en el conjunto (así lo
  numera `email_export`: primero sin sufijo, luego `_2`, `_3`).
- **`emparejar_exports_whatsapp` excluye el zip crudo.** El `_export_original.zip`
  que `whatsapp_intake` deja junto al `_chat.txt` ya no recibe fila propia (en
  W-02VUDR fabricó 5 filas basura `0000-00-00`); se anota `duplicado_de` su chat.
- **Parseo estricto del `_MANIFIESTO.md` + `md5:` en Modo 3.** `parse_manifiesto`
  gana `estricto=`: una fila con nº de columnas incorrecto ya no desaparece del
  catálogo en silencio (aborta ruidosamente). El catálogo, los índices y el verify
  parsean en estricto. La columna sha256 admite `md5:<32 hex>` para binarios
  grandes en nube pura (`sha_valido`), que la primera sesión con filesystem
  recalcula.
- **`fecha_aproximada` separa el marcador `(*)` del valor.** El catálogo YAML emite
  `fecha_doc` limpia (parseable) + `fecha_aproximada: true|false` en vez de
  `"2024-06-06(*)"`.
- **Copia por lote reanudable + ciclo de vida del `rcd`.** `copiar_manifiesto`
  escribe un log JSONL de progreso por fila y reanuda una corrida interrumpida sin
  re-copiar; gestiona el `rcd` (lo cierra si lo arrancó, no deja huérfano en
  :15572); `timeout` parametrizable y modo `async` con polling para copias grandes
  (>60s ya no cuentan como fallidas).
- **Correo: se lee el representante de cada hilo `.eml` que cae al `07` por
  defecto** (una lectura por hilo) para no degradar correspondencia de activación a
  reclamaciones. **Telemetría de fases** en el plan persistido (Paso 2-bis/7) para
  medir el A/B de velocidad.
```

- [ ] **Step 3: Bump del frontmatter a 1.12**

En `SKILL.md`, frontmatter: `version: "1.12"`.

- [ ] **Step 4: Confirmar que el guard pasa**

Run: `& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest tests/test_sala_lectura_version_changelog.py -v`
Expected: PASS (`frontmatter=1.12 == changelog=1.12`).

- [ ] **Step 5: Re-empaquetar el `.skill` + `check_skills` limpio**

Run:
```bash
& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" scripts/package_skill.py .claude/skills/organizar-sala-lectura dist/skills
& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" scripts/check_skills.py
```
Expected: `organizar-sala-lectura` NO aparece en "CHANGELOG sin actualizar" ni en ".skill caducado". (El re-import del `.skill` en Cowork es un paso manual posterior.)

- [ ] **Step 6: Commit**

```bash
git add ".claude/skills/organizar-sala-lectura/SKILL.md" ".claude/skills/organizar-sala-lectura/CHANGELOG.md" dist/skills/organizar-sala-lectura.skill
git commit -m "feat(sala-lectura): version 1.12 (items 9-16 del backlog robustez/velocidad)"
```

---

### Task 9: Suite completa verde + actualizar `PLAN.md`

**Files:**
- Modify: `PLAN.md` (marcar los ítems 9-16 del backlog como hechos en `[SIGUIENTE-PRECLASIFICACION-SALA-LECTURA]`)

- [ ] **Step 1: Suite completa (conteo por junit-xml)**

Run:
```bash
& "C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe" -m pytest -q --junit-xml=.pytest-junit.xml
```
Expected: 0 failed, 0 errors. Anotar el nuevo total (previo 2281 + los tests añadidos en Tasks 1-6).

- [ ] **Step 2: Marcar el estado en `PLAN.md`**

En `PLAN.md`, bajo `[SIGUIENTE-PRECLASIFICACION-SALA-LECTURA]`: marcar `[x]` el punto "PENDIENTE (3ª sesión) — 8 ítems 9-16" con el hash del PR una vez mergeado, con puntero a `docs/superpowers/plans/2026-07-22-robustez-velocidad-sala-lectura-tdd-9-16.md`. Retirar el ítem de la Cola priorizada (fila 7) o marcarlo cerrado.

- [ ] **Step 3: Commit**

```bash
git add PLAN.md
git commit -m "docs(plan): backlog robustez sala-lectura completo — items 9-16 hechos"
```

---

## Auto-revisión

**Cobertura de los 8 ítems (9-16):**
- Ítem 9 (progreso durable + reanudación) → Task 5 (`copiar_manifiesto` + JSONL) + Task 7 Step 3/4 (Paso 4 + "Corrida interrumpida").
- Ítem 10 (leer representante de hilo `.eml` que cae al 07) → Task 7 Step 2 (Paso 1-bis.c).
- Ítem 11 (dos bugs deterministas) → Task 1 (`agrupar_por_hilo`) + Task 2 (`emparejar_exports_whatsapp`) + Task 7 Step 1 (wiring a0).
- Ítem 12 (`parse_manifiesto` estricto) → Task 3 (`estricto=` + wire en los 3 consumidores).
- Ítem 13 (Modo 3 md5) → Task 3 (`sha_valido` admite `md5:`, test md5) + Task 7 Step 3 (prosa Paso 4 / Gotcha).
- Ítem 14 (timeout/async + ciclo de vida del `rcd`) → Task 6.
- Ítem 15 (fecha `(*)` fuera del valor) → Task 4 (`fecha_aproximada` en `CatalogEntry` + catálogo + verify).
- Ítem 16 (telemetría de fases) → Task 7 Step 5 (Paso 2-bis + Paso 7, solo prosa).

**Placeholders:** ninguno — código completo y ejecutable en Tasks 1-6; Tasks 7-9 son inserciones de texto exactas + comandos.

**Consistencia de tipos:** `parse_manifiesto(texto, *, estricto=False) -> list[dict]` (Task 3) consumido por catálogo/índices/verify con `estricto=True`. `sha_valido(valor) -> bool` (Task 3) usado por `manifiesto_a_catalogo.derivar`. `CatalogEntry.fecha_aproximada: bool | None` (Task 4) ∈ `CAMPOS_EMITIDOS`. `copiar_manifiesto(remote, pares, *, progreso_path=None, gestionar_rcd=True, timeout=60, usar_async=False)` — Task 5 introduce `progreso_path`; Task 6 añade `gestionar_rcd`/`timeout`/`usar_async` (superset, sin romper la firma de la Task 5). `copiar_renombrar(remote, src, dst, *, timeout=60, async_=False)` y `esperar_job(jobid, *, timeout_total=1800, intervalo=2.0)` (Task 6).

**No romper lo cerrado (v1.11):** las Tasks 3/4/6 modifican `verificar_sala.py`/`manifiesto_a_catalogo.py`/`copiar_manifiesto_rclone.py` de forma aditiva; los tests de regresión de cada script se corren en su Task. El estricto valida columnas, no el valor del sha, así que los fixtures de CLI de verify (`aaaa`) siguen pasando; solo los fixtures de catálogo (que ahora validan sha) suben a 64-hex.

**Fuera de alcance:** el fix de raíz del plugin `expedientes-xl` para `ERROR_FILE_NOT_HYDRATED` (re-stat en frío) sigue siendo tarea del plugin (`docs/MEJORAS_FUTURAS.md`); la 3ª corrida real A/B de velocidad (medición con la telemetría del ítem 16) es seguimiento operativo, no código.

**Decisión de versión:** este trabajo estrena **1.12** (frontmatter + entrada nueva de CHANGELOG); el guard de la v1.11 garantiza la sincronía.
