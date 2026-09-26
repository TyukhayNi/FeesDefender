---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: MEJORAS #316 — la población de la sala de lectura tiene contrato y se comprueba, en los dos productores (skill organizar-sala-lectura y motor CLI), y C3 honra lo declarado
---

# La sala de lectura da cuenta de todo lo de `00_Input` (MEJORAS #316)

> **Estado (2026-09-26):** construido con TDD; la R1 de Codex sobre el diff volvió `NO-SHIP` con
> once hallazgos, los once confirmados, y se remedió en este mismo PR **sin segunda ronda** (§7).
> Los §2 a §5 describen el diseño que queda tras la R1. Fila **#46** de `PLAN.md`.

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

## 2. Diseño (rev. tras la R1, §7)

**El contrato (`SKILL.md` 1.18, Paso 5):** cada fichero de `00_Input` **da cuenta de sí** de una de
cuatro maneras, y la verja comprueba cada una:

- una **fila con su ruta** que no la contradiga —la unidad es el par ruta/sha256 de la fila, como en
  la C3 del #407: una fila con la ruta de una fuente y otro sha256 la contradice y no acredita a
  nadie—;
- su **sha256 en otra fila**: el duplicado. Lo mide la verja y **no se declara**;
- su **contenido sin la cola de ceros del pull** (`MEJORAS #225`) en otra fila: el detector de C2,
  con el `00_Input` del caso;
- o una línea **`- excluido: `ruta` — motivo`** en `## No copiados`: una decisión, para lo que no es
  documento de este expediente —material de otro caso, un logotipo de firma sin texto—, nunca para lo
  que no se sabe leer.

`- duplicado: `ruta` — de `ruta`` es informativa y no da cuenta de nada; una ruta con fila no se
declara no copiada; el texto sin viñeta es comentario y un `###` sigue dentro de la sección. Solo
**dos reglas de productor** no piden nada: el **protocolo** del registro por ubicación y el **zip
crudo** que el intake de WhatsApp deja junto a su chat, en su lote o en `02_Whatsapp/`. La firma
`_firma_*` de `email_export` **es un adjunto más**: el productor la marca, no la descarta. Audios,
vídeos, zips y vCards son documentos: fila, con `08` si no se saben leer.

**La verja de la skill** (`verificar_sala.problemas_poblacion`, y el CLI): deduce la cobertura del
layout (`01_Procesado/02_Sala de máquina/_cobertura.json`) y el `00_Input` del caso; **sin cobertura
falla**, y solo `--sin-cobertura` —la sala que no tiene sala de máquina— da un OK que dice PARCIAL.
Contrasta lo que procesó la sala de máquina, no el disco. `manifiesto_parser.parse_no_copiados` lee
el formato cerrado (y el alias `duplicado, saltado`), y en modo estricto una viñeta fuera de formato
—también un `duplicado` que no dice de qué— es un error. La skill es autónoma: lleva
`scripts/intake_control.py`, **copia exacta** de `core/intake_control.py`, y su propia copia del
detector del relleno, las dos comparadas con las de `core` por tests.

**El motor CLI:** `inventory.scan` recoge todo lo que no es protocolo. Qué sabe leer el extractor lo
decide el extractor. Fuera `skipped` y la rama «sin_extension_relevante» del `organizar`.

**El registro:** los tres ficheros de la migración se casan **por nombre entero, con su sello**
(`RAIZ_PATRONES`), no por prefijo; un test corre el escritor y exige que lo que deja sea protocolo.

**C3** (`verificar_apertura`): la clave de la cobertura no pierde un `00_Input/` del cliente (la del
catálogo sí, que lo lleva); el zip crudo solo se aparta donde escribe el intake; la firma se exige;
la copia con relleno de `#225` cuenta por su contenido (`por_relleno_225`); una línea `duplicado` no
exime; y lo declarado `excluido` no se exige pero **se enseña** en el `ok`, con ruta y motivo. Un
manifiesto que existe y no se puede leer es `fallo`. `core` no importa la skill: parser, reglas y
detector son copias, con tests anti-deriva sobre el mismo texto, las mismas rutas y los mismos bytes.

## 3. Tests

**Antes de la R1, 31 nuevos**; **tras ella, 21 más en neto** (6.844 → 6.865 recogidos). El detalle
de los de la R1 está en el §7 y en los mensajes de sus commits.

**Cuatro tests fijaban la lista blanca, y se reescribieron declarándolo en su docstring:**

- `test_inventory_scan_filtra_extensiones` exigía que un `ruido.bin` quedara fuera: era el defecto.
  Ahora exige que entre, y que no exista `skipped`.
- `test_ficheros_sin_extension_relevante_NO_abortan_pero_se_declaran` exigía «sin material» con
  solo planos `.gml`/`.dxf`: ahora entran en la sala como `08` —y, tras la R1, se exigen las dos
  copias por su contenido, no «alguna acción»—.
- `test_inventory_clasifica_por_fuente` ponía `.pulled` y `.synced` donde no los escribe nadie: van
  a los sitios de sus productores, y tras la R1 un `.pulled` homónimo fuera de su sitio tiene que
  ENTRAR.
- `test_t1_el_adjunto_homonimo…` exigía el adjunto en `files ∪ skipped`; ahora en `files`.

**Un defecto de los propios tests, cazado en el camino:** la shell se comió las barras invertidas
de las rutas de Windows al escribirlos, y `"00_Input\2026…"` quedó como un escape octal. Un test
del parser pasaba **por la razón equivocada**. Las rutas se arman ahora con `chr(92)`.

**Mutantes — corregido tras la R1.** La primera versión de este plan decía «16 mutantes, 15 mueren
en memoria y el del inventario sobre una copia». **Esa cifra salía de un arnés del scratchpad y es
una afirmación mía, no evidencia**: la regla de que un arnés fuera del repo no acredita nada ya
estaba escrita. El arnés vive ahora en **`tests/_mutantes_sala_lectura_316.py`**: 32 mutantes, uno
por frontera del contrato y atado cada uno a su test, sobre una copia del árbol, con el contrato
estricto —base verde, ancla única y muerte solo por el aserto—. **32 de 32 muertos por su aserto**,
en una corrida sobre el código final. En la primera, C03 murió por `AttributeError` —el programa
roto, no detectado— y se reapuntó al fallo silencioso que nombra `_leer_cobertura`.

    python -m tests._mutantes_sala_lectura_316

## 4. Medido con los datos reales

Sobre los 24 expedientes con cobertura (23 con sala y W-02USSI sin ella), con el código de antes de
la R1 (`196b0aa`) y el de después:

- **La verja de la skill,** sobre los 17 manifiestos de salas montadas por ella: para **12** antes y
  **12** después, con 144 → 167 problemas. Los cambios: W-02O7E2 entra (sus 12 firmas no están en la
  sala), W-02Q38C sale (sus dos «duplicados» eran copias con relleno de `#225`), y W-0462E1 pasa de 3
  a 16 —dos firmas y **once `duplicado` que ni el sha256 ni el relleno confirman**—. W-02JSVZ sigue
  con 110 fuentes sin dar cuenta.
- **C3:** `main` tenía 5 en `ok`; el diseño de antes de la R1, 7; el de después, **6** (17 `fallo`,
  1 `pendiente`). Solo W-02O7E2 cambia de estado, por sus firmas. W-02UIQU sigue en `ok`: declara
  `excluido` su logotipo, y sus cuatro copias con relleno cuentan por su contenido.
- **W-02Y2J6 y W-030TZY siguen igual hasta que se vuelva a correr su `organizar`** con el inventario
  nuevo. Es una acción sobre el expediente, y la decide Nikolai.

## 5. Lo que no cubre, dicho

- **Las salas ya montadas no cambian solas:** hace falta re-correr la skill o el `organizar` CLI. En
  C3, W-02O7E2 y W-0462E1 salen ahora en `fallo` por lo que la R1 destapó —las firmas y los once
  «duplicados» sin confirmar— hasta que se rehagan.
- **La verja contrasta la cobertura, no el disco** (H-11): un fichero de `00_Input` que la sala de
  máquina no procesó no lo ve. Un censo físico contra la cobertura sería otra pieza, sin disparador.
- **Los dos productores no montan la misma sala** (H-08): el motor CLI —deprecado frente a la skill—
  copia el zip crudo de WhatsApp como documento y la skill lo aparta por regla. C3 acepta las dos y
  ninguna pierde un documento; la firma, tras la R1, la copian las dos.
- **Una fila `md5:` del Modo 3 da cuenta solo por su ruta,** y la verja no mide el relleno sin el
  `00_Input` del caso en su sitio: en los dos casos no da por visto lo que no puede medir.
- **`excluido` es una decisión:** C3 la enseña y no la juzga. El motivo lo juzga el letrado.
- **`SKILL.md` tiene 629 líneas** (619 antes de la R1), por encima de las 500 de la guía.
  Recortarlo es otro encargo: suprimir norma es cambio de contenido.
- **El paquete `.skill`** se construyó en el scratchpad y se comprobó: 12 ficheros idénticos a la
  fuente, y su `verificar_sala.py`, corrido aislado (`python -I`), deduce la cobertura y caza la nota
  de voz sin fila. El que importe Nikolai se empaqueta tras el merge.

## 6. Ronda y modelo

**Una ronda sobre el diff.** Toca `core/` y una skill, pero ni decide quién escribe ni puede
destruir datos de cliente: el inventario y la sala CLI escriben **más copias derivadas** en
`01_Procesado/` —nada se sobrescribe ni se borra del crudo—, y el registro solo clasifica tres
ficheros de la migración como protocolo. **Fila ordinaria: `gpt-6-sol` · `high` · `default`**,
cuarta del ledger de calibración de la #38.

## 7. Adjudicación de la revisión adversarial del diff (Codex, 2026-09-26) — NO-SHIP, remediado

- **Objeto revisado:** el diff `1aa1871..196b0aa` (la skill `organizar-sala-lectura` 1.18, `core/inventory.py`, `core/intake_control.py`, `core/sala_lectura.py`, `scripts/sala_lectura.py`, la C3 de `core/verificar_apertura.py` y sus tests), contra este plan
- **Ronda:** R1 de la pieza y la única de su presupuesto (toca `core/` y una skill, sin decidir quién escribe ni poder destruir datos de cliente)
- **Revisor:** Codex CLI `0.155.0-alpha.16.4`, `gpt-6-sol` · `high` · `default` (modelo y esfuerzo releídos del rollout; la velocidad, afirmada desde el lanzador conservado)
- **Informe recibido:** `docs/superpowers/plans/2026-09-26-sala-lectura-poblacion-316-r1-adversarial-review.md`
- **Hallazgos:** 11 — 3 `alta`, 7 `media`, 1 `baja`; 11 confirmados contra la fuente, 0 refutados (dos sub-puntos de H-05 se adjudican en contra: ver abajo)
- **Remediado en:** este mismo PR (#408), sobre `196b0aa`, en seis commits (`5fc3d0f`…`d040447`): la verja, su CLI y su parser, `preclasificar.py`, `core/intake_control.py` y su copia, C3, `SKILL.md` y su CHANGELOG, los tests y el arnés de mutación. **Ninguna ronda revisa el remedio**: el presupuesto de la pieza era una, y una segunda exige la autorización de Nikolai

**Los once se reprodujeron contra el código, no contra el informe** (acta §2). Y antes de remediar,
la pregunta de siempre —**¿de qué frontera es esto un ejemplo?**—, porque varios eran la misma:

- **H-03 (`alta` · `acotado`) es la frontera que la C3 cerró HORAS ANTES en el #407, reescrita con
  el mismo defecto en la verja nueva:** la unidad es el par ruta/sha256 de cada fila, y la verja lo
  partía en dos conjuntos globales, así que una fila `(a.pdf, sha B)` daba cuenta de `a.pdf`. Es la
  reincidencia más cara de la pieza: tenía el diagnóstico escrito el mismo día, en el módulo de al
  lado. **Remedio:** el cruce de la C3, por pares; la fila que contradice no acredita a nadie.
  **Medido antes:** cero filas contradictorias en los 17 manifiestos.
- **H-04 y H-09 (`media` · `acotado`) son una frontera: un hecho que se puede medir no se acredita
  declarándolo.** La verja aceptaba el duplicado por sha256 sin la línea que el Paso 5 prometía, y
  C3 aceptaba cualquier línea —también un «duplicado» que no lo era, que yo reproduje además del
  ejemplo del informe—. **Remedio:** el duplicado se prueba por su sha256, la línea `duplicado` pasa a
  informativa y no exime en ninguno de los dos, la promesa del Paso 5 se reescribe como es, y solo
  `excluido` es una declaración, que C3 enseña con ruta y motivo en vez de un «N declaradas». Del
  H-04, el «nunca ambas» que cita el informe no está en el texto —el Paso 5 decía «nunca ninguna de
  las dos»—, pero la contradicción que señala existe y cuesta tres líneas: una ruta con fila y en
  «No copiados» a la vez es un problema.
  **Y medirlo cambió el remedio:** con la línea sin valor, **ocho copias con la cola de ceros del
  pull** (`MEJORAS #225`) —cuatro en W-02UIQU, cuatro en W-0462E1— y dos más en la verja de W-02Q38C
  salían sin catalogar con su contenido en la sala. El relleno también es un hecho que se mide, y C2
  ya lo medía: su detector se parte en `_originales_de_relleno_225` y C3 y la verja cruzan esos
  candidatos con el catálogo. Lo que ni el sha256 ni el relleno confirman —once «duplicados» de
  W-0462E1— queda sin catalogar, que es lo que es.
- **H-01 (`alta` · `acotado`) y H-08 (`media` · `acotado`), la firma: la marca de un productor no es
  una exclusión.** `email_export` deposita el logotipo con `_firma_` delante y lo dice en el
  comentario de la misma constante que copié —«marca, no esconde», decisión de Nikolai del
  2026-09-06, después de que un revisor colara una aceptación de honorarios que el filtro tiraba—. Yo
  copié la constante sin su doctrina. **Remedio:** fuera la regla en la verja y en C3; la firma es un
  adjunto más, con fila o con una línea `excluido` —como ya hacía W-02UIQU—. Con eso, los dos
  productores la copian igual; la otra mitad de H-08, el zip crudo, queda declarada en el §5.
- **H-06, H-07 y H-10 (`media`, `media`, `baja` · `acotado`/`trivial`): una regla de productor vale
  donde el productor escribe, y como escribe.** La clave de la cobertura recortaba un `00_Input/` del
  cliente (la cobertura nunca lo lleva: cero de 24; el catálogo sí, 457 entradas), el zip crudo se
  apartaba en cualquier carpeta con dos nombres (los 14 reales están en lotes de WhatsApp o en
  `02_Whatsapp/`), y los tres ficheros de la migración casaban por prefijo (los tres reales casan con
  el sello). **Remedio:** dos claves, una por lado; el zip, solo donde escribe el intake; los tres
  nombres, enteros y con el sello, con un test que corre el escritor de verdad.
- **H-02 (`alta` · `trivial`).** El verify daba 0 sin cobertura, y el test lo exigía. **Remedio:**
  la cobertura se deduce del layout; sin ella, 1; `--sin-cobertura` da un OK PARCIAL; una cobertura
  pedida que no existe o no es una lista, y `--sin-cobertura` con una presente, son 2. Los tres tests
  del CLI que miran manifiesto contra disco pasan `--sin-cobertura`: sin él, los dos que esperan 1
  pasarían por la cobertura que falta aunque su comprobación se rompiera.
- **H-05 (`media` · `acotado`), en parte en contra.** Se remedia que un `duplicado` sin `de `ruta``
  pasara por formato cerrado (los 47 reales lo cumplen). **Se adjudican en contra dos sub-puntos:**
  el texto sin viñeta ignorado **falla hacia el lado seguro** —no declara nada, así que la fuente
  sigue sin dar cuenta de sí y la verja la nombra—, y las dos secciones reales lo usan para rótulos;
  y un `###` dentro de «No copiados» **es una subsección suya en Markdown**, así que cerrarla ahí
  rompería una estructura legítima (no hay ninguno en los datos). Los dos quedan escritos en el
  parser, en su copia de C3 y en `SKILL.md`, con un test que fija la semántica.
- **H-11 (`media` · `acotado`).** El Paso 5 prometía «cada fichero físico» y la verja mira la
  cobertura: la promesa se escribe como es (§5). La contradicción `md5`/`sha256` del Paso 5 era
  anterior a este diff (2026-06-18) y se reconcilia en una frase: una fila `md5:` da cuenta solo por
  su ruta. Y el paquete construido se probó (§5).

**Los tests que la R1 vio laxos, endurecidos:** el de los planos exige las dos copias por su
contenido, y el de las fuentes, que un `.pulled` fuera de su sitio entre. **Y los que se quitaron,
declarados en su commit:** los cuatro de la regla de la firma que se retira, y su anti-deriva.

**Lo que intentó refutar y no pudo, y se conserva:** los tres nombres de la migración corresponden a
su escritor y no hay un cuarto; la copia del registro en la skill es idéntica a la de `core`; los
cuatro tests reescritos corrigen asertos que perpetuaban la lista blanca, y el mutante de sufijos cae;
el CLI copia los formatos antes omitidos y el extractor los salta sin abortar; y C3 ya rechazaba la
entrada contradictoria que la verja aceptaba.

**Para la calibración de la #38** (fila 4 del ledger): once hallazgos confirmados —tres `alta`—, y
**dos omisiones** que aparecieron después, al medir el remedio contra los datos reales y no en la
ronda: las copias con relleno de `#225` que la línea `duplicado` estaba tapando, y los once
«duplicados» de W-0462E1 que nada confirma. Las dos son consecuencia del remedio de H-09, no defectos
del diff revisado, y se anotan como tales.

**Lo que NO cambia:** la verja vigila y no clasifica; C3 sigue siendo solo lectura y sin importar
escritores; las salas montadas no cambian solas; y re-correr el `organizar` de W-02Y2J6 antes de su
audiencia del 14/10 sigue siendo decisión de Nikolai.
