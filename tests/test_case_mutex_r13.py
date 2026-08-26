"""Las tres fronteras que R12 dejó abiertas — encontradas buscándolas a propósito.

## Cómo salieron

R13 preguntaba, como pregunta central: *¿queda alguna corrección de R12 que cierre el
ejemplo del informe y deje abierta la frontera?* Porque eso había pasado **tres rondas
seguidas** con la cota temporal (naïve → futuro → pasado).

Estas tres las encontré revisando mis propias correcciones con esa pregunta delante, no
esperando al informe. Las tres son de la misma familia y las tres viven **en el código que
R12 añadió**:

| # | La corrección de R12 | Lo que dejó fuera |
|---|---|---|
| H13-01 | la cota de desvío es simétrica… | …pero **no alcanza al reloj que usa `revalidar()`** |
| H13-02 | `revalidar()` mira el lease… | …**salvo si `ahora_fn` es `None`**, que es su valor por defecto |
| H13-03 | la pérdida se anota cuando el cuerpo falla… | …**solo si vino de una excepción**, no si el lease caducó |

**La lección, que es la misma por cuarta vez:** al remediar miro el camino que el revisor
describió y no el resto de caminos que llegan a la misma propiedad. Aquí la propiedad era
«ningún reloj sin acotar decide sobre el lease» y «una pérdida no puede evaporarse»; los
remedios de R12 las cumplían **en la vía del informe** y las incumplían en la de al lado.
"""
from __future__ import annotations

import json

import pytest

W = "W-R13TST"
AHORA = "2026-08-26T12:00:00Z"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


@pytest.fixture(autouse=True)
def _reloj_del_sistema_fijo(monkeypatch):
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: case_mutex._instante(AHORA))


def _caducar_en_disco(raiz):
    """Deja el lock con el MISMO nonce y el lease vencido hace una hora."""
    from core.casos.case_mutex import ruta_del_lock
    p = ruta_del_lock(W, raiz=raiz)
    estado = json.loads(p.read_text(encoding="utf-8"))
    estado["renewed_at"] = "2026-08-26T11:00:00Z"
    p.write_text(json.dumps(estado), encoding="utf-8")


# ==========================================================================
# H13-01 — la cota de desvío no alcanzaba al reloj de `revalidar()`
# ==========================================================================

class TestElRelojDeRevalidarTambienSeAcota:
    """R12 acotó `adquirir` y `renovar`. `revalidar()` quedó fuera.

    Y `revalidar()` es justo la función que el cuerpo llama **antes de publicar algo
    irreversible**: un `ahora_fn` roto le daba una garantía calculada contra un instante
    arbitrario.
    """

    def test_un_ahora_fn_absurdo_NO_da_garantia(self, raiz):
        from core.casos.case_mutex import tomado
        from core.casos.workspace_model import MutexPerdido
        visto = {}
        with pytest.raises(MutexPerdido):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz,
                        lease_seconds=60) as sesion:
                sesion.ahora_fn = lambda: "2000-01-01T00:00:00Z"
                visto["revalidar"] = sesion.revalidar()
                visto["perdido"] = sesion.perdido()
        assert visto["revalidar"] is False, (
            "revalidar() dio garantía calculando la caducidad contra un reloj de 2000: "
            "la cota simétrica no alcanzaba a esta vía (R13/H13-01)")
        assert visto["perdido"] is True

    def test_con_el_reloj_BUENO_sigue_dando_garantia(self, raiz):
        """Control negativo: acotar no puede convertirse en «decir que no siempre»."""
        from core.casos.case_mutex import tomado
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=600) as sesion:
            assert sesion.revalidar() is True


# ==========================================================================
# H13-02 — `ahora_fn=None` desactivaba la comprobación del lease
# ==========================================================================

class TestSinRelojNoHayGarantia:
    """El default era `None`, y con `None` la comprobación del lease se **saltaba**.

    O sea: una `SesionMutex` construida sin reloj volvía exactamente al comportamiento
    que R12/H12-02 declaró crítico. Un default que desactiva una comprobación de
    seguridad es fail-open, y este módulo lleva tres rondas diciendo que falla cerrado.
    """

    def test_una_sesion_sin_reloj_no_puede_afirmar_titularidad(self, raiz):
        from core.casos.case_mutex import SesionMutex, adquirir
        nonce = adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=1)
        _caducar_en_disco(raiz)
        with pytest.raises(TypeError):
            SesionMutex(w_code=W, nonce=nonce, raiz=raiz)

    def test_el_constructor_exige_el_reloj(self):
        """Que sea imposible construirla mal es mejor que comprobarlo dentro."""
        import dataclasses

        from core.casos.case_mutex import SesionMutex
        campos = {f.name: f for f in dataclasses.fields(SesionMutex)}
        assert campos["ahora_fn"].default is dataclasses.MISSING, (
            "`ahora_fn` tiene default: una sesión sin reloj se salta el lease")


# ==========================================================================
# H13-03 — la pérdida por CADUCIDAD se evaporaba
# ==========================================================================

def test_la_perdida_por_caducidad_tambien_se_anota(raiz):
    """R12/H12-04 anotaba la pérdida solo si venía de una **excepción**.

    Una pérdida por lease vencido —detectada por `revalidar()`— no deja `_causa`, así que
    con el cuerpo fallando la pérdida no llegaba al llamador por ninguna vía. Es la misma
    propiedad («una pérdida no se evapora») cumplida en un camino e incumplida en el otro.
    """
    from core.casos.case_mutex import tomado
    with pytest.raises(RuntimeError, match="EL DEL CUERPO") as exc:
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60) as sesion:
            _caducar_en_disco(raiz)
            sesion.revalidar()
            assert sesion.perdido(), "precondición: la caducidad marca la pérdida"
            raise RuntimeError("EL DEL CUERPO")
    notas = getattr(exc.value, "__notes__", [])
    assert any("[mutex]" in n for n in notas), (
        f"la pérdida por caducidad no llegó al llamador: notas={notas}")


def test_sin_perdida_sigue_sin_anotarse_nada(raiz):
    """Control negativo: una nota en el camino feliz sería ruido."""
    from core.casos.case_mutex import tomado
    with pytest.raises(RuntimeError) as exc:
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=600):
            raise RuntimeError("solo el del cuerpo")
    assert not any("[mutex]" in n for n in getattr(exc.value, "__notes__", []))
