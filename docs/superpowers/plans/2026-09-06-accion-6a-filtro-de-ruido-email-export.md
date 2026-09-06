---
estado: en curso
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

- [ ] **T1** — `clasificar_ruido` y sus cuatro reglas, en `core/email_export.py`. Tests: un mensaje
      por regla que casa + el negativo de cada una (la señal a medias no excluye).
- [ ] **T2** — `parse_headers` extrae `cc` (hoy solo `date, subject, from, to, message-id`).
      Corrección del escéptico, confirmada en `core/email_export.py:74-82`.
- [ ] **T3** — `_build_raw` de `tests/test_email_export.py:27` parametriza `To` y acepta `Cc`
      (hoy fija `To="despacho@tyukhay.legal"` en duro).
- [ ] **T4** — el cableado en el bucle: el excluido no se escribe, no cuenta como duplicado, **y su
      gid no entra en `_exported_ids.json`** (el aserto de reversibilidad).
- [ ] **T5** — `ExportReport.excluidos_ruido` + `resumen()` + evento `email_excluido_ruido`.
- [ ] **T6** — `--sin-filtro-ruido` en `scripts/export_label_emails.py`, cableado hasta
      `export_label(filtrar_ruido=...)`. Default: **filtrar**.
- [ ] **T7** — `MEJORAS #168`: destino externo con nombre de lote → no entra en el M9 del caso y el
      report nombra las dos rutas.
- [ ] **T8** — mutantes, uno por frontera. Como mínimo: (a) invertir el `continue` del filtro;
      (b) quitar el `cc` de `parse_headers`; (c) mover el filtro **detrás** de
      `nuevos_gids.append` (rompe la reversibilidad sin romper la exclusión — el mutante que
      distingue las dos propiedades); (d) cambiar `resolve()` por comparación de nombre en #168.

## 5. Presupuesto de rondas

**Una.** Radio de daño: la pieza **no** decide quién escribe sobre qué copia y **no** puede destruir
datos de cliente — el original vive en Gmail, la exclusión no borra nada y es reversible sin
`--force`. Por la tabla de `CLAUDE.md` §«Cuántas rondas», eso es una ronda sobre el diff.

## 6. Adjudicación de la R1

*(pendiente — se rellena cuando la ronda corra. El acta literal irá a su hermana
`…-accion-6a-filtro-ruido-r1-adversarial-review.md` bajo `docs/superpowers/specs/`; la
ruta se cita aquí cuando exista, porque el guard **G-citas** de
`tests/test_docs_gobernanza.py` comprueba que toda cita a un spec o plan esté en disco —
y tiene razón: una ruta escrita antes de tiempo es una promesa que el índice da por
cumplida.)*
