---
name: oposicion-alegacion-nulidad
description: >-
  Preparación de la contestación a la alegación de nulidad, anulabilidad, no
  incorporación o abusividad de un contrato formulada de contrario, evacuando el
  traslado del art. 408.2 LEC. Úsala SIEMPRE que, representando a la actora o
  reconvenida, haya que impugnar que el demandado ataque en su contestación la
  eficacia del contrato en que se funda la demanda. Dispara con frases como
  "contestar a la nulidad", "oposición a la alegación de nulidad", "traslado del
  408.2", "alegación de nulidad", "art. 408 LEC" o "nos alegan que el contrato es
  nulo". Aporta la estructura de ordinales, la clasificación de motivos por vías
  de ineficacia y las reglas de decisión; orquesta cendoj-descarga,
  verificacion-anclada-fuente y escritos-judiciales. Incluye módulo para
  mediación inmobiliaria / honorarios (legibilidad TRLGDCU, objeto principal,
  representación aparente). NO redacta la demanda o contestación inicial
  (escritos-judiciales) ni prepara la audiencia previa (preparacion-audiencia-previa).
metadata:
  type: workflow
  jurisdiction: ES
  area: civil
  version: "1.5.2"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# Oposición a la alegación de nulidad (art. 408.2 LEC)

## Qué resuelve esta skill

Cuando representamos a la **actora** y el demandado, en su contestación, alega
que el contrato en que se funda la demanda es nulo, anulable, no incorporado o
abusivo, el LAJ suele conferir a la actora un **traslado del art. 408.2 LEC**
para impugnar esa alegación. El cauce del 408.2 está pensado para la **nulidad
absoluta** opuesta por vía de **excepción** (no es reconvención: por eso hay
traslado y no contestación a reconvención); la **anulabilidad** por vicio del
consentimiento no cabe por excepción y exige acción o reconvención (ver
`references/reglas-decision.md`, Reglas 1 y 1 bis). Esta skill prepara ese escrito de contestación a la
alegación de nulidad: fija la estrategia, construye el índice por ordinales,
dirige la investigación jurisprudencial y produce el `.docx` final con el formato
del despacho.

No reimplementa lo que ya hacen otras skills del despacho: las **orquesta**. En
cada fase llama a la skill adecuada y le pasa el contexto. Su valor propio es lo
específico del trámite 408.2: la **delimitación del cauce**, la **clasificación
de los motivos por vías de ineficacia** y las **reglas de decisión** que evitan
los errores típicos.

Tiene **dos niveles**:

- **Núcleo general (408.2)** — sirve para cualquier alegación de nulidad de un
  contrato civil. Es lo que sigue en este documento.
- **Módulo de mediación inmobiliaria** — se activa cuando el contrato litigioso
  es un encargo de intermediación / nota de honorarios (caso típico de una
  agencia inmobiliaria / plataforma de reclamación de honorarios). Vive en
  `references/modulo-mediacion-inmobiliaria.md` y se carga solo cuando aplica.

## Encadenamiento con otras skills

Esta skill es la orquestadora. Apóyate en:

- **`verificacion-anclada-fuente`** — actívala de forma **transversal** desde el
  primer minuto. Ninguna cita, cifra, fecha o afirmación jurídica entra en el
  escrito "de memoria"; todo se ancla a fuente verificable (BOE, CENDOJ, TC,
  TJUE/EUR-Lex; subsidiariamente vLex, Lefebvre). Lo no verificable va a una
  lista "SIN VERIFICAR" o se retira.
  - **Jerarquía de fuentes (regla dura):** diccionarios (RAE-DPEJ), blogs de
    despacho y comentarios doctrinales sirven de **pista** para localizar, pero
    **no se citan en el escrito**. La cita procesal va siempre a **fuente
    primaria**: BOE (preceptos), CENDOJ con **ECLI/ROJ cotejado** (jurisprudencia
    española) y EUR-Lex/CURIA por ECLI (TJUE). Antes de incorporar cualquier
    resolución hallada en base privada, **descárgala y cotéjala en CENDOJ**; si no
    aparece, se retira (caso real: la "SAP La Rioja 334/2018" no existe como
    sentencia civil en CENDOJ).
  - **Biblioteca local** (`references/jurisprudencia/`): `indice_jurisprudencia.json`
    es la **fuente única de verdad** (metadatos, ECLI, `aplica`, rutas). Para
    **argumentar/citar**, lee los `.md` de `sentencias_md/`; para **aportar** en
    sala, usa el PDF de `sentencias_oficiales/` (CENDOJ) o el enlace oficial (TJUE).
    Nunca entrecomilles como literal un `.md` marcado `ficha`; abre la fuente
    oficial. Consulta `aplica` antes de citar (p. ej. STS 123/2020 = `no`).
- **`cendoj-descarga`** (o el agente `cendoj-bot`) — para localizar y descargar
  los PDF oficiales del CGPJ y cosechar los enlaces `openDocument` que irán en
  las notas al pie. El *hash* del CENDOJ no es deducible: hay que obtenerlo
  resolución por resolución. Las STJUE se construyen a mano desde EUR-Lex por
  ECLI.
- **`escritos-judiciales`** — **léela antes de generar el `.docx`** para aplicar
  el formato del despacho (Sala 1.ª) y producir el escrito firmable. Esta skill
  le entrega el contenido por ordinales ya verificado.
- **`preparacion-litigio-civil`** — si el expediente aún no está montado o no
  existe el documento maestro de hechos, pásala primero.

## Flujo de trabajo

Trabaja por fases y **confirma cada hito con el letrado por chat antes de
avanzar**. El letrado conoce el caso; tú aportas estructura, rigor y verificación.

### Fase 1 — Lectura y delimitación del trámite

1. Lee **toda** la documentación, no solo la de contraria:
   - La **demanda propia** y **todos los documentos aportados con ella** (doc. nº
     1, 2, 3…: contrato, anexos, correos, justificantes). Son la **base
     probatoria de la oposición**: la nulidad se rebate sobre todo con los hechos
     y documentos propios (p. ej. un anexo negociado prueba comprensión
     económica; el propio contrato acredita firma y contenido). No basta con
     reaccionar al escrito de contraria; hay que explotar lo propio.
   - El **escrito de contestación** que contiene la alegación de nulidad y los
     **documentos aportados de contrario**.
   - El **contrato y sus anexos** litigiosos y cualquier **peritaje análogo**
     disponible.
   Construye, si no existe, un inventario de la documental propia (doc. nº →
   contenido → qué hecho/argumento sostiene) para tenerla mapeada al redactar.
2. Identifica con precisión el trámite: ¿qué decreto concede el traslado y con
   qué fecha? ¿Qué plazo corre? El art. 408.2 remite al **plazo de contestación a
   la reconvención** (20 días en juicio ordinario), no a un plazo de 10 días. Esto
   encabeza el escrito.
3. Confirma a quién representamos (normalmente la actora) y la posición.

### Fase 2 — Extracción y clasificación de los motivos

Esta fase es la columna vertebral del escrito. Hazla con cuidado.

1. **Extrae todos los motivos de oposición** del escrito de contraria,
   **citados literalmente** (no parafraseados) y numerados M1…Mn. Vuélcalos por
   chat para visto bueno antes de seguir.
2. **Separa dos planos** (frontera decisiva):
   - **Eficacia del negocio** → es lo propio del 408.2 (nulidad / anulabilidad /
     no incorporación / abusividad).
   - **Fondo** (p. ej. inexigibilidad de la obligación, devengo, cuantía) → NO
     entra en el trámite de nulidad. Recolócalos: se contestan, en su caso, como
     cuestión de fondo, no aquí. Colarlos contamina el debate.
3. **Re-taxonomiza por VÍA DE INEFICACIA**, no por como los amontona el
   adversario. Cuatro vías, con presupuesto, efecto y régimen distintos (detalle y
   citas verificadas en `references/reglas-decision.md`):
   - **Vía A — nulidad absoluta / de pleno derecho**: falta de elemento esencial
     (art. 1261 CC), incluida la **simulación absoluta** (art. 1276 CC) y la
     **imposibilidad originaria del objeto**; causa u objeto ilícitos (arts.
     1271-1275 CC); contravención de norma imperativa (art. 6.3 CC); y **defecto de
     forma *ad solemnitatem*** cuando la ley la exija. → *nulidad radical*,
     imprescriptible (la acción **declarativa**), **apreciable de oficio**,
     oponible por **acción o excepción**. Es la modalidad a la que se refiere
     **nominalmente** el cauce del art. 408.2 LEC (el precepto no crea categoría
     sustantiva: solo abre el trámite). **Matiz del art. 6.3 CC** (nulidad como
     *ultima ratio*): no toda infracción de norma imperativa acarrea nulidad —
     opera "salvo que se establezca un efecto distinto" (STS 558/2019). La
     *inexistencia* se subsume aquí (no es vía procesal separada).
   - **Vía B — vicio del consentimiento** (error, dolo, violencia, intimidación;
     arts. 1265-1270 CC) → *anulabilidad* (arts. 1300-1301 CC). Caducidad 4 años
     (*dies a quo*: Regla 1 quater), **no** apreciable de oficio, exige **acción o
     reconvención** (Reglas 1 y 1 ter). El **error obstativo** deriva a la Vía A
     (frontera porosa, **uso estratégico**: ver Regla 1). La anulabilidad es
     **sanable** por confirmación (arts. 1309-1313 CC).
   - **Vía C — control de incorporación** (arts. 5 y 7 LCGC —cualquier adherente—;
     art. 80.1 TRLGDCU —solo consumidor—) → la cláusula se tiene por **no puesta**
     (no "nula"); el contrato subsiste sin ella (art. 10 LCGC). Apreciable de
     oficio; carga de la incorporación en el predisponente (Regla 5).
   - **Vía D — control de contenido** (cláusula no negociada con consumidor):
     primero **transparencia material** (arts. 80.1 y 82.1 TRLGDCU; arts. 4.2 y 5
     Dir. 93/13) —su falta **abre** el control, no equivale a abusividad—; después
     **abusividad** (desequilibrio importante contrario a la buena fe, arts. 82-83
     TRLGDCU) → **no vinculación** de la cláusula (art. 83), con **subsistencia sin
     integración** (STJUE C-618/10 y C-488/11; *excepción* Kásler C-26/13).
     Apreciable de oficio (Regla 1 bis).
4. Identifica solapamientos y el **"mejor flanco"**: el defecto transversal del
   escrito de contraria que permite ganar el trámite de raíz (típicamente, la
   falta de claridad/precisión de la propia alegación, art. 416.1.5.ª LEC).
   **Cautela:** el flanco formal cierra la **anulabilidad** (rogada), pero la
   **abusividad** y la **no incorporación** son apreciables **de oficio** (Regla
   1 bis): ahí la respuesta de fondo es indispensable, no basta el defecto
   procesal de contraria.

Lee `references/reglas-decision.md` para el detalle de cada test y las reglas que
evitan los errores típicos (sobre todo: recalificar la "nulidad de pleno
derecho" como anulabilidad; *ratione temporis* en normas de consumo; carga de la
prueba; objeto principal del art. 4.2 Dir. 93/13).

### Fase 3 — Índice por ordinales y esqueleto puente

1. Construye el índice primero jerárquico (I, II…) y conviértelo a ordinales
   (PRIMERO.- SEGUNDO.- …) con subapartados (1.1, 1.2). **El número de ordinales
   lo determinan los motivos que efectivamente alegue la contraria**, no una
   plantilla fija: solo se contesta lo que se ataca. `references/estructura-escrito.md`
   ofrece un **repertorio** de los apartados que suelen aparecer; selecciona,
   ordena y fusiona los que el caso pida y descarta el resto. Un escrito puede
   tener tres ordinales o nueve. Lo único razonablemente estable es abrir con la
   cuestión previa (si hay defecto de cauce o de claridad) y cerrar con costas.
2. Aprueba el índice con el letrado.
3. Genera un **`.docx` "puente" (esqueleto)** con la estructura aprobada y
   placeholders `[ … ]` bajo cada subapartado, ya en formato Sala 1.ª, para que
   el letrado lo siga en Word en paralelo. (Aquí ya conviene haber leído
   `escritos-judiciales` para el formato.)

### Fase 4 — Investigación jurisprudencial

1. Lanza la búsqueda en **subagentes/hilos paralelos**, uno por línea
   argumental, con prompt que fije la **tesis a sostener** y la **disciplina de
   verificación**. Busca doctrina general del TS + casos *squarely on point*
   (preferentemente Audiencias Provinciales para el detalle).
2. Cada subagente devuelve dossier con **ROJ/ECLI + fragmento literal del FJ +
   encaje**. El agente principal **re-verifica** (abre el PDF, coteja ROJ/ECLI y
   la cita literal). No te fíes de citas devueltas sin re-verificar.
3. Descarga los PDF oficiales con `cendoj-descarga` y cosecha los enlaces
   `openDocument`.

### Fase 5 — Redacción ordinal por ordinal

1. Redacta **un ordinal por turno**, volcando en el esqueleto y proponiéndolo por
   chat antes de fijarlo.
2. Inserta las citas de documentos directamente en el cuerpo cuando el formato lo
   permita (inmediatez probatoria).
3. Explota las **contradicciones internas** del escrito de contraria y los
   **hechos propios infrautilizados** (un anexo negociado puede a la vez probar
   comprensión económica, excluir la cláusula como "no negociada" y desmontar el
   dolo).

### Fase 6 — Verificación, revisión y cierre

1. **Verifica todas las citas** (ECLI/ROJ/fecha/asunto cotejados en el PDF
   oficial). Las **no localizables se retiran**, dejando el apartado anclado solo
   en lo sólido (texto del precepto del BOE).
2. **Revisión por subagente** del `.docx` completo: numeración, remisiones
   cruzadas, exactitud de preceptos, consistencia de datos e importes, y SUPLICO.
3. **Notas al pie** con cita íntegra (nº, fecha, ROJ/ECLI) + enlace de descarga
   clicable (CENDOJ `openDocument` / EUR-Lex). python-docx no soporta notas al
   pie de serie: hay que inyectar la parte XML (`footnotes.xml` + relación +
   content-type); prueba el mecanismo en aislado antes de tocar el documento
   completo. (Lo gestiona `escritos-judiciales`.)
4. **Acabado de formato** y render con LibreOffice para comprobar a la vista
   (las listas de Word descuadran sangrías idénticas en el XML → fija sangría
   explícita por párrafo).
5. Recorre el **checklist de cierre** (`assets/checklist-cierre.md`) antes de dar
   el escrito por listo para firma.
6. **Registra la ejecución** (Fase 1 de `EVOLUCION.md`): ejecuta el helper
   canónico `registrar_uso.py` con la referencia del asunto y las métricas del
   escrito (motivos por las cuatro vías, ordinales, módulo de mediación). Las vías
   van **dentro de `metricas`** (esquema unificado del despacho):

   ```bash
   python scripts/registrar_uso.py oposicion-alegacion-nulidad <REF> oposicion_408 \
       --archivos Oposicion_nulidad_<REF>.docx \
       --metricas '{"via_a": 1, "via_b": 2, "via_c": 0, "via_d": 1, "fondo": 1, "n_ordinales": 6, "ordinales": ["primero","segundo"], "modulo_mediacion": true}'
   ```

   Vías: `via_a` nulidad absoluta · `via_b` vicio del consentimiento ·
   `via_c` incorporación · `via_d` contenido/abusividad; `fondo` = motivos
   recolocados al fondo (fuera del 408.2). Escribe en el store central
   `data/_skill_logs/oposicion-alegacion-nulidad/uso.jsonl` (no en el bundle). Es
   el insumo del proceso de mejora de la skill.
7. **Cosecha de jurisprudencia** (paso obligatorio de cierre, vía **conector
   Google Drive**): usando los IDs de `scripts/drive_config.json`,
   - sube **un fichero** a la carpeta `cosecha/` (`cosecha_folder_id`) con nombre
     `AAAA-MM-DD_usuario_expediente.json` y el contenido de la sesión (ECLI
     citadas; `nuevas` = las que no estén en `indice_jurisprudencia.json`;
     candidatas; resultado). **Un fichero por sesión** — nunca reescribas uno común
     (Drive no permite *append* atómico → colisiones);
   - por cada sentencia verbatim cuya incorporación **sugieras**, sube su `.md` a
     `candidatas_verbatim/` (`candidatas_verbatim_folder_id`), nombrada por ECLI.
   No descargues, verifiques ni promuevas nada aquí: eso lo hace el mantenedor.
   (Esquema en el `_LEEME.md` de la carpeta de Drive.)

## Repertorio de apartados (no es una plantilla obligatoria)

Lo que sigue es el **catálogo** de apartados que la práctica ha consolidado para
este trámite, con la jurisprudencia de cabeza de serie en
`references/estructura-escrito.md`. **No hay un número fijo de ordinales**: elige
solo los que respondan a motivos realmente alegados, en el orden que mejor sirva
a la estrategia, y omite los demás. Catálogo habitual:

- **Cuestión previa** — delimitación del trámite 408.2 e indefensión (falta de
  claridad de la alegación, art. 416.1.5.ª LEC; objeto del trámite; art. 24 CE).
  Cuando existe este defecto, suele ser el mejor flanco y conviene abrir con él.
- **Consideraciones generales** — consumidor/adhesión sin ineficacia automática;
  calificación de las cuatro vías; carga de la prueba (art. 217 LEC).
- **Vicio del consentimiento** (→ anulabilidad) — consentimiento válido; el
  idioma no vicia per se; representación aparente / ratificación tácita; error no
  excusable; inexistencia