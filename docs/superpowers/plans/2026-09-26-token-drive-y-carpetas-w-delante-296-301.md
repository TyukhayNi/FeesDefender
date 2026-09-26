---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: MEJORAS #296 (el token y la carpeta de Drive dicen por qué no están) y #301 (las carpetas de E&V con el W-code delante derivan su dirección) — filas #42 y #47 de PLAN.md
---

# El alta dice por qué no lee Drive, y entiende las carpetas con el W-code delante (`MEJORAS #296` y `#301`)

> **Estado (2026-09-26):** construido con TDD; la R1 de Codex sobre el diff volvió `NO-SHIP` con
> siete hallazgos, los siete confirmados, y se remedió en este mismo PR **sin segunda ronda** (§7).
> Los §2 a §5 describen el diseño que queda tras la R1. Filas **#42** y **#47** de `PLAN.md`.

**Encargo.** Nikolai pidió seguir con el backlog de las últimas aperturas en la misma sesión que
el #407 y el #408, y eligió estas dos: las dos tocan `core/intake_drive.py` y salieron de las
aperturas de W-02UIQU y W-02Y2J6 (2026-09-25).

## 1. Lo medido

**#296 — un timeout que se traga como otra causa.** En las dos aperturas el alta abortó con
«--team-id no se pudo derivar de --folder-id (sin --folder-id o token/red)» con el token
vigente: `rclone config show gdrive_ev` tardó 3,9-6,7 s con otra corrida de rclone en marcha, y
`_get_drive_access_token` lo lanzaba con `timeout=5` y convertía el `TimeoutExpired` en `None`,
igual que un rclone ausente o un token sin bloque. Medido hoy en reposo: 0,11-0,14 s, cinco de
cinco. Y un dato que el backlog no tenía: **`rclone config show <remote inexistente>` sale con
código 0** y solo lo dice en un comentario (`# couldn't find type of fs for "…"`). El precheck de la
skill, que miraba el código de salida, clasificaba un remote inexistente como 3 —«client
compartido»— y juntaba el timeout con «no instalado» en el 4.

**#301 — el W-code delante.** `parse_ev_folder_name` solo conocía «<dirección> - W-XXXX -
<consultor>». Los `_caso.md` no guardan el nombre de la carpeta de E&V (0 de 40), así que el censo
se hizo con la Drive API, en solo lectura y contando formas, sin imprimir nombres: 53 unidades,
hasta 50 carpetas cada una (la primera página por nombre, no el universo).

| Forma | Carpetas |
|---|---|
| W-code en medio con guion (ya parseaban) | 1.847 |
| **W-code delante** (no parseaba ninguna) | **231** — 185 con guion detrás, 46 con espacio |
| W-code en medio sin guion delante | 331 — paréntesis, `_`, fechas y números alrededor |

El W-code delante no es cosa de Santander: aparece en muchas plazas. Y la ciudad delante
(«SANTANDER. <dirección>») solo en SaRS1, 24 de 24; la carpeta del expediente de W-02UIQU, que se
tecleó, no la lleva.

## 2. Diseño (rev. tras la R1, §7)

**#296.** Un solo lector del bloque `token`, `_leer_bloque_token`, para las dos lecturas (antes y
después de renovar), con **30 s** (`_TIMEOUT_RCLONE_TOKEN`, también para `rclone about`) y un
motivo por salida: tardó, rclone ausente, remote inexistente (su comentario inglés), config sin
línea `type` —lo que un remote de verdad siempre trae, y cubre otra versión de rclone que escriba
otro comentario—, sin bloque token, renovación fallida con el token «caducado o a punto de
caducar». El motivo **nunca** lleva nada de la salida de rclone. `obtener_token_drive() ->
TokenDrive(token, motivo)` es la API; `_get_drive_access_token` queda como envoltorio.
`leer_carpeta_drive(folder_id) -> (info, motivo)` dice además la red, el HTTP con su `reason` —solo
el identificador, nunca el cuerpo—, «sin permiso» **solo** si ese `reason` es de permisos, y la
razón que vio al agotar los reintentos por cuota; `get_drive_folder_info` queda como envoltorio. El
alta imprime el motivo en los dos sitios que decían «token/red»; el auditor de nombres de carpeta
también, sin mandar a mirar `rclone config show`; y el diagnóstico `scripts/diag_drive_autofill.py`
usa el lector único y ya no imprime nada del token. El precheck de la skill: 5 si rclone tarda, 4
si no está o la config no trae `type` (skill 1.19).

**#301.** El W-code delante, con guion o espacio detrás, **solo cuando el nombre cumple la
convención que lo hace inequívoco**: la dirección lleva número y el consultor —el último « - », si
hay más de un tramo— no; 219 de las 229 carpetas medidas la cumplen. Lo demás se rinde y lo dice
—el W-code está, lo que no se sabe es qué tramo es la dirección—. Solo separa el guion con espacios.
El W-code en medio sin guion **no** se interpreta. La ciudad de SaRS1 la quita el alta, **solo con
el W-code delante** —el formato de siempre conserva su prefijo como antes— y **solo si es la de
`--ciudad`**, sin mayúsculas ni tildes.

## 3. Tests

**Antes de la R1, 25 nuevos y uno endurecido**, vistos en rojo antes de su código salvo dos
controles: 7 del token, 3 de la carpeta, 8 del parser, 3 del alta, 2 del auditor (fichero nuevo) y
2 del precheck; y el de la autoderivación sin carpeta, que exige el motivo en el aviso (sin eso, su
mutante sobrevivía: medido sobre `faeeb4b`).

**Tras la R1, 14 más**, vistos en rojo antes del remedio: 3 formas ambiguas con el W-code delante
y una con la dirección partida, el token a punto de caducar, la config sin `type` (en el lector y
en el precheck), el 403 que no es de permisos, el que sí, la cuota agotada con su razón, la carpeta
ambigua en el alta, la ciudad del formato de siempre, y 2 del diagnóstico (fichero nuevo). **Y tres
cambios declarados**: el test del timeout tiene techo (20-60 s); el del remote inexistente exige el
motivo específico, no el de la config sin `type`; y los dos dobles de `rclone config show` llevan
`type = drive`, como la salida real.

**Los stubs del alta cambian de costura, declarado:** nueve sitios de `test_abrir_caso_cli.py`
simulaban `get_drive_folder_info`; el alta usa ahora `leer_carpeta_drive`, y los `boom` lo son de
las dos.

**Mutantes:** `tests/_mutantes_intake_drive_296_301.py`, en el repo, con el contrato estricto:
**30 de 30 muertos por su aserto** sobre el código final. El remedio dejó sin ancla a cuatro de los
18 primeros —sus líneas cambiaron—; lo cazó la comprobación de anclas del propio arnés y se
reapuntaron. Y el del comentario inglés del precheck quedó equivalente —la línea `type` lo
subsume—, así que la comprobación redundante salió del precheck y su mutante apunta a la nueva.

## 4. Medido con los datos reales

- **El censo, repetido con el parser final:** de las 231 carpetas con el W-code delante, **219**
  derivan su dirección; las 12 que no son las 10 ambiguas, 3 de ellas el W-code solo, y 2 con otro
  separador. Las 1.847 del formato de siempre, igual.
- **El precheck contra rclone real** con un remote que no existe: 4.
- **El timeout** no se reproduce en reposo (0,1 s): el remedio es el margen y el motivo; lo prueba
  el test que simula el `TimeoutExpired`.

## 5. Lo que no cubre, dicho

- **El truncado residual de H-01:** «W-… - Calle Mayor 5 - Bajo» cumple la convención —el último
  tramo no lleva número—, así que «Bajo» se toma por consultor y la dirección queda en «Calle Mayor
  5». Es incompleta, no falsa, y el alta la enseña en su línea `[auto]` antes de usarla.
- **Un rclone colgado de verdad** cuesta hasta 90 s: tres órdenes seguidas —leer, renovar,
  releer— a 30 s cada una, frente a los 20 de antes. El test fija el techo por orden (60 s).
- **C1 de `verificar_apertura`** sigue diciendo «token, red o permisos»: enumera las causas
  posibles y no elige una falsa.
- **Las 331 carpetas con el W-code en medio sin guion** siguen pidiendo el flag, a propósito.

## 6. Ronda y modelo

**Una ronda sobre el diff.** Toca `core/`, `scripts/` y una skill, sin decidir quién escribe ni
poder destruir datos de cliente: lee el token y la carpeta, y deriva una dirección que el alta
enseña antes de usarla. **Fila ordinaria: `gpt-6-sol` · `high` · `default`**, quinta y última del
ledger de calibración de la #38.

## 7. Adjudicación de la revisión adversarial del diff (Codex, 2026-09-26) — NO-SHIP, remediado

- **Objeto revisado:** el diff `aa46fcc..e55468c` (`core/intake_drive.py`, `scripts/abrir_caso.py`, `scripts/audit_ev_folder_names.py`, el precheck de la skill `organizar-sala-lectura` con su `SKILL.md`, los tests y el arnés de mutación), contra este plan
- **Ronda:** R1 de la pieza y la única de su presupuesto (toca `core/`, `scripts/` y una skill, sin decidir quién escribe ni poder destruir datos de cliente)
- **Revisor:** Codex CLI `0.155.0-alpha.16.4`, `gpt-6-sol` · `high` · `default` (modelo y esfuerzo releídos del rollout; la velocidad, afirmada desde el lanzador conservado)
- **Informe recibido:** `docs/superpowers/plans/2026-09-26-token-drive-y-carpetas-w-delante-296-301-r1-adversarial-review.md`
- **Hallazgos:** 7 — 1 `alta`, 3 `media`, 3 `baja`; 7 confirmados contra la fuente, 0 refutados (el coste de H-01 se adjudica `acotado` y no `estructural`: ver abajo)
- **Remediado en:** este mismo PR (#409), sobre `e55468c`: `core/intake_drive.py`, `scripts/abrir_caso.py`, `scripts/diag_drive_autofill.py`, el precheck de la skill y su `SKILL.md`, 14 tests nuevos y 30 mutantes. **Ninguna ronda revisa el remedio**: el presupuesto de la pieza era una, y una segunda exige la autorización de Nikolai

**Los siete se reprodujeron contra el código, no contra el informe** (acta §2), y la pregunta de
siempre —**¿de qué frontera es esto un ejemplo?**— los agrupa en tres:

- **H-01 (`alta`), la derivación que adivina.** Con el W-code delante, el último « - » separa el
  consultor solo por convención, y «W-… - Calle Mayor 5 - Portal 2» perdía un tramo y «W-… - Ana P»
  hacía de un consultor una dirección —hacia el `case_id`, que se propaga al CRM y a Gmail—. Es la
  frontera que `_direccion_de_la_carpeta` ya tenía escrita: *una derivación que adivina es peor que
  teclear*. **El revisor proponía no derivar sin un dato independiente (`estructural`); lo adjudico
  `acotado`**, porque el censo da ese dato para la mayoría: de 229 carpetas, **219** cumplen la
  convención que lo hace inequívoco —la dirección lleva número y el consultor no—, y las **10** que
  no la cumplen son justo las formas de sus contraejemplos. **Remedio:** se deriva solo en esa
  convención; lo demás pide el flag, diciendo que el W-code está y que lo que no se sabe es qué
  tramo es la dirección. El residuo —un tramo final sin número que es parte de la dirección— queda
  declarado en el §5.
- **H-02, H-04 y H-05 (`media`, `baja`, `baja`), la frontera de #296 entera: no elegir una causa al
  pintar.** Todo 403 que no fuera de cuota se llamaba «sin permiso», y la cuota agotada decía
  `rateLimitExceeded` fuera cual fuera la razón; la renovación decía «caducado» también dentro del
  margen de 5 min, donde el token aún vale; y el remote inexistente se reconocía solo por un
  comentario inglés de una versión de rclone. **Remedio:** la razón de la Drive API —su
  identificador, nunca el cuerpo— en el mensaje, y «sin permiso» solo si lo es; «caducado o a punto
  de caducar»; y la línea `type`, que todo remote de verdad trae. En el precheck esa línea subsume
  al comentario, y la comprobación redundante salió; en el lector se conserva, porque da el motivo
  definitivo.
- **H-03 (`media`), una transformación fuera de donde se midió.** La ciudad se quitaba también en
  el formato de siempre, que no tenía ese cambio medido. **Remedio:** solo con el W-code delante.
- **H-06 (`media`), el diagnóstico que imprimía el token.** Anterior al diff y declarado en el §5,
  pero el revisor tenía razón en que pertenece a esta limpieza: es el tercer lector del token, con
  el mismo timeout de 5 s y el mismo remote inexistente dado por bueno, y además escribía 30
  caracteres del access_token. **Remedio:** usa `obtener_token_drive` y no imprime nada del token.
  La tarea aparte que se había sugerido en la sesión se retiró.
- **H-07 (`baja`).** El test del timeout no tenía techo. **Remedio:** 20-60 s por orden, y el peor
  caso —90 s si rclone se cuelga en las tres órdenes— declarado en el §5.

**Dos cosas mías durante el remedio, dichas:** un `import re` que faltaba en `abrir_caso.py` y un
`_razon_de_error` que rompía con `{"error": "texto"}` —el cuerpo que un 500 real puede traer—; los
dos los cazó la suite antes del commit. Y el arnés: el remedio dejó sin ancla a cuatro mutantes,
que la comprobación de anclas cazó y se reapuntaron.

**Lo que intentó refutar y no pudo, y se conserva:** las rutas defensivas de `expiry` y la
renovación; que ningún motivo lleve la salida de rclone; los reintentos por cuota de
`leer_carpeta_drive`; que los tests del alta no llamen a la red —corrió el fichero con los sockets
bloqueados, en verde—; y que el guion pegado al W-code se rechace, que es lo conservador.

**Para la calibración de la #38** (fila 5, la última del ledger): siete hallazgos confirmados —uno
`alta`— y **ninguna omisión conocida** a esta fecha.

**Lo que NO cambia:** el alta sigue enseñando la dirección derivada antes de usarla; `--direccion`
explícito sigue ganando; y la corrida real de un alta con rclone ocupado sigue SIN VERIFICAR hasta
la próxima apertura que lo cruce.
