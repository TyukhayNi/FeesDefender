# Plantilla de skill del despacho

Punto de partida para que las skills **nuevas** nazcan con la misma anatomía. No es
una skill ejecutable: es un molde. Carpeta ignorada por `sync_skill_helpers.py`
(solo sincroniza `_shared/*.py`) y por el empaquetado.

## Cómo usarla

1. Copia esta carpeta a `.claude/skills/<nombre-de-la-skill>/`.
2. Renombra y rellena el frontmatter de `SKILL.md` (`name` == nombre de carpeta).
3. Elige los **ejes** y añade los **módulos** que correspondan (abajo).
4. Borra los comentarios guía y este `_LEEME.md`.
5. Comprueba conformidad: `python scripts/validate_skills.py` (modo aviso).

## Ejes de clasificación

- **`rol`** — dos familias más un eje transversal:
  - **Trabajo jurídico:** `fase` (un momento del litigio: preparación, audiencia previa,
    juicio) · `output` (produce un entregable concreto, p. ej. escritos `.docx`) ·
    `cliente` (aporta contexto de un cliente, p. ej. Engel & Völkers).
  - **Pipeline de datos del expediente:** `input` (mete datos crudos al expediente, p. ej.
    `intake-expediente`, `exportar-correos-etiqueta`; simétrico de `output`) · `procesado`
    (transforma el intake en artefactos internos, p. ej. `organizar-sala-maquina`,
    `organizar-sala-lectura`).
  - **Transversal a ambas:** `transversal` (comportamiento que cruza asuntos, p. ej.
    verificación, estilo).

  (Taxonomía a revalidar al construir el grafo de ecosistema — `docs/MEJORAS_FUTURAS.md` #50.)
- **`naturaleza`**: `atomica` (hace una cosa) · `orquestadora` (coordina otras
  skills; rellena entonces `orchestrates`).

## Módulos (añade según rol/naturaleza)

| Módulo | Cuándo | Qué añade |
|---|---|---|
| **Núcleo** | siempre | `SKILL.md`, `CHANGELOG.md`, `.gitignore`. Añade `LICENSE` solo si la licencia lo exige (p. ej. AGPL de tercero). |
| **OPERACIÓN** | la skill produce outputs en un expediente | helpers canónicos en `scripts/` (`registrar_outputs.py`, `registrar_uso.py`, `programar_revision.py`, `scaffold_caso.py`) vía `scripts/sync_skill_helpers.py`, y el bucle de `docs/MEJORA_CONTINUA_SKILLS.md`. Añade la carpeta al tuple `_TARGETS` del sincronizador. |
| **EVOLUCIÓN** | la skill quiere mejora asistida por uso | `EVOLUCION.md` con las cinco fases. |
| **JURISPRUDENCIA + COSECHA** | la skill cita y cosecha jurisprudencia | índice por ECLI + consolidador + `drive_config.json` (hoy solo en `oposicion-alegacion-nulidad`). |
| **ESTILO + VERIFICACIÓN** | la skill **redacta texto** y/o **maneja hechos, cifras o citas** | Texto: puntero al contrato `data/_estilo/contrato_estilo.md` (capa 1) en la fase de redacción + `pase-de-estilo` final (capa 2). Hechos/citas: encadena con `verificacion-anclada-fuente` (source-locked). Declara ambos en `metadata.requires`. No aplica a skills que no redactan ni citan (descarga, hoja de cálculo, scaffolding). |

`verificacion-anclada-fuente` (transversal) y `engel-volkers` (cliente) no llevan
módulos OPERACIÓN/EVOLUCIÓN: solo núcleo + identidad.

## Telemetría

Si añades el módulo OPERACIÓN, la telemetría usa **`registrar_uso.py`** (helper
canónico) y escribe en el store central `data/_skill_logs/<skill>/` (git-ignorado,
fuera del `.skill`). No crees loggers propios por skill: evita la doble telemetría.
