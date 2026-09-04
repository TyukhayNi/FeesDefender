---
tipo: revision-adversarial
objeto: "diff de los cinco defectos del pipeline medidos abriendo W-02JSVZ"
objeto_rev: "rama claude/nuevo-caso-bad-debt-ffe40e, 2e59fe3 -> 1120596"
commit: "1120596"
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k7vr
sha256_informe: b0e37d25cba5aa90ea567162bb493aaf6490a73717da43f330d9ff1ed1fe5f08
adjudicado_en: docs/superpowers/specs/2026-09-04-apertura-w02jsvz-pipeline-r1-adversarial-review.md §3
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revisión adversarial R1.** El §0 es el mandato literal, el §1 conserva la voz del
> revisor sin una coma cambiada, el §2 es la evidencia que verifiqué por mi cuenta y el §3 mi
> adjudicación.
>
> **Dónde vive la adjudicación, y por qué aquí.** La regla de `CLAUDE.md` es que la adjudicación
> va *embebida en el spec o el plan revisado*. **Este diff no tiene ninguno de los dos**: nació de
> abrir un expediente real (W-02JSVZ) y tropezar con cinco defectos, que se registraron como
> `MEJORAS #148` a `#152` y se arreglaron directamente. Crear un spec retrospectivo solo para
> tener dónde adjudicar sería papeleo, así que la adjudicación va en el §3 de esta misma acta,
> **declarado en el frontmatter** para que nadie la busque en otro sitio. No es la forma
> preferente y se dice, en vez de disimularlo. Precedentes del mismo día:
> `2026-09-04-gitignore-reglas-inertes-r1-adversarial-review.md` y
> `2026-09-04-crm-lectura-relaciones-r1-adversarial-review.md`.
>
> **Cuántas rondas: una estaba MAL contada, y el revisor lo demostró.** Antes de lanzarla escribí
> que a estas cinco piezas les tocaba **una** ronda porque «ninguna decide quién escribe sobre qué
> copia ni puede destruir datos de cliente». El hallazgo CRÍTICO demuestra que `#149` **sí** podía
> destruir prueba del cliente —un `unlink()` sin comparar bytes—, luego era pieza de **dos**
> rondas. La consecuencia no fue una R2 sobre lo mismo: fue **revertir `#149`**, que devuelve el
> diff a la categoría de una ronda. La segunda ronda queda para cuando `#149` se haga bien, con su
> contrato por ubicación, y esa sí nace con presupuesto de dos.

## 0. Mandato, literal

# MANDATO — Revisión adversarial de un DIFF de código (FeesDefender)

## Higiene, primero

Tu directorio de trabajo debe contener **solo este `MANDATO.md`**. Si encuentras cualquier otro
fichero (informes, logs, salidas), **no lo leas** y decláralo en la primera línea de tu informe.
Los ficheros `_sonda.txt` y `_sonda_out.txt`, si están, son de una sonda de arranque mía: ignóralos
y menciónalos.

## Rol

Eres el revisor adversarial. Tu trabajo es **encontrar defectos**, no aprobar. El autor del diff
(Claude) adjudicará cada hallazgo contra la fuente, así que un hallazgo concreto y falsable vale
mucho más que una observación general. No hace falta que seas amable.

## Objeto

Dos copias congeladas, en un directorio **hermano** al tuyo:

- `../rev-fd-pipeline-2243-obj/base/` — el estado ANTES (commit `2e59fe3a62bc15e90b11d051df322b2a93bd20d3`)
- `../rev-fd-pipeline-2243-obj/head/` — el estado DESPUÉS (commit `11205963369f9628730abff8f61119642a71aa02`)

No hay `.git`: no puedes acreditar la genealogía, solo el contenido. **Calcula el `sha256` de los
ficheros que revises al abrir y al cerrar** y hazlo constar: es la prueba de que no mutaste el
objeto (sustituye al `git status` limpio). Si necesitas escribir algo, escríbelo en TU directorio.

Ficheros de producción cambiados (los tests y `docs/` también están, y son parte del diff):

```
core/abrir_caso.py        core/config.py       core/sala_lectura.py    core/utils.py
scripts/abrir_caso.py     scripts/crm_ficha.py scripts/sala_lectura.py
```

## Contexto: qué dice el autor que arregló

Cinco defectos medidos abriendo un expediente real. El autor sostiene que:

1. **`core/abrir_caso.py` + `core/utils.py` + `scripts/abrir_caso.py`** — `componer_case_id` no
   validaba, así que una dirección con `/` («s/n») partía la carpeta del caso en dos y la corrida
   terminaba con **código 0**. Se extrae `exigir_sin_caracteres_de_ruta` (guarda **estrecha**: solo
   la gramática de rutas, no el formato canónico del `case_id`) y `validate_case_id` delega en ella.
2. **`core/config.py`** — cuatro ficheros de protocolo (`_ficha_crm.yaml`, `_intake_hashes.json`,
   `_ocurrencias_crm.json`, `_manifiesto.yaml`) entraban en el inventario probatorio de la sala de
   máquina. Se declaran en `INTAKE_CONTROL_FILES`.
3. **`scripts/crm_ficha.py`** — el CRM desescapa `&amp;` a `&` al guardar y la verificación
   comparaba byte a byte, así que salía con exit 1 sobre una escritura correcta. Se añade
   `_mismas_notas`, que desescapa las dos partes y compara por **igualdad**.
4. **`core/sala_lectura.py`** — `_md_path` y `_link_md` apuntaban a `01_Procesado/MD/` (motor
   jubilado) en vez de `01_Procesado/02_Sala de máquina/03_MD/`; se añade `_md_paths` para los
   bundles partidos por el split (`<slug>__d01_TIPO.md`).
5. **`core/sala_lectura.py` + `scripts/sala_lectura.py`** — `_write_worklist` reconstruía la
   worklist y borraba la clasificación hecha a mano; `organizar` omitía `catalogo` y `aplicar`, así
   que no convergía; la CLI no resolvía el W-code.

## Dónde el autor DECLARA no estar seguro

Ataca esto primero, y no te limites a esto:

- **El (2) es la superficie más expuesta.** Añadir nombres a `INTAKE_CONTROL_FILES` afecta a cinco
  consumidores: `core/intake_drive.py`, `core/intake_manual.py`, `core/inventory.py`,
  `core/email_export.py` y `scripts/migrar_layout_intake.py`. El autor **solo leyó
  `email_export.py`**. ¿Rompe alguno de los otros cuatro? ¿Puede un documento legítimo del caso
  quedar excluido del inventario probatorio por llamarse así? ¿Y `_manifiesto.yaml` por basename,
  en cualquier profundidad, es correcto?
- **(5) `_write_worklist` ahora fusiona.** Una fila cuyo hash ya no está en el residuo se
  **descarta** (solo se itera el residuo actual). ¿Se pierde algo con eso? ¿Qué pasa con una
  columna `Fecha` que el humano vació a propósito?
- **(5) `organizar` llama a `aplicar_clasificacion` sin condición.** ¿Interacción con `confianza`,
  `UMBRAL_CONFIANZA_AUTOMOVE` y el recálculo del residuo? ¿Puede quedar en bucle o perder trabajo
  si la worklist trae un `Tipo` inválido?
- **(1) La guarda es estrecha a propósito.** ¿Queda alguna vía que componga una ruta de caso desde
  entrada del usuario **sin** pasar por `componer_case_id`? El autor comprobó los llamadores de esa
  función, no la inversa.
- **(3) y (4):** ¿la normalización de entidades puede volverse permisiva y tragarse una pérdida
  real? ¿El `glob(f"{slug}__d*.md")` puede casar un fichero que no sea un segmento del documento?

## Puedes EJECUTAR, y eso cambia la ronda

El **Python de sistema** tiene `pytest`, `filelock`, `yaml`, `dotenv`, `typer`, `httpx` y `mcp`:

```
C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

Dos avisos que te ahorran falsos rojos:

- Usa `--basetemp` **relativo dentro de tu propio workdir** (no `C:\t\...`: tu sandbox no puede
  crearlo, da `PermissionError WinError 5`), y **corto**, o MAX_PATH tumba tests que están bien.
- **No mutes `../rev-fd-pipeline-2243-obj/head/`.** Si necesitas correr, cópialo a tu workdir.
- No tienes `pytest-randomly`. Si algo exige dos semillas, declara **SIN VERIFICAR**; eso lo cubre
  el autor.
- Dos tests de `tests/test_crm_dedup_incertidumbre.py` fallan **en base y en head** por falta de
  `.env` (`SUDESPACHO_LEGACY_HOST`). Es un defecto conocido y ajeno a este diff: no lo atribuyas.

## Qué tiene que devolver tu informe

Escribe `INFORME.md` en tu directorio, con:

1. **Un hallazgo por bloque**, y en cada uno: severidad (`CRÍTICO` / `ALTO` / `MEDIO` / `BAJO`),
   fichero y línea, **el escenario concreto de fallo** (entradas o estado → resultado incorrecto), y
   qué lo demostraría. Si lo ejecutaste, pega la salida.
2. Lo que revisaste y **no** encontraste defectuoso, en una línea por pieza. Sirve para saber qué
   quedó cubierto.
3. Lo que **no pudiste verificar**, y por qué. Un revisor que no corre no refuta: deja sin
   verificar, y eso hay que declararlo.
4. El `sha256` de los ficheros de producción del head, al abrir y al cerrar.
5. **En la ÚLTIMA línea, el veredicto, exactamente una de estas cuatro palabras y nada más:**

```
SHIP
SHIP-CON-RESERVAS
NO-SHIP
SIN-VERIFICAR
```

No inventes una quinta. Si dudas entre dos, elige la más conservadora y explica por qué arriba.

## 1. Informe recibido, literal

> Voz del revisor, sin una coma cambiada. El digest del frontmatter se computa sobre
> este bloque canonicalizado (`\r\n`→`\n`, sin saltos sobrantes al principio ni al
> final, UTF-8), que es lo que recomputa el guard G8.

<!-- informe-literal:inicio:k7vr -->
Higiene inicial: el directorio contenía únicamente `MANDATO.md`; no había informes, logs, `_sonda.txt` ni `_sonda_out.txt`.

# Revisión adversarial del diff 2e59fe3a → 11205963

## Hallazgos

### CRÍTICO — `scripts/migrar_layout_intake.py:87-100, 120-123`; causa en `core/config.py:585-588` — la migración borra por basename un documento de contenido distinto

**Escenario.** Ya existe el protocolo canónico `00_Input/_ficha_crm.yaml` y un correo antiguo contiene un adjunto legítimo distinto en `00_Input/03_Email/_ficha_crm.yaml`. Al ampliar `INTAKE_CONTROL_FILES`, la migración trata el segundo como estado de canal solo por su basename. Como el destino raíz ya existe, lo añade a `duplicados_a_borrar` y después ejecuta `unlink()` sin comparar bytes ni hash. Se pierde el adjunto. Ocurre igual con cualquiera de los otros tres nombres añadidos.

**Demostración ejecutada.** Una prueba diferencial con bytes `canonical protocol` y `legitimate email attachment` conservó ambos contenidos en base (`True`) y eliminó el segundo en head (`False`). La reproducción pytest en head produjo:

```text
FAILED test_migration_never_deletes_different_bytes_solely_by_control_basename
E assert b'legitimate email attachment' in {b'canonical protocol', ...}
```

Lo demostraría como corregido una colisión con bytes distintos que aborte o preserve ambos ficheros; solo podría descartarse automáticamente si el hash coincide.

### ALTO — `streamlit_app.py:1977-1994, 2151-2163`; sumidero en `core/case_manager.py:338-343` — la UI principal sigue reproduciendo exactamente el caso `s/n`

**Escenario.** La UI compone `_case_id_auto` con interpolación propia y pasa `final_case_id` directamente a `ensure_case`; no llama a `componer_case_id` ni a la guarda extraída. Con dirección `Castell De Rosanes s/n 08530`, Windows interpreta `/` como separador, crea dos componentes bajo la ciudad y la UI muestra `Caso local disponible`. La ruta es idéntica en base y head: el parche arregla el CLI de seis campos, no la puerta principal de alta.

**Demostración ejecutada.** Sobre head:

```text
FAILED test_case_creation_rejects_multicomponent_case_id
E Failed: DID NOT RAISE ValueError
```

Lo demostraría una prueba desde la composición real de Streamlit que verifique rechazo antes de `ensure_case` y ausencia de toda carpeta parcial.

### ALTO — `streamlit_app.py:1983-1994`; `core/casos/case_locator.py:132-158, 261-267`; `core/case_manager.py:338-343` — el override permite escapar de `CASOS_ROOT`

**Escenario.** Un usuario introduce `..\..\escape` o una ruta absoluta de Windows como override. `destino_de_alta` y `path_for_ciudad` concatenan sin exigir un componente relativo ni verificar contención; una ruta absoluta descarta la raíz y `..` la atraviesa. `ensure_case` hace `mkdir(parents=True)` y deposita allí el expediente. Esto no exige imponer formato canónico: falta la gramática mínima de ruta en el sumidero que todas las altas comparten.

**Demostración ejecutada.** La composición pura dio `C:\Windows` para un `case_id` absoluto, y la prueba sobre `ensure_case` produjo:

```text
FAILED test_case_creation_rejects_parent_traversal
E Failed: DID NOT RAISE ValueError
```

Lo demostraría una prueba de contención para rutas absolutas, `..`, `/` y `\` en `destino_de_alta`/`path_for_ciudad`, sin creación fuera de la raíz.

### ALTO — `core/sala_lectura.py:736-741` — `organizar` no incorpora documentos nuevos si ya hay cualquier catálogo

**Escenario.** Se cataloga `Factura uno.pdf`; después llega `Factura dos.pdf` a `00_Input`; se ejecuta `organizar`. Como `load_catalog()` no está vacío, se omiten `inventory.scan()` y `build_catalog()`. El segundo documento no entra en catálogo, worklist, índices ni sala, y el comando declara éxito.

**Demostración ejecutada.** Resultado de head:

```text
{'detenido_por_residuo': False, 'n_residuo': 0, 'acciones': {'COPY': 1}}
E assert {'Factura uno.pdf'} == {'Factura uno.pdf', 'Factura dos.pdf'}
```

Lo demostraría una prueba incremental con catálogo no vacío y una evidencia añadida después.

### ALTO — `core/config.py:585-588`; `core/intake_lotes.py:194-198`; `core/email_export.py:1079-1096`; `core/inventory.py:90-93` — la exclusión global por basename oculta adjuntos legítimos a cualquier profundidad

**Escenario.** Un correo trae un adjunto llamado `_intake_hashes.json`, `_ficha_crm.yaml`, `_ocurrencias_crm.json` o `_manifiesto.yaml`. El fichero se guarda dentro de `mensaje/adjuntos/`, pero `items_desde_disco()` y los demás consumidores aplican `p.name in INTAKE_CONTROL_FILES`, sin ubicación. El adjunto desaparece del manifiesto y del inventario probatorio. En email, la traza M9 sí puede registrarlo, dejando dos registros forenses incompatibles.

**Demostración ejecutada.** Para `mensaje/adjuntos/_intake_hashes.json`:

```text
base: ['mensaje/adjuntos/_intake_hashes.json']
head: []
FAILED test_nested_control_basename_is_not_dropped_from_lot_manifest
E assert [] == ['mensaje/adjuntos/_intake_hashes.json']
```

Lo demostraría restringir cada control a su ubicación contractual y probar homónimos en adjuntos, ramas CRM y subdirectorios de lotes.

### ALTO — `scripts/migrar_layout_intake.py:57-63, 87-105, 132-149` — un homónimo anidado se mueve pero sus referencias forenses quedan apuntando a la ruta antigua

**Escenario.** `03_Email/message/adjuntos/_ocurrencias_crm.json` es un adjunto legítimo y su ruta consta en M9, cobertura o catálogo. La migración mueve físicamente la carpeta `message` al lote, pero `_mapping_documental()` elimina el remapeo por `Path(k).name`. Los registros siguen apuntando a una ruta inexistente y el manifiesto nuevo también excluye el fichero.

**Demostración ejecutada.** Sobre M9:

```text
FAILED test_migration_remaps_forensic_path_for_nested_control_basename
E AssertionError: stale forensic path after move:
E 03_Email/message/adjuntos/_ocurrencias_crm.json
```

Lo demostraría verificar tras la migración que todas las rutas de M9, cobertura y catálogo existen y que el manifiesto incluye el adjunto.

### ALTO — `core/sala_lectura.py:273-286, 322-337`; `scripts/sala_lectura.py:87-100` — el flujo CLI entrega solo el primer segmento de un bundle

**Escenario.** Para un documento partido en `__d01_...md` y `__d02_...md`, el core concatena ambos y devuelve `md_paths`, pero `preparar-residuo` imprime únicamente `d['md_path']`, que es `d01`. El flujo humano que el propio CLI prescribe («lee cada MD») clasifica el documento con información incompleta.

**Demostración ejecutada.** La salida real solo mostró:

```text
1 doc(s) en residuo. Lee cada MD y rellena la worklist:
  - [2cbd22c9] documento ambiguo.pdf → ...__d01_DOC_A.md
FAILED test_cli_preparar_residuo_lists_every_split_segment
```

Lo demostraría exigir que stdout enumere todos los elementos de `md_paths`, o que el CLI materialice una vista concatenada explícita.

### ALTO — `core/sala_lectura.py:210-225, 733-741` — una fila obsoleta de la worklist sobrescribe una clasificación ya resuelta

**Escenario.** El catálogo contiene el hash como `06. PBC`, confianza `1.0`; quedó una fila antigua del mismo hash con `07. RECLAMACIONES`. El nuevo `organizar` llama siempre a `aplicar_clasificacion`, que casa solo por hash y no comprueba si la entrada sigue siendo residuo. Sobrescribe la decisión vigente y vuelve a fijar confianza `1.0`.

**Demostración ejecutada.** Sobre head:

```text
FAILED test_stale_worklist_row_does_not_overwrite_resolved_catalog_entry
E assert '07. RECLAMACIONES' == '06. PBC'
```

Lo demostraría que `aplicar` limite su dominio al residuo actual o use una precondición/versionado explícito.

### MEDIO — `core/sala_lectura.py:273-286` — un MD canónico obsoleto suprime todos los segmentos actuales

**Escenario.** Un documento antes pasó sin split y conserva `<slug>.md`; una corrida posterior produce `<slug>__d01_...md` y `__d02_...md`. `_md_paths()` devuelve inmediatamente el canónico si existe y no mira los segmentos. La clasificación recibe exclusivamente texto obsoleto.

**Demostración ejecutada.** Con canónico `STALE-PASSTHROUGH` y segmentos `CURRENT-A/B`:

```text
FAILED test_preparar_residuo_does_not_prefer_stale_canonical_over_segments
E assert 'CURRENT-A' in '<!-- ...md -->\nSTALE-PASSTHROUGH'
```

Lo demostraría una transición passthrough→split que archive/elimine el padre o haga preferentes los segmentos válidos.

### MEDIO — `core/sala_lectura.py:541-552, 575-578` — los enlaces «ver texto» siguen muertos para bundles partidos

**Escenario.** Solo existen `<slug>__d01_TIPO.md` y `<slug>__d02_TIPO.md`, como admite el docstring nuevo. `_link_md()` construye siempre `<slug>.md`; `render_indices()` publica ese enlace inexistente.

**Demostración ejecutada.** Sobre head:

```text
FAILED test_split_bundle_index_link_resolves_to_existing_md
E AssertionError: dead link: ../02_Sala de máquina/03_MD/documento_ambiguo__2cbd22c9.md
```

Lo demostraría resolver cada href generado desde `INDICE.md` y exigir que el destino exista; para un bundle hace falta decidir si enlazar todos los segmentos o una vista agregada.

### MEDIO — `core/sala_lectura.py:139-148, 206-225, 299-323` — un `Tipo` inválido crea un residuo irrecuperable desde el flujo normal

**Escenario.** El humano escribe `TIPO INVENTADO`. La fusión lo conserva; `aplicar_clasificacion` lo rechaza; `clasificar_caso` sigue contando el documento como residuo; pero `_hashes_residuo` solo selecciona filas cuyo `Tipo` está vacío. `organizar` se detiene y `preparar_residuo` devuelve `[]`: el siguiente ciclo no ofrece nada que corregir.

**Demostración ejecutada.** Resultado combinado:

```text
detenido_por_residuo = True
preparar_residuo(...) = []
FAILED test_invalid_tipo_remains_preparable_instead_of_becoming_invisible
```

Lo demostraría mantener los tipos no válidos dentro del conjunto preparable y mostrar un error accionable.

### MEDIO — `core/sala_lectura.py:139-147, 217-224` — vaciar `Fecha` deliberadamente no se conserva

**Escenario.** El humano borra una fecha inferida porque es incorrecta. La fusión usa `prev.get("Fecha") or fecha` y la repone; al aplicar, `fila["Fecha"] or e.fecha_doc` también impide borrar una fecha previa. Se publica una cronología que el revisor había intentado corregir.

**Demostración ejecutada.** Tras vaciar la celda y reclasificar:

```text
FAILED test_blank_date_remains_blank_after_worklist_merge
E assert '2025-01-02' == ''
```

Lo demostraría distinguir «fila/campo ausente» de «campo presente y vacío» y probar ambos estados.

### BAJO — `core/sala_lectura.py:286` — el glob no implementa la gramática ni el orden de los segmentos

**Escenario.** `glob(f"{slug}__d*.md")` acepta `__draft_notes.md` como segmento. Además `sorted()` es lexicográfico: con `d99` y `d100` concatena primero `d100`, alterando el orden documental.

**Demostración ejecutada.** Dos reproducciones dieron:

```text
['...__d100_DOC.md', '...__d99_DOC.md']
E Left contains one more item: ...__draft_notes.md
```

Lo demostraría aceptar solo `__d<dígitos>_<tipo>.md` y ordenar por el entero del identificador.

## Cobertura ejecutada

En una copia escribible de head ejecuté los seis módulos de tests afectados por el diff:

```text
python -m pytest tests/test_abrir_caso.py tests/test_abrir_caso_cli.py \
  tests/test_apertura_v1_control_files.py tests/test_crm_ficha_cli.py \
  tests/test_extractor_slug_colision.py tests/test_sala_lectura.py \
  --basetemp=..\bh -q -p no:cacheprovider
........................................................................ [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
exit code 0 (166 pruebas)
```

También ejecuté 14 reproducciones adversariales independientes en la copia de head:

```text
python -m pytest tests/test_adversarial_repros.py --basetemp=..\ba -q -p no:cacheprovider
FFFFFFFFFFFFFF                                                           [100%]
14 failed; exit code 1
```

Estas pruebas adversariales se crearon solo en la copia de trabajo; no forman parte ni modifican el objeto congelado.

## Revisado sin defecto encontrado

- `core/abrir_caso.py` + `core/utils.py` + `scripts/abrir_caso.py`: la vía nueva de seis campos sí rechaza `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>` y `|` en código, dirección y sufijo antes de crear el caso, y la CLI convierte el `ValueError` en salida 1.
- `scripts/crm_ficha.py`: `_mismas_notas` desescapa ambos lados una vez y después conserva igualdad estricta; aceptó `E&amp;V` frente a `E&V` y siguió rechazando pérdida real (`<p>abc</p>` frente a `<p>ab</p>`). No encontré una normalización permisiva.
- `core/config.py`: los cuatro protocolos dejan de entrar como evidencia cuando están en sus ubicaciones canónicas; el defecto es que el contrato se aplicó por basename global.
- `core/intake_drive.py`: la nueva lista altera el recuento de homónimos, pero no encontré un borrado adicional ni que ese recuento gobierne el éxito del pull.
- `core/inventory.py`: no encontré una nueva mutación de M9; sí queda la exclusión global ya informada.
- `core/email_export.py`: un lote normal con `.eml` no se considera vacío; la discordancia aparece en adjuntos homónimos.
- `core/sala_lectura.py`: la ruta canónica de MD no segmentados quedó corregida; la fusión conserva celdas no vacías de hashes que siguen realmente en residuo; un `Tipo` válido converge porque `aplicar` fija confianza `1.0` y el umbral usa `>= 0.80`.
- `scripts/sala_lectura.py`: la resolución de W-code mediante `_ref` está conectada a todos los subcomandos inspeccionados.
- Tests nuevos: cubren la exclusión positiva de protocolos, el caso sin catálogo, la fusión ordinaria y la concatenación del core; no cubren ubicación/profundidad, catálogo incremental, estados obsoletos ni la salida real del CLI.
- Documentación cambiada: comprobé las afirmaciones relativas a los cinco arreglos; las de bundles y convergencia quedan contradichas por los escenarios anteriores.

## No verificado

- No acredité genealogía: las copias no contienen `.git`, conforme al mandato; revisé exclusivamente su contenido.
- No ejecuté sobre expedientes reales ni contra el CRM/Drive, para no mutar estado externo. Las reproducciones usaron casos efímeros en la copia escribible.
- No ejecuté las dos semillas aleatorias porque el entorno no tiene `pytest-randomly`; esa cobertura queda expresamente **SIN VERIFICAR**.
- La suite completa no pudo acreditarse limpia en este entorno: además de los dos fallos conocidos de `test_crm_dedup_incertidumbre.py` por falta de `SUDESPACHO_LEGACY_HOST`, aparecieron pruebas que requieren `.git`, `.venv`, el wrapper MCP o escritura dentro de la copia fuente, capacidades ausentes/bloqueadas aquí. No uso esos rojos como hallazgos ni como refutación.
- No medí la frecuencia histórica de adjuntos con los cuatro basenames reservados; los fallos son deterministas cuando existe la colisión.

## Integridad del objeto revisado

Los siete ficheros de producción de head dieron el mismo SHA-256 al abrir y al cerrar:

| Fichero | SHA-256 apertura | SHA-256 cierre |
|---|---|---|
| `core/abrir_caso.py` | `873c0c2e3cb6458a6cc88476273c8b2f1fdbeef6e4a76991ac118cb7711fc9aa` | `873c0c2e3cb6458a6cc88476273c8b2f1fdbeef6e4a76991ac118cb7711fc9aa` |
| `core/config.py` | `099766d51de645be3890a97bd29a2173d15e69ecb6d296340d0b38b1f2c38656` | `099766d51de645be3890a97bd29a2173d15e69ecb6d296340d0b38b1f2c38656` |
| `core/sala_lectura.py` | `4cbe71490f2de41489f470cf02de1b2dcbb6bab83cb41fd8ba63fbe5e89323e1` | `4cbe71490f2de41489f470cf02de1b2dcbb6bab83cb41fd8ba63fbe5e89323e1` |
| `core/utils.py` | `58a3eb59fddab37390e349763afe2d851e63868730c5df8e762e726934789721` | `58a3eb59fddab37390e349763afe2d851e63868730c5df8e762e726934789721` |
| `scripts/abrir_caso.py` | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` | `bcb937066b9211dfa903a08d0ff14635c9e10ddb5d90b19a1c178a6029804375` |
| `scripts/crm_ficha.py` | `8cfe0c7c44577a02b9e39449335de0f3abac6a2183df4ed9d03c5e3bde255422` | `8cfe0c7c44577a02b9e39449335de0f3abac6a2183df4ed9d03c5e3bde255422` |
| `scripts/sala_lectura.py` | `e9386ce0416787e5fdf78219239f9e347f20ab26332998659711ba4361ca35e3` | `e9386ce0416787e5fdf78219239f9e347f20ab26332998659711ba4361ca35e3` |

El veredicto conservador es `NO-SHIP`: hay una pérdida de documento reproducible en migración y varias rutas de alta, inventario y clasificación que producen éxito aparente con estado incompleto o incorrecto.

NO-SHIP
<!-- informe-literal:fin:k7vr -->

## 2. Evidencia verificada por mí

Verifiqué en la fuente los dos hallazgos que deciden la gravedad, porque de ellos dependía si
esto era «falta trabajo» o «habría destruido un documento»:

- **`scripts/migrar_layout_intake.py:122`** — `for hijo in duplicados_a_borrar: hijo.unlink()`.
  Sin comparar bytes ni hash. El comentario tres líneas arriba dice que el borrado se aplaza a
  fase 2 **precisamente porque no es reversible**. Y en `:87-89` la condición es
  `mov.cajon == "03_Email" and hijo.name in config.INTAKE_CONTROL_FILES`: antes de mi cambio un
  `03_Email/_ficha_crm.yaml` no era fichero de control y se movía al lote como documento;
  después, se trata como estado de canal y, si el de la raíz existe, se borra.
- **`core/intake_lotes.py:197`** — `for p in sorted(lote_dir.rglob("*"))` con
  `if p.name in config.INTAKE_CONTROL_FILES: continue`. La exclusión muerde **a cualquier
  profundidad**, luego un adjunto llamado así desaparece del manifiesto del lote.

Los otros nueve los confirmé leyendo mi propio código, sin necesidad de reproducirlos: el
`if not load_catalog(...)` de `organizar`, el casado solo-por-hash de `aplicar_clasificacion`, el
`if canon.is_file(): return [canon]` de `_md_paths`, el `<slug>.md` construido en `_link_md`, el
`if not f["Tipo"].strip()` de `_hashes_residuo`, el `prev.get("Fecha") or fecha` de
`_write_worklist`, el `glob("__d*")` con `sorted()` lexicográfico, y el `d['md_path']` de la CLI.

**Integridad del objeto:** el revisor dio los siete `sha256` de los ficheros de producción
idénticos al abrir y al cerrar. No mutó el objeto.

## 3. Adjudicación

**Veredicto del revisor: `NO-SHIP`. Lo acepto entero. De 13 hallazgos no he refutado ninguno.**

### Confirmados e introducidos por este diff (11)

| # | Sev. | Hallazgo | Remediado en |
|---|---|---|---|
| 1 | CRÍTICO | `migrar_layout_intake` borra por basename un documento de contenido distinto | **REVERTIDO** `#149` (`4cd71dd`) |
| 2 | ALTO | La exclusión por basename oculta adjuntos legítimos a cualquier profundidad | **REVERTIDO** `#149` (`4cd71dd`) |
| 3 | ALTO | Un homónimo anidado se mueve y sus referencias forenses quedan rancias | **REVERTIDO** `#149` (`4cd71dd`) |
| 4 | ALTO | `organizar` no incorpora documentos nuevos si ya hay catálogo | `65f543a` |
| 5 | ALTO | Una fila obsoleta de la worklist pisa una clasificación resuelta | `65f543a` |
| 6 | ALTO | La CLI entrega solo el primer segmento de un bundle | `65f543a` |
| 7 | MEDIO | Un MD canónico obsoleto suprime los segmentos actuales | `65f543a` |
| 8 | MEDIO | Los enlaces «ver texto» siguen muertos para bundles partidos | `65f543a` |
| 9 | MEDIO | Un `Tipo` inválido crea un residuo irrecuperable | `65f543a` |
| 10 | MEDIO | Vaciar `Fecha` a propósito no se conserva | `65f543a` |
| 11 | BAJO | El glob no implementa la gramática ni el orden de los segmentos | `65f543a` |

Los tres primeros tienen **una sola causa**: apliqué la exclusión por **basename global** cuando
el contrato es **por ubicación**. Se revierte `#149` entero en vez de parchearlo, porque su forma
correcta toca cinco consumidores y puede borrar prueba: es pieza con presupuesto propio de dos
rondas, no el remate de esta.

### Confirmados pero PREEXISTENTES, fuera del alcance de este diff (2)

| Sev. | Hallazgo | Destino |
|---|---|---|
| ALTO | `streamlit_app.py` compone el `case_id` por su cuenta y reproduce el caso `s/n` idéntico | `MEJORAS #153` |
| ALTO | El override de ruta permite escapar de `CASOS_ROOT` (`..`, ruta absoluta) | `MEJORAS #154`, familia de `#141` |

El primero **responde la pregunta que yo declaré abierta en el mandato** —«¿queda alguna vía que
componga una ruta de caso sin pasar por `componer_case_id`?»— y la respuesta es sí, y es **la
puerta principal**: la que usan Paola y Ana. Mi `#148` arregló el CLI de seis flags. Por eso
`#153` va al backlog **por delante** de lo que ya arreglé, no detrás.

### Lo que el revisor dio por limpio, y por qué lo acepto

`scripts/crm_ficha.py` (probó que `E&amp;V` frente a `E&V` verifica y que `<p>abc</p>` frente a
`<p>ab</p>` sigue fallando: buscó la normalización permisiva y no la encontró) y la vía nueva de
seis campos de `abrir_caso` (probó los nueve caracteres prohibidos en los tres campos). Son las
dos piezas cuyos mutantes yo había escrito en los dos sentidos, y coincide.

### Tres errores míos que valen más que los hallazgos

1. **Escribí el diagnóstico correcto y no lo implementé.** En el propio texto de `MEJORAS #149`
   dejé escrito: «excluir `_manifiesto.yaml` por *basename* excluye cualquier fichero así llamado
   en cualquier sitio, y eso podría sacar del inventario un documento real. Lo correcto es
   excluirlo solo en la raíz de un lote, o sea una línea **más** una comprobación de ruta». Y
   escribí solo la línea. El revisor encontró exactamente lo que yo había identificado y
   abandonado. **Un riesgo escrito y no implementado es peor que no haberlo visto**, porque deja
   constancia de que se vio.
2. **Conté mal el radio de daño**, y con eso el presupuesto de rondas. Está en el §0 de esta acta.
3. **Repetí un defecto que este repo ya había aprendido.** El `prev.get("Fecha") or fecha` es la
   familia del `H-09` de `crm_ficha` —«una clave preparada y vacía significa que no hay dato»—,
   cerrado hace semanas y documentado en `core/crm_ficha.py`. Lo volví a escribir en otro fichero.

### Cobertura y lo que queda SIN VERIFICAR

- Nueve mutantes nuevos en `tests/test_sala_lectura_r1_adversarial.py`, **los nueve rojos antes**
  de remediar. 117 tests de la familia en verde tras la remediación.
- **SIN VERIFICAR por el revisor, y lo declaró:** las dos semillas aleatorias (su entorno no tiene
  `pytest-randomly`) y la suite completa limpia (su sandbox no tiene `.git`, `.venv` ni escritura
  en la copia fuente). Esa cobertura la aporta el autor y se dice así: dos corridas completas,
  una con orden de declaración y otra con `--randomly-seed=31337`, mismo resultado.
- **No hay R2 sobre este diff.** La remediación de los ocho hallazgos de la sala de lectura queda
  cubierta por sus nueve mutantes, **no por un revisor**, y eso es distinto: se declara en vez de
  presentarlo como revisado. El techo de rondas se respeta.
