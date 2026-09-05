---
titulo: "Un fichero, un espejo: dedup por bytes con procedencias en la sala de máquina (MEJORAS #147, vía A)"
fecha: 2026-09-06
estado: implementado
rev: "1"
relacionado: "MEJORAS #147 · PLAN fila #21 acción 11"
---

# Un fichero, un espejo: dedup por bytes con procedencias en la sala de máquina

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
