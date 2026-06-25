# Diseño — Motor de atomización de correo, Fase 3 (capa de caso)

> **Estado:** diseño aprobado por Nikolai 2026-06-25 (brainstorming).
> **Alcance:** capa ESPECÍFICA de caso sobre el motor genérico `core/email_atomize/`.
> **Banco de pruebas:** W-02VND1 (`BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta`).
> **Fuera de alcance (spec separado posterior):** fix de recall MSG-00018, OCR de adjuntos.
> **Disciplina:** brainstorming → spec → plan → TDD → verificación en vivo + revisión adversarial.

## 1. Contexto

Las Fases 1 (Capa A — MIME) y 2 (Layer B — reconstrucción de autoría inline) del motor
`core/email_atomize/` están completas y en `origin/main`. El motor lee
`<caso>/00_Input/03_Email/*.eml` y produce en `<caso>/01_Procesado/Emails/`: `mensajes/` (1 `.md`
por mensaje atómico), `adjuntos/`, `corpus.jsonl`, `_registro.json` (IDs congelados),
`CORREOS_LECTURA.md`, `INDICE_ADJUNTOS.md`, `_revision/{cola,casi_duplicados,del_burgo}.md`.

Hoy dos sets de identidades viven **sembrados en código** en `core/email_atomize/inline.py`:

```python
IDENTIDADES_VIGILADAS:  set[str] = {"per01a@example.invalid", "per01c@example.invalid"}
IDENTIDADES_CANDIDATAS: set[str] = {"per01b@example.invalid"}
```

Son datos del caso W-02VND1 dentro del motor genérico. La Fase 3 los saca a configuración de
caso y añade dos capacidades de caso que consumen las salidas congeladas del motor:
**vistas temáticas** y **entregas selladas**.

Fin último del proyecto: recuperar la autoría enterrada de **PersonaUno** para sostener el
levantamiento del velo de Tibidabo 8 S.L.

## 2. Objetivos y no-objetivos

**Objetivos.**
1. Sacar las identidades del caso a `<caso>/identidades.yaml` (input curado a mano; el motor solo
   lo lee). Sin fichero = comportamiento genérico (sets vacíos = hoy). Incluir unificación de
   persona (varias direcciones → una identidad).
2. Vistas temáticas (`dossier_del_burgo`, `nexo_causal`) dirigidas por `<caso>/vistas.yaml` +
   `identidades.yaml`, como artefacto de solo-lectura que **no muta** ningún `.md`.
3. `_entregas/` selladas: snapshot congelado del set entregable + manifiesto de hashes
   (`_SELLO.md`) para cadena de custodia.

**No-objetivos (spec/plan separados o posteriores).**
- Fix de recall MSG-00018 (reenvíos Outlook-escritorio ES sin contenedor de cita; etiqueta
  `"Enviado el:"`; bloque Outlook plano como estructural). Es ingeniería del **motor genérico**
  (regex/segmentación/fechas) y puede rebaselinar hashes legítimamente; se aísla.
- OCR de adjuntos.
- Modelo de actor rico de la Cronología Unificada (roles con vigencia, calificaciones del velo).
  Esta fase solo deja el terreno forward-compatible con `rol`/`notas` informativos.

## 3. Reglas duras (verificar tras cada cambio)

- **Los 277 `.md` de Capa A quedan BYTE-IDÉNTICOS.** Comparar hashes antes/después. Con
  `identidades.yaml` del piloto = datos de hoy, Layer B produce salida idéntica y Capa A no se
  toca. Vistas y entregas son ficheros nuevos en subdirectorios nuevos → no alteran bytes
  existentes.
- **IDs congelados** en `_registro.json`: nunca renumerar.
- **Cero misatribución:** un remitente se afirma solo desde cabecera verificada. Esta fase no
  relaja ninguna guarda de Layer B.
- **El motor es genérico:** lo del caso entra SOLO por config (`identidades.yaml` / `vistas.yaml`),
  nunca hardcodeado.
- **`00_Input/` inmutable.** Pipeline idempotente (las vistas se regeneran deterministas; las
  entregas son append-only por diseño).

## 4. Configuración de caso

Dos ficheros YAML curados a mano en la **raíz del caso** (`<caso>/`), junto a `_caso.md`. El motor
SOLO los lee; nunca los escribe ni los regenera. Ubicación case-wide elegida porque la Cronología
Unificada (D5) "formaliza `identidades.yaml`" como registro de actores de todo el expediente, y
porque un input curado no debe vivir en `01_Procesado/` (carpeta de artefactos GENERADOS).
Serialización: **PyYAML** (`yaml.safe_load`), estándar del repo.

### 4.1 `identidades.yaml`

```yaml
# identidades.yaml — registro de actores del caso (curado a mano; el motor SOLO lee).
# Sin este fichero, el motor se comporta de forma genérica (sets vacíos = comportamiento actual).
version: 1
caso: "W-02VND1"                # informativo

personas:
  - id: persona_uno          # slug estable y opaco; lo usan las vistas para agrupar
    nombre: "PersonaUno"
    vigilada: true               # doble control probatorio: toda cita suya → _revision/del_burgo.md
    rol: "tesis: administrador de hecho (levantamiento del velo)"   # OPCIONAL, informativo
    direcciones:
      - { email: per01a@example.invalid,            estado: confirmada }
      - { email: per01c@example.invalid,                 estado: confirmada }
      - { email: per01b@example.invalid,  estado: candidata }    # nunca alta: tope `media`

  - id: persona_dos
    nombre: "PersonaDos"
    vigilada: false
    rol: "letrado contraparte (despacho PersonaDos)"
    direcciones:
      - { email: ignacio@despacho-ab.example, estado: confirmada }
    notas: "PERSONA DISTINTA de PersonaUno — nunca fundir."
```

**Campos.** Requeridos (consume el motor): `id`, `nombre`, `vigilada` (bool), `direcciones`
(lista de `{email, estado}`, `estado ∈ {confirmada, candidata}`). Opcionales e informativos (el
motor los IGNORA): `rol`, `notas`, `version`, `caso`. Forward-compatible con la Cronología D5.

**Sets derivados (semántica idéntica a hoy):**
- `vigiladas = { email | persona.vigilada == true AND direccion.estado == "confirmada" }`
- `candidatas = { email | direccion.estado == "candidata" }`
- `mapa de unificación: email (lower) → persona.id` para agrupar en vistas.

**Invariantes.**
- Email normalizado a minúsculas al cargar (coherente con `inline._addr_o_nombre`, que ya
  devuelve `addr.lower()`).
- Un email no puede pertenecer a dos personas distintas (validar al cargar; error explícito).
- Personas distintas **nunca** se funden (la unificación agrupa por `persona.id`, no por
  apellido/nombre): `ignacio@despacho-ab.example` jamás cuelga de `persona_uno`.
- Con los datos del piloto, los sets derivados reproducen exactamente
  `vigiladas={per01a@example.invalid, per01c@example.invalid}`, `candidatas={per01b@example.invalid}`.

### 4.2 `vistas.yaml`

```yaml
version: 1
vistas:
  - id: dossier_del_burgo
    titulo: "Dossier — PersonaUno"
    tipo: persona                 # AUTO: mensajes de/para/cc de la persona, orden cronológico
    persona: persona_uno      # → mapa de unificación de identidades.yaml
  - id: nexo_causal
    titulo: "Nexo causal — Tibidabo 8"
    tipo: tematica                # CURADO por el letrado
    palabras_clave: ["tibidabo", "arras", "encargo", "comisión"]   # en asunto+cuerpo, ascii/casefold
    incluye_msg: ["MSG-00042"]    # forzar dentro (override gana)
    excluye_msg: ["MSG-00100"]    # forzar fuera (override gana)
    desde: "2024-01-01"           # opcional, ISO; filtra por fecha_iso del mensaje
    hasta: "2024-12-31"           # opcional, ISO
```

Sin `vistas.yaml` → no se genera ninguna vista. El motor ships **tipos de vista genéricos**; el
caso elige cuáles y sus parámetros (regla dura: nada de caso hardcodeado).

## 5. Arquitectura de módulos (en `core/email_atomize/`)

### 5.1 `identidades.py` (nuevo)
- `@dataclass Persona`: `id`, `nombre`, `vigilada`, `direcciones: list[(email, estado)]`,
  `rol=""`, `notas=""`.
- `@dataclass Identidades`: `vigiladas: frozenset[str]`, `candidatas: frozenset[str]`,
  `personas: dict[id, Persona]`, `_por_email: dict[email, id]`.
  - `persona_de(email) -> str | None`
  - `persona(id) -> Persona | None`
  - `Identidades()` por defecto = todo vacío (genérico).
- `cargar_identidades(case_dir: Path) -> Identidades`: lee `<case_dir>/identidades.yaml` si existe;
  si no, `Identidades()` vacío. Valida invariantes §4.1.
- **Reemplaza** los sets module-level de `inline.py` (`IDENTIDADES_VIGILADAS` /
  `IDENTIDADES_CANDIDATAS` se eliminan del código; su contenido pasa al YAML del caso).

### 5.2 `vistas.py` (nuevo)
- `@dataclass DefVista`: `id`, `titulo`, `tipo`, y campos según tipo
  (`persona` | `palabras_clave`/`incluye_msg`/`excluye_msg`/`desde`/`hasta`).
- `cargar_vistas(case_dir: Path) -> list[DefVista]`: lee `<case_dir>/vistas.yaml` si existe; si no,
  `[]`.
- `render_vistas(mensajes: list[RegistroMensaje], identidades: Identidades,
  defs: list[DefVista]) -> dict[str, str]`: función **pura** sobre la lista de mensajes en memoria
  → `{ "<id>.md": contenido }`. Sin re-leer disco.
  - **`tipo: persona`**: selecciona mensajes donde la persona aparece como **autor** (`de`) o
    **relacionada** (`para`/`cc`), vía mapa de unificación (cualquier dirección de la persona,
    `confirmada` o `candidata`). Orden cronológico `(fecha_iso, hora, msg_id)`. Cada fila marca:
    `Ref. MSG-NNNNN`, rol (autor/destinatario), `de`/`de_nombre`, fecha, **capa**, **confianza**,
    **estado de la dirección** (confirmada/candidata), y portador (`reconstruido_de`) si es Capa B.
  - **`tipo: tematica`**: incluye un mensaje si `(coincide ≥1 palabra_clave en asunto+cuerpo
    normalizado)` **OR** `msg_id ∈ incluye_msg`, y `msg_id ∉ excluye_msg`, y dentro de `[desde,
    hasta]` si se especifican. **Overrides ganan**: `incluye_msg` fuerza dentro aunque no haya
    keyword; `excluye_msg` fuerza fuera aunque haya keyword. Normalización de keywords/cuerpo con
    el mismo folding ascii/casefold que ya usa `inline._fold`/`normaliza_cuerpo` (reutilizar, no
    duplicar). Orden cronológico.
  - Una `DefVista` que referencia una `persona` inexistente, o un `tipo` desconocido → se **omite**
    con una nota en el report (no aborta la corrida; no inventa).
  - Cada vista lleva banner `GENERADO … NO editar` (coherente con el resto de vistas humanas).

### 5.3 `entregas.py` (nuevo)
- `SET_ENTREGABLE` = `["mensajes/", "adjuntos/", "vistas/", "corpus.jsonl",
  "CORREOS_LECTURA.md", "INDICE_ADJUNTOS.md"]` (no se sella `_revision/` —work product— ni
  `_registro.json` —interno—; revisable en el plan).
- `sellar(out_dir: Path, descr: str, *, commit: str | None = None, ahora: datetime | None = None)
  -> Path`:
  1. Crea `<out_dir>/_entregas/<AAAA-MM-DD>_<slug(descr)>/` (slug con `_slug_descripcion`).
  2. **Copia congelada** del `SET_ENTREGABLE` (vía `shutil.copytree`/`copy2`).
  3. Escribe `_SELLO.md`: timestamp ISO, `commit` git (best-effort: `git rev-parse HEAD`, si falla
     `"desconocido"`), nº de ficheros, y **sha256 por fichero** (tabla). Reutiliza
     `core.intake_manifest.compute_sha256_bytes`.
  - **Append-only:** si la carpeta destino ya existe, sufijo incremental (`_2`, …) — nunca
    sobrescribe una entrega previa. **No idempotente por diseño** (cada sello = entrega distinta).
  - `ahora`/`commit` inyectables para tests deterministas.

### 5.4 Refactor de enhebrado (inyección, sin estado global)
- `inline.reconstruir(m_a, raw, identidades: Identidades = Identidades())`: default vacío =
  genérico. Sustituye `IDENTIDADES_CANDIDATAS`/`IDENTIDADES_VIGILADAS` por
  `identidades.candidatas` / `identidades.vigiladas`. Misma lógica de cap (`media`,
  `identidad_candidata`) y de `en_revision` (vigilada).
- `render.render_revision(mensajes_b, punteros, watched=None, upgrades=None)`: el caller pasa
  `watched=identidades.vigiladas` (mantiene el parámetro ya existente).
- `pipeline.atomize_dir(src, out, *, case_dir: Path | None = None)`:
  - `case_dir` por defecto = `Path(out).parent.parent` (raíz del caso; `out` =
    `…/01_Procesado/Emails`). Override explícito para tests.
  - Carga `identidades = identidades.cargar_identidades(case_dir)` y
    `defs = vistas.cargar_vistas(case_dir)`.
  - Pasa `identidades` a `_pase_layer_b` → `reconstruir(..., identidades)` y a `render_revision`.
  - Tras escribir `corpus.jsonl`, genera `vistas/` con `render_vistas(mensajes, identidades, defs)`
    (mismo patrón idempotente que `_revision/`: poda `.md` huérfanos de `vistas/`).
- `pipeline.atomize_case(case_id)` pasa la raíz real del caso como `case_dir`.
- `pipeline.sellar_entrega(out, descr)` (wrapper a `entregas.sellar`) para el CLI.

### 5.5 CLI (`scripts/atomize_emails.py`)
- `--ref` / `--src --out` sin cambios; una corrida normal ahora también escribe `vistas/`.
- Nuevo `--entrega "<descr>"`: tras (o en vez de) atomizar, llama a `sellar_entrega` y reporta la
  ruta del sello. (Detalle de orquestación en el plan.)

## 6. Salidas nuevas

```
<caso>/identidades.yaml          # input curado (raíz del caso)
<caso>/vistas.yaml               # input curado (raíz del caso)
<caso>/01_Procesado/Emails/
  vistas/
    dossier_del_burgo.md
    nexo_causal.md
  _entregas/
    2026-06-25_entrega-instructora/
      mensajes/ … adjuntos/ … vistas/ … corpus.jsonl … CORREOS_LECTURA.md … INDICE_ADJUNTOS.md
      _SELLO.md
```

## 7. Impacto en tests existentes

- `tests/test_email_atomize_inline.py:200` (`test_reconstruir_watched_va_a_del_burgo_queue`)
  monkeypatchea `I.IDENTIDADES_VIGILADAS`. Se actualiza a pasar
  `identidades=Identidades(vigiladas={"per01a@example.invalid"})` a `reconstruir`. Cualquier otro test que
  dependa de los sets module-level se migra igual.
- Ningún otro consumidor de los sets fuera de `inline.py` / `render.py` (verificado por grep).

## 8. Plan de verificación EN VIVO (lección dura de la Fase 2)

Verificar SIEMPRE sobre los 277 reales de W-02VND1, no solo fixtures:
1. Crear `<caso>/identidades.yaml` + `vistas.yaml` del piloto con los datos de hoy
   (`palabras_clave` del nexo a fijar con Nikolai en el plan/ejecución).
2. Capturar el hash de los 277 `.md` de Capa A **antes** (línea base ya conocida de la Fase 2).
3. Re-correr `atomize_case("W-02VND1")`. Confirmar:
   - **277 Capa A byte-idénticos** (hash a hash).
   - Layer B sin cambios: 89 reconstruidos, PersonaUno 12 directos + 13 inline, candidata topada en
     `media`, idempotente (mismos fp, sin renumerar).
   - `vistas/dossier_del_burgo.md` y `vistas/nexo_causal.md` generadas; inspección manual de que
     el dossier agrupa correctamente las 3 direcciones de PersonaUno y NO incluye a Ignacio.
4. Probar `--entrega`: sello creado, `_SELLO.md` con sha256 correctos, segunda llamada crea carpeta
   distinta (append-only).
5. **Revisión adversarial de código** (workflow, lentes correctness/seguridad/regresión) antes de
   cerrar. Verificar cero misatribución nueva.

## 9. Método de trabajo

TDD por tarea (test→fail→impl→pass→commit), commits acotados a ficheros propios (working tree
compartido; no `git add -A`; no commitear `PLAN.md`/`CLAUDE.md`; hay post-commit hook que
auto-pushea `main`). Suite:
`python -m pytest -q --tb=no --ignore=tests/test_email_export_mcp_server.py
--ignore=tests/test_expedientes_xl_server.py`.

## 10. Decomposición

Esta fase = **capa de caso** (identidades + vistas + entregas). El fix de recall **MSG-00018** y el
OCR de adjuntos quedan para spec/plan separados posteriores.
