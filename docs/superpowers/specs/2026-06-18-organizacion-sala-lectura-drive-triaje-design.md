# Diseño — Sala de lectura por prompt + triaje de viabilidad (Drive del despacho)

**Fecha:** 2026-06-18
**Autor:** Nikolai Tyukhay (decisiones) + Claude Code (diseño)
**Estado:** propuesta para revisión

> **Decisiones cerradas (2026-06-18, sobre expediente real W-02VND1 Tibidabo 8, 61 ficheros):**
> - **Alcance:** la skill `organizar-sala-lectura` procesa **solo `00_Input/01_Drive EV/`** (39 ficheros). `04_Manual` (22) y demás fuentes quedan fuera de esta corrida.
> - **Destino:** `01_Procesado/Sala lectura Drive EV/` (tipo oración), **fuera de `00_Input`** para no ser re-ingerida por `inventory.scan` (rglob) ni pisada por re-pulls. Carpeta propia (por tipo) distinta de la del motor local (`01_Procesado/Sala lectura/`, por fuente) → sin colisión.
> - **Per-fuente** a este nivel (carpeta nombrada por la fuente), no sala unificada — al revés que la disposición *interna*, que es por tipo.
> - Requiere montar la **raíz del expediente** en Cowork (la salida vive fuera de `00_Input`).
> - Esto deroga, para la implementación, la estructura `01_Raw`/`02_Sala lectura` de §3-§4 de abajo (diseño previo).

## 1. Problema y objetivo

Cuando el despacho empieza a estudiar la viabilidad de una posible reclamación
de honorarios de mediación (cliente E&V), el material llega como un **intake
desordenado** en la carpeta del caso del **Drive del despacho** (no el de Engel;
ya se trabaja sobre la copia del despacho). Hoy ordenar y leer ese material exige
el motor local (`core/`: pipeline OCR + `sala_lectura`), que solo Nikolai puede
correr. Un abogado no técnico (p. ej. Paola) no puede.

**Objetivo:** dar a cualquier abogado del despacho **dos prompts (skills)** que
corren en **claude.ai/Cowork** con el conector de Drive — sin instalar nada, sin
`core/`, sin Docling — para:

1. **Organizar** la carpeta cruda en una **sala de lectura** legible, con las
   carpetas y nombres canónicos de E&V.
2. **Triar la viabilidad** leyendo esa sala ya organizada (semáforo + qué falta).

Es la **versión prompt-driven del primer paso de la sala de lectura**, coherente
con el motor local (misma taxonomía, mismos nombres canónicos, mismos índices).

## 2. Alcance

**Dentro:**
- Dos skills independientes (organización · triaje).
- Corren en claude.ai/Cowork sobre el **Drive del despacho**, vía conector de Drive.
- El modelo lee el contenido de cada fichero directamente (sin OCR local).
- No destructivo: se **copia**, el crudo queda intacto.

**Fuera (YAGNI):**
- Anonimización (no aplica a este flujo en la nube; se asume postura Cowork ya aceptada).
- El **informe formal de viabilidad** (sigue siendo la skill `viabilidad-prerelleno`
  + flujo completo sobre el expediente `00_Input`). Esto es un **pre-triaje**.
- Puente para que esta sala alimente luego el expediente formal de FeesDefender.
- **Registro global** (despacho-wide) de organizaciones. Aparcado a backlog; su
  disparador para promoverlo: "no sé qué casos se han organizado/triado".

## 3. Estructura en Drive

Todo dentro de la carpeta del caso en el **Drive del despacho**:

```
<Carpeta del caso (Drive del despacho)>/
├── 01_Raw/                       ← intake crudo, nombres originales, NO se toca
└── 02_Sala lectura/              ← organizado por copia
    ├── INDICE.md                 ← vista por tipo, generado (no editar)
    ├── CRONOLOGIA.md             ← vista por fecha, generado (no editar)
    ├── _MANIFIESTO.md            ← original → canónico → tipo → fecha → checksum
    ├── 00. FOTOS/
    ├── 01. ACTIVACIÓN/
    ├── 03. OFERTAS/
    ├── 04. ARRAS - ARRENDAMIENTOS/
    ├── 05. FACTURACIÓN - FINANZAS/
    ├── 06. PBC/
    ├── 07. RECLAMACIONES/
    ├── 08. PENDIENTE/
    └── _TRIAJE_VIABILIDAD.docx    ← interno; OK aquí (Drive del despacho, E&V no ve)
```

Las carpetas canónicas = `TAXONOMIA_EV` del motor (`core/config.py`). Disposición
**física por tipo** (no por fuente como el motor local), porque el intake de
viabilidad es de **una sola fuente** y agrupar por tipo es lo que ayuda a leer.

## 4. Skill 1 — Organización (`01_Raw → 02_Sala lectura`)

Reutilizable para **cualquier** carpeta desordenada del despacho, sea o no
viabilidad.

**Flujo:**
1. Recibe la carpeta del caso en Drive.
2. Si el crudo está suelto, lo recoge en `01_Raw/` (ver §6, mover vs copiar).
3. Para cada fichero: lee su contenido, decide el **tipo** (una de las 8 categorías
   `TAXONOMIA_EV`; lo ambiguo → `08. PENDIENTE`, no fuerza) y la **fecha** (del
   contenido; subsidiariamente del nombre o metadatos).
4. **Copia** a `02_Sala lectura/<tipo>/` con **nombre canónico**
   `fecha_tipo_descripcion.ext` (igual que `_nombre_canonico` del motor).
   - `descripcion`: slug ≤50 car., **sin PII** (ni nombres, ni DNI, ni direcciones).
5. Genera `INDICE.md` (por tipo, con enlaces y mapeo a nombre original),
   `CRONOLOGIA.md` (por fecha) y `_MANIFIESTO.md` (traza completa). Los tres con
   cabecera *"generado automáticamente — no editar a mano"*.

**Nomenclatura:** `01_Raw` conserva nombres originales; `02_Sala lectura` usa los
canónicos; `INDICE.md`/`_MANIFIESTO.md` mapean original ↔ canónico para no perder
la traza.

## 5. Skill 2 — Triaje de viabilidad

Específica de reclamaciones de honorarios de mediación. Lee la sala **ya
organizada** (más fiable: localiza antes la hoja de encargo, la reclamación, etc.).

**Salida:** `_TRIAJE_VIABILIDAD.docx` con semáforo 🟢/🟡/🔴 y, por cada factor,
veredicto + anclaje a documento (source-locked) o marca de **lo que falta**:
- Nota / hoja de encargo firmada (y legibilidad TRLGDCU si aplica).
- Nexo causal entre la intermediación y la operación cerrada.
- Obligado al pago (propietario / buscador / tercero).
- Prueba de la intermediación efectiva.
- Importe reclamado y base de cálculo.
- Plazos / prescripción.

Cierra con veredicto corto + **qué documentación pedir** para cerrar huecos.
Reutiliza los criterios del cuestionario de viabilidad existente
(`data/_plantillas/cuestionario_viabilidad.yaml`). Es triaje, **no** el informe
formal. No inventa: lo no acreditado se marca como pendiente.

## 6. Decisión técnica abierta (para el plan, no bloquea el diseño)

**¿El conector de Drive mueve ficheros (reparent) o solo copia?**
- Si **mueve:** `01_Raw` se llena moviendo el crudo (queda limpio el caso) y
  `02_Sala lectura` se llena por copia desde `01_Raw`.
- Si **solo copia** (lo observado en el conector de esta sesión): el crudo se queda
  donde esté como `01_Raw` o se copia a él (duplica). A decidir en el plan.

**Recomendación transversal: copiar, no mover, para construir `02_Sala lectura`.**
- Reversible: la clasificación la hace un LLM (falible); el crudo intacto es la red.
- Es la fase de viabilidad: quizá el caso **no** se coge → no reorganizar
  destructivamente antes de decidir.
- Paridad con el motor local (`shutil.copy2`).
- Coste = duplicación modesta de documentos; si el caso avanza y se valida la sala,
  `01_Raw` se puede purgar después.

**Dedup:** si `get_file_metadata` del conector expone `md5Checksum` (Google lo da),
`_MANIFIESTO.md` marca duplicados y no se copia dos veces el mismo hash; si no,
dedup por nombre+tamaño o se omite (a decidir en el plan).

## 7. Constancia / trazabilidad

- **Por caso (incluido):** `_MANIFIESTO.md` (análogo prompt-driven de
  `indice_documental.yaml`) + `INDICE.md`/`CRONOLOGIA.md`, todos con cabecera
  "generado, no editar". Documentan la carpeta creada y los ficheros duplicados.
- **Global / despacho-wide:** **fuera de alcance** (ver §2). Razón añadida: el
  despacho ya abandonó los logs compartidos en Drive por divergencia/duplicados
  (conector solo `create`); un registro global iría al repo o a un store, no a Drive.

## 8. Relación con el motor local

| Aspecto | Motor local (`core/sala_lectura.py`) | Prompt-driven (este diseño) |
|---|---|---|
| Dónde corre | Claude Code local + `core/` + Docling | claude.ai/Cowork, conector Drive |
| Origen | `00_Input/` (local) | `01_Raw/` (Drive del despacho) |
| Disposición física | por **fuente** (`Sala lectura/<fuente>/`) | por **tipo** (`02_Sala lectura/<tipo>/`) |
| Taxonomía / nombres | `TAXONOMIA_EV` / `_nombre_canonico` | **idénticos** |
| Índices | `INDICE.md` (fuente→tipo) / `CRONOLOGIA.md` | `INDICE.md` (por tipo) / `CRONOLOGIA.md` |
| SSOT | `indice_documental.yaml` | `_MANIFIESTO.md` |
| Clasificación | reglas + residuo a worklist resuelta por Claude | el modelo clasifica leyendo contenido |
| Destructivo | no (copia) | no (copia) |

Divergencia deliberada: física por tipo (origen único) y SSOT en Markdown (no hay
`core/` que lea YAML en Cowork). Se preserva el lenguaje común (taxonomía + nombres).

## 9. Errores y casos límite

- **Fichero ilegible** (binario raro, imagen sin texto): a `08. PENDIENTE`, anotado
  en el manifiesto como "no legible".
- **Sin fecha extraíble:** `0000-00-00` en el nombre canónico y "s/f" en índices
  (igual que el motor).
- **Re-ejecución (idempotencia):** la skill detecta `02_Sala lectura` existente y
  no re-duplica lo ya copiado (por nombre canónico + manifiesto); reporta qué saltó.
- **Carpeta enorme:** la skill avisa y procesa por lotes; deja constancia de lo
  cubierto (sin truncado silencioso).

## 10. Pruebas

Skills de Cowork: sin pytest. Verificación = **eval manual** sobre una carpeta de
intake real (o sintética sin PII): comprobar clasificación, nombres canónicos,
índices, manifiesto, idempotencia en segunda corrida, y triaje source-locked
(que marque huecos en vez de inventar). Documentar la eval en el `.skill`.

## 11. Empaquetado / distribución

Ambas skills se autoran en `.claude/skills/` (fuente única del despacho), se
empaquetan con `scripts/package_skill.py` y se importan en el servidor
(Cowork/claude.ai). Heredan el estilo de la casa y, el triaje, la verificación
anclada a fuente, vía `_plantilla-skill` (`requires`). Candidatas a formar parte de
un futuro **plugin "FeesDefender"** (capa de prompts), fuera del alcance de este spec.
