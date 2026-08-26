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

# Los doce del §10 más los tres del registro (Task 5), en su forma de código.
#
# Los tres últimos NO estaban en la tabla del §10 de la spec, y se añaden con ella:
# `REGISTRY_UNREADABLE` lo fuerza R7/H7-02 —el fallo cerrado necesita un error que el
# resolver pueda propagar en vez de un `[]` indistinguible de «no había nada»—, y los
# otros dos los pide el contrato del Task 5. Viven en el MODELO y no en el registro
# porque el resolver los muestra al usuario: así les aplican las reglas de mensaje del
# §10 y los ocho canarios del §16. Definirlos en el registro los habría dejado fuera de
# `errores_conocidos()` y por tanto fuera de los canarios, que es el hueco que R7
# castigó en H7-12.
CODIGOS_ESPERADOS = {
    "CASE_LOCKED", "LOCAL_WORKSPACE_MISSING", "LOCK_MISMATCH", "CASE_CONFLICT",
    "AMBIGUOUS_CASE", "RUNTIME_CANNOT_ACCESS_WORKSPACE", "CAPABILITY_DENIED",
    "CANONICAL_MUTATION_DEFERRED", "LOCK_NOT_MINE", "CHECKOUT_CANCELLED_ELSEWHERE",
    "WORKSPACE_UNDER_CATALOG_ROOT", "AUDIT_BASELINE_MISSING",
    "REGISTRY_UNREADABLE", "SCHEMA_NO_SOPORTADO", "RUTA_YA_REGISTRADA",
    # Los tres del mutex interproceso (Plan 2 de V1, decision D2 del §24). El §10 pasa
    # de 15 a 18 codigos, y la tabla lo admite sin reabrir nada porque dice «Como
    # minimo». `CASE_BUSY` NO es `CASE_LOCKED`: aquel dice que el caso esta prestado a
    # otra maquina segun el canon; este, que otro proceso de la mia lo esta tocando
    # ahora. Con un solo codigo, el operador no podria distinguir «espera dos minutos»
    # de «llama a quien lo tiene prestado».
    "CASE_BUSY", "MUTEX_NOT_MINE", "MUTEX_ILEGIBLE",
    # R11/H11-02: perder el mutex a mitad NO es «te equivocas de dueño». El §10
    # pasa de 18 a 19 codigos.
    "MUTEX_PERDIDO",
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

def test_estan_todos_los_codigos_declarados():
    reales = {c.codigo for c in wm.errores_conocidos()}
    assert reales == CODIGOS_ESPERADOS


def test_toda_subclase_desciende_de_workspace_error():
    for clase in wm.errores_conocidos():
        assert issubclass(clase, wm.WorkspaceError)


# Los ocho canarios de R7/H7-12. El canario original era uno solo —una ruta de
# Windows— y sus dos asertos (`[A-Za-z]:[\/]` y la contrabarra) cazaban 3 de los 8
# casos: Windows con las dos barras y UNC. Se le escapaban POSIX puro, la ruta
# relativa y las tres de PII del §16, y ademas nunca se INYECTABAN, asi que el
# hueco era doble. Medido antes de ampliarlo.
#
# Lo que NO se prueba, a proposito: que el mensaje no lleve un nombre. El §10.3 y
# el §5.3 mandan construirlo con «W-code, codigo, titular y fecha», o sea que el
# `titular` va DENTRO por diseno. Un canario de «ningun nombre» contradiria la
# fuente en vez de protegerla. El vector de fuga es `detalle`.
_CANARIOS_FUGA = {
    "windows_backslash": "C:" + chr(92) + "Users" + chr(92) + "alguien" + chr(92) + "caso",
    "windows_barra":     "C:/Users/alguien/caso",
    "unc":               chr(92) * 2 + "servidor" + chr(92) + "casos",
    "posix":             "/home/alguien/caso",
    "relativa":          "../Desktop/caso",
    "email":             "alguien@example.com",
    "direccion":         "Calle Mayor 3, 2 B",
    "nombre_en_detalle": "Fulanita Menganez",
}


@pytest.mark.parametrize("clase", sorted(wm.errores_conocidos(), key=lambda c: c.codigo))
@pytest.mark.parametrize("canario", sorted(_CANARIOS_FUGA), ids=sorted(_CANARIOS_FUGA))
def test_ningun_mensaje_de_error_reproduce_lo_que_se_le_pasa_en_detalle(clase, canario):
    """§16 y §10.3: el mensaje se construye con W-code, código, titular y fecha.

    Nunca con la ruta local ni con PII, que viven solo en el registro privado. Se
    inyecta cada canario COMO dato en `detalle` y se exige que el mensaje no lo
    reproduzca al formatear — ni entero ni en un fragmento reconocible.
    """
    valor = _CANARIOS_FUGA[canario]
    err = clase(
        w_code="W-TEST01",
        titular="otro.usuario",
        maquina="OTRA-MAQUINA",
        fecha="2026-08-24T10:00:00Z",
        detalle=valor,
    )
    texto = str(err)
    assert valor not in texto, texto
    assert not _RE_UNIDAD_WINDOWS.search(texto), texto
    assert chr(92) not in texto, texto
    # Fragmentos que delatan una fuga parcial, no solo la copia literal.
    for fragmento in ("alguien", "servidor", "Desktop", "example.com", "Menganez",
                      "Calle Mayor"):
        assert fragmento not in texto, (fragmento, texto)
    assert "W-TEST01" in texto
    assert err.codigo in CODIGOS_ESPERADOS


@pytest.mark.parametrize("clase", sorted(wm.errores_conocidos(), key=lambda c: c.codigo))
def test_ningun_error_sugiere_reintentar_contra_drive(clase):
    """§10, la segunda regla de mensaje, sobre LAS DOCE y no sobre una.

    R7/H7-12: solo se probaba en `CaseLocked`. Un mensaje que empuje a reintentar
    contra Drive convierte un bloqueo en una carrera, así que la regla es de todas.
    """
    err = clase(w_code="W-TEST01", titular="otro", maquina="M",
                fecha="2026-08-24T10:00:00Z", sin_efecto=True)
    texto = str(err).lower()
    for empujon in ("reintenta", "reintentar", "vuelve a intentar", "prueba de nuevo",
                    "fuerza", "--force"):
        assert empujon not in texto, (empujon, texto)


def test_el_error_dice_que_no_hubo_efecto_cuando_no_lo_hubo():
    """§10: «los mensajes deben indicar que no se produjo ningún efecto cuando
    así sea», y no pueden sugerir reintentar contra Drive como atajo."""
    err = wm.CaseLocked(w_code="W-TEST01", titular="otro", maquina="M",
                        fecha="2026-08-24T10:00:00Z", sin_efecto=True)
    texto = str(err).lower()
    assert "sin efecto" in texto or "no se produjo" in texto
    assert "reintenta" not in texto


# --------------------------------------------------------------------------
# `LocalWorkspaceMissing` tambien es un `FileNotFoundError`
# --------------------------------------------------------------------------
#
# Medido al migrar el Task 6: **15 sitios de produccion** capturan
# `FileNotFoundError`, entre ellos `scripts/abrir_caso.py:162` y `:173`,
# `scripts/crm_ficha.py:60` y `core/intake_drive.py:297`. Cinco funciones lanzaban
# `FileNotFoundError` a mano cuando el caso no existia, y al migrarlas al error
# estructurado del §10 la excepcion se ESCAPABA de esos manejadores.
#
# La suite solo cazo 3 de esos caminos, que es exactamente el modo de fallo caro:
# un cambio de tipo de excepcion rompe manejadores que ningun test cubre.
#
# La herencia doble no es un parche de compatibilidad: «el workspace local no
# existe» ES una condicion de fichero ausente. Lo que estaba mal era tener dos
# vocabularios para lo mismo.


def test_local_workspace_missing_es_tambien_filenotfounderror():
    assert issubclass(wm.LocalWorkspaceMissing, FileNotFoundError)
    assert issubclass(wm.LocalWorkspaceMissing, wm.WorkspaceError)


def test_un_except_filenotfounderror_preexistente_sigue_capturandolo():
    """El contrato que protege los 15 manejadores de produccion."""
    try:
        raise wm.LocalWorkspaceMissing(w_code="W-TEST01")
    except FileNotFoundError as exc:
        assert exc.codigo == "LOCAL_WORKSPACE_MISSING"
    else:
        pytest.fail("no lo capturo `except FileNotFoundError`")


def test_los_demas_errores_NO_son_filenotfounderror():
    """Solo este mapea a «no encontrado». Heredar en bloque seria mentir:
    un caso PRESTADO existe, y tratarlo como ausente es justo la confusion que
    todo este diseno intenta deshacer."""
    for clase in wm.errores_conocidos():
        if clase is wm.LocalWorkspaceMissing:
            continue
        assert not issubclass(clase, FileNotFoundError), clase.__name__


# --------------------------------------------------------------------------
# El mensaje dice, en palabras, QUE paso
# --------------------------------------------------------------------------
#
# `[LOCAL_WORKSPACE_MISSING]` a secas es un codigo, no un mensaje. Lo destaparon
# dos tests que esperaban la frase «no existe» y recibian solo el corchete — y
# tenian razon: quien lee un error en una CLI no deberia tener que traducir un
# identificador en mayusculas.
#
# La frase es FIJA por clase, nunca interpolada: el §16 prohibe rutas y PII, y una
# descripcion fija no puede filtrar nada por construccion.


def test_el_mensaje_lleva_una_frase_humana_ademas_del_codigo():
    texto = str(wm.LocalWorkspaceMissing(w_code="W-TEST01"))
    assert "LOCAL_WORKSPACE_MISSING" in texto
    assert "no existe" in texto.lower()


def test_la_descripcion_es_fija_y_no_interpola_nada():
    """Dos instancias con datos distintos comparten la misma frase."""
    a = str(wm.LocalWorkspaceMissing(w_code="W-AAAA1", detalle="/ruta/uno"))
    b = str(wm.LocalWorkspaceMissing(w_code="W-BBBB2", detalle="/ruta/dos"))
    frase = "no existe"
    assert frase in a.lower() and frase in b.lower()
    assert "/ruta/" not in a and "/ruta/" not in b


@pytest.mark.parametrize("clase", sorted(wm.errores_conocidos(), key=lambda c: c.codigo))
def test_toda_descripcion_declarada_respeta_los_canarios(clase):
    """Si una clase declara frase, la frase tampoco puede llevar ruta ni PII."""
    texto = str(clase(w_code="W-TEST01"))
    assert not _RE_UNIDAD_WINDOWS.search(texto), texto
    assert chr(92) not in texto, texto


# --------------------------------------------------------------------------
# El trabajo offline: restar una capacidad, nunca inyectarlas
# --------------------------------------------------------------------------
#
# El §7.1.5 y el §7.2.9 permiten trabajar en local cuando Drive no esta
# accesible, pero con `mutate_canonical = false`: se puede seguir, no publicar.
#
# `capabilities` NO se acepta en el constructor, y con razon —un llamador podria
# fabricarse un `blocked_*` con `MUTATE_CANONICAL` y el contrato entero dejaria de
# valer—. Pero eso prohibe INYECTAR, no RESTAR: un llamador que se quita una
# capacidad solo puede hacerse menos poderoso, nunca mas. La asimetria es la que
# permite expresar el offline sin abrir el agujero.


def test_offline_retira_las_capacidades_que_TOCAN_el_canon():
    """La version anterior de este test era VACUA y lo cazo la mutacion.

    Comprobaba que un `local_checkout` offline no tuviera `MUTATE_CANONICAL` — y
    ese modo **nunca la tuvo**: solo la tiene `drive_active`. Restarla no hacia
    nada, y el test pasaba con el mecanismo desactivado.

    Lo que un checkout local puede hacer contra el canon es CERRAR EL CICLO
    (`CHECKIN`); un scratch, PROMOVER. Sin Drive no se puede revalidar el nonce ni
    publicar, asi que son esas las que se retiran. Tal como estaba, un checkout
    offline seguia anunciando `CHECKIN`.
    """
    ws = _ws("local_checkout", mutate_canonical=False)
    assert not ws.permite(wm.Capability.CHECKIN)
    assert ws.permite(wm.Capability.WRITE_CASE)
    assert ws.permite(wm.Capability.INGEST)
    assert ws.permite(wm.Capability.READ_CASE)


def test_offline_retira_promote_en_un_scratch():
    ws = _ws("local_scratch", mutate_canonical=False)
    assert not ws.permite(wm.Capability.PROMOTE)
    assert ws.permite(wm.Capability.WRITE_CASE)


def test_offline_retira_las_tres_y_solo_esas():
    """El conjunto retirado es exactamente `CAPACIDADES_DE_CANON`."""
    for modo in wm.WorkspaceMode:
        base = wm.CAPACIDADES_POR_MODO[modo]
        off = _ws(modo.value, mutate_canonical=False).capabilities
        assert base - off <= wm.CAPACIDADES_DE_CANON, modo
        assert not (off & wm.CAPACIDADES_DE_CANON), modo


def test_por_defecto_no_resta_nada():
    completo = _ws("local_checkout")
    assert completo.capabilities == wm.CAPACIDADES_POR_MODO[
        wm.WorkspaceMode.LOCAL_CHECKOUT]


def test_restar_NUNCA_puede_conceder_de_mas():
    """La asimetria, fijada: el resultado siempre es subconjunto de la tabla."""
    for modo in wm.WorkspaceMode:
        base = wm.CAPACIDADES_POR_MODO[modo]
        for restar in (True, False):
            ws = _ws(modo.value, mutate_canonical=not restar)
            assert ws.capabilities <= base, (modo, restar)


def test_un_modo_bloqueado_sigue_sin_conceder_nada_aunque_no_se_reste():
    ws = _ws("blocked_conflict", mutate_canonical=True)
    assert not ws.permite(wm.Capability.MUTATE_CANONICAL)
    assert not ws.permite(wm.Capability.WRITE_CASE)


def test_los_errores_del_mutex_estan_en_la_tabla():
    from core.casos.workspace_model import (CaseBusy, MutexIlegible, MutexNotMine,
                                            errores_conocidos)
    codigos = {c.codigo for c in errores_conocidos()}
    assert {"CASE_BUSY", "MUTEX_NOT_MINE", "MUTEX_ILEGIBLE"} <= codigos
    for clase in (CaseBusy, MutexNotMine, MutexIlegible):
        assert clase in errores_conocidos()


def test_el_mensaje_del_mutex_no_lleva_rutas_ni_PII():
    from core.casos.workspace_model import CaseBusy
    exc = CaseBusy(w_code="W-TEST01", maquina="ESTA",
                   detalle=r"C:\Users\alguien\CASOS\BaRS1 - Calle Falsa 1 - (W-TEST01)")
    texto = str(exc)
    assert "W-TEST01" in texto
    assert "Calle Falsa" not in texto
    assert "C:" not in texto
