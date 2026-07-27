# Revisión adversarial adjudicada — cableado atomize en sala de máquina

> **Spec revisada:** `2026-07-27-cableado-atomize-sala-maquina-design.md` (rev. 1 → rev. 2).
> **Revisores:** Codex (independiente) + pasada propia de Claude (no independiente: autor de la
> spec). **`agy` NO se ejecutó** — cupo individual de Gemini agotado (reset ~36 h). No hay revisión
> de Gemini y no se sustituye por ninguna otra.
> **Adjudicación:** Claude, verificando cada hallazgo contra el código. Ni la convergencia de dos
> revisores ni una cita de línea con buena pinta eximen de abrir el fichero.

## Veredicto

**Revisión sustancial de la spec, no rediseño.** Codex propuso REWORK; no se acepta como veredicto
global. La decisión de fondo —dónde vive el disparo: `apply`, antes de construir el plan de OCR—
**sobrevivió intacta a las dos revisiones**: ningún hallazgo la ataca, y nadie propuso mejor sitio.
Lo que se cayó fue (a) una promesa sobrepasada, (b) el criterio de enumeración, (c) el contrato de
fallo y de evento.

El defecto estructural real es **H-09**: los objetivos «no tocar motor» y «`Emails/` siempre fresco»
son incompatibles. Es defecto del autor de la spec, no del revisor.

## El hallazgo de mayor valor

**`--extraer-adjuntos` deja ciego al atomizador.** Bug latente en `main`, ajeno a esta spec,
encontrado por Codex y verificado en sus dos patas:

- `iter_avistamientos` enumera con `base.glob("*.eml")`, no recursivo (`extract.py:53`).
- `_escribe_mensaje` con `extract_attachments=True` y adjuntos presentes escribe el `.eml` en una
  **subcarpeta** (`email_export.py:1123-1132`).

Los mensajes con adjuntos quedan invisibles para el motor. Sin error y sin nota. Contradice cómo
`PLAN.md` y `MEJORAS #68` presentan `07b0377` («la mitad resuelta» de #68.a): es una trampa armada.
Bloquea la casilla 3 del bloque. → `MEJORAS #98`.

## Tabla de adjudicación

| Hallazgo | Origen | Severidad adjudicada | Veredicto | Dónde se remedia |
|---|---|---|---|---|
| Enumeración `rglob` ≠ `glob` del motor | Codex H-01 | ALTO | **Aceptado y escalado** | §1.2, §4.1, §4.2 + `#98` |
| No-op deja salida rancia | Codex H-02 | ALTO (urgencia menor) | **Aceptado** | §4.3, tabla de decisión |
| Sin poda de `adjuntos/` | Codex H-03 | ALTO | **Aceptado** | §9.2 → `#99` |
| `identidades.yaml` inválido indistinguible de no-op | Codex H-04 | MEDIO | **Aceptado con matiz** | §4.4, §4.5 |
| Publicación no transaccional / IDs renumerados | Codex H-05 + propio H-01 | ALTO | **Aceptado (convergencia)** | §4.4, §9.3 → `#99` |
| Concurrencia intake / dos `apply` | Codex H-06 | **MEDIO** (rebajado de ALTO) | **Aceptado, severidad corregida** | §9.4 → `#99` |
| Evento sin `status` | Codex H-07 | MEDIO | **Aceptado** | §4.5 |
| Los 7 tests pasan con fallo real | Codex H-08 + propio H-03 | ALTO | **Aceptado** | §6, tests 6 y 9-11 |
| «No tocar motor» vs. «siempre fresco» | Codex H-09 | ALTO | **Aceptado — es el veredicto** | §2, rebaja explícita |
| Resolución repetida del caso | Codex H-10 | **BAJO** (rebajado de MEDIO) | **Aceptado, remedio adoptado** | §4.6 |
| Mitigación falsa sobre consumidores del log | Codex H-11 | BAJO | **Aceptado** | §8, fila corregida |
| Conteo de `.eml` duplicado en dos call sites | Propio H-04 | MEDIO | **Aceptado** | §4.1, predicado en el core |
| Duplicación garantizada de representación | Propio H-06 | BAJO | **Aceptado** | Nota en §9 / `#86` |

## Evidencia verificada (adjudicación, no confianza)

Comprobado abriendo el código, no aceptado por la cita del revisor:

- `extract.py:53` — `base.glob("*.eml")`, no recursivo. **Confirmado.**
- `email_export.py:1123-1132` — subcarpeta cuando `adjuntos and extract_attachments`. **Confirmado
  en el código**, no solo en el docstring.
- `pipeline.py:117-124` — la poda cubre solo `mensajes/*.md`. **Confirmado.**
- `descubrir.py:13` — recorre todos los sidecars sin contrastar `INDICE_ADJUNTOS.md`. **Confirmado.**
- `ids.py:37-46`, `93-96`, `104-107` — contador incremental, `write_text` sin temporal, JSON
  truncado → registro vacío en silencio. **Confirmado.**
- `pipeline.py:170` — `reg.save()` es la última línea. **Confirmado.**
- `abrir_caso.py:159-166` — `_shas_en_log` recorre **todos** los eventos sin filtrar. **Confirmado**:
  la mitigación de la rev. 1 era factualmente falsa.
- `test_intake_log.py:334` — `assert len(il.INTAKE_EVENTS) == 26`. **Confirmado**: añadir el evento
  rompe el test.
- `sala_maquina.py:645` (`:551` en el momento de la revisión; desplazado por el PR #147),
  `extractor.py:173-194`, `intake_log.py:168-172`, `config.py:547-550`,
  `pipeline.py:31-42`, `pipeline.py:281`, `pipeline.py:88-89` — afirmaciones de la rev. 1 que
  **resultaron correctas**.

### Refutación del §1.1: fallida, con matiz aceptado

Se intentó refutar por ambos revisores. **No existe camino** por el que el cableado haga que
`sm.ejecutar` cubra `01_Procesado/Emails/adjuntos`: las 18 escrituras del paquete
(`write_text|write_bytes|unlink|mkdir`) caen todas bajo `out_dir`, e `inventariar` solo recorre
`00_Input`. La afirmación central se sostiene.

Matiz aceptado de Codex: mostrar la contaminación **antes** del OCR permite abortar, limpiar y
reintentar → mejora indirecta de la corrección del corpus. No es cobertura automática. Incorporado
al §1.1.

## Errores e imprecisiones de los revisores

Registrados porque condicionan cuánto se puede copiar de una revisión sin comprobarla:

**Codex — cuatro citas de línea desplazadas** (apuntan a la función correcta, no a la línea):
`cargar_identidades` está en `pipeline.py:87`, no 82; el `glob` en `extract.py:53`, no 51; el assert
de eventos en `test_intake_log.py:334`, no 328; el `except JSONDecodeError` en `ids.py:104-107`, no
99. Navegación imprecisa, no invención — pero ninguna se copió a la spec sin verificar.

**Codex — H-06 inflado.** ALTO no está justificado: sin pérdida de datos, autocurable en la corrida
siguiente, y la parte que sí muerde (carrera de IDs) ya estaba contada en H-05. Rebajado a MEDIO.

**Codex — H-04 conflaciona dos casos.** Si el motor lanza en `cargar_identidades` (`pipeline.py:87`,
antes del `mkdir`) **no se ha mutado nada**: es el caso benigno. El peligroso es lanzar a media
escritura. El remedio cubre ambos, pero la distinción importa para la severidad.

**Codex — no verificó** el baseline `2424/0/0/76` ni la medición viva sobre W-02VND1. Lo declara
honestamente, y hace bien: ejecutar pytest habría violado el solo-lectura que se le pidió.

**Claude — pasada no independiente.** Es el autor de la spec. Su H-01 (renumeración de IDs) convergió
con el H-05 de Codex de forma independiente, lo que sube la confianza en ese hallazgo concreto; pero
no cubrió la enumeración ni la poda de adjuntos, que son los dos hallazgos de mayor valor de la
sesión y salieron de Codex. Lección repetida: el revisor externo mira donde el autor no piensa
mirar.

**Cobertura ausente: `agy`.** No corrió. No se sabe qué habría encontrado. No se registra como
«revisado por tres» nada que solo vieron dos.
