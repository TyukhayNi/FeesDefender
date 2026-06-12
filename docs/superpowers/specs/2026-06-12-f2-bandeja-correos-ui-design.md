# Diseño — F2 UI «Bandeja de correos» (§18.6 completo) + CLI thin

**Fecha:** 2026-06-12 · **Fase:** Intake procuradores F2 (última pieza) ·
**Implementación:** Claude Code · **Plan fino base:** `docs/PLAN_INTAKE_PROCURADORES_EMAIL.md` §6, §18.

## Objetivo

Cerrar F2 del intake de procuradores: la **pestaña Streamlit «Bandeja de correos»**
con la tarjeta rica de §18.6 (3 estados 🟢/🟡/🔴, checks verdes, combobox de
reasignación, vista Descartados) **+ un CLI thin** sobre `fetch_and_run`. Todo en
**dry-run**: la confirmación humana se registra en la terna de auditoría (§18.9)
pero **no escribe en el CRM** — la escritura real es F3.

## Contexto: qué existe y qué falta

Backend de F2 completo (s40, TDD, dry-run): `core/procurador_review.py` (terna +
divergencia + máquina de estados + store de cola), `core/procurador_runner.py`
(`process_email`/`run_intake`), `core/gmail_source.py` (`fetch_and_run`).

**Hallazgo que acota el alcance "nuevo":** la comparación señales↔expediente que
produce los checks verdes **ya está escrita** (`_check_signal_matches`,
`core/procurador_intake.py`), y `match_expediente` ya devuelve `datos_expediente`
y `senales_usadas`. Hoy esos datos se **descartan** en `from_intake_proposal` al
congelar el `RobotProposal`. Por tanto, lo "nuevo" se reduce a: (a) **persistir**
ese contexto en la cola, (b) una **búsqueda CRM por texto** para el combobox, (c)
una **lectura+recompute** al reasignar.

Primitivo de búsqueda reutilizable: `_autocomplete(element, term, client)` en
`core/sudespacho_relations.py` → `[{id, label, value, data}]` (cliente *legacy*
PHPSESSID; verificado import limpio 2026-06-12).

## Decisiones (cerradas con Nikolai 2026-06-12)

1. **Alcance:** §18.6 completo (tarjeta rica con checks verdes + combobox CRM).
2. **Datos de la tarjeta:** **persistir** el contexto en la cola; la tarjeta
   renderiza offline. Solo se llama al CRM al **reasignar** en el combobox.
   (Coherente con dry-run y con el snapshot que ya exige la terna §18.9; evita
   golpear el CRM en cada rerun de Streamlit.)
3. **Ubicación del core nuevo:** módulo nuevo **`core/procurador_search.py`**
   (búsqueda/lectura del combobox), separado del matcher para no acoplar el
   cliente legacy (PHPSESSID) al cliente REST (x-api-key) del matcher.
4. **«Confirmar en bloque las de alta»:** **desactivado de inicio** (plan §6:
   "empezar revisando todo"); se deja como casilla en la cabecera.

## Arquitectura (3 capas — lógica al core, UI solo orquesta)

### Core — pieza 1: persistir el contexto de la tarjeta en la cola

Ensanchar el snapshot persistido para que la tarjeta se reconstruya sin CRM.
Campos nuevos (en `RobotProposal`, que ya viaja dentro de `ReviewItem` y se
serializa con `asdict`):

- `signals: dict` — señales crudas del correo que la tarjeta muestra/compara:
  `su_ref`, `contrario`, `cliente`, `juzgado`, `num_asunto`, `tipo_procedimiento`,
  `tipo_actuacion`, `num_expediente`, `serie_expediente`. (Subconjunto serializable
  de `IntakeSignals`; **sin** `raw_llm` para no inflar el store con el JSON del LLM.)
- `datos_expediente: dict` — los `_MATCH_PROPERTIES` del expediente emparejado.
- `coincidencias: list[str]` — campos que coinciden (`senales_usadas` sin el
  prefijo de control), para pintar los checks verdes y el recuento "N datos
  coinciden".

`from_intake_proposal(email_id, proposal)` deja de tirarlos: los copia desde
`proposal.signals` y `proposal.match`. Retrocompat de lectura: `_item_from_dict`
del store usa `.get(...)` con default `{}`/`[]` cuando faltan (items viejos).

**Sin migración de datos**: la cola actual lleva PII y es gitignored/efímera; los
items previos simplemente no traen el contexto rico (tarjeta degradada hasta el
siguiente `run_intake`). Aceptable.

### Core — pieza 2: `core/procurador_search.py`

```
search_expedientes(term, *, element="expedientes_judiciales", client=None) -> list[dict]
    # wrapper fino sobre _autocomplete → [{"id": str, "label": str}]
    # element ∈ {expedientes_judiciales, expedientes_extrajudiciales, clientes}

fetch_expediente_datos(expediente_id, *, element=..., client=None) -> dict
    # query element_registries por id → dict con _MATCH_PROPERTIES
    # (mismo patrón de parseo de `values` que _search_by_num_serie)

recompute_coincidencias(signals_dict, datos_expediente) -> list[str]
    # reusa core.procurador_intake._check_signal_matches (reconstruye IntakeSignals
    # desde el dict persistido) → checks verdes del expediente reasignado
```

Cliente legacy para `search_expedientes` (autocomplete); cliente REST para
`fetch_expediente_datos`. Ambos inyectables (tests sin red).

### UI — pestaña «Bandeja de correos» (5ª tab de `streamlit_app.py`)

Añadir a la fila de tabs: `["Nuevo caso", "Casos", "Pipeline", "Visor", "Bandeja de correos"]`.

- **Login por persona:** `st.radio("Yo soy", [...])` → `set_actor(...)` al inicio
  del render. Alimenta `quien` en la terna.
- **Cabecera de triaje:** recuentos 🟢/🟡/🔴 (de `load_queue("pendiente")` por
  `confianza`) + filtro por procurador (remitente). Casilla "Confirmar en bloque
  las de alta" (desactivada de inicio).
- **3 tarjetas** (una por item pendiente), render según `proposal.confianza`:
  - 🟢 **alta:** datos del expediente con check verde por campo en `coincidencias`
    + recuento; carpeta en `selectbox`; enlace "cambiar" abre combobox colapsado;
    cuerpo compacto; botones **Confirmar** / **Descartar**.
  - 🟡 **dudosa:** combobox **abierto** (`search_expedientes`), **sin** checks,
    aviso "verifica"; **Guardar y confirmar**.
  - 🔴 **ninguna:** bloque "**datos detectados en el correo**" (desde `signals`);
    combobox vacío (toggle judicial/extrajudicial/clientes); carpeta y **Asignar y
    confirmar** **deshabilitados** hasta elegir expediente.
  - Al elegir expediente en el combobox → `fetch_expediente_datos` +
    `recompute_coincidencias` para refrescar checks y carpetas.
- **Acción → core:** construir `HumanAction` (con overrides si el humano cambió
  expediente/carpeta) → `transicionar(item, accion, motivo=...)` →
  `record_decision(proposal, action, quien=get_actor())` (terna + divergencia) →
  `upsert_queue_item(item_nuevo)`. **Dry-run**: no toca el CRM.
- **Vista "Descartados":** `st.expander` colapsado; `load_queue("descartado")`;
  fila remitente/asunto/fecha/`motivo_descarte` + "Recuperar → bandeja"
  (`transicionar(item, "recuperar")` + `upsert_queue_item`).
- **Enlace "abrir en el CRM":** URL normal del expediente (sesión propia del
  navegador de quien pincha; no comparte sesión).

UI solo orquesta: cero lógica de matching/divergencia/persistencia en Streamlit.

### CLI/scheduler thin

`scripts/intake_procuradores.py`:

```
python -m scripts.intake_procuradores [--once] [--query "..."] [--account ...]
```

Llama `fetch_and_run` y imprime recuentos (procesados / a bandeja {alta/dudosa/
ninguna} / descartados {por motivo}). **Dry-run.** Salida ASCII (gotcha cp1252
PowerShell). `fetch_fn` inyectable para smoke sin red.

**Scheduling:** se delega al SO / skill `schedule` (no demonio propio en esta
entrega). El gotcha PHPSESSID (~24 min) **solo** afecta al combobox de la UI; el
runner usa REST x-api-key y no se ve afectado.

## Tests (TDD)

**Core:**
- Round-trip del store con el snapshot ensanchado (señales/datos/coincidencias
  persisten y se releen; items viejos sin esos campos → `{}`/`[]`).
- `from_intake_proposal` copia señales+datos+coincidencias del `IntakeProposal`.
- `search_expedientes`: autocomplete mockeado → `[{id,label}]`; element toggle.
- `fetch_expediente_datos`: parseo de `values` por id (cliente REST mockeado).
- `recompute_coincidencias`: reconstruye `IntakeSignals` y delega en
  `_check_signal_matches` (varios casos: todo coincide / parcial / nada).

**CLI:** smoke con `fetch_fn` inyectado (recuentos correctos, dry-run).

**UI:** sin tests automáticos (patrón del repo); smoke manual documentado
(`run_app.bat` → pestaña Bandeja de correos sobre la cola real).

## Lo que NO entra (límites)

- **Escritura en el CRM** (relate + adjuntar): es **F3** (resolver auth nest-mail).
- **Renombrado de adjuntos + OCR + aprendizaje:** F4.
- **Demonio/scheduler persistente:** se delega al SO/`schedule`.
- **Migración de la cola vieja:** no se hace (efímera + gitignored).

## Riesgos / gotchas

- **PHPSESSID** del cliente legacy caduca (~24 min) → el combobox puede fallar; la
  UI debe degradar con mensaje accionable (renovar sesión), no romper la tarjeta.
- La API CRM solo soporta `equal`/`not-equal` (no `contains`); la búsqueda por
  texto del combobox se apoya en el **autocomplete** del CRM, no en filterGroup.
- Encoding UTF-8 sin BOM en todos los artefactos nuevos (CLAUDE.md).
