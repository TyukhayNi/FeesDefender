"""El `estado.json` por ronda de V1.

Spec §11 (tabla de riesgos): «reanudacion sin generacion comun -> fase verde sobre inputs
obsoletos -> `estado.json` atomico OBLIGATORIO desde la primera entrega».
Plan: docs/superpowers/plans/2026-09-03-apertura-v1-plan5-cableado.md, Task 8b.
"""
import json

from core import apertura_v1_estado as est


def test_sin_fichero_no_hay_ronda(tmp_path):
    assert est.leer(tmp_path) is None


def test_f27_la_escritura_es_atomica_y_lleva_id_de_ronda(tmp_path, monkeypatch):
    """F27. Escribir en sitio deja un JSON truncado si el proceso muere a mitad, y un
    estado ilegible es peor que ninguno: la siguiente ronda no sabe que hubo una."""
    reemplazos = []
    real = est.os.replace
    monkeypatch.setattr(est.os, "replace",
                        lambda a, b: (reemplazos.append((a, b)), real(a, b))[1])
    r = est.abrir(tmp_path, ronda_id="r1", ahora="2026-09-03T10:00:00+00:00")
    assert r.ronda_id == "r1"
    assert reemplazos, "la escritura no paso por os.replace"
    escrito = json.loads((tmp_path / "00_Input" / "_apertura_v1.json")
                         .read_text(encoding="utf-8"))
    assert escrito["ronda_id"] == "r1"


def test_f28_una_ronda_sin_cerrar_se_detecta(tmp_path):
    """F28. Es la propiedad entera: si la ronda anterior no se cerro, la siguiente NO
    puede tratar su salida como buena."""
    est.abrir(tmp_path, ronda_id="r1", ahora="2026-09-03T10:00:00+00:00")
    previa = est.leer(tmp_path)
    assert previa.terminada is None
    assert previa.sin_cerrar() is True


def test_una_ronda_cerrada_no_esta_sin_cerrar(tmp_path):
    r = est.abrir(tmp_path, ronda_id="r1", ahora="2026-09-03T10:00:00+00:00")
    est.cerrar(tmp_path, r, estado="preparado_con_pendientes",
               etapas={"drive": "hecha"}, ahora="2026-09-03T10:05:00+00:00")
    leida = est.leer(tmp_path)
    assert leida.sin_cerrar() is False
    assert leida.estado == "preparado_con_pendientes"
    assert leida.etapas == {"drive": "hecha"}


def test_un_estado_ilegible_se_trata_como_ausente(tmp_path):
    (tmp_path / "00_Input").mkdir(parents=True)
    (tmp_path / "00_Input" / "_apertura_v1.json").write_text("{roto", encoding="utf-8")
    assert est.leer(tmp_path) is None


def test_un_json_valido_sin_las_claves_minimas_tambien_es_ausente(tmp_path):
    (tmp_path / "00_Input").mkdir(parents=True)
    (tmp_path / "00_Input" / "_apertura_v1.json").write_text('{"otra": 1}',
                                                             encoding="utf-8")
    assert est.leer(tmp_path) is None


def test_no_queda_temporal_tras_una_escritura_correcta(tmp_path):
    est.abrir(tmp_path, ronda_id="r1", ahora="2026-09-03T10:00:00+00:00")
    sueltos = [p.name for p in (tmp_path / "00_Input").iterdir()
               if p.name.startswith(".apertura_v1.")]
    assert sueltos == []
