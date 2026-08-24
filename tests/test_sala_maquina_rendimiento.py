"""Coste de montaje de la sala de máquina: caché de hash, tope de reintentos, tiempos.

Tres costes verificados en código el 2026-08-04, ninguno de ellos el que suponía el
backlog (que apuntaba al disco de `01_OCR/`):

1. **`inventariar()` rehashea todo `00_Input` en cada corrida** — `file_sha256` sobre
   TODOS los ficheros solo para decidir qué saltarse. En W-02VND1 son 2,6 GB por corrida
   aunque no haya un solo documento nuevo (`MEJORAS #48`, anotación 2026-07-23).
2. **Los documentos que no se resuelven se re-OCR-izan para siempre** — el estado guarda
   solo los ÉXITOS (`{"procesados": [...]}`), así que un fallo vuelve a pagar OCR real en
   cada `apply`. ~169 documentos en W-02VND1 (`MEJORAS #84`).
3. **Nadie ha medido dónde se va el tiempo**, así que «¿duele la primera corrida o las
   re-corridas?» no se puede contestar. Sin ese dato, paralelizar el OCR es una apuesta:
   `ocr_pdf` no pasa `jobs`, luego ocrmypdf ya paraleliza **por página** con todos los
   núcleos, y el paralelismo externo puede comprar mucho (muchos documentos cortos) o casi
   nada (un escaneado largo).

**Por qué la caché es local y NO lee `00_Input/_intake_hashes.json`**, contra lo que
sugería `#48`: el manifiesto M9 está indexado **sha → rutas**, no ruta → sha; **no lleva
`size` ni `mtime`**, así que no hay forma de validar que su hash siga vigente —y confiar
en un hash sin validar debilita la cadena de custodia por la que el sha existe—; y está
incompleto (`core/intake_drive.py` no registra en él). La caché de aquí se invalida por
`(size, mtime_ns)` y **falla al lado seguro**: en `G:` el mtime puede cambiar al
rehidratar, y entonces se rehashea. Más lento, nunca incorrecto.

Datos SIEMPRE sintéticos. Ningún test mide tiempo real de reloj: se comprueba la
estructura del rastro, no su valor.
"""

from __future__ import annotations

import json
import os

import pytest

import scripts.sala_maquina as cli
from core import sala_maquina as sm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def caso(tmp_path, monkeypatch):
    """Caso con dos PDF en `00_Input`, sin nada procesado todavía."""
    case_dir = tmp_path / "BaRS9 - Prueba - (W-TEST99) - Vuelta"
    drive = case_dir / "00_Input" / "01_Drive EV"
    drive.mkdir(parents=True)
    (drive / "encargo.pdf").write_bytes(b"%PDF-1.4 encargo")
    (drive / "escaneo.pdf").write_bytes(b"%PDF-1.4 escaneo")

    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)
    return case_dir


def _contador_de_hash(monkeypatch) -> list[str]:
    """Sustituye `file_sha256` por un espía que cuenta a QUIÉN se hashea."""
    hasheados: list[str] = []
    real = sm.file_sha256

    def espia(path):
        hasheados.append(str(path))
        return real(path)

    monkeypatch.setattr(sm, "file_sha256", espia)
    return hasheados


def _estado(case_dir) -> dict:
    f = sm._sala_maquina_dir(case_dir) / cli._STATE
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _cob(rel: str, sha: str, *, estado: str = "empty") -> sm.DocCobertura:
    return sm.DocCobertura(slug=f"{rel.split('/')[-1]}__{sha[:8]}", rel_path=rel,
                           metodo="ocr", estado=estado, chars=0, sha256=sha,
                           parent_sha256=sha)


# ---------------------------------------------------------------------------
# 1. Caché de hash del inventario
# ---------------------------------------------------------------------------

def test_sin_cache_inventariar_hashea_todo(caso, monkeypatch):
    """Contrato de partida: la primera corrida no tiene nada que reutilizar."""
    hasheados = _contador_de_hash(monkeypatch)

    inv, cache = sm.inventariar_cacheado(caso, cache={})

    assert len(inv) == 2
    assert len(hasheados) == 2
    # La caché devuelta guarda con qué se validará la próxima vez.
    assert set(cache) == {"01_Drive EV/encargo.pdf", "01_Drive EV/escaneo.pdf"}


def test_con_cache_valida_no_se_rehashea_nada(caso, monkeypatch):
    """El caso que duele: re-corrida sin cambios. Hoy rehashea 2,6 GB."""
    _, cache = sm.inventariar_cacheado(caso, cache={})
    hasheados = _contador_de_hash(monkeypatch)

    inv, cache2 = sm.inventariar_cacheado(caso, cache=cache)

    assert hasheados == [], "una re-corrida sin cambios no debe hashear nada"
    # Y el inventario es el mismo: la caché no puede cambiar el resultado.
    assert {f["rel_path"]: f["sha256"] for f in inv} == \
           {r: v[2] for r, v in cache2.items()}


def test_si_cambia_el_contenido_se_rehashea_y_el_sha_es_nuevo(caso, monkeypatch):
    _, cache = sm.inventariar_cacheado(caso, cache={})
    antes = {f["rel_path"]: f["sha256"] for f in sm.inventariar_cacheado(caso, cache=cache)[0]}
    (caso / "00_Input" / "01_Drive EV" / "encargo.pdf").write_bytes(b"%PDF-1.4 OTRO texto")
    hasheados = _contador_de_hash(monkeypatch)

    inv, _ = sm.inventariar_cacheado(caso, cache=cache)

    assert len(hasheados) == 1, "solo el fichero cambiado se rehashea"
    ahora = {f["rel_path"]: f["sha256"] for f in inv}
    assert ahora["01_Drive EV/encargo.pdf"] != antes["01_Drive EV/encargo.pdf"]
    assert ahora["01_Drive EV/escaneo.pdf"] == antes["01_Drive EV/escaneo.pdf"]


def test_si_solo_cambia_el_mtime_se_rehashea_igual(caso, monkeypatch):
    """Falla al lado seguro: en `G:` el mtime baila al rehidratar.

    El resultado tiene que ser idéntico (mismo contenido → mismo sha); lo único que se
    paga es el hash. Confiar en el mtime al revés —dar por bueno el sha porque el mtime
    no cambió cuando el contenido sí— sería el fallo caro, y es el que fija el test de
    arriba.
    """
    _, cache = sm.inventariar_cacheado(caso, cache={})
    p = caso / "00_Input" / "01_Drive EV" / "encargo.pdf"
    st = p.stat()
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    hasheados = _contador_de_hash(monkeypatch)

    inv, cache2 = sm.inventariar_cacheado(caso, cache=cache)

    assert len(hasheados) == 1
    assert cache2["01_Drive EV/encargo.pdf"][2] == cache["01_Drive EV/encargo.pdf"][2]
    assert len(inv) == 2


def test_la_cache_no_conserva_ficheros_que_ya_no_existen(caso):
    """Sin poda, la caché de un caso grande crece sin techo con cada re-nombrado."""
    _, cache = sm.inventariar_cacheado(caso, cache={})
    (caso / "00_Input" / "01_Drive EV" / "escaneo.pdf").unlink()

    _, cache2 = sm.inventariar_cacheado(caso, cache=cache)

    assert set(cache2) == {"01_Drive EV/encargo.pdf"}


def test_apply_persiste_la_cache_en_el_estado(caso, monkeypatch):
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])

    cli.apply("W-TEST99")

    assert "hashes" in _estado(caso), "sin persistirla, la caché no sirve de nada"


# ---------------------------------------------------------------------------
# 2. Tope de reintentos de los no resueltos (MEJORAS #84)
# ---------------------------------------------------------------------------

def _falla_siempre(case_dir):
    """`ejecutar` que devuelve cobertura `empty` para todo lo que no se salta."""
    def _fake(cd, docs, *, case_id, vision=False, force=False, **kw):
        return [_cob(d.rel_path, d.sha256) for d in docs if not d.skip]
    return _fake


def test_un_documento_que_falla_se_reintenta_en_la_corrida_siguiente(caso, monkeypatch):
    """El comportamiento que NO hay que romper: un fallo transitorio se reintenta."""
    monkeypatch.setattr(cli.sm, "ejecutar", _falla_siempre(caso))

    cli.apply("W-TEST99")
    procesados_en_2a: list[int] = []

    def contar(cd, docs, *, case_id, vision=False, force=False, **kw):
        procesados_en_2a.append(len([d for d in docs if not d.skip]))
        return [_cob(d.rel_path, d.sha256) for d in docs if not d.skip]

    monkeypatch.setattr(cli.sm, "ejecutar", contar)
    cli.apply("W-TEST99")

    assert procesados_en_2a == [2], "un fallo debe reintentarse al menos una vez"


def test_agotado_el_tope_se_deja_de_reintentar(caso, monkeypatch):
    """El coste que se corta: ~169 documentos re-OCR-izados en cada corrida."""
    monkeypatch.setattr(cli.sm, "ejecutar", _falla_siempre(caso))
    for _ in range(sm.MAX_INTENTOS):
        cli.apply("W-TEST99")

    intentados: list[int] = []

    def contar(cd, docs, *, case_id, vision=False, force=False, **kw):
        intentados.append(len([d for d in docs if not d.skip]))
        return []

    monkeypatch.setattr(cli.sm, "ejecutar", contar)
    cli.apply("W-TEST99")

    assert intentados == [0], "tras el tope, no se vuelve a pagar OCR"


def test_los_agotados_se_declaran_en_cada_corrida(caso, monkeypatch, capsys):
    """La mitigación del footgun: si falta el motor OCR (`#91`) fallan TODOS.

    Sin este aviso, el caso se procesaría «en verde» saltándose el expediente entero.
    """
    monkeypatch.setattr(cli.sm, "ejecutar", _falla_siempre(caso))
    for _ in range(sm.MAX_INTENTOS):
        cli.apply("W-TEST99")
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    capsys.readouterr()

    cli.apply("W-TEST99")

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    assert "intentos agotados" in texto.lower()
    assert "2" in texto, "hay que decir CUÁNTOS, no solo que hay"


def test_force_reintenta_los_agotados(caso, monkeypatch):
    """La vía de escape, sin la cual un agotado sería una muerte definitiva."""
    monkeypatch.setattr(cli.sm, "ejecutar", _falla_siempre(caso))
    for _ in range(sm.MAX_INTENTOS):
        cli.apply("W-TEST99")

    intentados: list[int] = []

    def contar(cd, docs, *, case_id, vision=False, force=False, **kw):
        intentados.append(len([d for d in docs if not d.skip]))
        return []

    monkeypatch.setattr(cli.sm, "ejecutar", contar)
    cli.apply("W-TEST99", force=True)

    assert intentados == [2]


def test_un_exito_borra_los_intentos_acumulados(caso, monkeypatch):
    """Si no, un documento que falló dos veces y luego va bien arrastra el contador."""
    monkeypatch.setattr(cli.sm, "ejecutar", _falla_siempre(caso))
    cli.apply("W-TEST99")

    def ok(cd, docs, *, case_id, vision=False, force=False, **kw):
        return [_cob(d.rel_path, d.sha256, estado="ok") for d in docs if not d.skip]

    monkeypatch.setattr(cli.sm, "ejecutar", ok)
    cli.apply("W-TEST99")

    assert _estado(caso).get("intentos", {}) == {}


# ---------------------------------------------------------------------------
# 3. Instrumentación del tiempo
# ---------------------------------------------------------------------------

def test_apply_persiste_lo_que_el_gancho_le_entrega(caso, monkeypatch):
    """Doble FIEL: invoca `on_documento` como lo hace el motor real.

    Un doble que lo ignorase dejaría este test verde con cero líneas — probando el doble
    y no el cableado. La convención del repo ya se compró esa lección: siete tests con
    doble pasando sobre un defecto real (`test_sala_maquina_cableado_atomize`). Por eso
    abajo va además el mismo caso contra el motor de verdad.
    """
    def ok(cd, docs, *, case_id, vision=False, force=False, on_documento=None, **kw):
        filas = []
        for d in docs:
            if d.skip:
                continue
            mias = [_cob(d.rel_path, d.sha256, estado="ok")]
            filas.extend(mias)
            if on_documento is not None:
                on_documento(d, 7, mias)
        return filas

    monkeypatch.setattr(cli.sm, "ejecutar", ok)

    cli.apply("W-TEST99")

    f = sm._sala_maquina_dir(caso) / "_tiempos.jsonl"
    lineas = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    docs = [l for l in lineas if l.get("tipo") == "documento"]
    assert len(docs) == 2
    assert {d["ms"] for d in docs} == {7}
    assert {d["metodo"] for d in docs} == {"ocr"}
    assert {d["rel_path"] for d in docs} == {"01_Drive EV/encargo.pdf",
                                            "01_Drive EV/escaneo.pdf"}


def test_el_motor_real_dispara_el_gancho(tmp_path, monkeypatch):
    """Contra `sm.ejecutar` de verdad, sin doblarlo.

    Usa un `.txt` a propósito: entra por la vía `nativo`, que no llama a OCRmyPDF — así el
    test no depende de que Tesseract esté instalado ni tarda. Lo que se comprueba es que
    el gancho lo invoca el bucle REAL, que es justo lo que un doble no puede demostrar.
    """
    case_dir = tmp_path / "BaRS9 - Real - (W-TEST98) - Vuelta"
    (case_dir / "00_Input" / "04_Manual").mkdir(parents=True)
    (case_dir / "00_Input" / "04_Manual" / "nota.txt").write_text(
        "Encargo firmado el 3 de marzo. " * 20, encoding="utf-8")
    monkeypatch.setattr(cli, "caso_path", lambda cid: case_dir)
    monkeypatch.setattr(cli, "append_event", lambda destino, ev, *, details=None, case_id=None: None)
    monkeypatch.setattr(cli, "_atomizar_correo", lambda cid, cd: None)

    cli.apply("W-TEST98")

    f = sm._sala_maquina_dir(case_dir) / "_tiempos.jsonl"
    docs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
            if l.strip() and json.loads(l).get("tipo") == "documento"]
    assert len(docs) == 1
    assert docs[0]["rel_path"] == "04_Manual/nota.txt"
    assert docs[0]["metodo"] == "nativo"      # el método sale de la fila REAL
    assert docs[0]["estado"] == "ok"
    assert isinstance(docs[0]["ms"], int) and docs[0]["ms"] >= 0


def test_el_rastro_declara_el_coste_del_inventario(caso, monkeypatch):
    """Es la cifra que contesta «¿primera corrida o re-corridas?»."""
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])

    cli.apply("W-TEST99")

    f = sm._sala_maquina_dir(caso) / "_tiempos.jsonl"
    lineas = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    resumen = [l for l in lineas if l.get("tipo") == "corrida"]
    assert len(resumen) == 1
    assert isinstance(resumen[0]["ms_inventario"], int)
    assert isinstance(resumen[0]["ficheros_hasheados"], int)


def test_el_rastro_es_append_only_entre_corridas(caso, monkeypatch):
    """Comparar dos corridas es el uso entero del artefacto; sobrescribir lo anula."""
    monkeypatch.setattr(cli.sm, "ejecutar", lambda *a, **k: [])
    cli.apply("W-TEST99")
    cli.apply("W-TEST99")

    f = sm._sala_maquina_dir(caso) / "_tiempos.jsonl"
    corridas = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
                if l.strip() and json.loads(l).get("tipo") == "corrida"]
    assert len(corridas) == 2


def test_apply_imprime_el_resumen_de_tiempos(caso, monkeypatch, capsys):
    def ok(cd, docs, *, case_id, vision=False, force=False, **kw):
        return [_cob(d.rel_path, d.sha256, estado="ok") for d in docs if not d.skip]

    monkeypatch.setattr(cli.sm, "ejecutar", ok)

    cli.apply("W-TEST99")

    salida = capsys.readouterr().out
    assert "inventario" in salida.lower()
