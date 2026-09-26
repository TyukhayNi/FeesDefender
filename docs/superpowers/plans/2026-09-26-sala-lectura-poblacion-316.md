---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: MEJORAS #316 — la población de la sala de lectura tiene contrato y se comprueba, en los dos productores (skill organizar-sala-lectura y motor CLI), y C3 honra lo declarado
---

# La sala de lectura da cuenta de todo lo de `00_Input` (MEJORAS #316)

> **Estado (2026-09-26):** construido con TDD; la R1 de Codex sobre el diff (§6) está pendiente.
> Fila **#46** de `PLAN.md`.

**Encargo.** Nikolai pidió hacer el `#316` en la misma sesión que el #407, tras mergearlo. La
entrada del backlog decía «la sala de lectura no recoge audios, zips ni tarjetas de contacto, y
ninguna regla dice que no deba», medido por la C3 por identidad en 14 de 23 expedientes.

## 1. Lo medido: una frontera, dos productores

**La población del catálogo no tenía contrato.** Nada exigía, y nada comprobaba, que cada fichero
de `00_Input` acabase con fila en la sala o con una exclusión declarada. Y la sala la montan dos
productores distintos, con causas distintas:

- **La skill `organizar-sala-lectura`** (salas con el catálogo dentro de `Sala lectura/`). El Paso
  1 lo hace el agente con sus herramientas; su verify contrastaba el manifiesto con lo **copiado**,
  nunca con lo que había. Sobre los 17 manifiestos reales: las exclusiones se declaran en cinco
  formatos de texto libre —«No copiados», «Duplicados detectados», «Excluido de la sala»…—, y en
  varios casos ficheros enteros no figuran en ninguna parte.
- **El motor CLI** (`core/sala_lectura.py`, catálogo en `01_Procesado/`), que es el que montó
  **W-02Y2J6** (audiencia previa el 14/10) y W-030TZY. Causa en el código: `core/inventory.py`
  tenía una **lista blanca de extensiones** y mandaba lo demás a `skipped`, que nadie leía; el
  catálogo se construye con lo inventariado. El inventario de W-02Y2J6 tiene 22 en `skipped`: 8
  `.opus` —siete notas de voz de WhatsApp, transcritas en `03_MD`—, 11 `.zip`, 2 `.vcf` y 1 `.mp4`;
  el de W-030TZY, sus 7. En los 15 inventarios reales la lista dejó fuera también un `.pptx`, un
  `.m4a`, un `.numbers`, once documentos sin extensión y 54 planos `.gml`.

**Y la lista blanca hacía de filtro de protocolo sin decirlo:** apartaba tres ficheros que
`scripts/migrate_05crm_buckets.py` deja en la raíz (`_migration_05crm_<ts>.json`,
`_caso.md.bak_<ts>`, `_intake_hashes.json.bak_<ts>`) y que el registro por ubicación no
contemplaba; el propio comentario de `inventory.scan` contaba con ello. La sala de máquina, sin
lista, los inventariaba como documentos.

## 2. Diseño

**El contrato (`SKILL.md` 1.18, Paso 5):** cada fichero de `00_Input` tiene fila o una línea en
`## No copiados` con formato cerrado —`` - duplicado: `ruta` — de `…` `` o
`` - excluido: `ruta` — motivo ``—, nunca ninguna de las dos. Solo tres reglas de productor no piden
línea: el **protocolo** del registro por ubicación, el **zip crudo** de WhatsApp junto a su chat y
la **firma** `_firma_*` que `core/email_export` marca y deposita en un lote de correo
(`PREFIJO_FIRMA`). Audios, vídeos, zips y vCards son documentos: fila, con `08` si no se saben leer.

**La verja de la skill** (`verificar_sala.problemas_poblacion`, con `--cobertura`, que pasa a ser
obligatorio si existe la sala de máquina): cada fuente de la cobertura tiene fila por ruta o por
sha256 de origen, o línea declarada; si no, exit 1. `manifiesto_parser.parse_no_copiados` lee el
formato cerrado (y el alias antiguo `duplicado, saltado`), y en modo estricto una línea fuera de
formato es un error. `verificar()` no cambia: la verja es una función aparte, porque los tests de
fechas le pasan filas de cobertura mínimas. La skill es autónoma —en Cowork no hay `core/`—, así
que lleva `scripts/intake_control.py`, **copia exacta** de `core/intake_control.py`, con un test que
exige los mismos bytes.

**El motor CLI:** `inventory.scan` recoge todo lo que no es protocolo. Qué sabe leer el extractor
lo decide el extractor —salta con `ExtractionError` lo que no conoce, como ya hacía con las fotos—.
Fuera `skipped` y la rama «sin_extension_relevante» del `organizar`, que ya no se alcanza.

**El registro:** los tres ficheros de la migración entran en `RAIZ_PREFIJOS`, con su escritor real
contrastado por el test T10.

**C3** (`verificar_apertura`): no exige lo que la sala declara en `## No copiados` con formato
cerrado ni la firma de `email_export`; los cuenta aparte (`declaradas_no_copiadas`,
`firmas_de_correo`) y lo dice. Un manifiesto que existe y no se puede leer es `fallo`. `core` no
importa la skill ni `email_export`: parser, regla y prefijo son copias, y tres tests anti-deriva las
comparan con los originales sobre el mismo texto y las mismas rutas.

## 3. Tests

**31 nuevos:** cuatro del parser (formato, sin sección, texto libre y línea sin motivo en modo
estricto); diecisiete de la población (la firma solo en su lote y su anti-deriva, la copia exacta
del registro, la verja con fila por ruta y por sha256, con declaración, con las tres reglas y sus
controles, sin `rel_path`, y cuatro del CLI); uno del registro (los ficheros de la migración); uno
del inventario (audios, zips, vCards, `.pptx`, vídeo y sin extensión); ocho de C3 (declarada,
texto libre, firma y su control, manifiesto ilegible, y tres anti-deriva).

**Cuatro tests fijaban la lista blanca, y se reescriben declarándolo en su docstring:**

- `test_inventory_scan_filtra_extensiones` exigía que un `ruido.bin` quedara fuera: era el defecto.
  Ahora exige que entre, y que no exista `skipped`.
- `test_ficheros_sin_extension_relevante_NO_abortan_pero_se_declaran` exigía «sin material» con
  solo planos `.gml`/`.dxf`: ahora entran en la sala como `08`.
- `test_inventory_clasifica_por_fuente` ponía `.pulled` y `.synced` en `05_CRM/` y `01_Drive EV/`,
  donde no los escribe nadie —el pull v2 del CRM guarda su estado en `update_pull_state`—: los
  apartaba la lista, no el registro. Van a los sitios de sus productores.
- `test_t1_el_adjunto_homonimo…` exigía el adjunto en `files ∪ skipped`; ahora en `files`, que es
  más fuerte.

**Un defecto de los propios tests, cazado en el camino:** la shell se comió las barras invertidas
de las rutas de Windows al escribirlos, y `"00_Input\2026…"` quedó como un escape octal (`\x82`).
Un test del parser pasaba **por la razón equivocada** —los dos lados llevaban el mismo carácter de
control—. Las rutas se arman ahora con `chr(92)`.

**Mutantes:** 16 sobre la skill, C3, el inventario y el registro; 15 mueren en memoria, y el del
inventario —la lista blanca de vuelta— sobrevivía en memoria porque `test_inventory.py` hace
`importlib.reload`, que relee el módulo del disco y tira la copia mutada. Sobre una copia
`git archive` con la mutación escrita, **muere**: caen tres tests. El de identidad, vivo.

**Suite:** 6.844 recogidos, 0 fallos, 96 `skipped` (JUnit): los 6.813 de `main` más los 31.

## 4. Medido con los datos reales

- **La verja de la skill** sobre los 17 manifiestos de salas montadas por ella: habría parado **12**
  —W-02JSVZ con 110 fuentes sin dar cuenta; los demás, entre 1 y 6—; W-0462E1, además, por una
  línea de `## No copiados` en prosa.
- **C3** sobre los 23 expedientes: **7 en `ok`** (antes 5). W-02UIQU pasa a `ok` por sus 31
  declaraciones, y W-02O7E2 porque sus doce `.png` eran firmas de correo; W-0462E1 baja de 22 a 3
  (los zips que declara en prosa).
- **W-02Y2J6 y W-030TZY siguen igual hasta que se vuelva a correr su `organizar`** con el
  inventario nuevo: es lo que llevará a la sala sus audios, zips, vCards y vídeo. Es una acción
  sobre el expediente, y la decide Nikolai.

## 5. Lo que no cubre, dicho

- **Las salas ya montadas no cambian solas:** hace falta re-correr la skill o el `organizar` CLI.
  Las secciones antiguas con otros encabezados («Duplicados detectados», «Excluido de la sala») no
  se leen, y C3 sigue nombrando esos ficheros hasta que se declaren en el formato cerrado.
- **La verja de la skill vigila, no clasifica:** el agente sigue siendo quien lista y decide; lo que
  cambia es que no puede dar la sala por buena dejando algo sin decir.
- **`SKILL.md` tiene 619 líneas**, por encima de las 500 de la guía, y ya tenía 607. Recortarlo es
  otro encargo: suprimir norma es cambio de contenido.
- **El arnés de mutantes en memoria no vale para un módulo que sus tests recargan**
  (`importlib.reload`); ahí hace falta una copia con la mutación escrita.

## 6. Ronda y modelo

**Una ronda sobre el diff.** Toca `core/` y una skill, pero ni decide quién escribe ni puede
destruir datos de cliente: el inventario y la sala CLI escriben **más copias derivadas** en
`01_Procesado/` —nada se sobrescribe ni se borra del crudo—, y el registro solo clasifica tres
ficheros de la migración como protocolo. **Fila ordinaria: `gpt-6-sol` · `high` · `default`**,
cuarta del ledger de calibración de la #38.
