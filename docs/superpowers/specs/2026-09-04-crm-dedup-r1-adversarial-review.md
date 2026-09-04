---
tipo: revision-adversarial
objeto: "diff de la dedup del CRM: partes por NIF/email y expediente por W-code"
objeto_rev: "rama claude/crm-dedup-partes-y-expediente, commit ea457be"
commit: ea457be
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q4vt
sha256_informe: d5fa9c93fc2e556dc0251e77135d04ac6e1fb9123bd61f87ffaf001b0a8ec821
adjudicado_en: docs/superpowers/specs/2026-09-04-crm-dedup-r1-adversarial-review.md §3
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revision adversarial R1.** El §1 conserva la voz del revisor sin una coma
> cambiada; el §2 es la evidencia que verifique por mi cuenta y el §3 mi adjudicacion.
>
> **La adjudicacion va en el §3 de esta misma acta** porque este cambio no tiene spec ni
> plan donde embeberla: nacio de un encargo directo de Nikolai en una sesion de
> operacion. Se declara en el frontmatter para que nadie la busque en otro sitio.
>
> **Una ronda y no dos, por radio de dano** (`PLAN.md` fila #13): la pieza no decide
> quien puede escribir sobre que copia ni puede destruir datos de cliente. Escribe en el
> CRM —crea fichas y expedientes— pero eso ya lo hacia antes del cambio; lo que se anade
> es **una comprobacion previa que puede impedir escribir**.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q4vt -->

# Revisión adversarial R1 — diff `cb5b6b8` → `ea457be`

## Integridad, alcance y ejecución

- Objeto revisado por contenido: `C:/t/rev2/head/`, contrastado con `base/` y `DIFF.patch`. No hay `.git`; genealogía **SIN VERIFICAR**, conforme al encargo.
- Hash de apertura, comando exacto:

  ```powershell
  & 'C:\Program Files\Git\bin\bash.exe' -lc "cd /c/t/rev2/head && find . -type f -exec sha256sum {} + | sort -k2 | sha256sum"
  ```

  Salida:

  ```text
  8b8e43b2042b902a9bc1b1e0fea613537882b69d12a383eb43e7d73098a73a8d *-
  ```

- Todo lo que escribió pytest o las sondas se ejecutó sobre `C:/t/rev2/informe/run/`, copia del objeto. No se escribió en `head/` ni `base/`.
- Hash de cierre, mismo comando exacto y salida:

  ```text
  8b8e43b2042b902a9bc1b1e0fea613537882b69d12a383eb43e7d73098a73a8d *-
  ```

  Coincide con apertura y con el valor exigido: el objeto no fue mutado.

## H-01 — Un fallo de consulta de identidad autoriza crear y vincular una ficha duplicada

**Severidad:** ALTO

**Fichero y línea:** `core/sudespacho_relations.py:919-955`, `:982-991`, `:1189-1199`.

**Cómo lo comprobé:** desde `C:/t/rev2/informe` ejecuté:

```powershell
$env:PYTHONPATH='C:\t\rev2\informe\run'; & 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' run\probe_r1.py
```

Salida relevante:

```text
H1 identidad_500 resultado=('NUEVA', True) crear=1 vincular=1
```

**Escenario de fallo concreto:** ya existe el contrario con NIF `46139867G` o email `a@b.example`; las dos consultas `GET element_registries` reciben HTTP 500 (también vale red caída o clave ausente), pero el endpoint de creación vuelve a responder. `_buscar_registros` convierte ambos fallos en `[]`; `resolver_parte` concluye “nuevo”; `_resolver_o_crear_contrario` crea `NUEVA` y `ensure_contrario_vinculado` la vincula. El comentario de `:923-924` reconoce el duplicado como “peor caso”, pero ese resultado contradice directamente la garantía de deduplicación y escribe en el CRM.

## H-02 — La caída del chequeo de W-code se presenta como ausencia y `_alta_crm` crea el expediente duplicado

**Severidad:** ALTO

**Fichero y línea:** `core/sudespacho_relations.py:1019-1027`, `:1064-1076`; `scripts/abrir_caso.py:676-706`.

**Cómo lo comprobé:** mismo comando de sonda anterior. Salida relevante:

```text
H2 wcode_500 bloquea=False sin_comprobar=[] alta=1
```

**Escenario de fallo concreto:** el CRM ya contiene `W-02Q38C`; las búsquedas en ambas jurisdicciones reciben HTTP 500. El resultado declara `bloquea=False` y, pese al contrato de `sin_comprobar`, deja esa lista vacía. `_alta_crm` no muestra “SIN VERIFICAR” y ejecuta `create_expediente` una vez. Por tanto, el criterio que debía bloquear falla abierto precisamente cuando no pudo comprobarse.

## H-03 — La identidad depende del orden arbitrario del primer resultado y puede vincular otra ficha

**Severidad:** ALTO

**Fichero y línea:** `core/sudespacho_relations.py:982-999`.

**Cómo lo comprobé:** mismo comando de sonda. Salida relevante:

```text
H3 multiples orden_111_222=ResolucionParte(id=None, por=None, conflicto=('111', '222')) orden_222_111=ResolucionParte(id='222', por='nif', conflicto=None) un_criterio=ResolucionParte(id='111', por='nif', conflicto=None)
```

**Escenario de fallo concreto:** para el mismo estado del CRM, el NIF devuelve las fichas `{111, 222}` y el email devuelve `222`. Si el servidor ordena el NIF como `[111, 222]`, hay conflicto; si devuelve `[222, 111]`, no lo hay y se vincula `222`. Con sólo NIF y dos coincidencias, se vincula silenciosamente `111`. `_primer_id` pierde cardinalidad y conjunto, de modo que ni la decisión de conflicto ni la identidad son estables; una ficha distinta puede quedar vinculada sólo por aparecer primero.

## H-04 — El respaldo de colaborador vincula por email aunque el NIF haya quedado sin comprobar

**Severidad:** ALTO

**Fichero y línea:** `core/sudespacho_relations.py:1764-1788`.

**Cómo lo comprobé:** mismo comando de sonda. Salida relevante:

```text
H4 fallback_extra resultado=('999', False) link=('634', '999')
```

**Escenario de fallo concreto:** el NIF `11111111H` pertenece a la ficha `111`, pero su consulta filtrada falla y se colapsa a `[]`; el filtro de email tampoco resuelve, mientras el listado completo encuentra `ana@x.example` en la ficha `999`. Como el fallo del NIF no queda representado, el respaldo de `find_colaborador_by_email` vincula `999` sin levantar `ConflictoDeIdentidad`. El respaldo no atraviesa un conflicto ya devuelto —el `raise` lo impediría—, pero sí evita que llegue a existir cuando un criterio quedó sin comprobar.

## H-05 — La ruta judicial de colaboradores sigue siendo email-only y omite por completo el conflicto NIF/email

**Severidad:** ALTO

**Fichero y línea:** `core/sudespacho_relations.py:1934-1965`.

**Cómo lo comprobé:** mismo comando de sonda. Salida relevante:

```text
H5 colaborador_judicial resultado=('999', False) resolver_calls=0 link=('700', '999')
```

**Escenario de fallo concreto:** el NIF apunta a `111` y el email a `999`. `ensure_colaborador_vinculado_judicial` no llama a `resolver_parte`; busca sólo por email y vincula `999`. Si el email está vacío, puede incluso crear una ficha nueva aunque el NIF ya exista. Esto contradice la premisa del cambio de que la identidad de las partes se resuelve igual en las dos jurisdicciones.

## H-06 — Cualquier resultado de `like` por W-code se eleva a bloqueo sin validar el código exacto

**Severidad:** MEDIO

**Fichero y línea:** `core/sudespacho_relations.py:1064-1069`.

**Cómo lo comprobé:** mismo comando de sonda. La respuesta simulada reproduce la forma real `{id, values}` y contiene la referencia `Caso distinto (W-123456) - Vuelta`:

```text
H6 prefijo bloquea=True por_wcode=[('extrajudiciales', '700')]
```

**Escenario de fallo concreto:** se busca `W-12345`; el `like` devuelve una referencia con `W-123456`, que es otro código. El código sólo lee `id=700`, no inspecciona `values` ni aplica `wcode_match`, y bloquea el alta como duplicada. Los `%` o `_` tampoco se escapan antes de enviarse a `like`; en el camino normal el mutex restringe el W-code a alfanuméricos, pero una dirección sí puede contenerlos y la función pública tampoco valida por sí misma. La semántica exacta de escape del tenant para esos comodines: **SIN VERIFICAR**.

## H-07 — `_buscar_registros` sí puede lanzar y la excepción escapa de `_alta_crm` bajo el mutex

**Severidad:** MEDIO

**Fichero y línea:** `core/sudespacho_relations.py:907`, `:944-955`; `scripts/abrir_caso.py:676-696`.

**Cómo lo comprobé:** mismo comando de sonda. Salida relevante:

```text
H7 json_lista excepcion=AttributeError: 'list' object has no attribute 'get'
H7 alta_excepcion=AttributeError: 'list' object has no attribute 'get'
```

**Escenario de fallo concreto:** HTTP 200 con JSON válido pero de forma inesperada (`[]`, igual ocurriría con `null`) supera el `try` que sólo envuelve `r.json()` y falla en `data.get`. La excepción llega sin convertir a `_alta_crm`; allí la llamada está antes del `try` de creación y no se traduce a `AbortarApertura`. El guard AST de terminación bajo mutex sí pasa y no hay `typer.Exit` nuevo dentro del bloque, pero el CLI termina con una excepción cruda después de que el gestor del mutex desenrolle.

## H-08 — NIF/NIE/CIF y email sólo reciben `strip`; no hay identidad canónica

**Severidad:** MEDIO

**Fichero y línea:** `core/sudespacho_relations.py:221-245`, `:926`, `:981-983`.

**Cómo lo comprobé:** mismo comando de sonda. Salida relevante:

```text
H8 valores_enviados=['x-1234567-l', 'Foo@EXAMPLE.COM']
```

**Escenario de fallo concreto:** el CRM almacena el NIE `X1234567L` y el email `foo@example.com`; llegan `x-1234567-l` y `Foo@EXAMPLE.COM`. El cliente manda esas grafías sin retirar separadores ni normalizar caja, usando `equal`. Si el tenant compara literalmente, no encuentra la ficha y H-01 culmina en duplicado. Que el backend concreto haga comparación insensible a caja o normalice NIF: **SIN VERIFICAR**; lo comprobado es que esta capa no lo garantiza. El respaldo de colaboradores sí baja a minúsculas en cliente, pero contrarios no tienen ese respaldo y ningún camino canonicaliza NIF/NIE/CIF.

## H-09 — El tercer criterio de expediente (contrario) no está cableado en el único llamador productivo

**Severidad:** BAJO

**Fichero y línea:** `scripts/abrir_caso.py:676-678`; `core/sudespacho_relations.py:1078-1088`.

**Cómo lo comprobé:** búsqueda estática mostró que sólo `_alta_crm` llama a la función; la sonda capturó sus argumentos. Mismo comando de sonda, salida:

```text
H9 kwargs_busqueda_desde_alta={'w_code': 'W-02Q38C', 'direccion': 'Xabec 8'}
```

**Escenario de fallo concreto:** existe otro expediente del mismo contrario, con W-code y dirección distintos. `buscar_expedientes_duplicados(..., contrario_id=...)` produciría aviso, pero `_alta_crm` nunca pasa `contrario_id` y no hay otro llamador productivo. El criterio está construido y probado de forma aislada, pero no puede avisar durante el alta. Es BAJO porque, por decisión de producto, contrario sólo avisa y no bloquea.

## H-10 — Los tests verdes sustituyen justo las capas que contienen los fallos

**Severidad:** MEDIO

**Fichero y línea:** `tests/test_crm_dedup_partes.py:35-43`, `:52-77`; `tests/test_crm_dedup_expediente.py:33-34`, `:39-47`, `:95-103`, `:197-211`; `tests/test_abrir_caso_cli.py:42-57`.

**Cómo lo comprobé:** ejecuté las pruebas relevantes sobre la copia, añadiendo una fixture de revisión que hace fallar cualquier `socket.connect` real:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest tests/test_crm_dedup_partes.py tests/test_crm_dedup_expediente.py tests/test_sudespacho_relations.py tests/test_abrir_caso_cli.py tests/test_abrir_caso_exit_bajo_mutex.py --basetemp=..\bn2 -p review_no_network -p no:cacheprovider -o addopts=
```

Salida:

```text
collected 194 items
============================= 194 passed in 6.73s =============================
```

Después ejecuté las ocho aserciones adversariales:

```powershell
$env:PYTHONPATH='C:\t\rev2\informe\run'; & 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest run/tests/test_adversarial_r1.py -vv --basetemp=b2 -p no:cacheprovider
```

Salida resumida:

```text
collected 8 items
FAILED ...test_un_500_de_identidad_no_debe_autorizar_una_ficha_nueva
FAILED ...test_un_500_en_wcode_no_debe_acabar_en_alta_crm
FAILED ...test_resultados_multiples_se_resuelven_por_interseccion_no_por_orden
FAILED ...test_un_criterio_ambiguo_no_debe_elegir_el_primer_id
FAILED ...test_respaldo_de_colaborador_no_debe_vincular_si_el_nif_quedo_sin_comprobar
FAILED ...test_colaborador_judicial_tambien_debe_parar_ante_nif_y_email_distintos
FAILED ...test_like_de_wcode_no_debe_bloquear_un_codigo_mas_largo
FAILED ...test_buscar_registros_cumple_nunca_lanza_con_json_de_forma_inesperada
============================== 8 failed in 2.22s ==============================
```

**Escenario de fallo concreto:** `_busca` nunca devuelve más de un ID ni representa error; los dobles de expediente sólo devuelven `{"id": ...}` y omiten `values`; el test de “SIN VERIFICAR” inyecta un `DuplicadosExpediente(sin_comprobar=...)` ya construido, por lo que no prueba que un 500 lo produzca; no hay prueba de `ensure_colaborador_vinculado_judicial`. La fixture `autouse` de CLI sí impide las llamadas HTTP de módulo en ese fichero, pero también sustituye la búsqueda por un resultado vacío; los tests dedicados de cableado usan resultados prefabricados. Así pasan por construcción mientras no ejercen los estados de H-01 a H-07.

## Ejecución complementaria y límites

- La suite completa original, excluyendo únicamente la sonda añadida a la copia, se ejecutó con:

  ```powershell
  & 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest tests -q --ignore=tests/test_adversarial_r1.py --basetemp=..\bs -p no:cacheprovider
  ```

  Dio tres fallos ajenos al diff (`test_mcp_wrappers` y dos de `test_session_close_no_pude_medir`). Ejecutados sobre `base/`, fallan los mismos tres; no se atribuyen a este cambio.
- Orden aleatorio: **SIN VERIFICAR**. Comando:

  ```powershell
  & 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -c "import importlib.util; print(importlib.util.find_spec('pytest_randomly'))"
  ```

  Salida: `None`.
- No hubo acceso al CRM real en las 194 pruebas relevantes: cualquier apertura de socket estaba sustituida por una excepción heredada directamente de `BaseException`.

VEREDICTO: NO-SHIP

<!-- informe-literal:fin:q4vt -->

## 2. Evidencia verificada por el adjudicador

- **H-01 y H-02 CONFIRMADOS leyendo el código, y el agravante es mío:** el docstring que
  yo mismo escribí en `_buscar_registros` decía que la función *«no distingue «no hay» de
  «no pude mirar»»* y que *«los llamadores de dedup pueden vivir con eso porque el peor
  caso es crear una ficha de más»*. **El peor caso era exactamente lo que el encargo
  venía a impedir.** Nombré el defecto en prosa y lo dejé escrito como si fuera una
  decisión.
- **H-03 CONFIRMADO por la sonda del revisor, que reproduje leyendo `_primer_id`:**
  devolvía `items[0]`. Con el NIF dando `{111, 222}` y el email `222`, el orden de las
  filas decidía si había conflicto. No es una hipótesis: es lo que hace `list[0]`.
- **H-05 CONFIRMADO por conteo:** añadí `ensure_contrario_vinculado_judicial` y dejé
  `ensure_colaborador_vinculado_judicial` intacto, llamando a `find_colaborador_by_email`.
  El commit anterior afirmaba que «la identidad se resuelve igual en las dos
  jurisdicciones» y era falso para la mitad de las partes.
- **H-06 CONFIRMADO, y con una pieza construida sin encadenar:** `wcode_match` ya existía
  en el mismo módulo desde antes de este trabajo, resolviendo justamente el problema de
  comparar W-codes. No la usé.
- **H-08 MEDIDO POR MÍ contra el tenant real**, que es lo que el revisor declaró
  `SIN VERIFICAR` y sí podía comprobarse: el CRM **tolera** la caja (`…g` minúscula) y
  los espacios envolventes, y **no tolera** los separadores (la forma con puntos y guion
  no encuentra la ficha). El hallazgo se confirma, pero **acotado**: la canonicalización
  necesaria es quitar separadores, no bajar la caja.
- **H-09 CONFIRMADO con matiz que cambia el remedio:** el criterio por contrario no está
  cableado en `_alta_crm`, y **no puede estarlo** — en el alta todavía no hay contrario
  resuelto, se crea después. Su sitio es `crm_ficha`. Queda declarado como pendiente en
  el commit de remediación, no barrido.
- **Lo que NO pude verificar:** que el escape de `%` y `_` en `like` se comporte como el
  revisor supone. La dirección puede contenerlos y no se escapan. Queda anotado.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-04) — NO-SHIP, remediado

- **Objeto revisado:** diff `cb5b6b8..ea457be` — dedup de partes y de expediente en el CRM
- **Ronda:** 1
- **Revisor:** Codex
- **Informe recibido:** 2026-09-04, `sha256` en el frontmatter
- **Hallazgos:** 10 recibidos · **10 confirmados** · 0 refutados · 0 escalados
- **Remediado en:** `4332694`

**10 de 10 confirmados.** El revisor ejecutó de verdad: copió el árbol, corrió las 194
pruebas relevantes bajo una barrera de red propia, escribió **ocho tests adversariales**
que fallaban contra el código, y distinguió los tres fallos preexistentes de `main` de
los suyos corriéndolos también contra `base/`. El objeto no se mutó.

### La frontera, que es UNA y explica cinco de los diez

**El código colapsaba «no lo sé» en «no hay», y desde ahí escribía.** Un 500 durante una
apertura hacía concluir «esta parte no existe» y creaba una ficha duplicada; «no hay
expediente con este W-code» y daba de alta otro. **La protección desaparecía en silencio
y justo cuando algo fallaba** — que es el único momento en que hacía falta.

Y es la misma distinción que la pieza anterior de esta sesión —la verificación por
lectura de `crm_ficha`— predica en voz alta con su `SIN VERIFICAR`. La escribí en el
módulo de al lado y no la instalé aquí.

| # | Sev. | Frontera cerrada |
|---|---|---|
| H-01 | ALTO | Una consulta caída **no autoriza crear**: `Consulta(ok=…)` separa «no hay» de «no pude mirar» |
| H-02 | ALTO | El alta **aborta** si algo quedó sin comprobar; `--force` es la salida explícita |
| H-03 | ALTO | La identidad se decide por **conjuntos**, no por `items[0]`; varias fichas = ambiguo = parar |
| H-04 | ALTO | El respaldo cubre **solo el criterio email**; un NIF sin comprobar levanta igual |
| H-05 | ALTO | Las dos jurisdicciones pasan por `_resolver_colaborador` |
| H-06 | MEDIO | El W-code se **confirma exacto** con `wcode_match`; sin referencia es sin comprobar |
| H-07 | MEDIO | «Nunca lanza» pasa a ser cierto: el `try` cubre el parseo entero |
| H-08 | MEDIO | El NIF se canoniza sin separadores (acotado por medición propia) |
| H-09 | BAJO | Declarado pendiente con su razón: en el alta no hay contrario que consultar |
| H-10 | MEDIO | Los dobles ejercen consulta caída, resultados múltiples y la forma real con `values` |

### Lo que la remediación destapó por su cuenta

- **Mi política inicial era demasiado gruesa.** Al hacer que «sin API key» levantara,
  rompí dos tests que fuerzan **a propósito** el camino legacy sin clave. El respaldo por
  listado completo no es un parche: es una vía alternativa legítima que **sí** cubre el
  criterio email. La política afinada distingue qué criterio quedó sin cubrir, en vez de
  tratar toda incertidumbre como la misma.
- **El leak-guard bloqueó el commit de la remediación**: había usado el **NIF real del
  contrario** como ejemplo en un docstring, escribiéndolo mientras redactaba una nota
  sobre normalización de documentos. Saneado a un valor sintético; el dato medido se
  describe sin transcribirlo.
- **Y un error de edición propio, cazado por un censo:** al reemplazar un rango del
  módulo borré sin querer `_PROP_REFERENCIA`, `DuplicadosExpediente` y
  `buscar_expedientes_duplicados`, que caían dentro del rango. Lo destapó comparar por AST
  las definiciones del fichero contra las de `HEAD` — no el compilador, que seguía verde.
  **Editar por rangos exige censar lo que había dentro.**

### Lo que queda SIN VERIFICAR, declarado

- **Orden aleatorio:** el revisor no tiene `pytest-randomly`. Lo cubre el autor: suite
  completa con semillas **777** y **31337**.
- **Escape de `%` y `_` en `like`:** la dirección puede contener comodines y no se
  escapan. No se ha medido cómo los trata el tenant.
- **Consistencia eventual del CRM** tras una escritura: sigue sin medirse.
