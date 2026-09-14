"""`[APER-71]` — el email identifica un buzón, no a una persona.

Medido el 2026-09-10 sobre el expediente 643: la segunda firmante del encargo, **con NIF propio
y distinto**, comparte el correo doméstico con el primero —lo normal en un matrimonio, que es la
norma entre propietarios—. `resolver_parte` la resolvió a la ficha de él «por email» y
`_completar_contrario_existente` rellenó los huecos de la ficha ajena con sus datos.

Diseño y adjudicación de la R1:
`docs/superpowers/specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md` §§1-2 y §6.

**El vocabulario que faltaba (R1/H-01, H-02).** Un documento tiene TRES estados, no dos:
ausente, **utilizable** (tiene forma canónica) y **no interpretable** (se aportó algo que no
sobrevive a `_canonizar_documento`: `" -- . "` → `""`). Y comparar dos documentos es comparar
sus formas canónicas **en los dos lados**: `12.345.678-z` y `12345678Z` son el mismo.

**Y la frontera que obligó a reordenar la función (R1/H-03):** un criterio fuerte que identifica
unívocamente no puede quedar tapado por la multiplicidad de uno débil. La guarda de ambigüedad
del email se evaluaba ANTES del cruce con el NIF, así que el remedio de la rev. 1 —crear la ficha
de la segunda firmante— producía un buzón con dos fichas y **bloqueaba la corrida siguiente para
siempre**.
"""
from __future__ import annotations

import pytest

from core import sudespacho_relations as sr


# ---------------------------------------------------------------------------
# Doble del CRM: un censo de fichas en memoria, consultado como lo hace el core
# ---------------------------------------------------------------------------


def _registro(fid: str, *, nif: str = "", email: str = "") -> dict:
    """Una fila del CRM con la forma real: `{"id", "values": [{"property": {"name"}, "value"}]}`."""
    vals = []
    if nif:
        vals.append({"property": {"name": "nif_cif"}, "value": nif})
    if email:
        vals.append({"property": {"name": "email"}, "value": email})
    return {"id": fid, "values": vals}


def _censo(monkeypatch, fichas: list[dict], *, falla: str | None = None, orden_inverso: bool = False):
    """Sustituye `_buscar_registros` por una consulta sobre `fichas`.

    `falla` fuerza `ok=False` para esa propiedad, que es «no pude mirar» y no «no hay».
    `orden_inverso` devuelve las coincidencias al revés: la decisión no puede depender de eso.
    """
    llamadas: list[tuple[str, str, tuple[str, ...]]] = []

    def fake(elemento, propiedad, valor, *, operador="equal", limite=5, properties=()):
        llamadas.append((propiedad, valor, tuple(properties)))
        if falla == propiedad:
            return sr.Consulta(ok=False, motivo="HTTP 500")
        valor = (valor or "").strip()
        if not valor:
            return sr.Consulta()
        hits = []
        for f in fichas:
            v = sr._values_dict(f)
            actual = str(v.get(propiedad) or "")
            if propiedad == "nif_cif":
                casa = sr._canonizar_documento(actual) == sr._canonizar_documento(valor)
            else:
                casa = actual.strip().lower() == valor.lower()
            if casa:
                hits.append(f)
        if orden_inverso:
            hits.reverse()
        return sr.Consulta(registros=hits)

    monkeypatch.setattr(sr, "_buscar_registros", fake)
    return llamadas


ELEM = "clientes_contrarios"


# ---------------------------------------------------------------------------
# §2.1 — el orden de decisión
# ---------------------------------------------------------------------------


def test_h03_el_nif_unico_manda_aunque_el_email_devuelva_varias(monkeypatch):
    """**El hallazgo más grave de la R1.** Un NIF que identifica a una sola ficha resuelve,
    sin importar cuántas devuelva el buzón.

    Antes, `len(ids_mail) > 1` disparaba `ambiguo` **antes** de cruzar con el NIF, así que
    `ids_nif={B}` con `ids_mail={A,B}` salía ambiguo teniendo la respuesta unívoca delante.
    Eso es exactamente el estado que crea el remedio de esta pieza: en cuanto B existe, el
    buzón compartido devuelve dos.
    """
    _censo(monkeypatch, [
        _registro("A", nif="11111111H", email="casa@ejemplo.es"),
        _registro("B", nif="22222222J", email="casa@ejemplo.es"),
    ])
    r = sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")
    assert r.id == "B"
    assert r.por == "nif"
    assert r.resuelta


def test_h03_el_orden_de_los_resultados_no_cambia_la_decision(monkeypatch):
    """La misma pregunta, con el CRM devolviendo las filas al revés, da lo mismo."""
    fichas = [
        _registro("A", nif="11111111H", email="casa@ejemplo.es"),
        _registro("B", nif="22222222J", email="casa@ejemplo.es"),
    ]
    _censo(monkeypatch, fichas, orden_inverso=True)
    r = sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")
    assert (r.id, r.por) == ("B", "nif")


def test_el_nif_unico_fuera_del_conjunto_del_email_sigue_siendo_conflicto(monkeypatch):
    """Si el NIF apunta a una ficha que el buzón no incluye, son dos identidades: se para."""
    _censo(monkeypatch, [
        _registro("A", nif="11111111H", email="casa@ejemplo.es"),
        _registro("Z", nif="22222222J", email="otro@ejemplo.es"),
    ])
    r = sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")
    assert r.conflicto is not None
    assert not r.resuelta


def test_varias_fichas_por_nif_sigue_siendo_ambiguo(monkeypatch):
    """Lo que no cambia: si el criterio FUERTE es múltiple, no hay nada que desempate."""
    _censo(monkeypatch, [
        _registro("A", nif="11111111H", email="a@ejemplo.es"),
        _registro("B", nif="11111111H", email="b@ejemplo.es"),
    ])
    r = sr.resolver_parte(ELEM, nif="11111111H")
    assert set(r.ambiguo) == {"A", "B"}


def test_una_consulta_fallida_manda_sobre_todo_lo_demas(monkeypatch):
    """`sin_comprobar` conserva su precedencia. La R1 lo intentó refutar y no pudo."""
    _censo(monkeypatch, [_registro("A", nif="11111111H", email="casa@ejemplo.es")],
           falla="email")
    r = sr.resolver_parte(ELEM, nif="11111111H", email="casa@ejemplo.es")
    assert r.sin_comprobar
    assert not r.resuelta


# ---------------------------------------------------------------------------
# §1 — los tres estados de un documento (R1/H-01)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nif_raro", [" -- . ", "---", "  ·  "])
def test_h01_un_nif_no_interpretable_no_cae_a_la_politica_de_email(monkeypatch, nif_raro):
    """Se aportó un documento; que no sobreviva a la canonicalización no es «no se aportó».

    `_canonizar_documento(" -- . ")` devuelve `""`, y con eso la versión anterior **omitía la
    consulta por NIF** y resolvía por email: la sonda de la R1 vinculó la ficha ajena y le
    escribió el CP del otro. La pérdida de información al normalizar no puede degradar un dato
    aportado hasta activar otro criterio en silencio.
    """
    _censo(monkeypatch, [_registro("A", nif="11111111H", email="casa@ejemplo.es")])
    r = sr.resolver_parte(ELEM, nif=nif_raro, email="casa@ejemplo.es")

    assert r.id is None, "resolvió a una ficha con un documento que no se puede comparar"
    assert not r.resuelta
    assert "interpretable" in (r.motivo or "").lower(), r.motivo


def test_un_nif_ausente_de_verdad_si_usa_la_politica_de_email(monkeypatch):
    """El otro lado: sin nada que contrastar, el email es lo único posible. No cambia."""
    _censo(monkeypatch, [_registro("A", nif="11111111H", email="casa@ejemplo.es")])
    r = sr.resolver_parte(ELEM, email="casa@ejemplo.es")
    assert (r.id, r.por) == ("A", "email")


def test_sin_nif_y_con_varias_fichas_en_el_buzon_es_ambiguo(monkeypatch):
    """Sin criterio fuerte, dos fichas en el buzón no se desempatan."""
    _censo(monkeypatch, [
        _registro("A", nif="11111111H", email="casa@ejemplo.es"),
        _registro("B", nif="22222222J", email="casa@ejemplo.es"),
    ])
    r = sr.resolver_parte(ELEM, email="casa@ejemplo.es")
    assert set(r.ambiguo) == {"A", "B"}


# ---------------------------------------------------------------------------
# §2.2 — NIF utilizable que no casó ninguna ficha
# ---------------------------------------------------------------------------


def test_aper71_el_buzon_compartido_con_nif_distinto_crea_ficha_nueva(monkeypatch):
    """**El caso que da nombre a `[APER-71]`.**

    B tiene NIF propio que no existe en el CRM y comparte el correo doméstico con A. La ficha
    de A tiene un NIF utilizable y distinto: son dos personas. Se crea la de B; no se toca la
    de A.
    """
    _censo(monkeypatch, [_registro("A", nif="11111111H", email="casa@ejemplo.es")])
    r = sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")

    assert r.id is None and r.por is None
    assert r.resuelta, "no existe y se puede crear: no es un estado de incertidumbre"
    assert not r.conflicto and not r.ambiguo


def test_la_ficha_del_buzon_sin_nif_para_en_vez_de_crear(monkeypatch):
    """Sin NIF en la ficha no se puede distinguir «la misma sin registrar» de «otra».

    Fallar cerrado cuesta una intervención manual; fusionar dos personas corrompe la ficha de
    un cliente y se descubre tarde. Es la política que `_exigir_identidad_cierta` ya declara.
    """
    _censo(monkeypatch, [_registro("A", email="casa@ejemplo.es")])
    r = sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")

    assert not r.resuelta
    assert r.ambiguo or r.motivo


def test_h02_un_nif_igual_escrito_de_otra_forma_para_en_vez_de_duplicar(monkeypatch):
    """`12.345.678-z` y `12345678Z` son **el mismo documento**.

    Comparar los textos elegiría «difiere → crear» y **duplicaría una ficha legítima**;
    comparar las formas canónicas elige «coincide → para». La rev. 1 admitía las dos lecturas
    con efectos opuestos sobre la misma identidad.

    Que la consulta por NIF no la encontrase y el email sí es precisamente la señal de que algo
    no cuadra: no se adivina.
    """
    fichas = [_registro("A", nif="12.345.678-z", email="casa@ejemplo.es")]

    def fake(elemento, propiedad, valor, *, operador="equal", limite=5, properties=()):
        # El CRM busca por el valor LITERAL: con separadores no encuentra nada (medido
        # contra el tenant el 2026-09-04, docstring de `_canonizar_documento`).
        if propiedad == "nif_cif":
            return sr.Consulta(registros=[f for f in fichas
                                          if str(sr._values_dict(f).get("nif_cif")) == valor])
        return sr.Consulta(registros=[f for f in fichas
                                      if str(sr._values_dict(f).get("email")) == valor])

    monkeypatch.setattr(sr, "_buscar_registros", fake)
    r = sr.resolver_parte(ELEM, nif="12345678Z", email="casa@ejemplo.es")

    assert r.id is None, "duplicó una ficha legítima por comparar los textos"
    assert not r.resuelta


def test_para_si_alguna_ficha_del_buzon_no_queda_descartada(monkeypatch):
    """Crear exige que **todas** las fichas del buzón tengan NIF utilizable y distinto.

    Con dos fichas en el correo, una con NIF distinto y otra sin NIF, la segunda deja la
    pregunta abierta y la respuesta es parar — no «la mayoría dice que cree».
    """
    _censo(monkeypatch, [
        _registro("A", nif="11111111H", email="casa@ejemplo.es"),
        _registro("C", email="casa@ejemplo.es"),
    ])
    r = sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")
    assert not r.resuelta


def test_la_consulta_por_email_pide_tambien_el_nif(monkeypatch):
    """La tabla del §2.2 necesita el NIF de cada ficha del buzón, y sin una llamada más.

    `_buscar_registros` ya acepta `properties=` extra; la R1 lo verificó ejecutándolo con HTTP
    simulado. Si el NIF no viaja en esa consulta, la tabla no puede decidir y la función
    degradaría a la política vieja **sin que ningún otro test lo note**.
    """
    llamadas = _censo(monkeypatch, [_registro("A", nif="11111111H", email="casa@ejemplo.es")])
    sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")

    por_email = [c for c in llamadas if c[0] == "email"]
    assert por_email, "no se consultó por email"
    assert "nif_cif" in por_email[0][2], f"la consulta por email no pidió el NIF: {por_email[0]}"


# ---------------------------------------------------------------------------
# §2.3 — la reejecución converge (R1/H-03)
# ---------------------------------------------------------------------------


def test_la_segunda_corrida_sobre_el_mismo_yaml_converge(monkeypatch):
    """Tras crear B, **las dos partes se siguen resolviendo**. Es la propiedad que la rev. 1
    rompía: su remedio dejaba el expediente bloqueado a partir de la segunda corrida."""
    censo = [_registro("A", nif="11111111H", email="casa@ejemplo.es")]
    _censo(monkeypatch, censo)

    # Primera corrida: B no existe y se crea.
    assert sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es").resuelta
    censo.append(_registro("B", nif="22222222J", email="casa@ejemplo.es"))

    # Segunda: las dos resuelven a su ficha, con el buzón devolviendo dos.
    ra = sr.resolver_parte(ELEM, nif="11111111H", email="casa@ejemplo.es")
    rb = sr.resolver_parte(ELEM, nif="22222222J", email="casa@ejemplo.es")
    assert (ra.id, rb.id) == ("A", "B"), f"no converge: {ra} / {rb}"


def test_un_tercer_firmante_del_mismo_buzon_tambien_resuelve(monkeypatch):
    """Tres partes en un correo familiar no son un caso de laboratorio."""
    _censo(monkeypatch, [
        _registro("A", nif="11111111H", email="casa@ejemplo.es"),
        _registro("B", nif="22222222J", email="casa@ejemplo.es"),
        _registro("C", nif="33333333P", email="casa@ejemplo.es"),
    ])
    r = sr.resolver_parte(ELEM, nif="33333333P", email="casa@ejemplo.es")
    assert (r.id, r.por) == ("C", "nif")


# ---------------------------------------------------------------------------
# El mensaje que ve el letrado tiene que decir la verdad
# ---------------------------------------------------------------------------


def test_el_error_de_un_nif_no_interpretable_no_habla_de_varias_fichas(monkeypatch):
    """`_exigir_identidad_cierta` decía siempre «la busqueda devolvio VARIAS fichas».

    Para un NIF no interpretable eso es falso, y un mensaje falso manda a deduplicar en el CRM
    algo que no está duplicado.
    """
    _censo(monkeypatch, [_registro("A", nif="11111111H", email="casa@ejemplo.es")])
    r = sr.resolver_parte(ELEM, nif=" -- ", email="casa@ejemplo.es")

    with pytest.raises(sr.ConflictoDeIdentidad) as exc:
        sr._exigir_identidad_cierta(r, elemento=ELEM, nif=" -- ", email="casa@ejemplo.es")
    assert "VARIAS fichas" not in str(exc.value), str(exc.value)
