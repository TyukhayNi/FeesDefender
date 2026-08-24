"""Task 5 — el registro privado de workspaces.

Contrato: §5 y §15 de
`docs/superpowers/specs/2026-07-29-feesdefender-dual-case-workspace-design.md`,
más las decisiones que la **R7** forzó sobre el plan (§12 del plan):

- **H7-04:** la forma se decide AQUÍ — un fichero por W-code, `<w_code>.json`, con una
  LISTA dentro. Ni un JSON agregado (perdería altas concurrentes de W-codes distintos y
  haría que los lockfiles por W-code de D2 no se excluyeran) ni un fichero por entrada
  (dos entradas del mismo caso deben poder convivir: un checkout y un scratch).
- **H7-03:** la atomicidad se prueba ATRAVESANDO `alta()`, no simulando el temporal a
  mano. Un test que escribe el temporal y no renombra pasa aunque producción escriba
  in-place y jamás llame a `os.replace`.
- **H7-02:** un registro corrupto NO se convierte en «registro vacío». Falla CERRADO.

La raíz se **inyecta** en el constructor, igual que `ahora`. No se lee de `settings`
dentro de la pieza: el default de producción es `%LOCALAPPDATA%\\FeesDefender\\workspaces`,
y la barrera de `tests/_barrera.py` cubre rclone y `subprocess`, NO las escrituras al
perfil del usuario. Con la raíz inyectada, un test que se olvide no puede escribir fuera
de su `tmp_path` porque no tiene default al que caerse.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.casos import workspace_model as wm
from core.casos import workspace_registry as wr

AHORA = "2026-08-24T12:00:00Z"


# --------------------------------------------------------------------------
# Helpers del test
# --------------------------------------------------------------------------

def _registro(tmp_path: Path, *, ahora: str = AHORA) -> wr.WorkspaceRegistry:
    return wr.WorkspaceRegistry(tmp_path / "registro", ahora=ahora)


def _entrada(tmp_path: Path, *, w_code: str = "W-TEST99", tipo: str = "checkout",
             sufijo: str = "") -> wr.WorkspaceEntry:
    local = tmp_path / f"local{sufijo}" / f"BaRS9 - Prueba - ({w_code}) - Vuelta"
    local.mkdir(parents=True, exist_ok=True)
    return wr.WorkspaceEntry(
        case_id=f"BaRS9 - Prueba - ({w_code}) - Vuelta",
        w_code=w_code,
        canonical_ref="id_go_sintetico",
        local_path=local,
        nonce="nonce" + sufijo,
        maquina="ESTA-MAQUINA",
        tipo=tipo,
        ultima_validacion=AHORA,
        schema=wr.SCHEMA_SOPORTADO,
    )


# ------------------------------------------------------------------ la entrada

def test_la_entrada_es_inmutable(tmp_path):
    e = _entrada(tmp_path)
    with pytest.raises(Exception):          # FrozenInstanceError
        e.w_code = "W-OTRO"                 # type: ignore[misc]


# ------------------------------------------------------- dónde NO puede vivir

def test_la_raiz_no_puede_estar_bajo_casos_root(tmp_path, monkeypatch):
    """§16 y el criterio de la Fase 1: el registro es privado y vive FUERA del catálogo.

    Si viviera dentro, un `list_cases()` lo vería y un checkin lo subiría al Drive.
    """
    casos = tmp_path / "CASOS"
    casos.mkdir()
    monkeypatch.setattr(wr, "_casos_root", lambda: casos)
    with pytest.raises(wm.WorkspaceUnderCatalogRoot):
        wr.WorkspaceRegistry(casos / "workspaces", ahora=AHORA)


def test_la_raiz_no_puede_estar_bajo_el_repo(tmp_path, monkeypatch):
    """Ni dentro del repo: `git status` lo vería y acabaría commiteado."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(wr, "_casos_root", lambda: tmp_path / "otro")
    monkeypatch.setattr(wr, "_project_root", lambda: repo)
    with pytest.raises(wm.WorkspaceUnderCatalogRoot):
        wr.WorkspaceRegistry(repo / ".registro", ahora=AHORA)


# ---------------------------------------------------------------- alta y baja

def test_alta_y_buscar_dan_la_vuelta(tmp_path):
    reg = _registro(tmp_path)
    e = _entrada(tmp_path)
    reg.alta(e)
    hallados = reg.buscar(wm.CaseRef(w_code="W-TEST99"))
    assert [h.local_path for h in hallados] == [e.local_path]
    assert hallados[0].tipo == "checkout"


def test_buscar_sin_nada_registrado_devuelve_vacio(tmp_path):
    reg = _registro(tmp_path)
    assert reg.buscar(wm.CaseRef(w_code="W-TEST99")) == []


def test_dos_entradas_del_mismo_w_code_se_devuelven_AMBAS(tmp_path):
    """La desambiguación es del resolver (Task 7), no del registro.

    Un checkout y un scratch del mismo caso pueden coexistir: el registro los
    entrega los dos y el resolver decide o lanza `AmbiguousCase`. Si el registro
    se quedara con uno, el resolver no podría ni detectar la ambigüedad.
    """
    reg = _registro(tmp_path)
    reg.alta(_entrada(tmp_path, tipo="checkout", sufijo="_a"))
    reg.alta(_entrada(tmp_path, tipo="scratch", sufijo="_b"))
    hallados = reg.buscar(wm.CaseRef(w_code="W-TEST99"))
    assert len(hallados) == 2
    assert {h.tipo for h in hallados} == {"checkout", "scratch"}


def test_alta_de_una_ruta_ya_registrada_para_otro_caso_lanza(tmp_path):
    """La misma carpeta local no puede ser dos casos: sería split brain de identidad."""
    reg = _registro(tmp_path)
    primera = _entrada(tmp_path, w_code="W-AAAA1")
    reg.alta(primera)
    segunda = wr.WorkspaceEntry(
        case_id="BaRS9 - Otro - (W-BBBB2) - Vuelta",
        w_code="W-BBBB2",
        canonical_ref="otro_id_go",
        local_path=primera.local_path,          # ← la MISMA ruta
        nonce="nonce2",
        maquina="ESTA-MAQUINA",
        tipo="checkout",
        ultima_validacion=AHORA,
        schema=wr.SCHEMA_SOPORTADO,
    )
    with pytest.raises(wr.RutaYaRegistrada):
        reg.alta(segunda)


def test_baja_retira_la_entrada(tmp_path):
    reg = _registro(tmp_path)
    reg.alta(_entrada(tmp_path))
    reg.baja(wm.CaseRef(w_code="W-TEST99"))
    assert reg.buscar(wm.CaseRef(w_code="W-TEST99")) == []


def test_baja_de_lo_que_no_existe_no_lanza(tmp_path):
    """Idempotente: retirar dos veces no es un error, es el mismo estado final."""
    reg = _registro(tmp_path)
    reg.baja(wm.CaseRef(w_code="W-TEST99"))


# ------------------------------------------------------- un fichero por W-code

def test_el_layout_es_un_fichero_por_w_code(tmp_path):
    """H7-04: la forma es contrato, no detalle. De ella dependen la atomicidad por
    entrada y que los lockfiles por W-code de D2 no colisionen."""
    reg = _registro(tmp_path)
    reg.alta(_entrada(tmp_path, w_code="W-AAAA1"))
    reg.alta(_entrada(tmp_path, w_code="W-BBBB2", sufijo="_b"))
    ficheros = sorted(p.name for p in (tmp_path / "registro").glob("*.json"))
    assert ficheros == ["W-AAAA1.json", "W-BBBB2.json"]


def test_un_lockfile_de_d2_no_se_lee_como_entrada_ni_se_cuarentena(tmp_path):
    """D2 pone su lockfile por W-code en esta misma raíz. No es una entrada."""
    reg = _registro(tmp_path)
    reg.alta(_entrada(tmp_path))
    raiz = tmp_path / "registro"
    lock = raiz / "W-TEST99.lock"
    lock.write_text("pid=123", encoding="utf-8")

    assert len(reg.cargar()) == 1                      # el lock no es una entrada
    assert lock.exists()                               # y no se manda a cuarentena
    assert not list(raiz.glob("*.corrupto.*"))


# ------------------------------------------------------------- la atomicidad

def test_alta_es_atomica_atravesando_la_api(tmp_path, monkeypatch):
    """H7-03: se parchea `os.replace` EN EL MÓDULO DE PRODUCCIÓN y se invoca `alta()`.

    La versión anterior de este contrato decía «simulado escribiendo el temporal y no
    renombrando», que no llama a `alta()` — y por tanto pasa aunque producción escriba
    el destino in-place y jamás use `os.replace`.
    """
    reg = _registro(tmp_path)
    reg.alta(_entrada(tmp_path, sufijo="_previa"))
    destino = tmp_path / "registro" / "W-TEST99.json"
    antes = destino.read_bytes()

    vistos: list[tuple[Path, Path]] = []

    def _replace_que_falla(src, dst):
        vistos.append((Path(src), Path(dst)))
        raise OSError("disco lleno a mitad del rename")

    monkeypatch.setattr(wr.os, "replace", _replace_que_falla)
    with pytest.raises(OSError):
        reg.alta(_entrada(tmp_path, tipo="scratch", sufijo="_nueva"))

    assert destino.read_bytes() == antes, "el destino cambio: la escritura no fue atomica"
    assert vistos, "`alta()` no paso por `os.replace`: escribe in-place"
    src, dst = vistos[0]
    assert dst == destino
    assert src != destino, "el `src` del replace ES el destino: no hubo temporal"
    assert src.parent == destino.parent, (
        "el temporal no esta en el MISMO directorio que el destino: `os.replace` "
        "solo es atomico dentro del mismo sistema de ficheros")


def test_alta_no_escribe_in_place(tmp_path, monkeypatch):
    """El mutante obligatorio de H7-03, fijado como test: si producción usa
    `write_text` sobre el destino en vez de temporal + `os.replace`, esto muere."""
    reg = _registro(tmp_path)
    vistos: list[str] = []
    real = wr.os.replace

    def _espia(src, dst):
        vistos.append(str(dst))
        return real(src, dst)

    monkeypatch.setattr(wr.os, "replace", _espia)
    reg.alta(_entrada(tmp_path))
    assert vistos, "`alta()` no pasó por `os.replace`: escribe in-place"
    assert vistos[0].endswith("W-TEST99.json")


# ------------------------------------------------------------- el fallo cerrado

def test_un_registro_corrupto_lanza_y_no_devuelve_vacio(tmp_path):
    """H7-02: devolver `[]` borra la diferencia entre «no había workspace local» y
    «no puedo saber qué había». La segunda es la que impide autorizar Drive."""
    reg = _registro(tmp_path)
    raiz = tmp_path / "registro"
    raiz.mkdir(parents=True, exist_ok=True)
    # Truncado a mitad de una entrada, con el comienzo de una ruta local dentro.
    (raiz / "W-TEST99.json").write_text(
        '[{"case_id": "BaRS9 - Prueba - (W-TEST99) - Vuelta", "local_p',
        encoding="utf-8")
    with pytest.raises(wr.RegistryUnreadable):
        reg.cargar()


def test_el_corrupto_se_cuarentena_con_sus_bytes_intactos(tmp_path):
    reg = _registro(tmp_path)
    raiz = tmp_path / "registro"
    raiz.mkdir(parents=True, exist_ok=True)
    crudo = '[{"case_id": "BaRS9 - Prueba - (W-TEST99) - Vuelta", "local_p'
    (raiz / "W-TEST99.json").write_text(crudo, encoding="utf-8")

    with pytest.raises(wr.RegistryUnreadable):
        reg.cargar()

    cuarentena = list(raiz.glob("W-TEST99.json.corrupto.*"))
    assert len(cuarentena) == 1, "los bytes no se preservaron"
    assert cuarentena[0].read_text(encoding="utf-8") == crudo
    assert AHORA.replace(":", "-") in cuarentena[0].name, \
        "el nombre de la cuarentena no lleva el `ts` INYECTADO"


def test_el_corrupto_no_se_borra_nunca(tmp_path):
    reg = _registro(tmp_path)
    raiz = tmp_path / "registro"
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "W-TEST99.json").write_text("{roto", encoding="utf-8")
    with pytest.raises(wr.RegistryUnreadable):
        reg.cargar()
    assert list(raiz.glob("*.corrupto.*")), "se borró en vez de cuarentenarse"


def test_un_schema_no_soportado_lanza_y_no_adivina(tmp_path):
    reg = _registro(tmp_path)
    raiz = tmp_path / "registro"
    raiz.mkdir(parents=True, exist_ok=True)
    entrada = {
        "case_id": "BaRS9 - Prueba - (W-TEST99) - Vuelta",
        "w_code": "W-TEST99",
        "canonical_ref": "id_go",
        "local_path": str(tmp_path / "local"),
        "nonce": "n",
        "maquina": "M",
        "tipo": "checkout",
        "ultima_validacion": AHORA,
        "schema": wr.SCHEMA_SOPORTADO + 99,
    }
    (raiz / "W-TEST99.json").write_text(json.dumps([entrada]), encoding="utf-8")
    with pytest.raises(wr.SchemaNoSoportado):
        reg.cargar()


# ------------------------------------------------------------------ revalidar

def test_revalidar_usa_el_ts_inyectado_y_no_un_reloj_propio(tmp_path):
    """La pieza es pura: dos registros con `ahora` distinto dan resultados distintos,
    y ninguno consulta el reloj del sistema."""
    reg = _registro(tmp_path, ahora="2026-01-01T00:00:00Z")
    e = _entrada(tmp_path)
    reg.alta(e)
    reg.revalidar(wm.CaseRef(w_code="W-TEST99"), local_path=e.local_path)
    assert reg.buscar(wm.CaseRef(w_code="W-TEST99"))[0].ultima_validacion \
        == "2026-01-01T00:00:00Z"


def test_revalidar_de_lo_que_no_existe_lanza(tmp_path):
    reg = _registro(tmp_path)
    with pytest.raises(wm.LocalWorkspaceMissing):
        reg.revalidar(wm.CaseRef(w_code="W-TEST99"), local_path=tmp_path / "x")


# -------------------------------------------------------------- concurrencia

def test_dos_altas_de_w_codes_distintos_sobreviven_ambas(tmp_path):
    """H7-04: con un JSON agregado, el segundo reemplazo borraría el alta del primero.

    Se simula la carrera con la barrera peor: los dos leen el estado ANTES de que
    ninguno escriba, y luego escriben.
    """
    raiz = tmp_path / "registro"
    a = wr.WorkspaceRegistry(raiz, ahora=AHORA)
    b = wr.WorkspaceRegistry(raiz, ahora=AHORA)

    ea = _entrada(tmp_path, w_code="W-AAAA1", sufijo="_a")
    eb = _entrada(tmp_path, w_code="W-BBBB2", sufijo="_b")

    a.cargar()                    # ← barrera: ambos leen antes de escribir
    b.cargar()
    a.alta(ea)
    b.alta(eb)

    final = wr.WorkspaceRegistry(raiz, ahora=AHORA).cargar()
    assert {e.w_code for e in final} == {"W-AAAA1", "W-BBBB2"}


# ------------------------------------------------------------------- higiene

def test_el_fichero_no_contiene_secretos_ni_contenido_de_documentos(tmp_path):
    """§16: el registro guarda punteros, no contenido. Ni tokens ni texto del caso."""
    reg = _registro(tmp_path)
    reg.alta(_entrada(tmp_path))
    crudo = (tmp_path / "registro" / "W-TEST99.json").read_text(encoding="utf-8")
    for prohibido in ("PHPSESSID", "refreshToken", "password", "Bearer ",
                      "client_secret", "-----BEGIN"):
        assert prohibido not in crudo
    # Y solo las claves declaradas: nada de campos libres donde colar contenido.
    for entrada in json.loads(crudo):
        assert set(entrada) == {
            "case_id", "w_code", "canonical_ref", "local_path", "nonce",
            "maquina", "tipo", "ultima_validacion", "schema"}


def test_buscar_por_case_id_tambien_encuentra(tmp_path):
    """`CaseRef` admite identidad por `case_id` sin W-code; el registro la resuelve
    aunque el layout esté indexado por W-code."""
    reg = _registro(tmp_path)
    e = _entrada(tmp_path)
    reg.alta(e)
    assert reg.buscar(wm.CaseRef(case_id=e.case_id))[0].w_code == "W-TEST99"
