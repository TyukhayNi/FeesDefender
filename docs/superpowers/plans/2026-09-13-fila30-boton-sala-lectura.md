---
tipo: plan
estado: vigente
creado: 2026-09-13
rev: 1
---

# Fila #30 — el botón que disparaba el motor muerto, y la premisa que llevaba tres días rancia (`[APER-70]`)

## 1. El encargo, y lo que la medición le corrigió

La fila #30 decía: que el botón «📚 Sala de lectura» de Streamlit deje de llamar al
constructor deprecado. El daño declarado tenía dos mitades:

1. `streamlit_app.py:1397` llamaba a `core.sala_lectura.organizar`, y ese módulo abre su
   docstring con `[DEPRECADO 2026-06-18] … queda SUPERSEDIDO por la skill
   organizar-sala-lectura … No ampliar`. Quien pulsa ese botón son **Paola y Ana, que no
   tocan código**: no pueden leer una docstring antes de pulsar.
2. «Y lo que obtienen **no es la sala plana**».

**La primera mitad es cierta. La segunda está refutada contra la fuente**, y la cronología
explica por qué se citó tres días:

| Hora del 2026-09-10 | |
|---|---|
| 22:47:39 | `a545e43` anota `[APER-70]` en el runbook: «lo que produce **no** es la sala plana» |
| 22:58:29 | `a2e6676` (PR [#328](https://github.com/TyukhayNi/FeesDefender/pull/328)) aplana el motor |

`_directorio_destino` ([core/sala_lectura.py:761](../../../core/sala_lectura.py:761))
devuelve hoy el directorio plano, con la subcarpeta del documento compuesto como única
excepción — la misma que fija la skill. La frase fue cierta **once minutos**.

## 2. Lo que sí se midió, y es peor que la premisa

**El botón casi nunca podía terminar.** `clasificar_caso` resuelve automáticamente dos
cosas: imágenes, y ficheros cuyo **nombre** case una de ~30 palabras clave. Todo lo demás
cae a residuo y `organizar` **se detiene** con este mensaje en pantalla:

> ⏸ Quedan N documento(s) sin clasificar… **Pídele a Claude que los resuelva en una sesión**
> y vuelve a pulsar el botón.

Medición de referencia sobre un caso real: **19 clasificados / 42 residuo** sobre 61
documentos. El destinatario de ese mensaje no tiene Claude. Era una vía falsa, no una vía.

**Y si terminaba, entregaba 2 de los 4 artefactos contratados** (`MEJORAS #221`, confirmado
en W-030TZY y W-02NHNC): sin `_MANIFIESTO.md` —que no lo escribe **nadie** en todo `core/`
ni `scripts/`— y con el `indice_documental.yaml` en `01_Procesado/` en vez de dentro de la
sala.

**El motor no es código muerto**, y eso pesó en la decisión: **147 tests** en 11 ficheros lo
cubren, y el PR #328 le pasó dos rondas adversariales con 17 hallazgos tres días antes.

## 3. La decisión, y por qué no fue ninguna de las tres que el encargo ofrecía

El encargo ofrecía retirar el botón, redirigirlo, o dejarlo con un aviso. Se eligió una
cuarta, y el dato que la fuerza es este: **la skill que gobierna no corre desde Streamlit**.
`SKILL.md` §modos — «corre en claude.ai/Cowork o en Claude Code local». Es prompt-driven y
necesita un visto bueno humano sobre la propuesta de clasificación. No hay puente barato, y
`MEJORAS #34` ya lo tenía fichado desde 2026-06-17.

- **Redirigir** no tiene destino.
- **Dejarlo con un aviso** conserva el camino muerto y pone la decisión en manos de quien no
  puede juzgarla.
- **Retirarlo** no quita nada real —hoy el botón da un aviso irresoluble—, pero deja a Paola
  y Ana sin saber en qué punto está un caso.

**Lo que se hizo: el expander se queda y deja de escribir.** Pasa a solo lectura — si la
sala está montada, cuántos documentos tiene, cuáles de los cuatro artefactos le faltan, y el
texto para pedir el montaje. Quita el camino muerto *y* da algo que hoy no existía.

> Nikolai eligió primero **retirar el expander entero** y a los pocos minutos anuló su
> decisión en favor de esta. Se deja escrito: la opción retirada sigue siendo defendible y
> es el diff más limpio.

## 4. Lo construido

- **`core/sala_lectura_estado.py`** — lector de solo lectura (`montada`, `n_documentos`,
  `artefactos`, `solicitud`). **Delega** el veredicto de los cuatro artefactos en
  `verificar_apertura.c4_artefactos_de_la_sala`, que existía desde `MEJORAS #221` **sin
  ningún llamador fuera de su propio módulo**; transcribir esa lista la habría hecho
  divergir, que es como `_MD_SUBDIR` compuesto en dos sitios dejó 140 enlaces muertos
  (`MEJORAS #151`). La solicitud identifica **por W-code y nunca por el `case_id`**, que
  lleva la dirección del inmueble dentro (§16 de `SEGURIDAD_DATOS.md`).
- **`tests/test_guard_ui_sin_deprecados.py`** — la frontera, no el ejemplo: **la UI no puede
  importar ningún módulo de `core/` declarado deprecado**. Deprecar uno basta para que su uso
  en la UI se ponga rojo, sin tocar el guard. Distingue **declarar** de **citar** (el
  marcador abre la primera línea no vacía), y esa distinción la compró un falso positivo
  sobre el módulo nuevo de este mismo diff.
- **`streamlit_app.py`** — el expander, reescrito.
- El **CLI** `scripts/sala_lectura` **no se toca**: quien lo teclea sabe lo que teclea, y el
  runbook lo llama «el disparo rápido en local».

**Verificación:** suite **5457 recogidos, 0 fallos, 0 errores, 94 skipped** con la semilla
777 (+25 sobre el 116º cierre — exactamente los 8 del guard y los 17 del lector). Arnés de
mutación de **10 mutantes, 10 muertos**, más el control positivo sobre el árbol real:
recablear el motor a la UI pone el guard rojo nombrando módulo y línea de declaración.

**Pendiente operativo, que no bloquea:** el `.skill` de `organizar-sala-lectura` **v1.17**
queda empaquetado en `dist/skills/` (`sha256 4e8213e8…`, 11 ficheros, verificado por
lectura del `SKILL.md` empaquetado). **Instalarlo en Cowork es acción manual de Nikolai** —
sin ese paso, la skill gobierna sobre el papel y la instalada sigue siendo la anterior.

## 5. Adjudicación de la revisión adversarial (Codex, 2026-09-13) — NO-SHIP, remediado

- **Objeto revisado:** el diff `f1759cf..c133108` (seis ficheros), commit `c133108`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-09-13-fila30-r1-adversarial-review.md`
- **Hallazgos:** 9 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** este PR, sobre `c133108`

**El `ALTO` dice que había calibrado el lector contra el constructor equivocado.** La skill
`organizar-sala-lectura` —la que esta misma fila declara gobernante— pone los **cuatro**
artefactos dentro de `Sala lectura/`; `verificar_apertura.c4` buscaba el catálogo solo en
`01_Procesado/`, que es donde lo deja el motor deprecado. Resultado: una sala recién
construida por el constructor bueno salía **incompleta** en pantalla, con su propio catálogo
contado además como un documento más, y **volver a correr la skill no lo arreglaba nunca**.
Es la ironía exacta de esta fila: retiré el botón que llamaba al motor muerto y dejé al
lector midiendo con la regla del motor muerto.

Lo verifiqué por mi cuenta antes de aceptarlo, y hay dos pruebas independientes dentro del
repo: el árbol de `SKILL.md` y su propio `verificar_sala.py`, que excluye
`indice_documental.yaml` del recuento de la sala — o sea **asume** que vive ahí dentro.
Remedio: `c4` acepta **las dos** ubicaciones y su evidencia dice en cuál apareció
(`catalogo_en`), porque cuál es la canónica sigue sin decidirse (`MEJORAS #221`). Tolerar en
silencio habría escondido la ambigüedad en un tercer sitio.

**Los cuatro `MEDIO` son todos sobre instrumentos que prometían más de lo que medían:**

1. **H-02** — `rglob` se traga los errores de exploración, así que una sala ilegible decía
   «0 documento(s)» con la misma cara que una vacía. `n_documentos` pasa a ser `int | None`
   y la pantalla dice «no se pudo leer». Es [[feedback-no-lo-se-no-es-no-hay]] en una línea de UI.
2. **H-03 — el que más me interesa.** Mi test «no toca un solo byte» sellaba solo ficheros,
   así que **daba verde ante un `mkdir`**, que es justo la escritura que un lector comete.
   El revisor lo demostró corriendo **el cuerpo original de mi test** con un `estado`
   sustituido: `control_mkdir: ["VERDE","VERDE","VERDE"]`. Mi arnés tenía un mutante para
   eso (`M7`) y **moría por otros tests**, no por el sello: creí probada una propiedad que su
   propia guarda no comprobaba. El sello lleva ahora directorios y **dos controles positivos**.
3. **H-04** — el guard prometía «la UI no importa módulos deprecados» y lo que comprueba son
   los imports **estáticos y literales de un fichero**. Su inventario de once familias no
   cubiertas se transcribe entero en la docstring del guard.
4. **H-05** — en Windows `INDICE.md` e `indice.md` son el mismo fichero: `c4` lo veía como
   artefacto y el recuento lo sumaba como documento. Dos números de la misma pantalla
   discrepando sobre los mismos bytes. Se compara en `casefold()`; lo demás (auxiliares,
   vacíos, enlaces) se **declara** en vez de filtrarse a ciegas, porque un fichero oculto
   puede ser prueba válida.

**Y tres de los cuatro `BAJO` son frases mías que no se sostienen** (H-07: «dos de los
cuatro» mezclaba el inventario de la sala con el del expediente — el motor escribe **tres**;
H-08: «no lo escribe nadie» es literalmente falso, `scripts/redate_whatsapp_anexos.py:150`
reescribe el manifiesto, aunque no lo **genere**; H-09: un nombre de test que anunciaba un
módulo vivo sobre un fixture deprecado). El cuarto (H-06) invertía la precedencia
paquete/fichero respecto a como resuelve Python.

**Arnés tras la remediación: 17 mutantes, 17 muertos.** Los siete nuevos (`M11`–`M17`) son
uno por remediación. `M17` **sobrevivió** en la primera pasada —no tenía control para la
precedencia de paquetes— y eso le dio el test que le faltaba; es la lección de
[[feedback-mutacion-vale-por-su-mutante]] cobrada dos veces en la misma sesión.

**Cobertura declarada:** la remediación **no pasó revisión** — el presupuesto de una ronda
está consumido y el radio de daño no justifica una segunda (`CLAUDE.md`: 2 rondas solo si la
pieza decide quién escribe o puede destruir datos; esta **retira** una escritura). La
acreditan los 35 tests, el arnés de 17 mutantes y los controles positivos. Y queda **sin
verificar**, declarado por el propio revisor: la genealogía de las copias, la suite entera en
su entorno (sin `.venv` ni `git`), la UI arrancada de verdad, y las cifras **19/61** y «casi
siempre», que vienen de la bitácora del 2026-06-18 y no se remidieron aquí.
