"""Reconciliación del manifiesto en `--force`, ledger monotónico y permutación.

Spec: 2026-08-01-identidad-segmento-bundle-design.md §3.2, §3.3 y §5 (rev. 4).
"""
from __future__ import annotations

import pytest

from core import split_documental as split
from core.split_documental import ManifestValidationError


def _man(entradas, *, next_doc_id, retirados=(), fuente="01_Drive EV/b.pdf"):
    """Manifiesto mínimo: [(doc_id, pp, tipo)] → dict con ledger."""
    return {"fuente": fuente, "bundle_sha256": "a" * 64,
            "segmentos": [{"seg": i, "doc_id": did, "pp": pp, "tipo": tipo,
                           "role": "documento"}
                          for i, (did, pp, tipo) in enumerate(entradas, 1)],
            "delimitadores": [], "next_doc_id": next_doc_id, "retirados": list(retirados)}


def _propuesto(rangos):
    """Lo que `construir_manifiesto` produciría de una detección fresca: [(pp, tipo)]."""
    segs = [split.Segmento(i, int(pp.split("-")[0]), int(pp.split("-")[1]), tipo)
            for i, (pp, tipo) in enumerate(rangos, 1)]
    return split.construir_manifiesto("01_Drive EV/b.pdf", "b" * 64, segs, set())


def test_pp_identico_hereda_la_identidad():
    """Caso 1 de §5: reprocesar sin cambiar la segmentación conserva el doc_id.

    Es EL caso de uso real (re-OCR). Si esto no se cumple, todo lo demás sobra.
    """
    previo = _man([("d01", "1-3", "DOC_ARRAS"), ("d02", "5-9", "DOC_PBC")],
                  next_doc_id="d03")
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOC_ARRAS"),
                                                           ("5-9", "DOC_PBC")]))
    assert [e["doc_id"] for e in rec.manifiesto["segmentos"]] == ["d01", "d02"]
    assert rec.heredados == ["d01", "d02"] and rec.acunados == []
    assert rec.manifiesto["next_doc_id"] == "d03"      # no se acuñó nada: no avanza


def test_rango_nuevo_disjunto_acuna_del_high_water_mark():
    """Caso 2 de §5, con el ledger haciendo su trabajo."""
    previo = _man([("d01", "1-3", "DOC_ARRAS")], next_doc_id="d02")
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOC_ARRAS"),
                                                           ("5-9", "DOC_PBC")]))
    assert [e["doc_id"] for e in rec.manifiesto["segmentos"]] == ["d01", "d02"]
    assert rec.acunados == ["d02"]
    assert rec.manifiesto["next_doc_id"] == "d03"


def test_solape_sin_igualdad_detiene_el_force():
    """Caso 3 de §5: un split real (1-6 → 1-3 + 4-6) NO se empareja a ojo.

    Ningún rango nuevo iguala al viejo y los dos solapan: no hay identidad que heredar
    y el desempate por solape admitiría empates. Se para y decide una persona.
    """
    previo = _man([("d01", "1-6", "DOCUMENTO")], next_doc_id="d02")
    with pytest.raises(ManifestValidationError, match="solap"):
        split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOCUMENTO"),
                                                         ("4-6", "DOCUMENTO")]))


def test_entrada_desaparecida_se_retira_y_se_devuelve_para_archivar():
    """Caso 4 de §5: el doc_id va a tombstones y el llamador archiva sus artefactos."""
    previo = _man([("d01", "1-3", "DOC_ARRAS"), ("d02", "5-9", "DOC_PBC")],
                  next_doc_id="d03")
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "DOC_ARRAS")]))
    assert rec.manifiesto["retirados"] == ["d02"]
    assert [e["doc_id"] for e in rec.retirados] == ["d02"]
    assert rec.retirados[0]["tipo"] == "DOC_PBC", "hace falta el tipo para el slug viejo"


def test_retirar_el_maximo_no_permite_reutilizarlo():
    """§3.2: «correlativo al máximo existente» y «nunca reutiliza un retirado» no podían
    ser verdad a la vez. Con el high-water mark la contradicción desaparece."""
    previo = _man([("d01", "1-3", "A")], next_doc_id="d03", retirados=["d02"])
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "A"), ("5-9", "B")]))
    nuevos = [e["doc_id"] for e in rec.manifiesto["segmentos"]]
    assert "d02" not in nuevos, "reutilizó un doc_id dado de baja"
    assert nuevos == ["d01", "d03"] and rec.manifiesto["next_doc_id"] == "d04"


def test_retirados_acumula_los_tombstones_previos():
    """§8.4 lo exige por escrito y NINGÚN test lo comprobaba (H-22, mutante vivo).

    El mutante —`retirados` que no concatena el previo— pasaba los dos tests que tocan
    el ledger, porque uno no asserta `retirados` y el otro parte de `retirados=[]`.
    Perdido el tombstone, `validar_identidad` deja de vetar ese doc_id y el fallback de
    `_next_doc_id_de` recalcula un high-water MÁS BAJO: es N-B0-2 por la puerta de atrás.
    """
    previo = _man([("d01", "1-3", "A"), ("d03", "5-9", "B")], next_doc_id="d04",
                  retirados=["d02"])
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "A")]))
    assert rec.manifiesto["retirados"] == ["d02", "d03"], "se perdió un tombstone previo"
    con_d02 = {**rec.manifiesto,
               "segmentos": [{"seg": 1, "doc_id": "d02", "pp": "1-3", "tipo": "A",
                              "role": "documento"}]}
    with pytest.raises(ManifestValidationError, match="retirados"):
        split.validar_identidad(con_d02)


def test_pp_no_canonico_hereda_igual():
    """El manifiesto lo edita una persona: `01-03` es el mismo rango que `1-3` (H-06).

    Con el índice por cadena, la herencia fallaba Y el chequeo de solape casaba, así que
    `--force` abortaba diciendo que `1-3` «solapa con ['01-03']» — sobre sí mismo, y sin
    salida posible salvo editar el fichero a mano.
    """
    previo = _man([("d01", "01-03", "A"), ("d02", " 5 - 9 ", "B")], next_doc_id="d03")
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "A"), ("5-9", "B")]))
    assert [e["doc_id"] for e in rec.manifiesto["segmentos"]] == ["d01", "d02"]
    assert rec.acunados == []


def test_manifiesto_mixto_acuna_pero_lo_declara():
    """Acuñar sobre una entrada legacy es correcto; hacerlo callando, no (H-07)."""
    previo = {"fuente": "01_Drive EV/b.pdf", "bundle_sha256": "a" * 64,
              "delimitadores": [], "next_doc_id": "d02", "retirados": [],
              "segmentos": [{"seg": 1, "doc_id": "d01", "pp": "1-3", "tipo": "A",
                             "role": "documento"},
                            {"seg": 2, "pp": "5-9", "tipo": "B", "role": "documento"}]}
    rec = split.reconciliar_manifiesto(previo, _propuesto([("1-3", "A"), ("5-9", "B")]))
    assert rec.acunados == ["d02"]
    assert rec.legacy_sin_identidad == ["5-9"], "la entrada legacy debe quedar declarada"


def test_manifiesto_sin_segmentos_aborta():
    """`segmentos: []` archivaba el bundle entero, no publicaba nada y salía 0 (H-11)."""
    with pytest.raises(ManifestValidationError, match="al menos un segmento"):
        split.validar_identidad(_man([], next_doc_id="d01"))


def test_un_doc_id_retirado_en_los_segmentos_aborta():
    man = _man([("d01", "1-3", "A"), ("d02", "5-9", "B")], next_doc_id="d03",
               retirados=["d02"])
    with pytest.raises(ManifestValidationError, match="retirados"):
        split.validar_identidad(man)


def test_doc_id_repetido_aborta():
    man = _man([("d01", "1-3", "A"), ("d01", "5-9", "B")], next_doc_id="d02")
    with pytest.raises(ManifestValidationError, match="repetido"):
        split.validar_identidad(man)


def test_next_doc_id_por_debajo_de_lo_usado_aborta():
    man = _man([("d05", "1-3", "A")], next_doc_id="d02")
    with pytest.raises(ManifestValidationError, match="high-water"):
        split.validar_identidad(man)


def test_manifiesto_legacy_sin_doc_id_pide_el_retrofit_por_su_nombre():
    """No se acuñan identidades en silencio sobre un esquema viejo (decisión 4 del plan)."""
    man = {"fuente": "01_Drive EV/b.pdf", "bundle_sha256": "a" * 64,
           "segmentos": [{"seg": 1, "pp": "1-3", "tipo": "A", "role": "documento"}],
           "delimitadores": []}
    with pytest.raises(ManifestValidationError, match="retrofit"):
        split.validar_identidad(man)
    split.validar_identidad(man, exigir_doc_id=False)   # bajo --force sí se tolera


def test_permutacion_de_identidades_aborta():
    """§3.3: el conjunto de `pp` no cambia pero la correspondencia sí → identidades cruzadas."""
    man = _man([("d01", "5-9", "A"), ("d02", "1-3", "B")], next_doc_id="d03")
    with pytest.raises(ManifestValidationError, match="permutaci"):
        split.validar_edicion(man, {"d01": "1-3", "d02": "5-9"})


def test_editar_el_pp_a_un_rango_nuevo_esta_permitido():
    """La corrección del letrado es legítima: el manifiesto es SU gate."""
    man = _man([("d01", "1-4", "A"), ("d02", "5-9", "B")], next_doc_id="d03")
    split.validar_edicion(man, {"d01": "1-3", "d02": "5-9"})   # no lanza


def test_sin_baseline_no_se_finge_la_comprobacion():
    """Primera corrida o caso legacy sin `_cobertura.json`: no hay contra qué comparar."""
    man = _man([("d01", "5-9", "A")], next_doc_id="d02")
    split.validar_edicion(man, {})                              # no lanza


def test_validar_manifiesto_sigue_mirando_los_rangos_primero():
    """Los mensajes de rango/solape que ya existían no cambian de forma."""
    man = _man([("d01", "1-4", "X"), ("d02", "3-9", "Y")], next_doc_id="d03")
    with pytest.raises(ValueError, match="solap"):
        split.validar_manifiesto(man, total_pag=20)
