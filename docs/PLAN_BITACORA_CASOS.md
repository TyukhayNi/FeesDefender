---
estado: aparcado
dueño: Nikolai Tyukhay
---

# Plan — Bitácora razonada por caso

> Trazado el 2026-05-21 (sesión 24).
>
> **Objetivo**: capturar la sustancia de cada sesión de trabajo sobre un
> caso (decisiones tomadas, jurisprudencia descartada, dudas pendientes,
> próximos pasos) en un único `BITACORA.md` dentro del propio expediente,
> sin volcar el chat crudo de Cowork. Optimizar señal/ruido y dejar al
> abogado una bitácora navegable cuando reabra el caso semanas o meses
> después.
>
> **Antecedentes**: la idea original era reflejar todos los chats LLM en
> la carpeta del caso. Tras análisis (chat 2026-05-21) se descartó por
> ratio señal/ruido bajo, problemas de RGPD al volcar PII no
> deliberadamente, y porque los outputs valiosos del chat ya quedan en
> los documentos finales del caso. El resumen estructurado conserva el
> valor real (proceso de razonamiento) sin arrastrar el ruido.

---

## 1. Decisiones cerradas

| # | Decisión | Razón |
|---|----------|-------|
| 1 | **Único `BITACORA.md` por caso, append cronológico** (entrada más reciente arriba) | Búsqueda directa con Ctrl+F, exportable, sin navegar carpetas. |
| 2 | **Ámbito: Cowork principal, Claude Code opcional** | El trabajo legal sobre casos vive en Cowork. Claude Code se ejerce sobre el repo, no sobre casos — la integración en Claude Code queda disponible pero rara vez se invocará. |
| 3 | **Trigger: manual + automático al cierre** | Skill / slash command `/bitacora` invocable a demanda + hook al `/cierre` que pregunta «¿bitácora para qué caso?» si la sesión está asociada a un caso. |
| 4 | **Generación vía Haiku** (no Sonnet) | El resumen es estructurado y mecánico — Haiku da calidad suficiente, latencia baja, coste despreciable. Si se detecta pérdida de matiz, escalar a Sonnet. |
| 5 | **Sin anonimización al volcar** | El `BITACORA.md` vive dentro del propio caso, donde ya conviven documentos con PII. Anonimizar la bitácora es overkill y rompe la trazabilidad. El fichero hereda el régimen del expediente (gitignored vía `data/CASOS/`). |
| 6 | **Estructura de cada entrada: esquema fijo** | Ver §3. Prompt cerrado, sin libertad creativa del modelo. |
| 7 | **No archiva el chat crudo** | Se descarta dump JSON/JSONL dentro del caso. Como red de seguridad opcional cara a futuro: backup global mensual de `local-agent-mode-sessions\` fuera del proyecto (anotado como mejora #26 en `docs/MEJORAS_FUTURAS.md`, no parte de este plan). |
| 8 | **Ubicación: raíz del caso** | `BITACORA.md` directamente en la carpeta del caso (al lado de `_caso.md`). No es zona del core (núcleo del pipeline) ni zona del abogado (`90_NOTAS_PERSONALES/`) — es zona de proceso de trabajo. Convención propia. |
| 9 | **Cero acoplamiento con el core del pipeline** | Ningún módulo de `core/` (anon, sudespacho, intake, …) lee ni escribe `BITACORA.md`. La generación es responsabilidad de un módulo aislado `core/bitacora/`. |
| 10 | **Idempotencia y reversibilidad** | Si el usuario cancela durante la pregunta «¿qué caso?», nada se escribe. Si confirma y luego edita el `BITACORA.md` a mano, la siguiente entrada respeta el contenido previo (append, no rewrite). |

---

## 2. Arquitectura

### 2.1 Capas

```
Cowork / Claude Code (UI)
    │
    │  /bitacora <ref-caso>          ← invocación manual
    │  o
    │  /cierre → pregunta ¿bitácora?  ← invocación automática
    │
    ▼
core/bitacora/                       ← módulo nuevo, aislado
    ├── api.py        ← fachada pública: generar_entrada(case_id, transcripcion)
    ├── extractor.py  ← recupera la transcripción de la sesión activa
    ├── resumidor.py  ← llamada Haiku con prompt fijo de §3
    └── persistencia.py ← append al BITACORA.md del caso
        │
        ▼
data/CASOS/<CIUDAD>/<case_id>/BITACORA.md
```

### 2.2 Cómo obtener la transcripción de la sesión

Dos rutas según entorno:

**Cowork** — las sesiones se persisten en JSON estructurado bajo
`%APPDATA%\Claude\local-agent-mode-sessions\<workspace>\<session_id>\`.
La sesión activa se identifica por:

- variable de entorno o señal expuesta por el cliente (a investigar — ver
  §6 «Investigación previa»);
- o, si no hay señal nativa, el directorio con `mtime` más reciente bajo
  el workspace correspondiente al folder montado.

**Claude Code** — sesiones en `~/.claude/projects/<encoded-path>/<session>.jsonl`.
El propio Claude Code expone `$CLAUDE_SESSION_ID` y `$CLAUDE_PROJECT_DIR`,
suficiente para localizar el fichero exacto.

Tras localizar la sesión, `extractor.py` reduce a turnos `user` y
`assistant`, descarta tool calls (sin perder los resultados textuales
relevantes), y entrega texto plano al `resumidor.py`.

### 2.3 Asociación caso ↔ sesión

Estrategia jerárquica, en orden:

1. **Argumento explícito** — si el usuario invoca `/bitacora SaRS1`, la
   asociación está dada. No hay heurística.
2. **Workspace montado** — si Cowork se abrió con un folder montado que
   matchea `data/CASOS/<ciudad>/<case_id>/`, el case_id se deriva del
   path. Cubre el flujo dominante (Nikolai trabajando un caso concreto).
3. **Detección por mención** — escanear la transcripción buscando
   referencias `W-XXXXXX`, códigos `<CIUDAD><EQUIPO><TIPO>\d+` o nombres
   exactos de promoción. Si hay match único, sugerirlo. Si hay múltiples,
   preguntar al usuario.
4. **Pregunta explícita** — fallback. El hook de `/cierre` siempre
   pregunta antes de escribir, incluso si las heurísticas dieron match.

### 2.4 Generación del resumen

Llamada Haiku con prompt fijo del §3. Sin contexto adicional del caso
(el resumen es sobre la sesión, no sobre el caso). Coste estimado
< 0,01 € por entrada. Modelo: `claude-haiku-4-5` (ver fallback en §5).

### 2.5 Persistencia

Append en cabeza del `BITACORA.md`. Si el fichero no existe, crearlo con
cabecera mínima:

```markdown
# Bitácora — <case_id>

> Bitácora razonada del caso. Cada entrada resume una sesión de trabajo
> con LLM. Generada por `core/bitacora/`. Editable a mano.

---
```

Cada entrada nueva se inserta tras la cabecera con separador `---` antes
y después. Atomic write (escribir a `.tmp` + rename) para evitar dejar
el fichero corrupto si se interrumpe.

---

## 3. Esquema de una entrada

Plantilla fija que el prompt del `resumidor.py` debe producir:

```markdown
## 2026-05-21 · Claude Sonnet 4.6 · Cowork · sesión <id-corto>

**Qué hicimos**
- viñeta 1 (acción concreta, qué documento se generó / qué se analizó / qué se decidió)
- viñeta 2
- viñeta 3 (máx 5)

**Decisiones tomadas y por qué**
- decisión + breve justificación (1-2 líneas)
- decisión + breve justificación

**Dudas pendientes / siguientes pasos**
- pendiente concreto, accionable
- pendiente concreto, accionable

**Documentos generados o tocados**
- `02_Analisis/_ficha_operacion.xlsx` — pre-rellenada con datos cliente
- `09_Borradores/contestacion_v1.md` — borrador inicial recibido del frontier

---
```

Reglas del prompt:

1. **No inventar**. Si una sección no aplica, omitirla (no escribir "no
   procede"). Mejor 2 secciones sólidas que 4 con relleno.
2. **Brevedad por encima de exhaustividad**. Máx 200 palabras por
   entrada. Si la sesión fue muy productiva, lo importante es lo
   estructural, no recapitular cada turno.
3. **Anclaje en evidencia**. Los documentos generados / tocados se
   listan con su path relativo al caso. Los demás puntos pueden ser
   más libres pero deben referirse a hechos de la sesión, no a
   especulaciones.
4. **Cero formato decorativo**. Sin emojis. Sin negritas dentro del
   cuerpo. Cabeceras de sección sí (las del esquema). Lo mínimo
   necesario para que se lea bien en Markdown plano.

---

## 4. Fases de implementación

| Fase | Alcance | Coste estimado | Bloqueante |
|------|---------|----------------|------------|
| F1 | Módulo `core/bitacora/` con fachada `generar_entrada(case_id, transcripcion_txt) → ruta_md`. Prompt Haiku fijo. Persistencia atomic write con append en cabeza. Tests con fixtures de transcripciones sintéticas. | 1 sesión | — |
| F2 | Extractor de Cowork: dado un session_id (o auto-detección), produce la transcripción reducida a turnos user/assistant. | 0,5 sesión | F1 |
| F3 | Slash command / skill `bitacora` en Cowork: pide ref caso, llama extractor + fachada, devuelve diff de la entrada generada para confirmación, escribe al confirmar. | 1 sesión | F1 + F2 |
| F4 | Integración con `/cierre` (hook al cerrar sesión): si workspace montado matchea un case_id o si hay menciones explícitas, ofrecer bitácora antes de cerrar. | 0,5 sesión | F3 |
| F5 | Extractor + slash command para Claude Code (opcional). Usar `$CLAUDE_SESSION_ID`. Hook `SessionEnd` nativo. | 0,5 sesión | F1 |
| F6 | Polish: comando para regenerar entrada (overwrite explícito), comando para listar entradas de un caso, atajo `/bitacora-ultima` que muestra la última entrada de un caso. | 0,5 sesión | F1-F4 |

**Ruta crítica**: F1 → F2 → F3 → F4. F5 y F6 opcionales.

**Total estimado en ruta crítica**: 3 sesiones cowork.

---

## 5. Criterios de aceptación por fase

### F1 — Módulo core aislado

- `python -m pytest tests/test_bitacora_*.py -q` verde.
- Fachada con firma estable: `generar_entrada(case_id: str, transcripcion: str, modelo: str = "claude-haiku-4-5") -> Path`.
- Mock de la llamada al modelo en tests (no llamadas reales al endpoint).
- Atomic write verificado: si se interrumpe la escritura, el
  `BITACORA.md` previo queda intacto.
- Cobertura del prompt: prompt vive en `core/bitacora/prompts/resumen.md`,
  versionado y editable sin tocar código.

### F2 — Extractor Cowork

- Función `extraer_transcripcion(session_path: Path) -> str` que dado
  un path de sesión Cowork devuelve texto plano.
- Función `localizar_sesion_activa() -> Path | None` que devuelve la
  sesión con `mtime` más reciente del workspace actual.
- Tests con fixtures (JSON sintético + JSON real anonimizado de una
  sesión propia).

### F3 — Slash command Cowork

- Skill `bitacora` en `.claude/skills/bitacora/` con SKILL.md que
  describa los disparadores.
- Comportamiento end-to-end manual:
  1. `/bitacora SaRS1` → genera entrada en menos de 30 s.
  2. Muestra preview en chat.
  3. Pide confirmación antes de persistir.
  4. Tras `OK`, escribe en `data/CASOS/Santander/SaRS1 - ... /BITACORA.md`.
  5. Devuelve enlace `computer://` al fichero.
- Si el case_id no existe en `data/CASOS/`, error claro.

### F4 — Hook al cierre

- Modificar `scripts/session_close.py` para que, antes de cerrar,
  detecte si la sesión está asociada a un caso (vía workspace montado
  o menciones).
- Si hay match, mostrar pregunta «¿generar bitácora para `<case_id>`?
  [Y/n]».
- Si la sesión no está asociada a ningún caso, saltar silenciosamente.
- Si hay ambigüedad (varios case_id mencionados), listar y pedir
  elección.
- Compatible con `/cierre` slash command.

### F5 — Claude Code (opcional)

- Hook nativo `SessionEnd` configurado en `.claude/settings.json`.
- Comando `bitacora` disponible mediante `.claude/commands/bitacora.md`.
- Equivalente funcional al de Cowork pero usando `$CLAUDE_SESSION_ID` y
  el JSONL en lugar del JSON Cowork.

### F6 — Polish

- `/bitacora-ultima SaRS1` muestra la última entrada sin escribir.
- `/bitacora-regenerar SaRS1` regenera la última entrada (preserva el
  resto del fichero).
- Comando `python -m core.bitacora.cli list <case_id>` lista todas las
  entradas con fecha + título.

---

## 6. Investigación previa (pre-F2)

Pendiente antes de empezar F2:

1. **¿Cómo identifica Cowork la sesión activa?** Comprobar si hay variable
   de entorno expuesta, fichero de lock, o algún marcador. Si no, asumir
   heurística `mtime` más reciente.
2. **Schema del JSON de sesión Cowork**. Confirmar campos:
   - turnos `user` / `assistant` / `tool_use` / `tool_result`.
   - timestamp por turno.
   - modelo usado por turno.
   - flag de cancelación o sesión incompleta.
3. **Tamaño típico de una sesión Cowork** sobre un caso. Si supera 100k
   tokens al pasar a Haiku, necesitamos truncar inteligentemente (no
   simple `tail`).

Investigación = 2-4 h. Se hace antes de F2, idealmente sobre una sesión
real reciente (revisar 3-5 sesiones de Cowork del último mes).

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Cowork cambia el formato/path de sesiones sin previo aviso. | Aislar el extractor en `core/bitacora/extractor_cowork.py`. Tests sobre fixtures versionadas. Si Cowork cambia, solo cambia el extractor. |
| El usuario abandona la disciplina y deja de generar bitácoras. | Hook al `/cierre` reduce la fricción a cero. Pero si aun así no se usa, la feature simplemente no aporta valor — sin daño. |
| La llamada Haiku produce un resumen incorrecto. | Confirmación obligatoria antes de persistir (F3). Comando para regenerar (F6). El fichero queda editable a mano. |
| El `BITACORA.md` crece sin límite. | A partir de ~50 entradas, considerar archivo anual (mejora futura, no parte del MVP). Realidad: pocos casos van a llegar a esa cifra. |
| Sesiones cowork con PII se persisten en disco al volcar a la transcripción interna. | La transcripción no se persiste a disco — se mantiene en memoria, se pasa a Haiku, se descarta. El `BITACORA.md` resultante ya está dentro del caso (régimen idéntico al resto del expediente). |
| Coste API se dispara si se generan bitácoras compulsivamente. | Haiku ~0,01 €/entrada. Aunque se generen 200 entradas/mes son 2 €. No es preocupación real. |

---

## 8. Entregables al cierre del plan

- Módulo `core/bitacora/` con cobertura de tests dedicada.
- Skill `bitacora` en `.claude/skills/bitacora/`.
- Slash command `/bitacora` en Cowork y (si F5) en Claude Code.
- Hook integrado en `/cierre`.
- Documentación: este plan actualizado con notas de cierre + sección
  «Cómo usar la bitácora» en STATUS.md.
- Memoria de cierre: pequeña entrada en la memoria persistente con la
  decisión de diseño clave (resumen estructurado vs. dump crudo) para
  no re-litigarlo en el futuro.

---

## 9. Fuera de alcance (mejoras futuras)

- **Dump crudo de sesiones Cowork como red de seguridad**. Anotado como
  mejora #26 en `docs/MEJORAS_FUTURAS.md`. Idea: tarea programada que
  copia `local-agent-mode-sessions\` a un zip mensual en una carpeta
  gitignored fuera del proyecto.
- **Búsqueda full-text sobre todas las bitácoras del despacho**. Útil si
  se acumulan muchas. Indexable con `ripgrep` directamente — no requiere
  herramienta nueva. Si se vuelve frecuente, valorar índice persistente.
- **RAG local sobre bitácoras del caso** para que el pre-relleno LLM
  (plan `PLAN_PRERELLENO_LLM_VIABILIDAD.md`) tire de contexto histórico.
  Solo si se acumulan ≥10 entradas por caso y se demuestra valor real.
- **Bitácora multi-caso para sesiones que tocan varios casos a la vez**.
  El diseño actual genera una entrada por caso (replicando el resumen
  filtrado por menciones de cada uno). Si esto se vuelve frecuente y
  ruidoso, refactorizar.
