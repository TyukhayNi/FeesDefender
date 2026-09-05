---
tipo: spec
estado: en-revision
creado: 2026-09-05
objeto: "MEJORAS #146 — los registradores de `_caso.md` reconstruyen el fichero y destruyen lo que no es suyo"
rev: "1"
---

# `_caso.md`: actualizar conserva lo que no es del registrador

> **Rev. 1 (2026-09-05).** Diseño para cerrar `MEJORAS #146`. Origen: acción 2 del informe
> `2026-09-05-acciones-alta-expediente.md` (Codex, lectura estática sobre `9ec96f7`), contrastada
> contra `main` en `556b8b2`: el defecto sigue vivo, sin cambios desde que se reprodujo el
> 2026-09-04.

## 1. El problema, medido

`_write_case_index(case_dir, meta)` (`core/case_manager.py:109`) **construye** el `_caso.md`
entero a partir de un `CaseMeta`: el cuerpo, desde una plantilla; el frontmatter, con diez claves
fijas (`case_id`, `tipo`, `fase`, `fecha`, `estado`, `ciudad`, `referencia_crm`,
`sudespacho_expedientes`, `drive`, `meta`). Nunca lee lo que había.

Lo llaman cuatro funciones, contadas por `grep` el 2026-09-05 sobre `556b8b2`:

| Llamador | Línea | Cuándo corre |
|---|---|---|
| `ensure_case` | `:493` | solo si `_caso.md` **no existe** (`is_new`) |
| `register_expediente` | `:215` | tras cada alta CRM, y en `sync_sudespacho` |
| `register_drive_ev` | `:620` | en **cada pull de Drive** (`intake_drive.py:322`) |
| `cache_drive_folder_info` | `:734` | tras resolver la carpeta E&V por API |

La primera es la creación y no destruye nada. Las otras tres actualizan un fichero que ya
existe, y al reconstruirlo pierden **tres cosas**:

1. **El cuerpo escrito a mano.** Reproducido por resultado el 2026-09-04 (`MEJORAS #146`): una
   nota del abogado en el cuerpo, una llamada a `register_drive_ev`, la nota ya no está.
2. **Las claves del frontmatter que no están entre las diez.** `bucket_override`, que el propio
   `case_manager.py:1174` documenta como campo que el abogado edita a mano, no sobrevive a un pull.
3. **Las claves de `meta` ajenas a `CaseMeta`.** Los tres registradores filtran `meta` por
   `dataclasses.fields(CaseMeta)` antes de reconstruir (`:203-206`, `:615-616`, `:729-730`), así
   que cualquier clave añadida por otro módulo o por una versión posterior del modelo cae.

Lo que **sí** sobrevive hoy, y hay que no romper: los campos del lock de checkout
(`estado_repositorio`, `checkout_*`), porque están en `CaseMeta` y los registradores los
coalescen desde el `meta` persistido; el comentario de `:200-204` lo dice y `MEJORAS #146` lo
confirma.

El repo ya tiene la primitiva correcta: `_atomic_write_caso_md` (`:1307`) lee `fm + body`,
aplica un mutador al frontmatter y escribe atómicamente **conservando el cuerpo**. El comentario
de `:789` avisa de que se use esa y «nunca `_write_case_index`». El aviso está escrito para el
lock y no llegó a los registradores.

## 2. La frontera

**Toda escritura sobre un `_caso.md` que ya existe conserva lo que no es del escritor:** el
cuerpo que alguien redactó, las claves de frontmatter que otro módulo o el abogado añadieron, y
las claves de `meta` que el modelo no conoce. La propiedad, no el ejemplo: el ejemplo es la nota
perdida; la propiedad es que **reconstruir no es actualizar**.

La guarda va **en el sumidero** —`_write_case_index`—, no en cada registrador. Es la misma
lección que `MEJORAS #153`: una guarda en el envoltorio la rodea el siguiente llamador. Con la
guarda en la función que escribe, el cuarto registrador que alguien añada hereda la propiedad
sin saberlo.

## 3. Diseño

### 3.1. `_write_case_index` distingue crear de actualizar

Por existencia del fichero, que es lo que ya hace `ensure_case` para decidir `is_new`:

- **No existe** → como hoy: frontmatter de diez claves y cuerpo de plantilla. Sin cambios.
- **Existe** → **actualización preservadora**:
  1. `fm, body = read_md(index)`.
  2. **Frontmatter:** `fm_nuevo = {**fm, **propias}` donde `propias` son las diez claves de
     siempre. Lo ajeno (p. ej. `bucket_override`) queda donde estaba.
  3. **`meta`:** `fm_nuevo["meta"] = {**(fm.get("meta") or {}), **asdict(meta)}`. Las claves de
     `CaseMeta` las manda el dataclass —que los registradores ya han coalescido desde lo
     persistido—; las que `CaseMeta` no conoce se conservan.
  4. **Cuerpo:** se regenera **solo si nadie lo tocó**. «Nadie lo tocó» significa que el cuerpo
     que hay coincide, sin espacios de borde, con el que la plantilla habría producido a partir del
     `meta` **persistido** (el de antes de esta escritura). Si coincide, el cuerpo es obra de la
     plantilla y se vuelve a generar con el `meta` nuevo, para que la lista de expedientes y las
     líneas de Drive sigan al día. Si no coincide, **se conserva byte a byte**.
  5. **Escritura atómica:** fichero temporal en el mismo directorio y `os.replace`, como hace
     `_atomic_write_caso_md`. Hoy `write_md` escribe en sitio, así que un corte a mitad deja el
     índice truncado; eso se hereda del primer día y se arregla de paso porque la nueva rama
     toca exactamente esa línea.

La plantilla del cuerpo se extrae a una función pura `_cuerpo_del_indice(meta) -> str`, que es
la misma que usa la creación. No hay dos plantillas que puedan divergir.

### 3.2. Los registradores no cambian de forma

`register_expediente`, `register_drive_ev` y `cache_drive_folder_info` siguen coalesciendo los
campos conocidos y llamando a `_write_case_index`. No se reescriben para usar
`_atomic_write_caso_md`: la propiedad tiene que vivir en el sumidero, y reescribir tres
llamadores para dejar el sumidero destructivo sería remediar el ejemplo.

### 3.3. Lo que «nadie lo tocó» no puede ver, declarado

La comparación es contra la plantilla **actual**. Un `_caso.md` cuyo cuerpo generó una versión
anterior de la plantilla no coincide, y el diseño lo trata como **tocado**: lo conserva tal cual.
Consecuencia: en esos ficheros el cuerpo deja de reflejar los expedientes o los IDs de Drive que
se registren después. Es el lado seguro del error —conservar de más, nunca borrar de más— y el
frontmatter sigue siendo la fuente de verdad para todo lector del repo: el `grep` del 2026-09-05
sobre `core/`, `scripts/` y `streamlit_app.py` no encuentra **ningún** consumidor del cuerpo;
todos leen el frontmatter (`get_case_status`, `read_case_meta`, `get_drive_ev_ids`…).

El cuerpo se regenera con la plantilla **actual** en cuanto vuelve a coincidir, lo que en la
práctica no pasa sin intervención. No se migra: el precio es cosmético y la migración tocaría
ficheros de cliente para arreglar prosa.

### 3.4. Alternativas descartadas

- **Conservar siempre el cuerpo al actualizar** (lo que hace `_atomic_write_caso_md`). Más
  simple, pero deja el cuerpo rancio en el caso **normal** —un caso recién dado de alta y sin nota
  al que se le registra el expediente— y el cuerpo es la vista humana del índice.
- **Marcadores alrededor de las secciones generadas.** Permitiría regenerar solo esas y conservar
  el resto incluso en ficheros ya editados. Los `_caso.md` existentes no los llevan, así que
  exigiría migración, que es lo que el §3.3 decide no hacer. Queda como mejora si algún día el
  cuerpo rancio molesta.
- **Reescribir los tres registradores sobre `_atomic_write_caso_md`.** Remedia los tres ejemplos y
  deja el sumidero destructivo para el cuarto; ver §2.

## 4. Radio de daño y rondas

La pieza escribe el fichero que guarda el lock de checkout y los vínculos CRM de un expediente, y
el defecto que cierra **destruye una nota del abogado**. Por la regla del 2026-08-26 le tocan
**dos rondas**: esta sobre el diseño y otra sobre el diff. Codex no tiene cupo, así que ambas las
ejecuta el **revisor sustituto** de `AGENTS.md`: una sesión de Claude Code sin el contexto de
autoría, y la adjudicación declara que la independencia es **más débil** porque autor y revisor
son el mismo modelo.

## 5. Mutantes

Cada uno es un test en `tests/test_caso_md_preservar_al_actualizar.py`, y el test tiene que
morir con el código de `556b8b2`:

| # | Mutante | Qué debe pasar |
|---|---|---|
| M1 | nota a mano al final del cuerpo + `register_drive_ev` | la nota sigue, byte a byte |
| M2 | nota a mano + `register_expediente` | la nota sigue **y** el expediente está en el frontmatter |
| M3 | nota a mano + `cache_drive_folder_info` | la nota sigue |
| M4 | clave top-level ajena (`bucket_override`) + cualquiera de los tres | la clave sigue con su valor |
| M5 | clave ajena dentro de `meta` + cualquiera de los tres | la clave sigue con su valor |
| M6 | lock `prestado` con `checkout_*` + `register_expediente` | el lock sigue (hoy ya pasa: es el positivo que impide regresar) |
| M7 | cuerpo **intacto** + `register_expediente` | el cuerpo **sí** lista el expediente nuevo (positivo: no congelar de más) |
| M8 | `_caso.md` inexistente + `_write_case_index` | idéntico a hoy: diez claves y cuerpo de plantilla (positivo) |
| M9 | `register_drive_ev` dos veces con los mismos IDs | no reescribe (ya existe: `test_register_drive_ev_idempotente`) |
| M10 | escritura sobre fichero existente | no queda `._caso.*.tmp` residual en `00_Input/` |

M1-M5 son los que mueren hoy; M6-M9 son positivos y existen para que la guarda no se endurezca de
más, que fue lo que costó cinco fixtures el 2026-09-04.

## 6. Alcance explícito

- **Toca:** `_write_case_index` y la extracción de la plantilla del cuerpo, en
  `core/case_manager.py`. Tests nuevos. Cierre de `MEJORAS #146`. La regla de `CLAUDE.md` («NO se
  escriben notas en `_caso.md`… vigente hasta que cierre `MEJORAS #146`») y `[APER-54]` del runbook
  pasan a decir que la nota ya no se pierde, manteniendo `90_Notas personales` como sitio
  preferente porque ningún módulo del core lo lee.
- **No toca:** `_atomic_write_caso_md`, el camino de `ensure_case` sobre caso existente (ya muta
  con esa primitiva), los tres registradores, el formato del frontmatter, ni ningún `_caso.md`
  existente (sin migración).
- **No cubre:** la concurrencia entre dos escritores del mismo `_caso.md` —eso es `MEJORAS #126`
  y el mutex—; ni el `_caso.md` de la copia del Drive durante un checkout, que lo gobierna
  `repository_checkout` con sus propios mutadores.
