---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-06
---

# Acción 6a — el filtro de ruido deja de vivir solo en prosa

> **Fila 21 de `PLAN.md`, acción 6, sub-pieza (a).** Recorte de la acción 6 del informe de Codex
> «Acciones para mejorar el alta de expedientes» (sesión del 2026-09-04, fichero fechado
> 2026-09-05, sobre `9ec96f7`). Arrastra **`MEJORAS #168`**, que es la misma frontera en el
> escritor del mismo fichero. Elegida por Nikolai el 2026-09-06.

## 1. El disparador, que ya se consumó tres veces

La regla que impide que el correo de administración del despacho entre en el expediente de un
cliente **solo existe como prosa**: `RUNBOOK [APER-38]` y la memoria
`feedback-intake-email-exclusiones`. Nada la ejecuta. Por eso se ha repetido:

| Cuándo | Caso | Qué entró |
|---|---|---|
| 2026-07-13 | W-02XOR7 | facturación del despacho a `Proveedores.ES@`, reenvíos a `mails.repositorio@` |
| 2026-07-21 | W-02VUDR | lo mismo **más** circularización de auditoría y actas CFO+Legal |
| 2026-07-21 | W-02VUDR | y con ellas, adjuntos de **≥8 expedientes ajenos** |

La tercera es la que fija la gravedad y no es «ruido»: los anexos de la circularización de
auditoría llevan **la cartera completa de litigios del despacho**, en curso y resueltos. Depositarla
en el `00_Input` de un caso de E&V la pone delante de quien tenga acceso Drive a ese caso. La
confidencialidad rota ahí es **transversal a todos los clientes**, no solo al de este expediente.

**Root cause, en una línea:** el criterio existe, lo aplica un humano, y el humano no siempre está.

## 2. Qué entra y qué NO — la distinción que gobierna el alcance

`core/email_atomize/contaminacion.py` fija la doctrina de la casa y su docstring la enuncia:

> AVISA, nunca excluye: en un expediente probatorio, descartar en silencio es peor que arrastrar
> ruido — la decisión de borrar es del letrado.

**Eso sigue intacto y esta pieza no lo toca.** Son dos categorías distintas y confundirlas sería el
error:

| Categoría | Qué es | Qué se hace | Quién |
|---|---|---|---|
| **W-code ajeno** en asunto o adjunto | material que *quizá* no sea de este caso | **avisar**; decide el letrado | `contaminacion.detectar_cruce` — **sin cambios** |
| **administración del despacho** | material que **nunca** es prueba de ningún caso, y que trae confidencialidad de terceros | **no escribirlo** | esta pieza |

La segunda no es una decisión nueva: Nikolai la tomó el 2026-07-21 y la fijó en **borrar, ni
siquiera cuarentena** — una carpeta con guion bajo es una convención que respetan las herramientas,
no control de acceso para personas. No escribir es estrictamente más conservador que escribir y
borrar después, y el original sigue en Gmail, que es la fuente de verdad.

**Fuera de esta pieza, con nombre:** el default de `--extraer-adjuntos` (decisión de Nikolai + gate
de export real), el «checklist por fuente» de la acción 6 (sin diseño, se solapa con la 12), y el
colapso de la acción 6 completa. Esto es la sub-pieza (a).

## 3. Diseño

### 3.1 La regla de las reglas

**Una regla de exclusión se define por una señal ESTRUCTURAL —destinatario, cabecera— siempre que
la haya.** Solo se cae al asunto cuando no existe otra señal, y entonces el patrón tiene que ser
específico hasta el punto de que un correo del caso no pueda casarlo por accidente. **Ninguna regla
mira el cuerpo**, por la misma razón que `detectar_cruce` no lo mira: el letrado menciona
facturación y auditoría en su correspondencia con normalidad, así que el cuerpo da ruido y no señal.

### 3.2 La capa pura

```python
def clasificar_ruido(headers: dict[str, str]) -> str | None:
    """El nombre de la regla que excluye este mensaje, o None si es del caso."""
```

Recibe cabeceras ya parseadas, no toca disco, no muta nada — como `contaminacion`. Devuelve el
**nombre** de la regla (no un bool) porque el nombre es el motivo, y el motivo es lo que hace la
exclusión revisable.

Reglas, por orden de fuerza de la señal:

| Nombre | Señal | Por qué |
|---|---|---|
| `facturacion_despacho` | `To`/`Cc` contiene `proveedores.es@engelvoelkers.com` | estructural, cero ambigüedad: es el buzón de facturación de E&V |
| `repositorio_refs_vacias` | `To`/`Cc` contiene `mails.repositorio@gmail.com` **y** el asunto tiene forma de plantilla CRM con `S/R:`/`M/R:`/`Contrario:` vacíos | estructural + confirmación; el destinatario solo no basta |
| `auditoria` | asunto: circularización de auditoría / carta de auditores | sin señal estructural; patrón específico |
| `gobernanza_interna` | asunto: acta de reunión CFO + Legal | ídem |

**El formato de asunto del CRM, verificado en la fuente** (`docs/INTEGRACION_SUDESPACHO.md`, plantilla
GENERICO id 404): `S/R: {ref} · M/R: {num}/{serie} · Cliente: … · Contrario: …`, separador
**« · » (U+00B7)**. Una regex sin ese separador no casa — corrección del escéptico, confirmada.

### 3.3 El cableado

Punto de inserción: [`core/email_export.py:1040`](../../../core/email_export.py), en el bucle de
`export_label`, **justo tras `mid = message_id_of(raw_bytes)`** y **antes** de la lógica de
duplicados y de `_escribe_mensaje`.

Por qué ahí y no antes ni después:

- **antes de `vistos` / `report.duplicados`**: un mensaje excluido no debe contar como duplicado ni
  contaminar el conjunto de Message-ID vistos;
- **antes de `nuevos_gids.append(gid)`**: el gid no entra en `_exported_ids.json`, así que la
  exclusión es **reversible** — una corrida con `--sin-filtro-ruido` lo trae, sin `--force`.

### 3.4 El rastro, que es lo que hace la exclusión revisable

Dos niveles, y el segundo es el que importa:

1. `ExportReport.excluidos_ruido: list[dict]` (gmail_id, asunto, regla) + una línea en `resumen()`.
2. **Un evento `email_excluido_ruido` en `_intake_log.jsonl`** con la lista.

**Desviación consciente del dimensionado del 2026-09-06**, que dejaba el evento «fuera con nombre».
Sin él la propiedad que el informe de Codex pide —«lo excluido tiene motivo y **se puede
revisar**»— no la cumple nadie: la pantalla se pierde y el `.jsonl` no, que es exactamente el
argumento del docstring de `registrar_cierre_v1`. Coste: `intake_log` ya está importado.

### 3.5 `MEJORAS #168` — el destino externo que se cuela en el M9

Misma frontera que `#149` (**el nombre no es la ubicación**) trasladada al escritor: con un `dest`
que no está bajo el `00_Input/` del caso pero cuyo nombre casa `PATRON_LOTE`, `_emit_traza` registra
en el manifiesto **del caso** rutas que no existen en su `00_Input`, y `report.errors == []`.

Remedio: en `export_label`, antes de llamar a `_emit_traza`, verificar **por resultado** que
`dest.resolve()` cae bajo `config.caso_path(case_id).resolve() / "00_Input"`. Si no, no se registra
en el M9 y el report lo dice nombrando **las dos rutas**. Nunca en silencio.

## 4. Tasks (TDD — test primero, rojo visto, luego código)

- [x] **T1** — `clasificar_ruido` y sus cuatro reglas, en `core/email_export.py`. Tests: un mensaje
      por regla que casa + el negativo de cada una (la señal a medias no excluye).
- [x] **T2** — `parse_headers` extrae `cc` (hoy solo `date, subject, from, to, message-id`).
      Corrección del escéptico, confirmada en `core/email_export.py:74-82`.
- [x] **T3** — `_build_raw` de `tests/test_email_export.py:27` parametriza `To` y acepta `Cc`
      (hoy fija `To="despacho@tyukhay.legal"` en duro).
- [x] **T4** — el cableado en el bucle: el excluido no se escribe, no cuenta como duplicado, **y su
      gid no entra en `_exported_ids.json`** (el aserto de reversibilidad).
- [x] **T5** — `ExportReport.excluidos_ruido` + `resumen()` + evento `email_excluido_ruido`.
- [x] **T6** — `--sin-filtro-ruido` en `scripts/export_label_emails.py`, cableado hasta
      `export_label(filtrar_ruido=...)`. Default: **filtrar**.
- [x] **T7** — `MEJORAS #168`: destino externo con nombre de lote → no entra en el M9 del caso y el
      report nombra las dos rutas.
- [x] **T8** — mutantes, uno por frontera. Como mínimo: (a) invertir el `continue` del filtro;
      (b) quitar el `cc` de `parse_headers`; (c) mover el filtro **detrás** de
      `nuevos_gids.append` (rompe la reversibilidad sin romper la exclusión — el mutante que
      distingue las dos propiedades); (d) cambiar `resolve()` por comparación de nombre en #168.

## 5. Presupuesto de rondas

**Una.** Radio de daño: la pieza **no** decide quién escribe sobre qué copia y **no** puede destruir
datos de cliente — el original vive en Gmail, la exclusión no borra nada y es reversible sin
`--force`. Por la tabla de `CLAUDE.md` §«Cuántas rondas», eso es una ronda sobre el diff.

## 6. Adjudicación de la R1 — `NO-SHIP`, 6 hallazgos, **6 confirmados, 0 refutados**

**Revisor:** Codex (CLI 0.153.0-alpha.5, `gpt-5.6-sol`), sobre `727190f..17d9336` en copia externa
`git archive`, solo lectura por construcción — `sha256` de `core/email_export.py` idéntico al abrir
y al cerrar. **Acta literal, con su digest:**
[`…-accion-6a-filtro-ruido-r1-adversarial-review.md`](../specs/2026-09-06-accion-6a-filtro-ruido-r1-adversarial-review.md).

**La ronda valió lo que costó porque el revisor EJECUTÓ.** Corrió 152 tests, los 15 de
`contaminacion`, los 9 mutantes del arnés adaptados a su entorno, **un décimo mutante propio** y 19
sondas adversariales suyas. Tres de los seis hallazgos vienen con el escenario ejecutado y su log.
Ninguno salió de leer el diff.

| # | Sev. | Hallazgo | Adjudicación | Remedio |
|---|---|---|---|---|
| H-01 | ALTO | La exclusión se rodea por `_aplana_anidados` y `_deposita_mensaje_rescatado` | **CONFIRMADO** — verificado en la fuente antes de remediar: `:430` y `:636` escriben sin clasificar | El hijo anidado ya no se extrae; el rescate por enlace filtra; el **padre entra íntegro** y su carga se declara en `ruido_transportado` |
| H-02 | ALTO | El guard acepta destinos para los que `_emit_traza` calcula rutas falsas | **CONFIRMADO** — `_emit_traza` traza contra `dest.parent` (`:1424`) y yo solo comprobaba pertenencia | `_es_lote_del_caso`: **hijo directo** cuyo nombre lógico es su ubicación física |
| H-03 | ALTO | Las regex excluyen asuntos probatorios | **CONFIRMADO** — `\bacta\b.*\bcfo\b` casa a cualquier distancia; `auditor` es prefijo de `auditoría` | Conjunción `cfo`+`legal` a ≤40 caracteres; `auditor(es)?\b` con frontera |
| H-04 | MEDIO | `input_root.parent` no es el caso si `00_Input` es un alias | **CONFIRMADO** | `_raiz_logica_de` separada de `_input_root_de` |
| H-05 | MEDIO | La señal de destinatario es una subcadena, no una dirección | **CONFIRMADO** | `getaddresses` sobre la lista de headers |
| H-06 | MEDIO | El test de dedup no ejerce ninguna colisión | **CONFIRMADO** — y detectado **en paralelo** por el adjudicador | Test reescrito con colisión real + `M10` en el arnés |

### Lo que esta ronda enseña, que vale más que los seis remedios

**1. Remedié el ejemplo y no la frontera. Otra vez.** `MEJORAS #168` reportaba un destino
*totalmente externo*; cerré esa puerta y di la frontera por cerrada. H-02 demuestra que la
propiedad real era otra —«`dest.parent` es el `00_Input` del caso»— y que el destino externo era
**una instancia**, no la clase. Es la séptima aparición documentada de este modo de fallo en esta
casa, y la memoria que lo describe estaba cargada mientras lo cometía. **La pregunta «¿de qué
frontera es esto un ejemplo?» no se hace sola.**

**2. Escribí una afirmación sin medir, en un comentario, para justificar un atajo.** El comentario
de `_va_dirigido_a` decía que comparar por subcadena era seguro porque «un falso positivo no es
realista». No lo medí: era una intuición vestida de razón, en el sitio donde un lector futuro la
leería como un hecho comprobado. El revisor construyó el falso positivo en una línea (H-05). Un
comentario que afirma algo del mundo tiene el mismo deber de prueba que un aserto.

**3. Dos de mis tests pasaban por el camino equivocado, y de dos maneras distintas.**
`test_el_ruido_no_cuenta_como_duplicado` no ejercía nada porque el fixture no tenía colisiones
(H-06). Y el primer fixture de H-01 «demostraba» que el hijo anidado no se extraía cuando lo cierto
es que `add_attachment` con `message/rfc822` **no produce un anidado que `iter_nested_originals`
reconozca**: el test verde decía «el filtro lo paró» y el hecho era «nadie lo detectó». Los dos son
la familia del *instrumento que no puede dar el otro valor*, y ninguno de los dos lo habría
encontrado más cobertura: solo el mutante.

**4. Tres veces seguidas mi expectativa de mutación fue estrecha** (M05, M01, M08). No porque los
mutantes estuvieran mal apuntados, sino porque enumeré el test *obvio* y no todos los que cuelgan
de la propiedad atacada. El arnés lo caza al correr; escribirlo no basta.

### Cobertura declarada

- **`M15` sobrevive y se declara SIN COBERTURA**, en vez de fingirla: cierra la mitad del *alias
  entrante* de H-02 (una junction externa con nombre de lote apuntando dentro) y montarla en un test
  exige privilegios que el CI no tiene. El arnés lo imprime en cada corrida y avisa si algún día
  muere, para retirarlo de la lista.
- **Lo que el revisor declaró SIN VERIFICAR** y por tanto esta ronda no cubre: suite completa, dos
  semillas, servicios externos, corpus real, frecuencia real de falsos positivos, enlaces simbólicos
  distintos de junction NTFS, UNC y condiciones de carrera. Las dos semillas **sí** las corrió el
  autor: 4.748 tests, 0 fallos, 0 errores, 16 `skip`, semillas 777 y 31337.

### Lo que el revisor señaló y NO se remedia aquí, con su porqué

- **El índice de canal marca el `gmail_id` aunque el destino sea externo.** Preexistente, el propio
  revisor lo declara así y no es regresión de este diff. Queda en `MEJORAS #170`.
- **Un fallo del emisor durable deja la operación parcialmente materializada** (fichero escrito,
  índice `ok`, M9 vacío, sin report). El revisor no lo eleva a defecto de política y tiene razón:
  abortar al perder trazabilidad puede ser deliberado. Anotado, no decidido.
- **El render real del asunto del CRM con `M/R` vacío** — `SIN VERIFICAR` por el revisor y por mí:
  haría falta una plantilla renderizada de verdad. Si un volcado al repositorio se colara por ahí,
  el efecto es que **entra** (falso negativo), que es el lado seguro.

**Estado: los seis remediados, arnés 17 mutantes (16 muertos + 1 declarado), suite verde con dos
semillas. Una sola ronda, conforme al §5.**
