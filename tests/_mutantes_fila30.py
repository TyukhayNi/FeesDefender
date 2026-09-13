"""Arnés de mutación de la fila #30 (`[APER-70]`) — el botón de la sala de lectura.

Mismo contrato que `tests/_mutantes_mejoras_251.py` y `_mutantes_mejoras_214.py`, y está
aquí por la misma razón que ellos, que además es una lección **del mismo día**: en la R1 del
2026-09-13 un revisor no pudo verificar una cifra de mutantes porque las definiciones vivían
fuera del objeto revisado, y la declaró SIN VERIFICAR. **Una afirmación que nadie puede
comprobar no es un dato.**

Y este fichero nació justo de repetir ese error. Los 17 mutantes de la fila #30 se corrieron
desde un script del scratchpad, fuera del repo: el «17 de 17» del PR
[#364](https://github.com/TyukhayNi/FeesDefender/pull/364) era irreproducible en cuanto se
borrara ese directorio.

## Lo que comprueba, y por qué la segunda mitad es la que importa

Dos cosas por mutante:

1. que el mutante **mate al test al que se le apunta**, y
2. que ese test estuviera **verde antes de mutar**.

El script del scratchpad solo miraba si la suite entera seguía verde, y eso **no distingue
un mutante que muere por su test de uno que muere por otro cualquiera**. No es una
distinción teórica: es exactamente el hallazgo H-03 de la R1. `M7` —el que comprueba que el
lector no crea la carpeta que no encuentra— figuraba como «muerto», pero lo mataban otros
tests; el sello de `test_leer_el_estado_no_toca_un_solo_byte`, que es la guarda que M7 venía
a fijar, **daba verde**, porque sellaba solo ficheros y un `mkdir` no crea ninguno. Una
guarda que nunca se ha visto morder no acredita nada.

No es un test de pytest y no corre en la suite (el nombre empieza por `_`): muta ficheros del
árbol. Se ejecuta a mano, **con el árbol limpio**:

    python -m tests._mutantes_fila30
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

GUARD = "tests/test_guard_ui_sin_deprecados.py"
ESTADO = "core/sala_lectura_estado.py"
T_EST = "tests/test_sala_lectura_estado.py"
VA = "core/verificar_apertura.py"
T_VA = "tests/test_verificar_apertura.py"

#: (nombre, fichero a mutar, texto original, texto mutado, test que DEBE ponerse rojo).
MUTANTES: list[tuple[str, str, str, str, str]] = [
    # --- El guard: la UI no importa módulos deprecados ------------------------------
    ("M01 el detector vuelve a buscar la MENCIÓN del marcador", GUARD,
     "        return linea.strip() if linea.lstrip().startswith(MARCADOR) else None",
     "        return linea.strip() if MARCADOR in (doc or '') else None",
     f"{GUARD}::test_citar_el_marcador_no_es_declararlo"),

    ("M02 el marcador ya no tiene que ABRIR la línea", GUARD,
     "linea.lstrip().startswith(MARCADOR)",
     "(MARCADOR in linea)",
     f"{GUARD}::test_mencionar_el_marcador_en_la_primera_linea_tampoco_es_declararlo"),

    ("M03 solo se miran los imports del nivel superior", GUARD,
     "    for nodo in ast.walk(arbol):",
     "    for nodo in arbol.body:",
     f"{GUARD}::test_el_import_dentro_de_una_funcion_tambien_cuenta"),

    ("M04 `from core import x` deja de contarse", GUARD,
     "        elif isinstance(nodo, ast.ImportFrom):",
     "        elif isinstance(nodo, ast.ImportFrom) and False:",
     f"{GUARD}::test_control_positivo_un_modulo_deprecado_se_senala"),

    ("M05 [R1/H-06] el fichero gana al paquete, al revés que Python", GUARD,
     '    paquete = raiz_repo.joinpath(*partes, "__init__.py")\n'
     "    if paquete.is_file():\n"
     "        return paquete\n"
     '    modulo = raiz_repo.joinpath(*partes).with_suffix(".py")\n'
     "    return modulo if modulo.is_file() else None",
     '    modulo = raiz_repo.joinpath(*partes).with_suffix(".py")\n'
     "    if modulo.is_file():\n"
     "        return modulo\n"
     '    paquete = raiz_repo.joinpath(*partes, "__init__.py")\n'
     "    return paquete if paquete.is_file() else None",
     f"{GUARD}::test_con_paquete_y_fichero_homonimos_gana_el_paquete"),

    # --- El lector: lo que cuenta y lo que no --------------------------------------
    ("M06 los artefactos se cuentan como documentos", ESTADO,
     "            if raiz and nombre.casefold() in _ARTEFACTOS_EN_LA_SALA:\n"
     "                continue\n",
     "",
     f"{T_EST}::test_los_artefactos_no_cuentan_como_documentos"),

    ("M07 la exclusión pasa a ser por NOMBRE y no por posición", ESTADO,
     "            if raiz and nombre.casefold() in _ARTEFACTOS_EN_LA_SALA:",
     "            if nombre.casefold() in _ARTEFACTOS_EN_LA_SALA:",
     f"{T_EST}::test_un_fichero_con_nombre_de_artefacto_dentro_de_un_compuesto_si_cuenta"),

    # H-05 tiene DOS mitades y hacen falta los dos mutantes, porque el `casefold` está en
    # dos sitios y cada uno protege una grafía. El set ya viene normalizado, así que:
    #   · quitar el `casefold` del NOMBRE rompe `INDICE.md`  -> lo mata el test de MAYÚSCULAS
    #   · quitar el `casefold` del SET    rompe `indice.md`  -> lo mata el test de minúsculas
    # La primera versión de este arnés apuntaba el de arriba al test de minúsculas, o sea al
    # lado que ese mutante NO toca, y **sobrevivía**. Es el mismo defecto que H-03 en otro
    # sitio: un mutante que muere (o no) por un test que no es el suyo no acredita la guarda.
    ("M08a [R1/H-05] sin `casefold` en el NOMBRE: `INDICE.md` cuenta como documento",
     ESTADO,
     "            if raiz and nombre.casefold() in _ARTEFACTOS_EN_LA_SALA:",
     "            if raiz and nombre in _ARTEFACTOS_EN_LA_SALA:",
     f"{T_EST}::test_los_artefactos_no_cuentan_como_documentos"),

    ("M08b [R1/H-05] sin `casefold` en el SET: `indice.md` cuenta como documento", ESTADO,
     "_ARTEFACTOS_EN_LA_SALA = frozenset(n.casefold() for n in va._ARTEFACTOS_SALA)",
     "_ARTEFACTOS_EN_LA_SALA = frozenset(va._ARTEFACTOS_SALA)",
     f"{T_EST}::test_los_artefactos_en_minusculas_tampoco_cuentan_como_documentos"),

    ("M09 [R1/H-01b] el catálogo de la skill infla el recuento en uno", ESTADO,
     "_ARTEFACTOS_EN_LA_SALA = frozenset(n.casefold() for n in va._ARTEFACTOS_SALA)",
     "_ARTEFACTOS_EN_LA_SALA = frozenset(n.casefold() for n in va._ARTEFACTOS_SALA\n"
     "                                   if n != va._CATALOGO)",
     f"{T_EST}::test_el_catalogo_de_la_skill_no_se_cuenta_como_documento"),

    ("M10 los miembros de un documento compuesto dejan de contarse", ESTADO,
     "    for dirpath, _dirnames, nombres in os.walk(sala, onerror=_anota):",
     "    for dirpath, _dirnames, nombres in [(str(sala), [], "
     "[p.name for p in sala.iterdir() if p.is_file()])]:",
     f"{T_EST}::test_los_miembros_de_un_documento_compuesto_cuentan"),

    ("M11 [R1/H-02] una sala ilegible vuelve a decir «0 documentos»", ESTADO,
     "    for dirpath, _dirnames, nombres in os.walk(sala, onerror=_anota):",
     "    for dirpath, _dirnames, nombres in os.walk(sala):",
     f"{T_EST}::test_si_no_se_puede_enumerar_el_recuento_es_None_y_no_cero"),

    # --- El lector: lo que NO hace -------------------------------------------------
    ("M12 el lector crea la carpeta que no encuentra", ESTADO,
     "    sala = _sala(case_dir)",
     "    (case_dir / va._PROCESADO / va._SALA_LECTURA).mkdir(parents=True, "
     "exist_ok=True)\n    sala = _sala(case_dir)",
     f"{T_EST}::test_leer_el_estado_no_toca_un_solo_byte"),

    ("M13 [R1/H-03] el sello vuelve a ser ciego a los directorios", T_EST,
     "        if p.is_dir():\n"
     '            out.append((str(p.relative_to(raiz)) + "/", "<dir>"))\n'
     "        elif p.is_file():",
     "        if p.is_file():",
     f"{T_EST}::test_control_positivo_el_sello_ve_un_directorio_nuevo"),

    ("M14 una sala inexistente se declara montada", ESTADO,
     "        montada=sala is not None,",
     "        montada=True,",
     f"{T_EST}::test_sin_carpeta_de_sala_no_esta_montada"),

    # --- La solicitud: identifica sin exponer ---------------------------------------
    ("M15 la solicitud filtra el nombre de la carpeta (dirección del inmueble)", ESTADO,
     '    w = w_code_de_carpeta(case_dir.name) or "(carpeta sin W-code)"',
     "    w = w_code_de_carpeta(case_dir.name) or case_dir.name",
     f"{T_EST}::test_sin_w_code_la_solicitud_lo_dice_en_vez_de_filtrar_la_carpeta"),

    # --- `c4`: las dos ubicaciones del catálogo --------------------------------------
    ("M16 [R1/H-01] la sala montada por la SKILL vuelve a salir incompleta", VA,
     "    return (sala / _CATALOGO, proc / _CATALOGO)",
     "    return (proc / _CATALOGO,)",
     f"{T_VA}::test_c4_acepta_el_catalogo_DENTRO_de_la_sala_que_es_donde_lo_pone_la_skill"),

    ("M17 [R1/H-01] con el signo cambiado: el layout del MOTOR deja de valer", VA,
     "    return (sala / _CATALOGO, proc / _CATALOGO)",
     "    return (sala / _CATALOGO,)",
     f"{T_VA}::test_c4_sigue_aceptando_el_catalogo_en_01_procesado"),
]

#: (nombre, motivo). Mutantes que se conservan sin exigirles muerte, con su razón escrita.
SUPERVIVIENTES_DECLARADOS: list[tuple[str, str]] = []


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
