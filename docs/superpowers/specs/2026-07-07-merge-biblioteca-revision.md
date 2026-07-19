---
estado: historico
dueño: Nikolai Tyukhay
---

# REVISIÓN: Plan de Merge Desktop→Drive + Sistema de Biblioteca

**Fecha:** 2026-07-07
**Documento revisado:** HANDOFF_SESION_20260707_MERGE_BIBLIOTECA.md
**Revisor:** Claude (revisión de arquitectura, gobernanza y concurrencia)
**Destino:** Nikolai (decisiones) + Claude Code (implementación post-decisiones)

---

## 0. VEREDICTO: 🟡 AMARILLO

La dirección es correcta y la gobernanza está bien pensada, pero el plan tiene **un defecto de fondo** (el merge es de 2 vías y no puede detectar borrados ni divergencia real), **una contradicción interna en la máquina de estados**, y **cuatro huecos autorreferenciales** (los propios ficheros de control no tienen regla de merge). Ninguno es fatal; todos se corrigen en diseño, antes de escribir código. No implementar tal cual.

---

## 1. HALLAZGOS CRÍTICOS (bloquean implementación)

### H1. El merge es de 2 vías: no detecta borrados ni divergencia real

El algoritmo compara solo Desktop vs Drive **ahora**. Sin una tercera referencia (el estado en el momento del checkout) es imposible distinguir:

- «Archivo Drive-only» = ¿creado en Drive después del checkout (preservar) o **borrado deliberadamente en local** (propagar borrado)? El plan siempre preserva → los borrados locales nunca se propagan y el Drive acumula basura para siempre. Un duplicado o un documento mal clasificado que Nikolai borre en local **resucita** en cada checkin.
- «Diferente» en Cat. B = ¿solo cambió un lado (merge trivial) o cambiaron **ambos** (conflicto real)? El plan lo resuelve por timestamp, que es una heurística con pérdida de datos posible (ver H6).
- Renombrados locales (p. ej. corregir la fecha de un nombre canónico `AAAA-MM-DD_...`): aparecen como borrado+nuevo → el Drive queda con **ambas** copias.

**Corrección (patrón estándar, el de todo VCS): merge de 3 vías con baseline de checkout.**
En el checkout, generar `MANIFEST_CHECKOUT.json` (inventario ruta+hash de lo copiado) y guardarlo en el Drive junto al lock. En el checkin, la lógica pasa a ser determinista:

| Local vs base | Drive vs base | Acción |
|---|---|---|
| igual | igual | SKIP |
| cambiado | igual | copiar local → Drive |
| igual | cambiado | preservar Drive |
| cambiado | cambiado | **CONFLICTO** (manual) |
| ausente (borrado local) | igual | proponer borrado en Drive (con confirmación, a papelera de Drive) |
| ausente | cambiado | CONFLICTO |
| nuevo local | — | copiar |
| — | nuevo Drive | preservar |
| mismo hash, distinta ruta | — | detectar renombrado (mover, no duplicar) |

Esto **elimina la necesidad del criterio por timestamp** (Cat. B desaparece como categoría especial) y convierte «divergente» en un caso detectable con certeza, no una sospecha. Las categorías A/B/C quedan reducidas a: (A) maestros con política especial, (resto) 3 vías uniforme.

### H2. Los ficheros de control no tienen regla de merge (riesgo autorreferencial)

Ni `_caso.md` ni `_intake_log.jsonl` aparecen en las categorías A/B/C. Consecuencias si caen en el algoritmo genérico:

- `_caso.md` **es el lock**. Si la copia local (que dice `checked_out`) machaca la del Drive durante el checkin, el estado del lock lo escribe el fichero sincronizado, no el protocolo. Estado corrupto garantizado.
- `_intake_log.jsonl` es el registro forense **append-only**. Ni overwrite ni timestamp valen: si durante el checkout se añadieron eventos en el Drive (p. ej. `intake-expediente` depositó ficheros) y también en local, cualquier regla de las tres **destruye historia**. Necesita merge por unión de líneas (dedupe por hash de línea) o, mejor, la regla de H9 (mientras `checked_out`, solo escribe un lado).

**Corrección:** lista explícita `MERGE_EXCLUSIONS` gestionada por el protocolo, no por el sync: `_caso.md`, `_intake_log.jsonl`, `MANIFEST_CHECKOUT.json`, `AUDITLOG_MERGE_*.jsonl` y `90_NOTAS_PERSONALES/` (zona reservada: excluida en su totalidad; si debe viajar, solo copia server-side vía expedientes-xl sin que el contenido pase por el modelo — decisión de Nikolai, ver §8).

### H3. La máquina de estados se contradice y tiene estados muertos

- **Contradicción concreta:** la skill `checkin-caso` valida «checked_out/modified → sync_pendiente», pero `TRANSICIONES_PERMITIDAS` solo permite `checked_out → (modified, en_drive)`. Un checkin desde `checked_out` es ilegal según la propia tabla. Bug de diseño literal.
- **`modified` es inobservable:** el estado vive en el `_caso.md` del Drive (debe vivir ahí: un lock que no ven los demás no es un lock). Nadie va a actualizar el Drive cada vez que toque un fichero local. `modified` nunca se pondrá a mano → estado muerto que miente.
- **`sync_pendiente` y `sincronizado` son transitorios:** solo existen durante la ejecución del checkin. Un estado persistido que solo es cierto durante los segundos que dura una operación no aporta control; aporta la posibilidad de quedarse pegado ahí tras un crash.
- **`conflicto → en_drive` no está definido:** ¿abandonar conflictos deja el caso medio-mergeado y el local se tira? Pérdida de trabajo silenciosa.

**Corrección: reducir a 3 estados persistidos.**

```
disponible (en_drive)  → prestado (checked_out)
prestado               → disponible   [checkin OK, o cancelación con confirmación explícita]
prestado               → conflicto    [checkin con conflictos; el local SE CONSERVA]
conflicto              → prestado     [resolver en local y reintentar checkin]
conflicto              → disponible   [solo con resolución manual registrada en CONFLICTOS_RESUELTOS.md]
```

El checkin es una **operación** (con su AUDITLOG), no un estado en el que el caso descansa. Sin estados muertos, sin contradicción, sin crash-states. Los matices «modificado/pendiente» se leen del MANIFEST + AUDITLOG, no de un campo que hay que mantener a mano.

### H4. El AUDITLOG se copia al Drive antes de terminar de escribirse

El plan lo copia «como parte de FASE 2C», pero se le siguen añadiendo eventos en FASE 4 (resoluciones de conflictos), FASE 5 (verificación) y FASE 6 (borrado). La copia del Drive queda **truncada** — precisamente la evidencia que debía sobrevivir al borrado del local. Además, 2.1 dice que aterriza en `01_Procesado/` (Cat. B) mientras el texto dice que viaja «como 2C»: incoherencia interna.

**Corrección:** el AUDITLOG se sube al Drive como **último paso explícito** (nuevo checkpoint, después de la confirmación del usuario y antes de mover a papelera), fuera del pipeline de categorías (ya está en `MERGE_EXCLUSIONS` por H2). Verificar por hash que llegó completo **antes** de tocar el local.

### H5. `core/repository_checkout.py` no puede llamar a expedientes-xl

El pseudocódigo dice «Copiar Drive → local (via expedientes-xl)» dentro de funciones Python del repo. expedientes-xl es un **conector MCP de Cowork**: el código del repo no tiene acceso a él. Tal cual está diseñado, `checkout_case()` es inimplementable.

**Corrección: partir el módulo por la frontera real.**

- `core/repository_checkout.py` = **lógica pura**: `validar_transicion()`, mutación de `CaseMeta`, generación de eventos para `_intake_log.jsonl`, cálculo del plan de merge 3 vías a partir de dos inventarios + baseline (entrada: datos; salida: lista de acciones). Cero I/O contra Drive. Esto sí es capa Core y sí es testeable.
- El **movimiento de bytes** lo hace quien tenga el conector/motor: la skill de Cowork (expedientes-xl) o un script local con rclone (ver §6). Las skills orquestan; el core decide.

Esto además preserva la regla de oro del proyecto: Cowork orquesta y hace skills; el código lo escribe Claude Code.

---

## 2. HALLAZGOS IMPORTANTES (corregir en diseño, no bloquean la dirección)

### H6. Timestamps como criterio de merge (Cat. B) es frágil

El mtime local se altera al copiar (según herramienta), el `modifiedTime` de la API de Drive y el mtime del montaje `G:` no siempre coinciden, y hay skew/zonas horarias. «El más reciente gana» puede machacar el fichero bueno. Además la API de Drive solo da MD5 para ficheros binarios: los **Google-native** (Docs/Sheets, si los hay en el caso) no tienen hash → el algoritmo queda indefinido para ellos. Con el 3 vías de H1, el timestamp deja de ser criterio de decisión (queda como dato informativo en el reporte). Los Google-native necesitan regla propia: tratarlos siempre como conflicto o excluirlos.

### H7. Cat. A hace overwrite ciego de `identidades.yaml`, que es un maestro, no un derivado

El propio documento lo etiqueta «SSOT local, debe sincronizar». Si alguien tocó la versión del Drive durante el checkout (Marta, Ana, una regeneración), el overwrite la destruye **en silencio** — contradice «nunca perder datos en Drive». El snapshot de CP1 permite recuperar, pero nadie sabrá que hay que mirar el snapshot. Con baseline: si `hash(Drive) != hash(base)`, escalar a conflicto **incluso en Cat. A**. Overwrite ciego solo para derivados regenerables puros (INDICE, CRONOLOGIA, _MANIFIESTO).

### H8. El lock no es atómico

Check-and-set sobre un fichero en Drive no es una operación atómica: dos usuarios pueden leer `disponible` a la vez y escribir `prestado` ambos. Google Drive no ofrece compare-and-swap. Mitigación proporcionada al riesgo real (2-4 usuarios conocidos, operaciones a velocidad humana): **write-then-verify con nonce** — escribir el lock con `user + timestamp + nonce` aleatorio, esperar 2-3 s (ojo al sync lag conocido del Drive), releer, y confirmar que el nonce ganador es el propio. Documentar la ventana residual como riesgo aceptado. Alternativa más visible: fichero centinela `_CHECKOUT.lock` en la raíz del caso (además del frontmatter), que cualquier humano ve al navegar el Drive.

### H9. El pipeline y la UI de FeesDefender no respetan `checked_out` — y es el punto de integración más importante

La concurrencia real en este sistema no es Nikolai-vs-Karen: es **Nikolai-en-local vs el pipeline/Streamlit/skills escribiendo en el caso del Drive** (intake, ensure_case, organizar-sala-lectura, reorg 05_CRM…). El plan no dice en ningún sitio que esas escrituras deban comprobar `estado_repositorio`. Sin eso, la biblioteca es decorativa. **Cambio requerido en el MVP** (falta en la tabla 5.1): toda escritura al caso en Drive verifica el estado; si `prestado`, rechaza o encola con aviso. Decidir política (ver §8).

### H10. Deriva interna de checkpoints

El resumen dice «11 checkpoints», §1.5 termina en CP11 (papelera) y §1.7 lista 12 con otra numeración (CP10 = V1-V6 vs CP10 = confirmación de usuario). La regla de seguridad «nunca borrar antes de CPX» depende de qué numeración rige. Congelar una única tabla canónica de checkpoints antes de implementar. Añadir el checkpoint nuevo de H4 (AUDITLOG verificado en Drive antes de papelera).

### H11. Cobertura incompleta del árbol del caso

Cat. C solo lista `00_Input/04_Manual/`. Quedan sin categoría: `00_Input/01_Drive EV`, `02_Whatsapp`, `03_Email`, `05_CRM`, `06_Entrevistas` → comportamiento indefinido. Definir **regla por defecto** (todo lo no listado = conservador 3 vías) y la exclusión total de `90_NOTAS_PERSONALES/` (H2).

### H12. Colisión de nombre del AUDITLOG

`AUDITLOG_MERGE_20260707.jsonl` colisiona si hay dos checkins del mismo caso el mismo día (reintento tras conflicto: escenario probable). Usar `AUDITLOG_MERGE_20260707T0945Z.jsonl`. Lo mismo para `Drive_snapshot_*` y `MANIFEST_BORRADO_*`. Y los timestamps del ejemplo («09:45:12») deben ser ISO 8601 completos con fecha y zona.

### H13. El snapshot completo de CP1 es caro y ruidoso

Copiar ~1,3 GB dentro del Shared Drive antes de cada merge: cuota, tiempo, y carpetas-fantasma visibles para E&V (Marta navega ese Drive). Alternativa por capas: (a) `FILE_INVENTORY.json` con hashes — siempre; (b) copia previa **solo de los ficheros que van a ser sobrescritos o borrados** a una carpeta `_snapshot/` (equivale al `--backup-dir` de rclone); (c) para el resto, el versionado nativo de Drive (revisiones) ya es el rollback. Decidir dónde vive `_snapshot/` para no ensuciar la vista de E&V.

### H14. La papelera local de FASE 6 vive en el medio menos fiable

El propio plan asume «Desktop puede borrarse/moverse». La espera de 7 días en Desktop no es un backup, es cortesía: la garantía real es la verificación por hash contra Drive (CP de H4 + V-checks). Correcto, pero decirlo — y el borrado definitivo del «día 14» necesita dueño: una tarea programada de recordatorio, no memoria humana. Detalle: §6.3 mezcla «7 días» y «día 14».

---

## 3. GOBERNANZA — mayormente limpia, con tres matices

1. **«Un hecho, un hogar» está a punto de violarse.** El estado de checkout aparece en `_caso.md` **y** en la tabla de STATUS.md. Declarar explícitamente: definición = `config.py`; **hecho vigente = `_caso.md` del Drive (única autoridad del lock)**; historia = `_intake_log.jsonl`; STATUS.md = **vista derivada regenerable** (como INDICE.md). El local nunca es autoridad de su propio lock. Con esa declaración, coherente con GOBERNANZA_FUENTES_VERDAD.md.
2. **Repo público en Git:** los tests y fixtures no pueden contener case IDs reales (W-02VND1), nombres («W-02VND1»), ni rutas de usuario. Sintéticos siempre. El documento revisado los usa como ejemplo — bien para el handoff, prohibido en el repo.
3. **`checkout_local_path` en el frontmatter de `_caso.md`** expone la ruta local de Windows de Nikolai en un Drive compartido con E&V. Riesgo menor; valorar guardar solo el nombre de máquina o nada (la ruta completa ya queda en `_intake_log.jsonl`).

Arquitectura 3 capas: se respeta **solo si** se aplica H5 (core puro, skills orquestan I/O). Reparto Cowork/Claude Code del §6.2 del plan: correcto y conforme a la regla de oro.

---

## 4. IDEMPOTENCIA — el mecanismo bueno ya está en el plan, pero es el otro

El plan propone «reanudar desde el punto de fallo leyendo el AUDITLOG». Frágil: el log está en el Desktop que acaba de morir, y un puntero de reanudación exige parsear estados ambiguos. **La propiedad fuerte ya la tiene la Mejora C:** la guardia por hash («verificar en Drive antes de copiar; SKIP si idéntico») hace el merge **re-ejecutable desde cero con convergencia**. Esa es la doctrina de recuperación: ante cualquier fallo (OAuth, crash, red), re-lanzar el checkin completo; los hechos ya hechos se saltan solos. El AUDITLOG pasa a ser **evidencia forense**, no mecanismo de recovery — más simple y más robusto.

Orden por fichero para que esto sea verdad: `log(intent)` → copiar → **verificar hash releyendo del Drive** → `log(OK)`. Si crashea entre copiar y OK, la re-ejecución detecta hash idéntico y converge. La verificación por releída post-copia además sustituye con ventaja al V6 (ratio de tamaños al 97%: ruido, no gate — eliminar o dejar como informativo). Ojo: verificar contra la **API**, no contra `G:` (sync lag conocido produce falsos negativos).

---

## 5. RESPUESTAS A LOS CINCO ESCENARIOS DE RIESGO

1. **OAuth caduca en FASE 2B:** los lotes mitigan pero no resuelven — el token puede morir en cualquier momento. Solución real: capturar el error de auth → pausar → reautenticar → re-lanzar; la guardia por hash (§4) hace la re-ejecución segura. `MANIFEST_AUTH.json` es decorativo: no predice la caducidad. Mantener FASE 0 como smoke test, sin más pretensión.
2. **Drive rechaza una copia por permisos:** `log(FAIL)`, continuar con el resto, reportar al final en el DELTA; abortar solo ante fallo sistémico (N fallos consecutivos). Nunca abortar a mitad dejando estado ambiguo por un solo fichero.
3. **`local_path` movido/borrado antes del checkin:** el caso queda `prestado` con ruta inválida. Runbook explícito: el checkin valida la existencia de la ruta; si no existe, ofrecer (a) señalar nueva ruta, o (b) cancelar checkout con aviso «el Drive queda como en el checkout; trabajo local perdido». La alerta de timeout >7 días es el mecanismo de descubrimiento. Falta este runbook en el plan: añadirlo.
4. **Dos casos en checkout en paralelo (mismo usuario):** legítimo y debe permitirse — el lock es por caso. El plan no lo dice; decirlo. Los artefactos por caso (AUDITLOG, MANIFEST) viven en la carpeta del caso, así que no colisionan entre casos (sí intra-caso mismo día: H12).
5. **Conflicto en FASE 2C:** el diseño es correcto (marcar, no tocar, preservar local, estado `conflicto`). Con H1 los conflictos pasan de «hash distinto = sospecha» a «ambos lados cambiaron = certeza», reduciendo drásticamente los falsos positivos que fatigarían a Nikolai hasta que ignore los avisos.

---

## 6. SIMPLIFICACIONES Y PATRONES ESTÁNDAR

- **Máquina de 3 estados** (H3): −50 % de estados, cero contradicciones.
- **3 vías con baseline** (H1): elimina la Cat. B y el criterio por timestamp; el algoritmo se vuelve una tabla determinista testeable como función pura.
- **rclone como motor de copia** (evaluar): el despacho ya lo usa contra estas mismas carpetas. `--checksum` (comparación por hash), `--backup-dir` (snapshot automático de todo lo sobrescrito/borrado = H13 gratis), `--dry-run` (el DELTA de FASE 3 gratis), log JSON, retry/backoff maduro, y sin el problema OAuth-por-operación de expedientes-xl. Salvedades conocidas del propio despacho: usar el remote API, **no** el montaje `G:` (falsos «corrupted on transfer»), y `--drive-skip-shortcuts` siempre. Contrapartida: rclone corre en local (lado pipeline/Claude Code), no desde Cowork — encaja con el reparto de H5.
- **Precedentes internos reutilizados correctamente:** `_intake_log.jsonl` como telemetría, patrón MANIFEST, «flujo resistente a interrupciones» (persistir antes de pull), `_audit/relocations.jsonl`. El plan es coherente con la casa.

---

## 7. ROADMAP RECOMENDADO

**Paso 0 — Diseño v2 (antes de cualquier código):** aplicar H1-H5 y congelar: tabla 3 vías, 3 estados, `MERGE_EXCLUSIONS`, tabla canónica de checkpoints, autoridad del lock = `_caso.md` Drive.

**Paso 1 — Piloto manual en W-02VND1 (Cowork, sin código nuevo):** ejecutar el procedimiento completo una vez, dirigido por checklist con gates humanos. Objetivo: descubrir lo que el diseño no ve (Google-native, permisos, sync lag, volumen real de conflictos) **antes** de congelarlo en código. Es la versión barata del «Fase 2 piloto» del plan, movida delante del código.

**Paso 2 — Código (Claude Code):** `config.py` (3 estados + transiciones), `CaseMeta`, `repository_checkout.py` **puro** (plan de merge como función de inventarios), guard de escritura del pipeline (H9), tests: transiciones + tabla 3 vías completa + doble checkout rechazado + re-ejecución converge + round-trip de serialización de `_caso.md`.

**Paso 3 — Skills Cowork:** `checkout-caso` / `checkin-caso` orquestando core + motor de copia elegido.

**Paso 4 — Diferidos (bien identificados ya en el plan):** `audit_log.py`, script de timeouts (o tarea programada), sección STATUS.md, UI Streamlit.

---

## 8. PUNTOS DE BLOQUEO — DECISIONES DE NIKOLAI

1. **¿Merge de 3 vías con baseline de checkout?** (Recomendado. Cambia el algoritmo central; sin esto, los borrados locales no se propagan nunca.)
2. **Política de borrados:** ¿se propagan al Drive con confirmación explícita, o el Drive nunca borra (solo acumula)?
3. **Política del pipeline ante `prestado` (H9):** ¿rechazar escrituras al caso, o encolar en una bandeja para aplicar tras el checkin? ¿Y quién puede hacer checkout: solo Nikolai, o también Paola/Ana desde Streamlit?
4. **`90_NOTAS_PERSONALES/`:** ¿viaja en el merge vía copia server-side (sin pasar por el modelo) o queda fuera del checkout por completo?
5. **Motor de copia:** ¿expedientes-xl desde Cowork o rclone desde local? (Determina dónde corre el merge y cómo de grave es el problema OAuth.)
6. **Snapshot:** ¿inventario + backup selectivo de sobrescritos (recomendado) o copia completa pre-merge? ¿Dónde vive `_snapshot/` para no ensuciar la vista de E&V?

---

## 9. GAP ANALYSIS — RESUMEN

**Falta:** baseline de checkout (H1), reglas para `_caso.md` / `_intake_log.jsonl` / `90_NOTAS` (H2), guard del pipeline (H9), runbook de local perdido (§5.3), verificación por hash post-copia por fichero, subida final del AUDITLOG (H4), regla por defecto para carpetas no listadas (H11), manejo de Google-native (H6).

**Sobra:** estados `modified` / `sync_pendiente` / `sincronizado` (H3), criterio por timestamp (H1/H6), V6 como gate (§4), `MANIFEST_AUTH.json` como predictor (§5.1), snapshot completo (H13), reanudación por puntero de log (§4).

**Corregir:** contradicción checked_out→sync_pendiente (H3), numeración CP (H10), destino/momento del AUDITLOG (H4), nombres con fecha-hora (H12), frontera core/conector (H5), overwrite de `identidades.yaml` (H7).

---

**FIN DE REVISIÓN** — Estado: pendiente de decisiones §8 → diseño v2 → piloto manual → implementación.
