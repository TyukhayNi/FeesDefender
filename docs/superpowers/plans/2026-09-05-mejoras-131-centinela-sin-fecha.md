---
tipo: plan
objeto: "MEJORAS #131 — el centinela «sin fecha» de la sala de lectura es truthy y desactivó en silencio el Paso 1-bis.d"
estado_remediacion: remediado
creado: 2026-09-05
---

# `MEJORAS #131` — un valor que significa «no sé» no puede parecer un valor

> **Qué es esto.** Fila #18 de `PLAN.md`. El defecto no tenía plan propio: aquí viven el diseño en
> una página y la adjudicación de la ronda adversarial, porque el corpus de los guards G7/G8 es
> `docs/superpowers/` y una adjudicación en `MEJORAS_FUTURAS.md` quedaría sin comprobar.
>
> **Una ronda, por radio de daño:** la pieza no destruye datos ni decide quién escribe; degrada
> en silencio el timeline de la sala de lectura. La ronda la hizo **Codex** sobre el diff.

## 1. El defecto, medido

`preclasificar.fecha_de_nombre` devuelve `"0000-00-00"` cuando el nombre no lleva fecha. Esa
cadena va en los nombres canónicos y en la columna `fecha` del manifiesto, así que es **no vacía**
y, por tanto, *truthy*. En la sala de lectura de W-02X1WJ (2026-09-01) el Paso 1-bis.d de la skill
—consultar el espejo MD de todo binario opaco sin fecha ANTES de escribir `0000-00-00`, el paso
que la skill marca como no opcional— se implementó con `[f for f in filas if not f["fecha"] and
f["ext"] in OPACOS]`: **0 candidatos de 47**, paso desactivado, informe diciendo «0 sin fecha».
Corregido a mano: 47 candidatos, 27 fechas recuperadas.

## 2. La decisión

Dos vías, las dos en la entrada original: cambiar el tipo (`None`) o exportar la pregunta. Se
elige **exportar la pregunta**: el centinela sigue siendo una cadena porque tres consumidores
la escriben tal cual (nombres canónicos, manifiesto, `email_export._fecha_iso`), y cambiar el
tipo obligaría a tocarlos a todos con el riesgo simétrico (un `None` formateado como `"None"` en
un nombre). Lo que se cierra es que **la pregunta «¿tiene fecha?» viva una vez, en código, y la
skill la llame** en vez de reescribirla.

`scripts/preclasificar.py` (skill `organizar-sala-lectura`, v1.15): `SIN_FECHA` público,
`tiene_fecha(valor)` (False para `None`, vacío, `SIN_FECHA` con o sin sufijo, y fechas
aproximadas `(*)`; **no valida calendario**, y lo dice) y `candidatos_sin_fecha(filas)` (binarios
opacos sin fecha cierta, las filas mismas y en orden). El Paso 1-bis.d del `SKILL.md` llama al
helper; un guard exige la cita.

## 3. Tests y mutantes

`tests/test_preclasificar_sala_lectura.py`, bloque «MEJORAS #131»: el centinela es público y
truthy y `tiene_fecha` lo reconoce; el helper devuelve exactamente los opacos sin fecha frente al
filtro a mano que devolvía 1 de 4; la skill cita el helper; y, tras la R1: el helper acepta las
filas de cualquier etapa y falla ruidoso sin ruta; las imágenes opacas son las que la sala de
máquina convierte (guard contra `core.sala_maquina._EXTS_IMAGEN`); `tiene_fecha` no valida
calendario pero sí ausencia. **Mutantes: 13 muertos y un control negativo verde** (paráfrasis
inocua del paso), detalle en el §4.

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-05) — REQUIERE-REVISION, remediado

- **Objeto revisado:** el diff `f54bd5a..2f94bac` (PR #291)
- **Ronda:** 1 (diff) — la única, por radio de daño
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-05-mejoras-131-r1-adversarial-review.md`
- **Hallazgos:** 6 — 4 MEDIOS, 2 BAJOS; **6 confirmados, 0 refutados** (2 preexistentes fuera de alcance)
- **Remediado en:** commit `8dbcda7` (PR #291)

**Independencia: plena** — revisor Codex (`gpt-6-astra`), adjudicador Claude Code. Cada hallazgo
contrastado contra la fuente; lo que reproduje está en el §2 del acta.

| # | Sev. | Hallazgo (frontera, no ejemplo) | Veredicto | Remedio |
|---|---|---|---|---|
| H-01 | MEDIO | El helper solo miraba `nombre_canonico`/`ruta_original`; las filas del Paso 1 llevan `ruta`/`nombre` → **0 candidatos en silencio**, el mismo defecto que venía a arreglar | ✅ confirmado | `_CLAVES_RUTA` con las claves de cada etapa; fila sin ninguna → `ValueError`; tupla → `TypeError`. El `SKILL.md` dice qué filas pasar y que el fallo es ruidoso |
| H-02 | MEDIO | `heif` faltaba en `_EXT_OPACAS` aunque el repo lo convierte | ✅ confirmado | añadido, y la frontera contratada: guard `_EXTS_IMAGEN` del core ⊆ opacas de la skill |
| H-03 | MEDIO | El guard sobre el `SKILL.md` prometía «no vuelve al `not`» y solo garantiza la cita; anclado a la redacción literal («TODO») daba rojo por una paráfrasis inocua | ✅ confirmado | guard anclado al Paso 1-bis y al helper, con docstring que dice lo que garantiza y lo que no; CHANGELOG corregido; m07 pasa a control negativo |
| H-04 | BAJO | «fecha real» y «ÚNICA forma correcta» excedían el contrato (no valida calendario; `indices_desde_manifiesto` implementa la misma política) | ✅ confirmado | docstring preciso; test `2025-02-31` → True, declarado |
| H-05 | BAJO | El motor **deprecado** `core/sala_lectura.py` ordena `0000-00-00` y `(*)` por delante y pierde la marca — preexistente | ✅ confirmado, **no remediado** | fuera de alcance (motor retirado); anotado en `MEJORAS #169` |
| H-06 | MEDIO | `email_atomize/vistas._seleccion_tematica` compara el centinela lexicográficamente en rangos de fechas: entra con `hasta`, sale con `desde` — preexistente | ✅ confirmado, **no remediado** | fuera de alcance de la skill; `MEJORAS #169` con la medición y el remedio (clave de orden única + cubo `sin_fecha`) |

**Supervivientes del revisor, cerrados:** m08 (extensión sin `lower`), m09 (sin `heic`), m10
(sin el fallback de clave), m13 (sin `strip`), m14 (igualdad en vez de prefijo) tenían cobertura
ausente; ahora cada uno muere por su test. **m06** (una instrucción contraria escrita al lado de
la cita) **sobrevive por diseño** y se declara: un guard de subcadenas garantiza la cita, no la
semántica, y eso es lo que el docstring dice ahora.

**Cobertura de la remediación: sin revisión adversarial** (una ronda por radio de daño); los
contraejemplos del revisor se reprodujeron contra el código remediado (fila del Paso 1, HEIF,
paráfrasis del paso).
