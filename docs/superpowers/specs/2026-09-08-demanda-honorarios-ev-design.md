---
estado: propuesto
autor: Claude Code
fecha: 2026-09-08
revision: 2
abre: MEJORAS #179, MEJORAS #180, MEJORAS #181
rondas_previstas: 1
motivo_una_ronda: "no decide quien escribe sobre que copia ni puede destruir datos de cliente: lee el expediente y produce un escrito y un informe"
---

# Skill `demanda-honorarios-ev` — preparar y revisar la demanda de reclamación de honorarios

> Gemela **actora** de `contestacion-honorarios-art20-lau`. Cubre las siete
> `TIPOS_CASO_ACTORA` de Engel & Völkers, en dos modos: **preparar** el escrito desde el
> expediente y **revisar** un borrador ya escrito.
>
> **Higiene PII:** este documento referencia el caso de origen solo por `W-02USSI`. Ni el
> nombre del deudor, ni el del letrado contrario, ni la dirección del inmueble.

---

## 1. De dónde sale

De revisar el borrador de petición inicial de W-02USSI (75.020 €, redactado por el abogado
junior en febrero de 2026, autorizado como monitorio, aún sin presentar). Esa lectura produjo
seis defectos reutilizables y, más útil todavía, la comprobación de que **tres de las skills
del despacho ya poseían la mitad de lo que esta iba a construir**. El diseño que sigue es
más pequeño que el primero que se propuso, y a propósito.

La regla que lo gobierna es la de `contestacion-honorarios-art20-lau`, que dice de sí misma
haber nacido de un asunto real y bundlear esa experiencia: **una plantilla maestra sale de un
escrito aprobado por el letrado, no de la imaginación.** De ahí el §11.

## 2. Qué es y qué no es

**Es** la capa de **dominio** de la reclamación de honorarios de intermediación en posición
actora. Se inserta en el flujo genérico de `preparacion-litigio-civil` y corre sola en modo
revisión.

**No es** un flujo paralelo. No monta el expediente, no fija las decisiones cerradas del
despacho, no construye la cronología, no genera el `.docx`, no aplica el estilo, no verifica
las citas y no valora la viabilidad. Todo eso tiene dueño, y el dueño no es esta skill.

> **Rev. 2 (2026-09-09).** Terminada la revisión de la demanda de W-02USSI, el catálogo
> pasa de seis a **ocho** familias (§8, las nuevas 7 y 8) y la cadena de devengo gana el
> §5.1: **las condiciones del contrato privado son parte del eslabón 4**. Ese fue el
> hallazgo de fondo del caso, y la rev. 1 no lo tenía.

**Alcance material:** las siete `TIPOS_CASO_ACTORA` de `core/config.py` — `BAD_DEBT`,
`NEGATIVA_OFERTA`, `NEGATIVA_ARRAS`, `NEGATIVA_ESCRITURA`,
`NEGATIVA_CONTRATO_ARRENDAMIENTO`, `VUELTA`, `INCUMPLIMIENTO_EXCLUSIVA`. La frontera la
dibuja el código, no este documento. Si el `tipo_caso` del expediente está en
`TIPOS_CASO_DEFENSIVA`, la skill para y remite a la hermana que corresponda.

**Alcance procesal:** **verbal** si la cuantía es ≤ 15.000 € (art. 250.2 LEC), **ordinario**
si es > 15.000 € (art. 249.2). El **monitorio no es la vía del despacho** —asume el riesgo de
no localizar al deudor para el requerimiento— y solo se admite **con constancia nombrada de
la autorización**. Decidido por Nikolai el 2026-09-08.

## 3. Coordinación: quién posee qué

Lo esencial del diseño. Ninguna de estas casillas se duplica.

```
preparacion-litigio-civil ......... fase estrategica, cualquier escrito civil
  paso 1  tipo de escrito + posicion + PROCEDIMIENTO
  paso 2  arbol del expediente y maestros (PREPARACION_X.md, HECHOS_X.md)
  paso 3  decisiones cerradas estandar del despacho
  paso 4  reference/demanda.md  ....... generico  <-- aqui entra §5 de esta skill
  paso 5  decisiones del asunto: pretension, cuantia, intereses, prueba, documental
                                                   <-- aqui entra §9.1 (bloque MASC)
  paso 6  cronologia y personas clave
  paso 7  HECHOS_X.md con anclaje 🟢/🟡/🔴 ....... <-- aqui entra §6 y §7
  paso 8  revision deontologica del indice documental
                                                   <-- aqui entra §9.2
  paso 9  transicion
     |
     v
escritos-judiciales ............... el .docx y su forma
  formato de pagina, tipografia, encabezado/pie, inicio del escrito
  reglas tipograficas (nombres, comparecencia, negritas, nomens, sin em dash)
  seccion HECHOS: titulos, lista decimal continua, DOCUMENTO Nº XX
  citas de jurisprudencia a pie con ECLI (OBLIGATORIO)
  FUNDAMENTOS, SUPLICO, firmas, indice documental
  «Correcciones doctrinales que el escrito evita» (4)
  «Checklist antes de entregar» (27 items)
     |
     v
pase-de-estilo .................... capa 2, claridad y sin marcas de IA

verificacion-anclada-fuente ....... transversal y OBLIGATORIA en los dos modos
  Regla 5   jerarquia de fuentes: BOE.es y texto consolidado en la cima
  Regla 8   prohibicion de citas inventadas — enumera «preceptos legales»
  Regla 11  normas y proposiciones juridicas
cendoj-descarga ................... los ROJ/ECLI de cada resolucion citada
engel-volkers ..................... contexto de cliente, terminologia propietario/buscador
```

**Aguas arriba:** `triaje-viabilidad`, `viabilidad-prerelleno`.
**Aguas abajo:** `preparacion-audiencia-previa` (solo en ordinario).

### 3.1 Dos correcciones que la lectura impuso al diseño inicial

- **El defecto «nomenclatura de órgano caducada» ya está cubierto.** El checklist de
  `escritos-judiciales` lo dice literalmente: «Encabezamiento nombra la Sección del Tribunal
  de Instancia (§9), no "JUZGADO DE PRIMERA INSTANCIA" (Sección Civil por defecto en
  honorarios)». El borrador de W-02USSI es de febrero y esa regla es posterior: **es un
  escrito anterior a la regla, no un hueco de cobertura.** Fuera del catálogo.
- **El defecto «cita normativa que no dice lo que se le atribuye» pertenece a
  `verificacion-anclada-fuente`** (Reglas 8 y 11). Fuera del catálogo. Quedan **seis**.

## 4. Modos, y cómo se detectan

La Fase 0 la ejecuta `preparacion-litigio-civil` (pasos 1-2). Esta skill solo añade tres
resoluciones, **todas leídas, ninguna inferida**:

| Qué | De dónde | Si no resuelve |
|---|---|---|
| `tipo_caso` | `00_Input/_caso.md` → `meta.tipo_caso` | para: sin `tipo_caso` actora no es esta skill |
| Modo | ¿hay borrador? `05_Procedimiento/` + el `demanda_doc_id` que etiqueta `sync_sudespacho intake-judicial` | sin borrador → preparar; con borrador → revisar |
| Cauce | `tipo_procedimiento` + `cuantia` del expediente judicial del CRM, con la regla del §2 | si el CRM dice monitorio y **no hay constancia de autorización**, para y pregunta |

**Nunca del nombre de la carpeta.** El nombre del caso es una etiqueta legible, no una fuente
de identidad — y `core/casos/case_locator.py` demuestra por qué: su `buscar()` resuelve solo
por nombre de carpeta y eso ya produjo una carpeta sombra en el Drive del cliente el
2026-09-08 (`MEJORAS #176`).

## 5. El fondo genérico: la cadena de devengo

`references/cadena-de-devengo.md`. Las siete variantes son **un mismo argumento con un
eslabón distinto roto**:

| # | Eslabón | Qué acredita |
|---|---|---|
| 1 | **Encargo** | contrato de mediación válido, firmado por quien podía obligar al titular |
| 2 | **Estipulación de devengo** | la cláusula concreta que fija cuándo nace el derecho |
| 3 | **Gestión eficaz y determinante** | que el tercero conoció la oportunidad por la agencia |
| 4 | **Hecho de devengo** | el eslabón que se rompió, distinto por `tipo_caso` |
| 5 | **Importe y exigibilidad** | base + IVA, factura, vencimiento, requerimiento |

El núcleo doctrinal —corretaje atípico, honorarios devengados a la perfección del contrato
**salvo pacto**— es lo que convierte el eslabón 2 en la bisagra: **el pacto es la
estipulación**. De ahí la regla de dominio que sale de leer el borrador:

### 5.1 Las condiciones del contrato privado son parte del eslabón 4, no una nota al margen

**Aprendido al terminar la revisión de W-02USSI (2026-09-09).** El campo de batalla real no
fue ninguno de los defectos formales: fue que el contrato privado de arras llevaba una
**condición suspensiva** —«el mismo no surtirá efectos hasta entonces»— con dos requisitos, y
el escrito **no la mencionaba en ningún hecho**, mientras la contraria la había articulado por
escrito desde el primer mes. Todo el argumento del devengo se apoya en que la compraventa se
perfeccionó; una condición suspensiva incumplida ataca justo eso.

Por tanto el eslabón 4 obliga a tres cosas, en este orden:

1. **Inventariar TODAS las condiciones del contrato privado** —suspensivas, resolutorias, de
   financiación del comprador, plazos de acreditación— leyendo la comparecencia y los pactos,
   no el resumen. Y sus anexos, que pueden modificarlas (y contradecirse entre sí).
2. **Decir a quién obliga cada una**, porque de ahí sale la imputabilidad. Que la agencia
   obtenga por su cuenta lo que la cláusula manda acreditar **al vendedor** no cumple la
   condición tal como está redactada.
3. **Armar el art. 1119 CC** («se tendrá por cumplida la condición cuando el obligado
   impidiese voluntariamente su cumplimiento») **contra la condición concreta**, y no citarlo
   suelto en los fundamentos. Con el corolario que lo sostiene: la doctrina del devengo a la
   perfección opera **salvo pacto**, y el pacto —la estipulación de devengo del eslabón 2— es
   lo que desplaza al devengo por defecto.

**La comprobación del modo revisión, en una línea:** si el escrito afirma que el contrato se
perfeccionó y el contrato privado tiene una condición que el escrito no nombra, es un CRÍTICO,
no una mejora de redacción.

> **La estipulación de devengo se transcribe como texto, nunca solo pegada como imagen, y la
> paráfrasis del escrito tiene que casar rama por rama con la cláusula.**

En W-02USSI la cláusula viaja como imagen PNG dentro del `.rtf` (por eso el fichero pesa
1,7 MB) y la paráfrasis del escrito fusiona sus dos ramas, que tienen consecuencias
distintas: una da derecho a retener lo ya cobrado, la otra a la totalidad de los honorarios.

El fichero desarrolla, por cada `tipo_caso`, **qué módulo de Hecho debe existir** y con qué
anclaje. No sustituye al paso 7 de `preparacion-litigio-civil`: lo alimenta. Un eslabón sin
documento cerrado es un Hecho 🟡 con su medio de prueba anotado, nunca un 🟢 optimista.

Semilla de `references/jurisprudencia/`: los siete ROJ/ECLI que cita el borrador de W-02USSI,
**declarados pendientes de verificación** hasta que `cendoj-descarga` los baje.

## 6. Dónde está cada cosa: por censo, no por ruta

`references/donde-esta-cada-cosa.md`. Es la pieza que hace que «preparar más rápido» sea
cierto en vez de retórico, y la que está medida.

**Por qué no por ruta.** `core/config.py::CARPETA_ID_TO_PATH` tiene **cuatro** entradas
(`1`→`General`, `307`→`Civil/1ª Instancia/Declarativo/Demanda`, `308`→`.../Oposicion`,
`380`→`Civil/Preliminares/Demanda`). El `id_carpeta` de la carpeta DEMANDA del expediente
judicial de W-02USSI es **`304`**, y no está mapeado. Medido el 2026-09-08: los **23**
documentos del judicial cayeron en `05_CRM/99_Sin categoria/622/` y los **9** del
extrajudicial en `05_CRM/99_Otros/`. **Ninguno** en el árbol `CRM_TREE`. Una skill que
resolviera «tráeme el encargo» por ruta canónica diría «no lo encuentro» sobre un expediente
que lo tiene dentro.

**Orden de preferencia, con fallback declarado:**

1. **`00_Input/_caso.md` → `sudespacho_expedientes[].doc_ids`, y sobre todo el ROL.**
   `sync_sudespacho intake-judicial` ya etiqueta `demanda_doc_id`. La demanda se resuelve por
   rol, lo que la hace inmune al mapeo roto.
2. **`01_Procesado/02_Sala de máquina/_cobertura.json`** — censo legible por máquina de todo
   el corpus, con `slug`, `rel_path`, `sha256`, `doc_id`, `role`, `tipo`, `parent_slug`,
   `estado` y `chars`.
3. **`01_Procesado/Sala lectura/indice_documental.yaml`** (+ `INDICE.md`, `CRONOLOGIA.md`) —
   el mejor de los tres cuando `organizar-sala-lectura` se ha corrido.
4. **Si no hay ninguno: no se adivinan rutas.** La skill dice qué falta correr
   (`scripts.sala_maquina apply`, `organizar-sala-lectura`) y sigue con lo que haya,
   declarando qué eslabones quedan sin resolver.

### 6.1 El anclaje deja de ser un juicio y pasa a ser comprobable

Esta es la razón principal para leer el censo, por encima de la velocidad. `_cobertura.json`
trae el **estado de extracción**, así que el 🟢/🟡/🔴 del paso 7 se puede **verificar**:

> Un Hecho **🟢 exige** que su documento de soporte tenga `estado: ok` en el censo. Un
> documento `empty`, `low` o `sin_soporte` **no puede sostener un 🟢**: baja a 🟡 con el
> motivo del censo anotado, o se busca otra copia del mismo documento por `sha256`.

La regla es **mecánica y comprobable por script**: se lee `estado`, no se estima calidad. Que
el texto extraído sostenga *lo que el Hecho le atribuye* es juicio del letrado y queda fuera
del automatismo; lo que la skill garantiza es que **nadie ancle en 🟢 un documento cuyo texto
el expediente no tiene**.

En W-02USSI eso se caza solo, sin criterio humano: la carta de desistimiento del gestor
documental tiene **3 caracteres** de texto extraído (hay que ir a la copia de la carpeta de
reclamación de E&V, con 3.335), y el encargo de venta sale **`low` con la página 2 ciega**
siendo el documento que contiene la estipulación octava. Los dos son eslabones nucleares.

**Cautela obligatoria en el uso del censo:** `estado: empty` mezcla hoy «no tiene texto» y
«sí lo tiene y no se pudo leer» (`MEJORAS #178`). Mientras eso no se separe, la skill lee
también el campo `nota`: un espejo de 0 bytes cuya nota empieza por «fallo al procesar» es un
**fallo**, no un documento vacío, y se re-procesa antes de decidir nada.

## 7. Las puertas de dominio

`references/puertas-de-dominio.md`. **Solo lo que es de esta reclamación**; las puertas
genéricas del civil viven donde les toca (§9.1). Cada puerta: qué es, su fuente, cómo falla y
qué prueba la cierra.

| Puerta | Fuente | Cómo falla |
|---|---|---|
| Título documental suficiente | art. 812.1.2ª LEC (solo si el cauce es monitorio) | apoyar la deuda en una **proforma** en lugar de una factura |
| Competencia territorial | art. 813 LEC | tomar el domicilio del deudor de la ficha del CRM en vez de **la nota mercantil**; el 813 es competencia exclusiva, excluye sumisión y ordena auto de terminación si el deudor está en otro partido judicial |
| Localizabilidad del deudor | art. 815 LEC | elegir monitorio cuando algún requerimiento previo volvió **fallido**: es el riesgo que motiva la política del §2 |
| IVA sobre honorarios | jurisprudencia de AP | reclamar la base sin el IVA, o reclamarlo sin factura emitida |
| Intereses | Ley 3/2004 | contarlos desde la fecha de una **proforma** |
| Prescripción | art. 1964.2 CC | no fecharla desde el devengo del eslabón 4 |
| Autorización del cauce | política del despacho, §2 | dar por bueno un monitorio sin constancia nombrada |

## 8. El catálogo de defectos y el modo revisión

`references/catalogo-de-defectos.md`. **Ocho familias**, sembradas con defectos **medidos en
un escrito real**. Cada una con síntoma, detección, fuente y consecuencia.

| # | Familia | Detección |
|---|---|---|
| 1 | Puerta de cauce sin comprobar | cruzar el §7 contra los documentos que el propio escrito aporta |
| 2 | Documento invocado que no está en el ramo | mecánica: `scripts/cruzar_documental.py` |
| 3 | Documento del ramo que el escrito no cita | la misma, en dirección inversa |
| 4 | Título documental débil | proforma donde el cauce exige factura |
| 5 | Contradicción interna entre párrafos | lectura dirigida de los pares hecho/fundamento que se refieren al mismo evento |
| 6 | Paráfrasis que no casa con la cláusula transcrita | comparar rama por rama contra el texto de la estipulación |
| 7 | **Cita de apoyo cuya *ratio* contiene doctrina adversa** | por cada resolución citada, dos preguntas: ¿su supuesto de hecho es el nuestro?, ¿su *ratio* le da a la contraria algo que usar? |
| 8 | **Parte contractual omitida en la identificación** | cotejar la comparecencia del contrato privado contra el hecho que identifica a las partes |

**Las familias 7 y 8 salieron de terminar la revisión de W-02USSI el 2026-09-09**, después de
escribir la rev. 1 de este spec. Las dos merecen su sitio por lo que costó descubrirlas:

- **La 7.** El escrito cita una SAP como apoyo del IVA, y esa misma sentencia transcribe en su
  *ratio* la doctrina del TS de que el corretaje «se halla sometido a la condición suspensiva
  de la celebración del contrato pretendido» y que no se devenga si surge «cualquier diferencia
  sustancial obstativa de la celebración de la venta, porque en tal caso no llegó al estado de
  perfección». Es decir: **favorable para lo que se la usa, adversa para el núcleo del caso**,
  y aportada en el propio ramo. Una verificación que solo comprueba identidad —ROJ, ECLI,
  fecha, ponente— **no la detecta**: hay que leer el supuesto de hecho y la *ratio*. El
  `cendoj-descarga` ya lo advierte («un resultado parece on-point y no lo es»); el catálogo lo
  convierte en comprobación obligatoria del modo revisión.
- **La 8.** El escrito identifica a la parte compradora como dos personas físicas y **omite la
  sociedad** que figura en la comparecencia del contrato privado. En un escrito cuyo eje es
  que la compraventa se perfeccionó entre partes determinadas, identificar mal a una de ellas
  es un flanco gratuito.

**Y un *gotcha* de verificación, medido:** CENDOJ publica algunos ECLI de Audiencia
**con un espacio** (`ECLI:ES:AP B:2002:12928`). «Normalizarlo» a `ES:APB` hace que la búsqueda
por ECLI **no devuelva nada**, y eso se lee como «la cita no existe». Buscar por **ROJ** ante
cualquier resultado vacío antes de concluir ausencia. Va a `cendoj-descarga`, no aquí
(`MEJORAS #181`).

**La meta-regla, prestada de `CLAUDE.md`:** ante cada hallazgo, **«¿de qué frontera es esto un
ejemplo?»** antes de remediarlo. Remediar el caso que el informe describe, y no la propiedad
de la que es ejemplo, es cómo se gastan cuatro rondas en cerrar una sola cosa.

**Y la línea que hace honesto el informe:** una puerta que no se pudo comprobar se declara
**sin verificar**, nunca «cumplida». Es el corolario del revisor que no corre.

## 9. Aportaciones a skills existentes

Parte del entregable, no efectos colaterales.

### 9.1 `preparacion-litigio-civil` paso 5 — el bloque MASC

El paso 5 recorre pretensión, cuantía, intereses, prueba, testifical y documental, y **no
menciona el MASC**. La skill es v1.0 y la LO 1/2025 impone la actividad negociadora previa
como **requisito de procedibilidad de todo declarativo civil**. Es genérico: sirve a todos los
asuntos del despacho, no solo a los de E&V. Se añade como bloque de decisiones con estas
puertas, todas verificadas contra el texto consolidado (BOE-A-2025-76) el 2026-09-08:

- **Exigibilidad (art. 5.2).** Alcanza «todos los procesos declarativos del libro II y los
  procesos especiales del **libro IV**» de la LEC. La lista de excepciones incluye el **juicio
  cambiario** y **no** el monitorio; el art. 5.3 exceptúa el **monitorio europeo**, no el
  español.
- **La ventana del art. 7.3, y de qué rama se cuenta.** Un año, «respectivamente»: desde la
  **recepción de la solicitud** si no hubo respuesta, o desde la **terminación del proceso
  negociador** si la hubo. **Alegar la rama falsa acorta el plazo**, y es un error que se
  comete solo: en W-02USSI el borrador invoca la rama de «sin respuesta» mientras su propio
  hecho siguiente narra el burofax del letrado contrario y la negociación.
- **La terminación es del art. 10.4**, no del 7.3: cuatro supuestos (a-d).
- **El 10.4.d como palanca.** Un escrito a la contraparte dando por terminadas las
  negociaciones fija fecha nueva y reinicia el año. Barato y disponible.
- **Acreditación (art. 10.2)** y el documento que exige el **art. 264.4ª LEC**.

### 9.2 `preparacion-litigio-civil` paso 8 — el criterio deontológico, escrito

El paso 8 ya ordena revisar el índice documental para no aportar correspondencia entre
letrados sin consentimiento (art. 21 EGAE, art. 5 CDCGAE). La puerta existe y **en W-02USSI
se ejerció**: la actuación del CRM registra que se aportó la respuesta del letrado contrario
recortando las páginas del intercambio de correos que llevaban aviso de confidencialidad, y
que el burofax se interpretó fuera de ese aviso. Lo que no está escrito en ninguna parte es
**el criterio** con el que se resolvió. Se añade como nota, con la distinción
burofax / intercambio de correos con aviso.

## 10. Entregables

**Modo preparar.** Rellena la capa de dominio de los maestros de
`preparacion-litigio-civil` —los módulos de Hecho de la cadena de devengo con su anclaje
verificado contra el censo, y el índice documental resuelto por rol— y delega la generación
en `escritos-judiciales` y el pulido en `pase-de-estilo`.

**Modo revisar.** Produce un **informe de revisión** con dos secciones separadas y no
fusionables:

1. **Hallazgos**, por gravedad, cada uno con su fuente pegada.
2. **Puertas**: las comprobadas, y **las que no se pudieron comprobar**, con el motivo.

**No reescribe el borrador en silencio.** Propone el diff y lo deja a decisión del letrado.
El informe se escribe **fuera del repo** (lleva PII de terceros) y se entrega al letrado.

## 11. Estructura de la skill

```
.claude/skills/demanda-honorarios-ev/
├── SKILL.md
├── CHANGELOG.md
├── references/
│   ├── cadena-de-devengo.md        §5 — los 5 eslabones x 7 tipos_caso
│   ├── donde-esta-cada-cosa.md     §6 — censo, no ruta, con el fallback
│   ├── puertas-de-dominio.md       §7
│   ├── catalogo-de-defectos.md     §8 — las 6 familias
│   └── jurisprudencia/
│       └── INDICE.md               semilla: 7 ROJ/ECLI pendientes de verificar
├── scripts/
│   ├── cruzar_documental.py        defectos 2 y 3 + anclaje verificable (§6.1)
│   └── registrar_uso.py            patron de las hermanas
├── assets/
│   ├── checklist-previo.md
│   └── checklist-entrega.md
├── evals/
│   └── evals.json
└── logs/
    └── uso.jsonl
```

**Sin `assets/plantilla-maestra.txt` en la v1, y declarado como hueco en el `SKILL.md`.**
Hay un escrito real que auditar y ninguno **aprobado por el letrado** que imitar. La plantilla
entra cuando se apruebe el primero. Lo contrario sería imaginación con formato.

**Corolario honesto que el `SKILL.md` debe decir en voz alta:** la v1 **revisa mejor de lo que
prepara**.

## 12. Pruebas

- **`evals/evals.json`**, caso 1: W-02USSI en modo revisión. ¿Salen las seis familias?
- **Golden de `cruzar_documental.py`** sobre un escrito y un censo **sintéticos** (nunca el
  árbol de producción, regla de `CLAUDE.md`): documento citado que no está, documento presente
  que no se cita, y un Hecho 🟢 apoyado en un documento con 3 caracteres.
- **La advertencia escrita en el propio `evals.json`:** un eval sembrado del caso que lo parió
  es una **regresión**, no una generalización. Lo que prueba la skill es el segundo caso.

## 13. Decisiones cerradas

| # | Decisión | Quién y cuándo |
|---|---|---|
| D1 | Una skill con dos entradas, no dos skills | Nikolai, 2026-09-08 |
| D2 | Cauce = verbal o ordinario según cuantía; el monitorio no es la vía del despacho por el riesgo de no localizar al deudor | Nikolai, 2026-09-08 |
| D3 | El monitorio se admite con constancia nombrada de autorización; no es línea roja | Nikolai, 2026-09-08 |
| D4 | v1 genérica en el fondo, con capa de puertas por cauce; especialización después | Nikolai, 2026-09-08 |
| D5 | Alcance material = `TIPOS_CASO_ACTORA`, tomado del código | Claude, del código |
| D6 | Resolución de documentos por censo y rol, nunca por ruta canónica | Claude, medido en W-02USSI |
| D7 | Sin plantilla maestra en v1 | Claude, por el precedente de la skill hermana |
| D8 | El entregable incluye dos ediciones a `preparacion-litigio-civil` | Nikolai, 2026-09-08 |

## 14. Backlog que abre

- **`MEJORAS #179`** — `.claude/skills/verificacion-anclada-fuente/SKILL.md` tiene **359
  bytes NUL** de relleno tras la última línea, commiteados (blob `64f730f`). El texto
  decodifica bien como UTF-8, pero `file` lo llama `data` y **`grep` lo trata como binario**:
  la skill es invisible a cualquier búsqueda por contenido sobre `.claude/skills/`. Coste
  real: en esta misma sesión el comando que leyó las otras veinte skills no pudo leer esta.
  Falta además el guard: **ninguna verja comprueba hoy que un `SKILL.md` sea legible como
  texto**.
- **`MEJORAS #180`** — `id_carpeta 304` (carpeta DEMANDA del expediente judicial) no está en
  `CARPETA_ID_TO_PATH`, y por eso los 23 documentos del judicial de W-02USSI fueron a
  `99_Sin categoria/622`. **No se añade unilateralmente**: `config.py` fija la regla de doble
  verificación porque la etiqueta-hoja `DEMANDA` es ambigua entre `Declarativo/Demanda` (ya
  ocupada por `307`) y `Monitorio/Demanda`. Pendiente de que Nikolai confirme la rama en la
  UI del CRM.

Y una nota, no una entrada: `CONVENCIONES_DESPACHO §80` y `§187` y el índice del
`MANUAL_DESPACHO` presentan el monitorio como **la** vía del Bad Debt —con su checklist
D01-D17 y sus cuatro hitos de actuación del CRM— cuando por la D2 es la excepción. Se corrige
cuando haya disparador; hoy no lo hay, porque el caso vivo es precisamente una excepción
autorizada.

## 15. Revisión adversarial

**Una ronda, sobre el diff.** Por el radio de daño: la pieza no decide quién puede escribir
sobre qué copia de un expediente ni puede destruir ni corromper datos de cliente — lee el
expediente y produce un escrito y un informe. Criterio de `CLAUDE.md`, tabla de rondas.
