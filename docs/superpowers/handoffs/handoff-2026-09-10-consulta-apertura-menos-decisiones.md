---
tipo: handoff
estado: consumido
creado: 2026-09-10
origen: sesión de consulta del 2026-09-10 (Claude Code remoto, sin acceso a los transcripts) — lectura de los siete bloques de apertura de la bitácora de ese día (99º a 105º), de `MEJORAS #209`-`#239`, del runbook, de las filas 15 y 21 de `PLAN.md`, del §21 y §24 de la spec de apertura integral y del código de `scripts/abrir_caso.py` y `core/apertura_v1.py`
destino: Nikolai (decide el orden y las tres decisiones del §6) y la sesión de Claude Code que ejecute las piezas; lo durable se promueve a `PLAN.md` con su disparador y este fichero pasa a `consumido`
consumido_por: "PLAN.md fila #28 / bloque [SIGUIENTE-APERTURA-MENOS-DECISIONES] (promueve P5, P7 y P2 el 2026-09-11; P1, P3, P4, P6 y P8 siguen aquí sin promover)"
---

# Handoff — La apertura automatizada, medida sobre las siete aperturas del 2026-09-10, y cómo hacerla menos dependiente de las decisiones del letrado

**Andamio efímero, no fuente de verdad** (`GOBERNANZA_FUENTES_VERDAD §5`). Lo que aquí es
diagnóstico se apoya en mediciones ya escritas en la bitácora y en el backlog; lo que es
propuesta espera decisión. **No reserva ningún número de `MEJORAS`** —la lección del día es que
el número se coge al escribir, releyendo `main`— y **no toca `PLAN.md`**: la promoción es de
Nikolai.

## 0. La consulta y su premisa

La pregunta: «revisa qué se hizo para automatizar la apertura, si funcionó hoy y por qué me
pareció que no; quiero las aperturas menos dependientes de mis decisiones».

**Premisa 1 — «se hizo trabajo para automatizar la apertura»: confirmada, con alcance.**
Lo construido es la **primera vertical (V1)**: `--modo v1` de `scripts/abrir_caso.py`, que
encadena Drive E&V → pull del CRM ya registrado → sala de máquina bajo un mutex
(`scripts/abrir_caso.py::secuencia_v1`, secuenciador puro en `core/apertura_v1.py`). El alcance
lo fijó Nikolai el 2026-08-24 (spec §21): alta CRM y `crm_ficha` se difirieron a **V2**; Gmail,
LeadHub, sala de lectura, viabilidad y archivo a **V3**. **Ni V2 ni V3 se han construido.**

**Premisa 2 — «he tenido que estar encima del pipeline»: confirmada, y es estructural.** V1
automatiza el tramo que ya corría solo en segundo plano (el OCR es el 82 % del tiempo de
máquina, `[APER-67]`) y ese tiempo de máquina es ~15 % del reloj de una apertura (W-02NHNC:
14:18 de 1:37:22; W-02O7E2: 7:26 de 2:30:00, un 5 %). Lo demás —clasificar, viabilidad, ficha, verificar, reparar— sigue en
manos del operador o de una sesión que le pregunta.

**Premisa 3 — «cinco sesiones de apertura»: incompleta.** La bitácora tiene **siete** bloques de
apertura fechados el 2026-09-10: W-048U77, W-030TZY, W-02V48N, W-048UOL, W-02NHNC, W-02YZO4 y
W-02O7E2 —este último (105º, PR #333) entró en `main` mientras se escribía este handoff—.
Se han leído los siete. Los transcripts de las sesiones no están en el repo; lo leído es lo que
cada sesión dejó escrito (bloque de cierre, entradas de backlog, gotchas del runbook).

## 1. Qué hay construido, leído del código

| Tramo del runbook | Estado real | Dónde |
|---|---|---|
| §2 identidad | `--team-id`, `--codigo-caso`, `--sufijo` auto-derivados de `--folder-id` (B5); **`--direccion` a mano** | `scripts/abrir_caso.py::_autoderivar_drive_ev`; `MEJORAS #224` |
| §3 alta + Drive + OCR | **V1 cableada**: `drive` → `crm` → `sala_maquina`, mutex, `estado.json` por ronda, evento forense, `--hasta`, tres estados (`completo` inalcanzable por diseño) | `secuencia_v1`, `etapa_*`, `core/apertura_v1_estado.py` |
| §3 alta CRM | fuera de V1: **segundo comando** en modo `libre` (`--crm api`) | `[APER-66]`; `_alta_crm` |
| §4 correo / WhatsApp / manual | comandos sueltos en `libre`, una fuente por invocación; el intake de correo termina «OK» **sin OCR** | `_despachar_intake`; `MEJORAS #188` |
| §5 sala de máquina | dentro de V1; hay que **relanzarla** tras cada fuente nueva | `[APER-59]` |
| §6 etiqueta Gmail | **a mano** por MCP (crear, colorear, aplicar a cada hilo); `apply_label` por hilo devuelve éxito sin aplicar | `plugins/gmail_mcp/server.py:377`; `MEJORAS #237`; `[APER-69]` |
| §7 sala de lectura | **dos constructores** (skill v1.17 y CLI `organizar`); el CLI **se detiene** y pide clasificar el residuo a mano; hasta hoy anidaba por fuente y pisaba por colisión | `[APER-70]`; `core/sala_lectura.py::clasificar_caso`; `MEJORAS #226` (cerrado en PR #328) |
| §8 viabilidad | skill en sesión + `render_informe.py`, que **escribe solo las filas que recibe** | `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py` |
| §9 ficha CRM | `crm_ficha` desde un `_ficha_crm.yaml` **escrito a mano**; un solo contrario; cuantía entera; actuación **sin helper** | `scripts/crm_ficha.py`; `[APER-63]`; `MEJORAS #218`, `#209` |
| verificación | ninguna etapa comprueba el **expediente**; cada herramienta comprueba su **paso** | 93º cierre: «el OK que describía el paso y no el expediente» |

Coste de construcción de lo anterior, para calibrar: la spec de apertura integral lleva unas
veinte rondas adversariales (R1–R6, R10–R16, R18, R20, R-A/B/C, R21–R26) y su propio §21.1
anota «tres rondas, veinticuatro hallazgos y cero líneas de código de producción» en la
fase de diseño.

## 2. Qué pasó hoy, caso por caso

| Caso | V1 | Lo que rompió | Lo que exigió al operador |
|---|---|---|---|
| W-048U77 | **bloqueada dos rondas** (`FileNotFoundError` por 11 de 58 ficheros sin extensión; el montaje de Drive Desktop los renombra tras el pull) → 7 duplicados | `#214`, `#215` (contrato de arras `.docx` sin extensión en `sin_soporte`), `#217` (informe de firmas propone a la persona equivocada), `#218` (cuantía entera) | censo con `rclone lsf`, borrado por diferencia sha256, custodia aparte, `apply` a mano, lectura fila a fila del informe, `PUT` de la cuantía |
| W-030TZY | corrió; 46,5 min de máquina, 82 % OCR | `#219`–`#222`; CRM con dos fichas de la misma colaboradora → `ConflictoDeIdentidad` | **clasificar 80 documentos a mano**; dedup de fichas en el CRM en cuatro pasos; etiqueta Gmail y 6 hilos por MCP |
| W-02V48N | corrió (30 s alta+pull+alta CRM; 632 s la secuencia) | `#235` (gate ciego al W-code ajeno dentro del PDF), `#236` (`U+200E` en adjuntos WhatsApp), `#237` | barrido de documental de otro caso en **cuatro tandas, 235 ficheros**; rescate del export de WhatsApp; ASR aparte; corrección del tipo propuesto por la sesión |
| W-048UOL | corrió | tipo elegido al alta y **retipificado** el mismo día (40 ficheros); viabilidad con **51 de 88** filas sin marcar; sala aplanada a mano | decisión de retipificar; contar la columna del `.xlsx`; coordinación con dos sesiones que arreglaban lo mismo |
| W-02NHNC | corrió (5:18) | **`#225`** (pull rellena con ceros a múltiplo de 512: hash forense falso, dedup roto, OCR doble); `#224`, `#226`, `#227`, `#228` | ~15 min de reproceso; reponer 15 ficheros y regenerar la sala; cuantía a `_caso.md` a mano |
| W-02YZO4 | corrió | viabilidad con **70 de 88** sin marcar; §15.6 de `INTEGRACION` invertido (`items`/`hydra:member`) → «cero actuaciones» falso | aplanar la sala **arreglando el motor en la misma sesión** (PR #328, 2 rondas, 17 hallazgos); control positivo sobre el parser |
| W-02O7E2 | corrió; dos corridas de OCR, **7:26 de máquina sobre 2:30:00 de reloj** | **`#239`** (`ensure_contrario_vinculado` funde a dos deudores que comparten correo y lo dice como «existente»); `#190` segunda medición (los cuatro DNI y un vídeo, sin extensión, fuera del catálogo); cuatro grupos de colisión de nombre, no uno; `[APER-71]`, `[APER-72]` | crear y vincular a mano a la segunda deudora; reponer extensiones dos veces hasta declararlas en el catálogo; cuatro renumeraciones del backlog y dos del ordinal |

Reloj medido en W-02NHNC (103º): mecánica 38:41 · sala de lectura 12:16 · ficha CRM 6:48 ·
viabilidad 39:36 · **total 1:37:22, de los que 14:18 son de máquina**. Y en W-02O7E2 (105º): mecánica
12:00 · sala de lectura, viabilidad y ficha 2:18:00 · **total 2:30:00, de los que 7:26 son de máquina**.

Y el día en conjunto: **siete aperturas en hasta seis sesiones paralelas** (censo del 101º), 18 PRs
mergeados, 30 entradas nuevas de backlog (`#209`–`#239`), una misma entrada renumerada cuatro veces
(219 → 236 → 236 «devuelto» → 239) y un ordinal dos (103º → 104º → 105º), dos «101º cierre», el mismo
fichero (`core/sala_lectura.py`) arreglado por dos sesiones sin saberlo, y tres de cuatro
mensajes de coordinación con la foto rancia (101º). Una sesión hizo de «orquestador del
cierre por encargo de Nikolai» y aun así el reparto salió bien «por casualidad, no por la
premisa». Y la mesa de W-02O7E2 lo dejó escrito en su cierre: «la coordinación entre mesas
costó más que el trabajo que coordinaba».

## 3. Por qué pareció que no funcionó

1. **Lo automatizado es lo invisible.** V1 cubre el 15 % del reloj y era el tramo que ya
   corría desatendido en segundo plano. Todo lo que pide atención —etiqueta, clasificar,
   viabilidad, ficha, actuación, tipo, cuantía, dirección— quedó fuera **por decisión de alcance
   del 2026-08-24**, no por fallo: V2 y V3 nunca se construyeron. Abrir un extrajudicial sigue
   siendo, contados sobre el runbook, dos comandos de `abrir_caso` más unos diez comandos y
   skills sueltos, cada uno con su verificación a mano.
2. **Las herramientas dicen «OK» del paso, no del expediente.** Ocho veces hoy: `organizar`
   «organizada» con 2 de 4 artefactos (`#221`); `render_informe` «OK» con 51 y 70 filas sin
   marcar; `apply_label` éxito sin aplicar (`#237`); `verificar_sala` contando su propio aviso como un problema (`#216`);
   informe de firmas proponiendo un alta falsa (`#217`); pull «hecho» con hashes falsos
   (`#225`); parser de actuaciones devolviendo cero sobre 20.825; `ensure_contrario_vinculado` devolviendo
   «existente» con el id del otro deudor (`#239`). Mientras nada cierre el lazo
   sobre el expediente, el verificador es el letrado, y eso es «estar encima».
3. **Cuatro defectos de la capa base obligaron a reparar y reprocesar a mano:** el relleno con
   ceros (`#225`, afecta a prácticamente todo lo que entra por rclone), el renombrado del
   montaje (`#214`), la colisión de nombres en la sala (`#226`, ya cerrado) y los ficheros sin
   extensión que la sala de lectura descarta en silencio (`#190`, segunda medición en W-02O7E2, donde
   eran los DNI de quien firmó el encargo). Cualquier V2
   construida encima multiplica el reproceso.
4. **La atención se fue a orquestar sesiones, no expedientes.** Seis aperturas en paralelo con
   reparaciones de código intercaladas generaron la coordinación del punto anterior. La única
   apertura que declaró «sin tocar código» (W-02V48N) fue también la que menos coordinación
   costó.

## 4. Inventario de lo que hoy decide o teclea el letrado en una apertura

| Entrada humana | ¿Jurídica? | Fuente posible |
|---|---|---|
| W-code, `folder_id` | no | recon (ya) |
| ciudad | no | unidad compartida (B5 ya deriva el código; la ciudad sale del mismo nombre) |
| **dirección** | no | nombre de la carpeta de E&V (`#224` vía a) |
| tipo de caso | **sí, provisional** | propuesta de la sesión + confirmación; hoy dos de seis salieron mal a la primera |
| cuantía | **sí** | se conoce al leer el encargo, no al alta (`#227`) |
| nombre y rama de la etiqueta Gmail | no | `case_id` + tabla ciudad → `NN. CIUDAD` (`[APER-69]`) |
| hilos a etiquetar | **confirmación** | búsqueda por W-code y dirección; propuesta, no decisión |
| clasificación del residuo (tipo, parte, descripción por documento: 80 / 21 filas) | parcialmente | default `07`/`08` de `preclasificar` + lectura; nunca debería bloquear |
| 88 preguntas de viabilidad | **el veredicto sí**; el marcado de pendientes no | render completo por defecto |
| `_ficha_crm.yaml` (contrario, colaboradores, notas) | **contrario y deudor sí** | generado desde los datos ya extraídos |
| actuación (predefinida, duración, profesional) | no | id aprendido + duración del `estado.json` |
| verificación por lectura de cada paso | no | gates de resultado (§5, P2) |

De unas doce entradas, **cuatro son del letrado**: tipo (provisional), cuantía y base, quién es
el deudor, y el veredicto de viabilidad. Las otras ocho son derivables o verificables por
código.

## 5. Propuestas

**Principio (P0): las decisiones del letrado van al principio, una vez, y al final; en medio la
máquina no pregunta, declara pendientes.** Al principio, un único fichero de entrada
(`00_Input/_apertura.yaml` o los flags actuales): W-code, `folder_id`, ciudad, tipo con
`provisional: true`, cuantía si se sabe, pistas de correo, contrarios conocidos. Al final, una
**ficha de cierre** con los pendientes y las excepciones (acción 12 de la fila #21, que sigue sin
instrumento). En medio, el vocabulario que ya existe: `Pendiente`, `preparado_con_pendientes`,
`estado.json`. **La etiqueta Gmail y el alta CRM van después de la sala de lectura**, no antes:
así una retipificación es un renombrado local (barato, como demostró W-048UOL) y no el
cross-sistema que `[APER-04]` manda evitar.

### P1 — Terminar la secuencia sobre el secuenciador que ya existe (V2 + V3 mínimas)

`core/apertura_v1.py::secuenciar` recibe las etapas como invocables: añadir etapas no toca su
contrato. Etapas nuevas, en este orden tras `sala_maquina`: `email` (búsqueda por W-code y
dirección → propuesta de hilos → `create_label` + `apply_label` **por mensaje** → `export_label`
→ vuelta a `sala_maquina`, que cierra `#188`), `sala_lectura` (catálogo → clasificar con
default → aplicar → poblar → render → `verificar_sala`; **nunca se detiene**: el residuo queda
en la worklist y como pendiente `clasificacion_pendiente:N`), `viabilidad` (render con las 88
filas), `crm_alta` (con `--yes` y el `case_id` como referencia), `crm_ficha` (desde YAML
generado), `actuacion`, `verificar` (P2). Mismo mutex, mismo `estado.json`, `--hasta`,
idempotente. El diseño no hay que escribirlo: los contratos de V2/V3 están «diferidos, no
derogados» en la spec (§§5–9, tabla del §21.3); hace falta un **plan** corto, no una spec nueva.
**Radio de daño: escribe en CRM y Gmail → 2 rondas** (plan y diff), y ni una más.

### P2 — `verificar_apertura`: el «OK» del expediente, en código

Codificar las comprobaciones que hoy hace el letrado a mano y que cazaron los siete falsos «OK»:
censo remoto (`rclone lsf`) contra ficheros locales de `01_Drive EV` sin protocolo; hash contra
el `sha256Checksum` que declara Drive cuando existe (`#225` vía a); filas de `_cobertura.json`
menos hijos de bundle igual a entradas del catálogo (`[APER-60]` con la corrección del 102º);
los cuatro artefactos de la sala presentes (`#221`); 88 filas de viabilidad con respuesta o
pendiente; relectura de la ficha y las relaciones del CRM; actuación asociada por el lado del
expediente; hilos etiquetados igual a los propuestos; **cero W-codes ajenos** en los espejos MD
(`#235`, un `grep` sobre `03_MD`); cuantía de `_caso.md` igual a la del CRM. Cada comprobación
sale `ok | pendiente | fallo` al `estado.json` y al evento forense. 1 ronda. **Es la pieza que más
reduce el «estar encima»**, y no depende de P1: puede correr hoy como comando suelto.

### P3 — La capa base antes que cualquier V2: `#225`, `#214`, `#215`

`#214` y `#215` ya están promovidos (`[SIGUIENTE-TIPO-POR-BYTES]`); `#190` es de la misma familia
—extensión ausente, documento fuera del catálogo— y hoy tiene dos mediciones. **`#225` tiene disparador
consumado** (seis casos hoy y el histórico) y no está promovido. Su vía (c) —pull a *staging*
NTFS y copia verificada con `rclone check`— es el «staging disjunto» que la spec (§6.2) ya
prescribe y que `[APER-41]` hace a mano. Decisión de Nikolai pendiente, y cara: reponer el
histórico (crudo **y** derivados, del orden del doble) o declarar que el hash no acredita
procedencia en los expedientes abiertos antes.

### P4 — Sala de lectura sin parada y con un solo constructor

`core/sala_lectura.py::_categoria_por_nombre` devuelve `None` y manda al residuo todo lo que no
casa un patrón; la skill (`preclasificar.py:32`) devuelve **siempre** una categoría (`07` por
defecto, `08` para bundles conversacionales). Unificar los dos en la regla de la skill vacía el
residuo obligatorio: lo que queda es descripción y parte, que el letrado completa **cuando lee la
sala**, no antes de que exista. Decidir `[APER-70]` (la skill gobierna; el CLI es su motor o se
retira), apuntar el botón de Streamlit al camino vivo y re-importar los `.skill` caducados
(fila #14). 1 ronda.

### P5 — Viabilidad: el generador escribe las 88 filas

`render_informe.py` solo recorre `d["preguntas"]`; las filas no pasadas quedan sin la marca de
pendiente de entrevista, que es la mitad del valor de la hoja (51/88 y 70/88 hoy). Recorrer
`build_id_row_map(preg)` entero y marcar `sí` en lo no resuelto. De paso, `#228` (semáforo
`E22`). Cambio pequeño, 1 ronda.

### P6 — Ficha CRM y actuación sin YAML a mano

Generar el esqueleto de `_ficha_crm.yaml` desde `_apertura.yaml`, el informe de firmas y el JSON
de viabilidad (contrario, importes, fechas); `crm_ficha` con N contrarios (`[APER-63]`) y sin
fundir por email a dos deudores con NIF distinto (`#239`, `[APER-71]`); cuantía decimal (`#218`); `core/sudespacho_actuaciones.py` (`#209`) con el asunto canónico elegido por
**quién firma** —el prefijo es la tarifa, `[APER-72]`—, el `id_predefinido` solo cuando una instancia
real lo declare (`pre=65` en `APERTURA E ESTUDIO INICIAL CASO`; vacío en las 20 de `REVISION
VIABILIDAD`) y la duración leída del `estado.json` (`iniciada`/`terminada` ya existen; falta `duracion_s` en el evento) — que es a la
vez el instrumento de la acción 12. Corregir el §15.6 de `INTEGRACION_SUDESPACHO.md`
(`items`/`hydra:member` está al revés, 104º). 1 ronda.

### P7 — Identidad sin teclado

`#224` vía (a): dirección desde el nombre de la carpeta de E&V con el W-code como delimitador,
rindiéndose al flag cuando no lo encuentre. `#227` vía (a): `case_manager.update_meta` que fije
frontmatter y cuerpo conservando lo ajeno (cierra `#184` y `#192` de paso). Tipo `provisional`
en `_caso.md`, sin propagar a CRM ni Gmail hasta confirmarlo (P0). 1 ronda.

### P8 — Proceso: una sesión, N aperturas; apertura y reparación no se mezclan

Es la propuesta que más atención devuelve y no toca código. (a) Una sesión de apertura ejecuta
el runbook y **no toca el repo**: anota defectos en un fichero de trabajo y los ficha **al
final**, leyendo `origin/main` al escribir. (b) Como mucho una sesión de reparación en paralelo,
dueña del código. (c) Las aperturas del día en **serie en una sola sesión** o en lote (una cola de
casos que el CLI recorre): el mutex es por caso, la atención del letrado no. (d) En la bitácora,
un bloque «aperturas del día» en vez de un cierre numerado por caso — el 101º ya concluyó que
un cierre se cita por fecha, no por ordinal. Decisión de Nikolai.

## 6. Orden recomendado y lo que decide Nikolai

**Orden:** P5 y P7 (una tarde, quitan cuatro pasos manuales) → P2 (el lazo cerrado) → P3
(`#225` con su decisión) → P4 → P6 → P1 (que absorbe todo lo anterior como etapas). P8 desde la
próxima apertura.

**Tres decisiones que solo son suyas:**

1. **`#225`, histórico:** reponer crudo y derivados de los expedientes afectados, solo los con
   litigio vivo, o declarar la limitación del hash.
2. **`[APER-70]`:** qué constructor de la sala de lectura sobrevive (la propuesta es la skill).
3. **P8:** si acepta separar sesiones de apertura y de reparación y abrir en serie.

**Presupuesto de rondas, por su regla del 2026-08-26:** P1 dos (escribe en CRM y Gmail); el
resto una, sobre el diff. Y una advertencia medida: la spec de apertura integral consumió tres
rondas y veinticuatro hallazgos antes de la primera línea de código (§21.1). P1 se planifica
sobre la spec existente, no se rediseña.

## 7. Lo que este documento no hace

No reserva números de backlog ni promueve filas: cada `MEJORAS #NNN` citado ya existe en
`main`. No hay ronda adversarial: es prosa y su radio de daño sobre el repo es nulo. Y no ha
leído los transcripts de las sesiones, que no están en el repo: si en ellos hay una fricción que
la bitácora no recogió, no está aquí.

## 8. Qué se promovió de este handoff (añadido al consumirlo, 2026-09-11)

Nikolai promovió **tres** de las ocho propuestas al arrancar la sesión del 2026-09-11. Van a la
**fila #28** de `PLAN.md`, bloque `[SIGUIENTE-APERTURA-MENOS-DECISIONES]`, que es desde ahora su
hogar autoritativo de estado:

| Propuesta | Promovida | Backlog marcado `[PROMOVIDO → PLAN.md]` |
|---|---|---|
| P5 — las 88 filas de viabilidad | **sí** | `MEJORAS #228` |
| P7 — identidad sin teclado | **sí** | `MEJORAS #224`, `#227` |
| P2 — `verificar_apertura` | **sí** | ninguno: `#221` y `#235` **no** se marcan, porque P2 las **detecta** desde fuera y no las cierra |
| P1 — secuencia V2+V3 | no | necesita plan propio y dos rondas |
| P3 — capa base (`#225`, `#214`, `#215`) | no | espera la decisión de Nikolai sobre el histórico |
| P4 — sala sin parada, un constructor | no | espera decidir `[APER-70]` |
| P6 — ficha CRM y actuación sin YAML | no | depende de P2 y de la capa base |
| P8 — proceso | no | decisión de Nikolai, no es código |

Lo no promovido **no caduca con este fichero**: cada `MEJORAS #NNN` que cita sigue vivo en
`docs/MEJORAS_FUTURAS.md` con su medición, y las tres decisiones del §6 siguen abiertas.
