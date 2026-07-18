---
estado: aprobado (brainstorming 2026-07-18)
dueño: Nikolai Tyukhay
fecha: 2026-07-18
---

# Diseño — Builds de apertura de expediente B1–B5 (FeesDefender)

> **Fuente única del diseño.** No reabrir sus decisiones sin disparador. El detalle
> operativo del flujo vive en `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`; el detalle de la API
> del CRM (endpoints, campos, enums, tags) es SSOT en `docs/INTEGRACION_SUDESPACHO.md §10–§15`.
> Higiene PII: en este documento el caso se referencia solo por `W-XXXXXX`.

## 1. Contexto y disparador

Salen de consolidar 3 aperturas E2E del 2026-07-17 (W-02T3XO, W-02TH0W, W-046G2R) y de la
decisión de Nikolai (2026-07-18). Promovidas de `docs/MEJORAS_FUTURAS.md #70` y de
`PLAN.md [SIGUIENTE-APERTURA-EXPEDIENTE]`. Objetivo: suavizar el cuello de botella recurrente
de la apertura, sobre todo la **ficha CRM completa** (hoy 5-6 llamadas manuales).

Las cinco unidades:

- **B1** — `abrir_caso`/`crm-ficha`: rellenar la **ficha CRM completa** (tags equipo+ciudad,
  cliente propio EV, contrario, colaboradores, Notas) en vez de solo el alta mínima. **El que
  más ahorra.**
- **B2** — CLI `--case-id` para el intake incremental (resolver identidad desde `_caso.md`).
- **B3** — normalizador de teléfono a 9 dígitos (mata el `HTTP 400 movil is incorrect`).
- **B4** — evento `archivado` en `INTAKE_EVENTS`.
- **B5** — auto-derivar `--team-id`/`--codigo-caso`/`--sufijo` desde `--folder-id`.

## 2. Estado del repo verificado (2026-07-18, subagente)

Todos los hechos base **confirmados** contra el código (`file:line`):

- `scripts/abrir_caso.py::_alta_crm` (`:247-288`) con `--crm api` hace **solo** el alta mínima
  (`create_expediente` + `register_expediente`); **no** importa `sudespacho_relations`.
- Las primitivas existen en `core/sudespacho_relations.py`: `create_cliente_contrario` (`:789`),
  `link_contrario` (`:856`), `ensure_contrario_vinculado` (`:875`, dedup **NIF**),
  `create_colaborador` (`:975`), `link_colaborador` (`:1233`), `ensure_colaborador_vinculado`
  (`:1273`, dedup **email**), `link_ev_mmc` (`:1194`), + variantes judiciales. **No existe**
  `ensure_contrario_vinculado_judicial`.
- **No existe** ninguna función de update/PUT de expediente en `core/`; `Numero_Expediente`
  solo se fija al crear (`_get_next_num_expediente_extrajudicial`, `max+1`).
- **No hay** normalización de teléfono: los DTOs `NuevoClienteContrario` (`:207-223`, solo
  `movil`) y `NuevoColaborador` (`:188-204`, `movil`+`telefono`) y sus escritores REST/legacy
  mandan el valor **verbatim**.
- `case_locator.resolve_ref` (`core/casos/case_locator.py:72`) resuelve por W-code en
  `meta.id_go` del `_caso.md`.
- `INTAKE_EVENTS` (`core/intake_log.py:42-70`) tiene **25 eventos**, **sin** `archivado`
  (el docstring "17 tipos" está stale).
- Las constantes de tags existen (`core/sudespacho_create.py`). **Corrección de drift:** el
  código ya define `TAG_AZUL_BARCELONA=296`, `SEVILLA=291`, `BILBAO=292`, `SAN_SEBASTIAN=293`,
  `SANTANDER=294` (`:266-272`) — la doc §11.3 dice que no existen; la doc va por detrás.
- El "PUT de tags que concatena preservando `Numero_Expediente`" **no existe en código**: es
  solo nota de diseño en `INTEGRACION §10.7`. Lo construye B1.
- CLI `scripts/abrir_caso.py`: 6 flags de identidad obligatorios (`--w-code --ciudad
  --tipo-caso --codigo-caso --sufijo --direccion`) + `--folder-id`/`--team-id` opcionales.
  `get_drive_folder_info(folder_id)` (`core/intake_drive.py:569`) ya devuelve `name`+`driveId`.

## 3. Decisiones fijadas (brainstorming 2026-07-18) — no reabrir

1. **Superficie de B1** = **subcomando reentrante separado** (`scripts/crm_ficha.py`, invocado
   `python -m scripts.crm_ficha --case-id <ref>`) **+ tags equipo+ciudad enriquecidos en el
   alta**. El alta ocurre temprano (para tener `exp_id`); contrario/colaboradores/Notas salen
   de viabilidad, que corre después → van en el subcomando. Los tags equipo+ciudad se conocen
   en el alta → van en el **payload de creación** (cero PUT de tags → cero footgun de
   `Numero_Expediente`).
2. **Fuente de datos de la ficha** = **fichero YAML de caso `_ficha_crm.yaml`**, ubicado en
   **`00_Input/` (junto a `_caso.md`)**. La sesión/skill lo pre-rellena anclado a
   viabilidad + encargo + firmas de correo; Nikolai lo revisa (gate humano antes de tocar el
   CRM); el CLI lo consume. El core queda determinista y testeable.
3. **Normalización de teléfono** = en `__post_init__` de los DTOs (helper puro
   `normalize_es_phone`). Un único punto: cubre REST + legacy + CLI + skill + tests.
4. **`crm_ficha`** = **script sibling** de `abrir_caso` (no subcomando literal dentro del
   mismo app Typer), para no romper la invocación actual `python -m scripts.abrir_caso …`.
5. **Orden de PRs** = 1 → 4 (quick wins → B2 → B1 → B5).
6. **Restricción PII:** `_ficha_crm.yaml` lleva PII real → **siempre** dentro de
   `data/CASOS/<caso>/` (gitignored); nunca al repo ni al chat.

## 4. Arquitectura (patrón biblioteca)

Se respeta el principio de dos capas: **lógica determinista en `core/` (cerebro puro), la
CLI/UI solo orquesta.** Todo cambio de `core/` va con tests (TDD).

- **Puro** (sin I/O): `normalize_es_phone`, `descomponer_case_id`, mapas de tags
  (`tag_rojo_equipo`, `tag_azul_ciudad`), `merge_expediente_update` (junto a get/update para
  evitar el ciclo `sudespacho_create → crm_ficha → sudespacho_create`), `sufijo_de_tipo_caso`,
  `codigo_de_unidad`, carga/validación del YAML → `FichaCRMInput`.
- **I/O CRM** (`core/sudespacho_create.py`): `get_expediente`, `update_expediente`
  (GET→merge→PUT); los `ensure_*`/`link_*` ya existentes en `core/sudespacho_relations.py`.
- **I/O Drive** (`core/intake_drive`): fetch del nombre de la unidad compartida (B5).
- **Orquestadores finos** (`scripts/`): `abrir_caso` (alta+intake+tags), `crm_ficha` (ficha).

Mapa de módulos:

| Capa | Fichero | Cambio |
|---|---|---|
| Core puro | `core/utils.py` | `normalize_es_phone` |
| Core puro | `core/abrir_caso.py` | `descomponer_case_id`; `ciudad` en `Identidad`; tags equipo+ciudad en `crm_payload` |
| Core puro | `core/crm_ficha.py` **(nuevo)** | `FichaCRMInput`, loader YAML |
| Core config/IO | `core/sudespacho_create.py` | `tag_rojo_equipo`, `tag_azul_ciudad`; `merge_expediente_update` (puro); `get_expediente`, `update_expediente` (IO) |
| Core IO | `core/sudespacho_relations.py` | `normalize` en `__post_init__` de los 2 DTOs |
| Core log | `core/intake_log.py` | `archivado` en `INTAKE_EVENTS` + docstring |
| Core config/IO | `core/config.py` + `core/intake_drive.py` | `sufijo_de_tipo_caso`, `codigo_de_unidad`, fetch nombre unidad compartida (B5) |
| CLI | `scripts/abrir_caso.py` | `--case-id` (B2); auto-deriva desde `--folder-id` (B5) |
| CLI | `scripts/crm_ficha.py` **(nuevo)** | orquestador de la ficha (B1) |

---

## 5. PR-1 — quick wins (B4 + B3)

### B4 — evento `archivado`

- Añadir `"archivado"` al `frozenset` `INTAKE_EVENTS` (`core/intake_log.py:42-70`).
- Corregir el docstring stale (`:9`) del conteo (25 → 26).
- **Tests:** `append_event(caso, "archivado", details=…)` no lanza; guard
  `"archivado" in INTAKE_EVENTS`.

### B3 — `normalize_es_phone`

- **`core/utils.py`:** `def normalize_es_phone(raw: str) -> str`. Reglas (conservadoras):
  1. `""`/`None`-falsy → devolver tal cual (`""`).
  2. Quitar separadores: espacios (incl. `\xa0`), `.`, `-`, `/`, `(`, `)`.
  3. Quitar prefijo de país: `+34` → drop 3; `0034` → drop 4; `34` con longitud total 11 → drop 2.
  4. **No** validar longitud (eso lo hace el CRM). No tocar números extranjeros (`+33…` se
     deja intacto).
  5. **Idempotente:** `normalize_es_phone(normalize_es_phone(x)) == normalize_es_phone(x)`.
- **Aplicación:** en `__post_init__` de `NuevoClienteContrario` (`movil`) y `NuevoColaborador`
  (`movil`, `telefono`) en `core/sudespacho_relations.py`.
- **Tests:** unit del helper (`"+34 600 123 456"→"600123456"`, `"600123456"`,
  `"0034600123456"`, fijo `"934 567 890"→"934567890"`, `""`, `"+34600123456"`, idempotencia,
  extranjero intacto) + construcción de DTO normaliza los campos.

Como B3 vive en los DTOs, **PR-3 lo hereda gratis**.

---

## 6. PR-2 — B2: `--case-id` para intake incremental

Elimina la repetición de los 6 flags de identidad en cada intake posterior (frágil ante
espaciado/tilde, RUNBOOK §5).

- **Core puro (`core/abrir_caso.py`):** `def descomponer_case_id(case_id: str) ->
  tuple[str, str, str, str]` → `(codigo, direccion, w_code, sufijo)`. Inverso de
  `componer_case_id` (`codigo - direccion (w_code) - sufijo`): `codigo` = antes del primer
  ` - `; `sufijo` = después del último ` - `; del medio `direccion (w_code)` se extrae el
  w_code de los paréntesis (regex `_W_CODE_EN_NOMBRE`) y la dirección es el resto. Valida con
  `core.utils.validate_case_id`. **Test:** round-trip `descomponer(componer(...)) == ...`,
  incl. direcciones con guiones.
- **CLI (`scripts/abrir_caso.py`):**
  - Nueva opción `--case-id <ref>` (acepta case_id canónico completo **o** W-code).
  - Los 6 flags de identidad pasan a **opcionales** (`typer.Option(None, …)`).
  - **Validación XOR:** o `--case-id`, o los 6 flags de identidad (error claro si ambos o
    ninguno).
  - Con `--case-id`: `resolve_ref(ref)` → case_id canónico → `descomponer_case_id` +
    `tipo_caso`/`ciudad` leídos del frontmatter de `_caso.md` → construir `Identidad`
    directamente (el caso **ya existe** → se salta el chequeo de colisión; no hace falta
    `--force`).
- **Tests:** Typer runner con core mockeado — resuelve por W-code y por case_id completo;
  error si ambos/ninguno; identidad reconstruida correcta.

---

## 7. PR-3 — B1: ficha CRM end-to-end (el titular)

### 7.1 Alta enriquecida con tags equipo+ciudad (`core/abrir_caso.py`)

- Añadir `ciudad: str` a `Identidad` y a `resolver_identidad(...)` (el CLI ya tiene `--ciudad`).
- `crm_payload(identidad, *, cuantia)` construye los tags así (orden como los ejemplos de
  `INTEGRACION §11.4`):
  ```python
  tags = []
  rojo = sc.tag_rojo_equipo(identidad.codigo)   # None si desconocido
  azul = sc.tag_azul_ciudad(identidad.ciudad)   # None si desconocido
  if rojo: tags.append(rojo)
  if azul: tags.append(azul)
  tags += sc.tag_defaults_for_tipo_caso(identidad.tipo_caso)  # verde + lila/azul-valoración
  ```
- **`core/sudespacho_create.py`:**
  - `def tag_rojo_equipo(codigo: str) -> str | None`: `getattr(module, f"TAG_ROJO_{codigo}",
    None)` (las constantes se llaman exactamente `TAG_ROJO_BaRS3`, etc.). **Test:** un set de
    códigos válidos mapea; código desconocido → `None`.
  - `def tag_azul_ciudad(ciudad: str) -> str | None`: dict `{"Barcelona": TAG_AZUL_BARCELONA,
    "Madrid": …, "Valencia": …, "Sevilla": …, "Bilbao": …, "San Sebastián": …, "Santander":
    …}` con normalización de la clave (strip/acentos). Devuelve `None` si desconocida. **Test.**
- **Compatibilidad:** las altas existentes ganan tags más completos (retrocompatible). Se
  actualiza `INTEGRACION §11.3` y el RUNBOOK §9 (tags en el alta, no por PUT).

### 7.2 `update_expediente` seguro (lo que pidió Nikolai)

Todo en **`core/sudespacho_create.py`** (junto a la creación del expediente; evita el ciclo
de imports con `crm_ficha`).

- **Puro:** `def merge_expediente_update(actual: dict, cambios: dict) -> dict`:
  - parte de `dict(actual)`, aplica `cambios`;
  - **garantiza** que `Numero_Expediente` se preserva del `actual` (nunca lo pone a `0`);
  - **lanza** `ValueError` si `actual` no trae un `Numero_Expediente` válido (defensa: no
    hacer un PUT que lo pierda). **Tests exhaustivos** (preserva; cambia solo lo pedido;
    lanza si falta).
- **IO:**
  - `def get_expediente(exp_id: str) -> dict`: `GET /api/element_register/extrajudiciales/
    {exp_id}` (x-api-key). **Verificar en vivo** si necesita el workaround coma-500
    (`?properties=a,b,c`).
  - `def update_expediente(exp_id: str, cambios: dict) -> dict`: `get_expediente` →
    `merge_expediente_update` → `PUT /api/element_register/extrajudiciales/{exp_id}` → devuelve
    el registro actualizado. Único punto de reescritura del expediente.
- Uso en B1: `update_expediente(exp_id, {"Notas": ficha.notas_html})`.

### 7.3 Modelo de entrada `FichaCRMInput` + YAML

- **`_ficha_crm.yaml`** (en `00_Input/`, junto a `_caso.md`; prefijo `_` = control-file que el
  pipeline ignora):
  ```yaml
  cliente_propio: EV_MMC_SPAIN        # opcional; default EV_MMC_SPAIN (id 2). OTROS → ENGEL_VOLKERS_SPAIN
  contrario:                          # el deudor = firmante del encargo (no todo co-titular)
    nombre: ...
    apellido1: ...
    apellido2: ...
    nif: ...
    email: ...
    movil: ...
    direccion: ...
    poblacion: ...
  colaboradores:                      # TL + consultores; ficha completa (móvil + fijo)
    - nombre: ...
      email: ...
      movil: ...
      telefono: ...
      nif: ...
  notas_html: "..."                   # narrativo: tipo + partes + cláusula + cuantía (plantilla NOTA_<tipo> + datos)
  ```
- **Puro (`core/crm_ficha.py`):** `@dataclass FichaCRMInput` (contrario opcional; lista de
  colaboradores; `notas_html`; `cliente_propio`) + `def cargar_ficha_yaml(path) ->
  FichaCRMInput` (parseo + validación de campos mínimos; convierte a `NuevoClienteContrario`/
  `NuevoColaborador`, que ya normalizan el teléfono por B3). **Tests** con YAML sintéticos.

### 7.4 Orquestador `scripts/crm_ficha.py`

`python -m scripts.crm_ficha --case-id <ref> [--dry-run] [--yes]`:

1. `resolve_ref(ref)` → case_id → `exp_id` (de `case_manager.get_case_status`, elemento
   extrajudicial).
2. `cargar_ficha_yaml(00_Input/_ficha_crm.yaml)` → `FichaCRMInput`.
3. `--dry-run`: imprime el plan (qué se creará/vinculará/escribirá) y sale.
4. Ejecuta (con gate `--yes`/confirm, como `abrir_caso`):
   - `link_ev_mmc(exp_id, cliente_propio_id=…)`
   - si hay contrario: `ensure_contrario_vinculado(exp_id, contrario)` (dedup NIF)
   - por cada colaborador: `ensure_colaborador_vinculado(exp_id, colab)` (dedup email)
   - `update_expediente(exp_id, {"Notas": ficha.notas_html})`
5. **GET de verificación tras cada escritura** (regla del proyecto: el 201 no prueba el
   vínculo) + reporte al usuario. Tolerancia a caída como `_alta_crm` (avisa, no revienta).
- **Tests:** Typer runner con core mockeado — flujo completo, `--dry-run`, contrario ausente,
  N colaboradores, YAML faltante (error claro).

---

## 8. PR-4 — B5: auto-derivar identidad desde `--folder-id`

En `--fuente drive_ev`, si se omiten `--team-id`/`--codigo-caso`/`--sufijo`, derivarlos;
flags explícitos siempre ganan.

- **`--team-id`** = `driveId` vía `get_drive_folder_info(folder_id).drive_id` (ya existe). Sólido.
- **`--sufijo`** = `core.config.sufijo_de_tipo_caso(tipo_caso)`: mapa canónico con casos
  especiales (`LAU_20 → "LAU 20"`) + fallback `tipo.replace("_", " ").capitalize()`
  (`VUELTA → "Vuelta"`, `NEGATIVA_ESCRITURA → "Negativa escritura"`). **Test** con los tipos
  de `config.TIPOS_CASO_ALL`. Alinea con la memoria `feedback-case-sufijo-tipo-canonico`.
- **`--codigo-caso`** = nombre de la **unidad compartida** → `codigo_de_unidad(nombre)`.
  Requiere: (a) nueva IO en `core/intake_drive.py` para leer el nombre de la unidad
  compartida desde `driveId` (`GET /drive/v3/drives/{driveId}?fields=name`), y (b) el parser
  `codigo_de_unidad(nombre_unidad) -> str`. **La regla de parseo es lossy** ("Barcelona - S3"
  → "BaRS3") y depende de los nombres reales de las unidades compartidas → **se fija en el
  build con la lista real** (llamada `drives.list` o aportada por Nikolai). Por eso B5 va
  último.

---

## 9. Riesgos y verificación en vivo

- **R1 — reentrancia de los vínculos.** Los `ensure_*` deduplican la **entidad** (contrario
  por NIF, colaborador por email) pero **re-vinculan siempre** (`link_*` tras el `find`), y
  `link_ev_mmc` también hace POST siempre. Re-ejecutar `crm-ficha` podría **duplicar la
  relación** en el CRM (no la persona). Hoy **no hay ruta REST fiable para leer relaciones**
  (`DEAD_ENDS.md`), así que no se puede pre-chequear el vínculo. **Acción:** verificar en vivo
  si el re-POST duplica; si duplica, decidir mitigación (guard de lectura si aparece ruta, o
  documentar que la parte de vínculos de `crm-ficha` se corre una sola vez). La dedup de
  entidad garantiza que **nunca se crean personas duplicadas**.
- **R2 — `get_expediente` GET-by-id.** Confirmar en vivo si necesita el workaround coma-500.
- **R3 — `update_expediente` en vivo.** Verificar con GET que `Numero_Expediente` se preserva
  y que el PUT de reemplazo total no pierde otros campos (probar sobre expediente desechable).
- **R4 — B5 `codigo_de_unidad`.** Regla lossy pendiente de los nombres reales de unidades
  compartidas.
- **Verificación en vivo obligatoria (PR-3 y PR-4):** contra un **expediente desechable** del
  CRM (o visualmente en `tnm.sudespacho.net`), porque el 201/200 no prueba el efecto.

## 10. Actualizaciones de documentación (parte del build)

- `INTEGRACION_SUDESPACHO.md §11.3`: tags azules de ciudad ya existen en código (quitar el
  aviso de "no existen").
- `INTEGRACION_SUDESPACHO.md §10.7` / `RUNBOOK §9`: tags equipo+ciudad se ponen en el **alta**
  (no por PUT); `update_expediente` ya existe para `Notas`.
- `RUNBOOK §5`: `--case-id` disponible para intake incremental (B2).
- `RUNBOOK §4`: auto-derivación desde `--folder-id` (B5).
- `PLAN.md [SIGUIENTE-APERTURA-EXPEDIENTE]`: marcar B1–B5 con hash de PR al cerrar cada uno.
- `docs/MEJORAS_FUTURAS.md #70.a`: cerrar (B4 hecho).

## 11. Fuera de alcance (YAGNI)

- **Workflow completo `core/archivar_caso.py`** (`MEJORAS #70.b`) y enum de motivos de archivo
  (`#70.c`): B4 solo añade el evento; el orquestador de archivo es otro frente.
- **Actuación facturable** en la ficha (RUNBOOK §9.6): fuera de B1 (tarifa confidencial solo
  por UI; es otro build).
- **Variantes judiciales** de la ficha (`crm-ficha` judicial): B1 es extrajudicial. El
  judicial es frente propio (`PLAN [abrir-caso] F3-judicial`).
- **Skill Claude Code `abrir-caso`**: se valora cuando B1 esté mergeado (el RUNBOOK es el
  checklist hoy).
- **Envío de email desde el CRM** (`INTEGRACION §10.9`): otro frente.

## 12. Estrategia de tests y build

- **TDD** en todo `core/` (funciones puras primero). Las funciones IO con HTTP mockeado en
  unit tests **+ verificación en vivo** en PR-3/PR-4.
- La suite debe seguir verde (baseline ~2037; los 5 fallos de `test_sudespacho_relations` son
  **ambientales**, worktree sin `.env`). Conteo por `--junit-xml` (la línea de resumen no se
  captura por tubería en este Windows).
- **Un PR por unidad** (PR-1..PR-4). Cada uno: `writing-plans` → `subagent-driven-development`
  → **revisión adversarial** (workflow) → (PR-3/PR-4) verificación en vivo del CRM. `main`
  protegida: rama + PR, `leak-scan` verde. Nunca push directo ni `--no-verify`.

## 13. Secuencia y dependencias

```
PR-1 (B4 + B3)  ──► PR-3 (B1) hereda B3 (DTOs normalizados)
PR-2 (B2)       ──► independiente de PR-1/PR-3 (CLI)
PR-3 (B1)       ──► depende de B3 (PR-1); usa tags/DTOs/update_expediente
PR-4 (B5)       ──► independiente; último por la incertidumbre de codigo_de_unidad
```

PR-1 y PR-2 son paralelizables. PR-3 tras PR-1. PR-4 al final.
