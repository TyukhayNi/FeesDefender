# La corrida prepara y una sesión remata — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Meter el correo en la secuencia de apertura y hacer que la corrida deje escrito el JSON de viabilidad con lo derivable y el residuo marcado, para que una sesión lo remate en un paso.

**Architecture:** Dos etapas nuevas en la secuencia de `--modo v1` (`email` antes de `sala_maquina`, `viabilidad` antes de `verificar`), ambas con el patrón ya establecido por `etapa_crm_alta`: salen `saltada` con un pendiente declarado cuando no se les pide trabajo, nunca en silencio. Un módulo nuevo del core (`core/viabilidad_json.py`) es dueño del contrato del JSON, lo produce y lo valida; el consumidor (`render_informe.py`, que corre en el servidor y no puede importar del core) gana la regla simétrica de avisar de toda clave que no reconoce.

**Tech Stack:** Python 3.14, `typer` (CLI), `pytest` + `pytest-xdist` + `pytest-randomly`, `openpyxl` (solo en el test de integración del consumidor), `dataclasses`.

**Spec:** [`2026-09-15-corrida-prepara-sesion-remata-design.md`](../specs/2026-09-15-corrida-prepara-sesion-remata-design.md)

## Global Constraints

- **Entorno:** Windows + PowerShell. Todo comando shell arranca en el worktree. Python del venv de la raíz: `C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`.
- **Encoding:** UTF-8 sin BOM, siempre. En Python, `encoding="utf-8"` explícito en toda lectura y escritura.
- **Ningún test escribe en el árbol de producción.** Árboles sintéticos en `tmp_path`, pasados como argumento. Lo vigila `tests/test_guard_aislamiento_paralelo.py`. Agrupar con `xdist_group` **no vale**.
- **Nunca se borra ni se debilita un test para poner verde.** Ni `skip` nuevo, ni aserto relajado, ni `xfail` ampliado.
- **`main` está protegida:** rama + PR. Nunca commit directo.
- **Terminología:** propietario / buscador, nunca vendedor / comprador.
- **Un `--modo v1` inválido debe abortar ANTES de crear el esqueleto del caso.** Es la lección HA-06 de la R-A: la validación vive en `validar_modo`, que es pura y corre antes de la identidad, del mutex y de `ensure_case`. `_validar_flags` corre en `scripts/abrir_caso.py:1904`, **después** de `ensure_case`, y por eso no basta.
- **Verificar por resultado, nunca por status.** Un `OK` en pantalla no acredita que el dato llegara: el defecto H1 del spec salía con `OK`.

---

## Estructura de ficheros

| Fichero | Responsabilidad | PR |
|---|---|---|
| `docs/MEJORAS_FUTURAS.md` | marcar `#264` como promovida | 1 |
| `PLAN.md` | fila nueva referenciando `MEJORAS #264` | 1 |
| `core/apertura_v1.py` | precisar el `detalle` de `PENDIENTE_FUENTES_V3` | 1 |
| `scripts/abrir_caso.py` | `etapa_email`, su pendiente, la puerta, `validar_modo` | 1 |
| `tests/test_apertura_v1_email.py` | **nuevo** — la etapa y la puerta | 1 |
| `core/viabilidad_json.py` | **nuevo** — contrato, `preparar`, `validar` | 2 |
| `scripts/abrir_caso.py` | `etapa_viabilidad` y su sitio en la secuencia | 2 |
| `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py` | avisar de claves desconocidas | 2 |
| `docs/MEJORAS_FUTURAS.md` | ficha `#262` con el contrato corregido | 2 |
| `tests/test_viabilidad_json.py` | **nuevo** — contrato, productor, validador | 2 |
| `tests/test_render_informe_viabilidad.py` | **existente** — se le AÑADEN los tests del aviso | 2 |

> **Corrección del 2026-09-15, tras la Task 4.** El plan preveía crear
> `tests/test_viabilidad_render_informe.py`. **Ya existe `tests/test_render_informe_viabilidad.py`**
> —nombre casi idéntico, orden de palabras invertido— creado el 2026-09-11 en el PR #342, con 24
> tests que ya arrancan `render_informe.py` de verdad contra la plantilla real, y que ya cubre
> «las 88 filas salen marcadas». Crear el fichero nuevo habría duplicado la infraestructura y
> dejado dos ficheros indistinguibles por el nombre. Los tests nuevos se añaden **al existente**,
> reutilizando su `_generar(tmp_path, datos)` —que importa el módulo en vez de lanzar un
> `subprocess`— y el test de las 88 se retira de esta tanda por estar ya escrito.

---

# PR 1 — El correo entra en la corrida

## Task 1: Promover `MEJORAS #264` a `PLAN.md`

**Files:**
- Modify: `docs/MEJORAS_FUTURAS.md:12118` (cabecera de la ficha 264) y su bloque `**Disparador.**`
- Modify: `PLAN.md` (cola de prioridad)

**Interfaces:**
- Consumes: nada.
- Produces: nada de código. La etiqueta `MEJORAS #264` que las filas de `PLAN.md` referencian.

- [ ] **Step 1: Marcar la ficha como promovida**

En `docs/MEJORAS_FUTURAS.md`, la cabecera de la ficha 264 pasa de:

```markdown
## 264. Sala de lectura y viabilidad no son dos cableados: son UNA decisión
```

a:

```markdown
## 264. Sala de lectura y viabilidad no son dos cableados: son UNA decisión  [PROMOVIDO → PLAN.md]
```

- [ ] **Step 2: Cerrar el disparador con la decisión**

En esa misma ficha, el bloque `**Disparador.**` termina hoy diciendo que mientras Nikolai no elija
no se cabla ninguna etapa. Se le añade, **detrás del párrafo existente y sin borrarlo** (la
condición original es el registro de por qué se esperó):

```markdown
**Elegida la salida 3 el 2026-09-14** (decisión de Nikolai): *la corrida prepara y una sesión
remata*. Con ella entran también sus dos decisiones hermanas: el **correo entra** en la corrida, y
el **clasificador por LLM queda cerrado** —`MEJORAS #263` no se reabre: no se prueba prompt ni
modelo, y `scripts/medir_clasificador_llm.py` se queda quieto—.

**Se cabla solo la mitad de viabilidad.** La etapa `sala_lectura` sigue esperando: depende del mismo
lector, y montarla hoy produciría una etapa que siempre sale `saltada`.
Diseño: [`2026-09-15-corrida-prepara-sesion-remata-design.md`](superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md).
```

- [ ] **Step 3: Abrir la fila en `PLAN.md`**

En la cola de prioridad de `PLAN.md`, fila nueva. Copiar el estilo de las filas vecinas (una línea
de resumen, la etiqueta `MEJORAS #NN`, el estado). Texto:

```markdown
- [ ] **[APERTURA-VIABILIDAD]** La corrida prepara el JSON de viabilidad y una sesión lo remata en
  un paso, y el correo entra en la secuencia — `MEJORAS #264`, salida 3, elegida por Nikolai el
  2026-09-14. Dos hallazgos medidos el 2026-09-15 mueven el alcance: el contrato del JSON que
  publica `MEJORAS #262` tiene **cuatro campos mal** (12.000 € se tiran en silencio y sale `OK`), y
  el **equipo comercial no es derivable** de `_ficha_crm.yaml` (10 fichas reales, 25 colaboradores,
  cero claves de rol). La corrida rellena **4 de los 11 campos**; el resto queda como residuo
  marcado. **No cierra `#264`:** la etapa `sala_lectura` sigue abierta.
  Spec: `docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md` ·
  Plan: `docs/superpowers/plans/2026-09-15-corrida-prepara-sesion-remata.md`
```

- [ ] **Step 4: Comprobar que la promoción es legible por su etiqueta**

Run:
```bash
grep -c "MEJORAS #264" PLAN.md && grep -n "PROMOVIDO" docs/MEJORAS_FUTURAS.md | grep 264
```
Expected: el primero imprime `1` o más; el segundo imprime la línea 12118 con `[PROMOVIDO → PLAN.md]`.

- [ ] **Step 5: Commit**

```bash
git add docs/MEJORAS_FUTURAS.md PLAN.md
git commit -m "docs: MEJORAS #264 promovida a PLAN.md — Nikolai eligio la salida 3"
```

---

## Task 2: La etapa `email`

**Files:**
- Modify: `scripts/abrir_caso.py` — añadir `_PENDIENTE_EMAIL_NO_PEDIDO` y `etapa_email` junto a las demás etapas (tras `etapa_drive`, que termina en la zona de las líneas 643-700)
- Test: `tests/test_apertura_v1_email.py` (nuevo)

**Interfaces:**
- Consumes: `av1.EtapaResultado`, `av1.Pendiente` (`core/apertura_v1.py`); `email_export.email_dest_dir(case_id: str) -> Path` y `email_export.export_label(account, label, dest_dir, *, case_id=None, extract_attachments=True, ...) -> ExportReport` (`core/email_export.py:1188`, `:1823`).
- Produces: `etapa_email(ident, case_dir, *, cuenta: str | None, label: str | None, exportar=None) -> av1.EtapaResultado`. El parámetro `exportar` es la costura de test: un callable sin argumentos que devuelve un `ExportReport`. Task 3 la cablea en la secuencia.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_apertura_v1_email.py`:

```python
"""La etapa `email` de la secuencia de apertura.

Spec: docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md §4.
"""
import pytest

from core import apertura_v1 as av1
from scripts import abrir_caso as cli


class _Ident:
    case_id = "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    w_code = "W-TEST01"
    tipo_caso = "Vuelta"


class _Report:
    """Lo mínimo de `ExportReport` que la etapa lee."""

    def __init__(self, written=3, total_in_label=3, errors=None):
        self.written = written
        self.total_in_label = total_in_label
        self.errors = errors or []


def test_sin_cuenta_ni_label_sale_saltada_con_su_pendiente(tmp_path):
    """Sin etiqueta que traer no hay nada que hacer, y eso se DECLARA.

    `saltada` no es `hecha`: es una decisión con razón declarada. Y lleva pendiente
    porque una corrida sin correo tiene que ser distinguible de una con correo.
    """
    r = cli.etapa_email(_Ident(), tmp_path, cuenta=None, label=None)

    assert r.nombre == "email"
    assert r.estado == "saltada"
    assert r.pendientes, "una etapa saltada sin pendiente es un silencio"
    assert r.pendientes[0].codigo == "email_no_pedido"


def test_con_cuenta_y_label_sale_hecha_y_cuenta_lo_escrito(tmp_path):
    r = cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="CASO/X",
                        exportar=lambda: _Report(written=3, total_in_label=5))

    assert r.estado == "hecha"
    assert r.pendientes == ()
    assert "3" in r.detalle and "5" in r.detalle


def test_un_fallo_del_exportador_no_tumba_la_corrida(tmp_path):
    """El estado de V1 es el producto, no la traza: la etapa traduce, no propaga."""
    def _revienta():
        raise RuntimeError("token caducado")

    r = cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="CASO/X",
                        exportar=_revienta)

    assert r.estado == "fallo"
    assert "RuntimeError" in r.detalle and "token caducado" in r.detalle


def test_los_errores_parciales_del_export_se_dicen_sin_ser_un_fallo(tmp_path):
    """Un export que escribe y además acumula errores NO es un fallo, pero tampoco
    es un `hecha` limpio: los errores viajan como pendiente o la corrida los pierde."""
    r = cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="CASO/X",
                        exportar=lambda: _Report(written=2, total_in_label=4,
                                                 errors=["msg 7 sin adjunto"]))

    assert r.estado == "hecha"
    assert r.pendientes, "un export con errores que no deja pendiente los pierde"
    assert r.pendientes[0].codigo == "email_export_con_errores"


def test_la_etapa_nunca_llama_a_gmail_por_su_cuenta(tmp_path, monkeypatch):
    """La costura es obligatoria en test: si `exportar` no se inyecta, la etapa
    construiría el cliente real. Aquí se prueba que la costura MANDA."""
    llamadas = []
    monkeypatch.setattr(cli.email_export, "export_label",
                        lambda *a, **k: llamadas.append(a) or _Report())

    cli.etapa_email(_Ident(), tmp_path, cuenta="a@b.c", label="L",
                    exportar=lambda: _Report())

    assert llamadas == [], "con `exportar` inyectado no se toca `export_label`"
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_apertura_v1_email.py
```
Expected: FAIL — `AttributeError: module 'scripts.abrir_caso' has no attribute 'etapa_email'`.

- [ ] **Step 3: Escribir la implementación mínima**

En `scripts/abrir_caso.py`, junto a las demás etapas (después de `etapa_drive`):

```python
_PENDIENTE_EMAIL_NO_PEDIDO = av1.Pendiente(
    codigo="email_no_pedido",
    detalle="No se trajo correo: la corrida no dijo cual (--cuenta y --label). Si el "
            "caso tiene una etiqueta de Gmail, su material NO esta aqui.")


def etapa_email(ident, case_dir: Path, *, cuenta, label, exportar=None
                ) -> av1.EtapaResultado:
    """Etapa 2: exportar la etiqueta Gmail del caso a un lote nuevo de `00_Input`.

    **Va antes de `sala_maquina` y eso no es estetico.** La sala de maquina hace el OCR
    y la atomizacion leyendo `00_Input`; un adjunto que llegue solo por correo y se
    deposite despues no se OCR-ea ni aparece en la sala de lectura (`MEJORAS #68.a`).
    Poniendola antes, el gotcha del runbook se cumple por construccion y no por memoria
    del operador.

    **`export_label` solo LEE de Gmail** —`messages().get`, `messages().list`,
    `labels().list`— y escribe en el caso. Se midio el 2026-09-15 porque el dimensionado
    anterior afirmo lo contrario y costo una ronda mal presupuestada.
    """
    if not cuenta or not label:
        return av1.EtapaResultado(
            nombre="email", estado="saltada",
            detalle="no se pidio correo (sin --cuenta/--label)",
            pendientes=(_PENDIENTE_EMAIL_NO_PEDIDO,))

    def _exportar():
        dest = email_export.email_dest_dir(ident.case_id)   # reserva el lote (T8)
        return email_export.export_label(cuenta, label, dest, case_id=ident.case_id,
                                         extract_attachments=True)

    try:
        rep = (exportar or _exportar)()
    except Exception as exc:  # noqa: BLE001 — el estado de V1 es el producto, no la traza
        return av1.EtapaResultado(nombre="email", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")

    # Los errores parciales son un HECHO distinto de «el export fallo», y se pierden si
    # solo se mira el estado: `export_label` escribe lo que puede y acumula el resto.
    errores = list(getattr(rep, "errors", None) or [])
    pendientes = ()
    if errores:
        pendientes = (av1.Pendiente(
            codigo="email_export_con_errores",
            detalle=f"El export escribio, pero dejo {len(errores)} error(es): "
                    f"{errores[0]}" + (" (y mas)" if len(errores) > 1 else "")),)
    return av1.EtapaResultado(
        nombre="email", estado="hecha",
        detalle=f"etiqueta {label!r}: {rep.written} de {rep.total_in_label} mensajes "
                f"escritos",
        pendientes=pendientes)
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_apertura_v1_email.py
```
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_email.py
git commit -m "feat(apertura): etapa email, saltada con pendiente cuando no se pide"
```

---

## Task 3: Levantar la puerta y cablear la etapa

**Files:**
- Modify: `scripts/abrir_caso.py:285` (`_FUENTES_V1`), la firma de `validar_modo` (`:1614`) y su bloque de la fuente (`:1664-1670`), `_etapas_v2` (`:1260`), `secuencia_v1` (`:1273`), `ETAPAS_V1`/`ETAPAS_V2` (`:57`, `:62`), y el call site (`:1940`)
- Modify: `core/apertura_v1.py:37` (`detalle` de `PENDIENTE_FUENTES_V3`)
- Test: `tests/test_apertura_v1_email.py` (añadir)

**Interfaces:**
- Consumes: `etapa_email(...)` de Task 2.
- Produces: `validar_modo(modo, *, crm, fuente, force=False, dry_run=False, folder_id=None, case_id=None, hasta=None, cuenta=None, label=None) -> list[str]` — **dos parámetros nuevos al final, con default `None`**, para no romper a los llamadores existentes. `secuencia_v1(ident, case_dir, *, folder_id, team_id, crm="skip", hasta=None, etapas=None, cuenta=None, label=None)`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_apertura_v1_email.py`:

```python
def test_v1_ya_admite_la_fuente_email():
    errores = cli.validar_modo("v1", crm="skip", fuente="email", folder_id="F",
                               cuenta="a@b.c", label="CASO/X")
    assert not [e for e in errores if "--fuente" in e]


def test_v1_sigue_rechazando_las_fuentes_que_no_entraron():
    """La puerta se LEVANTA para email, no se borra: manual y whatsapp siguen fuera
    y siguen diciendo por que."""
    for fuente in ("manual", "whatsapp"):
        errores = cli.validar_modo("v1", crm="skip", fuente=fuente, folder_id="F")
        assert any("--fuente" in e for e in errores), fuente


def test_email_sin_cuenta_o_sin_label_se_rechaza_EN_validar_modo():
    """HA-06 de la R-A, aplicada a la fuente nueva.

    `_validar_flags` ya los exige, pero corre en la linea 1904: DESPUES de resolver
    identidad y de `ensure_case`. Abortar alli deja el esqueleto del caso ya creado,
    que es exactamente el defecto que la R-A encontro con `--hasta`. La puerta de v1
    vive en `validar_modo`, que es pura y corre antes de cualquier efecto.
    """
    sin_cuenta = cli.validar_modo("v1", crm="skip", fuente="email", folder_id="F",
                                  cuenta=None, label="CASO/X")
    sin_label = cli.validar_modo("v1", crm="skip", fuente="email", folder_id="F",
                                 cuenta="a@b.c", label=None)

    assert any("--cuenta" in e for e in sin_cuenta)
    assert any("--label" in e for e in sin_label)


def test_drive_ev_no_exige_los_flags_del_correo():
    errores = cli.validar_modo("v1", crm="skip", fuente="drive_ev", folder_id="F")
    assert not [e for e in errores if "--cuenta" in e or "--label" in e]


def test_email_corre_antes_que_la_sala_de_maquina():
    """La PROPIEDAD, no el indice: lo que importa es el orden relativo, porque es lo
    que hace que el OCR vea los adjuntos del correo."""
    nombres = list(cli.ETAPAS_V2)
    assert nombres.index("email") < nombres.index("sala_maquina")


def test_email_es_vocabulario_valido_de_hasta():
    assert not cli.validar_modo("v1", crm="skip", fuente="drive_ev", folder_id="F",
                                hasta="email")


def test_la_secuencia_construida_lleva_la_etapa_email():
    etapas = cli._etapas_v2(_Ident(), "/tmp/x", folder_id="F", team_id="T", crm="skip",
                            cuenta=None, label=None)
    assert [e.nombre for e in etapas] == list(cli.ETAPAS_V2)


def test_el_pendiente_permanente_ya_no_dice_que_el_correo_no_entra():
    """Se precisa el TEXTO, no el codigo: los cuatro ficheros que lo fijan comparan
    la referencia y `.codigo`. Y la distincion importa: la corrida no DESCUBRE correo
    —se le dice que etiqueta traer—, que es cosa distinta de no tocarlo."""
    assert av1.PENDIENTE_FUENTES_V3.codigo == "fuentes_v3_sin_consultar"
    assert "descubre" in av1.PENDIENTE_FUENTES_V3.detalle
    assert "LeadHub" in av1.PENDIENTE_FUENTES_V3.detalle
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_apertura_v1_email.py
```
Expected: FAIL — `validar_modo() got an unexpected keyword argument 'cuenta'` y `'email' is not in list`.

- [ ] **Step 3: Levantar la puerta**

En `scripts/abrir_caso.py:285`:

```python
_FUENTES_V1 = ("drive_ev", "email")
```

Y el bloque de `validar_modo` que la comprueba (hoy en `:1664`) pasa a:

```python
    if fuente not in _FUENTES_V1:
        errores.append(
            f"--modo v1 admite --fuente {' o '.join(_FUENTES_V1)} "
            f"(recibido: {fuente!r}). `manual` y `whatsapp` actuan sobre material que "
            "alguien deposita a mano, y V1 no tiene de donde sacarlo sin que se lo "
            "digan caso por caso."
        )
    # Los flags del correo se exigen AQUI, ademas de en `_validar_flags`, y no es
    # duplicacion: `_validar_flags` corre despues de resolver identidad y de
    # `ensure_case`, asi que abortar alli deja el esqueleto del caso ya creado. Es la
    # leccion HA-06 de la R-A, que se compro con `--hasta`.
    if fuente == "email":
        if not cuenta:
            errores.append(
                "--fuente email exige --cuenta: sin ella no hay buzon del que exportar.")
        if not label:
            errores.append(
                "--fuente email exige --label: sin ella no hay etiqueta que traer, y V1 "
                "no descubre cual es.")
```

Y la firma de `validar_modo` (`:1614`) gana los dos parámetros **al final**:

```python
def validar_modo(
    modo: str,
    *,
    crm: str | None,
    fuente: str,
    force: bool = False,
    dry_run: bool = False,
    folder_id: str | None = None,
    case_id: str | None = None,
    hasta: str | None = None,
    cuenta: str | None = None,
    label: str | None = None,
) -> list[str]:
```

- [ ] **Step 4: Cablear la etapa en la secuencia**

`ETAPAS_V1` y `ETAPAS_V2` (`:57`, `:62`):

```python
ETAPAS_V1 = ("drive", "email", "crm", "sala_maquina")
```

`_etapas_v2` (`:1260`) gana los dos parámetros y la etapa en su sitio:

```python
def _etapas_v2(ident, case_dir, *, folder_id, team_id, crm, cuenta=None, label=None):
    """Las etapas de V2, en el orden de `ETAPAS_V2`."""
    return [
        av1.Etapa("drive", lambda: etapa_drive(
            ident, case_dir, folder_id=folder_id, team_id=team_id)),
        av1.Etapa("email", lambda: etapa_email(
            ident, case_dir, cuenta=cuenta, label=label)),
        av1.Etapa("crm", lambda: etapa_crm(ident, case_dir)),
        av1.Etapa("sala_maquina", lambda: etapa_sala_maquina(ident)),
        av1.Etapa("crm_alta", lambda: etapa_crm_alta(ident, case_dir, crm=crm)),
        av1.Etapa("actuacion", lambda: etapa_actuacion(ident, case_dir, crm=crm)),
        av1.Etapa("verificar", lambda: etapa_verificar(ident, case_dir, crm=crm)),
    ]
```

`secuencia_v1` (`:1273`) los pasa:

```python
def secuencia_v1(ident, case_dir, *, folder_id, team_id, crm="skip", hasta=None,
                 etapas=None, cuenta=None, label=None):
```

y dentro:

```python
    if etapas is None:
        etapas = _etapas_v2(ident, case_dir, folder_id=folder_id, team_id=team_id,
                            crm=crm, cuenta=cuenta, label=label)
```

- [ ] **Step 5: Pasar los flags desde el CLI**

En el call site (`scripts/abrir_caso.py:1940`):

```python
                resultado_v1 = secuencia_v1(ident, case_dir, folder_id=folder_id,
                                            team_id=team_id, crm=crm, hasta=hasta,
                                            cuenta=cuenta, label=label)
```

Y donde el CLI invoca `validar_modo`, añadir `cuenta=cuenta, label=label`. Localizarlo con:

```bash
grep -n "validar_modo(" scripts/abrir_caso.py
```

- [ ] **Step 6: Precisar el pendiente permanente**

En `core/apertura_v1.py:37`:

```python
#: Permanente en toda ejecucion V1: el DESCUBRIMIENTO de fuentes es de V3 (spec §21.3).
PENDIENTE_FUENTES_V3 = Pendiente(
    codigo="fuentes_v3_sin_consultar",
    detalle="V1 no DESCUBRE fuentes: no busca que etiquetas de Gmail tiene este caso ni "
            "consulta LeadHub. Desde el 2026-09-15 si EXPORTA la etiqueta que se le "
            "diga (--cuenta/--label), que es cosa distinta. Si el material de este caso "
            "sigue sin depositar, no esta aqui.",
)
```

- [ ] **Step 6b: Actualizar los dos asertos que fijan la COMPOSICIÓN de la secuencia**

Esto **no es debilitar un test**: son dos asertos que describen de cuántas etapas se compone
la secuencia, y la secuencia cambia a propósito. Se actualizan a lo nuevo, no se relajan.
`tests/test_abrir_caso_v2_autorizacion.py:18` y `:24` dicen hoy:

```python
    assert ac.ETAPAS_V2[:3] == ac.ETAPAS_V1
    assert ac.ETAPAS_V2[3:] == ("crm_alta", "actuacion", "verificar")
```

Pasan a, **en este PR** (`viabilidad` todavía no existe — entra en la Task 7):

```python
    assert ac.ETAPAS_V2[:len(ac.ETAPAS_V1)] == ac.ETAPAS_V1
    assert ac.ETAPAS_V2[len(ac.ETAPAS_V1):] == ("crm_alta", "actuacion", "verificar")
```

El primero se escribe con `len(...)` y no con un `4` nuevo: un índice literal vuelve a
romperse en cuanto entre otra etapa —como entrará `viabilidad` dentro de dos tareas—, y lo
que el aserto quiere decir es «V2 empieza por V1 entera», no «V2 empieza por tres».

Comprobar además si `tests/_mutantes_plan5.py:225` sigue apuntando a su frontera: su mutante
cambia `ETAPAS_V2` por `ETAPAS_V1` en la validación de `--hasta`. Con `email` dentro de
`ETAPAS_V1`, ese mutante **sigue matando** (porque `crm_alta`, `actuacion`, `viabilidad` y
`verificar` quedan fuera), pero hay que **verlo morir**, no suponerlo: un mutante que deja
de morir por una razón distinta de la que lo apuntaba es una coartada, no una muerte.

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_abrir_caso_v2_autorizacion.py tests/test_abrir_caso_v2_etapas.py tests/test_apertura_v1_e2e.py
```
Expected: PASS.

- [ ] **Step 7: Correr los tests de la etapa y los cuatro ficheros que fijan el pendiente**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_apertura_v1_email.py tests/test_apertura_v1_secuenciador.py tests/test_apertura_v1_cableado.py tests/test_apertura_v1_costuras.py tests/test_abrir_caso_modo_v1.py
```
Expected: PASS. Si alguno de los cuatro ficheros antiguos falla, **leer el fallo antes de tocar nada**: significa que comparaba el texto del pendiente y no solo su referencia, y entonces el cambio del `detalle` no era gratis.

- [ ] **Step 8: Correr la suite entera, con las dos semillas**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=no -n auto -p randomly --randomly-seed=777
```
Expected: 0 fallos. Repetir con `--randomly-seed=31337`. **Un verde de una corrida no dice nada sobre el orden.**

- [ ] **Step 9: Commit**

```bash
git add scripts/abrir_caso.py core/apertura_v1.py tests/test_apertura_v1_email.py
git commit -m "feat(apertura): el correo entra en la secuencia — puerta levantada, no borrada"
```

---

# PR 2 — El JSON de viabilidad deja de ser efímero

## Task 4: El contrato y el validador

**Files:**
- Create: `core/viabilidad_json.py`
- Test: `tests/test_viabilidad_json.py` (nuevo)

**Interfaces:**
- Consumes: nada del repo.
- Produces:
  - `CAMPOS: dict[str, type]` — campo de primer nivel → tipo que el consumidor espera.
  - `CLAVES_EQUIPO`, `CLAVES_IMPORTES`, `CLAVES_ACTIVIDADES`: `tuple[str, ...]`.
  - `MARCA = "_residuo"` — el nombre del campo de marca.
  - `validar(datos: dict) -> list[str]` — lista de problemas; vacía significa válido.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_viabilidad_json.py`:

```python
"""El contrato del JSON de viabilidad, y su validador.

Los cinco defectos que se prueban aqui son los que `MEJORAS #262` publico como
contrato «derivado por ejecucion» y que resultaron INCORRECTOS, medidos el
2026-09-15 corriendo el consumidor real. Cada `test_rechaza_*` es uno de ellos.

Spec: docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md §2.
"""
import pytest

from core import viabilidad_json as vj


def _valido():
    """Un JSON minimo que el contrato acepta."""
    return {
        "case_id": "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta",
        "ref": "W-TEST01",
        "fecha": "2026-09-15",
        "equipo": {"director_captador": "", "asesor_captador": "",
                   "director_buscador": "", "asesor_buscador": ""},
        "observaciones": "Vuelta",
        "importes": {},
        "hitos": {},
        "preguntas": {},
        "actividades": {},
        "motivos_impago": "",
        "avisos": [],
        "bitacora_inicial": True,
        vj.MARCA: {"campos": [], "por_que": {}},
    }


def test_un_json_bien_formado_no_tiene_problemas():
    assert vj.validar(_valido()) == []


def test_rechaza_importes_con_las_claves_de_la_262():
    """H1, el defecto caro: `principal/costas/intereses` NO existen para el consumidor,
    que lee `precio/pct_honorarios/pagos_parciales/propuesta_pago`. Medido: con
    `principal: 12000` la celda H13 queda vacia y el script imprime OK."""
    d = _valido()
    d["importes"] = {"principal": 12000, "costas": 500, "intereses": 300}

    problemas = vj.validar(d)

    assert any("principal" in p for p in problemas)
    assert any("precio" in p for p in problemas), "el error debe decir cual es la buena"


def test_rechaza_motivos_impago_como_lista():
    """El consumidor hace `.strip()` y `.upper()`: una lista revienta con AttributeError."""
    d = _valido()
    d["motivos_impago"] = ["no reconoce la intermediacion"]

    assert any("motivos_impago" in p for p in vj.validar(d))


def test_rechaza_actividades_como_lista():
    """El consumidor hace `.get()`: una lista revienta con AttributeError."""
    d = _valido()
    d["actividades"] = [{"exposes_propiedad": 3}]

    assert any("actividades" in p for p in vj.validar(d))


def test_rechaza_bitacora_inicial_como_texto():
    """El consumidor la usa como BOOLEANO: el texto se descarta y se escribe uno fijo.
    Aceptar una cadena haria creer que ese texto viaja al informe."""
    d = _valido()
    d["bitacora_inicial"] = "mi texto"

    assert any("bitacora_inicial" in p for p in vj.validar(d))


def test_rechaza_avisos_como_lista_de_cadenas():
    """`avisos` es lista de OBJETOS: el consumidor hace `a.get("n")` sobre cada uno."""
    d = _valido()
    d["avisos"] = ["algo pasa"]

    assert any("avisos" in p for p in vj.validar(d))


def test_rechaza_equipo_como_texto():
    d = _valido()
    d["equipo"] = "APELLIDO, Nombre"

    assert any("equipo" in p for p in vj.validar(d))


def test_avisa_de_una_clave_de_equipo_que_no_existe():
    d = _valido()
    d["equipo"]["director_comercial"] = "X"

    assert any("director_comercial" in p for p in vj.validar(d))


def test_avisa_de_un_campo_de_primer_nivel_desconocido():
    d = _valido()
    d["importe_total"] = 1

    assert any("importe_total" in p for p in vj.validar(d))


def test_el_validador_puede_dar_los_DOS_valores():
    """Control positivo. Un validador que solo se ha visto decir «bien» no acredita
    nada: es el defecto que dejo pasar los cuatro campos de #262."""
    assert vj.validar(_valido()) == []
    assert vj.validar({**_valido(), "motivos_impago": []}) != []
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_viabilidad_json.py
```
Expected: FAIL — `ModuleNotFoundError: No module named 'core.viabilidad_json'`.

- [ ] **Step 3: Escribir el módulo**

Crear `core/viabilidad_json.py`:

```python
"""El JSON de la 1a pasada de viabilidad: su contrato, su productor y su validador.

**Por que existe este modulo y no una convencion.** `MEJORAS #262` publico el contrato
de este JSON «derivado POR EJECUCION», y salio mal en CUATRO campos: su corrida paso
listas VACIAS y claves desconocidas, que el consumidor sustituye o ignora sin avisar, asi
que el instrumento no podia dar el otro valor. Medido el 2026-09-15: con
`importes: {principal: 12000}` la celda del precio queda vacia y el script imprime `OK`.
Un contrato que solo vive en prosa vuelve a pasar por eso; este vive en `CAMPOS` y en
`validar`, y los tests lo fijan contra el consumidor real.

El consumidor es `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py`, que
corre en el SERVIDOR (Cowork) y no puede importar de aqui. Por eso la validacion esta a
los dos lados: este modulo impide que la corrida escriba basura, y el aviso de claves
desconocidas del consumidor impide que una sesion la escriba a mano. No es duplicacion:
el defecto medido ocurre en el consumidor.
"""
from __future__ import annotations

#: Campo de primer nivel -> tipo que el consumidor espera. Derivado LEYENDO el consumidor
#: y comprobado CORRIENDOLO: `tests/test_render_informe_viabilidad.py`, que arranca
#: `render_informe.py` de verdad contra la plantilla real.
CAMPOS: dict[str, type | tuple[type, ...]] = {
    "case_id": str,
    "ref": str,
    "fecha": str,
    "equipo": dict,
    "observaciones": str,
    "importes": dict,
    "hitos": dict,
    "preguntas": dict,
    "actividades": dict,
    "motivos_impago": str,      # `.strip()` y `.upper()`: NO es una lista
    "avisos": list,             # de OBJETOS, no de cadenas
    "bitacora_inicial": bool,   # se usa como booleano; su texto se descarta
}

CLAVES_EQUIPO = ("director_captador", "asesor_captador",
                 "director_buscador", "asesor_buscador")
#: Las que el consumidor escribe en celdas. `principal`, `costas` e `intereses` —lo que
#: publico #262— NO estan aqui a proposito: no existen para el consumidor.
CLAVES_IMPORTES = ("precio", "pct_honorarios", "pagos_parciales", "propuesta_pago")
CLAVES_ACTIVIDADES = ("exposes_propiedad", "visitas_propiedad",
                      "exposes_buscador", "visitas_buscador")

#: Las claves de `importes` que #262 publico y que se tiran en silencio. Se nombran para
#: que el error DIGA cual es la buena en vez de solo decir que esa no vale.
_IMPORTES_DE_LA_262 = {
    "principal": "precio",
    "costas": None,
    "intereses": None,
}

#: El campo donde la corrida declara lo que no pudo derivar. Guion bajo, como el resto del
#: protocolo del expediente (`_ficha_crm.yaml`, `_recibo_actuacion.json`).
MARCA = "_residuo"


def _problema_de_tipo(nombre, valor, esperado) -> str | None:
    if isinstance(esperado, type) and esperado is bool:
        # `bool` antes que `int`: en Python `True` es `int`, y dejar pasar un 1 aqui
        # aceptaria un JSON que el consumidor interpreta distinto.
        if not isinstance(valor, bool):
            return (f"{nombre}: se espera bool y llego {type(valor).__name__} "
                    f"({valor!r}). El consumidor lo usa como booleano y descarta su "
                    f"contenido.")
        return None
    if not isinstance(valor, esperado):
        return (f"{nombre}: se espera {esperado.__name__} y llego "
                f"{type(valor).__name__} ({valor!r}).")
    return None


def validar(datos: dict) -> list[str]:
    """Los problemas de `datos` contra el contrato. Lista vacia = valido.

    Devuelve TODOS los problemas, no el primero: quien escribe un JSON a mano quiere
    verlos de una vez.
    """
    problemas: list[str] = []
    if not isinstance(datos, dict):
        return [f"el JSON de viabilidad debe ser un objeto y es "
                f"{type(datos).__name__}."]

    for nombre in datos:
        if nombre not in CAMPOS and nombre != MARCA:
            problemas.append(
                f"{nombre}: campo desconocido; el consumidor lo ignorara en silencio. "
                f"Conocidos: {', '.join(sorted(CAMPOS))}.")

    for nombre, esperado in CAMPOS.items():
        if nombre not in datos:
            continue
        p = _problema_de_tipo(nombre, datos[nombre], esperado)
        if p:
            problemas.append(p)

    problemas.extend(_problemas_de_importes(datos.get("importes")))
    problemas.extend(
        _claves_ajenas("equipo", datos.get("equipo"), CLAVES_EQUIPO))
    problemas.extend(
        _claves_ajenas("actividades", datos.get("actividades"), CLAVES_ACTIVIDADES))
    problemas.extend(_problemas_de_avisos(datos.get("avisos")))
    return problemas


def _claves_ajenas(nombre, valor, conocidas) -> list[str]:
    if not isinstance(valor, dict):
        return []
    return [f"{nombre}.{k}: clave desconocida; se ignorara en silencio. "
            f"Conocidas: {', '.join(conocidas)}."
            for k in valor if k not in conocidas]


def _problemas_de_importes(valor) -> list[str]:
    """Las claves de #262 llevan mensaje propio: el error tiene que decir cual es la
    buena, no solo que esa no vale."""
    if not isinstance(valor, dict):
        return []
    problemas = []
    for k in valor:
        if k in CLAVES_IMPORTES:
            continue
        buena = _IMPORTES_DE_LA_262.get(k, "")
        if k in _IMPORTES_DE_LA_262:
            extra = (f" Probablemente querias 'precio'." if buena
                     else " El informe no tiene celda para eso.")
            problemas.append(
                f"importes.{k}: clave que publico MEJORAS #262 y que el consumidor NO "
                f"lee: su valor se tira en silencio.{extra} "
                f"Validas: {', '.join(CLAVES_IMPORTES)}.")
        else:
            problemas.append(
                f"importes.{k}: clave desconocida; se ignorara en silencio. "
                f"Validas: {', '.join(CLAVES_IMPORTES)}.")
    return problemas


def _problemas_de_avisos(valor) -> list[str]:
    if not isinstance(valor, list):
        return []
    return [f"avisos[{i}]: se espera un objeto y llego {type(a).__name__} ({a!r}); "
            f"el consumidor hace .get() sobre cada aviso."
            for i, a in enumerate(valor) if not isinstance(a, dict)]
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_viabilidad_json.py
```
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add core/viabilidad_json.py tests/test_viabilidad_json.py
git commit -m "feat(viabilidad): el contrato del JSON como dato, con su validador"
```

---

## Task 5: El productor

**Files:**
- Modify: `core/viabilidad_json.py`
- Test: `tests/test_viabilidad_json.py` (añadir)

**Interfaces:**
- Consumes: `CAMPOS`, `MARCA`, `validar` de Task 4. `Identidad` (`core/abrir_caso.py:82`), de la que se leen `case_id`, `w_code` y `tipo_caso`.
- Produces:
  - `NOMBRE_FICHERO = "_viabilidad.json"`
  - `ruta(case_dir) -> Path`
  - `preparar(ident, *, hoy: str) -> dict`
  - `escribir(case_dir, datos) -> Path` (levanta `FileExistsError` si ya existe)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/test_viabilidad_json.py`:

```python
import json


class _Ident:
    case_id = "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    w_code = "W-TEST01"
    tipo_caso = "Vuelta"


def test_preparar_rellena_los_cuatro_derivables():
    d = vj.preparar(_Ident(), hoy="2026-09-15")

    assert d["case_id"] == "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    assert d["ref"] == "W-TEST01"
    assert d["fecha"] == "2026-09-15"
    assert d["observaciones"] == "Vuelta"


def test_preparar_deja_el_equipo_VACIO_y_nunca_inventado():
    """H2: el rol no existe como dato en la apertura. Medido sobre 10 fichas reales y
    25 colaboradores: cero claves de rol, cargo o lado. Rellenarlo seria inventar."""
    d = vj.preparar(_Ident(), hoy="2026-09-15")

    assert set(d["equipo"]) == set(vj.CLAVES_EQUIPO)
    assert all(v == "" for v in d["equipo"].values())


def test_lo_que_preparar_produce_es_valido():
    """El productor y el validador tienen que estar de acuerdo, o uno de los dos miente."""
    assert vj.validar(vj.preparar(_Ident(), hoy="2026-09-15")) == []


def test_la_marca_nombra_lo_que_falta_y_por_que():
    """Un esqueleto vacio sin marca es indistinguible de un JSON que alguien creyo
    completo. Y un valor vacio es ambiguo: no distingue «nadie lo puso» de «se miro y
    no habia»."""
    d = vj.preparar(_Ident(), hoy="2026-09-15")
    marca = d[vj.MARCA]

    assert "equipo" in marca["campos"]
    assert "hitos" in marca["campos"] and "preguntas" in marca["campos"]
    assert "case_id" not in marca["campos"], "lo derivado no es residuo"
    assert "_ficha_crm.yaml" in marca["por_que"]["equipo"], (
        "la razon de `equipo` es distinta de las demas: el dato NO EXISTE en la "
        "apertura, no es que haya que leer el expediente")


def test_escribir_deja_el_fichero_donde_vive_el_protocolo(tmp_path):
    (tmp_path / "00_Input").mkdir()

    p = vj.escribir(tmp_path, vj.preparar(_Ident(), hoy="2026-09-15"))

    assert p == tmp_path / "00_Input" / "_viabilidad.json"
    assert json.loads(p.read_text(encoding="utf-8"))["ref"] == "W-TEST01"


def test_escribir_NUNCA_sobrescribe(tmp_path):
    """Lo unico caro de este fichero es lo que puso la sesion que lo remato. Un
    reintento que lo pisa destruye justo eso."""
    (tmp_path / "00_Input").mkdir()
    p = vj.ruta(tmp_path)
    p.write_text('{"ref": "LO QUE PUSO LA SESION"}', encoding="utf-8")

    with pytest.raises(FileExistsError):
        vj.escribir(tmp_path, vj.preparar(_Ident(), hoy="2026-09-15"))

    assert "LO QUE PUSO LA SESION" in p.read_text(encoding="utf-8")


def test_escribir_no_valida_a_medias_deja_el_fichero(tmp_path):
    """Si el JSON no cumple el contrato no se escribe NADA: un fichero a medias es
    peor que ninguno, porque bloquea el reintento sin contener el trabajo."""
    (tmp_path / "00_Input").mkdir()

    with pytest.raises(ValueError):
        vj.escribir(tmp_path, {"motivos_impago": []})

    assert not vj.ruta(tmp_path).exists()
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_viabilidad_json.py
```
Expected: FAIL — `AttributeError: module 'core.viabilidad_json' has no attribute 'preparar'`.

- [ ] **Step 3: Escribir el productor**

Añadir a `core/viabilidad_json.py`:

```python
import json
from pathlib import Path

#: Vive en `00_Input/` y no junto al informe, aunque `#262` sugiriera lo segundo: hay
#: precedente exacto (`_recibo_actuacion.json`), `core/intake_control.py` ya mantiene ahi
#: la lista de ficheros de protocolo que no se inventarian como documento del cliente, y
#: este JSON es la ENTRADA del informe, no una version suya.
NOMBRE_FICHERO = "_viabilidad.json"

#: Lo que la corrida NO puede derivar, con la razon. `equipo` lleva una distinta de las
#: demas a proposito: las otras se resuelven leyendo el expediente y esa no se resuelve
#: leyendo nada, porque el dato no existe en la apertura.
_POR_QUE_FALTA = {
    "equipo": ("El rol (director/asesor x captador/buscador) NO EXISTE como dato en la "
               "apertura: `_ficha_crm.yaml` trae nombre, email, movil, telefono y nif, y "
               "ninguna clave de rol o lado (medido el 2026-09-15 sobre 10 fichas y 25 "
               "colaboradores). No se resuelve leyendo el expediente: hay que saberlo."),
    "importes": "Salen de la escritura, las arras o la hoja de encargo: hay que leerlas.",
    "hitos": "Los 14 hitos exigen leer la documental del expediente.",
    "preguntas": "Las 88 preguntas del cuestionario exigen leer la documental.",
    "avisos": "Salen de lo que se encuentre al leer.",
    "actividades": "Exposes y visitas salen del CRM de E&V o de la documental.",
    "motivos_impago": "Solo si consta la postura del deudor en la documental.",
}


def ruta(case_dir) -> Path:
    return Path(case_dir) / "00_Input" / NOMBRE_FICHERO


def preparar(ident, *, hoy: str) -> dict:
    """El JSON con lo que la corrida SI puede derivar, y el residuo marcado.

    Cuatro campos de once. Los 14 hitos y las 88 preguntas siguen siendo trabajo de una
    sesion, y este modulo no finge lo contrario: por eso existe la marca.

    `hoy` se RECIBE, no se lee aqui: una fecha que el modulo saca del reloj no se puede
    fijar en un test, y la regla de la casa es que la fecha se toma del sistema en el
    punto que la escribe, nunca del contexto.
    """
    return {
        "case_id": ident.case_id,
        "ref": ident.w_code,
        "fecha": hoy,
        "observaciones": ident.tipo_caso,
        "equipo": {k: "" for k in CLAVES_EQUIPO},
        "importes": {},
        "hitos": {},
        "preguntas": {},
        "actividades": {},
        "motivos_impago": "",
        "avisos": [],
        "bitacora_inicial": True,
        MARCA: {
            "campos": sorted(_POR_QUE_FALTA),
            "por_que": dict(_POR_QUE_FALTA),
            "lo_remata": ("Una sesion que lea el expediente. Rellena estos campos y corre "
                          "render_informe.py de la skill `viabilidad-prerelleno`."),
        },
    }


def escribir(case_dir, datos: dict) -> Path:
    """Escribe el JSON. **Nunca sobrescribe** y **nunca deja un fichero a medias.**

    Valida ANTES de abrir nada: un fichero incompleto bloquea el reintento sin contener
    el trabajo, que es lo peor de los dos mundos.
    """
    problemas = validar(datos)
    if problemas:
        raise ValueError(
            "el JSON de viabilidad no cumple el contrato, no se escribe nada:\n  - "
            + "\n  - ".join(problemas))
    destino = ruta(case_dir)
    if destino.exists():
        raise FileExistsError(
            f"{destino} ya existe. Lo unico caro de este fichero es lo que puso la "
            f"sesion que lo remato: no se pisa.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return destino
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_viabilidad_json.py
```
Expected: PASS, 17 tests.

- [ ] **Step 5: Commit**

```bash
git add core/viabilidad_json.py tests/test_viabilidad_json.py
git commit -m "feat(viabilidad): preparar() deja 4 de 11 campos y marca el residuo"
```

---

## Task 6: El consumidor avisa de lo que no reconoce

**Files:**
- Modify: `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py`
- Test: `tests/test_render_informe_viabilidad.py` — **existente, se le AÑADEN los tests**

**Interfaces:**
- Consumes: `core.viabilidad_json` **solo en el test**, para cruzar los dos contratos. El script **no** importa del core: corre en el servidor. Del fichero de test existente se reutilizan `SCRIPTS`, `PLANTILLA`, el módulo ya importado `render_informe` y el helper `_generar(tmp_path, datos) -> Path`.
- Produces: nada que otra tarea consuma.

- [ ] **Step 1: Escribir los tests que fallan**

**Añadir al final de `tests/test_render_informe_viabilidad.py`** (no crear fichero nuevo: ya
existe y trae la infraestructura). Reutiliza `_generar`, que importa el módulo en vez de lanzar un
`subprocess`, y `capsys`, que el fichero ya usa para capturar los avisos:

```python
# --- El contrato del JSON contra su productor (`core/viabilidad_json.py`) -------------
#
# Es el control que `MEJORAS #262` no tuvo: su contrato se publico como «derivado por
# ejecucion» y salio mal en cuatro campos porque la corrida paso valores VACIOS, que el
# consumidor sustituye sin avisar. Aqui se cruzan los dos lados y se leen las CELDAS, no
# el codigo de salida: el defecto salia con `OK` en pantalla.

from core import viabilidad_json as vj


class _IdentFalsa:
    case_id = "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    w_code = "W-TEST01"
    tipo_caso = "Vuelta"


def _preparado():
    return vj.preparar(_IdentFalsa(), hoy="2026-09-15")


def test_el_json_que_produce_preparar_corre_de_verdad(tmp_path):
    """Lo que la corrida escribe tiene que atravesar el consumidor. Si esto se rompe, la
    etapa estara dejando un fichero que no sirve para lo unico para lo que existe."""
    salida = _generar(tmp_path, _preparado())

    assert salida.exists()


def test_el_precio_LLEGA_a_su_celda(tmp_path):
    """Control positivo del defecto medido: el instrumento tiene que poder dar los dos
    valores. Con la clave BUENA el importe llega a H13."""
    datos = _preparado()
    datos["importes"] = {"precio": 12000}

    salida = _generar(tmp_path, datos)

    assert openpyxl.load_workbook(salida)["INFORMACION"]["H13"].value == 12000


def test_avisa_de_una_clave_de_importes_que_no_lee(tmp_path, capsys):
    """El defecto de `MEJORAS #262`: `principal: 12000` no llegaba a ninguna celda y el
    script imprimia OK. Ahora lo dice, y la celda sigue vacia."""
    datos = _preparado()
    datos["importes"] = {"principal": 12000}

    salida = _generar(tmp_path, datos)

    assert "principal" in capsys.readouterr().err
    assert openpyxl.load_workbook(salida)["INFORMACION"]["H13"].value is None


def test_avisa_de_un_campo_de_primer_nivel_desconocido(tmp_path, capsys):
    datos = _preparado()
    datos["importe_total"] = 1

    _generar(tmp_path, datos)

    assert "importe_total" in capsys.readouterr().err


def test_avisa_de_una_clave_de_actividades_que_no_lee(tmp_path, capsys):
    datos = _preparado()
    datos["actividades"] = {"visitas_totales": 4}

    _generar(tmp_path, datos)

    assert "visitas_totales" in capsys.readouterr().err


def test_NO_avisa_del_campo_de_marca_del_productor(tmp_path, capsys):
    """Es del contrato aunque el consumidor no lo use. Un aviso que sale en TODAS las
    corridas deja de leerse, y entonces el que importa se pierde en el ruido."""
    _generar(tmp_path, _preparado())

    assert vj.MARCA not in capsys.readouterr().err


def test_NO_avisa_de_las_claves_conocidas(tmp_path, capsys):
    """La otra mitad del control positivo: un avisador que avisa de todo no informa."""
    datos = _preparado()
    datos["importes"] = {"precio": 1, "pct_honorarios": 5}
    datos["actividades"] = {"visitas_propiedad": 2}

    _generar(tmp_path, datos)

    err = capsys.readouterr().err
    for clave in ("precio", "pct_honorarios", "visitas_propiedad", "observaciones"):
        assert f"'{clave}'" not in err, f"aviso de sobra sobre {clave}"


def test_los_dos_contratos_no_han_divergido():
    """El core y la skill viven en dos sitios que no se importan —la skill corre en el
    servidor—. Este test es lo unico que los ata: si alguien añade un campo en uno y no
    en el otro, salta aqui."""
    fuente = (SCRIPTS / "render_informe.py").read_text(encoding="utf-8")
    for campo in vj.CAMPOS:
        assert f'"{campo}"' in fuente, (
            f"`{campo}` esta en el contrato del core y no aparece en render_informe.py")
```

**El test de «las 88 filas salen marcadas» NO se escribe**: ya existe en este mismo fichero
(`test_las_88_filas_salen_marcadas`, más `test_la_plantilla_declara_88_preguntas`). Escribirlo otra
vez sería duplicar una propiedad ya protegida.

- [ ] **Step 2: Correr los tests y verlos fallar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_render_informe_viabilidad.py
```
Expected: FAIL en los cuatro tests de aviso — el `stderr` no contiene `principal` ni `importe_total` ni `visitas_totales`.

- [ ] **Step 3: Añadir la regla al consumidor**

En `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py`, tras las constantes
`EQUIPO_CELLS` (línea ~63), añadir:

```python
# --- Claves que este script LEE. Todo lo que no este aqui se ignora, y por eso se avisa.
#
# La regla, una y la misma para todo el fichero: TODA clave que no reconozco se dice en
# voz alta. Ya se hacia con los hitos y las preguntas —que se recorren por clave— y NO se
# hacia en los campos de primer nivel ni dentro de `importes`/`actividades`, que se leen
# con `.get()`. Esa asimetria costo un defecto medido el 2026-09-15: `importes.principal`
# —la clave que publico `MEJORAS #262` como contrato— no llega a ninguna celda, y el
# script imprimia `OK`. Doce mil euros en silencio.
CAMPOS_CONOCIDOS = {
    "case_id", "ref", "fecha", "equipo", "observaciones", "importes", "hitos",
    "preguntas", "actividades", "motivos_impago", "avisos", "bitacora_inicial",
    # Del productor (`core/viabilidad_json.py`): este script no lo usa, pero es del
    # contrato. Avisar de el en CADA corrida seria ruido, y un aviso que sale siempre
    # deja de leerse.
    "_residuo",
}
CLAVES_IMPORTES = {"precio", "pct_honorarios", "pagos_parciales", "propuesta_pago"}
CLAVES_ACTIVIDADES = {"exposes_propiedad", "visitas_propiedad",
                      "exposes_buscador", "visitas_buscador"}


def avisa_de_claves_ajenas(d):
    """Dice en voz alta lo que este script no va a leer."""
    for k in d:
        if k not in CAMPOS_CONOCIDOS:
            warn(f"campo '{k}' desconocido — se ignora.")
    for nombre, conocidas in (("importes", CLAVES_IMPORTES),
                              ("actividades", CLAVES_ACTIVIDADES)):
        valor = d.get(nombre)
        if not isinstance(valor, dict):
            continue
        for k in valor:
            if k not in conocidas:
                warn(f"{nombre}.'{k}' no se lee — su valor se descarta. "
                     f"Validas: {', '.join(sorted(conocidas))}.")
```

Y en `main()`, justo después de `d = json.load(f)`:

```python
    avisa_de_claves_ajenas(d)
```

- [ ] **Step 4: Correr los tests y verlos pasar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_render_informe_viabilidad.py
```
Expected: PASS, 9 tests.

- [ ] **Step 5: Subir la versión de la skill y anotar el CHANGELOG**

La skill se ejecuta en el servidor y **se re-importa a mano**; `plugin update` compara por
versión, así que sin subirla el `.skill` empaquetado no reemplaza nada. En
`.claude/skills/viabilidad-prerelleno/SKILL.md`, subir el número de versión, y añadir al
principio de `CHANGELOG.md`:

```markdown
## v<N+1> — 2026-09-15

- `render_informe.py` **avisa de toda clave que no lee**: campos de primer nivel, y las
  de `importes` y `actividades`. Antes solo avisaba de hitos y preguntas desconocidos, y
  esa asimetría dejaba pasar en silencio la clave `importes.principal` que publicó
  `MEJORAS #262` como contrato: 12.000 € que no llegaban a ninguna celda con un `OK` en
  pantalla. Medido el 2026-09-15.
- Reconoce `_residuo`, el campo con el que `core/viabilidad_json.py` declara lo que la
  corrida de apertura no pudo derivar. No lo usa y no avisa de él.
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/viabilidad-prerelleno/ tests/test_render_informe_viabilidad.py
git commit -m "fix(viabilidad): el consumidor avisa de TODA clave que no lee"
```

---

## Task 7: La etapa `viabilidad`

**Files:**
- Modify: `scripts/abrir_caso.py` — `etapa_viabilidad`, `ETAPAS_V2`, `_etapas_v2`
- Test: `tests/test_apertura_v1_viabilidad.py` (nuevo)

**Interfaces:**
- Consumes: `core.viabilidad_json.preparar`, `.escribir`, `.ruta`, `.MARCA` (Tasks 4-5); `av1.EtapaResultado`, `av1.Pendiente`.
- Produces: `etapa_viabilidad(ident, case_dir, *, hoy=None) -> av1.EtapaResultado`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_apertura_v1_viabilidad.py`:

```python
"""La etapa `viabilidad`: la corrida prepara, una sesion remata.

Spec: docs/superpowers/specs/2026-09-15-corrida-prepara-sesion-remata-design.md §5.
"""
import json

from core import viabilidad_json as vj
from scripts import abrir_caso as cli


class _Ident:
    case_id = "BaRS9 - Calle de Prueba 1 (W-TEST01) - Vuelta"
    w_code = "W-TEST01"
    tipo_caso = "Vuelta"


def test_escribe_el_json_y_sale_hecha(tmp_path):
    (tmp_path / "00_Input").mkdir()

    r = cli.etapa_viabilidad(_Ident(), tmp_path, hoy="2026-09-15")

    assert r.estado == "hecha"
    assert vj.ruta(tmp_path).exists()
    assert json.loads(vj.ruta(tmp_path).read_text(encoding="utf-8"))["ref"] == "W-TEST01"


def test_deja_pendiente_lo_que_no_pudo_derivar(tmp_path):
    """El «residuo marcado» de la salida 3 es la mitad del valor de esta etapa: sin el,
    la corrida deja un fichero casi vacio sin decir que falta."""
    (tmp_path / "00_Input").mkdir()

    r = cli.etapa_viabilidad(_Ident(), tmp_path, hoy="2026-09-15")

    assert r.pendientes
    assert r.pendientes[0].codigo == "viabilidad_sin_rematar"
    assert "equipo" in r.pendientes[0].detalle


def test_si_ya_existe_sale_saltada_y_NO_lo_pisa(tmp_path):
    """Lo unico caro del fichero es lo que puso la sesion. Relanzar la corrida no
    puede destruirlo."""
    (tmp_path / "00_Input").mkdir()
    antes = '{"ref": "LO QUE PUSO LA SESION"}'
    vj.ruta(tmp_path).write_text(antes, encoding="utf-8")

    r = cli.etapa_viabilidad(_Ident(), tmp_path, hoy="2026-09-15")

    assert r.estado == "saltada"
    assert vj.ruta(tmp_path).read_text(encoding="utf-8") == antes


def test_un_fallo_al_escribir_no_tumba_la_corrida(tmp_path):
    """Sin `00_Input` la escritura no puede completarse; la etapa lo traduce."""
    r = cli.etapa_viabilidad(_Ident(), tmp_path / "no-existe", hoy="2026-09-15")

    assert r.estado in ("hecha", "fallo")
    if r.estado == "fallo":
        assert r.detalle


def test_viabilidad_corre_despues_de_todo_y_antes_de_verificar():
    nombres = list(cli.ETAPAS_V2)
    assert nombres.index("viabilidad") < nombres.index("verificar")
    assert nombres.index("sala_maquina") < nombres.index("viabilidad")
    assert nombres[-1] == "verificar", "verificar cierra la corrida"
```

- [ ] **Step 2: Correr los tests y verlos fallar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_apertura_v1_viabilidad.py
```
Expected: FAIL — `AttributeError: module 'scripts.abrir_caso' has no attribute 'etapa_viabilidad'`.

- [ ] **Step 3: Escribir la etapa y cablearla**

En `scripts/abrir_caso.py`, junto a las demás etapas:

```python
def etapa_viabilidad(ident, case_dir: Path, *, hoy=None) -> av1.EtapaResultado:
    """Etapa final: dejar escrito el JSON de la 1a pasada de viabilidad.

    **La corrida prepara y una sesion remata** — la salida 3 de `MEJORAS #264`, elegida
    por Nikolai el 2026-09-14. Deja CUATRO de los once campos; los 14 hitos y las 88
    preguntas siguen siendo trabajo de una sesion, y por eso el residuo va marcado.

    **Nunca sobrescribe.** Si el fichero existe, lo que contiene es el trabajo de la
    sesion que lo remato, que es lo unico caro de todo esto.
    """
    from core import viabilidad_json as vj

    hoy = hoy or datetime.date.today().isoformat()
    if vj.ruta(case_dir).exists():
        return av1.EtapaResultado(
            nombre="viabilidad", estado="saltada",
            detalle=f"{vj.NOMBRE_FICHERO} ya existe; no se pisa")
    try:
        datos = vj.preparar(ident, hoy=hoy)
        destino = vj.escribir(case_dir, datos)
    except Exception as exc:  # noqa: BLE001 — el estado de V1 es el producto
        return av1.EtapaResultado(nombre="viabilidad", estado="fallo",
                                  detalle=f"{type(exc).__name__}: {exc}")
    residuo = datos[vj.MARCA]["campos"]
    return av1.EtapaResultado(
        nombre="viabilidad", estado="hecha",
        detalle=f"{destino.name} escrito con lo derivable ({len(residuo)} campos "
                f"pendientes de una sesion)",
        pendientes=(av1.Pendiente(
            codigo="viabilidad_sin_rematar",
            detalle="El JSON de viabilidad esta preparado, no completo: faltan "
                    + ", ".join(residuo)
                    + ". Los rellena una sesion que lea el expediente, y despues corre "
                      "render_informe.py de la skill `viabilidad-prerelleno`."),))
```

Comprobar que `datetime` está importado en el módulo; si no, añadir `import datetime`
junto a los demás imports de la cabecera.

`ETAPAS_V2` (`:62`):

```python
ETAPAS_V2 = ETAPAS_V1 + ("crm_alta", "actuacion", "viabilidad", "verificar")
```

Y en `_etapas_v2`, entre `actuacion` y `verificar`:

```python
        av1.Etapa("viabilidad", lambda: etapa_viabilidad(ident, case_dir)),
```

**Y el aserto de composición que la Task 3 dejó apuntando a tres etapas finales.** En
`tests/test_abrir_caso_v2_autorizacion.py:24`, ahora que `viabilidad` existe:

```python
    assert ac.ETAPAS_V2[len(ac.ETAPAS_V1):] == ("crm_alta", "actuacion", "viabilidad",
                                                "verificar")
```

Igual que en la Task 3: es la composición la que cambia a propósito, no el aserto el que
se relaja.

- [ ] **Step 4: Correr los tests y verlos pasar**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_apertura_v1_viabilidad.py tests/test_apertura_v1_email.py
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/abrir_caso.py tests/test_apertura_v1_viabilidad.py
git commit -m "feat(apertura): etapa viabilidad — la corrida prepara, una sesion remata"
```

---

## Task 8: Corregir la ficha `MEJORAS #262`

**Files:**
- Modify: `docs/MEJORAS_FUTURAS.md` (ficha 262, el bloque del contrato JSON, líneas ~12022-12046)

**Interfaces:**
- Consumes: nada.
- Produces: nada de código.

- [ ] **Step 1: Sustituir el bloque del contrato**

El bloque que empieza en «**El contrato del JSON, derivado POR EJECUCIÓN el 2026-09-14**»
y su `json` pasa a:

````markdown
**El contrato del JSON — corregido el 2026-09-15, y la corrección enseña más que el
contrato.** Lo que esta ficha publicó el 2026-09-14 como «derivado POR EJECUCIÓN» tenía
**cuatro campos mal**. La forma canónica vive ahora en `core/viabilidad_json.py`, que es
código y tiene tests contra el consumidor real; esto es su reflejo:

```json
{
  "case_id": "...", "ref": "W-XXXXX", "fecha": "AAAA-MM-DD",
  "equipo": {"director_captador": "APELLIDO, Nombre", "asesor_captador": "...",
             "director_buscador": "...", "asesor_buscador": "..."},
  "observaciones": "...",
  "importes": {"precio": 0, "pct_honorarios": 5, "pagos_parciales": 0,
               "propuesta_pago": 0},
  "hitos": {"<id de la plantilla>": {"score": 0, "fecha": "AAAA-MM-DD"}},
  "preguntas": {"<id de la plantilla>": {"respuesta": "...", "cita": "...", "confianza": "..."}},
  "actividades": {"exposes_propiedad": 0, "visitas_propiedad": 0,
                  "exposes_buscador": 0, "visitas_buscador": 0},
  "motivos_impago": "cadena, NO lista",
  "avisos": [{"n": 1, "tipo": "...", "aviso": "...", "impacto": "...", "fuente": "...",
              "severidad": "alta|media|baja", "accion": "...", "sube": "no", "estado": "abierto"}],
  "bitacora_inicial": true,
  "_residuo": {"campos": ["..."], "por_que": {"...": "..."}}
}
```

**Los cuatro que estaban mal, medidos corriendo el consumidor el 2026-09-15:**

| Campo | Decía | Es | Qué pasaba |
|---|---|---|---|
| `importes` | `{principal, costas, intereses}` | `{precio, pct_honorarios, pagos_parciales, propuesta_pago}` | los tres se ignoran: con `principal: 12000` la celda `H13` queda vacía y el script imprime `OK` |
| `motivos_impago` | lista | **cadena** | `AttributeError: 'list' object has no attribute 'strip'` |
| `actividades` | lista | **objeto** de 4 claves | `AttributeError: 'list' object has no attribute 'get'` |
| `bitacora_inicial` | texto | **booleano**; su texto se descarta | se escribe un texto fijo |
| `avisos` | lista de objetos ✅ | — | **fila de control**: acertó, junto con `equipo` — acredita que la medición no era ciega |

**Por qué su ejecución no pudo verlo, que es lo que hay que no repetir.** Aquella corrida
pasó `[]` en los dos campos de lista y claves desconocidas en `importes`. Una lista vacía
es *falsy*, así que `d.get(...) or ""` y `or {}` la sustituyen y **nunca revientan**; y
`.get()` sobre una clave inexistente devuelve el default **sin avisar**. **El instrumento
no podía dar el otro valor**: esa corrida era incapaz de distinguir «campo correcto» de
«campo ignorado», y salió `OK` en los dos casos. Correr algo no acredita nada si la
corrida no puede fallar por lo que se quiere medir.

**Remediado en la frontera, no en el ejemplo** (PR de `MEJORAS #264`): `render_informe.py`
ya avisaba de los hitos y las preguntas que no reconocía y **callaba** en los campos de
primer nivel y dentro de `importes`/`actividades`. Esa asimetría era el defecto. Ahora
avisa de toda clave que no lee, y `core/viabilidad_json.validar` lo comprueba del lado
del productor.
````

- [ ] **Step 2: Cerrar el disparador de la ficha**

Al bloque `**Disparador.**` de la ficha 262 se le añade al final:

```markdown
**Parcialmente atendida el 2026-09-15** (`MEJORAS #264`, salida 3): el JSON deja de ser
efímero para las corridas de apertura —`core/viabilidad_json.py` lo escribe en
`00_Input/_viabilidad.json` con lo derivable y el residuo marcado—. **Lo que sigue
abierto:** los informes ya entregados no tienen JSON y no se pueden reproducir; esto solo
cubre de aquí en adelante.
```

- [ ] **Step 3: Comprobar que el contrato del doc y el del código no divergen**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m pytest -q --tb=short tests/test_render_informe_viabilidad.py::test_los_dos_contratos_no_han_divergido
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/MEJORAS_FUTURAS.md
git commit -m "docs: MEJORAS #262 tenia CUATRO campos mal — y su ejecucion no podia verlo"
```

---

## Cierre de PR 2

- [ ] **Step 1: Suite entera, dos semillas**

Run:
```bash
C:/Users/tnm33/Dev/FeesDefender/.venv/Scripts/python.exe -m scripts.session_close
```
Corre las dos semillas fijas (777 y 31337). Expected: 0 fallos en ambas. **Aceptar un
cambio son DOS semillas, no una.**

- [ ] **Step 2: Revisión adversarial**

Una ronda por PR, sobre el **diff**, ejecutada por Codex y adjudicada contra la fuente.
El mandato no coacciona y pide los dos ejes (severidad y coste del remedio). Lanzarla con
vigía que cubra la **muerte** además del fin (`-o <fichero>`), según
`docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md` §4.
Acta hermana `…-r1-adversarial-review.md` por PR, con su digest.

- [ ] **Step 3: Declarar la exención de la Task 1 y la Task 8**

En el PR: la promoción a `PLAN.md` y la corrección de la ficha `#262` son documentación y
no cambian ninguna línea que corra en producción → **0 rondas, declarado**. El resto del
diff sí entra en la ronda. Una exención silenciosa es indistinguible de un olvido.

---

## Auto-revisión de este plan

**Cobertura del spec:**

| Sección del spec | Task |
|---|---|
| §3 promoción de `#264` | Task 1 |
| §4.2 etapa `email`, `saltada` con pendiente | Task 2 |
| §4.2 puerta levantada, no borrada | Task 3 |
| §4.2 `PENDIENTE_FUENTES_V3` precisado | Task 3, Step 6 |
| §4.2 orden antes de `sala_maquina` | Task 3 (test de la propiedad) |
| §5.1 la frontera del aviso | Task 6 |
| §5.2 validación a los dos lados | Tasks 4 (productor) y 6 (consumidor) |
| §5.3 contrato, `preparar`, `validar` | Tasks 4 y 5 |
| §5.3 `00_Input/`, nunca sobrescribe | Task 5 |
| §5.4 etapa `viabilidad` antes de `verificar` | Task 7 |
| §5.5 ficha `#262` corregida | Task 8 |
| §5.6 el JSON corre de verdad por el consumidor | Task 6 (sobre el fichero de test ya existente) |

**Añadido que el spec no preveía:** la exigencia de `--cuenta`/`--label` dentro de
`validar_modo` (Task 3). `_validar_flags` ya los pide, pero corre en la línea 1904,
**después de `ensure_case`**: abortar allí deja el esqueleto del caso ya creado, que es
exactamente el defecto HA-06 que la R-A encontró con `--hasta`. Sin esto, levantar la
puerta habría reintroducido un defecto ya comprado.

**Dos cosas medidas al auto-revisar, que habrían salido como rojos sin explicación:**

1. **El conteo de la columna M es 90, no 88**, si se cuentan las filas con *algo* escrito:
   la cabecera y su subtítulo también escriben ahí. Las 88 son las que valen `sí`/`no`. Un
   test escrito con el criterio ancho habría fijado la cabecera como si fuera una pregunta.
2. **`tests/test_abrir_caso_v2_autorizacion.py:18` y `:24` fijan la composición de la
   secuencia** con índices literales (`[:3]`, `[3:]`). Las dos etapas nuevas los rompen, en
   dos PRs distintos. Están tratados en la Task 3 Step 6b y en la Task 7 Step 3, con el
   aserto reescrito en términos de `len(ETAPAS_V1)` para que la próxima etapa no lo vuelva
   a romper. **No es relajarlos: es que la composición cambia a propósito.**

**Consistencia de tipos:** `etapa_email(ident, case_dir, *, cuenta, label, exportar=None)`,
`etapa_viabilidad(ident, case_dir, *, hoy=None)`, `vj.preparar(ident, *, hoy)`,
`vj.escribir(case_dir, datos)`, `vj.ruta(case_dir)`, `vj.validar(datos)`. `MARCA` es
`"_residuo"` en el core y la cadena literal `"_residuo"` en `CAMPOS_CONOCIDOS` del
consumidor, que no puede importarlo — y `test_los_dos_contratos_no_han_divergido` es lo
que ata los dos lados.
