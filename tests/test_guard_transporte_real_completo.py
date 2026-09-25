"""El transporte REAL expone todo lo que el core le pide. Nada de esto lo ven los dobles.

Defecto que este guard existe para impedir, encontrado el 2026-09-21 releyendo el diff
de F2 **después** de que sus 92 tests estuvieran en verde:

> `refrescar` llama `entorno_exp.codicert.estados(...)` y `cosechar`
> `entorno_exp.codicert.certificado(...)`. El transporte que monta `entorno_real` —el
> ÚNICO que se usa en producción— exponía cuatro métodos: `credito`, `listar`,
> `enviar_burofax` y `enviar_eec`. Los dos que F2 estrenaba **no estaban**.

Los 92 tests pasaban porque todos inyectan un doble, y el doble sí los tiene. El camino
real habría muerto con `AttributeError` en la primera invocación de `codicert estado`.
Es la misma forma de fallo que [[feedback-la-pieza-inalcanzable-de-extremo-a-extremo]]:
verde completo sobre una etapa que no podía ejecutarse.

**Por qué el guard deriva la lista y no la escribe.** Una constante con los seis nombres
se desincroniza en cuanto alguien añada un séptimo, y entonces este fichero estaría
verde mientras el defecto vuelve. Se extrae por AST lo que el core **consume de verdad**
—todo `<algo>.codicert.<metodo>`— y se contrasta contra lo que el transporte real
**ofrece**. Así el guard cubre la frontera («el transporte está completo») y no el
ejemplo («faltaban estos dos»).
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path

import pytest

from core import codicert as _cod
from core import expedicion_certificada as exp

MODULO = Path(exp.__file__)


def _metodos_consumidos(puerto: str = "codicert") -> set[str]:
    """Todo `<algo>.<puerto>.<metodo>(...)` que aparece en el core.

    Casa `entorno_exp.codicert.estados(...)` y cualquier variante futura del nombre de
    la variable: lo que importa es el atributo del puerto de por medio.

    **Sirve para los dos puertos**, y eso no es generalidad gratuita: el defecto
    original (`estados`/`certificado` ausentes del transporte) es una propiedad del
    patrón —«un puerto inyectable cuyo doble está completo y cuya implementación real
    no»—, no del puerto de Codicert. `gestor` tiene la misma forma y ganó tres
    métodos remediando la R1. Cubrir uno solo sería remediar el ejemplo.
    """
    arbol = ast.parse(MODULO.read_text(encoding="utf-8"))
    consumidos: set[str] = set()
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Attribute)
                and isinstance(nodo.value, ast.Attribute)
                and nodo.value.attr == puerto):
            consumidos.add(nodo.attr)
    return consumidos


def test_el_gestor_real_ofrece_TODO_lo_que_cosechar_le_pide(monkeypatch):
    """El mismo guard sobre el OTRO puerto inyectable (la frontera de H-01)."""
    gestor = _transporte_real(monkeypatch, atributo="gestor")
    faltan = sorted(m for m in _metodos_consumidos("gestor")
                    if not callable(getattr(gestor, m, None)))
    assert not faltan, (
        f"`entorno_real` monta un gestor documental al que le faltan {faltan}, y "
        "`cosechar` los llama. Los dobles de los tests sí los tienen.")


def test_el_censo_del_gestor_no_esta_vacio():
    assert len(_metodos_consumidos("gestor")) >= 3, _metodos_consumidos("gestor")


def _transporte_real(monkeypatch, atributo: str = "codicert"):
    """El puerto que monta `entorno_real`, sin tocar la red.

    Se doblan `credenciales` y `acceso` —las dos únicas llamadas de red que hace— para
    quedarnos con el objeto que devuelve, que es lo que se examina.
    """
    monkeypatch.setattr(_cod, "credenciales", lambda plaza, entorno: ("u.bd", "clave"))
    monkeypatch.setattr(
        _cod, "acceso",
        lambda u, c, *, entorno, cliente=None: _cod.Ficha(token="t", vence=datetime.max))
    return getattr(exp.entorno_real(plaza="Madrid", entorno="sandbox"), atributo)


def test_el_core_consume_algo_del_transporte():
    """Control de que el extractor no devuelve vacío: un guard sobre el conjunto
    vacío es verde siempre y no prueba nada."""
    assert len(_metodos_consumidos()) >= 4, _metodos_consumidos()


def test_el_transporte_real_ofrece_TODO_lo_que_el_core_consume(monkeypatch):
    """El guard. Con la lista derivada, no escrita."""
    transporte = _transporte_real(monkeypatch)
    faltan = sorted(m for m in _metodos_consumidos()
                    if not callable(getattr(transporte, m, None)))
    assert not faltan, (
        f"`entorno_real` monta un transporte al que le faltan {faltan}, y el core los "
        "llama. Los dobles de los tests sí los tienen, así que esto NO lo detecta "
        "ninguna prueba de comportamiento: el camino real muere con AttributeError en "
        "la primera invocación.")


def test_el_guard_MUERDE_sobre_un_transporte_incompleto(monkeypatch):
    """El otro valor. Sin esto, el guard de arriba podría estar verde por vacío."""
    transporte = _transporte_real(monkeypatch)

    class Mutilado:
        """El transporte tal como estaba ANTES del arreglo: sin las dos de F2."""

        credito = listar = enviar_burofax = enviar_eec = staticmethod(lambda **kw: None)

    faltan = sorted(m for m in _metodos_consumidos()
                    if not callable(getattr(Mutilado(), m, None)))
    assert "estados" in faltan and "certificado" in faltan, (
        "el guard no detecta el defecto histórico que existe para impedir")
    # y sobre el real, ninguno de esos dos falta
    assert callable(getattr(transporte, "estados", None))
    assert callable(getattr(transporte, "certificado", None))


@pytest.mark.parametrize("metodo", ["credito", "listar", "estados", "certificado"])
def test_las_lecturas_del_transporte_real_llegan_al_modulo_de_transporte(monkeypatch,
                                                                         metodo):
    """No basta con que el método EXISTA: tiene que llamar a `core.codicert`.

    Un `def estados(self, id): pass` pasaría el guard de arriba y devolvería `None`,
    que es el mismo fallo con otra cara — `refrescar` recibiría un histórico vacío y
    daría por «sin hechos acreditados» un envío entregado.
    """
    llamadas: list[str] = []
    for nombre in ("credito", "listar", "estados", "certificado"):
        monkeypatch.setattr(_cod, nombre,
                            lambda *a, _n=nombre, **kw: llamadas.append(_n) or [])
    transporte = _transporte_real(monkeypatch)
    getattr(transporte, metodo)(*(["006a"] if metodo in ("estados", "certificado") else []))
    assert llamadas == [metodo]


def test_el_entorno_real_trae_el_OCR_REAL(monkeypatch):
    """El puerto que estrena la R2 de F3 (H-01): sin `ocr`, `preparar_aportables` para, y
    los dobles lo traen, así que esto NO lo ve ninguna prueba de comportamiento. Tiene que
    ser el adaptador de verdad —no `None`, no un doble—."""
    assert _transporte_real(monkeypatch, atributo="ocr") is exp._ocr_aportable


def test_descargar_adjunto_del_transporte_real_llega_al_modulo_de_transporte(monkeypatch):
    """La lectura que estrena F3. Mismo contrato que las cuatro de arriba: no basta con
    que exista; tiene que llamar a `core.codicert` con el envío y el nombre."""
    llamadas: list[tuple] = []
    monkeypatch.setattr(_cod, "descargar_adjunto",
                        lambda ficha, id_envio, nombre, *, entorno, cliente=None:
                        llamadas.append((id_envio, nombre, entorno)) or b"%PDF")
    transporte = _transporte_real(monkeypatch)
    assert transporte.descargar_adjunto("006a", "OVC.pdf") == b"%PDF"
    assert llamadas == [("006a", "OVC.pdf", "sandbox")]
