# Expediente scratch (caso de trabajo local) — diseño

**Fecha:** 2026-07-14. **Origen:** brainstorming tras la sesión E2E VALERO
(W-02XOR7 / BaRS8): OCR → sala de máquina → refuerzo por visión → audiencia
previa. **Estado:** decisión de arquitectura **aprobada**. **Implementación:**
Cluster B del roadmap post-VALERO (`MEJORAS #59`, entrada
`[SIGUIENTE-INFRA-POST-VALERO]` de `PLAN.md`).

## Problema

FeesDefender asume que todo caso es un **expediente**: carpeta en el Drive del
despacho con estructura fija (`00_Input/`, `01_Procesado/`…) y una ficha de
identidad `00_Input/_caso.md` (`meta`: W-code, partes, juzgado, `tipo_caso`,
`cliente`). Numerosas skills leen esa ficha para decidir su comportamiento —
p. ej. `preparacion-audiencia-previa` comprueba `_caso.md` para activar el modo
Engel & Völkers (terminología propietario/buscador, guardado en
`05_Procedimiento/`, registro en intake).

En la sesión VALERO se procesó un caso real desde una **carpeta suelta del
escritorio**, sin `_caso.md`, forzando `CASOS_ROOT` por variable de entorno y
montando `00_Input/` a mano. Consecuencias: la skill de audiencia previa lo trató
como **civil genérico** (no E&V), hubo que parchear salidas a mano, y no había
custodia atada a un expediente.

## Decisión

Opción **"expediente scratch" híbrida**, frente a las alternativas descartadas:

- *Todo es expediente (abrir-caso siempre):* una sola vía y custodia total, pero
  impone ceremonia y disponibilidad de Drive/CRM para trabajo rápido o pre-alta
  (VALERO era pre-alta, en local).
- *Carpeta suelta de primera clase (`--case-dir` sin ficha):* lo más rápido, pero
  duplica vías de código, deja casos **fuera de custodia** y **no** resuelve la
  detección E&V (el problema del `_caso.md` persiste).

El scratch es un superconjunto: rápido y local como la carpeta suelta, pero con la
ficha mínima que hace que las skills acierten, y **promocionable** a expediente
completo o descartable.

## Diseño

- **Marcador de identidad.** Un comando ligero escribe un `_caso.md` **stub** con
  `meta` mínimo (`id_go`/W-code, partes, `ciudad`, `tipo_caso`, `cliente` = E&V
  por defecto, `estado: scratch`). No toca Drive ni CRM. Reutiliza el escritor de
  `_caso.md` existente (`core/case_manager.py` / `_shared/scaffold_caso.py`).
- **Ubicación y estructura.** Local, bajo una raíz de trabajo; estructura estándar
  (`00_Input/`, `01_Procesado/`). Se apunta con flag **`--case-dir`/`--casos-root`**
  en el pipeline, en lugar del override de entorno de la sesión VALERO.
- **Detección E&V — resuelta de raíz.** Como existe `_caso.md`, todas las skills lo
  detectan como caso E&V sin cambios en ellas: el stub cierra el punto #7 del
  listado.
- **Custodia mínima.** `_intake_log.jsonl` se crea igual (ya lo hace
  `core/intake_log.append_event`); las entradas marcan el estado `scratch` para
  distinguirlo del expediente canónico del Drive.
- **Promoción.** Comando `promover` que sube el scratch a expediente completo del
  Drive (vía la biblioteca checkin/rclone) y da de alta en CRM, reutilizando
  `core/abrir_caso.py`. Idempotente y reentrante.

## Alcance (Cluster B)

1. Comando **crear-scratch** (stub `_caso.md` + estructura local mínima).
2. Flags **`--case-dir`/`--casos-root`** en `scripts/sala_maquina` y orquestadores
   afines (elimina el override de entorno como única vía).
3. Comando **`promover`** scratch → expediente Drive + alta CRM.
4. Detección E&V: **sin código nuevo** en las skills (la resuelve el stub).

## Fuera de alcance

- Los demás clusters del roadmap: A (cobertura/visión, `MEJORAS #58`), C
  (`gen_solicitud`, `#60`), y el backlog D/E/F (`#61-#63`).
- Cambiar la vía única de expediente-en-Drive para casos ya dados de alta.

## Custodia y gobernanza

Un scratch sin promocionar es un caso **fuera del Drive**: el `_intake_log` local
da trazabilidad mínima, pero la custodia canónica exige la promoción. Debe quedar
documentado en `docs/SEGURIDAD_DATOS.md` y `docs/GOBERNANZA_FUENTES_VERDAD.md` que
el estado `scratch` es transitorio y no sustituye al expediente del Drive para
prueba.
