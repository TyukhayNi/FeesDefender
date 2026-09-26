---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: MEJORAS #306, #307 y #287 — tres falsos rojos de `verificar_apertura`: C1 con los nativos de Google, C2 con el relleno de los ficheros que ya acaban en ceros, y C3 por identidad y no por cardinalidad
---

# `verificar_apertura`: los tres falsos rojos de las aperturas del 15 al 25 de septiembre

> **Estado (2026-09-26):** construido con TDD; la R1 de Codex sobre el diff (§6) está pendiente.
> Fila **#45** de `PLAN.md`. PR #407.

**Encargo.** Nikolai pidió el 2026-09-26 seguir limpiando el backlog de las últimas aperturas y
eligió este bloque: `#306` (C1), `#307` (C2) y `#287` (C3). Los tres son la **misma clase de
defecto**: una comprobación que compara dos lados sin aplicar la transformación que uno de ellos
sufrió —la exportación de rclone, la cola de ceros del pull, el split de la sala de máquina—. Y los
tres gritaban sobre expedientes sanos, que es como una verja se acaba ignorando.

## 1. Lo medido, antes de tocar nada

**C1 (`#306`).** En W-02Y2J6, `remoto 88, local 88` y aun así `fallo`, con los **mismos** ocho
ficheros faltando y sobrando: nativos de Google, que la API nombra sin extensión y el pull deja en
disco con la de exportación. El adaptador **pedía** el `mimeType` —para reconocer carpetas— y lo
tiraba. El pull no fija `--drive-export-formats` (`core/intake_drive.py`), así que rige el defecto
de rclone, comprobado en la 1.73.5: `docx,xlsx,pptx,svg`.

**C2 (`#307`).** En el mismo caso, cinco ficheros «sin explicar» —cuatro zips de WhatsApp y un
`.docx`— que eran exactamente `#225`. `_es_el_relleno_de_225` probaba **una** frontera, la del
primer cero de la cola, y todo ZIP acaba en `00 00` (la longitud del comentario de su registro
final), a menudo con más ceros delante (los bytes altos del desplazamiento del directorio central).

**C3 (`#287`).** Sobre los **23** expedientes de `CASOS_ROOT` que tienen cobertura y catálogo:

- el **100 %** de los hijos de bundle lleva un slug que deriva del padre (`<padre>__…`), y el padre
  **no tiene fila** por diseño del split: la guarda de R1/H-02 no se cumplía nunca. Las pocas
  «filas de padre» que aparecen son filas `duplicado` que casualmente llevan ese slug;
- **por cardinalidad no cuadra ninguno**, ni sumando un documento por bundle: la cobertura y el
  catálogo cuentan poblaciones distintas —copias por sha256, ficheros de protocolo de coberturas
  antiguas, el zip crudo de WhatsApp—;
- **por identidad sí**: la premisa de R1/H-03 («no comparten clave») era falsa. La cobertura lleva
  la ruta de origen (`rel_path`) y el sha256; el catálogo, la misma ruta (`ruta_relativa`) y el
  mismo sha256 (`hash`). Cruzando por ruta y, si no, por sha256, seis casos quedaban a cero y el
  resto con residuos pequeños y legibles.

## 2. Diseño

**C1 — cada objeto remoto se cruza por el nombre que el pull le da en disco.**
`FicheroRemoto.mime_type` guarda el tipo que declara Drive. `ruta_local_esperada(f)` añade la
extensión de exportación de rclone a los cuatro tipos de sus formatos por defecto (documento, hoja,
presentación, dibujo). C1 cruza, muestra y busca colisiones por esa ruta; C2 cruza por la misma
clave, así que un nativo exportado que cae sobre un fichero subido (`x` → `x.docx` junto a un
`x.docx`) es una colisión en C1 y una clave con dos checksums en C2. Un nativo **sin** formato de
exportación —formulario, sitio— sigue contando como faltante. La evidencia cuenta los nativos
cruzados, y el `ok` lo dice.

**C2 — se prueba cada frontera posible dentro de la cola de ceros, y el hash fija cuál es.** Las
condiciones no cambian —tamaño múltiplo de 512, cola de menos de 512, una sola lectura con el
tamaño comprobado al cerrar—; lo que cambia es que el original candidato es **cualquier** prefijo
tras el cual solo quedan ceros, y solo se confirma si hashea al sha256 que Drive declara. Sigue
siendo prueba y no parecido: con el prefijo de longitud L igual al original, lo que queda detrás
son ceros hasta el siguiente múltiplo de 512, que es la firma exacta de `#225`.

**C3 — la cobertura contra el catálogo, documento a documento.** Una fuente es cada `rel_path`
distinto (un bundle partido es una). Está catalogada si su ruta es una `ruta_relativa` o, si no, si
su sha256 **de origen** (`parent_sha256`, o `sha256` en un documento suelto) es un `hash`. Y cada
entrada del catálogo tiene que tener su fuente. Las rutas se comparan relativas a `00_Input/`, con
`/` y en NFC: tres casos reales escriben `00_Input/…` en el catálogo.

Solo dos cosas no se exigen, **las dos reglas de sus productores** y contadas en la evidencia:

- lo que el registro por ubicación declara protocolo (`core/intake_control.es_fichero_de_protocolo`,
  `MEJORAS #149`): la misma pregunta que hoy se hace la sala de máquina para no inventariarlo. Ese
  módulo no importa nada de `core` ni escribe;
- el `_export_original.zip` con un `_chat.txt` en su misma carpeta, que la skill aparta por regla
  (`preclasificar.emparejar_exports_whatsapp`). El nombre se copia —este módulo no importa
  escritores— y un test anti-deriva lo compara con el del intake y el de la skill.

La cobertura tiene que estar sana para cruzarla: un hijo acredita a su padre en la cobertura **o en
su propio slug** (`split_documental._slug_seg`), y una fila sin `rel_path` es `fallo`. Los dos
catálogos (sala y `01_Procesado`), si existen los dos, cuadran cuando tienen **las mismas
entradas**, no el mismo número, y el fallo dice cuántas sobran en cada uno.

## 3. Tests

**C2 (5 nuevos y uno reescrito).** El ZIP real rellenado se confirma; una cola de ceros más larga
que el relleno se resuelve por el hash; si ninguna frontera cuadra no se confirma; unos bytes
**añadidos** antes del relleno no se confirman; y `n9b`, el escenario del `n9` original con el
contenido alterado, no se confirma.

**`n9` se reescribe, y es un cambio de aserto que se declara aquí.** Exigía que un fichero que ya
acababa en ceros, con el relleno detrás, saliera **sin** confirmar: era la premisa del diseño de una
sola frontera, que no podía saber dónde acababa el original. Con el hash fijando la frontera, la
etiqueta de ese caso es **verdadera**, y el test ahora exige que se confirme. Lo que protegía —que no
se ponga una etiqueta falsa— lo sostienen `n8`, `n10`, `n11`, `r1_h05b` y `n9b`, este último en su
mismo escenario. No hay otro aserto relajado en el diff.

**C1 (9 nuevos).** El adaptador conserva el tipo; los cuatro tipos cruzan (parametrizado); el nativo
que falta se nombra con su extensión; el formulario sigue faltando; un fichero no nativo no gana
extensión; y la colisión nativo/subido en C1 y en C2.

**C3 (14 nuevos).** El bundle sin fila padre cuadra por su ruta; lo no catalogado se nombra; la copia
por sha256 cuenta; una pieza se cruza por el sha256 del PDF de origen; el protocolo de una cobertura
antigua no se exige y se declara; un homónimo de protocolo fuera de su sitio sí se exige; el zip
crudo junto a su chat no se exige, y sin chat sí; una entrada del catálogo sin fuente es `fallo`; la
ruta del catálogo cruza con prefijo, barras invertidas y NFD; dos catálogos con el mismo número y
distinto contenido son `fallo`; una fila sin `rel_path` es `fallo`; un hijo cuyo slug no deriva del
padre sigue siendo huérfano; y el anti-deriva del nombre del zip crudo.

**Los fixtures de C3 cambian de forma, en un commit aparte y neutro** (`c1f63aa`): el catálogo del
fixture llevaba `slug` y `titulo`, que el real no tiene, y la cobertura no llevaba `rel_path`, que la
real lleva siempre. Con ese commit y la C3 anterior intacta, el fichero entero seguía verde: ningún
aserto cambió, solo los datos. Los tests que esperan `ok` catalogan ahora las fuentes que su
cobertura tiene.

**Y uno en `test_intake_drive.py`:** el pull no fija formatos de exportación, de modo que la tabla de
C1 sigue describiendo el disco.

**Mutantes, en memoria y sin tocar el árbol** (un plugin de pytest que ejecuta una copia mutada del
módulo): 3 de C2, 5 de C1, 14 de C3 y 1 del pull; **los 23 mueren**, y el mutante identidad queda
vivo, que es lo que prueba que el arnés no mata por sí solo.

**Suite:** 6.800 recogidos, 0 fallos, 0 errores, 96 `skipped` (JUnit), sobre la rama con `main`
(`cc98244`) fusionado. `main` recoge 6.771 en una copia de ese commit: +29, los de este diff.

## 4. Medido con la herramienta real, no con los tests

La C3 nueva sobre los 23 expedientes, en solo lectura:

- **5 en `ok`**: W-02NHNC, W-02YZO4, W-02T3XO, W-030A13, W-048U77. W-030A13 es el caso con que se
  fichó `#287`: 36 fuentes, 34 por ruta y 2 por sha256 (el mismo PDF en dos carpetas).
- **14 en `fallo` que nombra lo no catalogado**, casi todo lo que la sala de máquina no extrae:
  W-02Y2J6, 18 (8 `.opus`, 7 `.zip`, 2 `.vcf`, 1 `.mp4`), W-030TZY 7, W-02O7E2 12 `.png`, W-0462E1
  22… Son documentos del expediente que la sala de lectura no recoge; si debe recogerlos es contrato
  de la skill, y se ficha aparte (`MEJORAS #316`).
- **4 en el `fallo` de dos catálogos que no cuadran** (W-02VND1, W-02Q38C, W-02JSVZ, W-04A6LI), que
  ya daban antes por tener distinto número de entradas; ahora el detalle dice cuántas sobran en
  cada uno.

C1 y C2 no se han corrido contra la red: la corrida real de `verificar_apertura --con-red` queda
**SIN VERIFICAR** para la próxima apertura, con los datos de `#306` y `#307` como control.

## 5. Lo que no cubre, dicho

- **C1:** los nativos sin formato de exportación y los accesos directos (el pull usa
  `--drive-skip-shortcuts`) siguen saliendo faltantes. Es lo honesto —el pull no los trae—, pero no
  hay caso medido y el detalle no los distingue de un fichero perdido.
- **C1:** presentación y dibujo se cruzan por la regla de rclone, sin caso medido.
- **C2:** no se lee el `size` que declara Drive. No hace falta —el hash fija la frontera—, y pedirlo
  añadiría un campo al adaptador que no se puede probar sin red.
- **C3:** la decisión de qué ubicación del catálogo gana (`MEJORAS #221`) sigue abierta, y con los dos
  presentes y distintos C3 sigue en `fallo`. Y un catálogo antiguo sin la ruta de `00_Input` (W-02JSVZ)
  solo se cruza por sha256.
- **C3:** una fila `duplicado` cuyo titular tampoco está catalogado sale como no catalogada; es el
  mismo residuo que el titular, contado por procedencia.

## 6. Ronda y modelo

**Una ronda sobre el diff.** Toca `core/` —que nunca queda exento— pero no escribe datos de cliente
ni decide quién escribe: es un verificador de solo lectura. **Fila ordinaria: `gpt-6-sol` · `high` ·
`default`**, tercera del ledger de calibración de la #38. La frontera que haría subir a Astra sería
un falso verde silencioso; cada relajación del diff (el cruce de nativos, las fronteras de C2, las
dos exclusiones de C3) tiene su control positivo y su mutante muerto, y la fila de gobernanza de la
política es para guards y exenciones de la revisión, no para un verificador de producto. Se queda en
la fila que toca.
