# Diseño — Fix de extracción de remitente "Apellido, Nombre <addr>" (iteración 1 del gap sin_cabecera)

> Fix de bug acotado en `core/email_atomize/inline.py` (`_addr_o_nombre`). Causa raíz por
> depuración sistemática sobre W-02VND1. Iteración 1 de 3 del gap `sin_cabecera` (ver MEJORAS #46).
> Spec base: Layer B + F4 media-reconstruida. Prime directive: **cero misatribución**.

## 0. Causa raíz (verificada)

Los consultores de E&V firman con display-name **"Apellido, Nombre"** (`PersonaCuatro, Eva`,
`PersonaCinco, Isabel`, `PersonaSeis, Marta`, `Espín, Anna`). En `_addr_o_nombre(raw)` el motor usa
`email.utils.parseaddr`, que interpreta la **coma** como separador de direcciones y devuelve
`('', 'Apellido')` → `addr` sin `@` → **`de=""`**. Resultado: citas con `De: Apellido, Nombre
<addr>` quedan `sin_cabecera`/sin remitente y NO se atribuyen ni promueven, pese a llevar un
`<addr>` literal e inequívoco.

Reproducción: `parsear_anclaje("De: PersonaCuatro, Eva <persona.cuatro@engelvoelkers.com>\n…")` →
`de=''`; sin la coma (`De: Eva <addr>`) → `de='eva.pratpadros@…'`. Confirmado sobre el correo
Eva→Consulado de [PAIS_EXTRANJERO] (7-jul, "Re: offer letter TIBIDABO 8", interior de MSG-00305) y sobre las
filas `comma_EV` del informe de auditoría.

## 1. Fix

En `core/email_atomize/inline.py`, `_addr_o_nombre(raw)`: **preferir la extracción directa del
`<addr>`** (regex `_RE_ADDR`, ya existente: `<\s*([^<>\s]+@[^<>\s]+)\s*>`) ANTES de `parseaddr`.
Si hay un `<addr>`, esa es la dirección (anclada al literal), y el display-name es el texto previo
al `<`. Si no hay `<addr>`, se mantiene el comportamiento actual (`parseaddr`, que cubre la
dirección desnuda `a@b.com`).

```python
def _addr_o_nombre(raw: str) -> tuple[str, str]:
    """``(de, de_nombre)`` desde un valor De:/From:. Nunca inventa una dirección.
    Prefiere el <addr> literal (robusto ante display-names con coma "Apellido, Nombre <addr>",
    que rompen parseaddr); si no hay <addr>, cae a parseaddr (dirección desnuda)."""
    raw = raw or ""
    m = _RE_ADDR.search(raw)
    if m:
        addr = m.group(1).lower()
        nombre = raw[: m.start()].strip().strip('"').strip().rstrip("<").strip()
        return addr, nombre
    nombre, addr = parseaddr(raw)
    if "@" in addr:
        return addr.lower(), (nombre or "").strip()
    return "", (nombre or addr or raw).strip()
```

- **Aditivo / seguro:** solo cambia el resultado para entradas con `<addr>` que `parseaddr` no
  resolvía (coma). Para `Nombre <addr>` sin coma, ambos caminos dan la misma `addr`. Sigue sin
  inventar nunca una dirección (solo afirma lo que está entre `<…@…>`). Prime directive intacto.
- **Alcance iteración 1:** solo `_addr_o_nombre`. NO aborda valores de cabecera en línea aparte
  (`De:` ↵ valor) ni `<` ↵ email ↵ `>` partido (iteración 2), ni la recursión dentro de
  reconstrucciones (iteración 3, Gap 2). El correo interior de MSG-00305 necesita las 3.

## 2. Plan de tests (TDD)

**Puros (`tests/test_email_atomize_inline.py`):**
1. `parsear_anclaje("De: PersonaCuatro, Eva <persona.cuatro@engelvoelkers.com>\nEnviado: 7 de julio
   de 2025\nAsunto: x", "outlook_es")` → `de == "persona.cuatro@engelvoelkers.com"`,
   `de_nombre` contiene "PersonaCuatro, Eva" (hoy: `de==""`).
2. Regresión: `De: Eva <eva@x.com>` (sin coma) → `de=="eva@x.com"`, `de_nombre=="Eva"`.
3. Regresión: display-name SIN `<addr>` (`De: PersonaUno`) → `de==""` (no inventa).
4. Regresión: dirección desnuda (`De: eva@x.com`) → `de=="eva@x.com"`.
5. `clasificar`/promoción: un bloque no estructural con `De: Apellido, Nombre <addr>` + fecha →
   `media-reconstruida` (antes `media`/sin remitente).

**Glue (`tests/test_email_atomize_pipeline_b.py`):** portador texto plano con cita
`De: Apellido, Nombre <addr>` + `Enviado el: …` → 1 atom `media-reconstruida` con el `de` correcto.

**Regresión dura:** suite del motor verde; Capa A byte-idéntica.

## 3. Verificación sobre datos reales (post-fix)

Re-correr `atomize_case('W-02VND1')` (idempotente, escribe en `G:`). Esperado: nuevos atoms
`media-reconstruida` para las citas de E&V con coma que tengan fecha parseable (Isabel "Fwd
MEMORIA", Eva "Fwd Planos", Anna "Nota simple"…); medir cuántos de los `comma_EV` + del bucket
`sin_cabecera` se recuperan. Capa A byte-idéntica; idempotente; cada nuevo atom auditado contra su
`.eml` (el `<addr>` aparece literal). NOTA: muchas citas Apple dentro de blockquote (`El X
escribió:`) seguirán sin remitente hasta la iteración 2 — no esperar que caiga todo el bucket.

## 4. Fuera de alcance (iteraciones 2-3)

Valores de cabecera en línea aparte + `<` ↵ email ↵ `>` partido; atribución Apple/gmail dentro del
blockquote cuando la cabecera va en el cuerpo; recursión dentro de reconstrucciones (Gap 2). El
correo interior de MSG-00305 (Eva→[PAIS_EXTRANJERO] 7-jul) depende de las tres.
