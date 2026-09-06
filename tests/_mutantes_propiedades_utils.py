"""Manifiesto de mutacion de las propiedades de `core/utils.py`. Ejecutable, no una afirmacion.

    python -m tests._mutantes_propiedades_utils

Existe por la misma razon que los otros tres arneses del repo: cada docstring de
`tests/test_propiedades_utils.py` **afirma** que un mutante concreto lo mata, y una
afirmacion en prosa dentro del propio fichero que afirma no es verificable. Aqui estan
los parches, el comando y el test que debe ponerse rojo por cada uno.

## Este arnes mide ADEMAS otra cosa

Corre los mutantes contra **dos** conjuntos a la vez:

  - `tests/test_propiedades_utils.py` — las property tests nuevas (2026-09-06).
  - `tests/test_utils.py`             — los tests de EJEMPLO que ya existian.

Y reporta por separado quien mata a quien. Eso responde la pregunta que de verdad
importaba al adoptar `hypothesis`, y que no se contesta con un porcentaje de cobertura:
**¿que defectos entran por delante de la suite de ejemplos y solo caza la propiedad?**
Un mutante marcado `SOLO LA PROPIEDAD` es exactamente eso, medido.

## Como se lee el resultado

- **SOBREVIVE** = el contrato NO esta probado ahi. Es el hallazgo, no un fallo del arnes.
- **SOLO LA PROPIEDAD** = los tests de ejemplo lo dejan pasar. Es lo que compro `hypothesis`.
- **AMBOS** = coincidencia de cobertura; la propiedad no aporta ahi, y decirlo es parte
  del trabajo. Un arnes que solo cuenta victorias no sirve para decidir nada.

## Las dos trampas, heredadas de `_mutantes_mejoras_136`

- **Muta desde el INDICE**: `git checkout -- .` restaura lo commiteado, asi que el arbol
  tiene que estar limpio antes de correr. Sin eso se pierde trabajo sin commitear.
- `-p no:randomly` y `-p no:cacheprovider`: el arnes compara conjuntos de tests rojos, y
  el orden aleatorio o una cache de `--lf` los harian variar entre corridas.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PY = sys.executable

PROPIEDADES = "tests/test_propiedades_utils.py"
EJEMPLOS = "tests/test_utils.py"
FICHEROS = (PROPIEDADES, EJEMPLOS)

U = "core/utils.py"

#: `(nombre, fichero, ancla, sustituto, tests que DEBEN morir)`.
#:
#: **Sobre los `esperado` de M05, M07, M08 y M09, que llevan DOS tests cada uno.** No es
#: laxitud: los guards se contratan desde las **dos direcciones** —`test_lo_que_pasa_el_
#: guard_es_un_solo_componente` dice que lo aceptado cumple todas las promesas, y
#: `test_el_guard_rechaza_lo_que_no_puede_ser_un_componente` dice que lo inyectado se
#: rechaza siempre—. Retirar una guarda rompe LAS DOS, porque las dos hablan de esa misma
#: propiedad. La primera version de este arnes solo listaba la direccion del rechazo y el
#: informe los marco «MAL APUNTADO»: lo estrecho era mi expectativa, no el mutante. Es el
#: mismo matiz que documenta `_mutantes_mejoras_136`. **No lo «arregles» de vuelta.**
MUTANTES = [
    # --- normalize_es_phone -------------------------------------------------
    ("M01 `normalize_es_phone` vuelve a un solo paso (el codigo previo al 2026-09-06)", U,
     "    while True:\n"
     '        if s.startswith("+34"):\n'
     "            s = s[3:]\n"
     '        elif s.startswith("0034"):\n'
     "            s = s[4:]\n"
     '        elif s.startswith("34") and len(s) == 11:\n'
     "            s = s[2:]\n"
     "        else:\n"
     "            return s",
     '    if s.startswith("+34"):\n'
     "        s = s[3:]\n"
     '    elif s.startswith("0034"):\n'
     "        s = s[4:]\n"
     '    elif s.startswith("34") and len(s) == 11:\n'
     "        s = s[2:]\n"
     "    return s",
     {"test_normalize_es_phone_es_idempotente",
      "test_normalize_es_phone_nunca_devuelve_prefijo_de_pais"}),

    ("M02 `normalize_es_phone` deja de reconocer el prefijo `0034`", U,
     '        elif s.startswith("0034"):\n            s = s[4:]\n',
     "",
     {"test_normalize_es_phone_nunca_devuelve_prefijo_de_pais"}),

    # --- neutralizar_case_id ------------------------------------------------
    ("M03 `neutralizar_case_id` devuelve la DIRECCION en vez del marcador", U,
     'f"{m.group(\'prefijo\')} - [DIRECCION] "',
     'f"{m.group(\'prefijo\')} - {m.group(\'direccion\')} "',
     {"test_neutralizar_case_id_no_deja_la_direccion"}),

    ("M04 `neutralizar_case_id` rompe la estructura (se come el ` - `)", U,
     'f"{m.group(\'prefijo\')} - [DIRECCION] "',
     'f"{m.group(\'prefijo\')} [DIRECCION] "',
     {"test_neutralizar_case_id_devuelve_algo_que_sigue_siendo_valido",
      "test_neutralizar_case_id_no_deja_la_direccion"}),

    # --- exigir_componente_de_ruta / exigir_sin_caracteres_de_ruta ----------
    ("M05 la guarda de caracteres prohibidos no muerde", U,
     '    if _WIN_FORBIDDEN.search(valor or ""):',
     "    if False:",
     {"test_el_guard_rechaza_lo_que_no_puede_ser_un_componente",
      "test_lo_que_pasa_el_guard_es_un_solo_componente"}),

    ("M06 la guarda de VACIO desaparece (el H-02 que convirtio CASOS_ROOT en expediente)", U,
     # La tilde de `vacío` NO es opcional: el ancla se compara literal contra el fichero,
     # y escribirla sin tilde daba «el ancla aparece 0 veces» — un mutante que no llega a
     # aplicarse parece un mutante que muere, y no es lo mismo.
     '    if not (valor or "").strip():\n'
     '        raise ValueError(f"{campo} no puede estar vacío.")\n',
     "",
     {"test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas"}),

    ("M07 la guarda de `.` / `..` desaparece", U,
     '    if valor.strip() in (".", ".."):',
     "    if False:",
     {"test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas",
      "test_lo_que_pasa_el_guard_es_un_solo_componente"}),

    ("M08 la guarda de espacios al borde desaparece (el H-03 del andamiaje parcial)", U,
     "    if valor != valor.strip():",
     "    if False:",
     {"test_lo_que_pasa_el_guard_es_un_solo_componente",
      "test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas"}),

    ("M09 la guarda de caracteres de control desaparece", U,
     "    if any(ord(c) < 32 for c in valor):",
     "    if False:",
     {"test_lo_que_pasa_el_guard_es_un_solo_componente",
      "test_el_guard_rechaza_lo_que_no_puede_ser_un_componente"}),
]


def _corre() -> set[str]:
    r = subprocess.run(
        [PY, "-m", "pytest", *FICHEROS, "-q", "--tb=no", "-p", "no:cacheprovider",
         "-p", "no:randomly"],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    return {ln.split(" ")[1] for ln in (r.stdout or "").splitlines()
            if ln.startswith("FAILED ")}


def _restaura() -> None:
    subprocess.run(["git", "checkout", "--", "."], cwd=RAIZ, check=True)


def main() -> int:
    sucio = subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ,
                           capture_output=True, encoding="utf-8").stdout.strip()
    if sucio:
        print("ARBOL SUCIO: se restaura con `git checkout` desde el INDICE y perderias\n"
              "lo no commiteado. Commitea antes de mutar.\n" + sucio)
        return 2

    base = _corre()
    if base:
        print("EL ARBOL LIMPIO NO ESTA VERDE:", sorted(base))
        return 2
    print("base: verde\n")

    fallidos = 0
    solo_propiedad = 0
    for nombre, fichero, viejo, nuevo, esperado in MUTANTES:
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
            _restaura()

        if not rojos:
            print(f"[X ] {nombre}: SOBREVIVE - el contrato no esta probado ahi")
            fallidos += 1
            continue

        por_propiedad = {t for t in rojos if PROPIEDADES.replace("/", "\\") in t
                         or PROPIEDADES in t}
        por_ejemplo = rojos - por_propiedad
        propios = {t for t in por_propiedad if any(m in t for m in esperado)}
        ajenos = por_propiedad - propios

        ok = bool(propios) and not ajenos
        fallidos += 0 if ok else 1
        etiqueta = "SOLO LA PROPIEDAD" if not por_ejemplo else "AMBOS"
        if not por_ejemplo:
            solo_propiedad += 1
        print(f"[{'ok' if ok else 'X '}] {nombre}  <<{etiqueta}>>")
        print(f"        propiedad mata {len(propios)}: " + ", ".join(
            sorted(t.split("::")[-1] for t in propios)))
        if por_ejemplo:
            print(f"        ejemplo   mata {len(por_ejemplo)}: " + ", ".join(
                sorted(t.split("::")[-1] for t in por_ejemplo)))
        if ajenos:
            print(f"        MAL APUNTADO, tambien mata {len(ajenos)}: " + ", ".join(
                sorted(t.split("::")[-1] for t in ajenos)))

    print(f"\nmal apuntados o supervivientes: {fallidos}")
    print(f"mutantes que SOLO caza la propiedad: {solo_propiedad} de {len(MUTANTES)}")
    return 1 if fallidos else 0


if __name__ == "__main__":
    raise SystemExit(main())
