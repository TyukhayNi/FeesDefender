"""Arnés de mutación de P4 — `[APER-61]` y la sala de lectura sin parada obligatoria.

Mismo contrato que `tests/_mutantes_fila30.py`, y **en el repo por su misma lección**: el
«17 de 17» de la fila #30 se corrió desde un script del scratchpad y resultó ser 16 de 17
al portarlo aquí, porque el script solo miraba si la suite seguía verde. Una cifra que
nadie puede reproducir no es un dato.

## Lo que comprueba, y por qué la segunda mitad es la que importa

Dos cosas por mutante:

1. que el mutante **mate al test al que se le apunta**, y
2. que ese test estuviera **verde antes de mutar**.

Sin la segunda, un mutante que muere por un test cualquiera cuenta como muerto y la guarda
que venía a fijar puede no haber mordido nunca.

No es un test de pytest y no corre en la suite (el nombre empieza por `_`): muta ficheros
del árbol. Se ejecuta a mano, **con el árbol limpio**:

    python -m tests._mutantes_p4
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

SL = "core/sala_lectura.py"
CLI = "scripts/sala_lectura.py"
T_P4 = "tests/test_sala_lectura_p4_sin_parada.py"
T_SL = "tests/test_sala_lectura.py"

#: (nombre, fichero a mutar, texto original, texto mutado, test que DEBE ponerse rojo).
MUTANTES: list[tuple[str, str, str, str, str]] = [
    # --- Pieza 1: [APER-61], la identidad se enruta por parte ------------------------
    ("M01 la identidad del vendedor vuelve a PBC", SL,
     '    ("06. PBC", ("anexo 1", "anexo 2", "anexos 1", "anexos 2", "pbc", "blanqueo")),',
     '    ("06. PBC", ("anexo 1", "anexo 2", "anexos 1", "anexos 2", "pbc", "blanqueo",\n'
     '                "dni", "nie", "pasaporte", "nota simple", "titularidad")),',
     f"{T_P4}::test_aper61_la_identidad_no_va_a_pbc"),

    ("M02 la activación deja de reconocer la identidad", SL,
     '                        "dni", "nie", "pasaporte", "nota simple", "titularidad")),',
     '                        )),',
     f"{T_P4}::test_aper61_la_identidad_no_va_a_pbc"),

    ("M03 los Anexos 1 y 2 dejan de ser PBC", SL,
     '    ("06. PBC", ("anexo 1", "anexo 2", "anexos 1", "anexos 2", "pbc", "blanqueo")),',
     '    ("06. PBC", ("pbc", "blanqueo")),',
     f"{T_P4}::test_aper61_la_identidad_no_va_a_pbc"),

    ("M04 la hoja de visita vuelve a ser activación (era del comprador)", SL,
     '    ("03. OFERTAS", ("oferta", "contraoferta", "hoja de visita", "ficha comprador")),',
     '    ("03. OFERTAS", ("oferta", "contraoferta")),',
     f"{T_P4}::test_aper61_la_hoja_de_visita_es_del_comprador"),

    # --- Pieza 1b: la frontera del token (límite IZQUIERDO, y solo izquierdo) --------
    ("M05 sin límite de palabra: el token vuelve a casar DENTRO de otra", SL,
     '    (categoria, re.compile("|".join(r"\\b" + re.escape(t) for t in tokens)))',
     '    (categoria, re.compile("|".join(re.escape(t) for t in tokens)))',
     f"{T_P4}::test_un_token_no_casa_dentro_de_otra_palabra"),

    ("M06 límite TAMBIÉN a la derecha: se pierden `oferta2` y `PBC1`", SL,
     '    (categoria, re.compile("|".join(r"\\b" + re.escape(t) for t in tokens)))',
     '    (categoria, re.compile("|".join(r"\\b" + re.escape(t) + r"\\b" for t in tokens)))',
     f"{T_P4}::test_un_token_tolera_el_sufijo_de_su_palabra"),

    # --- Pieza 2: el residuo se marca, y se marca con la confianza de la ausencia ----
    ("M07 el residuo vuelve a salir SIN tipo", SL,
     "        e.tipo_documental = CATEGORIA_PENDIENTE",
     "        e.tipo_documental = None",
     f"{T_P4}::test_el_residuo_recibe_pendiente_con_confianza_cero"),

    ("M08 el pendiente nace con confianza plena: queda CONGELADO", SL,
     "        e.confianza = _CONF_PENDIENTE",
     "        e.confianza = 1.0",
     f"{T_P4}::test_el_pendiente_no_se_congela_en_la_corrida_siguiente"),

    ("M09 `_CONF_PENDIENTE` sube por encima del umbral", SL,
     "_CONF_PENDIENTE = 0.0",
     "_CONF_PENDIENTE = 0.9",
     f"{T_P4}::test_el_residuo_recibe_pendiente_con_confianza_cero"),

    ("M10 el pendiente pierde su fecha inferida (entraría como 0000-00-00)", SL,
     "        fecha, fuente = _fecha_de(case_id, e)\n"
     "        e.tipo_documental = CATEGORIA_PENDIENTE\n"
     "        e.fecha_doc, e.fecha_fuente = fecha, fuente",
     "        e.tipo_documental = CATEGORIA_PENDIENTE",
     f"{T_P4}::test_el_pendiente_entra_con_su_fecha_no_con_ceros"),

    # --- Pieza 2b: `organizar` ya no aborta -----------------------------------------
    ("M11 vuelve la parada: con residuo no se monta nada", SL,
     "    aplicar_clasificacion(case_id, solo_residuo=True)\n"
     "    clasif = clasificar_caso(case_id)\n"
     "    render_indices(case_id)",
     "    aplicar_clasificacion(case_id, solo_residuo=True)\n"
     "    clasif = clasificar_caso(case_id)\n"
     "    if clasif['n_residuo']:\n"
     "        return {'case_id': case_id, 'n_pendientes': clasif['n_residuo'],\n"
     "                'acciones': {}, 'sin_material': False,\n"
     "                'worklist': str(_revisar_dir(case_id) / WORKLIST_NAME)}\n"
     "    render_indices(case_id)",
     f"{T_SL}::test_cli_organizar_YA_NO_se_detiene_con_residuo"),

    ("M12 `n_pendientes` miente: siempre cero", SL,
     '    return {"case_id": case_id, "n_pendientes": clasif["n_residuo"],',
     '    return {"case_id": case_id, "n_pendientes": 0,',
     f"{T_P4}::test_organizar_monta_la_sala_aunque_haya_residuo"),

    ("M13 la sala se monta pero SIN poblar (solo índices)", SL,
     "    pob = poblar_sala_lectura(case_id, crm_docs=crm_docs)",
     "    pob = {'acciones': {}}",
     f"{T_P4}::test_organizar_monta_la_sala_aunque_haya_residuo"),

    ("M14 la worklist deja de escribirse (se pierde el camino de corrección)", SL,
     "    _write_worklist(case_id, residuo)",
     "    pass",
     f"{T_P4}::test_la_worklist_se_sigue_escribiendo_con_el_residuo"),

    # --- La frontera: qué cuenta como decisión --------------------------------------
    ("M15 `es_decision` acepta el 08 como clasificación", SL,
     '    return bool(t) and t in TAXONOMIA_EV and t != CATEGORIA_PENDIENTE',
     "    return bool(t) and t in TAXONOMIA_EV",
     f"{T_P4}::test_un_08_escrito_en_la_worklist_no_congela_el_documento"),

    ("M16 un 08 escrito a mano se aplica con confianza plena", SL,
     "        e.confianza = 1.0 if es_decision(tipo) else _CONF_PENDIENTE",
     "        e.confianza = 1.0",
     f"{T_P4}::test_un_08_escrito_en_la_worklist_no_congela_el_documento"),

    ("M17 `_hashes_residuo` vuelve a preguntar por la taxonomía entera", SL,
     "            if not es_decision(f[\"Tipo\"])]",
     "            if f['Tipo'].strip() not in TAXONOMIA_EV]",
     f"{T_P4}::test_un_08_escrito_en_la_worklist_no_congela_el_documento"),

    ("M18 la worklist rellenada deja de pisar el pendiente", SL,
     "        ya_resuelto = bool(e.tipo_documental) and (e.confianza or 0) >= UMBRAL_CONFIANZA_AUTOMOVE",
     "        ya_resuelto = bool(e.tipo_documental)",
     f"{T_P4}::test_la_worklist_rellenada_pisa_el_pendiente"),

    # --- La regla conserva su «no lo sé» ---------------------------------------------
    ("M19 `_categoria_por_nombre` decide el 08 por su cuenta", SL,
     "    for categoria, patron in _KEYWORDS_RE:\n"
     "        if patron.search(low):\n"
     "            return categoria\n"
     "    return None",
     "    for categoria, patron in _KEYWORDS_RE:\n"
     "        if patron.search(low):\n"
     "            return categoria\n"
     "    return CATEGORIA_PENDIENTE",
     f"{T_P4}::test_categoria_por_nombre_sigue_devolviendo_none_sin_pistas"),

    # --- La guarda de «no había nada que hacer» no se toca ---------------------------
    ("M20 quitar la parada se lleva por delante la guarda de sin_material", SL,
     '        return {"case_id": case_id, "n_pendientes": 0,\n'
     '                "acciones": {}, "sin_material": True, "motivo": motivo,',
     '        return {"case_id": case_id, "n_pendientes": 0,\n'
     '                "acciones": {}, "sin_material": False, "motivo": motivo,',
     f"{T_P4}::test_sin_material_sigue_sin_montar_nada"),
]

#: (nombre, motivo). Mutantes que se conservan sin exigirles muerte, con su razón escrita.
SUPERVIVIENTES_DECLARADOS: list[tuple[str, str]] = [
    ("el AVISO del CLI sobre los pendientes (`scripts/sala_lectura.py`)",
     "No hay mutante que lo mate porque no hay test que lo cubra: el subcomando "
     "`organizar` del CLI no tiene test propio —no lo tenía antes de P4 tampoco— y lo que "
     "este diff le cambia es el TEXTO que imprime, no una decisión. El contenido "
     "verificable (que hay pendientes y cuántos) sale de `n_pendientes`, que sí está "
     "cubierto por M12. Se declara en vez de fabricar un test de `CliRunner` que solo "
     "comprobaría que una cadena contiene otra cadena."),
]


def _corre(test: str) -> int:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:randomly", test],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    return r.returncode


def main() -> int:
    fallos: list[str] = []
    for nombre, fichero, viejo, nuevo, test in MUTANTES:
        objetivo = RAIZ / fichero
        s = io.open(objetivo, encoding="utf-8").read()
        if viejo not in s:
            print(f"[ARNES ROTO] {nombre}: el texto original ya no esta en {fichero}")
            fallos.append(nombre)
            continue
        if _corre(test) != 0:
            print(f"[ARNES ROTO] {nombre}: {test.split('::')[-1]} YA estaba rojo sin mutar")
            fallos.append(nombre)
            continue
        io.open(objetivo, "w", encoding="utf-8", newline="\n").write(
            s.replace(viejo, nuevo, 1))
        try:
            rc = _corre(test)
        finally:
            io.open(objetivo, "w", encoding="utf-8", newline="\n").write(s)
        if rc == 0:
            print(f"[SUPERVIVIENTE] {nombre}  <- no lo mata {test.split('::')[-1]}")
            fallos.append(nombre)
        else:
            print(f"[muerto] {nombre}")

    print()
    print(f"{len(MUTANTES)} mutantes, {len(MUTANTES) - len(fallos)} muertos.")
    print("SUPERVIVIENTES/ROTOS:", ", ".join(fallos) if fallos else "ninguno")
    for nombre, motivo in SUPERVIVIENTES_DECLARADOS:
        print()
        print("[DECLARADO, no matado] " + nombre)
        print("  " + motivo)
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
