# Email Atomize — `media-reconstruida` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task in the current session, dispatching each Task to a fresh subagent with the exact steps below, reviewing each before moving on.

**Goal:** Añadir el peldaño de confianza `media-reconstruida` a `core/email_atomize/`: bloques de cabecera con remitente válido (`<addr>`) y fecha coherente, pero **sin estructura** (no blockquote / no run de `>`), se **promueven** a atom capa B propio con autoridad menor que `alta-reconstruida` (banner "por verificar", `en_revision: true`, línea `De (reconstruido, por verificar)`), y se listan en un nuevo `_revision/reconstruidos.md` **con su espejo `reconstruidos.jsonl`** (spec §5/§7, para re-alertado idempotente). Prime directive heredado intacto: **cero misatribución** (remitente solo desde `<addr>` literal). La salida de Capa A queda **byte-idéntica**.

**Architecture:** Cambios aditivos en 3 módulos puros + glue. (1) `inline.clasificar()` gana una rama; (2) `inline.reconstruir()` enruta `media-reconstruida` a `res.candidatos` y lo fuerza a `en_revision`; (3) `render.render_md` (banner 3 vías), `render.render_correos_lectura` (línea `De` 3 vías), `render.render_revision` (claves `reconstruidos.md` + `reconstruidos.jsonl`); (4) `pipeline._pase_layer_b` ya enruta `candidatos` al minteo → **sin cambio de lógica de promoción** (solo un contador opcional en `AtomizeReport`). `model.py` y `corpus.py` **no se tocan** (campos y emisión ya soportan el caso: `confianza` es str libre; `corpus._fila` ya emite `confianza`/`fingerprint`/`en_revision`).

**Tech Stack:** Python 3.11+, pytest (+ pytest-randomly), stdlib (`email`, `html.parser`, `dataclasses`, `json`). Windows/PowerShell. Comandos desde la raíz del repo `C:\Users\tnm33\Dev\FeesDefender`.

**Desviaciones de spec documentadas (decididas, no omitidas):**
- **Candidata en `del_burgo.md` (spec §6, §1 líneas 69-71)**: un `media-reconstruida` cuyo `de ∈ candidatas` (no vigilada) **se promueve correctamente** (el cap a `media` solo dispara para `alta-reconstruida`, `inline.py` línea 687), pero `render_revision` filtra `del_burgo.md` solo por `watched` (vigiladas) — `candidatas` y `vigiladas` son sets disjuntos. Por tanto una candidata `media-reconstruida` queda promovida y en revisión, **pero ausente de `del_burgo.md`**. Esto **se difiere explícitamente** en este plan (no se altera el filtro de `del_burgo.md`): tratarlo exige decidir si `del_burgo.md` debe listar `watched ∪ candidatas`, lo cual cambia la semántica de la cola vigilada y queda fuera del alcance del peldaño nuevo. Anotado como invariante pendiente de §6 para una iteración posterior.

---

### Task 1 — `clasificar()`: rama `media-reconstruida` + tests puros + actualizar test línea 155

**Files:**
- Modify: `core/email_atomize/inline.py` (función `clasificar`, líneas 573-606; concretamente el bloque de las líneas 593-594)
- Test: `tests/test_email_atomize_inline.py` (bloque T8; nuevos tests + actualización del test de las líneas 155-158)

Pasos:

- [ ] **(1) Escribir tests puros nuevos que fallan.** Añadir al final del bloque T8 de `tests/test_email_atomize_inline.py` (justo después de `test_clasifica_email_invalido_no_promueve`, línea 161-163, antes del comentario `# --- T9 ---` de la línea 166), este código COMPLETO:

```python
def test_clasifica_media_reconstruida_no_estructural_con_email_y_fecha():
    # No estructural pero con remitente válido + fecha coherente + no ambigua + no discrepancia
    # → PROMUEVE a media-reconstruida (nuevo peldaño).
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    conf, motivo = I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)
    assert conf == "media-reconstruida" and motivo == "no_estructural"


def test_clasifica_media_reconstruida_solo_nombre_no_promueve():
    # Display name sin <addr> → email inválido → NO promueve (queda en media/baja).
    anc = I.Anclaje(de="", de_nombre="PersonaUno", fecha_iso="2020-01-01")
    conf, _ = I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)
    assert conf in ("media", "baja") and conf != "media-reconstruida"


def test_clasifica_media_reconstruida_sin_fecha_no_promueve():
    # Email válido pero sin fecha coherente → NO promueve.
    anc = I.Anclaje(de="a@x.com", fecha_iso="0000-00-00")
    conf, _ = I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)
    assert conf in ("media", "baja") and conf != "media-reconstruida"


def test_clasifica_estructural_completo_sigue_alta_reconstruida():
    # Regresión del peldaño alto: estructural + email + fecha → alta-reconstruida (sin cambio).
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    conf, _ = I.clasificar(anc, "2020-02-01", estructural=True, ambigua=False)
    assert conf == "alta-reconstruida"
```

- [ ] **(2) Correr los tests nuevos.** `python -m pytest -q "tests/test_email_atomize_inline.py::test_clasifica_media_reconstruida_no_estructural_con_email_y_fecha" -v`
  EXPECTED: **FAIL** — `clasificar(anc, ..., estructural=False, ambigua=False)` hoy cae al `else` y devuelve `("media", "no_estructural")` (líneas 600-606), no `"media-reconstruida"`; `assert conf == "media-reconstruida"` falla.

- [ ] **(3) Implementación mínima en `clasificar()`.** En `core/email_atomize/inline.py`, reemplazar el old_string LITERAL (líneas 593-594):

old_string:
```python
    if email_ok and fecha_ok and estructural and not ambigua and not discrepancia:
        return "alta-reconstruida", "ok"
```

new_string:
```python
    if email_ok and fecha_ok and not ambigua and not discrepancia:
        if estructural:
            return "alta-reconstruida", "ok"
        return "media-reconstruida", "no_estructural"
```

- [ ] **(4) Correr los 4 tests nuevos + el de regresión alta.** `python -m pytest -q "tests/test_email_atomize_inline.py::test_clasifica_media_reconstruida_no_estructural_con_email_y_fecha" "tests/test_email_atomize_inline.py::test_clasifica_media_reconstruida_solo_nombre_no_promueve" "tests/test_email_atomize_inline.py::test_clasifica_media_reconstruida_sin_fecha_no_promueve" "tests/test_email_atomize_inline.py::test_clasifica_estructural_completo_sigue_alta_reconstruida" -v`
  EXPECTED: **PASS** (4 passed).

- [ ] **(5) Actualizar el test existente de las líneas 155-158 (ROMPE con el cambio).** El test `test_clasifica_sin_estructura_o_ambigua_demota_a_media` afirma hoy que `clasificar(anc, ..., estructural=False, ambigua=False)[0] == "media"`. El cambio lo convierte en `"media-reconstruida"`. Es el **único** test existente que rompe (verificado: el de la línea 151 usa `clasificar(None, ...)` → `"baja"`, no afectado; los de las líneas 138-147 y 161-163 son estructurales o email-inválido, no afectados). Reemplazar el old_string LITERAL en `tests/test_email_atomize_inline.py` (líneas 155-158):

old_string:
```python
def test_clasifica_sin_estructura_o_ambigua_demota_a_media():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    assert I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)[0] == "media"
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=True)[0] == "media"
```

new_string:
```python
def test_clasifica_sin_estructura_o_ambigua_demota_a_media():
    anc = I.Anclaje(de="a@x.com", fecha_iso="2020-01-01")
    # No estructural pero completo y no ambiguo → ahora PROMUEVE a media-reconstruida (nuevo peldaño).
    assert I.clasificar(anc, "2020-02-01", estructural=False, ambigua=False)[0] == "media-reconstruida"
    # Ambigua (varias cabeceras apiladas levantadas del cuerpo) → sigue topada a media (no promueve).
    assert I.clasificar(anc, "2020-02-01", estructural=True, ambigua=True)[0] == "media"
```

- [ ] **(6) Correr el test actualizado + el bloque T8 completo.** `python -m pytest -q "tests/test_email_atomize_inline.py" -k "clasifica" -v`
  EXPECTED: **PASS** (todos los `clasifica*` verdes; incluye `test_clasifica_alta_reconstruida_requiere_todo` (línea 138), `test_clasifica_fecha_posterior_al_portador_no_alta` (línea 145), `test_clasifica_headerless_es_baja_sin_remitente` (línea 150), `test_clasifica_email_invalido_no_promueve` (línea 161), sin regresión).

- [ ] **(7) Commit.** `git add core/email_atomize/inline.py tests/test_email_atomize_inline.py && git commit -m "feat(email-atomize): clasificar() promueve media-reconstruida (no estructural + email+fecha) [F4]"`

---

### Task 2 — `reconstruir()`: routing a `candidatos` + `en_revision` para `media-reconstruida`

**Files:**
- Modify: `core/email_atomize/inline.py` (función `reconstruir`, líneas 658-710; concretamente líneas 702 y 703)
- Test: `tests/test_email_atomize_inline.py` (bloque T9; `EmailMessage` ya importado en línea 169, `_ra` ya definido en línea 173)

Pasos:

- [ ] **(1) Escribir los tests que fallan.** Añadir al final del bloque T9 de `tests/test_email_atomize_inline.py` (después de `test_indice_layer_a_resuelve_por_cuerpo_sha`, línea 212, al final del fichero), este código COMPLETO. Reutiliza el helper existente `_ra` y construye un portador de TEXTO PLANO (no HTML → `estructural=False` → `media-reconstruida`). Incluye también la cobertura de **ambigua vía `reconstruir()`** (spec §8 test 6: dos cabeceras apiladas levantadas del cuerpo → NO va a candidatos):

```python
def _eml_carrier_plano(de_cita, fecha_label, asunto_cita, cuerpo_cita):
    # .eml de TEXTO PLANO con bloque outlook_es (De:/Enviado:/Para:/Asunto:) NO estructural.
    m = EmailMessage()
    m["Message-ID"] = "<carrier-plano@x>"; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    cuerpo = (f"Te reenvio esto abajo.\n\n"
              f"De: Jaime <{de_cita}>\nEnviado: {fecha_label}\nPara: x@y\nAsunto: {asunto_cita}\n"
              f"{cuerpo_cita}\n")
    m.set_content(cuerpo)
    return m.as_bytes()


def test_reconstruir_media_reconstruida_va_a_candidatos_y_en_revision():
    raw = _eml_carrier_plano("alguien@x.com", "1 de mayo de 2020", "Tibidabo",
                             "contenido citado suficientemente largo para superar el floor de 24")
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), raw)
    medias = [s for s in res.candidatos if s.confianza == "media-reconstruida"]
    assert medias, "media-reconstruida debe enrutarse a candidatos, no a punteros"
    assert medias[0].de == "alguien@x.com"
    assert medias[0].en_revision is True   # los media-reconstruida SIEMPRE entran en revisión
    # No queda como puntero de cola:
    assert not any(getattr(p, "confianza", "") == "media-reconstruida" for p in res.punteros)


def test_reconstruir_dos_cabeceras_apiladas_no_promueve():
    # Spec §8 test 6: dos bloques De:/Enviado: apilados levantados del cuerpo → ambigua=True
    # → NO va a candidatos (queda en punteros/cola), NO se fabrica remitente.
    m = EmailMessage()
    m["Message-ID"] = "<carrier-apilado@x>"; m["Subject"] = "RV"; m["From"] = "c@x"; m["To"] = "d@x"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    cuerpo = ("Reenvio esto:\n\n"
              "De: Uno <uno@x.com>\nEnviado: 1 de mayo de 2020\nPara: x@y\nAsunto: A\n"
              "De: Dos <dos@x.com>\nEnviado: 2 de mayo de 2020\nPara: x@y\nAsunto: B\n"
              "cuerpo citado suficientemente largo para superar el floor de 24 chars\n")
    m.set_content(cuerpo)
    res = I.reconstruir(_ra(fecha_iso="2026-06-01"), m.as_bytes())
    assert not any(getattr(s, "confianza", "") == "media-reconstruida" for s in res.candidatos)
```

> Nota de robustez: `test_reconstruir_dos_cabeceras_apiladas_no_promueve` ancla la prime directive (no fabricar remitente con cabeceras apiladas). La segmentación real puede dividir o no estos bloques; el invariante verificado es que NINGÚN `media-reconstruida` aterrice en `candidatos` desde un bloque ambiguo. Si la segmentación los separase en dos segmentos no ambiguos, ajustar el aserto a verificar que cada `de` proviene de un `<addr>` literal y que no se mezcla cuerpo entre remitentes (consultar al revisor antes de relajar el aserto).

- [ ] **(2) Correr el primer test.** `python -m pytest -q "tests/test_email_atomize_inline.py::test_reconstruir_media_reconstruida_va_a_candidatos_y_en_revision" -v`
  EXPECTED: **FAIL** — hoy `reconstruir()` solo enruta `conf == "alta-reconstruida"` a `res.candidatos` (línea 703); un `media-reconstruida` cae al `else` y se convierte en `SegmentoEnterrado` en `res.punteros` (líneas 705-709). `medias` queda vacío → `assert medias` falla.

- [ ] **(3) Implementación mínima — `en_revision`.** En `core/email_atomize/inline.py`, reemplazar el old_string LITERAL (línea 702):

old_string:
```python
        seg.en_revision = watched or conf in ("media", "baja")
```

new_string:
```python
        seg.en_revision = watched or conf in ("media", "baja", "media-reconstruida")
```

- [ ] **(4) Implementación mínima — routing.** En `core/email_atomize/inline.py`, reemplazar el old_string LITERAL (línea 703):

old_string:
```python
        if conf == "alta-reconstruida":
            res.candidatos.append(seg)
```

new_string:
```python
        if conf in ("alta-reconstruida", "media-reconstruida"):
            res.candidatos.append(seg)
```

- [ ] **(5) Correr los nuevos tests + regresión de T9.** `python -m pytest -q "tests/test_email_atomize_inline.py" -k "reconstruir or indice" -v`
  EXPECTED: **PASS** — ambos tests nuevos pasan y no rompen `test_reconstruir_promueve_del_burgo_inline` (línea 192), `test_reconstruir_watched_va_a_del_burgo_queue` (línea 202), `test_indice_layer_a_resuelve_por_cuerpo_sha` (línea 212).

- [ ] **(6) Commit.** `git add core/email_atomize/inline.py tests/test_email_atomize_inline.py && git commit -m "feat(email-atomize): reconstruir() enruta media-reconstruida a candidatos + en_revision [F4]"`

---

### Task 3 — `render_md`: banner 3 vías (APPEND a fichero de test PREEXISTENTE)

**Files:**
- Modify: `core/email_atomize/render.py` (función `render_md`, banner líneas 76-81)
- Test: `tests/test_email_atomize_render.py` (**fichero YA EXISTENTE, 46 líneas, con `from __future__`, imports `RegistroMensaje, AdjuntoRef`, helper `_msg()` y 3 tests `test_nombre_fichero_mensaje` / `test_render_md_tiene_frontmatter_y_cuerpo` / `test_render_marca_flags_solo_si_true`**)

> **CRÍTICO — manejo del fichero (incidencia major de las 3 revisiones):** `tests/test_email_atomize_render.py` **YA EXISTE**. NO recrearlo ni sobrescribirlo (perdería los 3 tests existentes y el import de `AdjuntoRef`). **APPEND** únicamente: añadir AL FINAL del fichero (i) el helper NUEVO `_mb(confianza)` **una sola vez** (lo reutilizan también Tasks 4 y 5), y (ii) las dos funciones de banner. **No tocar** los imports (línea 2 `from core.email_atomize.model import RegistroMensaje, AdjuntoRef` — `RegistroMensaje` ya disponible), ni el helper `_msg`, ni los 3 tests previos.

Pasos:

- [ ] **(1) APPEND al final de `tests/test_email_atomize_render.py`.** Añadir este código COMPLETO al final del fichero existente (sin tocar nada de las líneas 1-46):

```python
def _mb(confianza):
    # Helper de capa B reconstruida — reutilizado por Tasks 3, 4 y 5.
    return RegistroMensaje(
        msg_id="MSG-09001", capa="B", confianza=confianza, de="a@x.com", de_nombre="Ana",
        fecha_iso="2020-05-01", asunto="Tibidabo", cuerpo="cuerpo del mensaje reconstruido",
        reconstruido_desde_cita=True, reconstruido_de="MSG-00007", en_revision=True,
        fingerprint="fp:abc123", fuente="email")


def test_render_md_banner_media_reconstruida():
    md = R.render_md(_mb("media-reconstruida"))
    assert "> AUTORÍA POR VERIFICAR — reconstruida de una cita; remitente por cabecera, sin autenticar" in md
    assert "AUTORÍA POR RECONSTRUIR" not in md          # ya no usa la rama genérica antigua
    assert "RECONSTRUIDO DESDE CITA" not in md          # ni la de alta


def test_render_md_banner_alta_reconstruida_sin_cambio():
    md = R.render_md(_mb("alta-reconstruida"))
    assert "> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline" in md
```

> Nota: `_mb` no pasa `AdjuntoRef`; `RegistroMensaje` rellena `adjuntos` por defecto. El import de `AdjuntoRef` (línea 2) sigue siendo necesario para `test_render_md_tiene_frontmatter_y_cuerpo` — NO eliminarlo.

- [ ] **(2) Correr el test.** `python -m pytest -q "tests/test_email_atomize_render.py::test_render_md_banner_media_reconstruida" -v`
  EXPECTED: **FAIL** — el banner actual (líneas 77-80) solo tiene 2 ramas: para `media-reconstruida` (≠ `alta-reconstruida`) cae al `else` y emite `"> AUTORÍA POR RECONSTRUIR — sin verificar"`, no el texto esperado. `assert "...sin autenticar" in md` falla.

- [ ] **(3) Implementación mínima.** En `core/email_atomize/render.py`, reemplazar el old_string LITERAL (líneas 76-81):

old_string:
```python
    banner = ""
    if m.capa == "B":
        banner = ("> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline\n\n"
                  if m.confianza == "alta-reconstruida"
                  else "> AUTORÍA POR RECONSTRUIR — sin verificar\n\n")
    return _GEN_MD + "\n".join(fm) + "\n\n" + banner + m.cuerpo.strip() + "\n"
```

new_string:
```python
    banner = ""
    if m.capa == "B":
        if m.confianza == "alta-reconstruida":
            banner = "> RECONSTRUIDO DESDE CITA — remitente verificado por cabecera inline\n\n"
        elif m.confianza == "media-reconstruida":
            banner = ("> AUTORÍA POR VERIFICAR — reconstruida de una cita; "
                      "remitente por cabecera, sin autenticar\n\n")
        else:
            banner = "> AUTORÍA POR RECONSTRUIR — sin verificar\n\n"
    return _GEN_MD + "\n".join(fm) + "\n\n" + banner + m.cuerpo.strip() + "\n"
```

- [ ] **(4) Correr ambos tests de banner + los 3 tests previos (no regresión).** `python -m pytest -q "tests/test_email_atomize_render.py" -v`
  EXPECTED: **PASS** (5 passed: los 3 originales + los 2 de banner).

- [ ] **(5) Commit.** `git add core/email_atomize/render.py tests/test_email_atomize_render.py && git commit -m "feat(email-atomize): render_md banner 3 vías (media-reconstruida = por verificar) [F4]"`

---

### Task 4 — `render_correos_lectura`: línea `De` 3 vías

**Files:**
- Modify: `core/email_atomize/render.py` (función `render_correos_lectura`, rama capa B líneas 101-104)
- Test: `tests/test_email_atomize_render.py` (APPEND; reutiliza `_mb` de Task 3)

Pasos:

- [ ] **(1) APPEND los tests al final de `tests/test_email_atomize_render.py`** (reutilizan `_mb`, ya definido en Task 3):

```python
def test_render_lectura_de_media_reconstruida_por_verificar():
    vista = R.render_correos_lectura([_mb("media-reconstruida")])
    assert "**De (reconstruido, por verificar):**" in vista
    assert "sin autenticar" in vista or "sin verificar" in vista
    # No usa el rótulo de alta (verificado por cabecera) para un media-reconstruida:
    assert "remitente verificado por cabecera" not in vista


def test_render_lectura_de_alta_reconstruida_sin_cambio():
    vista = R.render_correos_lectura([_mb("alta-reconstruida")])
    assert "**De (reconstruido):**" in vista
    assert "remitente verificado por cabecera" in vista
```

- [ ] **(2) Correr el test.** `python -m pytest -q "tests/test_email_atomize_render.py::test_render_lectura_de_media_reconstruida_por_verificar" -v`
  EXPECTED: **FAIL** — la rama actual (líneas 101-104) usa para todo capa B `"**De (reconstruido):**"` + `"remitente verificado por cabecera"`; el texto `"**De (reconstruido, por verificar):**"` no existe. `assert ... in vista` falla.

- [ ] **(3) Implementación mínima.** En `core/email_atomize/render.py`, reemplazar el old_string LITERAL (líneas 101-104):

old_string:
```python
        if m.capa == "B":
            out.append(f"**De (reconstruido):** {m.de_nombre or m.de} <{m.de}>  ")
            out.append("_Mensaje recuperado de una cita; remitente verificado por cabecera "
                       f"(Ref. {m.reconstruido_de or '—'})_  ")
        else:
            out.append(f"**De:** {m.de_nombre or m.de} <{m.de}>  ")
```

new_string:
```python
        if m.capa == "B" and m.confianza == "media-reconstruida":
            out.append(f"**De (reconstruido, por verificar):** {m.de_nombre or m.de} <{m.de}>  ")
            out.append("_Mensaje reconstruido de una cita; remitente por cabecera, sin autenticar "
                       f"(Ref. {m.reconstruido_de or '—'})_  ")
        elif m.capa == "B":
            out.append(f"**De (reconstruido):** {m.de_nombre or m.de} <{m.de}>  ")
            out.append("_Mensaje recuperado de una cita; remitente verificado por cabecera "
                       f"(Ref. {m.reconstruido_de or '—'})_  ")
        else:
            out.append(f"**De:** {m.de_nombre or m.de} <{m.de}>  ")
```

- [ ] **(4) Correr ambos tests de lectura.** `python -m pytest -q "tests/test_email_atomize_render.py" -k "lectura" -v`
  EXPECTED: **PASS** (2 passed).

- [ ] **(5) Commit.** `git add core/email_atomize/render.py tests/test_email_atomize_render.py && git commit -m "feat(email-atomize): render_correos_lectura línea De 3 vías (media-reconstruida) [F4]"`

---

### Task 5 — `render_revision`: nuevas claves `reconstruidos.md` + `reconstruidos.jsonl`

**Files:**
- Modify: `core/email_atomize/render.py` (función `render_revision`, firma `(mensajes_b, punteros, watched=None, upgrades=None) -> dict`, líneas 124-166; concretamente el `return` de líneas 164-166)
- Test: `tests/test_email_atomize_render.py` (APPEND; reutiliza `_mb` de Task 3; importa `json`)

> **Major (Review 2a):** la spec §5/§7 exige DOS artefactos para el peldaño nuevo: `reconstruidos.md` Y su espejo `reconstruidos.jsonl` ("para re-alertado idempotente"). Se añaden ambas claves; el pipeline (línea 129-130) ya itera `.items()` y escribe toda clave del dict → ambos aterrizan en disco **sin tocar pipeline**. El assert de set se fija a **5 claves** (no consagra la omisión del .jsonl).

Pasos:

- [ ] **(1) APPEND el test al final de `tests/test_email_atomize_render.py`** (añadir `import json` al inicio del fichero si no estuviera; el fichero NO lo importa hoy, así que añadir `import json` justo bajo `from __future__ import annotations` en la línea 1):

old_string (línea 1):
```python
from __future__ import annotations
from core.email_atomize.model import RegistroMensaje, AdjuntoRef
```

new_string:
```python
from __future__ import annotations
import json
from core.email_atomize.model import RegistroMensaje, AdjuntoRef
```

Y AÑADIR al final del fichero:

```python
def test_render_revision_emite_reconstruidos_md_y_jsonl():
    mb_media = _mb("media-reconstruida")
    mb_alta = RegistroMensaje(
        msg_id="MSG-09002", capa="B", confianza="alta-reconstruida", de="b@x.com",
        fecha_iso="2020-06-01", asunto="Otro", cuerpo="otro cuerpo",
        reconstruido_desde_cita=True, reconstruido_de="MSG-00008", fingerprint="fp:def456")
    d = R.render_revision([mb_media, mb_alta], [], watched=None)
    # Mantiene las claves existentes + las dos nuevas:
    assert set(d) == {"cola.md", "casi_duplicados.md", "del_burgo.md",
                      "reconstruidos.md", "reconstruidos.jsonl"}
    rec = d["reconstruidos.md"]
    # Lista SOLO los media-reconstruida, con sus columnas:
    assert "MSG-09001" in rec and "a@x.com" in rec and "2020-05-01" in rec
    assert "Tibidabo" in rec and "MSG-00007" in rec
    # NO incluye el alta-reconstruida:
    assert "MSG-09002" not in rec
    # El espejo .jsonl: una línea JSON parseable por cada media-reconstruida, y solo esos:
    lineas = [l for l in d["reconstruidos.jsonl"].splitlines() if l.strip()]
    assert len(lineas) == 1
    fila = json.loads(lineas[0])
    assert fila["msg_id"] == "MSG-09001" and fila["de"] == "a@x.com"
    assert fila["fecha_iso"] == "2020-05-01" and fila["reconstruido_de"] == "MSG-00007"
    assert fila["fingerprint"] == "fp:abc123"
```

- [ ] **(2) Correr el test.** `python -m pytest -q "tests/test_email_atomize_render.py::test_render_revision_emite_reconstruidos_md_y_jsonl" -v`
  EXPECTED: **FAIL** — `render_revision` devuelve hoy solo `{"cola.md", "casi_duplicados.md", "del_burgo.md"}` (líneas 164-166); `set(d)` no contiene las claves nuevas → `assert set(d) == {...}` falla por desigualdad.

- [ ] **(3) Implementación mínima — construir tabla `.md` + espejo `.jsonl`.** En `core/email_atomize/render.py`, reemplazar el old_string LITERAL (líneas 164-166):

old_string:
```python
    return {"cola.md": "\n".join(cola) + "\n",
            "casi_duplicados.md": "\n".join(casi) + "\n",
            "del_burgo.md": "\n".join(db) + "\n"}
```

new_string:
```python
    medias = sorted((m for m in mensajes_b if m.confianza == "media-reconstruida"),
                    key=lambda m: (m.msg_id, m.fingerprint))   # determinista → idempotente
    rec = [_GEN_VIEW, "# Reconstruidos (media-reconstruida) — checklist de verificación\n",
           "Atoms capa B promovidos desde una cita NO estructural: remitente por cabecera "
           "(fiable), límite de cuerpo por adyacencia (por verificar). Cotejar cada uno contra "
           "su `.eml` portador.\n",
           "| Ref | De | Fecha | Asunto | Portador | Extracto |",
           "| --- | --- | --- | --- | --- | --- |"]
    rec_jsonl = []
    for m in medias:
        ext = (m.cuerpo or "").replace("|", " ").replace("\n", " ").strip()[:120]
        asu = (m.asunto or "").replace("|", " ").replace("\n", " ").strip()
        rec.append(f"| {m.msg_id} | {m.de} | {m.fecha_iso} | {asu} | "
                   f"{m.reconstruido_de} | {ext} |")
        rec_jsonl.append(json.dumps(
            {"msg_id": m.msg_id, "de": m.de, "fecha_iso": m.fecha_iso, "asunto": m.asunto,
             "reconstruido_de": m.reconstruido_de, "fingerprint": m.fingerprint},
            ensure_ascii=False, sort_keys=True))

    return {"cola.md": "\n".join(cola) + "\n",
            "casi_duplicados.md": "\n".join(casi) + "\n",
            "del_burgo.md": "\n".join(db) + "\n",
            "reconstruidos.md": "\n".join(rec) + "\n",
            "reconstruidos.jsonl": ("\n".join(rec_jsonl) + "\n") if rec_jsonl else ""}
```

> Verificar que `import json` está presente al inicio de `core/email_atomize/render.py`; si no, añadirlo en la zona de imports del módulo (no dentro de la función).

- [ ] **(4) Correr el test + el fichero render completo + el render_b preexistente (no regresión).** `python -m pytest -q "tests/test_email_atomize_render.py" "tests/test_email_atomize_render_b.py" -v`
  EXPECTED: **PASS** — el nuevo test pasa; los 5 tests previos de `test_email_atomize_render.py` siguen verdes; `test_render_revision_tres_colas` (render_b, usa `in` no `==`) y `test_render_revision_sin_watched_produce_del_burgo_vacio` siguen verdes (las claves extra no rompen `in`). Nota: el pipeline (`atomize_dir` líneas 129-130) ya itera `R.render_revision(...).items()` y escribe TODAS las claves → `reconstruidos.md` y `reconstruidos.jsonl` se escriben en disco **sin tocar pipeline**.

- [ ] **(5) Commit.** `git add core/email_atomize/render.py tests/test_email_atomize_render.py && git commit -m "feat(email-atomize): render_revision emite reconstruidos.md + reconstruidos.jsonl (checklist + espejo) [F4]"`

---

### Task 6 — Glue end-to-end: portador outlook plano → atom B media-reconstruida + dedup-first + idempotencia

**Files:**
- Modify: `core/email_atomize/pipeline.py` (`AtomizeReport`, líneas 34-35; `atomize_dir`, líneas 113-114) — contador `reconstruidos_media` (este Task lo hace **obligatorio**, no opcional, para que el aserto del test glue case con la implementación)
- Test: `tests/test_email_atomize_pipeline_b.py` (`json` + `EmailMessage` ya importados, líneas 2-3; añadir helper + tests glue tras `_carrier_gmail`, antes de `test_layerb_promueve_y_no_renumera_capaA`)

Pasos:

- [ ] **(1) Implementar PRIMERO el contador `reconstruidos_media`** (para que el `EXPECTED PASS` del test glue sea correcto desde la primera corrida). En `core/email_atomize/pipeline.py`, reemplazar el old_string LITERAL (líneas 34-35):

old_string:
```python
    reconstruidos_b: int = 0          # mensajes capa B promovidos (alta-reconstruida)
    citas_a_revision: int = 0         # punteros media/baja a _revision/cola.md
```

new_string:
```python
    reconstruidos_b: int = 0          # mensajes capa B promovidos (alta + media reconstruida)
    reconstruidos_media: int = 0      # de los anteriores, los media-reconstruida (no estructural)
    citas_a_revision: int = 0         # punteros media/baja a _revision/cola.md
```

Y reemplazar el old_string LITERAL (líneas 113-114):

old_string:
```python
    report.mensajes = len(mensajes)
    report.reconstruidos_b = len(mensajes_b)
```

new_string:
```python
    report.mensajes = len(mensajes)
    report.reconstruidos_b = len(mensajes_b)
    report.reconstruidos_media = sum(1 for m in mensajes_b if m.confianza == "media-reconstruida")
```

- [ ] **(2) Escribir el helper + test glue (camino feliz).** Añadir a `tests/test_email_atomize_pipeline_b.py` (tras `_carrier_gmail`, antes de `test_layerb_promueve_y_no_renumera_capaA`), este código COMPLETO. El portador es **texto plano** con bloque `De:/Enviado:/Para:/Asunto:` y cuerpo >24 chars, **sin blockquote** → `estructural=False` → `media-reconstruida`. El aserto aísla el atom B leyendo SOLO el `.md` que contiene `confianza: media-reconstruida` (no la concatenación global — incidencia minor de las 3 revisiones sobre `b_md`/`contenido_b` muerto):

```python
def _carrier_outlook_plano(mid, de_cita, fecha_label, asunto_cita, cuerpo_cita):
    """Portador de TEXTO PLANO con bloque outlook_es (De:/Enviado:/Para:/Asunto:), SIN
    blockquote → estructural=False → promovible a media-reconstruida."""
    m = EmailMessage()
    m["Message-ID"] = mid
    m["Subject"] = "RV: " + asunto_cita
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"
    m["From"] = "c@x"
    m["To"] = "d@x"
    cuerpo = (f"Te reenvio el correo de abajo.\n\n"
              f"De: Jaime <{de_cita}>\nEnviado: {fecha_label}\nPara: x@y\n"
              f"Asunto: {asunto_cita}\n{cuerpo_cita}\n")
    m.set_content(cuerpo)
    return m.as_bytes()


def test_layerb_outlook_plano_promueve_media_reconstruida(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_carrier_plano.eml").write_bytes(_carrier_outlook_plano(
        "<carrier-plano@x>", "alguien@x.com", "1 de mayo de 2020", "Tibidabo",
        "contenido citado suficientemente largo para superar el floor de 24 chars"))
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    # Capa A: 1 portador; Capa B: 1 media-reconstruida
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 2
    # Aislar el atom B por su contenido (no por nombre de fichero):
    b_mds = [p for p in mds if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert len(b_mds) == 1
    contenido_b = b_mds[0].read_text(encoding="utf-8")
    assert "confianza: media-reconstruida" in contenido_b
    assert "en_revision: true" in contenido_b
    # reconstruidos.md + reconstruidos.jsonl existen y listan el atom:
    assert (out / "_revision" / "reconstruidos.md").exists()
    assert (out / "_revision" / "reconstruidos.jsonl").exists()
    rec = (out / "_revision" / "reconstruidos.md").read_text(encoding="utf-8")
    assert "alguien@x.com" in rec and "2020-05-01" in rec
    jl = [l for l in (out / "_revision" / "reconstruidos.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    assert len(jl) == 1 and json.loads(jl[0])["de"] == "alguien@x.com"
    # Contadores:
    assert rep.reconstruidos_b == 1
    assert rep.reconstruidos_media == 1
    # Idempotencia: re-run no renumera ni duplica
    reg = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    reg2 = json.loads((out / "_registro.json").read_text(encoding="utf-8"))
    assert reg2["mensajes_fp"] == reg["mensajes_fp"]
    assert len(sorted((out / "mensajes").glob("*.md"))) == 2
```

- [ ] **(3) Escribir el test glue de dedup-first (spec §8 test 8).** Guardarraíl dedup-first aplicado al peldaño nuevo: un `media-reconstruida` cuyo cuerpo ya existe como `.eml` limpio de Capa A **NO duplica** — `idx.resolver` (por `cuerpo_sha`) lo resuelve a la copia limpia y registra el cruce en `casi_duplicados.md`, sin acuñar `.md` B nuevo. Añadir a `tests/test_email_atomize_pipeline_b.py`:

```python
def _eml_limpio(mid, de, fecha_rfc, asunto, cuerpo):
    """Mensaje limpio de Capa A (autor directo) cuyo cuerpo será luego citado por un portador."""
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = asunto
    m["Date"] = fecha_rfc; m["From"] = de; m["To"] = "x@y"
    m.set_content(cuerpo)
    return m.as_bytes()


def test_layerb_media_reconstruida_dedup_contra_capa_a(tmp_path):
    # El cuerpo citado en el portador plano REPRODUCE el de un .eml limpio ya presente:
    cuerpo = "contenido identico citado suficientemente largo para superar el floor de 24 chars"
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2020-05-01_limpio.eml").write_bytes(_eml_limpio(
        "<limpio@x>", "alguien@x.com", "Fri, 01 May 2020 09:00:00 +0200", "Tibidabo", cuerpo))
    (src / "2026-06-01_carrier_plano.eml").write_bytes(_carrier_outlook_plano(
        "<carrier-plano@x>", "alguien@x.com", "1 de mayo de 2020", "Tibidabo", cuerpo))
    rep = P.atomize_dir(src, out, case_dir=tmp_path)
    mds = sorted((out / "mensajes").glob("*.md"))
    # NO se acuña un .md B nuevo: solo el .md de Capa A del mensaje limpio (1 portador limpio
    # + 1 portador plano = 2 de Capa A; CERO B porque la cita resuelve a la copia limpia).
    b_mds = [p for p in mds if "confianza: media-reconstruida" in p.read_text(encoding="utf-8")]
    assert b_mds == [], "una cita que reproduce un .eml limpio NO debe acuñar un B nuevo"
    assert rep.upgrades >= 1
    casi = (out / "_revision" / "casi_duplicados.md").read_text(encoding="utf-8")
    assert "<carrier-plano@x>" in casi or "limpio" in casi.lower() or rep.upgrades >= 1
```

> Nota de robustez: el aserto final de `casi_duplicados.md` es tolerante (varias formas de registrar el cruce). El invariante duro es `b_mds == []` + `rep.upgrades >= 1`. Si la resolución por `cuerpo_sha` requiere que el cuerpo citado sea exactamente colapsable (`es_cuerpo_colapsable`), ajustar `cuerpo` para que la normalización del portador coincida con la del limpio; depurar con superpowers:systematic-debugging si `upgrades == 0`, NO relajar el invariante `b_mds == []`.

- [ ] **(4) Correr los tests glue.** `python -m pytest -q "tests/test_email_atomize_pipeline_b.py::test_layerb_outlook_plano_promueve_media_reconstruida" "tests/test_email_atomize_pipeline_b.py::test_layerb_media_reconstruida_dedup_contra_capa_a" -v`
  EXPECTED: **PASS** — con Tasks 1, 2, 5 mergeadas y el contador de paso (1) ya implementado: el portador plano clasifica `media-reconstruida`, `reconstruir()` lo enruta a `candidatos`, `_pase_layer_b` lo mintea (consume `res.candidatos`, línea 175) salvo que `idx.resolver` lo resuelva a Capa A (caso dedup), `render_md` emite `confianza: media-reconstruida` + `en_revision: true`, y `reconstruidos.md`/`.jsonl` se escriben. Si **FALLA**, depurar con superpowers:systematic-debugging antes de seguir (señal de regresión en Tasks 1/2/5 o de interacción con `idx.resolver`).

- [ ] **(5) Correr el fichero glue completo (regresión).** `python -m pytest -q "tests/test_email_atomize_pipeline_b.py" -v`
  EXPECTED: **PASS** — los nuevos tests + `test_layerb_promueve_y_no_renumera_capaA` + `test_layerb_headerless_no_promueve_va_a_cola` siguen verdes (el `_carrier_gmail` estructural sigue dando `alta-reconstruida`; el headerless sigue en `cola.md`).

- [ ] **(6) Commit.** `git add core/email_atomize/pipeline.py tests/test_email_atomize_pipeline_b.py && git commit -m "feat(email-atomize): glue media-reconstruida end-to-end + dedup-first + contador reconstruidos_media [F4]"`

---

### Task 7 — Regresión dura: salida de Capa A byte-idéntica

**Files:**
- Test: `tests/test_email_atomize_pipeline_b.py` (tests de regresión Capa A)

Pasos:

- [ ] **(1) Escribir los tests de regresión.** Anclan que un portador **sin citas promovibles** (puro Capa A) produce un `.md` cuyo frontmatter **no gana campos de Layer B** ni banner — la garantía "los .md de Capa A byte-idénticos" (prime directive de no-churn). Añadir al final de `tests/test_email_atomize_pipeline_b.py`:

```python
def _carrier_solo_capa_a(mid):
    """Portador SIN cita promovible: cuerpo de autor, sin bloque De:/Enviado: ni blockquote.
    Su único atom es Capa A (confianza alta), no debe ganar campos Layer B."""
    m = EmailMessage()
    m["Message-ID"] = mid; m["Subject"] = "Nota interna"
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0200"; m["From"] = "c@x"; m["To"] = "d@x"
    m.set_content("Esta es una nota de autor sin citas ni cabeceras reenviadas.\nSaludos.\n")
    return m.as_bytes()


def test_capa_a_md_no_gana_campos_layer_b(tmp_path):
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_nota.eml").write_bytes(_carrier_solo_capa_a("<nota@x>"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    mds = sorted((out / "mensajes").glob("*.md"))
    assert len(mds) == 1                                  # solo el atom de Capa A
    md = mds[0].read_text(encoding="utf-8")
    assert "capa: A" in md and "confianza: alta" in md
    # El frontmatter de Capa A NO gana campos de Layer B ni banner:
    for marca in ("reconstruido_desde_cita: true", "reconstruido_de:", "en_revision: true",
                  "confianza: media-reconstruida", "> AUTORÍA POR VERIFICAR",
                  "> RECONSTRUIDO DESDE CITA", "> AUTORÍA POR RECONSTRUIR"):
        assert marca not in md, f"Capa A no debe contener: {marca!r}"


def test_capa_a_md_byte_identico_entre_corridas(tmp_path):
    # Mismo portador Capa A; el .md debe ser idéntico tras dos corridas (idempotencia + no churn).
    src = tmp_path / "03_Email"; out = tmp_path / "Emails"; src.mkdir()
    (src / "2026-06-01_nota.eml").write_bytes(_carrier_solo_capa_a("<nota@x>"))
    P.atomize_dir(src, out, case_dir=tmp_path)
    md1 = sorted((out / "mensajes").glob("*.md"))[0].read_bytes()
    P.atomize_dir(src, out, case_dir=tmp_path)
    md2 = sorted((out / "mensajes").glob("*.md"))[0].read_bytes()
    assert md1 == md2                                     # byte-idéntico entre corridas
```

- [ ] **(2) Correr los tests.** `python -m pytest -q "tests/test_email_atomize_pipeline_b.py::test_capa_a_md_no_gana_campos_layer_b" "tests/test_email_atomize_pipeline_b.py::test_capa_a_md_byte_identico_entre_corridas" -v`
  EXPECTED: **PASS** — los cambios de Tasks 1-6 son aditivos sobre la rama capa B; `render_md` para `capa == "A"` no entra en el bloque del banner (línea 77 `if m.capa == "B"`) y `_construir_mensaje` (pipeline) no setea ningún campo Layer B. Si **FALLA**, hay regresión que filtra campos B a Capa A — detener y depurar con superpowers:systematic-debugging (guard de la prime directive de no-churn).

- [ ] **(3) Correr la suite COMPLETA del motor (regresión global, INCLUYE render_b).** `python -m pytest -q "tests/test_email_atomize_inline.py" "tests/test_email_atomize_render.py" "tests/test_email_atomize_render_b.py" "tests/test_email_atomize_pipeline_b.py" --tb=short`
  EXPECTED: **PASS** (todos verdes; sin regresiones en T4-T9, render, render_b ni glue). `tests/test_email_atomize_render_b.py` es **superficie de regresión** de los cambios de banner (Task 3), línea `De` (Task 4) y claves de `render_revision` (Task 5): sus 5 tests deben seguir verdes — `alta-reconstruida` sin cambio; `test_render_revision_tres_colas` y `test_render_revision_sin_watched_produce_del_burgo_vacio` usan `in`/filtros tolerantes, no `==`, así que las claves extra no rompen.

- [ ] **(4) Correr la suite COMPLETA del repo (gate final).** `python -m pytest -q --tb=short`
  EXPECTED: **PASS** — la suite entera verde. El último número conocido en STATUS/memoria es 1252; el delta esperado es el nº de tests nuevos de este plan (Task 1: +4; Task 2: +2; Task 3: +2; Task 4: +2; Task 5: +1; Task 6: +2; Task 7: +2 = **+15**, total esperado ~1267; el test de la línea 155 se actualiza, no se suma). Cualquier número distinto debe explicarse en `STATUS.md` al cerrar.

- [ ] **(5) Commit.** `git add tests/test_email_atomize_pipeline_b.py && git commit -m "test(email-atomize): regresión dura Capa A byte-idéntica (no churn Layer B F4)"`

---

**Notas de cierre para el ejecutor:**
- **`model.py` y `corpus.py` no se tocan** en ningún Task (restricción 8): `confianza` es `str` libre; `corpus._fila` ya emite `confianza`/`fingerprint`/`en_revision`; los consumidores máquina filtran `confianza == "media-reconstruida"`.
- **`pipeline._pase_layer_b` no cambia su lógica de promoción** (restricción 7): consume `res.candidatos` (línea 175) e itera `R.render_revision(...).items()` (líneas 129-130) escribiendo toda clave del dict → `reconstruidos.md` y `reconstruidos.jsonl` aterrizan solos. El único cambio en `pipeline.py` es el contador `reconstruidos_media` (Task 6 paso 1).
- **Superficie de regresión declarada:** `tests/test_email_atomize_render_b.py` ejercita el banner capa B (`RECONSTRUIDO DESDE CITA`), la línea `De (reconstruido)` y las tres colas de `render_revision`, todos tocados en Tasks 3/4/5. Verificado que sus 5 tests SOBREVIVEN (alta-reconstruida sin cambio; claves del dict por inclusión, no igualdad). Su corrida está incluida en Task 7 paso 3.
- **Desviación de spec documentada (candidata en `del_burgo.md`, §6/§1):** un `media-reconstruida` con `de ∈ candidatas` se promueve correctamente pero NO aparece en `del_burgo.md` (filtra solo por `watched`/vigiladas). Se **difiere** explícitamente (no se altera el filtro): tratarlo cambia la semántica de la cola vigilada. Queda como invariante pendiente de §6 para una iteración posterior.
- **Verificación adversarial sobre datos reales** (`--ref W-02VND1`, §9 de la spec: auditar cada `media-reconstruida` contra su `.eml`, cobertura de los 36, idempotencia, PersonaUno/Ignacio) queda **fuera de este plan** (post-build, requiere autorización para escribir en `G:` y los keywords del nexo causal — alineado con el "déjalo" registrado en memoria). No ejecutar escritura en `G:` en este plan.

**Ficheros tocados (todos absolutos):**
- `C:\Users\tnm33\Dev\FeesDefender\core\email_atomize\inline.py` (Tasks 1, 2)
- `C:\Users\tnm33\Dev\FeesDefender\core\email_atomize\render.py` (Tasks 3, 4, 5)
- `C:\Users\tnm33\Dev\FeesDefender\core\email_atomize\pipeline.py` (Task 6: contador `reconstruidos_media`)
- `C:\Users\tnm33\Dev\FeesDefender\tests\test_email_atomize_inline.py` (Tasks 1, 2)
- `C:\Users\tnm33\Dev\FeesDefender\tests\test_email_atomize_render.py` (APPEND; Tasks 3, 4, 5 — fichero PREEXISTENTE, nunca sobrescribir)
- `C:\Users\tnm33\Dev\FeesDefender\tests\test_email_atomize_pipeline_b.py` (Tasks 6, 7)
