---
estado: aprobado
dueño: Nikolai Tyukhay
fecha: 2026-07-14
backlog: MEJORAS #58 (Cluster A)
---

# Diseño — Cluster A: fiabilidad de la Sala de máquina

> Disparador concreto: intake de un caso escaneado de +200 páginas + fallo real
> vivido en la sesión VALERO (se perdió la cobertura de 35 filas; el `--vision`
> resultó un no-op silencioso). Cierra `MEJORAS #58` (Cluster A del roadmap
> post-VALERO, PR #41).

## Contexto

La Sala de máquina (`core/sala_maquina.py` + `scripts/sala_maquina.py`, skill
`organizar-sala-maquina`) convierte el crudo de `00_Input/` en
`01_Procesado/02_Sala de máquina/`. Tres defectos de fiabilidad, todos
observados en vivo:

- **A1 — La cobertura se pierde en corridas incrementales.** `apply` construye el
  plan con los ya-procesados marcados `skip=True`; `ejecutar()` los salta, así que
  `cob` solo trae el delta de la corrida. `apply` reescribe `_cobertura.md` con
  `render_cobertura(cob)` → se pierden las filas previas. En cambio
  `_sala_maquina_state.json` **sí acumula** (`_estado_previo | exitosos`).
  Asimetría: el estado sobrevive, la worklist de revisión humana no.
- **A2 — `--vision` es un no-op traicionero.** El stub `_transcribir_vision` lanza
  `NotImplementedError`; `_reforzar_con_vision` lo traga en un `except Exception`
  y deja una nota "refuerzo vision falló…" por documento — aparenta un intento
  real. Quien pasa `--vision` sin cablear el transcriptor no recibe aviso claro.
- **A3 — No hay forma persistente de reforzar los dudosos.** En VALERO el refuerzo
  por visión se hizo a mano en sesión (render → transcripción → MD + estado +
  cobertura reescritos manualmente).

Invariantes que no se rompen: core puro / CLI orquesta I/O; jamás escribir en
`00_Input/` ni `90_Notas personales/` (`destino_seguro`); aislamiento de fallo por
documento (un doc que revienta no tumba el lote); idempotencia por sha.

## A1 — Cobertura acumulativa

**Principio:** la cobertura se persiste estructurada y se vuelve **simétrica con el
estado**.

- Nuevo artefacto `_cobertura.json` en la carpeta de la Sala de máquina (junto a
  `_sala_maquina_state.json`). `_cobertura.md` (en `01_Procesado/_revisar/`) pasa a
  ser una **vista derivada** de él.
- Semántica de fusión en `apply`, idéntica a la del estado (`scripts/sala_maquina.py:77`):
  - **sin `--force`:** `cob_final = fusionar_cobertura(previa, delta)` — el delta gana por `slug`.
  - **con `--force`:** `cob_final = delta` — foto fresca (nada se saltó, es autoritativo).
- El mensaje "N a revisar" y `_cobertura.md` se derivan de `cob_final`.

**Clave de fusión = `slug`** (`output_slug(rel_path, sha8)`). Consistente con el
modelo de estado por sha: si un fichero cambia de contenido cambia su sha → nuevo
slug → nueva fila; la vieja persiste igual que el estado deja shas viejos. Es una
propiedad conocida y aceptada, no un bug.

**Core (funciones puras nuevas):**
- `fusionar_cobertura(previa, nueva) -> list[DocCobertura]` — dict por `slug`, la
  nueva gana; preserva el orden (previas primero, luego nuevas no vistas).
- `cobertura_a_dicts(cob) -> list[dict]` / `cobertura_desde_dicts(ds) -> list[DocCobertura]`
  — serialización robusta (ignora claves extra, tolera ausencia de opcionales).

**CLI:** `_cobertura_previa(case_dir)` (carga `_cobertura.json`, `[]` si no existe)
y `_guardar_cobertura(case_dir, cob)` (escribe `_cobertura.json`). `apply` fusiona,
guarda json y `_cobertura.md` desde `cob_final`.

## A2 — `--vision` que avisa (fin del no-op silencioso)

- **Core:** `vision_cableada() -> bool`. El stub se marca con
  `_transcribir_vision._es_stub = True`; `vision_cableada()` devuelve
  `not getattr(_transcribir_vision, "_es_stub", False)`. Un monkeypatch de
  producción/test reemplaza la función por una sin la marca → se detecta cableado.
- **CLI:** en `apply` (y `reforzar`), si `vision` y `not sm.vision_cableada()` →
  mensaje claro + `raise typer.Exit(2)` **antes** de procesar nada.
- **Distinción limpia, deliberada:** *no cableado* = aborto ruidoso por adelantado
  (error de configuración); *cableado pero falla en el doc X* = nota blanda aislada
  y el lote sigue (comportamiento actual del core, **intacto**).

## A3 — Comando `reforzar`

Nuevo `python -m scripts.sala_maquina reforzar "<case_id>"`.

- **Visión forzada a on** + preflight `vision_cableada()` (aborta claro si no).
- **Objetivo:** entradas de `_cobertura.json` con `estado ∈ {low, empty}` **y**
  `metodo ∈ {pypdf, ocr}` (documentos con páginas renderizables; `nativo`,
  `sin_soporte` y `error` no se benefician de renderizar páginas → se saltan).
- **Ejecución:** construye el plan desde el inventario, lo filtra a las
  `rel_path` objetivo, fuerza `skip=False`, corre `ejecutar(vision=True)`.
- **Persistencia:** fusiona el delta en la cobertura previa, reescribe
  `_cobertura.json` + `_cobertura.md`, actualiza estado (`previo | éxitos`),
  registra evento `procesado_sala_maquina` con `details={"modo": "reforzar"}`.
- **Limitación honesta (documentada):** reutiliza `ejecutar`, así que **re-OCR-iza**
  los docs objetivo. Se prima corrección y reutilización de código probado sobre la
  microoptimización de no repetir OCR. Solo es útil desde un flujo que inyecta el
  transcriptor (skill / sesión Claude): el CLII pelado aborta en el preflight.

## Errores y bordes

- `reforzar` sin `_cobertura.json`: mensaje "nada que reforzar; corre `apply` primero".
- `reforzar` sin dudosos objetivo: mensaje "0 documentos a reforzar", sin cambios.
- Guard `00_Input`/`90_Notas personales`: sin cambios (todo pasa por `destino_seguro`).
- Aislamiento por documento en `reforzar`: heredado de `ejecutar` (sin código nuevo).

## Testing (TDD)

- A1: `apply` incremental acumula ambas filas en `_cobertura.md`; `--force` da foto
  fresca; unit `fusionar_cobertura` (nueva gana por slug) + round-trip de serialización.
- A2: `--vision` sin cablear aborta con `Exit` sin procesar; `vision_cableada`
  detecta stub vs monkeypatch.
- A3: `reforzar` reprocesa solo dudosos con visión (un `low`→`ok`, un `ok` intacto,
  un `nativo` no tocado); sin visión cableada aborta; actualiza estado + cobertura.
- Regresión: suite completa verde salvo los 5 fallos ambientales pre-existentes de
  `test_sudespacho_relations` (= main).

## Documentación

Actualizar `.claude/skills/organizar-sala-maquina/SKILL.md`: documentar el comando
`reforzar`, el requisito de visión cableada de `--vision`, y que la cobertura ahora
es acumulativa entre corridas.

## Fuera de alcance

- El registro único de caso estilo `index.yaml` (§H del `PLAN_MOTOR_DOCUMENTAL`, fase
  F1): `_cobertura.json` es un paso local, no ese registro. No se adelanta aquí.
- Cablear `--vision` a un transcriptor automático fuera de proceso (canal de
  inyección): queda para el flujo de la skill; aquí solo se garantiza fail-loud + el
  punto de inyección por monkeypatch.
