---
tipo: handoff
estado: historico
creado: 2026-06-18
origen: sesión Cowork (diseño, no toca código)
destino: Claude Code (repo FeesDefender)
consumido_por: "no construido como tal (core/intake_buzon.py inexistente); superado por el flujo de intake vigente (skill intake-expediente + organizar-sala-lectura; T1–T3 resueltos por expedientes-xl)"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# HANDOFF — Buzón de intake universal (skill Cowork `buzon-intake`)

## 1. Objetivo
Una carpeta-buzón donde cualquier abogado suelta uno o varios documentos sin
pensar en su tipo. Una skill de Cowork **clasifica por FUENTE/tipo de entrada**,
enruta cada fichero a la carpeta de fuente que ya existe en `00_Input/`, deja
traza, y **vacía el buzón moviendo (no borrando)** los originales a una papelera
fechada.

## 2. Decisiones cerradas (Nikolai, 2026-06-18)
1. **Eje de clasificación = FUENTE**, no taxonomía temática E&V. La taxonomía
   (Activación, Ofertas, PBC, Facturación, Reclamaciones…) se sigue resolviendo
   aguas abajo en la sala de lectura / `indice_documental.yaml`. **No** se crean
   carpetas temáticas en `00_Input` (respeta la decisión 2026-06-18 de mantener
   la taxonomía en `INDICE.md`, no en carpetas).
2. **"Vaciar" = mover con red de seguridad**: copia al destino con dedup por
   hash + traza en manifest, y el original va a una papelera/`_procesado/`
   fechada. Nada se borra de verdad (respeta add-only / no tocar el crudo).
3. **Skill de Cowork, prompt-driven**, disparable por **cualquier abogado** con
   acceso al expediente y la skill instalada (no Streamlit, no solo Nikolai).

## 3. ⚠️ BLOCKER CRÍTICO (T1) — el conector Drive de Cowork no borra ni mueve
El conector Drive de Cowork **solo soporta `create`** (ni `update` ni `delete`;
modificar un fichero genera un duplicado homónimo). Por tanto, una skill de
Cowork que opere vía el conector **no puede vaciar el buzón** (mover = copiar +
borrar original; el borrado no existe). La decisión 2 y la decisión 3, juntas,
son hoy técnicamente incompatibles sobre Drive.

**Opciones para resolver T1 (elegir con Claude Code):**
- **(A) Buzón en disco local + vaciado por el motor.** La skill Cowork clasifica
  y propone; el movimiento/vaciado real lo ejecuta un módulo local
  (`core/intake_buzon.py`) disparado por Streamlit o CLI, donde sí hay
  `os.replace`/`shutil.move`. Pierde el "cualquier abogado desde Cowork puro".
- **(B) Cowork solo crea copias en destino; el buzón NO se vacía por la skill.**
  El original permanece en el buzón como red de seguridad; un proceso local
  (rclone/`session_close`/Claude Code) reconcilia y archiva los procesados a
  papelera. La skill marca lo procesado con un `_procesado.jsonl` (create-only).
- **(C) Sustituir el conector** por una vía que soporte move (API Drive directa /
  rclone) — fuera del alcance del conector actual.

Recomendación de diseño: **(B)** como MVP (no rompe nada, multiusuario real,
create-only encaja con el conector), con el vaciado físico delegado a un paso
local posterior. Confirmar con Nikolai si el buzón vive en Drive (multiusuario)
o en el árbol local (donde el motor sí puede mover).

## 4. Flujo propuesto
1. Abogado suelta N ficheros (incl. ZIP) en el buzón del expediente.
2. La skill lee cada fichero **en claro** (excepción RGPD §2 ya autorizada:
   "la skill lee todo `00_Input` en claro").
3. **Clasifica por fuente** (tabla §5) con confianza; el residuo ambiguo va a
   `04_Manual/` (cajón comodín) — nunca se adivina.
4. Copia al destino con `nombre_canonico` (`AAAA-MM-DD_descripcion`) + dedup por
   hash + entrada en manifest/`_intake_log.jsonl` + evento de intake.
5. Marca el original como procesado; el vaciado físico según T1.

## 5. Tabla de enrutamiento por fuente (reaprovecha pipelines existentes)
| Señal detectada | Destino | Pipeline que ya existe |
|---|---|---|
| Export de chat WhatsApp (`.txt`/`.zip` iOS/Android) | `02_Whatsapp/` | `core/whatsapp_intake.py` (`analyze`+`deposit_export`) |
| Correo (`.eml`/`.msg` / cuerpo+adjuntos) | `03_Email/` | intake email (Fase B, **pendiente**) |
| Documento descargado del CRM (rama procesal) | `05_CRM/` | `intake_manual.save_file_crm_branch` |
| Transcripción de entrevista (rol+apellido) | `06_Entrevistas/` | **andamiaje muerto** — `[SIGUIENTE-INTAKE-ENTREVISTAS]` |
| Cualquier otro / residuo ambiguo | `04_Manual/` | `intake_manual.save_file` / `extract_zip` |

Nota: dos destinos dependen de trabajo no cerrado (email Fase B; entrevistas
muerto). El MVP puede arrancar con WhatsApp + CRM + Manual y degradar el resto a
`04_Manual` hasta que esos intakes existan.

## 6. Red de seguridad y traza (decisión 2)
- **Dedup por hash sha256 de bytes** (llave canónica, coherente con el catálogo).
- **Manifest / `_intake_log.jsonl`**: origen, destino, fuente detectada,
  confianza, hash, timestamp, actor.
- **Idempotencia**: re-soltar el mismo fichero no duplica (hash ya visto).
- **Papelera fechada** (`00_Input/_buzon_procesado/AAAA-MM-DD/`) en vez de borrado.
- **Gate de confianza**: por debajo del umbral → `04_Manual` + marca "revisar",
  nunca a una fuente equivocada.

## 7. Reconciliación arquitectónica (no romper lo vigente)
- `00_Input` sigue organizado **por fuente**; la **taxonomía temática** permanece
  en `indice_documental.yaml`/`INDICE.md` (sala de lectura aguas abajo).
- **Add-only / no tocar el crudo** se respeta vía mover-a-papelera, no borrar.
- La sala de lectura (`organizar-sala-lectura` / `core/sala_lectura.py`) ya hace
  la clasificación **temática** leyendo desde `00_Input`: este buzón es el paso
  **anterior** (mete bien clasificado por fuente), no lo sustituye.

## 8. Relación con el backlog
- **`MEJORAS #34`** (skill-Cowork multiusuario): esta skill **es** un caso de #34.
  Si el buzón vive en Drive, T1 es exactamente el muro de #34; documentarlo aquí.
- **`[SIGUIENTE-INTAKE-ENTREVISTAS]`** y **email Fase B**: prerrequisitos suaves
  para que el enrutamiento a `06_Entrevistas/` y `03_Email/` no degrade a Manual.
- **`[SIGUIENTE-SALA-UNICA-PLANA]`**: la skill debe respetar que la taxonomía no
  vuelve a las carpetas.

## 9. Decisiones abiertas para Claude Code / Nikolai
- **T1**: ¿buzón en Drive (multiusuario, create-only, vaciado diferido) o en el
  árbol local (vaciado inmediato, pierde Cowork puro)? → §3.
- **T2**: ¿la skill es 100% prompt-driven (clasifica leyendo y llama a los
  intakes existentes) o se apoya en un `core/intake_buzon.py` que orquesta el
  enrutamiento de forma determinista? (recomendado: core determinista + skill que
  solo decide la fuente del residuo dudoso, como en `clasificar_residuo_llm`).
- **T3**: nombre de la skill y ubicación canónica del buzón
  (`00_Input/00_Buzón/` por caso vs buzón global que deduce el expediente).

---
*Generado en sesión Cowork (diseño, sin tocar el repo). Implementación y commit:
Claude Code.*
