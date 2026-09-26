"""Arnés de mutación de `MEJORAS #296` (el token y la carpeta de Drive dicen por qué no están) y
`#301` (las carpetas de E&V con el W-code delante) — SOBRE UNA COPIA del árbol.

    python -m tests._mutantes_intake_drive_296_301            # todos
    python -m tests._mutantes_intake_drive_296_301 T W        # solo los que empiezan así
    python -m tests._mutantes_intake_drive_296_301 --anclas   # solo comprueba las anclas

Un mutante por frontera del contrato en prosa —el de los docstrings de `obtener_token_drive`,
`leer_carpeta_drive` y `parse_ev_folder_name`, el de `abrir_caso._direccion_de_la_carpeta` y el
del precheck de la skill—, cada uno atado al test que dice guardarla. Varios reintroducen el
defecto exacto que el backlog midió: el timeout de 5 s, el «token/red» del alta, el 3 de un
remote inexistente, el W-code delante que no parsea.

Contrato estricto, el de `_mutantes_crm_ficha.py`: base verde, ancla única que compila, y
muerte solo por el aserto del test (`AssertionError` o `Failed`), nunca por un programa roto.
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

ID = "core/intake_drive.py"
AC = "scripts/abrir_caso.py"
AU = "scripts/audit_ev_folder_names.py"
PRE = f"{_SKILL}/scripts/precheck_rclone.py"

T_ID = "tests/test_intake_drive.py"
T_AC = "tests/test_abrir_caso_cli.py"
T_AU = "tests/test_audit_ev_folder_names.py"
T_PRE = "tests/test_precheck_rclone.py"
_TOK = f"{T_ID}::TestObtenerTokenDrive"
_CAR = f"{T_ID}::TestLeerCarpetaDrive"

#: (nombre, fichero, [(ancla, sustitución), …], test que tiene que ponerse rojo).
MUTANTES: list[tuple[str, str, list[tuple[str, str]], str]] = [
    # --- #296: el lector del token ---------------------------------------------------------
    ("T01 el timeout vuelve a 5 s", ID,
     [("_TIMEOUT_RCLONE_TOKEN = 30\n", "_TIMEOUT_RCLONE_TOKEN = 5\n")],
     f"{_TOK}::test_el_timeout_de_las_dos_ordenes_es_holgado"),

    ("T02 la lectura que tarda sale como un fallo cualquiera", ID,
     [('        return None, (f"{orden} tardó más de {_TIMEOUT_RCLONE_TOKEN} s (¿otra corrida de rclone "\n',
       '        return None, (f"{orden} falló "\n')],
     f"{_TOK}::test_si_config_show_TARDA_lo_dice"),

    ("T03 el remote inexistente no se reconoce", ID,
     [("    if _REMOTE_INEXISTENTE in salida:\n", "    if False:\n")],
     f"{_TOK}::test_si_el_remote_no_existe_lo_dice"),

    ("T04 la renovación que tarda pierde su causa", ID,
     [('        return TokenDrive(None, ("el token estaba caducado y renovarlo (`rclone about gdrive_ev:`) "\n',
       '        return TokenDrive(None, ("renovación fallida "\n')],
     f"{_TOK}::test_si_RENOVAR_tarda_lo_dice"),

    # El mutante deja el programa funcionando y arrastra la salida de rclone al motivo: es la
    # fuga que el test existe para detectar.
    ("T05 el motivo arrastra la salida de rclone", ID,
     [('        return None, f"el remote `{remote}` no tiene un bloque `token` legible (¿falta el login?)"\n',
       '        return None, f"el remote `{remote}` no tiene un bloque `token` legible: {salida[:160]}"\n')],
     f"{_TOK}::test_el_motivo_nunca_lleva_la_salida_de_rclone"),

    # --- #296: la carpeta ---------------------------------------------------------------------
    ("T06 la carpeta pierde el motivo del token", ID,
     [('        return None, f"no hay token de `gdrive_ev`: {token.motivo}"\n',
       '        return None, "no hay token de `gdrive_ev`"\n')],
     f"{_CAR}::test_sin_token_devuelve_el_motivo_del_token"),

    ("T07 el HTTP que no es 200 no se dice", ID,
     [('            return None, f"la Drive API respondió HTTP {r.status_code}{pista}"\n',
       '            return None, "la Drive API falló"\n')],
     f"{_CAR}::test_un_http_que_no_es_200_se_dice"),

    # --- #296: el alta, los dos sitios que decían «token/red» -----------------------------
    ("A01 el error de --team-id vuelve a «token/red»", AC,
     [('            typer.echo(f"[ERROR] --team-id no se pudo derivar de --folder-id ({motivo_team}): "\n',
       '            typer.echo(f"[ERROR] --team-id no se pudo derivar de --folder-id (token/red): "\n')],
     f"{T_AC}::test_cli_drive_ev_team_id_no_derivable_DICE_POR_QUE"),

    ("A02 el aviso de la autoderivación vuelve a «token/red»", AC,
     [('            typer.echo(f"[auto] No se pudo leer la carpeta de Drive: {motivo}. "\n',
       '            typer.echo("[auto] No se pudo leer la carpeta de Drive (token/red). "\n')],
     f"{T_AC}::test_cli_drive_ev_folder_info_none_degrada_limpio"),

    ("A03 el auditor pierde el motivo", AU,
     [('            f"[ERROR] No se pudo obtener access_token de gdrive_ev: {lectura.motivo}.\\n"\n',
       '            "[ERROR] No se pudo obtener access_token de gdrive_ev.\\n"\n')],
     f"{T_AU}::test_sin_token_dice_el_motivo_y_sale_con_2"),

    # --- #296: el precheck de la skill -------------------------------------------------------
    ("P01 el precheck junta el timeout con «no instalado»", PRE,
     [("    except subprocess.TimeoutExpired:\n        return 5\n",
       "    except subprocess.TimeoutExpired:\n        return 4\n")],
     f"{T_PRE}::test_exit_5_si_rclone_TARDA_y_el_veredicto_lo_dice"),

    ("P02 el precheck no reconoce el remote inexistente", PRE,
     [('    if r.returncode != 0 or _REMOTE_INEXISTENTE in (r.stdout or ""):\n',
       "    if r.returncode != 0:\n")],
     f"{T_PRE}::test_exit_4_si_el_remote_NO_EXISTE_aunque_rclone_salga_con_0"),

    # --- #301: el parser ---------------------------------------------------------------------
    ("W01 el W-code delante no se reconoce", ID,
     [("    m = _EV_FOLDER_W_DELANTE_RE.match(nombre)\n", "    m = None\n")],
     f"{T_ID}::test_parse_folder_w_code_DELANTE"),

    ("W02 el consultor se queda en la dirección", ID,
     [('        direccion = " - ".join(tramos[:-1]) if len(tramos) >= 2 else "".join(tramos)\n',
       '        direccion = " - ".join(tramos)\n')],
     f"{T_ID}::test_parse_folder_w_code_DELANTE"),

    ("W03 cualquier guion separa tramos, también el «1-2» de un piso", ID,
     [(r'_SEPARADOR_DE_TRAMO_RE = re.compile(r"\s+[-–]\s+")' + "\n",
       r'_SEPARADOR_DE_TRAMO_RE = re.compile(r"\s*[-–]\s*")' + "\n")],
     f"{T_ID}::test_parse_folder_w_code_DELANTE"),

    ("W04 el W-code en medio SIN guion también se interpreta", ID,
     [(r'    r"^(.*?)\s*[-–]\s*(W-[A-Z0-9]{5,8})\b",' + "\n",
       r'    r"^(.*?)\s*[-–]?\s*(W-[A-Z0-9]{5,8})\b",' + "\n")],
     f"{T_ID}::test_parse_folder_w_code_en_medio_SIN_guion_no_se_adivina"),

    # --- #301: la ciudad que SaRS1 pone delante ---------------------------------------------
    ("C01 la ciudad del caso no se quita", AC,
     [("    sin_ciudad = _sin_la_ciudad_delante(derivada, ciudad)\n",
       "    sin_ciudad = derivada\n")],
     f"{T_AC}::test_cli_drive_ev_direccion_de_una_carpeta_con_el_W_CODE_DELANTE_y_su_ciudad"),

    ("C02 se quita cualquier palabra en mayúsculas con punto", AC,
     [("    if ciudad and punto and resto.strip() and _pliega(cabeza.strip()) == _pliega(ciudad.strip()):\n",
       "    if ciudad and punto and resto.strip() and cabeza.strip().isupper():\n")],
     f"{T_AC}::test_cli_drive_ev_un_prefijo_que_NO_es_la_ciudad_se_conserva"),
]

#: Tipos con los que un rojo SÍ es la detección de la propiedad.
_DETECCION = frozenset({"AssertionError", "Failed"})


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _copia() -> Path:
    destino = Path(tempfile.mkdtemp(prefix="mutantes_296_301_"))
    for d in _COPIAR_DIRS:
        shutil.copytree(RAIZ / d, destino / d, ignore=_IGNORAR)
    for f in _COPIAR_FICHEROS:
        if (RAIZ / f).is_file():
            shutil.copy2(RAIZ / f, destino / f)
    return destino


def _tipo(mensaje: str) -> str:
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
