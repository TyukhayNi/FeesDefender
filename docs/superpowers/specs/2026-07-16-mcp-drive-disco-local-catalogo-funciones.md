# Catálogo de funciones — MCP sobre Drive montado localmente

> Hoja de trabajo del diseño **"Drive como disco"** (memoria: `project-mcp-drive-disco-local`).
> Objetivo: que Cowork Desktop opere **ambas Drives** (`G:` = Tyukhay, `H:` = E&V)
> enteras a velocidad de disco, sin el conector nativo por API.
> Fecha: 2026-07-16. **Estado: fase de investigación cerrada — verificado en vivo contra el montaje real.**

## Cómo trabajamos esta hoja

Recorremos la tabla **función por función**. Para cada una decidimos en la columna
**Decisión**: `INCLUIR`, `DESCARTAR`, o `PENDIENTE`. La columna **Estado actual** dice
de dónde partimos. Cuando cerremos todo, esto alimenta el spec formal.

## Leyenda de estado actual

- **✅ tenemos** — ya cableado hoy (entre `expedientes` estándar y `expedientes-xl`).
- **🟢 añadido** — candidato ya acordado para incluir (2026-07-16).
- **⚪ posible** — técnicamente factible sobre el FS, pero aún no en alcance.
- **🌐 solo API** — imposible por montaje; solo vía `google-despacho` (capa nube).
- **⚠️ evitar / no aplica** — no tiene sentido o es frágil/peligroso en Drive.

## Decisiones marco ya tomadas

- Alcance del sandbox (**revisado 2026-07-16 tras revisión adversarial**):
  - **LECTURA/listar/buscar**: TODO `G:\` y `H:\`, **incluidos** los backups
    (`G:\Otros ordenadores` y unidades/carpetas tipo BACKUP).
  - **ESCRITURA/mover/renombrar/copiar-a-destino/zip**: **solo fuera** de los backups
    (backups quedan en **solo-lectura** para la IA).
  - Implementación: raíces de lectura = `G:\` + `H:\`; **denylist de escritura** =
    `G:\Otros ordenadores` + carpetas BACKUP. La guarda vive en el guardarraíl de ESCRITURA.
- **Sin borrado** (ningún `delete`).
- Enfoque de construcción (revisado tras la investigación): **A + guarda de hidratación
  + bloqueo `.g*`**. El "A puro" (solo ensanchar raíces) **no basta**: con ~26% de
  ficheros en estado frío, leer/zipear/hashear a ciegas congela el hilo del MCP.

---

## Tabla de trabajo

| # | Función | Qué hace | Estado actual | Decisión | Notas (✔ = verificado 2026-07-16) |
|---|---------|----------|:---:|:---:|-------|
| **Leer** ||||||
| 1 | Leer texto completo | Devuelve el texto de un fichero (txt/md/eml/csv/json…) | ✅ | INCLUIR | Ya en uso |
| 2 | Leer varios ficheros a la vez | Lee un lote en una llamada | ✅ | INCLUIR | |
| 3 | Leer parcial (head/tail líneas) | Primeras/últimas N líneas | ✅ | INCLUIR | ✔ En frío puede hidratar el fichero entero |
| 4 | Leer rango de bytes | Extrae solo un tramo de un fichero grande | ⚪ | **DESCARTAR** | ✔ La hidratación en frío anula el ahorro |
| 5 | Leer binario al modelo (base64) | Vuelca los bytes de un binario al modelo | ✅ | **DESCARTAR** | Anti-patrón (caro; COLD dispara descarga). Retirar del alcance expuesto; solo interno si algún flujo lo exige |
| 6 | Metadatos de PDF / EXIF de foto | Nº de páginas, dimensiones, fecha de captura | ⚪ | **DIFERIR** | Útil para triaje sin abrir, pero sin disparador concreto |
| 7 | Leer Google Doc/Sheet/Slides nativo | Contenido de un `.gdoc`/`.gsheet` | 🌐 | **BLOQUEAR + API** | ✔ Leerlo da `ERROR_INVALID_FUNCTION` (kernel). Interceptar `.g*` y desviar a `google-despacho`. El ID sale de la BD, pero usamos API |
| **Navegar / inspeccionar** ||||||
| 8 | Listar carpeta | Hijos directos | ✅ | INCLUIR | |
| 9 | Listar con tamaños | Hijos + tamaño de cada uno | ✅ | INCLUIR | |
| 10 | Árbol recursivo | Estructura completa bajo una carpeta | ✅ | INCLUIR | Cuidado sobre raíces enormes |
| 11 | Metadatos de fichero | Tamaño, fechas, tipo | ✅ | INCLUIR | ✔ Atributos Windows mienten (todo `Normal`) |
| 12 | `du` / conteo de carpeta | Peso total y nº de ficheros | 🟢 | INCLUIR | Evita copiar a ciegas; combinar con estado HOT/COLD |
| 13 | Espacio libre del volumen | Bytes libres de la unidad | 🟢 | INCLUIR | ✔ Medir el volumen físico de la caché (`content_cache`), NO el virtual de `G:`/`H:` |
| 14 | Resolver atajo `.lnk`/shortcut de Drive | Destino real de un acceso directo | 🌐/⚠️ | **INCLUIR** | ✔ Aquí son `.lnk` estándar → `H:\.shortcut-targets-by-id\<id>\`. Fallback robusto: tabla `shortcut_details` de la BD. Validar acceso al destino |
| **Buscar** ||||||
| 15 | Buscar por nombre / patrón | Encuentra ficheros por su nombre | ✅ | INCLUIR | ✔ Nombre local ≠ nombre nube (case / `(1)`) |
| 16 | Buscar por contenido (grep) | Busca texto DENTRO de ficheros | 🟢 | INCLUIR | El mayor salto para trabajo legal; aplica guarda de hidratación |
| 17 | Buscar por metadatos de Drive | Dueño, "compartido conmigo", destacados, etiquetas | 🌐 | (solo API) | Metadatos de nube |
| **Escribir / crear** ||||||
| 18 | Crear carpeta (anidada) | Crea estructura de carpetas | ✅ | INCLUIR | |
| 19 | Escribir texto nuevo | Crea un fichero de texto | ✅ | INCLUIR | |
| 20 | Editar texto (find/replace) | Modifica texto existente | ✅ | INCLUIR | |
| 21 | Anexar texto | Añade al final (logs `.jsonl`) | ✅ | INCLUIR | |
| 22 | Escribir binario de verdad | Escribe bytes decodificados (no stub) | ✅ | INCLUIR | `write_file_base64` |
| 23 | Fijar timestamps (mtime/ctime) | Cambia fechas de un fichero | ⚠️ | **DESCARTAR** | Drive gestiona fechas; la sync las sobrescribe |
| **Mover / copiar / organizar** ||||||
| 24 | Copiar fichero | Copia no destructiva | ✅ | INCLUIR | Copiar un COLD dispara descarga (esperado) |
| 25 | Copiar árbol | Copia recursiva de una carpeta | ✅ | INCLUIR | Aplica guarda de hidratación en árboles fríos grandes |
| 26 | Mover | Cambia un fichero de carpeta | ✅ | INCLUIR | Destructivo si el destino existe |
| 27 | Renombrar | Cambia el nombre (= mover) | ✅ | INCLUIR | |
| 28 | Renombrado en lote por patrón | Aplica nomenclatura a un intake de golpe | 🟢 | INCLUIR | Nomenclatura del despacho |
| 29 | Borrar | Elimina fichero/carpeta | ⚪ | DESCARTAR | Decidido: sin borrado |
| **Comprimir** ||||||
| 30 | Extraer zip/tar | Descomprime en destino | ✅ | INCLUIR | |
| 31 | Crear zip | Empaqueta ficheros/carpeta | 🟢 | INCLUIR | ✔ **Guarda**: abortar/avisar si el árbol tiene COLD grandes (hidratación masiva) |
| **Integridad** ||||||
| 32 | SHA-256 de fichero | Hash de un fichero | ✅ | INCLUIR | ✔ Mantener SHA-256 local; **solo sobre HOT** (guarda). Rechazado MD5-de-API como custodia |
| 33 | SHA-256 de árbol | Hash de todos los ficheros de una carpeta | ✅ | INCLUIR | ✔ Idem; guarda anti-hidratación-masiva |
| 34 | Verificar árbol contra manifiesto | Confirma copia fiel bit a bit | ⚪ | **INCLUIR** | Encaja con custodia SHA-256 y el `MANIFEST_CHECKOUT.json` de checkout/checkin; aplica guarda de hidratación |
| 35 | Diff de dos ficheros / árboles | Compara versiones | ⚪ | **DIFERIR** | Nicho; sin caso concreto |
| **Estado Stream (NUEVO)** ||||||
| 45 | **Estado de hidratación (HOT/COLD)** | Dice si los bytes están en local sin disparar descarga | 🟢 | **INCLUIR** | ✔ Vía BD `metadata_sqlite_db` (`item_properties.key='content-entry'`). **Oráculo opcional y frágil** (ver §Realidad Stream). Base de todas las guardas |
| **Capa Drive (nube)** ||||||
| 36 | Compartir / permisos | Quién puede ver/editar | 🌐 | (solo API) | `google-despacho.create_permission` |
| 37 | Historial de versiones | Revisiones de un fichero | 🌐 | (solo API) | |
| 38 | Comentarios / sugerencias | Anotaciones en Docs | 🌐 | (solo API) | |
| 39 | Listar papelera / restaurar | Recuperar borrados | 🌐 | (solo API) | Borrar sí manda a papelera |
| 40 | Pin offline / liberar espacio | Control de sync de GDFD | 🌐/⚠️ | (solo API) | No es op de FS estándar |
| **No aplica / peligroso** ||||||
| 41 | `chmod` / `chown` / ACL POSIX | Permisos de fichero Unix | ⚠️ | DESCARTAR | Sin sentido en FS de Drive |
| 42 | Symlinks / hardlinks | Enlaces de fichero | ⚠️ | DESCARTAR | GDFD no los soporta fiable |
| 43 | Watch / notificación de cambios | Avisa al cambiar algo | ⚪/⚠️ | **DESCARTAR** | ✔ `ReadDirectoryChangesW` existe pero es inconsistente para cambios de nube; sin caso claro |
| 44 | Ejecutar / lanzar un fichero | Corre un binario | ⚠️ | DESCARTAR | Superficie de seguridad; fuera por diseño |

---

## Realidad Stream + oráculo de hidratación (BD GDFD)

Un montaje GDFD **no es un disco normal**: parte de los ficheros son "fríos"
(solo-nube) y leerlos dispara una descarga bloqueante. Esto obliga a una capa
consciente de hidratación. Todo lo de abajo está **verificado en vivo** (2026-07-16).

### Cómo detectar hidratación sin disparar descargas

- Las **APIs de Windows mienten**: atributos = `Normal` (sin flag `OFFLINE 0x1000`);
  `GetCompressedFileSizeW` devuelve el tamaño lógico. No sirven para discriminar.
- El **único método local fiable** es la BD interna de GDFD:
  `%LOCALAPPDATA%\Google\DriveFS\<idCuenta>\metadata_sqlite_db` (SQLite legible).
  - Tabla `items`: `stable_id, id (=fileId de Drive), proto(blob), trashed, starred,
    mime_type, is_folder, file_size, local_title, team_drive_stable_id, ...`
  - Tabla `stable_ids`: `stable_id ↔ cloud_id`.
  - Tabla `shortcut_details`: `shortcut → target` (resolución de atajos offline).
  - Tabla `item_properties`: la clave **`content-entry`** presente = **bytes en caché
    local (HOT)**; ausente en un fichero real = **frío (COLD)**.
- **Discriminador confirmado**: 138.167 ficheros reales → **102.001 HOT / 36.166 COLD**.
- Clave `offlineStatus` que sugería la IA externa **NO existe** (inventada). El estado
  "fijado offline a propósito" va por `local-cache-reason` (solo 1.178 ficheros).

### Reglas de uso de la BD (candado de diseño)

- **Oráculo OPCIONAL y frágil**: BD privada, indocumentada, cambia de esquema entre
  versiones y es un **índice gigante de PII** (`local_title` = nombres de cliente). La
  *corrección* nunca depende de ella; solo la *optimización/guarda*. Si el esquema
  cambia o no está → degradar a "estado desconocido → proceder con timeout amplio".
- **Trío WAL**: leerla con consistencia exige copiar `metadata_sqlite_db` + `-wal` +
  `-shm` juntos (abrir con `immutable=1` lee una foto que ignora el `-wal` → estado
  obsoleto). Para el guard hay que respetar el WAL.
- **No** duplicar en la BD lo que da la API soportada (IDs, permisos, papelera): para
  eso, `google-despacho`.

### Guardas que se derivan (mínimo viable)

1. **Guarda de hidratación** antes de leer/copiar/zipear/hashear: si HOT → adelante; si
   COLD y grande → avisar/abortar con error controlado (`ERROR_FILE_NOT_HYDRATED`).
2. **Bloqueo de extensión propietaria** `.gdoc/.gsheet/.gslides`: prohibida la lectura
   local (da error de kernel); desviar a exportación por API.
3. **Timeouts amplios** en cualquier lectura (abrir un COLD puede tardar minutos).

### Otras trampas verificadas / anotadas

- `G:`/`H:` **no** son volúmenes estándar (`Get-Volume` no los ve) → driver propietario
  (no la Cloud Files API de Windows). Aparecen `mirror_metadata_sqlite.db` y ficheros
  `mirror_*`: el modo puede no ser Stream puro (irrelevante: la guarda es agnóstica de
  modo — en Mirror todo es HOT y nunca salta).
- Nombre local ≠ nombre nube (case-sensitivity, sufijos `(1)`): no cruzar API↔local por
  nombre.
- `~$` de Office → `ERROR_SHARING_VIOLATION` más frecuente sobre directorios activos.
- `MAX_PATH` (260) puede romper rutas profundas que sí existen en la nube.

---

## Evidencia (comprobaciones ejecutadas 2026-07-16)

| Comprobación | Resultado |
|---|---|
| `Get-Volume G,H` | No los reconoce como volúmenes → driver propietario |
| Leer stub `.gdoc` (`ReadAllText`) | `ERROR_INVALID_FUNCTION` (kernel bloquea lectura de `.g*`) |
| Resolver `.lnk` (`WScript.Shell`) | → `H:\.shortcut-targets-by-id\<fileId>\<nombre>` |
| Atributos de ficheros | `Normal` en todos (sin flag OFFLINE) |
| `GetCompressedFileSizeW` | Devuelve tamaño lógico (no distingue hidratación) |
| `metadata_sqlite_db` | Existe (144 MB / 259 MB) + `mirror_metadata_sqlite.db` (162 MB) |
| Esquema BD | `items`(18 cols), `stable_ids`, `shortcut_details`, `item_properties` |
| `item_properties.content-entry` | 121.659 / 165.058 items |
| Ficheros reales HOT vs COLD | 102.001 HOT / 36.166 COLD (de 138.167) |
| Carpeta `content_cache` | Existe bajo `DriveFS\<idCuenta>\` |

---

## Pendientes de decidir

**Ninguno — todos cerrados (2026-07-16).** Cierre de los últimos 5:
#5 leer binario al modelo → DESCARTAR · #6 metadatos PDF/EXIF → DIFERIR ·
#34 verificar manifiesto → INCLUIR · #35 diff → DIFERIR · #43 watch → DESCARTAR.

## Resumen de decisiones

- **INCLUIR** (alcance del MCP): 1, 2, 3, 8–16, 18–22, 24–28, 30–34, **45 (estado HOT/COLD)**.
- **DIFERIR** (sin disparador): 6, 35.
- **DESCARTAR**: 4, 5, 23, 29, 41, 42, 43, 44.
- **SOLO API** (`google-despacho`, no el FS): 7, 17, 36–40.
- **Guardas transversales**: hidratación (pre-lectura/copia/zip/hash) · bloqueo `.g*` ·
  timeouts amplios.

## Guardas y hallazgos adoptados (revisión adversarial, 4 rondas)

1. **Escritura atómica**: nunca sobrescribir in-place; escribir a `.tmp` + renombrar
   (replace). Evita corrupción por colisión con edición humana en la nube.
2. **Anti-escape de sandbox por atajos**: todo destino resuelto de un `.lnk`/`shortcut_details`
   se **re-valida** por el guardarraíl y debe empezar por `G:\`/`H:\`; si apunta a otra
   unidad, UNC de red o ruta del sistema → bloquear y reportar.
3. **Pipeline de guarda de lectura**: extensión `.g*` (bloquear→API) → estado HOT/COLD
   (BD) → si COLD y >10 MB, abortar `ERROR_FILE_NOT_HYDRATED`.
4. **Aislamiento de la BD GDFD**: copiar el trío `metadata_sqlite_db`+`-wal`+`-shm` y
   consultar solo-lectura sobre la copia; **degradación elegante** (si el esquema cambia →
   modo conservador: hidratación "desconocida", timeouts 60 s).
5. **Robustez de E/S**: offload de operaciones pesadas fuera del canal MCP · backoff
   exponencial ante `ERROR_SHARING_VIOLATION` (`~$` de Office) · prefijo `\\?\` para
   `MAX_PATH` · `du` desde la BD · dry-run en batch-rename · tope en copy-tree
   (>150 MB o >10% COLD) · **log de auditoría de operaciones mutantes fuera del volumen Drive**.

## Candidatos net-new (aceptados a verificar)

- **#46 confirmar subida a la nube** (tabla `operations`): tras escribir prueba, confirmar
  que GDFD la subió (custodia). *A verificar: detalle en blob `proto`, ¿consultable?*
- **#47 mapear propietario** (`items.is_owner`, `shared_with_me_date`): procedencia del
  documento. Columnas existen.
- **#48 huella de dispositivo** (registro GDFD): cadena de custodia máquina↔acción. Opcional.

## Riesgos abiertos (VERIFICAR antes de congelar el spec)

- **#4 leer rango de bytes**: fuente externa se contradice entre rondas (¿el header de un
  COLD se lee rápido o fuerza descarga total?). DESCARTADO salvo test con fichero frío.
- **`attrib +P -U`** para forzar hidratación: ¿funciona y es reversible en GDFD actual?
- **tabla `operations`** como cola de subida: ¿estado "pendiente" consultable sin decodificar
  el protobuf indocumentado?
