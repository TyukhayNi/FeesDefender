"""Arnés de mutación de la población de la sala de lectura (`MEJORAS #316`, fila #46, PR #408)
y de su R1 adversarial — SOBRE UNA COPIA del árbol.

    python -m tests._mutantes_sala_lectura_316            # todos
    python -m tests._mutantes_sala_lectura_316 V03 K      # solo los que empiezan así
    python -m tests._mutantes_sala_lectura_316 --anclas   # solo comprueba las anclas

**Por qué vive aquí.** El plan del #408 citó cifras de mutantes de un arnés del scratchpad, y la
regla ya estaba escrita (memoria `feedback-mutacion-vale-por-su-mutante`, §(a) del 2026-09-13):
un arnés fuera del repo no acredita nada, porque nadie más puede correrlo. Este sí.

**Cómo se eligen.** Un mutante por frontera del contrato EN PROSA —el de `SKILL.md` Paso 5 y
6.5, el docstring de C3 y los hallazgos de la R1—, cada uno atado al test que dice guardarla. Y
algunos, a propósito, reintroducen el defecto exacto que la R1 encontró (la firma exenta, el
recorte de la cobertura, el `duplicado` que exime, el 0 sin cobertura).

**Qué cuenta como muerte** (el contrato estricto de `_mutantes_crm_ficha.py`):

1. el test objetivo pasa en la copia SIN mutar;
2. cada ancla aparece EXACTAMENTE una vez y el fichero mutado compila;
3. mutado, el test se EJECUTA (`--junitxml`) y falla por su aserto (`AssertionError`, o
   `Failed` de `pytest.raises`). Un `<error>` de colección o cualquier otra excepción —un
   programa roto— NO cuenta: morir no es ser detectado.

Se copia `core`, `scripts`, `tests` y la skill; al cerrar se comprueba que los ficheros del
árbol vivo que se mutaron conservan su `sha256`.
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

_SKILL = ".claude/skills/organizar-sala-lectura"
_COPIAR_DIRS = ("core", "scripts", "tests", _SKILL)
_COPIAR_FICHEROS = ("pyproject.toml",)
_IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")

VS = f"{_SKILL}/scripts/verificar_sala.py"
PRE = f"{_SKILL}/scripts/preclasificar.py"
MP = f"{_SKILL}/scripts/manifiesto_parser.py"
VA = "core/verificar_apertura.py"
IC = "core/intake_control.py"
INV = "core/inventory.py"

T_POB = "tests/test_sala_lectura_poblacion_316.py"
T_MP = "tests/test_manifiesto_parser.py"
T_PRE = "tests/test_preclasificar_sala_lectura.py"
T_VA = "tests/test_verificar_apertura.py"
T_IC = "tests/test_intake_control_por_ubicacion.py"
T_MIG = "tests/test_migrate_05crm_buckets.py"
T_INV = "tests/test_inventory.py"
T_CERO = "tests/test_sala_lectura_cero_acciones.py"

#: (nombre, fichero, [(ancla, sustitución), …], test que tiene que ponerse rojo).
MUTANTES: list[tuple[str, str, list[tuple[str, str]], str]] = [
    # --- La verja de población de la skill ------------------------------------------------
    ("V01 una fuente sin fila ni línea no es problema", VS,
     [("        problemas.append(f\"{muestra[k]}: la sala de máquina la procesó y no tiene fila en el \"\n",
       "        continue\n        problemas.append(f\"{muestra[k]}: la sala de máquina la procesó y no tiene fila en el \"\n")],
     f"{T_POB}::test_una_fuente_SIN_fila_ni_declaracion_es_un_problema"),

    # H-03: la fila con la ruta de la fuente y otro sha256.
    ("V02 una fila nunca contradice a su fuente", VS,
     [("        return (ruta in fuentes and _es_sha256(h) and h not in fuentes[ruta]\n",
       "        return False and (ruta in fuentes and _es_sha256(h) and h not in fuentes[ruta]\n")],
     f"{T_POB}::test_una_fila_con_la_ruta_de_la_fuente_y_otro_sha256_la_contradice"),

    # H-03, la otra mitad del par: la contradictoria no acredita por su hash.
    ("V03 el índice de sha256 incluye las filas contradictorias", VS,
     [("    shas = {h for _, h in coherentes if _es_sha256(h)}\n",
       "    shas = {h for _, h in pares if _es_sha256(h)}\n")],
     f"{T_POB}::test_una_fila_contradictoria_no_acredita_por_su_hash_a_otra_fuente"),

    # H-04/H-09: la línea `duplicado` no da cuenta de nada.
    ("V04 una línea duplicado exime como excluido", VS,
     [("        if fuentes[k] & shas or k in declaradas[\"excluido\"]:\n",
       "        if fuentes[k] & shas or k in declaradas[\"excluido\"] or k in declaradas[\"duplicado\"]:\n")],
     f"{T_POB}::test_una_linea_duplicado_NO_da_cuenta_si_su_contenido_no_esta_en_ninguna_fila"),

    # El contrario: el duplicado por sha256 SÍ da cuenta, sin declararse.
    ("V05 el duplicado por sha256 no da cuenta", VS,
     [("        if fuentes[k] & shas or k in declaradas[\"excluido\"]:\n",
       "        if k in declaradas[\"excluido\"]:\n")],
     f"{T_POB}::test_un_duplicado_por_sha256_no_necesita_fila_ni_linea"),

    ("V06 fila y línea en No copiados a la vez no es problema", VS,
     [("    for k in sorted((declaradas[\"excluido\"] | declaradas[\"duplicado\"]) & rutas_con_fila):\n",
       "    for k in sorted(set()):\n")],
     f"{T_POB}::test_una_ruta_con_fila_y_declarada_no_copiada_es_una_contradiccion"),

    # H-01, el defecto exacto: la firma vuelve a estar exenta.
    ("V07 la firma _firma_ vuelve a estar exenta", VS,
     [("        if intake_control.es_fichero_de_protocolo(k) or k in crudos:\n",
       "        if intake_control.es_fichero_de_protocolo(k) or k in crudos or \\\n"
       "                k.rsplit(\"/\", 1)[-1].startswith(\"_firma_\"):\n")],
     f"{T_POB}::test_la_firma_de_correo_es_un_adjunto_mas_y_pide_fila_o_linea"),

    # H-06, el defecto exacto: la ruta de la cobertura pierde su `00_Input/`.
    ("V08 la clave de la cobertura recorta 00_Input", VS,
     [("    return unicodedata.normalize(\"NFC\", (rel or \"\").strip().replace(\"\\\\\", \"/\"))\n",
       "    return _clave_ruta(rel)\n")],
     f"{T_POB}::test_la_ruta_de_la_cobertura_no_pierde_un_00_Input_del_cliente"),

    # Una fila `md5:` no es un sha256: no contradice.
    ("V09 una fila md5 se toma por sha256 y contradice", VS,
     [("        return (ruta in fuentes and _es_sha256(h) and h not in fuentes[ruta]\n",
       "        return (ruta in fuentes and bool(h) and h not in fuentes[ruta]\n")],
     f"{T_POB}::test_una_fila_md5_da_cuenta_de_su_fuente_por_la_ruta"),

    # El relleno de `MEJORAS #225` como cruce por contenido: salió de medir el remedio de
    # H-09 contra los casos reales (ocho copias que la línea `duplicado` ya no eximía).
    ("V10 la verja no mide el relleno de #225", VS,
     [("        if input_dir is not None and _originales_de_relleno_225(Path(input_dir) / muestra[k]) & shas:\n",
       "        if False:\n")],
     f"{T_POB}::test_una_copia_con_el_relleno_de_225_da_cuenta_por_su_contenido"),

    # La costura del CLI: el `00_Input` que `main` deduce tiene que llegar a la verja.
    ("V11 el CLI no le pasa el 00_Input a la verja", VS,
     [("                                         entrada if entrada.is_dir() else None)\n",
       "                                         None)\n")],
     f"{T_POB}::test_cli_mide_el_relleno_con_el_00_Input_del_layout"),

    # --- El CLI de la verja (H-02) --------------------------------------------------------
    ("C01 sin cobertura, el verify da 0", VS,
     [("    elif not sin_cobertura:\n        problemas.append(\"no hay cobertura",
       "    elif False:\n        problemas.append(\"no hay cobertura")],
     f"{T_POB}::test_cli_sin_cobertura_FALLA_salvo_con_sin_cobertura"),

    ("C02 la cobertura no se deduce del layout", VS,
     [("        if _cobertura_hermana(sala_dir).exists():\n",
       "        if False and _cobertura_hermana(sala_dir).exists():\n")],
     f"{T_POB}::test_cli_deduce_la_cobertura_de_la_sala_de_maquina_hermana"),

    # Reapuntado en la primera corrida: con `if False:` el diccionario llegaba a `verificar()`
    # y el programa moría con `AttributeError` —muerto por estar roto, no detectado—. El fallo
    # silencioso de verdad es el que el docstring de `_leer_cobertura` nombra: tomar lo ilegible
    # por una cobertura vacía, y dar OK.
    ("C03 una cobertura que no es una lista se toma por vacía", VS,
     [("    if not isinstance(datos, list):\n        return None, f\"la cobertura {p} no es una lista",
       "    if not isinstance(datos, list):\n        return [], \"\"\n"
       "        return None, f\"la cobertura {p} no es una lista")],
     f"{T_POB}::test_cli_una_cobertura_que_no_existe_o_no_es_una_lista_es_un_error_de_uso"),

    ("C05 una cobertura pedida que no existe se trata como si no se hubiera pedido", VS,
     [("    elif not cobertura_path.exists():\n        print(f\"no existe la cobertura {cobertura_path}\"); return 2\n",
       "    elif not cobertura_path.exists():\n        cobertura_path = None\n")],
     f"{T_POB}::test_cli_una_cobertura_que_no_existe_o_no_es_una_lista_es_un_error_de_uso"),

    ("C04 --sin-cobertura se acepta con una cobertura presente", VS,
     [("    if sin_cobertura and cobertura_path is not None:\n",
       "    if False:\n")],
     f"{T_POB}::test_cli_sin_cobertura_con_una_cobertura_presente_es_un_error"),

    # --- El parser y el zip crudo (H-05, H-07) ---------------------------------------------
    ("P01 un duplicado sin «de `ruta`» es de formato cerrado", MP,
     [("        if not m or (m.group(\"motivo\").startswith(\"duplicado\")\n"
       "                     and not _DETALLE_DE_DUPLICADO.match(m.group(\"detalle\"))):\n",
       "        if not m:\n")],
     f"{T_MP}::test_no_copiados_ESTRICTO_un_duplicado_sin_de_ruta_es_un_error"),

    ("W01 el zip crudo se aparta en cualquier carpeta", PRE,
     [("        return len(partes) > 1 and bool(_LUGAR_DEL_INTAKE_WHATSAPP.match(partes[0]))\n",
       "        return True\n")],
     f"{T_PRE}::test_emparejar_exports_whatsapp_solo_donde_escribe_el_intake"),

    # --- C3 --------------------------------------------------------------------------------
    ("K01 C3 vuelve a eximir la firma", VA,
     [("        elif clave in crudos:\n",
       "        elif clave in crudos or clave.rsplit(\"/\", 1)[-1].startswith(\"_firma_\"):\n")],
     f"{T_VA}::test_316_c3_la_firma_de_correo_es_un_adjunto_mas_y_se_exige"),

    ("K02 C3 exime también las líneas duplicado", VA,
     [("                      if m == \"excluido\"}\n",
       "                      if m in (\"excluido\", \"duplicado\")}\n")],
     f"{T_VA}::test_316_c3_una_linea_duplicado_NO_exime_si_su_contenido_no_esta_en_el_catalogo"),

    ("K03 el ok de C3 esconde las exclusiones tras un número", VA,
     [("                     f\"sin contraste: {'; '.join(declaradas_usadas[:3])}{mas}\")\n",
       "                     f\"sin contraste\")\n")],
     f"{T_VA}::test_316_c3_una_exclusion_declarada_se_dice_con_su_ruta_y_su_motivo"),

    ("K04 C3 recorta el 00_Input de la cobertura", VA,
     [("        clave = _clave_de_cobertura(rel)\n",
       "        clave = _clave_de_ruta_de_origen(rel)\n")],
     f"{T_VA}::test_316_c3_la_ruta_de_la_cobertura_no_pierde_un_00_Input_del_cliente"),

    ("K05 C3 aparta el zip crudo en cualquier carpeta", VA,
     [("        return len(partes) > 1 and bool(_LUGAR_DEL_INTAKE_WHATSAPP.fullmatch(partes[0]))\n",
       "        return True\n")],
     f"{T_VA}::test_316_c3_el_zip_crudo_solo_se_aparta_donde_escribe_el_intake"),

    ("K06 el parser de C3 acepta un duplicado sin «de `ruta`»", VA,
     [("        if motivo == \"duplicado\" and not _DETALLE_DE_DUPLICADO.match(m.group(\"detalle\")):\n"
       "            continue\n",
       "")],
     f"{T_VA}::test_316_anti_deriva_no_copiados_se_lee_igual_en_C3_y_en_la_skill"),

    ("K07 C3 no mide el relleno de #225", VA,
     [("        elif _originales_de_relleno_225(entrada / muestra[clave]) & hashes_catalogo:\n",
       "        elif False:\n")],
     f"{T_VA}::test_316_c3_una_copia_con_el_relleno_de_225_esta_catalogada_por_su_contenido"),

    # El relleno solo acredita contra el catálogo que NO contradice (la frontera de H-03).
    ("K08 C3 acepta el relleno de cualquier sha256, no solo del catálogo", VA,
     [("        elif _originales_de_relleno_225(entrada / muestra[clave]) & hashes_catalogo:\n",
       "        elif _originales_de_relleno_225(entrada / muestra[clave]):\n")],
     f"{T_VA}::test_316_c3_una_cola_de_ceros_que_no_es_la_de_un_documento_catalogado_se_exige"),

    # El detector de C2 se partió en dos para que C3 lo use (`_originales_de_relleno_225`): la
    # frontera del #307 —detrás del original solo puede haber ceros— tiene que seguir guardada.
    ("K09 el detector del relleno acepta prefijos que no acaban en la cola de ceros", VA,
     [("            if seguro + k >= frontera:\n                candidatos.add(h.hexdigest().lower())\n",
       "            if True:\n                candidatos.add(h.hexdigest().lower())\n")],
     f"{T_VA}::test_307_un_original_con_bytes_AÑADIDOS_antes_del_relleno_no_se_confirma"),

    # --- El registro de protocolo (H-10) ---------------------------------------------------
    ("R01 los patrones casan por el principio", IC,
     [("                or any(pat.fullmatch(nombre) for pat in RAIZ_PATRONES))\n",
       "                or any(pat.match(nombre) for pat in RAIZ_PATRONES))\n")],
     f"{T_IC}::test_los_nombres_de_la_migracion_se_casan_con_su_sello_y_no_por_prefijo"),

    ("R02 vuelven los prefijos de la migración", IC,
     [("    \"_viabilidad.json.\",\n)\n",
       "    \"_viabilidad.json.\",\n    \"_migration_05crm_\", \"_caso.md.bak_\", \"_intake_hashes.json.bak_\",\n)\n")],
     f"{T_IC}::test_los_nombres_de_la_migracion_se_casan_con_su_sello_y_no_por_prefijo"),

    # Estrechar de más: la copia de seguridad real deja de casar.
    ("R03 el patrón de la copia del manifiesto no casa con el escritor", IC,
     [("    re.compile(r\"_intake_hashes\\.json\\.bak_\\d{8}t\\d{6}\"),\n",
       "    re.compile(r\"_intake_hashes\\.json\\.bak_\\d{8}t\\d{6}z\"),\n")],
     f"{T_MIG}::test_lo_que_la_migracion_deja_en_la_raiz_de_00_input_es_protocolo"),

    # --- Los dos tests reescritos que la R1 vio laxos --------------------------------------
    ("I01 el inventario vuelve a dejar fuera un plano", INV,
     [("        if es_fichero_de_protocolo(path.relative_to(input_dir).as_posix()):\n",
       "        if es_fichero_de_protocolo(path.relative_to(input_dir).as_posix()) or \\\n"
       "                path.suffix == \".dxf\":\n")],
     f"{T_CERO}::test_los_planos_y_lo_que_no_se_sabe_leer_ENTRAN_en_la_sala"),

    ("I02 el inventario aparta todo .pulled, esté donde esté", INV,
     [("        if es_fichero_de_protocolo(path.relative_to(input_dir).as_posix()):\n",
       "        if es_fichero_de_protocolo(path.relative_to(input_dir).as_posix()) or \\\n"
       "                path.name == \".pulled\":\n")],
     f"{T_INV}::test_inventory_clasifica_por_fuente"),
]

#: Tipos con los que un rojo SÍ es la detección de la propiedad.
_DETECCION = frozenset({"AssertionError", "Failed"})


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copia() -> Path:
    destino = Path(tempfile.mkdtemp(prefix="mutantes_316_"))
    for d in _COPIAR_DIRS:
        shutil.copytree(RAIZ / d, destino / d, ignore=_IGNORAR)
    for f in _COPIAR_FICHEROS:
        if (RAIZ / f).is_file():
            shutil.copy2(RAIZ / f, destino / f)
    return destino


def _tipo(mensaje: str) -> str:
    """`paquete.modulo.Clase: texto` → `Clase`; un `assert …` reescrito sin mensaje propio
    también es un `AssertionError`."""
    m = (mensaje or "").strip()
    if m == "assert" or m.startswith("assert "):
        return "AssertionError"
    return m.split(":", 1)[0].strip().rsplit(".", 1)[-1]


def _corre(copia: Path, test: str, junit: Path) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line", "-p", "no:randomly",
         "-p", "no:cacheprovider", "-W", "ignore::DeprecationWarning",
         f"--junitxml={junit}", test],
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
