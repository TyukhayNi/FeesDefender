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
]


def _corre() -> set[str]:
    r = subprocess.run(
        [PY, "-m", "pytest", *FICHEROS, "-q", "--tb=no", "-p", "no:cacheprovider",
         "--basetemp=" + _BASETEMP, "-p", "no:randomly"],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    return {ln.split(" ")[1] for ln in (r.stdout or "").splitlines()
            if ln.startswith("FAILED ")}


def main() -> int:
    sucio = subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ,
                           capture_output=True, encoding="utf-8").stdout.strip()
    if sucio:
        print("ARBOL SUCIO: se restaura con `git checkout` desde el INDICE.\n" + sucio)
        return 2
    if _corre():
        print("EL ARBOL LIMPIO NO ESTA VERDE")
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
        p.write_text(txt.replace(viejo, nuevo), encoding="utf-8", newline="")
        try:
            rojos = _corre()
        finally:
            subprocess.run(["git", "checkout", "--", "."], cwd=RAIZ, check=True)

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
