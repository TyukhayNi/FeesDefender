"""Modelo puro del workspace dual: `CaseRef`, modos, capacidades y errores.

Spec: docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md
§5.1 (identidad), §5.2 (modos), §5.3 (el valor validado), §5.4 (capacidades),
§10 (los doce códigos de error), §16 (los mensajes no llevan rutas locales).
Plan: docs/superpowers/plans/2026-07-29-dual-workspace-fase0-fase1.md, Task 4.

Esta pieza es PURA: no toca disco, no lee reloj, no resuelve nada. Solo responde
«¿dónde se trabaja y qué está permitido?» como dato.
"""
from __future__ import annotations

import dataclasses
import re

import pytest

from core.casos import workspace_model as wm

# --------------------------------------------------------------------------
# La matriz del §5.4, transcrita ENTERA y a mano desde la spec.
#
# Se escribe aquí completa a propósito, y no derivada de `CAPACIDADES_POR_MODO`:
# un test que calcule lo esperado a partir del dato que valida no prueba nada.
# La lección viene de R6/H6-07 — una prueba vale lo que vale su capacidad de
# morir cuando la fuente y el código discrepan.
#
# Lectura de la tabla del §5.4, fila por fila:
#   drive_active   -> Leer sí; Ingestar/generar sí; Mutar canon «según operación»
#                     (el modo lo concede, la operación decide); cerrar = checkout.
#   local_checkout -> Leer sí; ingestar/generar «sí, en local»; mutar canon NO
#                     «durante el trabajo»; cerrar = checkin.
#   local_scratch  -> Leer sí; ingestar/generar sí; mutar canon no; cerrar = promover.
#   bloqueado      -> «Solo diagnóstico autorizado» / no / no / resolver conflicto.
#
# DECISIÓN DE DISEÑO, declarada porque la spec deja el borde abierto: los dos
# modos `blocked_*` no conceden NADA, ni `read_case`. El §5.2 dice que son
# «resultados de resolución, no workspaces utilizables», y el «diagnóstico
# autorizado» del §5.4 es una autorización aparte —`diagnostico=True` en el
# resolver del Task 7—, no una capacidad del modo. Si la revisión lo refuta, lo
# que cambia es esta tabla y su fila, no la forma del contrato.
# --------------------------------------------------------------------------
MATRIZ_ESPERADA = {
    "drive_active": {
        "read_case", "write_case", "ingest", "generate_derivatives",
        "mutate_canonical", "checkout",
    },
    "local_checkout": {
        "read_case", "write_case", "ingest", "generate_derivatives", "checkin",
    },
    "local_scratch": {
        "read_case", "write_case", "ingest", "generate_derivatives", "promote",
    },
    "blocked_foreign_checkout": set(),
    "blocked_conflict": set(),
}

# Los doce del §10, en su forma de código.
CODIGOS_ESPERADOS = {
    "CASE_LOCKED", "LOCAL_WORKSPACE_MISSING", "LOCK_MISMATCH", "CASE_CONFLICT",
    "AMBIGUOUS_CASE", "RUNTIME_CANNOT_ACCESS_WORKSPACE", "CAPABILITY_DENIED",
    "CANONICAL_MUTATION_DEFERRED", "LOCK_NOT_MINE", "CHECKOUT_CANCELLED_ELSEWHERE",
    "WORKSPACE_UNDER_CATALOG_ROOT", "AUDIT_BASELINE_MISSING",
}

_RE_UNIDAD_WINDOWS = re.compile(r"[A-Za-z]:[\\/]")


def _ws(modo, **kw):
    """Un `CaseWorkspace` válido del modo pedido, para no repetir el constructor."""
    modo = wm.WorkspaceMode(modo)
    base = dict(
        case_ref=wm.CaseRef(w_code="W-TEST01"),
        mode=modo,
        working_root=None if modo.name.startswith("BLOCKED") else __import__("pathlib").Path("X"),
        canonical_ref=None,
        checkout_user=None,
        checkout_maquina=None,
        checkout_nonce=None,
        checkout_timestamp=None,
        validado_en="2026-08-24T00:00:00Z",
        procedencia="test",
    )
    base.update(kw)
    return wm.CaseWorkspace(**base)


# ------------------------------------------------------------------ §5.1 CaseRef

def test_caseref_sin_identidad_lanza():
    with pytest.raises(ValueError):
        wm.CaseRef()


def test_caseref_solo_con_canonical_ref_no_es_identidad():
    """El §5.1: «el nombre de carpeta es una presentación y no basta como
    identidad». La referencia canónica de Drive tampoco: hace falta case_id o
    W-code."""
    with pytest.raises(ValueError):
        wm.CaseRef(canonical_ref="drive://algo")


@pytest.mark.parametrize("crudo,esperado", [
    (" w-test01 ", "W-TEST01"),
    ("W-Test01", "W-TEST01"),
    ("W-TEST01", "W-TEST01"),
])
def test_caseref_normaliza_el_w_code(crudo, esperado):
    assert wm.CaseRef.normalizar(crudo) == esperado
    assert wm.CaseRef(w_code=crudo).w_code == esperado


def test_caseref_es_inmutable():
    ref = wm.CaseRef(w_code="W-TEST01")
    with pytest.raises(dataclasses.FrozenInstanceError):
        ref.w_code = "W-OTRO"


def test_caseref_vacio_en_blanco_no_cuenta_como_identidad():
    """Una cadena de espacios no es un W-code: si contara, `CaseRef("  ")`
    pasaría la validación y el catálogo buscaría un caso inexistente."""
    with pytest.raises(ValueError):
        wm.CaseRef(w_code="   ")


def test_caseref_normaliza_un_w_code_en_blanco_a_none_no_a_cadena_vacia():
    """El hueco que encontró un mutante superviviente del arnés del Task 4.

    Con `case_id` presente, el `ValueError` NO salta, así que la única defensa
    contra un `w_code = ""` colándose en la identidad es que la normalización lo
    convierta en `None`. Y un `""` sería dañino: dos `CaseRef` del mismo caso
    —uno construido con `w_code="  "` y otro sin `w_code`— dejarían de ser
    iguales, y el catálogo buscaría por cadena vacía.

    El test anterior no lo cubría: pasaba por falsedad de `""`, no por la
    normalización. Es la misma figura que R6/H6-07 a escala pequeña.
    """
    ref = wm.CaseRef(case_id="BaX - Calle Falsa 1 (W-A1) - Bad debt", w_code="   ")
    assert ref.w_code is None
    assert ref == wm.CaseRef(case_id="BaX - Calle Falsa 1 (W-A1) - Bad debt")


# -------------------------------------------------------- §5.2 / §5.4 la matriz

def test_los_modos_son_los_cinco_del_spec():
    assert {m.value for m in wm.WorkspaceMode} == set(MATRIZ_ESPERADA)


def test_las_capacidades_son_las_ocho_del_spec():
    assert {c.value for c in wm.Capability} == {
        "read_case", "write_case", "ingest", "generate_derivatives",
        "mutate_canonical", "checkout", "checkin", "promote",
    }


def test_la_matriz_de_capacidades_es_la_del_spec():
    """La tabla del §5.4 como DATO, comparada entera contra la transcripción a
    mano de arriba. Cualquier deriva —una capacidad de más o de menos en
    cualquier modo— pone este test rojo."""
    real = {m.value: {c.value for c in caps}
            for m, caps in wm.CAPACIDADES_POR_MODO.items()}
    assert real == MATRIZ_ESPERADA


def test_la_matriz_cubre_todos_los_modos():
    """Un modo sin fila en la tabla es un `KeyError` en producción, no un
    default seguro."""
    assert set(wm.CAPACIDADES_POR_MODO) == set(wm.WorkspaceMode)


@pytest.mark.parametrize("modo", ["blocked_foreign_checkout", "blocked_conflict"])
@pytest.mark.parametrize("cap", ["write_case", "ingest", "generate_derivatives",
                                 "mutate_canonical", "checkout", "checkin", "promote"])
def test_los_modos_bloqueados_no_conceden_nada_mutante(modo, cap):
    assert not _ws(modo).permite(wm.Capability(cap))


def test_local_checkout_no_concede_mutate_canonical():
    """§5.4: «No durante trabajo». Es la invariante que impide que una copia
    prestada escriba en el canon."""
    assert not _ws("local_checkout").permite(wm.Capability.MUTATE_CANONICAL)


def test_local_scratch_no_concede_mutate_canonical():
    assert not _ws("local_scratch").permite(wm.Capability.MUTATE_CANONICAL)


def test_solo_drive_active_cierra_ciclo_con_checkout():
    assert _ws("drive_active").permite(wm.Capability.CHECKOUT)
    assert not _ws("local_checkout").permite(wm.Capability.CHECKOUT)
    assert _ws("local_checkout").permite(wm.Capability.CHECKIN)
    assert _ws("local_scratch").permite(wm.Capability.PROMOTE)


@pytest.mark.parametrize("modo,mutable", [
    ("drive_active", True),
    ("local_checkout", True),
    ("local_scratch", True),
    ("blocked_foreign_checkout", False),
    ("blocked_conflict", False),
])
def test_es_mutable(modo, mutable):
    assert _ws(modo).es_mutable is mutable


# ------------------------------------------------------- §5.3 el valor validado

def test_working_root_ausente_con_modo_mutable_es_incoherente():
    """§5.3: `working_root` existe «solo cuando el runtime puede acceder». Un
    modo mutable sin raíz de trabajo es un estado que ningún motor puede honrar,
    así que no se construye."""
    with pytest.raises(ValueError):
        _ws("drive_active", working_root=None)


def test_working_root_presente_en_modo_bloqueado_es_incoherente():
    """La simétrica, que es la que se olvida: un modo `blocked_*` con raíz de
    trabajo invita a que un llamador la use «solo para leer»."""
    import pathlib
    with pytest.raises(ValueError):
        _ws("blocked_conflict", working_root=pathlib.Path("X"))


def test_el_workspace_es_inmutable():
    ws = _ws("drive_active")
    with pytest.raises(dataclasses.FrozenInstanceError):
        ws.mode = wm.WorkspaceMode.LOCAL_SCRATCH


def test_las_capacidades_se_derivan_del_modo_y_no_se_inyectan():
    """Si el constructor aceptara `capabilities` sueltas, un llamador podría
    fabricarse un `blocked_*` con `MUTATE_CANONICAL`. La tabla es la fuente."""
    ws = _ws("local_checkout")
    assert ws.capabilities == wm.CAPACIDADES_POR_MODO[wm.WorkspaceMode.LOCAL_CHECKOUT]
    with pytest.raises(TypeError):
        _ws("blocked_conflict", capabilities=frozenset(wm.Capability))


def test_exigir_lanza_capability_denied_con_su_codigo():
    ws = _ws("local_checkout")
    with pytest.raises(wm.CapabilityDenied) as exc:
        ws.exigir(wm.Capability.MUTATE_CANONICAL)
    assert exc.value.codigo == "CAPABILITY_DENIED"


def test_exigir_no_lanza_cuando_el_modo_concede():
    assert _ws("drive_active").exigir(wm.Capability.INGEST) is None


# ------------------------------------------------------------- §10 los errores

def test_estan_los_doce_codigos_del_spec():
    reales = {c.codigo for c in wm.errores_conocidos()}
    assert reales == CODIGOS_ESPERADOS


def test_toda_subclase_desciende_de_workspace_error():
    for clase in wm.errores_conocidos():
        assert issubclass(clase, wm.WorkspaceError)


@pytest.mark.parametrize("clase", sorted(wm.errores_conocidos(), key=lambda c: c.codigo))
def test_ningun_mensaje_de_error_lleva_una_ruta_local(clase):
    """§16 y §10.3: el mensaje se construye con W-code, código, titular y fecha.
    Nunca con la ruta local, que vive solo en el registro privado.

    Se le pasa una ruta de Windows COMO dato para comprobar que el mensaje no la
    reproduce por accidente al formatear.
    """
    err = clase(
        w_code="W-TEST01",
        titular="otro.usuario",
        maquina="OTRA-MAQUINA",
        fecha="2026-08-24T10:00:00Z",
        detalle=r"C:\Users\alguien\Desktop\caso",
    )
    texto = str(err)
    assert not _RE_UNIDAD_WINDOWS.search(texto), texto
    assert "\\" not in texto, texto
    assert "W-TEST01" in texto
    assert err.codigo in CODIGOS_ESPERADOS


def test_el_error_dice_que_no_hubo_efecto_cuando_no_lo_hubo():
    """§10: «los mensajes deben indicar que no se produjo ningún efecto cuando
    así sea», y no pueden sugerir reintentar contra Drive como atajo."""
    err = wm.CaseLocked(w_code="W-TEST01", titular="otro", maquina="M",
                        fecha="2026-08-24T10:00:00Z", sin_efecto=True)
    texto = str(err).lower()
    assert "sin efecto" in texto or "no se produjo" in texto
    assert "reintenta" not in texto
