"""Arnés de mutación de `crm_ficha` (plan rev. 2, Task 9) — SOBRE UNA COPIA del árbol.

    python -m tests._mutantes_crm_ficha            # todos
    python -m tests._mutantes_crm_ficha M19 M20    # solo los que empiezan así
    python -m tests._mutantes_crm_ficha --anclas   # solo comprueba que cada ancla está una vez

**Por qué sobre una copia.** La §9 del plan lo justificaba diciendo que mutar el árbol vivo es
«justo lo que prohíbe» `tests/test_guard_aislamiento_paralelo.py`, y eso no es exacto: el guard
exime a los arneses porque pytest no los colecciona. La razón es otra, y basta: un arnés que se
cae a mitad deja el árbol vivo MUTADO (lo midió P4, y por eso `_mutantes_p6.py` arma la
restauración antes de mutar). Con una copia, esa posibilidad no existe por construcción, y al
cerrar se comprueba que los ficheros mutados del árbol vivo conservan su `sha256`.

**Qué cuenta como muerte, y es más estricto que en P6.** Por mutante:

1. el test objetivo pasa en la copia SIN mutar (base verde);
2. cada ancla aparece EXACTAMENTE una vez, y el fichero mutado compila;
3. mutado, el test se EJECUTA (`--junitxml`) y falla por su ASERTO: un `<failure>` de tipo
   `AssertionError` o `Failed` (el de `pytest.raises`), o por una de las guardas de arnés que
   los propios tests usan para detectar (`NoDebiaLlamarse`, `LecturaNoDeclarada`). Un `<error>`
   (colección, setup) o cualquier otro tipo —un `NameError`, un `ValueError` de un programa que
   ya no funciona— NO cuenta: morir no es ser detectado.

El detalle de cada mutante queda en un JSON junto a la copia, y la salida dice su ruta.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_COPIAR_DIRS = ("core", "scripts", "tests")
_COPIAR_FICHEROS = ("pyproject.toml",)
_IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")

FICHA = "core/crm_ficha.py"
CLI = "scripts/crm_ficha.py"
REL = "core/sudespacho_relations.py"
FIRMAS = "scripts/crm_colaboradores_firmas.py"
T_LECTOR = "tests/test_crm_ficha_lector.py"
T_AUD = "tests/test_crm_ficha_auditoria.py"
T_CLI = "tests/test_crm_ficha_cli.py"
T_INT = "tests/test_crm_ficha_integracion.py"
T_ID = "tests/test_crm_ficha_id_crm.py"
T_FIRMAS = "tests/test_crm_colaboradores_firmas_cli.py"

_FASE_PREVIA = "    previas = _fase_previa(ficha)\n    if previas:\n"
_LINK_EV = "        link_ev_mmc(exp_id, cliente_propio_id=cliente_propio_id)\n"
_LECTURA_FINAL = "    for elemento, id_, declarado, _creado in resueltas:\n"
_IDENTIDAD = ('    if not (_nif(d.get("nif")) or _hay(d.get("email")) '
              'or _id_crm(d.get("id_crm"))):\n')
T_N = "tests/test_crm_ficha_n_contrarios.py"

#: (nombre, fichero, [(ancla, sustitución), …], test que tiene que ponerse rojo).
MUTANTES: list[tuple[str, str, list[tuple[str, str]], str]] = [
    # --- A.1: el lector sin pérdida y sus dos consumidores --------------------------------------
    ("M01 el lector acepta claves repetidas", FICHA,
     [("        if clave in vistas:\n", "        if False:\n")],
     f"{T_LECTOR}::test_R1H01_una_clave_repetida_se_rechaza_con_su_linea"),

    # Sin esta comprobación el merge sigue sin pasar —el constructor no sabe construir su
    # etiqueta y levanta—, pero sale como «inválido», sin su línea ni su causa: lo que el mutante
    # acredita es el DIAGNÓSTICO, que es lo que el test pide.
    ("M02 el lector deja de reconocer el merge sin alias", FICHA,
     [("        if clave_node.tag == _ETIQUETA_MERGE:\n", "        if False:\n")],
     f"{T_LECTOR}::test_R2_el_merge_SIN_alias_se_rechaza"),

    ("M03 cargar_ficha_yaml vuelve a yaml.safe_load (consumidor 1)", FICHA,
     [("    data = leer_yaml_ficha(path)\n",
       '    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}\n')],
     f"{T_LECTOR}::test_cargar_ficha_yaml_lee_con_el_lector_sin_perdida"),

    ("M04 apply vuelve a yaml.safe_load (consumidor 2)", FIRMAS,
     [("        datos = leer_yaml_ficha(ficha_path)\n",
       '        datos = yaml.safe_load(ficha_path.read_text(encoding="utf-8")) or {}\n')],
     f"{T_FIRMAS}::TestApplyNoReescribeUnaFichaQuePerderiaDatos::"
     "test_una_clave_repetida_falla_sin_tocar_el_fichero"),

    # --- A.2-A.4: claves, tipos, identidad y construcción ---------------------------------------
    ("M05 un escalar vuelve a aceptar mappings y listas", FICHA,
     [('    return [f"{ruta}: tiene que ser un texto o null, y es {_forma(valor)}"]\n',
       "    return []\n")],
     f"{T_LECTOR}::test_R1H02_un_mapping_o_una_lista_en_CUALQUIER_escalar_se_rechaza"),

    # Re-apuntado en la R3 (H-02): el NIF cuenta como identidad por su forma canónica.
    ("M06 se quita la exigencia de identidad", FICHA,
     [(_IDENTIDAD, "    if False:\n")],
     f"{T_LECTOR}::test_R1H04_una_parte_sin_identidad_estable_se_rechaza"),

    ("M07 dos asignaciones del constructor cruzadas", FICHA,
     [("    return NuevoClienteContrario(**{c: _valor(d.get(c)) for c in CLAVES_CONTRARIO\n",
       '    return NuevoClienteContrario(**{c: _valor(d.get({"apellido1": "apellido2", '
       '"apellido2": "apellido1"}.get(c, c))) for c in CLAVES_CONTRARIO\n')],
     f"{T_LECTOR}::test_cada_clave_llega_a_su_atributo"),

    # --- B.1-B.2: las auditorías puras ----------------------------------------------------------
    ("M08 se quita el cálculo de sobrantes", FICHA,
     [('            sobran += [f"{bloque} id={id_}"] * max(0, v - p)\n', "            pass\n")],
     f"{T_AUD}::test_R288_el_653_dos_colaboradores_de_mas_son_sobrantes"),

    # Ejecutable: `Counter(set(...))` pierde la multiplicidad sin cambiar de tipo, así que muere
    # por el aserto y no por un `TypeError` (R2, acta §5).
    ("M09 la multiplicidad se cambia por un conjunto", FICHA,
     [("        pedidos = Counter(str(i) for i in esperado.get(bloque, ()))\n",
       "        pedidos = Counter(set(str(i) for i in esperado.get(bloque, ())))\n")],
     f"{T_AUD}::test_multiplicidad_en_los_dos_sentidos_y_id_int_frente_a_str"),

    ("M10 auditar_datos devuelve siempre []", FICHA,
     [("    fuera: list[Discrepancia] = []\n", "    return []\n")],
     f"{T_AUD}::test_R1H03_la_ficha_de_w030a13_con_el_apellido_vacio_no_pasa"),

    ("M11 la provincia se normaliza solo de un lado", FICHA,
     [("    return _n_texto(provincia_canonica(str(v)) or v)\n",
       "    return provincia_canonica(str(v)) or v\n")],
     f"{T_AUD}::test_R2H03_la_provincia_se_compara_igual_en_los_dos_lados"),

    # --- B.2-B.4 en el CLI ----------------------------------------------------------------------
    ("M12 la lectura final se salta los colaboradores", CLI,
     [(_LECTURA_FINAL, "    for elemento, id_, declarado, _creado in [r for r in resueltas "
                       'if r[0] != "colaboradores"]:\n')],
     f"{T_CLI}::TestLosDatosDeLaFicha::test_un_colaborador_con_un_dato_distinto_da_DATO"),

    ("M13 la lectura final se salta las partes creadas", CLI,
     [(_LECTURA_FINAL, "    for elemento, id_, declarado, _creado in [r for r in resueltas "
                       "if not r[3]]:\n")],
     f"{T_INT}::test_una_parte_CREADA_a_la_que_el_CRM_no_guardo_un_dato_da_DATO"),

    ("M14 la parcial emite sobrantes", CLI,
     [("            _vinculos(parcial, parcial=True)\n", "            _vinculos(parcial)\n")],
     f"{T_CLI}::TestLaParcial::test_la_parcial_no_emite_sobrantes"),

    ("M15 un SIN VERIFICAR tapa un fallo conocido", CLI,
     [("    if faltan or sobran or datos_mal:\n",
       "    if (faltan or sobran or datos_mal) and not sin_verificar:\n")],
     f"{T_CLI}::TestLosDatosDeLaFicha::test_un_fallo_conocido_gana_a_un_SIN_VERIFICAR"),

    # --- A.4: id_crm en el core y la fase previa ------------------------------------------------
    ("M16 el core ignora id_crm (contrario)", REL,
     [('    if datos.id_crm:\n        return datos.id_crm\n    r = resolver_parte("clientes_contrarios"',
       '    r = resolver_parte("clientes_contrarios"')],
     f"{T_ID}::test_con_id_crm_el_contrario_no_se_busca_ni_se_crea_y_se_completa"),

    ("M17 el core ignora id_crm (colaborador)", REL,
     [("    if datos.id_crm:\n        return datos.id_crm\n    return _resolver_colaborador(",
       "    return _resolver_colaborador(")],
     f"{T_ID}::test_con_id_crm_el_colaborador_tampoco"),

    ("M18 se quita la fase previa", CLI,
     [(_FASE_PREVIA, "    previas = []\n    if previas:\n")],
     f"{T_INT}::test_R2H01_dato_distinto_preexistente_cero_writers_con_el_completado_real"),

    ("M19 la fase previa va detrás de link_ev_mmc", CLI,
     [(_FASE_PREVIA, "    previas = []\n    if previas:\n"),
      (_LINK_EV, _LINK_EV + "        if _fase_previa(ficha):\n"
                            "            raise typer.Exit(code=1)\n")],
     f"{T_CLI}::TestLaFasePrevia::"
     "test_R2H01_un_dato_distinto_en_una_ficha_existente_no_deja_escribir_NADA"),

    ("M20 la fase previa corre antes del corte de --dry-run", CLI,
     [(_FASE_PREVIA, "    previas = []\n    if previas:\n"),
      ("    if dry_run:\n", "    _fase_previa(ficha)\n    if dry_run:\n")],
     f"{T_CLI}::TestLaFasePrevia::test_R2H08_dry_run_con_id_crm_no_lee_el_CRM"),

    # --- R3 (plan §10): los cuatro hallazgos, la observación y los huecos que señaló en §5 -----
    # H-01. Las dos anclas se distinguen por la sangría y por el salto de línea delante: la del
    # colaborador (28 espacios) está contenida en la del contrario (33) si no se ancla al `\n`.
    ("M21 el NIF del contrario viaja como se escribió (H-01)", FICHA,
     [('                                 nif=_nif(d.get("nif")), id_crm=',
       '                                 nif=_valor(d.get("nif")), id_crm=')],
     f"{T_INT}::test_R3H01_un_nif_con_separadores_converge_con_el_filtro_del_CRM[contrario]"),

    ("M22 el NIF del colaborador viaja como se escribió (H-01)", FICHA,
     [('\n                            nif=_nif(d.get("nif")), id_crm=',
       '\n                            nif=_valor(d.get("nif")), id_crm=')],
     f"{T_INT}::test_R3H01_colaborador_por_id_con_un_nif_ajeno_deja_la_resolucion_por_nif_"
     "ambigua"),

    ("M23 un NIF que se vacía sin separadores vuelve a pasar (H-02)", FICHA,
     [("    if _hay(v) and not _nif(v):\n", "    if False:\n")],
     f"{T_LECTOR}::test_R3H02_un_nif_que_se_queda_vacio_se_rechaza_aunque_haya_otra_identidad"
     "[-contrario-contrario]"),

    ("M24 cualquier texto en `nif` vuelve a contar como identidad (H-02)", FICHA,
     [(_IDENTIDAD, _IDENTIDAD.replace('_nif(d.get("nif"))', '_hay(d.get("nif"))'))],
     f"{T_LECTOR}::test_R3H02_un_nif_que_se_queda_vacio_no_cuenta_como_identidad"),

    ("M25 lo de debajo de un merge deja de mirarse (H-03)", FICHA,
     [("            loader.construct_object(valor_node, deep=deep)     # lo de debajo también "
       "(R3/H-03)\n", "            pass\n")],
     f"{T_LECTOR}::test_R3H03_lo_de_debajo_de_un_merge_tambien_se_informa"),

    ("M26 una clave escalar que no es texto vuelve a pasar (H-03)", FICHA,
     [("        if not isinstance(clave, str):\n", "        if False:\n")],
     f"{T_LECTOR}::test_R3H03_una_clave_escalar_que_no_es_texto_se_rechaza_con_su_linea[numero]"),

    ("M27 el mismo NIF o id_crm en dos partes deja de ser la misma parte (obs.)", FICHA,
     [("            if misma:\n", "            if False:\n")],
     f"{T_LECTOR}::test_R3_dos_partes_con_la_misma_identidad_se_rechazan[nif]"),

    ("M28 un email compartido deja de exigir el NIF de las dos (obs.)", FICHA,
     [('            if correo and correo == _email(e.get("email")) and not (ambas_id or '
       'ambas_nif):\n', "            if False:\n")],
     f"{T_LECTOR}::test_R3_un_email_compartido_sin_el_nif_de_las_dos_se_rechaza[solo-email]"),

    ("M29 la fase previa deja pasar dos partes que resuelven a la misma ficha (obs.)", CLI,
     [("            if existente in vistas:\n", "            if False:\n")],
     f"{T_INT}::test_R3_dos_partes_que_resuelven_a_la_misma_ficha_cero_writers[contrario]"),

    # §5 del informe: reglas con test y sin mutante que acreditara su sensibilidad.
    ("M30 una clave desconocida de una parte deja de rechazarse", FICHA,
     [('    p = [f"{ruta}.{k}: clave desconocida{_sugerencia(k, validas)}" for k in d if k not in '
       'validas]\n', "    p = []\n")],
     f"{T_LECTOR}::test_varios_problemas_salen_todos"),

    ("M31 un id_crm que no es un número vuelve a pasar", FICHA,
     [('    if d.get("id_crm") is not None and _id_crm(d["id_crm"]) is None:     # null = no hay '
       'dato\n', "    if False:\n")],
     f"{T_LECTOR}::test_id_crm_que_no_es_el_numero_de_una_ficha_se_rechaza['12a']"),

    ("M32 un teléfono que se vacía al normalizar vuelve a pasar", FICHA,
     [("        if _hay(v) and not normalize_es_phone(v.strip()):\n", "        if False:\n")],
     f"{T_LECTOR}::test_R2H02_un_telefono_que_se_queda_vacio_se_rechaza"
     "[movil-'+34'-contrario-contrario]"),

    ("M33 una provincia que el Select no reconoce vuelve a pasar", FICHA,
     [('    if "provincia" in validas and _hay(v) and provincia_canonica(v) is None:\n',
       "    if False:\n")],
     f"{T_LECTOR}::test_R2H02_una_provincia_que_no_existe_se_rechaza_al_validar"),

    # H-04: la versión EJECUTABLE del M11 de P6. Quitar solo el mensaje dejaba el elemento
    # inválido vivo y el programa moría en `_contrario_de` con `AttributeError`; filtrarlo es la
    # pérdida silenciosa que el test existe para detectar, y muere por `DID NOT RAISE`.
    ("M34 un elemento inválido de la lista se filtra en silencio (H-04)", FICHA,
     [("    elif isinstance(contr, list):\n        for i, e in enumerate(contr):\n",
       "    elif isinstance(contr, list):\n"
       "        contr[:] = [e for e in contr if isinstance(e, dict)]\n"
       "        for i, e in enumerate(contr):\n")],
     f"{T_N}::test_un_elemento_invalido_aborta_con_su_indice"),
]

#: Tipos con los que un rojo SÍ es la detección de la propiedad.
_DETECCION = frozenset({"AssertionError", "Failed", "NoDebiaLlamarse", "LecturaNoDeclarada"})


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copia() -> Path:
    destino = Path(tempfile.mkdtemp(prefix="mutantes_crm_ficha_"))
    for d in _COPIAR_DIRS:
        shutil.copytree(RAIZ / d, destino / d, ignore=_IGNORAR)
    for f in _COPIAR_FICHEROS:
        if (RAIZ / f).is_file():
            shutil.copy2(RAIZ / f, destino / f)
    return destino


def _tipo(mensaje: str) -> str:
    """`paquete.modulo.Clase: texto` → `Clase`.

    Una aserción que pytest reescribe y que no trae mensaje propio llega como `assert …`, sin el
    nombre de la clase delante: también es un `AssertionError` (medido con el M19 de este arnés,
    que se dio por «muerto por otra cosa» con el aserto a la vista)."""
    m = (mensaje or "").strip()
    if m == "assert" or m.startswith("assert "):
        return "AssertionError"
    return m.split(":", 1)[0].strip().rsplit(".", 1)[-1]


def _corre(copia: Path, test: str, junit: Path) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line", "-p", "no:randomly",
         "-p", "no:cacheprovider", f"--junitxml={junit}", test],
        cwd=copia, capture_output=True, encoding="utf-8", errors="replace", env=env)
    casos = fallos = errores = 0
    tipos: list[str] = []
    if junit.is_file():
        for caso in ET.parse(junit).getroot().iter("testcase"):
            casos += 1
            for f in caso.findall("failure"):
                fallos += 1
                tipos.append(_tipo(f.get("message", "")))
            errores += len(caso.findall("error"))
    return {"rc": r.returncode, "casos": casos, "fallos": fallos, "errores": errores,
            "tipos": sorted(set(tipos)), "salida": (r.stdout or "")[-1500:]}


def _anclas(raiz: Path) -> list[str]:
    malas = []
    for nombre, fichero, cambios, _ in MUTANTES:
        texto = (raiz / fichero).read_text(encoding="utf-8").replace("\r\n", "\n")
        for viejo, _nuevo in cambios:
            n = texto.count(viejo)
            if n != 1:
                malas.append(f"{nombre}: el ancla aparece {n} veces en {fichero}")
    return malas


def main(argv: list[str]) -> int:
    malas = _anclas(RAIZ)
    if malas:
        print("\n".join(f"[ARNES ROTO] {m}" for m in malas))
        return 1
    if "--anclas" in argv:
        print(f"{len(MUTANTES)} mutantes: todas las anclas aparecen exactamente una vez.")
        return 0

    prefijos = [a for a in argv if not a.startswith("-")]
    elegidos = [m for m in MUTANTES if not prefijos or m[0].startswith(tuple(prefijos))]
    vivos = {f: _sha(RAIZ / f) for f in {m[1] for m in elegidos}}
    copia = _copia()
    informe: list[dict] = []
    fallos: list[str] = []
    try:
        for i, (nombre, fichero, cambios, test) in enumerate(elegidos, 1):
            objetivo = copia / fichero
            original = objetivo.read_bytes()
            base = _corre(copia, test, copia / f"_base_{i:02d}.xml")
            fila = {"mutante": nombre, "test": test, "base": base}
            if base["rc"] != 0 or base["casos"] == 0 or base["fallos"] or base["errores"]:
                fila["veredicto"] = "BASE NO VERDE"
                print(f"[ARNES ROTO] {nombre}: el test no pasa sin mutar ({base['rc']}, "
                      f"{base['casos']} casos)")
                fallos.append(nombre)
                informe.append(fila)
                continue
            texto = original.decode("utf-8")
            eol = "\r\n" if "\r\n" in texto else "\n"
            mutado = texto.replace("\r\n", "\n")
            for viejo, nuevo in cambios:
                mutado = mutado.replace(viejo, nuevo, 1)
            try:
                compile(mutado, fichero, "exec")
            except SyntaxError as exc:
                fila["veredicto"] = f"NO COMPILA (línea {exc.lineno}: {exc.msg})"
                print(f"[ARNES ROTO] {nombre}: la mutación no compila (línea {exc.lineno})")
                fallos.append(nombre)
                informe.append(fila)
                continue
            try:
                objetivo.write_bytes(mutado.replace("\n", eol).encode("utf-8"))
                mut = _corre(copia, test, copia / f"_mut_{i:02d}.xml")
            finally:
                objetivo.write_bytes(original)
            fila["mutado"] = mut
            detectado = [t for t in mut["tipos"] if t in _DETECCION]
            if mut["casos"] == 0:
                fila["veredicto"] = "NO SE EJECUTÓ"
            elif mut["errores"]:
                fila["veredicto"] = "ERROR DE COLECCIÓN O SETUP"
            elif mut["fallos"] == 0:
                fila["veredicto"] = "SUPERVIVIENTE"
            elif not detectado:
                fila["veredicto"] = f"MURIÓ POR OTRA COSA: {mut['tipos']}"
            else:
                fila["veredicto"] = "muerto"
            informe.append(fila)
            if fila["veredicto"] == "muerto":
                print(f"[muerto] {nombre}  ({', '.join(detectado)})")
            else:
                print(f"[{fila['veredicto']}] {nombre}  <- {test.split('::')[-1]}")
                fallos.append(nombre)
    finally:
        (copia / "_informe_mutantes.json").write_text(
            json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
        intactos = all(_sha(RAIZ / f) == h for f, h in vivos.items())

    print()
    print(f"{len(elegidos)} mutantes, {len(elegidos) - len(fallos)} muertos por su aserto.")
    print("SUPERVIVIENTES/ROTOS:", ", ".join(fallos) if fallos else "ninguno")
    print(f"Árbol vivo intacto (sha256 de los ficheros mutados): {'sí' if intactos else 'NO'}")
    print(f"Detalle: {copia / '_informe_mutantes.json'}")
    return 1 if fallos or not intactos else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
