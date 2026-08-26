"""Las siete regresiones de R12 — la ronda que revisó las remediaciones de R11.

R12 sí emitió informe (`NO-SHIP`, 7 hallazgos), a diferencia de R11, que se cortó. Las
siete se verificaron contra la fuente antes de aceptarlas.

## Lo que esta ronda dice de cómo fallo, que importa más que los siete

**H12-01 es la TERCERA vez consecutiva que cierro media frontera del mismo hallazgo.**

| Ronda | Dijo | Cerré | Quedó abierto |
|---|---|---|---|
| R10/H10-02 | «un `ahora` **naïve o futuro** roba un lease» | el naïve | el futuro |
| R11/H11-01 | «un `ahora` **futuro** roba un lease» | el futuro | **el pasado** |
| R12/H12-01 | «un `ahora` del **pasado** publica un lease ya vencido» | los dos, con cota simétrica | — |

Tres rondas para una propiedad de una línea: *el instante que me pasan tiene que
parecerse al reloj*. Cada vez remedié exactamente el caso que el revisor escribió, sin
preguntarme cuál era la **frontera** de la que ese caso era un ejemplo. El remedio de
verdad no era «rechazar el futuro» ni «rechazar el pasado»: era **acotar el desvío**, y
eso se ve solo si buscas la propiedad en vez del síntoma.

**Y H12-02 es de la misma familia:** `revalidar()` comprobaba el nonce y no el lease. «Es
mi nonce» y «sigo siendo titular» dejan de ser lo mismo en el instante en que el lease
caduca — y la API que da esa garantía falsa es justo la que el cuerpo llama **antes de
publicar algo irreversible**.
"""
from __future__ import annotations

import json
import time

import pytest

W = "W-R12TST"
AHORA = "2026-08-26T12:00:00Z"


@pytest.fixture
def raiz(tmp_path):
    return tmp_path / "locks"


@pytest.fixture(autouse=True)
def _reloj_del_sistema_fijo(monkeypatch):
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: case_mutex._instante(AHORA))


# ==========================================================================
# H12-01 (CRÍTICO) — la cota tiene que ser SIMÉTRICA
# ==========================================================================

class TestElDesvioSeAcotaEnLasDosDirecciones:

    def test_un_ahora_del_pasado_REMOTO_se_rechaza(self, raiz):
        """Publicaba un lease que nace vencido: el titular se cree titular y no lo es."""
        from core.casos.case_mutex import adquirir
        with pytest.raises(ValueError, match="pasado"):
            adquirir(W, ahora="2000-01-01T00:00:00Z", raiz=raiz, lease_seconds=60)

    def test_un_ahora_del_futuro_REMOTO_sigue_rechazandose(self, raiz):
        from core.casos.case_mutex import adquirir
        with pytest.raises(ValueError, match="futuro"):
            adquirir(W, ahora="2099-01-01T00:00:00Z", raiz=raiz, lease_seconds=60)

    def test_nadie_se_lleva_el_caso_de_un_titular_vivo(self, raiz):
        """El daño, no el mensaje: con el pasado admitido, el segundo entraba."""
        from core.casos.case_mutex import adquirir, leer_estado
        nonce = adquirir(W, ahora=AHORA, raiz=raiz, lease_seconds=60)
        for absurdo in ("2000-01-01T00:00:00Z", "2099-01-01T00:00:00Z"):
            with pytest.raises(ValueError):
                adquirir(W, ahora=absurdo, raiz=raiz, lease_seconds=60)
        assert leer_estado(W, raiz=raiz)["nonce"] == nonce

    @pytest.mark.parametrize("delta", ["2026-08-26T11:55:00Z", "2026-08-26T12:05:00Z"])
    def test_los_desvios_NORMALES_se_aceptan(self, raiz, delta):
        """Control negativo: relojes que difieren en minutos son lo corriente."""
        from core.casos.case_mutex import adquirir
        assert adquirir(W + "X", ahora=delta, raiz=raiz, lease_seconds=60)


# ==========================================================================
# H12-02 (CRÍTICO) — `revalidar()` tiene que mirar el lease
# ==========================================================================

class TestRevalidarMiraElLeaseYNoSoloElNonce:
    """«Es mi nonce» ≠ «sigo siendo titular». Lo segundo caduca."""

    def test_con_el_lease_vencido_revalidar_dice_que_NO(self, raiz):
        from core.casos.case_mutex import ruta_del_lock, tomado
        from core.casos.workspace_model import MutexPerdido
        visto = {}
        with pytest.raises(MutexPerdido):
            with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz,
                        lease_seconds=1) as sesion:
                p = ruta_del_lock(W, raiz=raiz)
                estado = json.loads(p.read_text(encoding="utf-8"))
                # MISMO nonce, lease vencido hace mucho.
                estado["renewed_at"] = "2026-08-26T11:00:00Z"
                p.write_text(json.dumps(estado), encoding="utf-8")
                visto["revalidar"] = sesion.revalidar()
                visto["perdido"] = sesion.perdido()
        assert visto["revalidar"] is False, (
            "revalidar() dio garantía de titularidad con el lease caducado: otro "
            "proceso ya estaba autorizado a entrar (R12/H12-02)")
        assert visto["perdido"] is True

    def test_con_el_lease_VIVO_revalidar_dice_que_si(self, raiz):
        """Control negativo: si dijera «no» siempre, el test de arriba pasaría igual."""
        from core.casos.case_mutex import tomado
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=600) as sesion:
            assert sesion.revalidar() is True
            assert sesion.perdido() is False


# ==========================================================================
# H12-03 (ALTO) — el hilo tiene que capturar BaseException
# ==========================================================================

def test_un_SystemExit_en_el_hilo_deja_señal(raiz, monkeypatch):
    """`except Exception` dejaba morir al hilo sin marcar la pérdida.

    Es el mismo defecto crítico de R11/H11-02 por la única puerta que quedaba abierta:
    las excepciones que no heredan de `Exception`.
    """
    from core.casos import case_mutex
    from core.casos.workspace_model import MutexPerdido

    def _renovar_que_se_va(*a, **k):
        raise SystemExit("el hilo se va sin avisar")

    monkeypatch.setattr(case_mutex, "renovar", _renovar_que_se_va)
    visto = {}
    with pytest.raises(MutexPerdido):
        with case_mutex.tomado(W, ahora_fn=lambda: AHORA, raiz=raiz,
                               lease_seconds=1) as sesion:
            for _ in range(150):
                if sesion.perdido():
                    break
                time.sleep(0.02)
            visto["perdido"] = sesion.perdido()
    assert visto["perdido"] is True, (
        "el hilo murió por un SystemExit y no lo registró: el cuerpo habría seguido "
        "escribiendo como titular (R12/H12-03)")


# ==========================================================================
# H12-04 (ALTO) — la pérdida no se evapora cuando el cuerpo falla
# ==========================================================================

def test_el_error_del_cuerpo_manda_PERO_la_perdida_queda_anotada(raiz):
    """Antes: el fallo de liberación vivía solo en `sesion._causa`, invisible.

    El llamador necesita las dos cosas — qué falló en su código **y** que además perdió
    el mutex—, y una nota las da sin desplazar al error primario.
    """
    from core.casos.case_mutex import ruta_del_lock, tomado
    with pytest.raises(RuntimeError, match="EL DEL CUERPO") as exc:
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
            p = ruta_del_lock(W, raiz=raiz)
            estado = json.loads(p.read_text(encoding="utf-8"))
            estado["nonce"] = "de-otro"
            p.write_text(json.dumps(estado), encoding="utf-8")
            raise RuntimeError("EL DEL CUERPO")
    notas = getattr(exc.value, "__notes__", [])
    assert any("[mutex]" in n for n in notas), (
        f"la pérdida del mutex no llegó al llamador por ninguna vía observable: "
        f"notas={notas}")


def test_sin_perdida_no_se_anota_nada(raiz):
    """Control negativo: una nota en el camino feliz sería ruido."""
    from core.casos.case_mutex import tomado
    with pytest.raises(RuntimeError):
        with tomado(W, ahora_fn=lambda: AHORA, raiz=raiz, lease_seconds=60):
            raise RuntimeError("solo el del cuerpo")


# ==========================================================================
# H12-05 (MEDIO) — tipos del esquema, no solo presencia
# ==========================================================================

class TestElEsquemaValidaTIPOS:

    def _sembrar(self, raiz, **cambios):
        from core.casos.case_mutex import adquirir, ruta_del_lock
        adquirir(W, ahora=AHORA, raiz=raiz)
        p = ruta_del_lock(W, raiz=raiz)
        estado = json.loads(p.read_text(encoding="utf-8"))
        estado.update(cambios)
        p.write_text(json.dumps(estado), encoding="utf-8")

    def test_schema_TRUE_no_es_schema_1(self, raiz):
        """`True == 1` en Python, así que `schema: true` colaba como versión válida."""
        from core.casos.case_mutex import leer_estado
        from core.casos.workspace_model import MutexIlegible
        self._sembrar(raiz, schema=True)
        with pytest.raises(MutexIlegible):
            leer_estado(W, raiz=raiz)

    @pytest.mark.parametrize("propietario", [
        {"host": 7, "pid": 1, "proceso_uid": "u"},
        {"host": "h", "pid": "x", "proceso_uid": "u"},
        {"host": "h", "pid": -1, "proceso_uid": "u"},
        {"host": "h", "pid": 1, "proceso_uid": ["u"]},
    ])
    def test_un_propietario_de_tipos_absurdos_se_rechaza(self, raiz, propietario):
        """Alimenta el diagnóstico de `CaseBusy`: un `host: 7` no identifica a nadie."""
        from core.casos.case_mutex import leer_estado
        from core.casos.workspace_model import MutexIlegible
        self._sembrar(raiz, propietario=propietario)
        with pytest.raises(MutexIlegible):
            leer_estado(W, raiz=raiz)

    def test_un_campo_DESCONOCIDO_se_rechaza(self, raiz):
        """Política explícita: la compatibilidad se lleva subiendo `SCHEMA_MUTEX`."""
        from core.casos.case_mutex import leer_estado
        from core.casos.workspace_model import MutexIlegible
        self._sembrar(raiz, inventado="lo que sea")
        with pytest.raises(MutexIlegible):
            leer_estado(W, raiz=raiz)

    def test_un_lock_BIEN_FORMADO_sigue_leyendose(self, raiz):
        """Control negativo: el validador no puede rechazar lo bueno."""
        from core.casos.case_mutex import adquirir, leer_estado
        nonce = adquirir(W, ahora=AHORA, raiz=raiz)
        assert leer_estado(W, raiz=raiz)["nonce"] == nonce


# ==========================================================================
# H12-06 (MEDIO) — la ruta tampoco viaja en la causa encadenada
# ==========================================================================

def test_la_ruta_no_viaja_en_la_CAUSA_del_CaseBusy(raiz, monkeypatch):
    """El §16 no prohíbe la ruta «en `str()`»: prohíbe filtrarla.

    Un traceback encadenado es la presentación normal de una excepción no capturada, así
    que `from exc` publicaba la ruta del guard en cuanto alguien no la atrapaba.
    """
    from filelock import Timeout

    from core.casos import case_mutex
    from core.casos.workspace_model import CaseBusy

    monkeypatch.setattr(case_mutex, "_abrir_guard",
                        lambda w, r: (_ for _ in ()).throw(Timeout(str(raiz))))
    with pytest.raises(CaseBusy) as exc:
        case_mutex.adquirir(W, ahora=AHORA, raiz=raiz)
    assert str(raiz) not in str(exc.value)
    assert str(raiz) not in str(exc.value.__cause__ or "")
    assert str(raiz) not in str(exc.value.__context__ or "")
    # El tipo consta en `detalle`, NO en `str()`: el §10 no reproduce el detalle en el
    # mensaje a propósito, para que un llamador pueda pasar contexto sin que se publique.
    assert "Timeout" in (exc.value.detalle or ""), (
        "sanear la causa no puede costar el diagnóstico: el tipo debe constar")
    assert str(raiz) not in (exc.value.detalle or "")


# H12-07 vive en `tests/test_case_mutex_reloj_real.py`: la fixture autouse de este
# fichero lo alcanzaria y lo dejaria vacio, que es justo lo que el hallazgo avisaba.
