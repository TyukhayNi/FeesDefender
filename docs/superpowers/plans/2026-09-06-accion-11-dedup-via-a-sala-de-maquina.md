---
titulo: "Un fichero, un espejo: dedup por bytes con procedencias en la sala de máquina (MEJORAS #147, vía A)"
fecha: 2026-09-06
estado: implementado
rev: "2"
relacionado: "MEJORAS #147 · PLAN fila #21 acción 11"
---

# Un fichero, un espejo: dedup por bytes con procedencias en la sala de máquina

> **Rev. 2 (2026-09-06), tras la R1 adversarial de Codex sobre el diff (`NO-SHIP`, 7 hallazgos, 7 confirmados, 0 refutados; remediados en el PR #296).** Adjudicación en el **§4**.
>
> Plan corto de la **vía A** de `MEJORAS #147`, la barata y cierta. Medido en W-02Q38C el
> 2026-09-04: 51 espejos MD para 49 contenidos distintos; el `Certificado titularidad…` estaba en
> `ARRAS/` y en `OFERTAS/OFERTA 1 …/` con el **mismo `sha256`**, y la sala de máquina pagó dos OCR,
> escribió dos MD y el corpus que lee el LLM de viabilidad contó el mismo hecho dos veces. Radio
> de daño: produce derivados, no toca el crudo ni destruye nada → **una ronda**, sobre el diff (§4).

## 1. Qué se cambia y qué no

**Se cambia.** `plan()` marca `duplicado_de = <rel_path del titular>` en toda entrada del inventario
cuyo `sha256` ya apareció antes (el inventario va en orden `sorted`, así que el titular es
determinista: el primero por ruta). `ejecutar()` no procesa la copia: le da una **fila de custodia
propia** (su `rel_path`, su `sha256`, método `duplicado`, `chars=0`, estado **heredado** del titular
—el peor de sus filas—, nota con la ruta del espejo único) y **anota en el titular** «también en
<ruta> (mismo sha256)». El preview del CLI cuenta `duplicados: N` aparte y no los suma a las rutas.

**Por qué la llave es el `sha256` del crudo y no `text_sha256`.** La entrada de `MEJORAS #147`
proponía llavear por el hash del texto. Para la vía A (mismos bytes) los dos son equivalentes, y
el hash del crudo ya está en el inventario **antes** de pagar el OCR: es lo que ahorra el segundo
OCR. El hash del texto es la llave de la vía B (mismo documento re-descargado con bytes distintos)
y necesita una noción de identidad documental (C.S.V., protocolo) que no se toca aquí.

**No se cambia.** El crudo: las dos copias siguen en `00_Input/` (es el Drive del cliente). La
identidad de las filas de cobertura (`_clave_cobertura`, por `rel_path`): siguen siendo DOS filas
de custodia, como documenta `fusionar_cobertura` (a). El estado idempotente por `sha256`: la copia
hereda el `skip` del titular, así que en corridas posteriores ninguna de las dos se reprocesa.
`reforzar` no ve al duplicado (`_REFORZABLES` no lo incluye: no tiene PDF propio que renderizar).

## 2. Decisiones que no son detalle

1. **La copia hereda el peor estado del titular.** Si el titular salió `empty`, la copia no puede
   salir `ok`: saldría de la worklist de `_cobertura.md` un documento que sí requiere revisión.
2. **La titularidad es DURABLE y la elige la capacidad de extraer, no el orden** (R1, H-01 y
   H-06). `plan()` recibe `productores_previos` (los `rel_path` con espejo propio en la cobertura
   persistida): quien ya tiene espejo lo conserva aunque aparezca una carpeta que ordene antes,
   con `--force` incluido; dos productoras legadas siguen siendo dos (no se retira una generación
   existente). Si nadie tiene espejo, titular es la primera procedencia cuya ruta sabe extraer
   (un DOCX sin extensión es `sin_soporte`; su copia `.docx` es `nativo` y debe ser la titular).
3. **Nunca colapsar contra nada** (R1, H-05). La copia es alias si el titular dejó filas en esta
   corrida —salvo que todas sean `sin_soporte`— o si su espejo YA está en disco (`--solo <copia>`,
   `reforzar`); solo si no hay ni filas ni espejo se procesa como un documento más.
4. **La relación se reconcilia al fusionar** (R1, H-04). `reconciliar_alias` corre sobre la
   cobertura completa tras `fusionar_cobertura` en `apply` y en `reforzar`: el alias toma el peor
   estado vigente de las productoras con su sha, `alias_de` al día, y el titular recupera
   «también en …» (idempotente). Sin esto, reprocesar solo al titular dejaba a la copia con el
   estado viejo y al titular sin la procedencia.
5. **El alias es una referencia ESTRUCTURADA** (R1, H-02): `DocCobertura.alias_de` (slug del
   titular). El validador de la ficha CRM (`corpus_legible`) no cuenta la copia ni como legible ni
   como ilegible: su texto está entero en el espejo del titular, y pedirle un `<slug>.md` propio la
   convertía en un falso «sin espejo MD» que además cambiaba la salida del validador.
6. **La nota apunta a rutas que existen** (R1, H-07): `03_MD/<slug>.md` para el suelto;
   `02_Documentos/<parent>/` y el patrón `03_MD/<parent>__dNN_*.md` para el bundle.
7. **Lo que sigue silencioso, con nombre.** Si el titular se procesó en una corrida ANTERIOR y la
   copia aparece después (nueva carpeta con el mismo fichero), el estado por `sha256` la salta y
   **no deja fila**: es el comportamiento de siempre y no cambia aquí.

## 3. Pruebas

`tests/test_sala_maquina_duplicados.py` — D1 `plan()` marca la copia y no el titular, shas distintos
no se marcan, la copia hereda el `skip`; D2 un espejo, dos filas, el extractor corre una sola vez,
el render muestra las dos procedencias; D3 estado heredado (`empty`); D4 copia de un bundle; D5 sin
filas del titular la copia se procesa; D6 el preview cuenta aparte; D7 `fusionar_cobertura`
conserva las dos filas.

Docs tocados: `SKILL.md` de `organizar-sala-maquina` 1.6 + CHANGELOG, `MEJORAS_FUTURAS.md` #147
(vía A resuelta; B y C siguen), `PLAN.md` fila 21 acción 11 — y la fila 10 de la cola, que seguía
«pendiente» para el ítem cerrado como acción 10 (PR #294): ✅ y colapsada al ledger.

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-06) — NO-SHIP, remediado

- **Objeto revisado:** el diff `8bfd098..cb63770` (PR #296)
- **Ronda:** 1 (diff) — la única por radio de daño
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-06-accion-11-dedup-via-a-r1-adversarial-review.md`
- **Hallazgos:** 7 — **7 confirmados, 0 refutados**
- **Remediado en:** commit `0b7985d` (PR #296); esta rev. 2 del plan

**Independencia: plena** — revisor Codex (`gpt-6-astra`), adjudicador Claude Code. Cada hallazgo
se contrastó contra la fuente; lo que reproduje está en el §2 del acta. **Antes de la ronda**, en
autorrevisión, encontré y remedié que la copia sumaba un segundo intento al sha del titular
(`MAX_INTENTOS` en dos corridas): commit `4612d1b`, test D8. El revisor recibió el diff SIN ese
remedio (`8bfd098..cb63770`) y se dice.

| # | Sev. | Hallazgo (frontera, no ejemplo) | Veredicto | Remedio |
|---|---|---|---|---|
| H-01 | ALTO | El titular era «el primero por ruta»: un DOCX sin extensión (`sin_soporte`) suprimía a su copia `.docx` (`nativo`), que sí sabía extraer — mismos bytes no es misma capacidad de extracción | ✅ confirmado (reproducido con python-docx) | El titular es la primera procedencia con ruta que sabe extraer; y si aun así sus filas son todas `sin_soporte`, la copia se procesa. D9/D9b; M11, M14 mueren |
| H-02 | ALTO | `corpus_legible` convertía toda fila `ok` en un `<slug>.md` a leer; la copia no lo tiene → falso «sin espejo MD» que además cambiaba la salida del validador (de `Exit(1)` a «1 sin comprobar») | ✅ confirmado (leído en `crm_ficha_validacion.py:305` y `crm_ficha_validar.py:87`) | `DocCobertura.alias_de` (referencia estructurada al titular) y `corpus_legible` no cuenta la fila `duplicado` ni como legible ni como ilegible. D10; M13 muere |
| H-03 | ALTO | El bucle de intentos iteraba también la copia y sumaba N intentos por corrida al mismo sha: `MAX_INTENTOS` se agotaba tras una sola tentativa real | ✅ confirmado — **lo encontré en autorrevisión y lo remedié antes de recibir el informe** (`4612d1b`, D8); el revisor lo midió sobre el diff anterior | La copia no cuenta en `intentos`. D8; M9 muere |
| H-04 | MEDIO | Reprocesar solo al titular (`--solo`, `reforzar`) sustituía sus filas por otras frescas (sin «también en») y dejaba a la copia con el estado viejo | ✅ confirmado | `reconciliar_alias` sobre la cobertura fusionada en `apply` y `reforzar`: estado heredado vigente, `alias_de` al día, procedencia reanotada (idempotente). D11/D11b; M10, M10b, M17 mueren |
| H-05 | MEDIO | `--solo <copia>` desmarcaba solo la copia: sin filas del titular en la corrida, el fallback la procesaba → segundo MD (stems distintos) o reescritura del compartido con otro `source_path` (mismo stem) | ✅ confirmado | Si el espejo del titular ya está en disco, la copia es alias (provisional; `reconciliar_alias` pone el estado). D12 (dos variantes); M6 muere |
| H-06 | ALTO | La titularidad la decidía el orden de ruta: una carpeta nueva que ordena antes convertía al titular de ayer en alias sin retirar su espejo (dos MD activos); y dos bundles legados materializados pasaban a «una fila alias» con sus artefactos huérfanos (integridad → salida 3) | ✅ confirmado | Titularidad **durable**: `plan()` recibe `productores_previos` (con `--force` también); quien tiene espejo lo conserva y dos productoras legadas siguen siendo dos — no se retira ninguna generación. D13; M12 muere |
| H-07 | BAJO | La nota del bundle anunciaba `03_MD/<parent>` como si fuera una ruta; no existe ni como fichero ni como carpeta | ✅ confirmado | `03_MD/<slug>.md` para el suelto; `02_Documentos/<parent>/` y `03_MD/<parent>__dNN_*.md` para el bundle. D14 comprueba que la ruta existe |

**Lo que el revisor verificó y resultó correcto:** primera corrida con dos PDFs de nombres
distintos → un MD, dos filas, ninguna extracción de la copia; mismo nombre y mismo sha → sin
segunda materialización ni colisión; `_clave_cobertura` conserva las dos filas; `skip` y
`agotados` por sha dan el mismo resultado al grupo; una copia `empty` no entra en `exitosos`;
`duplicado` no está en `_REFORZABLES`; `90_Notas personales/` y los ficheros de protocolo no roban
la titularidad; `detectar_ocr_ciego.filas_ok` devuelve al titular una vez; el censo de escrituras
sigue en 91. **Sus tres mutantes supervivientes** (M1 `_peor_estado` con varias filas, M2 mismo
slug, M3 el gancho `on_documento`) tienen ahora test (D15, D15b) y mueren; su M4 (guard textual de
O9 de la acción 10) se acepta como límite conocido de ese guard: el test funcional O9 sí cuenta la
ruta. **Declarado sin verificar por el revisor:** suite completa (la corre el autor, dos semillas,
tras la remediación), OCR/LibreOffice/visión reales, W-02Q38C real, la skill en Cowork, caídas de
proceso y concurrencia. **Medido y no remediado, con nombre:** la reconstrucción de cobertura desde
`03_MD/` (sin `_cobertura.json`) devuelve una sola procedencia y pierde «también en» — el alias
solo vive en el JSON; `documentos_procesados` del evento forense cuenta filas (copias incluidas),
no contenidos únicos; y la copia que aparece en una corrida POSTERIOR al titular sigue sin fila
(§2.7 del plan, diferido).

**Cobertura de la remediación: sin segunda ronda** (regla de rondas: una por radio de daño); los
contraejemplos del revisor se reprodujeron contra el código remediado, cada uno con su test y su
mutante.
