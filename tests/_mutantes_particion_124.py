"""¿La partición sirve? Un mutante de cada propiedad, y **cada uno mata SOLO su fichero**.

    python -m tests._mutantes_particion_124

Es el único test de que partir la pieza haya servido para algo. Que los dos ficheros pasen
no lo demuestra: lo demuestra que **romper la ubicación no ponga rojo un test de identidad,
y al revés**. Si un mutante de una mata tests de la otra, siguen acopladas y la partición es
cosmética.

## Por qué esto existe

`MEJORAS #124` recibió cuatro rondas y **ninguna volvió limpia**. El patrón medido no fue
descuido: fue que la invariante modo/raíz y la regla de identidad vivían en una función
compartiendo `canon_dir`, así que **cada arreglo de una rompía la otra** —dos veces
seguidas, R25/H25-03 y R26/H26-01—. La decisión de partirlas sale de ahí, y esta es su
condición de cierre.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PY = sys.executable
_BASETEMP = "C:/t/part124"          # FUERA del arbol: dentro tumba tests que estan bien

UBI = "tests/test_ubicacion_del_workspace.py"
IDE = "tests/test_escritura_sobre_workspace.py"
FICHEROS = (UBI, IDE, "tests/test_sala_maquina_por_la_costura.py",
            "tests/test_escritura_costura.py")

MUTANTES = [
    # --- Propiedad A: UBICACION. Solo puede matar tests de `UBI`. ----------------
    ("A1 el modo local deja de exigir FUERA", "core/casos/ubicacion.py",
     '    if donde != FUERA:',
     '    if False:',
     UBI),
    ("A2 `drive_active` deja de exigir DENTRO", "core/casos/ubicacion.py",
     '        if donde != DENTRO:',
     '        if False:',
     UBI),
    ("A3 la ubicacion deja de fallar cerrado", "core/casos/ubicacion.py",
     '    donde = clasificar_bajo(Path(workspace.working_root), raiz_del_catalogo())',
     '    donde = clasificar_bajo(Path(workspace.working_root), raiz_del_catalogo())\n'
     '    donde = FUERA if donde != DENTRO else donde',
     UBI),

    # --- Propiedad B: IDENTIDAD. Solo puede matar tests de `IDE`. ----------------
    # El ancla lleva la linea siguiente porque `canon = id_go or del_nombre` aparece en
    # las DOS funciones de identidad —la historica y la del workspace— y un ancla ambigua
    # muta la que no toca. El arnes lo detecto solo, que es para lo que sirve.
    ("B1 la peticion vuelve a ser prueba", "core/casos/escritura.py",
     "    canon = id_go or del_nombre\n"
     "    if not canon:\n"
     "        return None, raiz,",
     "    canon = id_go or del_nombre or (next(iter(pedidos)) if pedidos else None)\n"
     "    if not canon:\n"
     "        return None, raiz,",
     IDE),
    ("B2 se ignora `meta.id_go`", "core/casos/escritura.py",
     '    id_go = (str(case_locator.read_case_meta(canon_dir).get("id_go") or "")\n'
     '             .strip().upper()) or None',
     '    id_go = None',
     IDE),
    ("B3 dos `case_id` distintos dejan de rechazarse", "core/casos/escritura.py",
     '    if len(ids) > 1:',
     '    if False:',
     IDE),

    # --- Los TRES que escribio R27 y yo no tenia. --------------------------------
    #
    # Mis seis pasaban, y con ellos afirme «cero cruzan». El revisor escribio otros y
    # dos SOBREVIVIERON y uno CRUZO. La leccion no es que faltaran mutantes: es que
    # **«mis mutantes no cruzan» no es «la particion no se cruza»**, y yo dije lo
    # segundo habiendo medido lo primero.
    ("A4 la ubicacion no se llama para `drive_active` (R27/H27-02)",
     "core/casos/escritura.py",
     "    ubicacion.exigir_coherente(workspace)",
     "    if WorkspaceMode(workspace.mode) is not WorkspaceMode.DRIVE_ACTIVE:\n"
     "        ubicacion.exigir_coherente(workspace)",
     UBI),
    ("A5 el rechazo temprano de modo bloqueado (R27/H27-03)", "core/casos/ubicacion.py",
     "    if modo.es_bloqueado or workspace.working_root is None:",
     "    if False and (modo.es_bloqueado or workspace.working_root is None):",
     UBI),
    ("B4 `drive_active` deja de exigir el expediente CORRECTO (R27/H27-02)",
     "core/casos/escritura.py",
     "    if WorkspaceMode(workspace.mode) is WorkspaceMode.DRIVE_ACTIVE \\\n"
     "            and _normal(raiz) != _normal(canon_dir):",
     "    if False and WorkspaceMode(workspace.mode) is WorkspaceMode.DRIVE_ACTIVE \\\n"
     "            and _normal(raiz) != _normal(canon_dir):",
     IDE),
    ("B5 un `drive_active` sin canon deja de rechazarse (R27/H27-01)",
     "core/casos/escritura.py",
     "        if WorkspaceMode(workspace.mode) is WorkspaceMode.DRIVE_ACTIVE:\n"
     "            raise IdentidadDiscordante(",
     "        if False:\n"
     "            raise IdentidadDiscordante(",
     IDE),
]


def _corre() -> tuple[set[str], bool]:
    """`(tests que fallaron, la corrida fue una ejecucion VALIDA de pytest)`.

    **La segunda mitad la obliga R27/H27-04, y sin ella nada de lo que este arnes dijo
    valia.** La version anterior devolvia solo las lineas `FAILED `, asi que un error de
    coleccion —un fichero que no existe, un `ImportError`— daba el conjunto vacio, o sea
    «cero fallos», o sea **baseline verde**. El revisor lo reprodujo apuntandolo a un
    fichero inexistente.

    Es la misma clase que la busqueda mutilada leida como ausencia: «no hay fallos» y
    «no pude ejecutar» se veian igual.
    """
    r = subprocess.run(
        [PY, "-m", "pytest", *FICHEROS, "-q", "--tb=no", "-p", "no:cacheprovider",
         "--basetemp=" + _BASETEMP, "-p", "no:randomly"],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    salida = (r.stdout or "") + (r.stderr or "")
    fallos = {ln.split(" ")[1] for ln in salida.splitlines()
              if ln.startswith("FAILED ")}
    # `returncode` 0 = todo verde; 1 = hubo fallos de test. Cualquier otro (2 = uso,
    # 3 = interno, 4 = uso de linea de comandos, 5 = nada recogido) NO es una ejecucion
    # valida. Y un `ERROR` de coleccion o de setup tampoco, aunque el codigo sea 1.
    valida = r.returncode in (0, 1) and "ERROR" not in salida and "error" not in (
        r.stderr or "").lower()
    return fallos, valida


def main() -> int:
    g = subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ,
                       capture_output=True, encoding="utf-8")
    if g.returncode != 0:                      # H27-04: `git` tambien puede fallar
        print("NO SE PUDO CONSULTAR GIT:", g.stderr)
        return 2
    if g.stdout.strip():
        print("ARBOL SUCIO: se restaura desde los bytes originales, pero un arbol sucio\n"
              "hace ambiguo el baseline.\n" + g.stdout.strip())
        return 2

    fallos, valida = _corre()
    if not valida:
        print("LA CORRIDA BASE NO FUE UNA EJECUCION VALIDA DE PYTEST: no se puede "
              "afirmar nada. «Cero fallos» y «no se ejecuto» NO son lo mismo.")
        return 2
    if fallos:
        print("EL ARBOL LIMPIO NO ESTA VERDE:", sorted(fallos))
        return 2
    print("base: verde\n")

    fallidos = 0
    for nombre, fichero, viejo, nuevo, propio in MUTANTES:
        p = RAIZ / fichero
        txt = p.read_text(encoding="utf-8")
        if txt.count(viejo) != 1:
            print(f"[X ] {nombre}: el ancla aparece {txt.count(viejo)} veces")
            fallidos += 1
            continue
        # H27-05: los bytes originales se guardan ANTES, la escritura va DENTRO del
        # `try`, y se restaura SOLO este fichero — no `git checkout -- .`, que se
        # llevaria por delante cualquier cambio concurrente en otro sitio.
        original = p.read_bytes()
        try:
            p.write_text(txt.replace(viejo, nuevo), encoding="utf-8", newline="")
            rojos, valida = _corre()
        finally:
            p.write_bytes(original)
            if p.read_bytes() != original:
                print(f"[X ] {nombre}: NO SE PUDO RESTAURAR {fichero}. Se aborta.")
                return 2

        if not valida:
            print(f"[X ] {nombre}: la corrida NO fue valida; no se puede decir si "
                  f"muere o sobrevive")
            fallidos += 1
            continue
        if not rojos:
            print(f"[X ] {nombre}: SOBREVIVE")
            fallidos += 1
            continue
        ajenos = {t for t in rojos if not t.startswith(propio)}
        ok = not ajenos
        fallidos += 0 if ok else 1
        print(f"[{'ok' if ok else 'X '}] {nombre}")
        print(f"        mata {len(rojos)} en {propio.split('/')[-1]}")
        if ajenos:
            print("        ACOPLADAS, tambien mata: " + ", ".join(sorted(ajenos)))

    print("\nmutantes que cruzan la particion:", fallidos)
    return 1 if fallidos else 0


if __name__ == "__main__":
    raise SystemExit(main())
