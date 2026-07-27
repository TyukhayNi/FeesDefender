"""Tests del sistema de checkout/checkin (Merge Desktop→Drive + Biblioteca).

Módulos bajo test:
- ``core.config``: máquina de 3 estados + exclusiones + derivados (SSOT de definición).
- ``core.repository_checkout``: cerebro PURO — transiciones, plan de merge de
  3 vías (tabla canónica de 9 casos, §4.1 del DISEÑO_V2), guard de escritura
  (§6), constructores de eventos. CERO I/O contra Drive.
- ``core.case_manager``: helpers de lock sobre ``_caso.md`` (write-then-verify,
  liberación, conflicto) + round-trip de serialización.

Datos SIEMPRE sintéticos (el repo es público): case ids de desarrollo
(``EV-2026-001``), rutas relativas genéricas, hashes ficticios.
"""

from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rc():
    from core import repository_checkout as _rc
    importlib.reload(_rc)
    return _rc


@pytest.fixture
def cfg(tmp_casos_root):
    from core import config as _cfg
    return _cfg


@pytest.fixture
def cm(tmp_casos_root):
    from core import case_manager as _cm
    importlib.reload(_cm)
    return _cm


@pytest.fixture
def il(tmp_casos_root):
    from core import intake_log as _il
    importlib.reload(_il)
    return _il


# Helpers sintéticos ---------------------------------------------------------

def _e(hash_: str | None, size: int = 100) -> dict:
    """Entrada de inventario sintética."""
    return {"hash": hash_, "size": size}


# ===========================================================================
# 1. Máquina de estados (config SSOT) y validar_transicion
# ===========================================================================

def test_estados_y_transiciones_son_ssot_en_config(cfg):
    assert cfg.ESTADO_REPO_DISPONIBLE == "disponible"
    assert cfg.ESTADO_REPO_PRESTADO == "prestado"
    assert cfg.ESTADO_REPO_CONFLICTO == "conflicto"
    assert cfg.TRANSICIONES_PERMITIDAS == {
        "disponible": ("prestado",),
        "prestado": ("disponible", "conflicto"),
        "conflicto": ("prestado", "disponible"),
    }


@pytest.mark.parametrize("origen,destino", [
    ("disponible", "prestado"),
    ("prestado", "disponible"),
    ("prestado", "conflicto"),
    ("conflicto", "prestado"),
    ("conflicto", "disponible"),
])
def test_transiciones_validas_no_lanzan(rc, origen, destino):
    rc.validar_transicion(origen, destino)  # no raise


@pytest.mark.parametrize("origen,destino", [
    ("disponible", "conflicto"),   # no se puede entrar en conflicto sin pasar por prestado
    ("disponible", "disponible"),  # no-op ilegal
    ("prestado", "prestado"),      # doble checkout: ilegal
    ("conflicto", "conflicto"),
])
def test_transiciones_invalidas_lanzan(rc, origen, destino):
    with pytest.raises(rc.TransicionInvalida):
        rc.validar_transicion(origen, destino)


def test_transicion_desde_estado_desconocido_lanza(rc):
    with pytest.raises(rc.TransicionInvalida):
        rc.validar_transicion("sincronizado", "prestado")  # estado muerto del v1


# ===========================================================================
# 2. Exclusiones del merge (§5) — gestionadas por protocolo, nunca por el sync
# ===========================================================================

@pytest.mark.parametrize("relpath", [
    "00_Input/_caso.md",
    "00_Input/_intake_log.jsonl",
    "MANIFEST_CHECKOUT.json",
    "AUDITLOG_MERGE_2026-07-07T0945Z.jsonl",
    "_snapshot/2026-07-07T0945Z/algo.pdf",
    "_pendiente_checkin/intake/doc.pdf",
    "90_Notas personales/nota.md",
    "90_Notas personales/sub/otra.md",
])
def test_esta_excluido_true(rc, relpath):
    assert rc.esta_excluido(relpath) is True


@pytest.mark.parametrize("relpath", [
    "00_Input/04_Manual/doc.pdf",
    "01_Procesado/Sala lectura/INDICE.md",
    "identidades.yaml",
    "00_Input/05_CRM/01_Demanda/demanda.pdf",
])
def test_esta_excluido_false(rc, relpath):
    assert rc.esta_excluido(relpath) is False


def test_esta_excluido_normaliza_backslashes(rc):
    assert rc.esta_excluido("90_Notas personales\\nota.md") is True


def test_plan_merge_ignora_ficheros_excluidos(rc):
    # Aunque difieran L/D/B, un fichero excluido no genera acción de merge.
    local = {"00_Input/_caso.md": _e("aaa")}
    drive = {"00_Input/_caso.md": _e("bbb")}
    base = {"00_Input/_caso.md": _e("ccc")}
    plan = rc.plan_merge(local, drive, base)
    assert plan == []


# ===========================================================================
# 3. Tabla canónica de merge de 3 vías (§4.1) — los 9 casos
# ===========================================================================

def _accion_de(plan, ruta):
    for a in plan:
        if a.ruta == ruta:
            return a
    return None


def test_caso1_igual_igual_skip(rc):
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({p: _e("h1")}, {p: _e("h1")}, {p: _e("h1")})
    # SKIP no necesita aparecer en el plan de acciones; si aparece, es SKIP.
    a = _accion_de(plan, p)
    assert a is None or a.accion == rc.ACCION_SKIP


def test_caso2_cambiado_igual_copy_local(rc):
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({p: _e("h_local")}, {p: _e("h_base")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_COPY_LOCAL
    assert a.caso_tabla == 2


def test_caso3_igual_cambiado_preserve_drive(rc):
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({p: _e("h_base")}, {p: _e("h_drive")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_PRESERVE_DRIVE
    assert a.caso_tabla == 3


def test_caso4_ambos_cambiados_conflict(rc):
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({p: _e("h_local")}, {p: _e("h_drive")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_CONFLICT
    assert a.caso_tabla == 4


def test_caso4_ambos_cambiados_pero_identicos_skip(rc):
    # Refinamiento anti-fatiga: si ambos lados convergieron al MISMO contenido,
    # no hay divergencia real → SKIP (no CONFLICT). Documentado en el módulo.
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({p: _e("h_igual")}, {p: _e("h_igual")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a is None or a.accion == rc.ACCION_SKIP


def test_caso5_borrado_local_drive_igual_delete_drive(rc):
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({}, {p: _e("h_base")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_DELETE_DRIVE
    assert a.caso_tabla == 5


def test_caso6_borrado_local_drive_cambiado_conflict(rc):
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({}, {p: _e("h_drive")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_CONFLICT
    assert a.caso_tabla == 6


def test_caso7_nuevo_en_local_copy_local(rc):
    p = "00_Input/04_Manual/nuevo.pdf"
    plan = rc.plan_merge({p: _e("h_new")}, {}, {})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_COPY_LOCAL
    assert a.caso_tabla == 7


def test_caso8_nuevo_en_drive_preserve_drive(rc):
    p = "00_Input/04_Manual/nuevo_drive.pdf"
    plan = rc.plan_merge({}, {p: _e("h_new")}, {})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_PRESERVE_DRIVE
    assert a.caso_tabla == 8


def test_caso9_renombrado_detectado_por_hash(rc):
    # Fichero movido en local: aparece como nuevo local + huérfano en Drive con
    # el MISMO hash → RENAME (mover en Drive, no duplicar).
    viejo = "00_Input/04_Manual/2026-01-01_doc.pdf"
    nuevo = "00_Input/04_Manual/2026-02-02_doc.pdf"
    local = {nuevo: _e("h_mismo")}
    drive = {viejo: _e("h_mismo")}
    base = {viejo: _e("h_mismo")}
    plan = rc.plan_merge(local, drive, base)
    a = _accion_de(plan, nuevo)
    assert a.accion == rc.ACCION_RENAME
    assert a.ruta_origen == viejo
    # El path viejo NO debe generar además un DELETE_DRIVE/PRESERVE_DRIVE suelto.
    viejo_acc = _accion_de(plan, viejo)
    assert viejo_acc is None or viejo_acc.accion == rc.ACCION_RENAME


def test_borrado_en_ambos_lados_no_genera_accion(rc):
    p = "00_Input/04_Manual/a.pdf"
    plan = rc.plan_merge({}, {}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a is None or a.accion == rc.ACCION_SKIP


# ===========================================================================
# 4. Derivados regenerables (§4.2) — local gana salvo que Drive cambiara
# ===========================================================================

def test_derivado_local_gana_si_drive_intacto(rc):
    p = "01_Procesado/Sala lectura/INDICE.md"
    plan = rc.plan_merge({p: _e("h_local")}, {p: _e("h_base")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_COPY_LOCAL


def test_derivado_conflict_si_drive_cambio_durante_prestamo(rc):
    p = "01_Procesado/Sala lectura/CRONOLOGIA.md"
    plan = rc.plan_merge({p: _e("h_local")}, {p: _e("h_drive")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_CONFLICT


def test_identidades_yaml_no_es_derivado_va_por_tabla_general(rc):
    # identidades.yaml es MAESTRO: cambiado/cambiado → CONFLICT, no overwrite.
    p = "identidades.yaml"
    plan = rc.plan_merge({p: _e("h_local")}, {p: _e("h_drive")}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_CONFLICT


# ===========================================================================
# 5. Google-native (§4.2) — sin MD5 → siempre PRESERVE_DRIVE
# ===========================================================================

def test_google_native_sin_hash_preserve_drive(rc):
    p = "00_Input/04_Manual/documento_google"
    plan = rc.plan_merge({}, {p: _e(None)}, {})
    a = _accion_de(plan, p)
    assert a.accion == rc.ACCION_PRESERVE_DRIVE
    assert a.google_native is True


# ===========================================================================
# 6. Idempotencia / convergencia (§4.4)
# ===========================================================================

def test_reejecucion_converge_a_skip(rc):
    # Tras aplicar un COPY_LOCAL, re-ejecutar con el MISMO baseline converge a
    # SKIP (Drive == local ahora; ambos "cambiados" respecto a base pero iguales).
    p = "00_Input/04_Manual/a.pdf"
    local = {p: _e("h_local")}
    drive = {p: _e("h_base")}
    base = {p: _e("h_base")}
    plan1 = rc.plan_merge(local, drive, base)
    assert _accion_de(plan1, p).accion == rc.ACCION_COPY_LOCAL
    # Simular ejecución: Drive pasa a tener el contenido local.
    drive2 = {p: _e("h_local")}
    plan2 = rc.plan_merge(local, drive2, base)
    a2 = _accion_de(plan2, p)
    assert a2 is None or a2.accion == rc.ACCION_SKIP


# ===========================================================================
# 7. Guard de escritura (§6) — bandeja _pendiente_checkin
# ===========================================================================

def test_guard_permite_si_disponible(rc, cfg):
    d = rc.decidir_escritura(cfg.ESTADO_REPO_DISPONIBLE, "00_Input/04_Manual/x.pdf", "intake")
    assert d.permitido is True
    assert d.desviar is False


def test_guard_desvia_si_prestado(rc, cfg):
    d = rc.decidir_escritura(cfg.ESTADO_REPO_PRESTADO, "00_Input/04_Manual/x.pdf", "intake")
    assert d.permitido is False
    assert d.desviar is True
    assert d.ruta_bandeja == "_pendiente_checkin/intake/00_Input/04_Manual/x.pdf"
    assert d.evento == "pendiente_checkin"


def test_guard_desvia_si_conflicto(rc, cfg):
    d = rc.decidir_escritura(cfg.ESTADO_REPO_CONFLICTO, "00_Input/03_Email/x.eml", "email")
    assert d.desviar is True
    assert d.ruta_bandeja.startswith("_pendiente_checkin/email/")


def test_guard_protocolo_siempre_escribe(rc, cfg):
    # El propio protocolo (lock, log, bandeja) está exento del guard.
    d = rc.decidir_escritura(cfg.ESTADO_REPO_PRESTADO, "00_Input/_caso.md", "protocolo",
                             es_protocolo=True)
    assert d.permitido is True
    assert d.desviar is False


# ===========================================================================
# 8. Constructores de eventos (para _intake_log.jsonl)
# ===========================================================================

def test_evento_checkout_details_tiene_campos_clave(rc):
    det = rc.evento_checkout_details(
        user="Nikolai Tyukhay",
        timestamp="2026-07-07T09:45:12Z",
        nonce="abc123",
        maquina="TNM-PC",
        ruta_local="C:/Users/x/Desktop/caso",
        n_ficheros=3676,
        manifest_hash="deadbeef",
    )
    assert det["user"] == "Nikolai Tyukhay"
    assert det["checkout_nonce"] == "abc123"
    assert det["n_ficheros"] == 3676
    assert det["manifest_hash"] == "deadbeef"
    # La ruta local completa vive en el log, no en _caso.md (§2.2).
    assert det["ruta_local"] == "C:/Users/x/Desktop/caso"


def test_evento_checkin_details_resume_el_plan(rc):
    det = rc.evento_checkin_details(
        user="Nikolai Tyukhay",
        timestamp="2026-07-07T10:30:00Z",
        copiados=449,
        preservados=10,
        borrados=8,
        conflictos=0,
        renombrados=6,
        resultado="verde",
        auditlog="AUDITLOG_MERGE_2026-07-07T1030Z.jsonl",
    )
    assert det["copiados"] == 449
    assert det["conflictos"] == 0
    assert det["resultado"] == "verde"
    assert det["auditlog"].startswith("AUDITLOG_MERGE_")


# ===========================================================================
# 8b. Mutadores puros del lock (fm→fm) — fuente única compartida CLI/case_manager
# ===========================================================================

def test_estado_de_fm_default_disponible(rc):
    assert rc.estado_de_fm({}) == "disponible"
    assert rc.estado_de_fm({"meta": {}}) == "disponible"
    assert rc.estado_de_fm({"meta": {"estado_repositorio": "prestado"}}) == "prestado"


def test_aplicar_lock_prestado_setea_campos_y_no_ruta(rc):
    fm = {"meta": {"case_id": "X"}}
    fm2 = rc.aplicar_lock_prestado(fm, user="U", timestamp="2026-07-07T09:00:00Z",
                                   nonce="N", maquina="M", notas="n")
    m = fm2["meta"]
    assert m["estado_repositorio"] == "prestado"
    assert m["checkout_user"] == "U"
    assert m["checkout_timestamp"] == "2026-07-07T09:00:00Z"
    assert m["checkout_nonce"] == "N"
    assert m["checkout_maquina"] == "M"
    assert m["checkout_notas"] == "n"
    assert "checkout_local_path" not in m  # §2.2: la ruta local no va a _caso.md


def test_aplicar_lock_crea_meta_si_falta(rc):
    fm2 = rc.aplicar_lock_prestado({}, user="U", timestamp="T", nonce="N",
                                   maquina=None, notas=None)
    assert fm2["meta"]["estado_repositorio"] == "prestado"


def test_aplicar_lock_liberado_limpia_y_marca_checkin(rc):
    fm = {"meta": {"estado_repositorio": "prestado", "checkout_user": "U",
                   "checkout_nonce": "N", "checkout_maquina": "M"}}
    fm2 = rc.aplicar_lock_liberado(fm, timestamp="2026-07-07T10:00:00Z", auditlog="A.jsonl")
    m = fm2["meta"]
    assert m["estado_repositorio"] == "disponible"
    assert m["checkout_user"] is None
    assert m["checkout_nonce"] is None
    assert m["checkout_maquina"] is None
    assert m["ultimo_checkin_timestamp"] == "2026-07-07T10:00:00Z"
    assert m["ultimo_checkin_auditlog"] == "A.jsonl"


def test_aplicar_estado_conflicto(rc):
    fm = {"meta": {"estado_repositorio": "prestado"}}
    fm2 = rc.aplicar_estado(fm, "conflicto")
    assert fm2["meta"]["estado_repositorio"] == "conflicto"


# ===========================================================================
# 9. Lock sobre _caso.md (case_manager) — write-then-verify, round-trip
# ===========================================================================

def _crear_caso(cm, case_id="EV-2026-001"):
    cm.ensure_case(case_id, titulo="Caso sintético de prueba")
    return case_id


def test_estado_por_defecto_es_disponible(cm):
    case_id = _crear_caso(cm)
    assert cm.leer_estado_repositorio(case_id) == "disponible"


def test_escribir_lock_transiciona_a_prestado(cm):
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay", timestamp="2026-07-07T09:45:12Z",
                     nonce="nonceA", maquina="TNM-PC")
    assert cm.leer_estado_repositorio(case_id) == "prestado"
    lock = cm.leer_lock(case_id)
    assert lock["checkout_user"] == "Nikolai Tyukhay"
    assert lock["checkout_nonce"] == "nonceA"
    assert lock["checkout_maquina"] == "TNM-PC"


def test_doble_checkout_rechazado(cm):
    # Segundo checkout sobre un caso ya prestado → TransicionInvalida
    # (prestado → prestado no está permitido).
    from core import repository_checkout as rc
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay", timestamp="2026-07-07T09:45:12Z",
                     nonce="nonceA")
    with pytest.raises(rc.TransicionInvalida):
        cm.escribir_lock(case_id, user="Karen Paola Barreto",
                         timestamp="2026-07-07T09:46:00Z", nonce="nonceB")
    # El lock sigue siendo del primero.
    assert cm.leer_lock(case_id)["checkout_nonce"] == "nonceA"


def test_write_then_verify_nonce_detecta_perdedor(rc):
    # Tras releer el lock del Drive, el nonce ganador debe ser el propio.
    fm_drive = {"meta": {"estado_repositorio": "prestado", "checkout_nonce": "ganador"}}
    assert rc.verificar_nonce(fm_drive, "ganador") is True
    assert rc.verificar_nonce(fm_drive, "perdedor") is False


def test_liberar_lock_vuelve_a_disponible(cm):
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay", timestamp="2026-07-07T09:45:12Z",
                     nonce="nonceA")
    cm.liberar_lock(case_id, timestamp="2026-07-07T10:30:00Z",
                    auditlog="AUDITLOG_MERGE_2026-07-07T1030Z.jsonl")
    assert cm.leer_estado_repositorio(case_id) == "disponible"
    lock = cm.leer_lock(case_id)
    assert lock["checkout_user"] is None
    assert lock["checkout_nonce"] is None
    assert lock["ultimo_checkin_timestamp"] == "2026-07-07T10:30:00Z"
    assert lock["ultimo_checkin_auditlog"] == "AUDITLOG_MERGE_2026-07-07T1030Z.jsonl"


def test_marcar_conflicto_desde_prestado(cm):
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay", timestamp="2026-07-07T09:45:12Z",
                     nonce="nonceA")
    cm.marcar_conflicto(case_id)
    assert cm.leer_estado_repositorio(case_id) == "conflicto"


def test_round_trip_serializacion_caso_md(cm):
    # El lock persiste en _caso.md y se relee idéntico tras reconstruir CaseMeta.
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Ana Solange Velastegui",
                     timestamp="2026-07-07T11:00:00Z", nonce="xyz",
                     maquina="ANA-PC", notas="revisión escritos")
    lock = cm.leer_lock(case_id)
    assert lock["estado_repositorio"] == "prestado"
    assert lock["checkout_user"] == "Ana Solange Velastegui"
    assert lock["checkout_timestamp"] == "2026-07-07T11:00:00Z"
    assert lock["checkout_maquina"] == "ANA-PC"
    assert lock["checkout_notas"] == "revisión escritos"


def test_lock_no_expone_ruta_local_en_caso_md(cm):
    # §2.2 D5 / gobernanza §3: la ruta local NO va a _caso.md (visible para E&V).
    from core.config import caso_path
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay", timestamp="2026-07-07T09:45:12Z",
                     nonce="nonceA", maquina="TNM-PC")
    texto = (caso_path(case_id) / "00_Input" / "_caso.md").read_text(encoding="utf-8")
    assert "checkout_local_path" not in texto


def test_lock_retrocompatible_caso_sin_campos(cm):
    # Un _caso.md preexistente (sin los campos nuevos) se lee como "disponible".
    from core.config import caso_path
    case_id = _crear_caso(cm)
    # ensure_case no escribe estado_repositorio; debe defaultear a disponible.
    idx = caso_path(case_id) / "00_Input" / "_caso.md"
    assert "estado_repositorio" not in idx.read_text(encoding="utf-8") or \
        cm.leer_estado_repositorio(case_id) == "disponible"
    assert cm.leer_estado_repositorio(case_id) == "disponible"


# ===========================================================================
# 10. Bandeja _pendiente_checkin — evento en el log
# ===========================================================================

def test_evento_pendiente_checkin_registrable(cm, il):
    case_id = _crear_caso(cm)
    from core import repository_checkout as rc
    d = rc.decidir_escritura("prestado", "00_Input/04_Manual/x.pdf", "intake")
    il.append_event(case_id, d.evento, details={
        "origen": "intake",
        "ruta_bandeja": d.ruta_bandeja,
        "ruta_original": "00_Input/04_Manual/x.pdf",
    })
    eventos = il.read_events(case_id)
    assert any(e["event"] == "pendiente_checkin" for e in eventos)


def test_guard_escritura_disponible_permite_sin_evento(cm, il):
    case_id = _crear_caso(cm)
    d = cm.guard_escritura(case_id, "00_Input/04_Manual/x.pdf", "intake")
    assert d.permitido is True
    assert il.read_events(case_id) == []  # no emite evento cuando permite


def test_guard_escritura_prestado_desvia_y_registra_evento(cm, il):
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay",
                     timestamp="2026-07-07T09:45:12Z", nonce="n")
    d = cm.guard_escritura(case_id, "00_Input/04_Manual/x.pdf", "intake")
    assert d.desviar is True
    assert d.ruta_bandeja == "_pendiente_checkin/intake/00_Input/04_Manual/x.pdf"
    eventos = il.read_events(case_id)
    pend = [e for e in eventos if e["event"] == "pendiente_checkin"]
    assert len(pend) == 1
    assert pend[0]["details"]["ruta_original"] == "00_Input/04_Manual/x.pdf"


def test_dir_intake_disponible_devuelve_ruta_normal(cm):
    from core.config import caso_path
    case_id = _crear_caso(cm)
    d = cm.dir_intake(case_id, "00_Input/02_Whatsapp/03_Otros/chat", "whatsapp")
    assert d == caso_path(case_id) / "00_Input/02_Whatsapp/03_Otros/chat"


def test_dir_intake_prestado_devuelve_bandeja_y_registra(cm, il):
    from core.config import caso_path
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay",
                     timestamp="2026-07-07T09:45:12Z", nonce="n")
    d = cm.dir_intake(case_id, "00_Input/02_Whatsapp/03_Otros/chat", "whatsapp")
    assert d == caso_path(case_id) / "_pendiente_checkin/whatsapp/00_Input/02_Whatsapp/03_Otros/chat"
    assert any(e["event"] == "pendiente_checkin" for e in il.read_events(case_id))


def test_guard_escritura_protocolo_exento(cm, il):
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay",
                     timestamp="2026-07-07T09:45:12Z", nonce="n")
    d = cm.guard_escritura(case_id, "00_Input/_caso.md", "protocolo", es_protocolo=True)
    assert d.permitido is True
    assert not any(e["event"] == "pendiente_checkin" for e in il.read_events(case_id))


# ===========================================================================
# 11. Guard cableado en el intake manual (punto de escritura real, §6)
# ===========================================================================

def _reload_intake_manual(tmp_casos_root):
    from core import intake_manual as _im
    importlib.reload(_im)
    return _im


def test_save_file_escribe_normal_si_disponible(cm, tmp_casos_root):
    im = _reload_intake_manual(tmp_casos_root)
    case_id = _crear_caso(cm)
    dest = im.save_file(case_id, "x.pdf", b"data")
    from core.intake_lotes import PATRON_LOTE
    assert PATRON_LOTE.match(dest.parent.name).group(2) == "manual"
    assert "_pendiente_checkin" not in dest.as_posix()
    assert dest.read_bytes() == b"data"


def test_save_file_desvia_a_bandeja_si_prestado(cm, il, tmp_casos_root):
    from core.config import caso_path
    im = _reload_intake_manual(tmp_casos_root)
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay",
                     timestamp="2026-07-07T09:45:12Z", nonce="n")
    dest = im.save_file(case_id, "x.pdf", b"data")
    # Se escribió en la bandeja, no en 04_Manual.
    assert "_pendiente_checkin/manual/" in dest.as_posix()
    assert dest.read_bytes() == b"data"
    assert not (caso_path(case_id) / "00_Input" / "04_Manual" / "x.pdf").exists()
    # Y quedó traza en el log.
    assert any(e["event"] == "pendiente_checkin" for e in il.read_events(case_id))


def test_save_file_crm_branch_desvia_si_prestado(cm, tmp_casos_root):
    from core.config import caso_path
    im = _reload_intake_manual(tmp_casos_root)
    case_id = _crear_caso(cm)
    cm.escribir_lock(case_id, user="Nikolai Tyukhay",
                     timestamp="2026-07-07T09:45:12Z", nonce="n")
    dest = im.save_file_crm_branch(case_id, "General", "d.pdf", b"x")
    assert "_pendiente_checkin/crm_manual/" in dest.as_posix()
    assert not (caso_path(case_id) / "00_Input" / "05_CRM" / "General" / "d.pdf").exists()


# ===========================================================================
# 8. Grupos de merge indivisibles + derivado borrado en Drive (N6)
# ===========================================================================
#
# Hallazgo N6 de la revisión adversarial (2026-07-27). Tres defectos distintos:
#   a) un COPY_LOCAL se sube aunque un hermano de su grupo esté en CONFLICT;
#   b) un derivado ausente en Drive pero presente en el baseline se resucita
#      (Drive lo borró durante el préstamo → debe ser CONFLICT, caso 6);
#   c) el peor: si el mapa solo cambió en Drive → PRESERVE_DRIVE, no hay
#      conflicto, el semáforo sale verde y el ledger local se sube igualmente
#      → Drive con mapa nuevo y ledger viejo, en silencio.

_MAPA = "05_Procedimiento/_mapa_procesal.yaml"
_LEDGER = "05_Procedimiento/_MANIFIESTO_PROCESAL.json"
_OCURR = "00_Input/_ocurrencias_crm.json"


def test_derivado_borrado_en_drive_durante_prestamo_es_conflict(rc):
    """N6b: Drive borró un derivado que sigue en local → decisión manual.

    Coherencia con el caso 6 de la tabla general: hoy la rama de derivados
    devuelve COPY_LOCAL sin mirar el baseline y lo resucita.
    """
    p = "01_Procesado/Sala lectura/INDICE.md"
    plan = rc.plan_merge({p: _e("h_local")}, {}, {p: _e("h_base")})
    a = _accion_de(plan, p)
    assert a is not None and a.accion == rc.ACCION_CONFLICT


def test_derivado_nuevo_en_local_sigue_siendo_copy_local(rc):
    """No regresión: sin baseline es un alta genuina, no una resurrección."""
    p = "01_Procesado/Sala lectura/INDICE.md"
    plan = rc.plan_merge({p: _e("h_local")}, {}, {})
    a = _accion_de(plan, p)
    assert a is not None and a.accion == rc.ACCION_COPY_LOCAL


def test_grupo_vetado_si_un_miembro_esta_en_conflicto(rc):
    """N6a: el mapa en conflicto veta la subida del ledger y de las ocurrencias."""
    plan = rc.plan_merge(
        local={_MAPA: _e("h_local"), _LEDGER: _e("l_local"), _OCURR: _e("o_local")},
        drive={_MAPA: _e("h_drive"), _LEDGER: _e("l_base"), _OCURR: _e("o_base")},
        base={_MAPA: _e("h_base"), _LEDGER: _e("l_base"), _OCURR: _e("o_base")},
    )
    assert _accion_de(plan, _MAPA).accion == rc.ACCION_CONFLICT
    for p in (_LEDGER, _OCURR):
        a = _accion_de(plan, p)
        assert a is not None and a.accion == rc.ACCION_VETO_GRUPO, p
        assert _MAPA in a.motivo


def test_grupo_vetado_si_el_mapa_solo_cambio_en_drive(rc):
    """N6c, el caso silencioso: PRESERVE_DRIVE en el mapa también veta.

    No hay conflicto, así que sin el veto el semáforo saldría verde y el Drive
    se quedaría con mapa nuevo y ledger viejo.
    """
    plan = rc.plan_merge(
        local={_MAPA: _e("h_base"), _LEDGER: _e("l_local")},
        drive={_MAPA: _e("h_drive"), _LEDGER: _e("l_base")},
        base={_MAPA: _e("h_base"), _LEDGER: _e("l_base")},
    )
    assert _accion_de(plan, _MAPA).accion == rc.ACCION_PRESERVE_DRIVE
    a = _accion_de(plan, _LEDGER)
    assert a is not None and a.accion == rc.ACCION_VETO_GRUPO


def test_grupo_no_vetado_si_todos_sus_miembros_suben_o_no_cambian(rc):
    """El caso normal: el trío viaja junto sin trabas."""
    plan = rc.plan_merge(
        local={_MAPA: _e("h_local"), _LEDGER: _e("l_local"), _OCURR: _e("o_base")},
        drive={_MAPA: _e("h_base"), _LEDGER: _e("l_base"), _OCURR: _e("o_base")},
        base={_MAPA: _e("h_base"), _LEDGER: _e("l_base"), _OCURR: _e("o_base")},
    )
    assert _accion_de(plan, _MAPA).accion == rc.ACCION_COPY_LOCAL
    assert _accion_de(plan, _LEDGER).accion == rc.ACCION_COPY_LOCAL
    # Las ocurrencias no cambiaron: SKIP implícito, y no vetan a nadie.
    assert _accion_de(plan, _OCURR) is None


def test_veto_no_alcanza_a_ficheros_fuera_del_grupo(rc):
    """Opción A: el escrito del letrado sube aunque el mapa esté en conflicto."""
    demanda = "05_Procedimiento/DEMANDA_W-02MA0R.docx"
    plan = rc.plan_merge(
        local={_MAPA: _e("h_local"), demanda: _e("d_local")},
        drive={_MAPA: _e("h_drive")},
        base={_MAPA: _e("h_base")},
    )
    assert _accion_de(plan, _MAPA).accion == rc.ACCION_CONFLICT
    assert _accion_de(plan, demanda).accion == rc.ACCION_COPY_LOCAL


def test_resumen_plan_cuenta_los_vetados(rc):
    plan = rc.plan_merge(
        local={_MAPA: _e("h_base"), _LEDGER: _e("l_local")},
        drive={_MAPA: _e("h_drive"), _LEDGER: _e("l_base")},
        base={_MAPA: _e("h_base"), _LEDGER: _e("l_base")},
    )
    assert rc.resumen_plan(plan)[rc.ACCION_VETO_GRUPO] == 1


def test_grupos_merge_son_ssot_en_config(rc, cfg):
    """La definición de los grupos vive en config, no en el cerebro."""
    assert hasattr(cfg, "GRUPOS_MERGE")
    todas = {r for g in cfg.GRUPOS_MERGE for r in g}
    assert {_MAPA, _LEDGER, _OCURR} <= todas
