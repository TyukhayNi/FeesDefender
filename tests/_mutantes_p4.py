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
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

SL = "core/sala_lectura.py"
CLI = "scripts/sala_lectura.py"
T_P4 = "tests/test_sala_lectura_p4_sin_parada.py"
T_SL = "tests/test_sala_lectura.py"
T_R1 = "tests/test_sala_lectura_p4_r1.py"

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

    # [R1/H-06] M03 y M04 retiraban VARIAS ramas a la vez, así que su muerte solo
    # acreditaba sensibilidad a ALGUNA. Separadas, cada token responde por sí mismo: el
    # revisor midió que retirar solo `anexo 1` o solo `ficha comprador` dejaba las 38
    # pruebas verdes. Y el ejemplo del Anexo 1 llevaba «PBC» dentro, así que casaba por
    # otro token aunque se retirase el suyo — el defecto estaba en la ENTRADA de prueba,
    # no solo en el mutante.
    ("M03a el `anexo 1` deja de ser PBC", SL,
     '"anexo 1", "anexo 2",',
     '"anexo 2",',
     f"{T_P4}::test_aper61_la_identidad_no_va_a_pbc"),

    ("M03b el `anexo 2` deja de ser PBC", SL,
     '"anexo 1", "anexo 2",',
     '"anexo 1",',
     f"{T_P4}::test_aper61_la_identidad_no_va_a_pbc"),

    ("M04a la hoja de visita deja de ser del comprador", SL,
     '"hoja de visita", "ficha comprador"',
     '"ficha comprador"',
     f"{T_P4}::test_aper61_la_hoja_de_visita_es_del_comprador"),

    ("M04b la ficha de comprador deja de ser del comprador", SL,
     '"hoja de visita", "ficha comprador"',
     '"hoja de visita"',
     f"{T_R1}::test_la_ficha_de_comprador_es_del_comprador"),

    # --- Pieza 1b: la frontera del token (límite IZQUIERDO, y solo izquierdo) --------
    # [R1] La política del token vive en `_patron` desde el remedio de H-05: estos dos
    # mutantes la atacan ahí, no en la comprensión de lista que la consumía antes.
    ("M05 sin límite de palabra: el token vuelve a casar DENTRO de otra", SL,
     '    return r"\\b" + re.escape(token) + cola',
     "    return re.escape(token) + cola",
     f"{T_P4}::test_un_token_no_casa_dentro_de_otra_palabra"),

    ("M06 límite TAMBIÉN a la derecha: se pierden `oferta2` y `PBC1`", SL,
     '    return r"\\b" + re.escape(token) + cola',
     '    return r"\\b" + re.escape(token) + r"\\b"',
     f"{T_P4}::test_un_token_tolera_el_sufijo_de_su_palabra"),

    # --- Pieza 2: el residuo se marca, y se marca con la confianza de la ausencia ----
    ("M07 el residuo vuelve a salir SIN tipo", SL,
     "        e.tipo_documental = CATEGORIA_PENDIENTE",
     "        e.tipo_documental = None",
     f"{T_P4}::test_el_residuo_recibe_pendiente_con_confianza_cero"),

    ("M09 `_CONF_PENDIENTE` sube por encima del umbral", SL,
     "_CONF_PENDIENTE = 0.0",
     "_CONF_PENDIENTE = 0.9",
     f"{T_P4}::test_el_residuo_recibe_pendiente_con_confianza_cero"),

    ("M10 el pendiente pierde su fecha inferida (entraría como 0000-00-00)", SL,
     "        if e.fecha_fuente is None:\n"
     "            e.fecha_doc, e.fecha_fuente = _fecha_de(case_id, e)\n"
     "        e.tipo_documental = CATEGORIA_PENDIENTE",
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

    # M18 («la worklist rellenada deja de pisar el pendiente») se RETIRA: tras el remedio de
    # H-01 su texto original es el mismo que ataca M23, así que eran el mismo mutante con dos
    # nombres. Conservarlo habría inflado el número sin añadir una propiedad.

    # --- La regla conserva su «no lo sé» ---------------------------------------------
    ("M19 `_categoria_por_nombre` decide el 08 por su cuenta", SL,
     "            return categoria\n"
     "    return None",
     "            return categoria\n"
     "    return CATEGORIA_PENDIENTE",
     f"{T_P4}::test_categoria_por_nombre_sigue_devolviendo_none_sin_pistas"),

    # --- La guarda de `preparar-residuo` no puede quedarse INERTE --------------------
    # --- [R1] Los cinco remedios de la ronda, cada uno con su mutante ------------------
    ("M22 [H-01] `clasificar_caso` vuelve a leer solo la confianza: el 08 heredado se congela", SL,
     "        if es_decision(e.tipo_documental) and (e.confianza or 0) >= UMBRAL_CONFIANZA_AUTOMOVE:",
     "        if e.tipo_documental and (e.confianza or 0) >= UMBRAL_CONFIANZA_AUTOMOVE:",
     f"{T_R1}::test_h01_un_08_con_confianza_alta_vuelve_a_ser_residuo"),

    ("M23 [H-01] `solo_residuo` vuelve a proteger un 08 de su propia corrección", SL,
     "        ya_resuelto = es_decision(e.tipo_documental) and (e.confianza or 0) >= UMBRAL_CONFIANZA_AUTOMOVE",
     "        ya_resuelto = bool(e.tipo_documental) and (e.confianza or 0) >= UMBRAL_CONFIANZA_AUTOMOVE",
     f"{T_R1}::test_h01_la_correccion_de_un_08_heredado_se_aplica"),

    ("M24 [H-02] el reintento vuelve a pisar la fecha decidida", SL,
     "        if e.fecha_fuente is None:\n"
     "            e.fecha_doc, e.fecha_fuente = _fecha_de(case_id, e)",
     "        e.fecha_doc, e.fecha_fuente = _fecha_de(case_id, e)",
     f"{T_R1}::test_h02_el_reintento_no_pisa_la_fecha_que_puso_el_letrado"),

    ("M25 [H-03] la celda 08 vuelve a ser intocable para el escritor", SL,
     '            if celdas[idx] and not (col == "Tipo" and not es_decision(celdas[idx])):',
     "            if celdas[idx]:",
     f"{T_R1}::test_h03_rellenar_worklist_pisa_una_celda_que_dice_08"),

    ("M26 [H-03] con el signo cambiado: pisa TAMBIÉN una categoría real", SL,
     '            if celdas[idx] and not (col == "Tipo" and not es_decision(celdas[idx])):',
     '            if celdas[idx] and col != "Tipo":',
     f"{T_R1}::test_h03_una_categoria_real_ya_escrita_sigue_sin_pisarse"),

    ("M27 [H-04] la parte escrita en el nombre deja de mandar", SL,
     "            if categoria in _CATEGORIAS_POR_PARTE and _RE_COMPRADOR.search(low) \\\n"
     "                    and not _RE_VENDEDOR.search(low):\n"
     '                return "03. OFERTAS"',
     "            pass",
     f"{T_R1}::test_h04_la_parte_escrita_en_el_nombre_gana"),

    ("M28 [H-04] la regla de parte se aplica a TODAS las categorías", SL,
     "            if categoria in _CATEGORIAS_POR_PARTE and _RE_COMPRADOR.search(low) \\",
     "            if True and _RE_COMPRADOR.search(low) \\",
     f"{T_R1}::test_un_requerimiento_al_comprador_sigue_siendo_reclamacion"),

    ("M29 [H-05] el token numérico vuelve a tolerar otro dígito: Anexo 10 es Anexo 1", SL,
     r'''    cola = r"(?!\d)" if token[-1].isdigit() else ""''',
     '    cola = ""',
     f"{T_R1}::test_h05_los_anexos_10_y_20_no_son_los_anexos_1_y_2"),

    ("M30 [H-05] con el signo cambiado: TODOS los tokens cierran y se pierde `oferta2`", SL,
     r'''    cola = r"(?!\d)" if token[-1].isdigit() else ""''',
     r'''    cola = r"\b"''',
     f"{T_R1}::test_h05_los_verdaderos_positivos_con_sufijo_se_conservan"),

    ("M31 el aviso de pendientes del CLI desaparece", CLI,
     '    if r["n_pendientes"]:',
     "    if False:",
     f"{T_R1}::test_el_cli_organizar_dice_cuantos_pendientes_quedan_y_donde_corregirlos"),

    ("M21 la guarda del CLI vuelve a preguntar por «sin tipo» (queda inerte)", CLI,
     "                    if not sala_lectura.es_decision(e.tipo_documental)]",
     "                    if not e.tipo_documental]",
     f"{T_P4}::test_la_cli_no_declara_clasificado_un_catalogo_lleno_de_pendientes"),

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
    # El aviso de pendientes del CLI ESTABA aquí, declarado con el motivo «solo cambia TEXTO,
    # no una decisión». El revisor lo refutó con razón —al retirar la parada, ese aviso es el
    # ÚNICO canal por el que el letrado se entera de que queda trabajo; antes se lo decía el
    # propio bloqueo— y hoy tiene test y mutante (M31). Lo que queda declarado es otra cosa:
    ("`_CONF_PENDIENTE = 0.0` ya no tiene mutante propio (era M08)",
     "Y la razón es un resultado de la ronda, no una excusa: **el remedio de H-01 lo volvió "
     "redundante.** Mientras las guardas preguntaban solo por la confianza, bajarla era lo "
     "ÚNICO que impedía congelar un pendiente; desde que preguntan `es_decision`, un `08` "
     "vuelve al residuo aunque su confianza sea 1.0 — que es exactamente el estado heredado "
     "que describía H-01. Mutar la asignación a `1.0` deja verde el test de la no-congelación "
     "porque esa propiedad ya no depende de ella. La constante se conserva por coherencia "
     "semántica (un `08` no es una decisión y su confianza no debe decir lo contrario) y su "
     "VALOR sigue fijado por M09. Se declara en vez de reapuntar M08 al mismo test que M09: "
     "serían dos mutantes de una sola propiedad, que es lo que la R1 criticó en su punto 7."),
]


def _escribir(path: Path, texto: str, *, intentos: int = 5) -> None:
    """Escribe `path`, reintentando el fallo TRANSITORIO de Windows.

    `OSError: [Errno 22] Invalid argument` y `PermissionError` aparecen cuando otro proceso
    —un indexador, un antivirus, el pytest que acaba de importar el módulo— aún tiene un
    handle abierto sobre el fichero que se acaba de reescribir. Medido: abortó el arnés entre
    dos mutantes. Un arnés que se cae a mitad **deja el árbol mutado**, así que esta función
    y el `finally` de `main` son las dos mitades de la misma garantía.
    """
    ultimo: OSError | None = None
    for i in range(intentos):
        try:
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(texto)
            return
        except OSError as exc:            # incluye PermissionError
            ultimo = exc
            time.sleep(0.2 * (i + 1))
    raise RuntimeError(
        f"no se pudo restaurar {path} tras {intentos} intentos: {ultimo!r}. "
        "COMPRUEBA EL ARBOL antes de seguir: puede haber quedado mutado.") from ultimo


#: Código de salida de pytest para «error de uso»: aquí significa, casi siempre, que el nodo
#: de test **no existe** — un mutante apuntado a un fichero o a un nombre equivocado.
_PYTEST_USAGE_ERROR = 4


def _corre(test: str) -> tuple[int, str]:
    """Corre un test en subproceso y devuelve `(rc, salida)`.

    **La salida se devuelve porque el código solo no distingue los dos fallos que importan.**
    Un mutante apuntado a un test que no existe da `rc=4`, y el arnés lo leía como «el test YA
    estaba rojo sin mutar» — un diagnóstico equivocado que manda a buscar un defecto donde no
    lo hay. Pasó con `M04b`, apuntado a `T_P4` cuando su test vive en `T_R1`: se declaró roto
    el arnés por la razón falsa, y la verdadera —una referencia mal escrita— solo apareció al
    leer el mensaje. `main` las separa.

    `PYTHONDONTWRITEBYTECODE` y `-p no:cacheprovider` son higiene, no el remedio de ese
    defecto: el arnés reescribe `core/sala_lectura.py` entre corridas y no conviene que dos
    procesos se disputen un `.pyc`.
    """
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:randomly",
         "-p", "no:cacheprovider", test],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace", env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    fallos: list[str] = []
    for nombre, fichero, viejo, nuevo, test in MUTANTES:
        objetivo = RAIZ / fichero
        s = io.open(objetivo, encoding="utf-8").read()
        if viejo not in s:
            print(f"[ARNES ROTO] {nombre}: el texto original ya no esta en {fichero}")
            fallos.append(nombre)
            continue
        rc_previo, salida = _corre(test)
        if rc_previo == _PYTEST_USAGE_ERROR:
            # **«No existe» no es «está rojo».** Son dos defectos distintos del arnés y el
            # remedio de cada uno es otro: aquí se corrige la REFERENCIA del mutante; allí,
            # el test o el código. Decirlos igual manda a buscar donde no está.
            print(f"[ARNES ROTO] {nombre}: el test al que apunta NO EXISTE → {test}")
            fallos.append(nombre)
            continue
        if rc_previo != 0:
            print(f"[ARNES ROTO] {nombre}: {test.split('::')[-1]} YA estaba rojo sin mutar")
            fallos.append(nombre)
            continue
        # **La restauración se arma ANTES de mutar, no después.** El `try` empezaba en la
        # línea siguiente a la escritura, así que un fallo *al mutar* saltaba fuera del bucle
        # con el fichero ya reescrito y sin restaurar: el árbol se quedaba mutado y el
        # siguiente que corriera la suite vería rojos inexplicables en producción. Pasó:
        # `OSError: [Errno 22]` escribiendo `core/sala_lectura.py` —transitorio, un handle
        # ajeno en Windows— abortó el arnés a mitad. Salió bien de milagro; la garantía no
        # puede depender de eso.
        try:
            _escribir(objetivo, s.replace(viejo, nuevo, 1))
            rc, _ = _corre(test)
        finally:
            _escribir(objetivo, s)
        if rc == _PYTEST_USAGE_ERROR:
            # Mutar no puede hacer desaparecer un test que existía hace un segundo: si pasa,
            # la mutación rompió la COLECCIÓN del fichero (sintaxis, import), y entonces el
            # rojo no prueba la propiedad — prueba que Python no puede leer el módulo.
            print(f"[ARNES ROTO] {nombre}: mutado, el test dejó de COLECCIONAR (rc=4): la "
                  "mutación rompe el módulo, no la propiedad")
            fallos.append(nombre)
        elif rc == 0:
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
