"""Propiedades de `core/utils.py`: lo que el docstring PROMETE, sobre miles de entradas.

Estas no son unit tests con más ejemplos. Cada una comprueba una **propiedad universal
que el código ya afirma de sí mismo** — y la afirma en prosa, que es donde nadie la
verifica. Un unit test cubre los casos que se le ocurrieron a quien lo escribió; el
problema es que quien lo escribió es también quien escribió la función, así que los dos
comparten el mismo punto ciego. Eso es el test tautológico, y aquí lo que rompe la
tautología es que **los ejemplos no los elige nadie**.

## Lo que encontró el primer día (2026-09-06)

`normalize_es_phone` **no era idempotente**, con el docstring afirmándolo sin condición
desde el principio. Con un prefijo doble —`"0034 +34 600 111 222"`, o sea un copiar-pegar
de una firma de correo o de una ficha del CRM— devolvía `"+34600111222"`: con el `+34`
puesto, que es lo único que la función existe para quitar, y camino del
`HTTP 400 movil is incorrect`. Tres tests de ejemplo la cubrían y ninguno lo vio.

## La lección de método, que vale más que el bug

**`st.text()` dio verde falso.** Dos mil ejemplos aleatorios no aciertan jamás el prefijo
literal `"0034"`, así que la propiedad «pasaba» sin haberse ejercitado nunca. Una
estrategia genérica sobre una función que **bifurca por literales** no prueba nada: hay
que generar entradas *con la forma del dominio*. De ahí `telefono_es()`.

Corolario, y es la regla de esta casa aplicada a `hypothesis`: **una property test verde
no vale hasta que se ha visto roja.** Cada una de las de abajo mata al menos un mutante,
y el mutante está nombrado en su docstring.
"""

from __future__ import annotations

import re

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from core.utils import (
    _CASE_ID_NEW_PARTES,
    exigir_componente_de_ruta,
    neutralizar_case_id,
    normalize_es_phone,
    validate_case_id,
)

#: `deadline=None` porque en Windows el primer ejemplo paga el import y hypothesis lo
#: lee como test lento; `suppress_health_check` por los `.filter()` de las estrategias
#: de `case_id`, que descartan lo bastante como para disparar el aviso sin que eso
#: signifique que la estrategia sea mala.
AJUSTES = settings(
    max_examples=400,
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)


# --- Estrategias con FORMA de dominio ---------------------------------------
# Genéricas no sirven: ver el docstring del módulo.

_SEPARADORES = st.sampled_from(["", " ", "-", ".", "/", "(", ")", "  "])
_PREFIJOS_ES = st.sampled_from(["+34", "0034", "34"])


@st.composite
def telefono_es(draw) -> str:
    """Un teléfono español tal y como llega de verdad: con separadores y, a veces, el
    prefijo de país **repetido**. Esa repetición es el punto: es lo que produce un
    copiar-pegar de una firma o de una ficha, y es lo que `st.text()` no genera nunca.
    """
    bruto = ""
    for _ in range(draw(st.integers(min_value=0, max_value=3))):
        bruto += draw(_PREFIJOS_ES) + draw(_SEPARADORES)
    for digito in draw(st.text(alphabet="0123456789", min_size=1, max_size=9)):
        bruto += digito + draw(_SEPARADORES)
    return bruto


#: Alfabeto de un tramo libre del `case_id`: sin los caracteres que Windows prohíbe
#: (los rechaza `exigir_sin_caracteres_de_ruta`) y sin paréntesis, que delimitan la
#: referencia y partirían el tramo.
_ALFABETO_TRAMO = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,.-ºªñÑáéíóú"

_PREFIJO_CASO = st.from_regex(r"\A[A-Z][a-zA-Z][A-Z]{2}[0-9]{1,3}\Z")
_REFERENCIA = st.one_of(
    st.from_regex(r"\AW-[A-Z0-9]{6}\Z"),
    st.just("SIN REFERENCIA"),
)
_TRAMO_LIBRE = st.text(alphabet=_ALFABETO_TRAMO, min_size=1, max_size=30).filter(
    lambda t: t.strip() != ""
)


@st.composite
def case_id_nuevo(draw) -> tuple[str, str, str, str, str]:
    """Un `case_id` del formato nuevo **y sus cuatro tramos**, para poder aseverar
    sobre la dirección sin adivinar dónde estaba.
    """
    prefijo = draw(_PREFIJO_CASO)
    direccion = draw(_TRAMO_LIBRE)
    referencia = draw(_REFERENCIA)
    categoria = draw(_TRAMO_LIBRE)
    cid = f"{prefijo} - {direccion.strip()} ({referencia}) - {categoria.strip()}"
    return cid, prefijo, direccion.strip(), referencia, categoria.strip()


# --- normalize_es_phone -----------------------------------------------------


@AJUSTES
@given(telefono_es())
def test_normalize_es_phone_es_idempotente(bruto: str) -> None:
    """La promesa literal del docstring: `f(f(x)) == f(x)`.

    **Mutante que la mata:** cambiar el `while True:` de `normalize_es_phone` por un
    `if` (la implementación anterior al 2026-09-06). Contraejemplo mínimo con el que
    la property test la encontró: `"0034+34600111222"`.
    """
    una = normalize_es_phone(bruto)
    assert normalize_es_phone(una) == una, f"no idempotente sobre {bruto!r}: {una!r}"


@AJUSTES
@given(telefono_es())
def test_normalize_es_phone_nunca_devuelve_prefijo_de_pais(bruto: str) -> None:
    """El contrato REAL, que es más fuerte que la idempotencia y es el que le importa
    al CRM: la salida no lleva `+34` ni `0034`, porque el CRM los rechaza con
    `HTTP 400 movil is incorrect`.

    La idempotencia es una consecuencia; esto es la razón de ser de la función. Una
    implementación podría ser idempotente y seguir devolviendo el prefijo — por eso
    van las dos.

    **Mutante que la mata:** el mismo `if` en vez de `while`, o retirar la rama
    `startswith("0034")`.
    """
    salida = normalize_es_phone(bruto)
    assert not salida.startswith(("+34", "0034")), (
        f"{bruto!r} -> {salida!r}: sale con prefijo de país, que es lo que el CRM "
        f"rechaza y lo único que esta función existe para quitar"
    )


# --- neutralizar_case_id ----------------------------------------------------


@AJUSTES
@given(case_id_nuevo())
def test_neutralizar_case_id_devuelve_algo_que_sigue_siendo_valido(datos) -> None:
    """La promesa literal: «el resultado sigue siendo un `case_id` válido para
    `validate_case_id`».

    Importa porque el valor neutralizado viaja en el frontmatter de `06_Anonimizado/`
    y lo vuelve a leer el pipeline: si dejara de validar, la neutralización rompería
    el expediente en vez de protegerlo.

    **Mutante que la mata:** quitar el ` - ` entre `[DIRECCION]` y la referencia en el
    `return` de `neutralizar_case_id`.
    """
    cid, *_ = datos
    # Auto-comprobación de la ESTRATEGIA: si esto salta, el fallo es de los generadores
    # de arriba, no del código bajo prueba — y sin esto el test podría pasar en vacío.
    validate_case_id(cid)
    validate_case_id(neutralizar_case_id(cid))


@AJUSTES
@given(case_id_nuevo())
def test_neutralizar_case_id_no_deja_la_direccion(datos) -> None:
    """La dirección (el único tramo con PII) no sobrevive, y los otros tres sí.

    **Este aserto es estructural y no un `in`, y esa es la parte que enseña.** Lo
    escribí dos veces como `direccion not in salida` y saltó las dos, ninguna por un
    defecto del código: primero con `direccion='0000'` sobre `(W-000000)` —dentro de la
    REFERENCIA, que se conserva a propósito— y luego con `direccion='C'`, que está
    dentro del literal `[DIRECCION]`. Parchear el segundo caso habría dejado vivo un
    tercero.

    La frontera no era ninguno de los dos ejemplos: **«la dirección desapareció» no se
    puede expresar como substring** de un texto que contiene otros tramos y un
    marcador. Se expresa **reparseando la salida** y mirando qué hay en el hueco de la
    dirección — que además comprueba de paso que los otros tres tramos siguen intactos,
    o sea que la neutralización no se llevó por delante nada que no fuera suyo.

    **Mutante que lo mata:** devolver `m.group('direccion')` en vez de `[DIRECCION]`.
    """
    cid, prefijo, direccion, referencia, categoria = datos
    salida = neutralizar_case_id(cid)

    reparseada = _CASE_ID_NEW_PARTES.match(salida)
    assert reparseada is not None, f"{salida!r} ya no es un case_id parseable"
    assert reparseada.group("direccion") == "[DIRECCION]", (
        f"el hueco de la dirección contiene {reparseada.group('direccion')!r} y no el "
        f"marcador: eso es PII en el frontmatter de 06_Anonimizado/, que puede acabar "
        f"en un LLM externo (entrada: {cid!r})"
    )
    assert reparseada.group("prefijo") == prefijo
    assert reparseada.group("ref") == f"({referencia})"
    assert reparseada.group("categoria") == categoria


# --- exigir_componente_de_ruta ----------------------------------------------


@AJUSTES
@given(st.text(max_size=60))
def test_lo_que_pasa_el_guard_es_un_solo_componente(valor: str) -> None:
    """Lo que el guard deja pasar cumple TODAS sus promesas a la vez.

    Su docstring documenta tres propiedades perdidas en extracciones sucesivas —el «no
    vacío» (R1/H-02), los espacios al borde (R2/H-03) y los caracteres de control—, y
    cada una se recuperó por separado después de que faltara. Esta property las
    comprueba juntas, que es la única forma de que la cuarta no vuelva a colarse.

    **Mutante que la mata:** retirar cualquiera de las cuatro guardas de la función.
    """
    try:
        salida = exigir_componente_de_ruta(valor, campo="campo")
    except ValueError:
        return  # rechazar es una respuesta correcta; lo que se contrata es el ACEPTAR

    assert salida == valor
    assert salida.strip() == salida != "", f"{valor!r} pasó con espacios al borde o vacío"
    assert salida not in (".", ".."), f"{valor!r} pasó siendo una posición relativa"
    assert not re.search(r'[\\/:*?"<>|]', salida), f"{valor!r} pasó con carácter prohibido"
    assert not any(ord(c) < 32 for c in salida), f"{valor!r} pasó con carácter de control"


@AJUSTES
@given(
    st.text(alphabet="abcXYZ019", min_size=1, max_size=10),
    st.sampled_from(["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\x00", "\n", "\t"]),
    st.integers(min_value=0, max_value=10),
)
def test_el_guard_rechaza_lo_que_no_puede_ser_un_componente(
    base: str, veneno: str, corte: int
) -> None:
    """La dirección que importa para la seguridad: **inyectar** un separador o un
    carácter de control en cualquier posición hace que el guard lance, siempre.

    El test de arriba contrata lo que el guard acepta; este contrata lo que **no puede**
    aceptar. Un guard que nunca rechaza pasa el primero y muere aquí — es la guarda
    inerte, y en este repo ya ha aparecido más de una vez.

    **Mutante que lo mata:** convertir el `raise` de `exigir_sin_caracteres_de_ruta` en
    un `return valor`.
    """
    pos = min(corte, len(base))
    envenenado = base[:pos] + veneno + base[pos:]
    with pytest.raises(ValueError):
        exigir_componente_de_ruta(envenenado, campo="campo")


@AJUSTES
@given(st.sampled_from(["", " ", "   ", "\t", ".", "..", " . ", " .. "]))
def test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas(valor: str) -> None:
    """Los casos que el docstring nombra por su nombre porque ya se perdieron una vez.

    El `""` es H-02: al extraer `exigir_sin_caracteres_de_ruta` se quedó atrás la
    comprobación de vacío, y `ensure_case("")` convertía `CASOS_ROOT` **entero** en un
    expediente, con sus nueve subcarpetas dentro.

    **Mutante que lo mata:** retirar el `if not (valor or "").strip()`.
    """
    with pytest.raises(ValueError):
        exigir_componente_de_ruta(valor, campo="campo")
