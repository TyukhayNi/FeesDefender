---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: MEJORAS #296 (el token y la carpeta de Drive dicen por qué no están) y #301 (las carpetas de E&V con el W-code delante derivan su dirección) — filas #42 y #47 de PLAN.md
---

# El alta dice por qué no lee Drive, y entiende las carpetas con el W-code delante (`MEJORAS #296` y `#301`)

> **Estado (2026-09-26):** construido con TDD; la R1 de Codex sobre el diff (§6) está pendiente.
> Filas **#42** y **#47** de `PLAN.md`.

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

## 2. Diseño

**#296.** Un solo lector del bloque `token`, `_leer_bloque_token`, para las dos lecturas (antes y
después de renovar), con **30 s** (`_TIMEOUT_RCLONE_TOKEN`, también para `rclone about`) y un
motivo por salida: tardó, rclone ausente, remote inexistente (por su comentario), sin bloque,
renovación fallida. El motivo **nunca** lleva nada de la salida de rclone, que escribe el token y
el `client_secret` en claro. `obtener_token_drive() -> TokenDrive(token, motivo)` es la API; la de
siempre, `_get_drive_access_token`, queda como su envoltorio. `leer_carpeta_drive(folder_id) ->
(info, motivo)` dice además la red, el HTTP (401, 403 y 404 con su pista) o la cuota;
`get_drive_folder_info` queda como envoltorio. El alta imprime el motivo en los dos sitios que
decían «token/red»; el auditor de nombres de carpeta también, sin mandar a mirar `rclone config
show`. Y el precheck de la skill: 5 si rclone tarda, 4 si no está o el remote no existe; todo lo
distinto de 0 sigue llevando a la copia secuencial (skill 1.19).

**#301.** El W-code delante, con guion o espacio detrás: la dirección es lo que queda hasta el
**último** « - » —el consultor, la misma convención del otro orden—, y solo separa el guion con
espacios, para no partir el «1-2» de un piso. El W-code en medio sin guion **no** se interpreta:
en esas formas el prefijo no es una dirección, y derivar adivinando es peor que teclear. La
ciudad de SaRS1 la quita el alta —no el parser, que no sabe de qué ciudad es el caso— y **solo si
es la de `--ciudad`**, sin mayúsculas ni tildes: «AVDA.» también es una palabra en mayúsculas con
punto.

## 3. Tests

**25 nuevos**, vistos en rojo antes de su código salvo dos controles: 7 del token (tardó, timeout
holgado en las dos órdenes, remote inexistente, sin rclone, renovación que tarda, token vigente
sin motivo, el motivo sin la salida de rclone), 3 de la carpeta, 8 del parser (6 formas con el
W-code delante, el W-code solo y el control sin guion), 3 del alta (el motivo en el error de
`--team-id`, la ciudad del caso fuera, y el control de «AVDA.»), 2 del auditor (fichero nuevo) y 2
del precheck. **Y uno endurecido**: el de la autoderivación sin carpeta exige ahora el motivo en
el aviso; sin eso, el mutante que lo quitaba sobrevivía (medido sobre `faeeb4b`).

**Los stubs del alta cambian de costura, declarado:** nueve sitios de `test_abrir_caso_cli.py`
simulaban `get_drive_folder_info`; el alta usa ahora `leer_carpeta_drive`, así que pasan a esa, y
los que eran `boom` lo son de las dos, para que no queden vacíos.

**Mutantes:** `tests/_mutantes_intake_drive_296_301.py`, en el repo, con el contrato estricto (base
verde, ancla única, muerte solo por el aserto): **18 de 18 muertos por su aserto**, en su primera
corrida.

**Suite de los ficheros que tocan estos módulos:** 1.310 recogidos, 0 fallos (36 ficheros).

## 4. Medido con los datos reales

- **El censo, repetido con el parser nuevo:** de las 231 carpetas con el W-code delante, 226
  derivan su dirección; de las cinco que no, tres son el W-code solo. Las 1.847 de siempre, igual.
- **El precheck contra rclone real** con un remote que no existe: 4, «rclone no instalado o el
  remote no existe».
- **El timeout** no se puede reproducir en reposo (0,1 s): el remedio es el margen y el motivo; la
  prueba de que se dice es el test que simula el `TimeoutExpired`.

## 5. Lo que no cubre, dicho

- **`scripts/diag_drive_autofill.py`** lee el token con su propia copia de `config show` (5 s),
  da por existente un remote que no existe e **imprime 30 caracteres del access_token**. Es
  anterior y queda fuera: tarea aparte, sugerida en la sesión.
- **C1 de `verificar_apertura`** sigue diciendo «token, red o permisos» sin la causa concreta:
  enumera las posibles y no elige una falsa, así que no es este defecto.
- **Las 331 carpetas con el W-code en medio sin guion** siguen pidiendo el flag, a propósito.
- **Un rclone colgado de verdad** cuesta ahora 30 s en cada lectura del token, en vez de 5.

## 6. Ronda y modelo

**Una ronda sobre el diff.** Toca `core/`, `scripts/` y una skill, sin decidir quién escribe ni
poder destruir datos de cliente: lee el token y la carpeta, y deriva una dirección que el alta
enseña antes de usarla. **Fila ordinaria: `gpt-6-sol` · `high` · `default`**, quinta y última del
ledger de calibración de la #38.
