"""Contrato de la costura de escritura — Plan 3A, Task 2. Fronteras C0-C8.

La costura reúne las dos decisiones que hoy están separadas o ausentes —¿tengo el mutex?
¿el guard desvía?— y **efectúa** el destino en vez de aconsejarlo. Que devuelva una
capacidad y no un `Path` es la remediación de R14/H14-05: una API que autoriza y deja al
llamador componer su propia ruta no cierra el agujero, lo mueve.

**C0 va primero porque es el CRÍTICO de R14.** El mutex se indexaba por el W-code del
nombre de la carpeta cuando la identidad canónica del catálogo es `meta.id_go`, y nadie
comprobaba que concordaran: dos lockfiles para un expediente.
"""
from __future__ import annotations

import io

import pytest

AHORA = "2026-08-26T12:00:00Z"


def reloj() -> str:
    return AHORA


@pytest.fixture
def raiz(tmp_path):
    """Raíz de lockfiles, **hermana** de CASOS_ROOT.

    No puede vivir bajo `CASOS_ROOT` —`list_cases()` la vería y un checkin la subiría al
    Drive— y `raiz_de_locks` lo comprueba, así que ponerla dentro rompería el montaje y
    no el contrato.
    """
    return tmp_path / "locks"


@pytest.fixture(autouse=True)
def _reloj_del_sistema_fijo(monkeypatch):
    from core.casos import case_mutex
    monkeypatch.setattr(case_mutex, "_ahora_del_sistema",
                        lambda: case_mutex._instante(AHORA))


@pytest.fixture(autouse=True)
def _mapa_limpio():
    from core.casos import mutex_sesion
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()
    yield
    with mutex_sesion._CANDADO:
        mutex_sesion._SESIONES.clear()


def monta_caso(root, nombre: str, id_go: str | None, estado: str = "disponible"):
    """Un expediente mínimo con la identidad y el estado que se le pidan.

    `id_go` es lo que el catálogo considera canónico; `nombre` es la presentación. Poder
    darles valores distintos **es** el montaje que C0 necesita.
    """
    d = root / nombre
    (d / "00_Input").mkdir(parents=True)
    lineas = ["---", "meta:"]
    if id_go is not None:
        lineas.append(f"  id_go: {id_go}")
    lineas += [f"  estado_repositorio: {estado}", "---", ""]
    io.open(d / "00_Input" / "_caso.md", "w", encoding="utf-8", newline="\n").write(
        "\n".join(lineas))
    return d


def ref_de(w):
    from core.casos.workspace_model import CaseRef
    return CaseRef(w_code=w)


# --------------------------------------------------------------------------- C0

def test_c0_rechaza_cuando_el_nombre_y_el_id_go_discrepan(tmp_casos_root, raiz):
    """C0 — el CRÍTICO de R14/H14-01.

    El docstring de `CaseRef` dice que el nombre de carpeta «es una presentación y no
    basta como identidad». Si la costura aceptara la discrepancia, un proceso que llega
    por el nombre y otro que llega por el metadato tomarían **dos** lockfiles distintos
    para el mismo expediente, los dos creyéndose protegidos.
    """
    from core.casos import escritura
    from core.casos.workspace_model import IdentidadDiscordante

    monta_caso(tmp_casos_root, "Ba001 - x - (W-NOMBRE) - t", id_go="W-METADAT")

    with pytest.raises(IdentidadDiscordante):
        escritura.deposito(ref_de("W-METADAT"), "00_Input", "intake",
                           clase="contenido", modo="libre", raiz=raiz)


def test_c0_acepta_cuando_concuerdan(tmp_casos_root, raiz):
    """C0-bis — el control negativo. Sin esto, C0 pasaría con una costura que rechaza todo."""
    from core.casos import escritura, mutex_sesion

    monta_caso(tmp_casos_root, "Ba001 - x - (W-IGUAL1) - t", id_go="W-IGUAL1")
    ref = ref_de("W-IGUAL1")

    with mutex_sesion.sostenido(ref, ahora_fn=reloj, raiz=raiz):
        d = escritura.deposito(ref, "00_Input", "intake",
                               clase="contenido", modo="v1", raiz=raiz)
    assert d.protegida_por_mutex is True
    assert d.desviada is False


# --------------------------------------------------------------------------- C1

def test_c1_sin_mutex_en_v1_rechaza(tmp_casos_root, raiz):
    """C1 — en `v1` el mutex no es opcional. Si lo fuera, no protegería nada."""
    from core.casos import escritura
    from core.casos.workspace_model import EscrituraSinMutex

    monta_caso(tmp_casos_root, "Ba001 - x - (W-SINMTX) - t", id_go="W-SINMTX")

    with pytest.raises(EscrituraSinMutex):
        escritura.deposito(ref_de("W-SINMTX"), "00_Input", "intake",
                           clase="contenido", modo="v1", raiz=raiz)


def test_c1_sin_mutex_en_libre_deposita_y_lo_declara(tmp_casos_root, raiz):
    """C1-bis — el trinquete.

    Rechazar en `libre` desde el primer día convertiría cualquier camino sin cablear en
    un fallo duro de las vías de intake de `streamlit_app.py`, que es la herramienta
    diaria del equipo. El hueco se **declara** y se cuenta; no se tapa.
    """
    from core.casos import escritura

    monta_caso(tmp_casos_root, "Ba001 - x - (W-LIBRE1) - t", id_go="W-LIBRE1")

    d = escritura.deposito(ref_de("W-LIBRE1"), "00_Input", "intake",
                           clase="contenido", modo="libre", raiz=raiz)
    assert d.protegida_por_mutex is False
    assert d.motivo_sin_mutex, "una escritura sin proteger tiene que decir POR QUÉ"
    destino = d.escribir_texto("x.txt", "hola")
    assert destino.read_text(encoding="utf-8") == "hola"


# --------------------------------------------------------------------------- C2

@pytest.mark.parametrize("modo", ["v1", "libre"])
def test_c2_mutex_perdido_rechaza_en_los_dos_modos(tmp_casos_root, raiz, modo):
    """C2 — «lo tenía» no es «lo tengo», y perder no degrada a no tener.

    Un mutex perdido a mitad de operación no es un hueco de migración: son dos procesos
    creyéndose titulares. Por eso rechaza también en `libre`, donde C1 no rechaza.
    """
    from core.casos import case_mutex, escritura, mutex_sesion
    from core.casos.workspace_model import MutexPerdido

    monta_caso(tmp_casos_root, "Ba001 - x - (W-PERDI1) - t", id_go="W-PERDI1")
    ref = ref_de("W-PERDI1")

    with pytest.raises(MutexPerdido):
        with mutex_sesion.sostenido(ref, ahora_fn=reloj, raiz=raiz):
            case_mutex.ruta_del_lock("W-PERDI1", raiz=raiz).unlink()
            with pytest.raises(MutexPerdido):
                escritura.deposito(ref, "00_Input", "intake",
                                   clase="contenido", modo=modo, raiz=raiz)


def test_c2_el_error_de_perdida_no_es_el_de_ausencia(tmp_casos_root, raiz):
    """C2-bis — tipos distintos, no mensajes distintos.

    Con un solo error el operador no podría separar «cablea el mutex aquí» de «otro
    proceso te lo quitó», que piden acciones opuestas.
    """
    from core.casos.workspace_model import EscrituraSinMutex, MutexPerdido
    assert EscrituraSinMutex is not MutexPerdido
    assert EscrituraSinMutex.codigo != MutexPerdido.codigo


# --------------------------------------------------------------------------- C3

def test_c3_caso_prestado_desvia_a_la_bandeja(tmp_casos_root, raiz):
    """C3 — el guard sigue mandando sobre el destino, y la costura lo obedece."""
    from core.casos import escritura, mutex_sesion

    monta_caso(tmp_casos_root, "Ba001 - x - (W-PREST1) - t", id_go="W-PREST1",
               estado="prestado")
    ref = ref_de("W-PREST1")

    with mutex_sesion.sostenido(ref, ahora_fn=reloj, raiz=raiz):
        d = escritura.deposito(ref, "00_Input", "intake",
                               clase="contenido", modo="v1", raiz=raiz)
        assert d.desviada is True
        destino = d.escribir_texto("x.txt", "hola")
    assert "_pendiente_checkin" in destino.as_posix()
    assert destino.read_text(encoding="utf-8") == "hola"


# --------------------------------------------------------------------------- C4

def test_c4_protocolo_exento_del_desvio_nunca_del_mutex(tmp_casos_root, raiz):
    """C4 — la exención es del desvío y solo del desvío.

    Es la frase que el §25 convierte en declaración: las doce filas de protocolo estaban
    exentas **por omisión**, y omisión no es exención.
    """
    from core.casos import escritura, mutex_sesion
    from core.casos.workspace_model import EscrituraSinMutex

    monta_caso(tmp_casos_root, "Ba001 - x - (W-PROTO1) - t", id_go="W-PROTO1",
               estado="prestado")
    ref = ref_de("W-PROTO1")

    # Exento del desvío: escribe en la ruta viva aunque el caso esté prestado.
    with mutex_sesion.sostenido(ref, ahora_fn=reloj, raiz=raiz):
        d = escritura.deposito(ref, "00_Input", "protocolo",
                               clase="protocolo", modo="v1", raiz=raiz)
        assert d.desviada is False

    # Pero NO exento del mutex: sin él, en v1, rechaza igual.
    with pytest.raises(EscrituraSinMutex):
        escritura.deposito(ref, "00_Input", "protocolo",
                           clase="protocolo", modo="v1", raiz=raiz)


# --------------------------------------------------------------------------- C5

def test_c5_derivado_no_tiene_exencion_posible(tmp_casos_root, raiz):
    """C5 — las diez filas de clase derivado son bytes del expediente.

    Hoy ninguna consulta el guard, así que un caso prestado recibe sus derivados en la
    ruta canónica. Aquí no hay valor de `clase` que lo exima.
    """
    from core.casos import escritura, mutex_sesion

    monta_caso(tmp_casos_root, "Ba001 - x - (W-DERIV1) - t", id_go="W-DERIV1",
               estado="prestado")
    ref = ref_de("W-DERIV1")

    with mutex_sesion.sostenido(ref, ahora_fn=reloj, raiz=raiz):
        d = escritura.deposito(ref, "01_Procesado/02_Sala de máquina/01_OCR",
                               "pipeline", clase="derivado", modo="v1", raiz=raiz)
        assert d.desviada is True, "un derivado no puede caer en la ruta viva de un prestado"


def test_c5b_una_clase_desconocida_lanza(tmp_casos_root, raiz):
    """C5-bis — lo que no se reconoce no puede degradar a exento."""
    from core.casos import escritura

    monta_caso(tmp_casos_root, "Ba001 - x - (W-CLASE1) - t", id_go="W-CLASE1")
    with pytest.raises(ValueError, match="clase"):
        escritura.deposito(ref_de("W-CLASE1"), "00_Input", "intake",
                           clase="inventada", modo="libre", raiz=raiz)


# --------------------------------------------------------------------------- C6

def test_c6_sin_w_code_en_v1_aborta_y_en_libre_lo_declara(tmp_casos_root, raiz):
    """C6 — segundo de los tres estados de identidad: no hay ninguna."""
    from core.casos import escritura
    from core.casos.workspace_model import CaseRef, IdentidadNoUtilizable

    nombre = "carpeta sin codigo"
    monta_caso(tmp_casos_root, nombre, id_go=None)
    ref = CaseRef(case_id=nombre)
    assert ref.w_code is None

    with pytest.raises(IdentidadNoUtilizable):
        escritura.deposito(ref, "00_Input", "intake",
                           clase="contenido", modo="v1", raiz=raiz)

    d = escritura.deposito(ref, "00_Input", "intake",
                           clase="contenido", modo="libre", raiz=raiz)
    assert d.protegida_por_mutex is False
    assert "identidad" in (d.motivo_sin_mutex or "").lower()


def test_c6b_un_w_code_que_el_mutex_no_admite_es_un_TERCER_estado(tmp_casos_root, raiz):
    """C6-bis — el estado que la rev. 1 del plan no enumeraba.

    Medido: `_w_code_de` extrae `W-AB` (dos caracteres) y códigos de 22, y
    `_w_code_valido` los **rechaza** porque exige 3-20. Sin esta rama, lo que sale es un
    `ValueError` crudo escapando de un validador privado, que no es una salida declarada.
    """
    from core.casos import escritura
    from core.casos.workspace_model import CaseRef, IdentidadNoUtilizable

    nombre = "Ba001 - x - (W-AB) - t"
    monta_caso(tmp_casos_root, nombre, id_go="W-AB")

    d = escritura.deposito(CaseRef(case_id=nombre), "00_Input", "intake",
                           clase="contenido", modo="libre", raiz=raiz)
    assert d.protegida_por_mutex is False
    assert "W-AB" not in (d.motivo_sin_mutex or ""), (
        "el motivo no debe reproducir el valor crudo; el §16 gobierna los mensajes")

    with pytest.raises(IdentidadNoUtilizable):
        escritura.deposito(CaseRef(case_id=nombre), "00_Input", "intake",
                           clase="contenido", modo="v1", raiz=raiz)


# --------------------------------------------------------------------------- C7

def test_c7_el_mutex_se_exige_antes_del_guard(tmp_casos_root, raiz):
    """C7 — el orden, que es la mitad del diseño.

    `guard_escritura` emite un evento `pendiente_checkin` cuando desvía, y ese evento es
    la fila #13 del write-set: protocolo, obligada a ir bajo mutex. Si el mutex se
    exigiera **después**, la escritura del propio guard nacería fuera de él.

    Se mide por el efecto observable: rechazar sin haber dejado el evento.
    """
    from core.casos import escritura
    from core.casos.workspace_model import EscrituraSinMutex

    d = monta_caso(tmp_casos_root, "Ba001 - x - (W-ORDEN1) - t", id_go="W-ORDEN1",
                   estado="prestado")
    log = d / "00_Input" / "_intake_log.jsonl"

    with pytest.raises(EscrituraSinMutex):
        escritura.deposito(ref_de("W-ORDEN1"), "00_Input", "intake",
                           clase="contenido", modo="v1", raiz=raiz)

    assert not log.exists(), (
        "el guard corrió ANTES de exigir el mutex: dejó su evento de desvío fuera de "
        "toda protección, que es exactamente lo que el orden evita")


# --------------------------------------------------------------------------- C8

def test_c8_el_deposito_no_expone_la_raiz_del_caso(tmp_casos_root, raiz):
    """C8 — H14-05: una capacidad que devuelve la raíz no es una capacidad.

    Si el `Deposito` publicara el directorio del caso, el llamador podría recomponer
    cualquier ruta y el censo del Task 7 no lo vería — que es el patrón exacto de la
    fila #8, donde `_intake_drive_ev` vuelve a `case_dir` después de pasar por el guard.
    """
    from pathlib import Path

    from core.casos import escritura

    monta_caso(tmp_casos_root, "Ba001 - x - (W-CAPAC1) - t", id_go="W-CAPAC1")
    d = escritura.deposito(ref_de("W-CAPAC1"), "00_Input", "intake",
                           clase="contenido", modo="libre", raiz=raiz)

    publicos = {n for n in dir(d) if not n.startswith("_")}
    expuestos = {n for n in publicos
                 if isinstance(getattr(d, n, None), Path)}
    assert not expuestos, (
        f"el Deposito publica rutas y no debe: {sorted(expuestos)}. La raíz del caso es "
        f"justo lo que no puede salir de aquí")


@pytest.mark.parametrize("fuga", ["../fuera.txt", "00_Input/../../fuera.txt"])
def test_c8b_una_ruta_que_escapa_del_destino_se_rechaza(tmp_casos_root, raiz, fuga):
    """C8-bis — la contención se comprueba, no se supone.

    Sin esto, `dir_para("..")` devuelve la raíz del caso y C8 pasa siendo mentira: la
    capacidad no expondría la raíz por un atributo, la regalaría por un argumento.
    """
    from core.casos import escritura

    monta_caso(tmp_casos_root, "Ba001 - x - (W-FUGA01) - t", id_go="W-FUGA01")
    d = escritura.deposito(ref_de("W-FUGA01"), "00_Input", "intake",
                           clase="contenido", modo="libre", raiz=raiz)
    with pytest.raises(ValueError, match="escapa"):
        d.escribir_texto(fuga, "no")


def test_c6c_discordancia_y_ausencia_no_comparten_codigo():
    """C6-ter — dos condiciones, dos códigos.

    «Este expediente tiene DOS identidades» es un problema de integridad que hay que
    mirar ya; «esta carpeta no lleva W-code» es una convención de nombre que no se
    cumple. Con un solo código el operador no puede separarlas, que es el mismo
    argumento con el que `CASE_BUSY` se separó de `CASE_LOCKED`.
    """
    from core.casos.workspace_model import IdentidadDiscordante, IdentidadNoUtilizable
    assert IdentidadDiscordante.codigo != IdentidadNoUtilizable.codigo
