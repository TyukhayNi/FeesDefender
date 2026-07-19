# Prompt de arranque — BUILD de la Cronología Unificada de Prueba (Claude Code)

> Cópialo tal cual en Claude Code, abierto en el repo `C:\Users\tnm33\Dev\FeesDefender`.

---

Vamos a **construir** la Cronología Unificada de Prueba en `core/`. El **diseño está cerrado** (8 fases, 0–7); hoy NO se diseña, se construye. Banco de pruebas: expediente W-02VND1 ([inmueble]).

## Antes de tocar nada

1. Lee `STATUS.md`, `PLAN.md` y `CLAUDE.md` (apertura de sesión estándar: `git log --oneline -5`, `python -m pytest -q --tb=no`).
2. Lee el spec de diseño **`PLAN_CRONOLOGIA_UNIFICADA.md` v7** (lo he dejado en el repo; si no está, pídemelo — vive en el outputs de Cowork). Es la fuente única del diseño: 12 secciones, decisiones D1–D6 (esquema), F3.D1–D5 (correlación), F4.D1–D2 (tiempo), F5.D1–D2 (ingesta), F6.D1–D2 (vistas/custodia), F7.D1 (piloto).
3. Material build-ready complementario (handoffs de stress-test, en el outputs de Cowork): `handoff_F3D4`/`F3D5` (pseudocódigo del 🟢🟡🔴 y de la contradicción), `handoff_F4D1`/`F4D2`, `handoff_F5D1`/`F5D2`, `handoff_F6D1`. No re-derives lo que ya está ahí.

## Reglas de diseño que el build NO puede romper (resumen; el detalle está en el spec)

- **Modelo B:** el átomo es un acto datado anclado a un registro de fuente; nunca un hecho inferido. La interpretación vive en la capa derivada (`HECHOS_X.md`, semáforo 🟢🟡🔴), separada.
- **Tres capas con frontera tajante (F5.D1):** atomizador (bytes→átomos, por fuente) · adaptador (átomo→ficha de acto del esquema común, emite tokens de actor crudos sin resolver) · **núcleo agnóstico** (asigna EVT-id por `(fuente, clave_natural)`, resuelve identidad, deduplica, correlaciona, ordena en el tiempo, enlaza, genera vistas). El adaptador NUNCA asigna EVT-id, crea enlaces, correlaciona ni resuelve identidad.
- **Staging** (F5.D2): salida del adaptador = actos normalizados sin resolver en `01_Procesado/Cronologia/_staging/<fuente>.jsonl`; el núcleo opera siempre sobre la **unión** multi-fuente.
- **Correlación ≠ fusión:** dentro de una fuente se deduplica; entre fuentes se correlaciona (enlace), nunca se funde. Corroboración de contenido (orígenes independientes) ≠ circulación (mismo artefacto por varios canales).
- **Tiempo (F4):** fecha en EDTF; orden **parcial** (antes/después/contiene/contenido_en/indeterminado) con propagación segura que NO muta el `cuando.fecha` canónico.
- **Idempotencia:** libro `huella→EVT-id` congelado; re-ejecutar no renumera; upgrade conserva id; split de un átomo ya citado → revisión humana.
- **Custodia:** almacén/registro/vistas = work-product; la prueba son las fuentes apuntadas. Anclaje siempre al crudo de `00_Input` + hash de intake.
- **Intocables:** el **motor de correo está congelado** (es el primer adaptador, no se modifica); **`00_Input` es inmutable**; **`90_Notas personales` no se lee, escribe, indexa NI lista** (prohibición absoluta, decisión de Nikolai).
- Reglas del repo (CLAUDE.md): cambios en `core/` siempre con tests en `tests/`; Windows/PowerShell; UTF-8 sin BOM; terminología propietario/buscador; NIG fuera de payloads.

## Orden de build (incremental, con tests en cada paso)

1. **Motor de correo (primer atomizador).** Su diseño está cerrado y congelado desde el 24/06 (ver memoria del proyecto / `caso_w02vnd1_atomizacion_email`): atomiza `00_Input/03_Email` a `01_Procesado/Emails/` (`mensajes/*.md` + `corpus.jsonl` + `_registro.json` + índices + `adjuntos/`). Constrúyelo en `core/` con su suite. Primero una **pasada de medición** sobre datos reales para validar la huella de dedup antes de construir todo.
2. **Esqueleto del núcleo agnóstico.** Ficha del acto (esquema común, §3.1 del spec), `_registro_cronologia.json` (libro `huella→EVT-id`, IDs `EVT-/ATT-/ENL-/HD-/ACT-/HIP-`), resolución de identidad contra `identidades.yaml`, contrato de staging. Tests de idempotencia y de la frontera adaptador↔núcleo.
3. **Adaptador-lector de correo** (solo lectura sobre la salida del motor congelado → fichas de acto en staging). Campos que el motor no expone → default determinista (no inferencia), nunca reabrir el motor.
4. **Atomizador + adaptador de WhatsApp** sobre las 4 conversaciones de `00_Input/02_Whatsapp` (formato iOS `[D/M/AA, HH:MM:SS] Emisor: texto`, adjuntos inline ya renombrados). Es la pieza nueva del piloto.
5. **Piloto end-to-end (correo + WhatsApp)** → `CRONOLOGIA_ACTOS` + dossier del velo. Criterio de éxito (F7.D1), tres hechos-test del caso:
   - correlación-no-fusión del documento que viaja por dos canales (TITULAR REAL 2021 en Drive + WA-PersonaSiete; Capex; Planos) → corroboración/circulación bien etiquetadas;
   - identidad PersonaTres/PersonaTres unificada + ficha CRM "PersonaUno" resuelta como **PersonaTres por teléfono** (no por el rótulo);
   - punto controvertido del precio ("no negociable 21,3M") y la ruptura del 14/08/2025 ("no os reconozco") marcados **sin resolver**.

## Cómo arrancar

No empieces a picar código aún. Primero:
1. Confirma que has leído `STATUS.md`/`PLAN.md`/`CLAUDE.md` y el spec v7.
2. Resúmeme en pocas líneas el estado del repo y si el motor de correo ya tiene algo construido o parte de cero.
3. Propón el **plan de build del paso 1 (motor de correo)** con su lista de tests, para mi visto bueno, antes de escribir.
4. Anota el arranque en `PLAN.md` (referencia al spec v7) y deja `STATUS.md` al día al cerrar sesión.
