---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md
objeto_rev: "3"
commit: eb1b81a2bc5fc8688bed47a003a97aa4ffe79a5d
ronda: "3"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: qwzt
sha256_informe: 513e9c2288a2cc92624a52f9e665ebb018fc02796b9e57cef06d515a43ad3f6e
adjudicado_en: docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md §20
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R3.** El §1 conserva literalmente la voz del revisor. La
> adjudicación vive en el §20 del objeto, no aquí.
>
> **Independencia restablecida.** R1 y R2 las adjudicó Codex por indisponibilidad de Claude
> Code, con la advertencia `independencia_adjudicacion: debilitada-misma-familia`. Esta ronda
> vuelve a la regla ordinaria de `CLAUDE.md`: revisa Codex, adjudica Claude Code. El mandato
> de esta ronda ordenó expresamente atacar ese punto ciego antes que la rev. 3.
>
> **Montaje del revisor.** Codex leyó una copia externa del árbol completo del commit
> `eb1b81a`, obtenida con `git archive`: el repositorio quedó de solo lectura **por
> construcción**, no por contrato. Sin `.git` y sin red. La evidencia de no-mutación es el
> SHA-256 del objeto y de las dos actas previas al abrir y al cerrar, no un `git status`.

## 0. Mandato (literal, tal como se entregó)

```text
MANDATO R3, NUMERADO POR DAÑO

OBJETO
- Spec: `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, rev. 3.
- Árbol a revisar: COPIA EXTERNA, completa y de solo lectura por construcción, en
  C:\Users\tnm33\.codex\reviews\_arbol-r3-eb1b81a
  Es el árbol íntegro del commit eb1b81a2bc5fc8688bed47a003a97aa4ffe79a5d (rama codex/docs/apertura-integral-w02q38c, PR #225), obtenido con `git archive`. Incluye core/, scripts/, tests/, docs/, CLAUDE.md y AGENTS.md. No tiene `.git`: no hay nada que ensuciar y no necesitas git para revisar.
- Digests del objeto: en esa copia el fichero está en CRLF y su SHA-256 es
  081D97268AAA654929A14912A413479BF11FC4E943140DD3411DD827490C3607.
  Su forma canónica (normalizada a LF) es
  5440F8639A99D1DC3DB9FB18C4E57BC6525694D8D99E094F26A2B5824C484245.
  Verifica los dos al arrancar y decláralo. La discrepancia entre ambos es el final de línea, no un hallazgo.
- Actas previas, en la misma copia: `docs/superpowers/specs/2026-08-15-apertura-integral-r1-adversarial-review.md` y `...-r2-adversarial-review.md`. Adjudicaciones de R1 y R2: §§18-19 del objeto.
- Contrato de gobernanza de revisiones: `docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md`, en la misma copia. Léelo entero: fija qué es un acta, qué es una adjudicación y qué vocabularios son cerrados.

CONTEXTO QUE NO PUEDES IGNORAR
R1 y R2 terminaron NO-SHIP con diecisiete hallazgos. Los adjudicaste TÚ (Codex) por indisponibilidad de Claude Code, y el propio acta R2 lo declara: `independencia_adjudicacion: debilitada-misma-familia`. Esta ronda existe, en primer lugar, para atacar ese punto ciego. Trata las adjudicaciones §§18-19 como material bajo sospecha, no como hechos establecidos.

1. Audita la adjudicación, no solo el remedio. Para cada uno de los diecisiete hallazgos de R1 y R2: (a) ¿el veredicto adjudicado (confirmado / rebajado / refutado) se sostiene contra la fuente real, o se sostiene solo contra la prosa de la spec?; (b) ¿el remedio de la rev. 3 es implementable, suficiente y OBSERVABLE, o solo renombra el riesgo?; (c) ¿hay algún hallazgo marcado remediado cuyo remedio no esté realmente en el texto de la rev. 3?; (d) ¿hay algún hallazgo refutado por una razón que un revisor de otra familia no habría aceptado? Señala expresamente los que quedaron SIN VERIFICAR y hoy se leen como cubiertos.
2. Ataca la decisión central de arquitectura del §1 —completar y cablear `scripts.abrir_caso`, `scripts.crm_ficha` y los motores existentes en vez de crear un orquestador nuevo— contra el CÓDIGO REAL de core/, scripts/ y tests/ de la copia. ¿Existen las piezas que la spec supone? ¿El cableado es viable sin rediseñar identidad, CRM, intake o procesamiento documental? ¿Promete la spec capacidades que hoy no existen? Verifica en particular que ninguna fase se apoye en piezas construidas que nadie encadena: comprueba los llamadores reales, no la existencia del módulo.
3. Busca rutas nuevas de pérdida, sobrescritura, duplicación, contaminación cruzada entre casos, fuga PII/secretos, falsa custodia y efectos externos declarados completos sin readback. Incluye carreras entre staging y commit, recuperación tras crash, reejecución/idempotencia, y la cadena CRM -> `_ficha_crm.yaml` -> `_caso.md` con sus tres superficies de partes.
4. Contrasta fronteras y contratos: Gmail, Drive E&V, Sudespacho, LeadHub / repo hermano FeesDefender-crm, sala de máquina, sala de lectura, viabilidad y rama judicial. Presta atención especial a la «excepción temporal de Nikolai sin entrega probatoria» y al límite de capacidad declarado del repo hermano: ¿queda el límite bien bloqueado, o permite declarar cerrada una apertura sin paquete probatorio? Comprueba que la spec no contradiga contratos anteriores no derogados (CLAUDE.md, AGENTS.md, el contrato de gobernanza, la arquitectura dual del expediente activo, el runbook de apertura), todos presentes en la copia.
5. Revisa los criterios de aceptación y la estrategia de entrega: cada criterio debe ser demostrable por test o evidencia concreta, ninguno puede contradecir a otro, el orden no puede exigir infraestructura inexistente y no puede admitir éxito parcial disfrazado de verde.
6. Decide si la rev. 3 está lista para escribir UN plan TDD único: SHIP / LISTA-CON-CAMBIOS / REQUIERE-REVISION / NO-SHIP. Distingue defectos bloqueantes de riesgos deliberados y bien bloqueados. No diseñes un motor mayor ni amplíes el encargo.

CONTRATO ESTRICTO
- Trabaja SOLO sobre la copia externa. No toques `C:\Users\tnm33\Dev\FeesDefender` ni `C:\Users\tnm33\Dev\FeesDefender-crm` ni ningún sistema externo (Drive, Gmail, Sudespacho, LeadHub). No hay red. Si intentas un comando git contra esos repos fallará por propiedad del directorio: es deliberado, no lo sortees.
- La copia es el objeto de registro. No la modifiques. Al arrancar y al terminar, calcula el SHA-256 del objeto y de las dos actas previas: deben coincidir. Incluye esa evidencia en el informe: sustituye al `git status` limpio.
- No lances subagentes. Haz las pasadas necesarias tú mismo.
- Si ejecutas tests o experimentos, hazlo sobre una copia tuya bajo tu directorio de trabajo o el temporal, con `PYTHONDONTWRITEBYTECODE=1`, `pytest -p no:cacheprovider` y `--basetemp` en una ruta CORTA (MAX_PATH produce fallos falsos). Ningún efecto externo. Nada de tocar casos reales.
- Contrasta contra el código real y las fuentes completas, no contra el diff ni contra la seguridad con que esté redactada la spec.
- Hallazgos numerados H3-01, H3-02… ordenados por severidad y daño. Cada uno: severidad, `file:line` preciso, hecho, impacto, evidencia o reproducción, y corrección mínima. No infles nitpicks.
- Secciones obligatorias del informe: Identificación y alcance; Fortalezas; Hallazgos; Respuesta al mandato 1-6 punto por punto; Preguntas y limitaciones; Veredicto. TÚ NO ADJUDICAS: adjudica Claude Code contra la fuente. Si algo no pudiste verificar, dilo como SIN VERIFICAR — un revisor que no corre no refuta.
- Escribe el informe ÚNICAMENTE en: C:\Users\tnm33\.codex\reviews\2026-08-24-apertura-integral-r3\2026-08-24-apertura-integral-r3-adversarial-review.md
- Ese fichero no existe: no sobrescribas ningún informe previo. Formato canónico: UTF-8 sin BOM, finales LF, exactamente un salto final.
- Devuelve en el mensaje final: ruta exacta, SHA-256 canónico del informe, conteo de hallazgos por severidad, veredicto, lista breve de hallazgos y los digests del objeto antes y después. Sin ruta y digest la revisión no cuenta.
```

## 1. Informe recibido de Codex, sin modificar

Digest declarado por el revisor y verificado de forma independiente al recibirlo, contra
`C:\Users\tnm33\.codex\reviews\2026-08-24-apertura-integral-r3\2026-08-24-apertura-integral-r3-adversarial-review.md`:
513E9C2288A2CC92624A52F9E665EBB018FC02796B9E57CEF06D515A43AD3F6E.

<!-- informe-literal:inicio:qwzt -->
# Revisión adversarial R3 — apertura integral de expediente

## Identificación y alcance

- **Fecha:** 2026-08-24.
- **Objeto:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`, rev. 3.
- **Commit declarado del archivo externo:** `eb1b81a2bc5fc8688bed47a003a97aa4ffe79a5d`.
- **Copia examinada:** `C:\Users\tnm33\.codex\reviews\_arbol-r3-eb1b81a`.
- **Ronda:** R3.
- **Rol:** revisor adversarial. Este informe no adjudica R1, R2 ni R3. La adjudicación corresponde a Claude Code contra las fuentes.
- **Alcance real:** spec, actas R1/R2, gobernanza, `CLAUDE.md`, `AGENTS.md`, arquitectura dual, runbook, `PLAN.md`, y código y tests de `core/`, `scripts/`, `plugins/` y `tests/` contenidos en la copia. No se consultó el diff ni se usó Git.
- **Sistemas expresamente no tocados:** repositorios de desarrollo, repo hermano `FeesDefender-crm`, Drive, Gmail, Sudespacho y LeadHub. No hubo red ni efectos externos.

### Integridad del objeto

La forma física del objeto usa CRLF. La normalización canónica sustituye CRLF/CR por LF; esa diferencia de finales de línea no es un hallazgo.

| Fichero | SHA-256 físico al inicio | SHA-256 físico al final | SHA-256 canónico LF al inicio/final |
|---|---|---|---|
| objeto rev. 3 | `081D97268AAA654929A14912A413479BF11FC4E943140DD3411DD827490C3607` | `081D97268AAA654929A14912A413479BF11FC4E943140DD3411DD827490C3607` | `5440F8639A99D1DC3DB9FB18C4E57BC6525694D8D99E094F26A2B5824C484245` |
| acta R1 | `E30D9EF9EFABD1F822F9F67DB547217BB77C9C2FC9945BA1805F88ACA658A57F` | `E30D9EF9EFABD1F822F9F67DB547217BB77C9C2FC9945BA1805F88ACA658A57F` | `DCCD508F3AF46C68D6F0E26F1633F73D4D9A1D2CDBA3BF240F1A9D5C6589E4E2` |
| acta R2 | `55A88365DC52656A9DBBE172F923BC288984BDAE7C58A1DFAE7215D885104032` | `55A88365DC52656A9DBBE172F923BC288984BDAE7C58A1DFAE7215D885104032` | `DD969F63E49A36E29260A1F30AF8356674DF6AF8E3AB3984A329F5617011CEC5` |

Los tres SHA-256 físicos son idénticos antes y después. Esta evidencia sustituye al `git status` por tratarse de un `git archive` sin `.git`.

### Método y cobertura ejecutada

Se trazaron las promesas de la spec hasta sus llamadores reales y hasta los contratos no derogados. Las búsquedas estáticas verificaron que no existe implementación de `CaseWorkspace`, `input_generation` ni `consecutive_unchanged` en `core/`, `scripts/` o `tests/`; tampoco aparece una primitiva de lock como `filelock`, `portalocker`, `fasteners`, `msvcrt.locking` o `CreateMutex`. `estado.json` solo aparece en la spec: el único nombre próximo en código es el control ajeno `_contenido_estado.json`.

Se intentó ejecutar, sobre una copia propia corta en `%LOCALAPPDATA%\Temp\fdr3t`, la caracterización `tests/test_repository_cli_defectos.py` con `PYTHONDONTWRITEBYTECODE=1`, `pytest -p no:cacheprovider` y `--basetemp C:\Users\tnm33\AppData\Local\Temp\fdr3b`. Los siete casos terminaron en error de *setup* antes de ejecutar su cuerpo porque `core/config.py:14` importa `dotenv` y el entorno de revisión no contiene `python-dotenv`. No se instaló nada ni se usó red. Por tanto, esa cobertura dinámica queda **SIN VERIFICAR**; no refuta los defectos, que siguen caracterizados en el fuente.

## Fortalezas

1. La rev. 3 separa correctamente alta mínima y ficha completa, impide inferir al deudor desde el aviso y hace explícita la autoridad por campo (`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:498-533`).
2. El gate posterior de revisión humana queda ligado a una versión remota concreta y a una resincronización CRM → YAML → `_caso.md`; una edición posterior invalida la atestación (`:574-623`). El remedio de H2-05 es ahora observable.
3. La cuantía se define como decimal exacto y se rechazan céntimos si el contrato remoto no demuestra ida y vuelta exacta (`:190-214`, `:909-910`).
4. Drive adopta una sola semántica —espejo versionado— con historia content-addressed y tombstones, en lugar de mezclar espejo mutable y lote inmutable (`:282-298`).
5. `no_aplica_confirmado` resuelve el conflicto de tipos de viabilidad sin fabricar un XLSX (`:449-482`, `:911-912`).
6. La rama judicial queda bloqueada mientras no exista un adaptador judicial verificado; no se reutiliza silenciosamente el alta extrajudicial (`:216-230`, `:968-969`).
7. La limitación de LeadHub está redactada con honestidad: el arnés no es recolector ni paquete probatorio, y sin entrega/reverificación el caso puede ser `preparado_con_pendientes`, nunca `completo` (`:348-356`, `:876-884`).
8. La spec reconoce que `os.replace` no evita *lost updates*, exige staging disjunto y prohíbe tomar un exit 0 como prueba material (`:249-257`, `:397-405`, `:895-899`).

## Hallazgos

### H3-01 — CRÍTICA — La excepción temporal de workspace contradice el contrato dual y no puede probar ausencia de otra copia operativa

**File:line:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:105-119,1043,1175,1183-1185`; `docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md:178-201,408-477,875-934`; `core/casos/case_locator.py:26-43,72-121`; `core/case_manager.py:599-612,692-749`; `scripts/abrir_caso.py:400-428,479-484`.

**Hecho.** La rev. 3 declara que leer `estado_repositorio: disponible` en Drive, o probar un caso nuevo en Drive/Sudespacho/checkout/scratch, elimina el riesgo hasta que exista `CaseWorkspace`. El contrato dual vigente exige lo contrario: todo entrypoint mutante debe resolver primero un `CaseWorkspace`, consultar el registro privado, distinguir checkout/scratch/Drive y bloquear ambigüedad. En el código real no existe ese resolver. `path_for` devuelve una ruta inexistente como fallback, `resolve_ref` devuelve la referencia sin resolver y el estado ausente/corrupto se degrada a `disponible`; el guard vigente además desvía escrituras en vez de resolver la copia activa. La propia arquitectura sitúa el registro, el resolver estricto y la primera vertical en sus fases 1–3.

**Impacto.** Un checkout o scratch no detectable desde Drive puede coexistir con una apertura que muta el canon y servicios externos. También puede materializarse una carpeta sombra o mezclarse custodia/log en una copia distinta de los bytes. Es pérdida de unicidad del expediente activo y contaminación cruzada, no una mera limitación de compatibilidad.

**Evidencia/reproducción.** La matriz de resolución requerida está en el diseño dual `:408-450`; el fallback prohibido y el caso real W-02ZIIF están documentados en `:467-477`. En la implementación, `case_locator.path_for()` acaba en `return flat` (`core/casos/case_locator.py:26-43`) y `scripts.abrir_caso` llama `ensure_case` antes de cualquier autorización de workspace (`scripts/abrir_caso.py:479-484`). No hay ninguna aparición implementada de `CaseWorkspace` en `core/`, `scripts/` o `tests/`.

**Corrección mínima.** Retirar la afirmación de que el gate temporal elimina el riesgo y hacer predecesor de esta vertical el núcleo contractual mínimo de `CaseWorkspace`: identidad inequívoca, registro local, resolver estricto, capacidades y cero efectos en los cuatro planos. Si no se adopta ese predecesor, la apertura mutante debe quedar bloqueada; una lectura aislada de `estado_repositorio` no es una derogación suficiente del contrato dual.

### H3-02 — CRÍTICA — El “mutex interproceso” sigue siendo una propiedad sin mecanismo ni espacio de nombres seguro

**File:line:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:112-115,397-405,1008-1010,1174`; `core/case_manager.py:1020-1068`; `tests/test_repository_cli_defectos.py:127-225`.

**Hecho.** La rev. 3 exige un mutex, propietario, nonce, espera acotada y recuperación de abandono, pero no fija primitiva, ubicación, adquisición atómica, ámbito entre procesos/máquinas, regla de expiración ni prueba segura de muerte del propietario. Para un caso nuevo exige adquirir “el mutex del W-code” antes de crear la carpeta, sin decir dónde vive ese lock global ni cómo dos procesos derivan exactamente el mismo objeto. En el árbol no existe implementación o dependencia de exclusión apropiada; `_atomic_write_caso_md` declara expresamente “sin lock, sin versionado”.

**Impacto.** Dos procesos pueden creerse propietarios, publicar dos esqueletos o perder actualizaciones de manifest, log, `_caso.md` y `estado.json`. Una recuperación basada solo en antigüedad/PID puede robar un lock vivo; un proceso puede liberar el lock ajeno. Para un W-code nuevo, rutas distintas por ciudad/fallback pueden incluso producir mutex distintos.

**Evidencia/reproducción.** El test de defectos contiene escenarios de doble titular y rollback que libera lock ajeno (`tests/test_repository_cli_defectos.py:127-225`). Su ejecución dinámica quedó **SIN VERIFICAR** por falta de `python-dotenv`, pero la ausencia de la primitiva y el read-modify-replace sin lock son verificables estáticamente.

**Corrección mínima.** Especificar una primitiva concreta y su namespace estable por identidad canónica, independiente de que exista la carpeta; adquisición/renovación/liberación atómicas; prueba de titularidad; criterio de abandono que no confunda proceso vivo o PID reutilizado; y lista cerrada de escritores obligados a usarla. Añadir pruebas con dos procesos reales para caso existente, caso nuevo, crash del dueño y tentativa de liberación ajena.

### H3-03 — CRÍTICA — El protocolo durable no contiene la información ni el orden necesarios para recuperar efectos cruzados

**File:line:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:232-247,407-424,737-745,784-792,895-897,972-974,989-997,1176`; `scripts/crm_ficha.py:91-120`; `core/sync_sudespacho.py:1462-1500`.

**Hecho.** El remedio de H2-03 difiere la pieza decisiva a “el orden específico de la operación” sin definir ese orden para Gmail, Drive, Sudespacho, archivo o CRM → YAML → `_caso.md`. El esquema mínimo de `operations` solo conserva `kind`, `status`, `generation`, una lista `expected` y dos instantes. No conserva identidad del destino remoto, digest de petición, clave de reconciliación, artefactos publicados, paso alcanzado, respuesta/readback, versión previa, compensación ni resultado de cada efecto. La intención detallada descrita para el alta CRM en §5.2 tampoco cabe en el esquema mostrado.

**Impacto.** Tras un crash no puede distinguirse entre “remoto no llamado”, “remoto confirmó pero no se proyectó localmente”, “bytes publicados sin manifest”, “YAML nuevo con `_caso.md` viejo” o “relación intentada sin readback”. La reanudación puede repetir un POST, dejar una fase verde sobre artefactos incoherentes o declarar custodia completa sin poder reconstruir qué se verificó.

**Evidencia/reproducción.** El código actual ilustra la necesidad: `scripts.crm_ficha` realiza varias mutaciones y, si el GET final falla, solo avisa y aun imprime `OK ficha CRM completada` (`:91-120`). En `pull_expediente_v2`, el registro de ocurrencias se guarda antes de aplicar el guard de escritura a los bytes (`core/sync_sudespacho.py:1462-1500`). Un `operation_id` con una lista de expectativas no permite reconciliar esos estados intermedios.

**Corrección mínima.** Definir, para cada clase de operación no idempotente, su registro durable cerrado, orden de publicación, evidencia de readback, estados intermedios y algoritmo de recuperación. El registro debe identificar caso, target y petición de forma estable y enlazar cada artefacto/efecto con su `operation_id`. Los criterios de crash deben enumerar y probar cada frontera concreta; no basta una secuencia genérica.

### H3-04 — ALTA — Ningún llamador real ejecuta el flujo que la spec promete dejar sin supervisión

**File:line:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:26-43,789-792,891-897,1001-1020`; `scripts/abrir_caso.py:390-428,479-499`; `scripts/crm_ficha.py:40-120`; `scripts/sync_sudespacho.py:159-203`; `scripts/sala_lectura.py:117-118`; `plugins/gmail_mcp/server.py:361-410`.

**Hecho.** Las piezas existen de forma fragmentaria, pero no hay un propietario ejecutable del orden, la reanudación ni las dos rondas de estabilización. `scripts.abrir_caso` crea/reutiliza el caso, ejecuta una única fuente y el alta CRM inicial, y termina en `OK Caso abierto`; no llama al pull Sudespacho, Gmail, salas, viabilidad, ficha completa ni punto fijo. `scripts.crm_ficha` es otro comando aislado. `pull_expediente_v2` tiene llamadores en `sync_sudespacho`, `scheduled_sync` y otros, pero no en `abrir_caso`. Las operaciones Gmail solo están expuestas en el plugin; la sala de lectura solo es llamada por su propio CLI. La spec dice además que `estado.json` “no ejecuta fases”.

**Impacto.** “Cablear detrás de entrypoints existentes” puede producir validadores aislados sin nadie que lance la siguiente fase, reconsulte fuentes o reanude una operación. El runbook seguiría siendo el coordinador humano que el problema declara insuficiente, mientras los criterios 1 y 2 podrían ponerse verdes por comando sin demostrar una apertura integral.

**Evidencia/reproducción.** El inventario de llamadas del árbol no encuentra `pull_expediente_v2`, `sala_lectura.organizar` ni las funciones de etiquetado Gmail desde `scripts.abrir_caso`. Su último efecto es `_alta_crm(...)` seguido de `OK Caso abierto` (`scripts/abrir_caso.py:497-499`).

**Corrección mínima.** Nombrar en la spec un dueño ejecutable de la secuencia y de cada transición: puede ser un entrypoint existente ampliado o una secuencia externa explícita con un driver probado. Si se mantiene deliberadamente al operador como driver, retirar la promesa de trabajo mecánico sin supervisión y hacer que el criterio E2E pruebe esa realidad. No hace falta diseñar aquí un motor mayor; sí resolver quién llama.

### H3-05 — ALTA — Un staging antiguo puede publicarse después de uno nuevo y hacer retroceder la generación activa

**File:line:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:249-257,282-298,397-418,758-764,975-979`.

**Hecho.** La serialización impide *lost updates* simultáneos, pero no impide reordenar observaciones remotas. La spec no obliga a comparar, al adquirir el mutex, la versión/cursor remoto observado por el staging con la última observación ya comprometida. El CAS descrito compara `revision` local y fusiona estado, no establece un orden de frescura por fuente.

**Impacto.** A descarga una fotografía antigua; B descarga una nueva y publica primero; A adquiere después el lock y puede publicar su fotografía antigua como generación activa más reciente. El histórico conserva bytes, pero índices, sala de lectura y punto fijo vuelven a una vista que omite evidencia reciente. El resultado puede ser una falsa completitud sin pérdida física detectable.

**Evidencia/reproducción.** Planificación determinista: (1) A consulta Drive en versión V1 y queda en staging; (2) aparece D2; (3) B consulta V2 y compromete generación G2; (4) A obtiene el mutex y compromete G3 desde V1. Ninguna regla de `:249-257`, `:291-298` o `:758-764` rechaza el paso 4. La prueba de “unión íntegra” del criterio 41 tampoco prueba que la generación activa sea la más fresca.

**Corrección mínima.** Persistir en cada staging el cursor/versión o fotografía material de origen y, dentro del lock, compararla con la última atestación comprometida de esa fuente. Una observación anterior no puede reemplazar el puntero activo; debe descartarse o reconciliarse y volver a consultar. Añadir el interleaving A(V1)-B(V2)-A(commit) a los criterios 41, 42 y 48.

### H3-06 — ALTA — `estado.json` no conserva las dos atestaciones completas que dice acreditar

**File:line:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:625-658,709-755,758-780,992-997,1177`.

**Hecho.** §9 exige conservar dos atestaciones completas o una cadena de digests que permita reproducirlas. El esquema mantiene en `sources` una sola observación mutable por fuente y en `fixed_point.attested_rounds` solo `round_id`, `sources_digest` e instante. No existe mapa inmutable de rondas, referencia content-addressed al payload de cada ronda, digest previo ni regla de canonicalización que permita reconstruir qué fuentes, query IDs, snapshots y generaciones formaron la ronda anterior.

**Impacto.** Tras sobrescribir `sources`, el segundo digest no prueba que hubo dos rondas completas y frescas ni permite auditar una fuente saltada o cambiada. Un contador puede leerse como cubierto sin evidencia reproducible, repitiendo el defecto de H2-04 bajo nombres nuevos.

**Evidencia/reproducción.** Escribir R1 en `sources`, añadir su digest a `attested_rounds`, sobrescribir `sources` con R2 y añadir otro digest deja solo R2 más dos hashes opacos. No hay datos desde los que recomputar el digest de R1 ni comprobar que incluía todas las fuentes obligatorias.

**Corrección mínima.** Conservar cada ronda atestada como snapshot inmutable completo, o guardar una referencia content-addressed verificable a ese snapshot con canonicalización y encadenamiento definidos. `fixed_point` debe referenciar exactamente dos rondas recomputables de la misma generación.

### H3-07 — MEDIA — La retención postal máxima de siete días carece de ejecutor y evidencia tras crash

**File:line:** `docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md:553-569,932-934,998-1000,1004-1023`.

**Hecho.** La spec manda eliminar perfiles/cachés/respuestas al terminar y todo log técnico transitorio en un máximo de siete días, pero no asigna el borrado a ningún componente, arranque, tarea programada o almacén con TTL. “Al terminar” no cubre kill, corte de energía o proceso que nunca vuelve; la estrategia de entrega tampoco construye un recolector de retención.

**Impacto.** Componentes postales del domicilio y metadatos de consulta pueden persistir indefinidamente tras un crash, incumpliendo el límite declarado y ampliando la superficie de PII. El criterio 49 no tiene hoy evidencia producible más allá de una ejecución feliz.

**Evidencia/reproducción.** Crear un temporal/log y terminar el proceso entre escritura y cleanup. Sin siguiente ejecución o scheduler no hay actor que lo borre al día 7. El texto no define una prueba con reloj inyectado ni un inventario de residuos.

**Corrección mínima.** Evitar persistir cuando sea posible; usar cleanup `finally` para la ruta normal y un *janitor* nombrado y obligatorio al arranque o una tarea con TTL para residuos. Definir ubicación, timestamp autoritativo, comportamiento ante reloj anómalo y prueba con reloj inyectado que cubra éxito, fallo y crash.

## Respuesta al mandato 1–6

### 1. Auditoría de las adjudicaciones y de los remedios R1/R2

La tabla no adjudica: prepara evidencia para que Claude Code lo haga. “Se sostiene” significa que el hecho puede trazarse al código o contrato de esta copia; “SIN VERIFICAR” significa que falta la fuente externa, no que el hallazgo esté refutado.

| Hallazgo previo | Fuente real en R3 | Remedio rev. 3: suficiencia, implementación y observabilidad |
|---|---|---|
| H-01 | Se sostiene: manifest y `_caso.md` son read-modify-replace sin exclusión (`core/case_manager.py:1020-1068`). | **Insuficiente.** El mutex sigue sin mecanismo y el protocolo durable no recupera el conjunto; H3-02/H3-03. |
| H-02 | La ausencia de recolector/paquete local es verificable; el reparto de actores del repo hermano queda **SIN VERIFICAR**. | El bloqueo operativo de LeadHub sí está en `:348-356` y es observable. La autorización v3.7/`8bc09ea` solo aparece afirmada en la spec: **SIN VERIFICAR** contra el repo hermano. |
| H-03 | Se sostiene: `.pulled` puede saltar el pull actual (`core/intake_drive.py:202-230`, citado y concordante con código). | El remedio de consulta remota por ronda está en texto y es observable, pero necesita el dueño de ejecución y la prueba de rondas de H3-04/H3-06. |
| H-04 | Se sostiene: el adaptador vigente trata Drive como espejo fijo con `--inplace` (`core/config.py:529-537`; `core/intake_drive.py:257-273`). | La semántica versionada está bien definida, pero el commit no impide regresión de frescura; H3-05. |
| H-05 | Se sostiene: el loader admite una ficha mínima y `--yes` escribe (`core/crm_ficha.py:27-80`; `scripts/crm_ficha.py:76-103`). | **Suficiente como decisión deliberada de diseño:** procedencia cerrada, contradicción bloqueante, estado pendiente y revisión remota atestada. El riesgo write-before-review queda explícito, no renombrado. |
| H-06 | Se sostiene: `_alta_crm` pierde la distinción timeout-after-commit y el CLI imprime éxito (`scripts/abrir_caso.py:265-305,497-499`). | La regla de no repetir POST está en §5.2, pero el registro durable no contiene lo necesario para aplicarla de forma general; H3-03. |
| H-07 | Se sostiene: `float` y redondeo entero siguen en el código actual (`scripts/abrir_caso.py:380`; `core/sudespacho_create.py:1245-1248,1439-1442`). | **Suficiente y observable:** `Decimal`, escala máxima 2 y rechazo si el remoto no prueba céntimos. |
| H-08 | Se sostiene: no hay generación común ni `estado.json` implementado. | **Parcial.** El estado pasa a primera entrega, pero operaciones y prueba de dos rondas son insuficientes; H3-03/H3-06. |
| H-09 | Se sostiene: la rev. 1 abría una salida postal sin adaptador/contrato. | Allowlist y minimización están en texto; la retención no tiene ejecutor (H3-07) y las condiciones reales de Correos/Catastro quedan **SIN VERIFICAR** sin acceso externo. |
| H2-01 | Se sostiene contra código y tests caracterizados. | **No remediado materialmente:** propietario/nonce no sustituyen una primitiva; H3-02. |
| H2-02 | Se sostiene contra el contrato dual y el código sin `CaseWorkspace`. | **Remedio incompatible con la fuente:** el frontmatter de Drive no puede probar checkout/scratch ni conceder capacidades; H3-01. |
| H2-03 | Se sostiene: múltiples ficheros/remotos no forman una transacción. | **Remedio incompleto:** orden específico y datos de recuperación ausentes; H3-03. |
| H2-04 | Se sostiene: se necesita prueba de rondas, no solo estado actual. | `round_id` y transiciones mejoran la observabilidad, pero las rondas anteriores no son reproducibles; H3-06. |
| H2-05 | Se sostiene. | **Remediado en texto de forma suficiente y observable:** versión remota exacta, GET posterior, CAS y nueva revisión ante cambio (`:600-614`, `:784-787`). |
| H2-06 | El contrato/commit del repo hermano queda **SIN VERIFICAR**. | La rev. 3 no permite que Nikolai produzca entrega probatoria ni que esa vía llegue a `completo`; ese bloqueo sí es verificable. La existencia/vigencia de la excepción §2.1 sigue **SIN VERIFICAR**. |
| H2-07 | Se sostiene: los motores actuales son aditivos y requieren reconciliación. | **Remedio suficiente en diseño:** generación activa, retirada de huérfanos del corpus e historia preservada; su implementación deberá probar lectores e índices reales. |
| H2-08 | Se sostiene contra `INFORME_VIABILIDAD_TIPOS`. | **Remediado en texto:** `no_aplica_confirmado` es estado cerrado y criterio demostrable. |

Quedaban, por tanto, leídos como cubiertos sin verificación independiente: la autoridad/actor de H-02, la excepción externa de H2-06, las condiciones reales de los adaptadores postales y la ejecución dinámica de los siete defectos de checkout. Los remedios de H-01, H-06, H-08, H2-01, H2-02, H2-03 y H2-04 están presentes nominalmente en la rev. 3, pero no cierran el daño. No se detectó un remedio declarado que falte por completo del texto; sí remedios cuyo nombre existe y cuyo contrato operativo no.

### 2. Decisión central de arquitectura contra el código real

| Pieza supuesta | Existe | Llamadores/capacidad real |
|---|---|---|
| `scripts.abrir_caso` | Sí | Solo resuelve/crea, ejecuta una fuente y alta CRM inicial; termina en `OK Caso abierto` (`scripts/abrir_caso.py:479-499`). No encadena el resto. |
| `scripts.crm_ficha` | Sí | Carga YAML y muta relaciones/notas; el GET fallido no tumba el éxito y la revisión de relaciones es visual (`scripts/crm_ficha.py:91-120`). No implementa aún las tres superficies ni el estado candidato. |
| `pull_expediente_v2` | Sí | Lo llaman `sync_sudespacho`, `scheduled_sync`, `judicial_intake` y otros; no `abrir_caso`. El guard llega después de guardar ocurrencias (`core/sync_sudespacho.py:1462-1500`). |
| Gmail | Parcial | `create_label`, `apply_label` y `rename_label` existen solo como operaciones del plugin (`plugins/gmail_mcp/server.py:361-410`); no hay cadena de apertura. |
| Sala de lectura | Sí | `scripts/sala_lectura.py:117-118` llama al motor, pero ninguna apertura la invoca. La spec debe conservar la skill/entrypoint canónico del runbook, no legitimar por accidente el motor deprecado. |
| Sala de máquina/atomización/viabilidad | Sí, fragmentarias | Hay motores y CLIs, pero no comparten generación ni un llamador de estabilización. |
| `estado.json`, `operations`, punto fijo | No | No hay implementación en `core/`, `scripts/` o `tests/`. |
| `CaseWorkspace` | No | El contrato existe; sus fases operativas siguen pendientes. |
| Mutex nuevo | No | No se encontró primitiva ni dependencia. |

Reutilizar los motores existentes es razonable; la conclusión “por ello no hace falta dueño de coordinación” no se sigue del código. El cableado exige además rediseñar la resolución/autorización de workspace y los commits compartidos, precisamente porque identidad, intake, CRM y procesamiento resuelven rutas dentro de servicios de `core`, no solo en los CLIs (`docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md:945-953`). La rev. 3 promete capacidades inexistentes —workspace seguro, exclusión, recuperación, generación y estabilización— y no identifica quién las ejecuta. H3-01 a H3-04 impiden escribir un plan TDD único sin tomar decisiones arquitectónicas que la spec aún deja abiertas.

### 3. Nuevas rutas de daño

- **Pérdida/contaminación entre copias:** H3-01.
- **Lost update, doble inicialización y liberación ajena:** H3-02.
- **Falsa custodia y doble efecto remoto tras crash:** H3-03.
- **Éxito parcial presentado por piezas aisladas:** H3-04.
- **Regresión de la generación activa por carrera staging/commit:** H3-05.
- **Punto fijo no auditable:** H3-06.
- **Persistencia de metadatos postales tras crash:** H3-07.

La cadena CRM → `_ficha_crm.yaml` → `_caso.md` está bien orientada en `:574-614`, pero hoy no existe: el DTO solo exige `nombre` (`core/crm_ficha.py:27-80`), `scripts.crm_ficha` no escribe `_caso.md`, y el helper vigente busca contrario solo por NIF y crea si la búsqueda devuelve `None` (`core/sudespacho_relations.py:878-970`). La implementación deberá distinguir “cero candidatos concluyente” de “sin NIF/API inaccesible”; el contrato §5.2 ya ordena bloquear, por lo que no se abre un hallazgo adicional si H3-03 se corrige de forma específica.

### 4. Fronteras y contratos

- **Gmail:** la spec exige descubrimiento expansivo, jerarquía/color y clasificación jurídica previa. Las operaciones existen, pero no hay llamador ni estado común. No se verificó Gmail real.
- **Drive E&V:** el espejo versionado es coherente, pero el gate de workspace y la monotonía de la observación remota no están cerrados (H3-01/H3-05).
- **Sudespacho:** la spec correctamente exige W-code como gate y readback. El código vigente escribe/registrar antes de algunas verificaciones (`scripts/sync_sudespacho.py:159-203`; `core/sync_sudespacho.py:1462-1500`), así que es capacidad por construir, no existente.
- **LeadHub / repo hermano:** solo se pudo verificar el límite declarado dentro de esta copia. `FeesDefender-crm` v3.7 y `8bc09ea` no están en el objeto y no se accedió al hermano: **SIN VERIFICAR**. Aun así, `:348-356` bloquea correctamente `completo` si solo hay arnés o vía Nikolai sin paquete; no permite cerrar falsamente la apertura.
- **Sala de máquina y sala de lectura:** los motores actuales existen, pero la reconciliación por generación y la exclusión de derivados obsoletos son nuevas. El runbook mantiene como canónica la skill/CLI y advierte contra el motor deprecado; el plan debe fijar la lista blanca antes de cablear.
- **Viabilidad:** `no_aplica_confirmado` evita inventar informes y la decisión jurídica sigue reservada al abogado.
- **Rama judicial:** queda correctamente bloqueada sin adaptador verificado.
- **Arquitectura dual:** hay contradicción material no derogada; H3-01.
- **Runbook:** la spec pretende convertir su orden en gates, pero sin dueño ejecutable H3-04 deja la coordinación humana intacta.
- **Gobernanza:** se conserva la separación informe/adjudicación y el vocabulario cerrado. Este informe no trata sus conclusiones como adjudicadas.

### 5. Criterios de aceptación y estrategia de entrega

Leyenda: **D** = demostrable mediante test estático/unitario/contrato/E2E concreto; **B** = el criterio está bloqueado o es insuficiente por un hallazgo R3; **SV** = su fuente externa no fue verificable en esta ronda.

| Criterio(s) | Estado | Evidencia exigible / defecto |
|---|---|---|
| 1 | B | Debe existir un dueño real de la secuencia y resolver workspace; H3-01/H3-04. |
| 2 | B | Crash/reanudación requiere contratos de operación específicos; H3-03. |
| 3 | D | Inyectar exit 0 con invariantes materiales fallidas. |
| 4–5 | D | Manifest por fichero, hash y colisión de destinos. |
| 6 | D | Fixture Gmail con destinatario lista y usuario ausente. |
| 7 | D | Doble Sudespacho con W-code ajeno y universo listado/materializado. |
| 8–9 | D | Doble LeadHub que registra mutación/paquete incompleto y estados de espera. |
| 10 | B | Reconsultas y generación activa necesitan driver y orden de frescura; H3-04/H3-05. |
| 11–13 | D | Decimal/escala, matriz de tipos y enum final cerrado. |
| 14 | B | La suite E2E es concreta, pero contiene workspace, crash y punto fijo aún indefinidos; H3-01/H3-03/H3-06. |
| 15–18 | D | Resolvedor puro, exclusiones, layout y vacío/error Sudespacho con fixtures. |
| 19 | D/SV | El preflight puede bloquear el arnés; la capacidad real del hermano queda **SIN VERIFICAR**. |
| 20–22 | D | GET de campos, normalización y bloqueo postal con dobles del CRM. |
| 23 | B | Allowlist/minimización son comprobables; la retención máxima carece de ejecutor; H3-07. |
| 24 | B | Las tres proyecciones dependen del protocolo durable incompleto; H3-03. |
| 25–26 | D | GET/merge/PUT/GET y reescritura estructural de `_caso.md` con fixtures. |
| 27 | D, pero insuficiente | La ausencia del nuevo CLI es comprobable; no demuestra quién coordina. H3-04. |
| 28–32 | D | Gates de alta mínima, fuentes, identidad, Gmail y autorización única. |
| 33 | B | W-code y no-sombra dependen del resolver contractual; H3-01. |
| 34–35 | D | CLI contract tests sobre `--crm skip`, flags y evento. |
| 36 | B | Cero efectos en workspace no disponible exige `CaseWorkspace`; H3-01. |
| 37–39 | D | Procesos solapados, bloqueo judicial y relación sin readback con dobles. |
| 40 | B | Archivo multiefecto necesita registros y orden por efecto; H3-03. |
| 41 | B | Falta mutex ejecutable y no se prueba frescura del activo; H3-02/H3-05. |
| 42 | D, pero insuficiente | Historia/tombstone es demostrable; añadir el interleaving de H3-05. |
| 43 | D/SV | Preflight contra versión/contrato; vigencia externa **SIN VERIFICAR**. |
| 44 | D | Atastación remota exacta y bloqueo downstream. |
| 45–46 | B | CAS/proyección y timeout-after-commit necesitan esquema de operación suficiente; H3-03. |
| 47 | B | El esquema no conserva dos rondas recomputables; H3-06. |
| 48 | B | Invalidez/publicación tras crash y orden de frescura no están definidos; H3-03/H3-05. |
| 49 | B | Falta actor de retención y prueba de crash/reloj; H3-07. |
| 50 | B | Cablear sin CLI no resuelve workspace, mutex, operaciones ni dueño de ejecución; H3-01–H3-04. |

El orden de §15 tampoco está listo para un único plan. Su bloque 1 presupone decisiones aún abiertas de workspace, lock y recuperación; el bloque 2 “completa `crm_ficha`” antes de cerrar en el bloque 3 Drive, salas y viabilidad, que son precondiciones expresas de la ficha (`:498-503`). Se pueden construir unidades con dobles, pero no declarar completo el bloque 2 ni iniciar una apertura real del bloque 5 antes de cerrar esas dependencias. Un plan único hoy tendría que adjudicar arquitectura en vez de ejecutar una spec cerrada y admitiría verdes parciales por componente.

### 6. Decisión de preparación para plan TDD

La rev. 3 **no está lista** para escribir un plan TDD único. Hay tres defectos críticos abiertos: autorización de workspace incompatible con el contrato vigente, exclusión interproceso no especificada y recuperación multiefecto no implementable desde el esquema. Los riesgos deliberados bien bloqueados —write-before-review, LeadHub pendiente y rama judicial no disponible— no causan este veredicto. Lo causan rutas no bloqueadas de escritura en la copia equivocada, carrera, duplicación y falsa recuperación.

## Preguntas y limitaciones

1. ¿Claude Code acepta una derogación explícita del invariante dual “resolver antes de escribir”? Este informe no encuentra base técnica para aceptarla; la rev. 3 la presenta como conservación del contrato, no como derogación.
2. ¿Qué primitiva y namespace deben coordinar un W-code antes de que exista el expediente? La spec no lo decide.
3. ¿Qué entrypoint o driver ejecuta nuevas rondas y reanudaciones? El código no contiene ese llamador y la spec niega capacidad ejecutora a `estado.json`.
4. La vigencia de `FeesDefender-crm` v3.7/`8bc09ea`, el reparto real Nikolai/Marta y las condiciones de Correos/Catastro están **SIN VERIFICAR** porque las fuentes están fuera del objeto y el mandato prohíbe acceder a ellas.
5. Los siete tests de defectos de checkout quedaron **SIN VERIFICAR** dinámicamente por `ModuleNotFoundError: dotenv`; no se interpretaron como pasados ni refutados.
6. No se ejecutaron integraciones vivas ni pruebas que requirieran secretos, red o casos reales. La revisión de esas fronteras es contractual y estática.

## Veredicto

**NO-SHIP**

Conteo: **3 CRÍTICAS · 3 ALTAS · 1 MEDIA · 0 BAJAS**.

La corrección mínima previa a una nueva revisión es cerrar H3-01, H3-02 y H3-03 en la spec; definir el dueño de ejecución de H3-04; añadir monotonía de observación y evidencia reproducible de rondas para H3-05/H3-06; y asignar el borrado verificable de H3-07. Claude Code debe adjudicar cada punto contra las fuentes, en especial los dos extremos externos que aquí permanecen **SIN VERIFICAR**.
<!-- informe-literal:fin:qwzt -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-24)

Verificado contra la fuente, no contra el informe. Las rutas se refieren al árbol del commit
`eb1b81a`; las citas de la spec son a
`docs/superpowers/specs/2026-08-15-orquestador-apertura-expediente-design.md`.

**Custodia del informe.** `sha256` recomputado sobre el fichero recibido:
`513E9C2288A2CC92624A52F9E665EBB018FC02796B9E57CEF06D515A43AD3F6E`, idéntico al declarado por
el revisor. LF puro, sin BOM, exactamente un salto final. Los digests del objeto y de las dos
actas previas que el revisor declara al abrir y al cerrar coinciden entre sí.

### Afirmaciones de código, comprobadas

| Afirmación del informe | Comprobación |
|---|---|
| `CaseWorkspace` no está implementado | `grep "class CaseWorkspace\|CaseWorkspace("` en `core/`, `scripts/`, `tests/`: **0 apariciones** |
| `path_for` devuelve una ruta inexistente como fallback | `core/casos/case_locator.py:26-43` termina en `return flat`; el docstring lo declara («compatible con creación de casos nuevos») |
| `resolve_ref` devuelve la referencia sin resolver | `core/casos/case_locator.py:99-121`, `return ref` final |
| El estado ausente se lee como `disponible` | `core/case_manager.py:94` (`estado_repositorio: str = "disponible"`), `core/case_manager.py:599-602`, y `core/config.py:368` lo declara retrocompatible |
| El guard vigente desvía en vez de resolver la copia activa | `core/case_manager.py:692-727`: lee el estado del `_caso.md` **del Drive** y desvía a `_pendiente_checkin/<origen>/` |
| No existe primitiva de exclusión | Sin `filelock`, `portalocker`, `fasteners`, `LockFileEx` ni `fcntl` en `core/`, `scripts/`, `requirements*.txt`. El único `msvcrt` del árbol es `getwch` (entrada de teclado) en `core/anon/anonimizar.py:615,624` |
| `_atomic_write_caso_md` no tiene lock | `core/case_manager.py:1020-1028`: «Sin lock, sin versionado», literal en el docstring |
| Ningún llamador encadena el flujo integral | `scripts/abrir_caso.py:479-499` termina en `_alta_crm(...)` + `OK Caso abierto`. `grep "pull_expediente_v2\|sala_lectura\|sala_maquina\|organizar\|viabilidad\|crm_ficha"` sobre ese fichero: **0 apariciones** |
| `crm_ficha` imprime éxito con el GET de verificación caído | `scripts/crm_ficha.py:112-120`: el fallo emite `[AVISO]` y a continuación se imprime `OK ficha CRM completada`. El comentario del código lo declara deliberado («la verificación no debe tumbar el éxito») |
| El registro de ocurrencias se guarda antes del guard | `core/sync_sudespacho.py:1467-1479` (`ocurrencias.save()`) precede a `:1486` (`guard_escritura`) |
| El esquema de `operations` no permite reconciliar | `:702-745`: `operations` conserva `kind`, `status`, `generation`, `expected`, `started_at`, `verified_at`; sin identidad del destino remoto, digest de petición, clave de reconciliación, paso alcanzado ni resultado del readback |
| `attested_rounds` no permite recomputar una ronda | `:748-753`: solo `round_id`, `sources_digest`, `completed_at`; `sources` (`:713-725`) es **una** observación mutable por fuente |
| El mutex se exige sin primitiva ni namespace | `:397-405` pide propietario, nonce, espera acotada y recuperación de abandono; no fija primitiva, ubicación ni ámbito |
| No hay regla de monotonía por frescura | `:249-257` y `:397-418` serializan el commit, pero ninguna regla rechaza publicar una observación anterior después de una posterior |
| La retención de 7 días no tiene ejecutor | `:566-568` y criterio 49 (`:998-1000`) fijan el plazo; `:420` reconcilia **operaciones** al arrancar, no residuos. Sin janitor, scheduler ni TTL en la spec |

### Prueba dinámica que el revisor dejó SIN VERIFICAR: ejecutada

Codex no pudo correr `tests/test_repository_cli_defectos.py` (`ModuleNotFoundError: dotenv` en
su entorno). Ejecutada aquí con el venv del repo:

```text
7 xfailed, 0 xpassed
```

Los siete defectos del frontal de la biblioteca siguen vivos. Dos son directamente el daño de
H3-02: `test_defecto_doble_titular` («el write-then-verify no impide dos titulares — A relee su
propio nonce porque su push pisó el de B») y
`test_defecto_rollback_cancela_un_lock_ajeno` («el rollback cancela el lock sin comprobar que
siga siendo el propio»). La caracterización **refuerza** el hallazgo: propietario y nonce ya
existen en el lock de checkout y no bastan.

### Los dos extremos externos que el mandato le prohibía mirar: verificados

El mandato acotó a Codex a la copia, así que declaró **SIN VERIFICAR** la existencia y el
alcance de la autorización del repo hermano. Comprobado aquí:

- `FeesDefender-crm`, rama `main`: el commit `8bc09ea50e890e6dcd6c902bad0555921674034d`
  («Autoriza piloto medido de Nikolai», 2026-08-15) **existe y es ancestro de `HEAD`**.
- `C:\Users\tnm33\Dev\FeesDefender-crm\docs\superpowers\specs\2026-07-31-descarga-fichas-crm-leadhub-design.md:38-41` describe la
  v3.7 con el alcance exacto que la spec le atribuye: «excepción experimental previa y acotada
  para que Nikolai ejecute el arnés de medición con su propia cuenta, sin entrega probatoria;
  Marta conserva la operación ordinaria y subsidiaria del piloto», y expira al cerrar la
  medición. `:56-59` confirma que esa corrida «no produce ni entrega el paquete probatorio».

Por tanto la afirmación de la spec sobre el contrato hermano es **cierta**, y los `SIN
VERIFICAR` de H-02 y H2-06 quedan cerrados a favor del documento revisado.

### Lo que sigue sin verificar, y se declara

Las condiciones reales de uso del localizador de Correos y de la Sede Electrónica del Catastro
no se han comprobado en ninguna ronda: exigen leer los términos de cada servicio, no el repo.
Nadie las ha mirado, así que no se dan por cubiertas.
