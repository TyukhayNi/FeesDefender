"""Manifiesto de mutacion de la RENOVACION del mutex por caso (`MEJORAS #145`).

    python -m tests._mutantes_renovacion_mutex

Ejecutable, no una afirmacion: decir «el test sigue matando al mutante que rompe la
renovacion» en un mensaje de commit no es verificable. Aqui estan los parches, el comando
y los tests que deben ponerse rojos.

## Por que existe este arnes y no bastaba el que ya habia

Porque el arreglo del 2026-09-07 **repartio en dos** la propiedad que un solo test
probaba con un plazo de pared: `test_RENUEVA_mientras_el_cuerpo_corre` sigue midiendo el
mecanismo —hay un renovador, llama a `renovar`, el disco cambia, el competidor se queda
fuera— y `test_el_renovador_DESPIERTA_dos_veces_por_lease` mide la **puntualidad** contra
la constante de produccion, sin reloj. Un reparto asi solo vale si cada mitad tiene su
mutante: `M02` es el que lo demuestra, porque es el unico que el presupuesto generoso del
primero ya **no** puede matar.

## Como se lee

- **SOBREVIVE** = el contrato NO esta probado ahi. Es el hallazgo, no un fallo del arnes.
- **MAL APUNTADO** = mata tests de OTRA frontera. Salvo que los muertos «de mas» dependan
  todos de la MISMA propiedad, en cuyo caso lo estrecho era la expectativa.

**Trampa heredada del arnes de `#136`:** `git checkout -- .` restaura desde el INDICE,
asi que el arbol tiene que estar limpio antes de correr o se pierde lo no commiteado.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PY = sys.executable
FICHEROS = ("tests/test_case_mutex.py",
            "tests/test_case_mutex_r11.py",
            "tests/test_case_mutex_r12.py")

CM = "core/casos/case_mutex.py"

#: `(nombre, fichero, ancla, sustituto, tests que DEBEN morir)`.
MUTANTES = [
    ("M01 el renovador no renueva nunca", CM,
     "                renovar(w_code, nonce=nonce, ahora=ahora_fn(), raiz=raiz)",
     "                pass  # mutante: el renovador no renueva",
     # Los tres cuelgan de la MISMA propiedad —que el hilo llama a `renovar`—: uno la mira
     # por el disco y dos por la senal que el fallo de esa llamada deja.
     {"test_RENUEVA_mientras_el_cuerpo_corre",
      "test_es_EL_HILO_quien_detecta_la_perdida_sin_que_nadie_pregunte",
      "test_un_SystemExit_en_el_hilo_deja_señal"}),

    ("M02 el renovador duerme MAS que el lease", CM,
     "        while not parar.wait(lease / _FRACCION_LATIDO):",
     "        while not parar.wait(lease * 2):",
     # EL mutante que justifica el reparto. Renovar «alguna vez» sigue ocurriendo —a los
     # 6 s, con un lease de 3— asi que el test del mecanismo, con su presupuesto de veinte
     # latidos, lo deja pasar. Antes lo mataba de refilon un plazo de pared de 3 s, o sea
     # por una coincidencia que la carga de la maquina podia deshacer en cualquier momento.
     {"test_el_renovador_DESPIERTA_dos_veces_por_lease"}),

    ("M03 la renovacion no mueve `renewed_at`", CM,
     '        estado["renewed_at"] = ahora',
     "        pass  # mutante: renueva sin mover el instante",
     {"test_RENUEVA_mientras_el_cuerpo_corre",
      "test_renovar_lo_alarga_y_lo_defiende"}),

    ("M04 el hilo vuelve a morir CALLADO (R11/H11-02)", CM,
     "                sesion.marcar_perdido(exc)\n                return",
     "                return",
     # Los dos tests que este arreglo TOCO. Si el mutante sobreviviera, la migracion al
     # presupuesto derivado se habria llevado por delante el critico de R11.
     {"test_es_EL_HILO_quien_detecta_la_perdida_sin_que_nadie_pregunte",
      "test_un_SystemExit_en_el_hilo_deja_señal"}),

    ("M05 el CASE_BUSY del lease vivo deja de nombrar el instante", CM,
     '                           fecha=estado["renewed_at"],',
     "                           fecha=None,",
     # La frontera del aserto nuevo: `_guard` traduce su `Timeout` al MISMO `CaseBusy`, asi
     # que un `pytest.raises` a secas no distingue «el lease esta vivo» de «la seccion
     # critica esta ocupada». Sin `fecha`, esa distincion no se puede hacer.
     {"test_RENUEVA_mientras_el_cuerpo_corre"}),

    ("M06 el hilo arranca pero no late", CM,
     '    hilo = threading.Thread(target=_latir, name=f"mutex-{w_code}", daemon=True)',
     '    hilo = threading.Thread(target=lambda: None, name=f"mutex-{w_code}",\n'
     "                            daemon=True)",
     # La mitad de la puntualidad que NO es el periodo: que haya alguien a quien
     # despertar. Misma propiedad que M01, atacada por el otro extremo.
     {"test_RENUEVA_mientras_el_cuerpo_corre",
      "test_el_renovador_DESPIERTA_dos_veces_por_lease",
      "test_es_EL_HILO_quien_detecta_la_perdida_sin_que_nadie_pregunte",
      "test_un_SystemExit_en_el_hilo_deja_señal"}),
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
            print(f"[X ] {nombre}: SOBREVIVE — el contrato no esta probado ahi")
            fallidos += 1
            continue
        propios = {t for t in rojos if any(m in t for m in esperado)}
        ajenos = rojos - propios
        ok = bool(propios) and not ajenos
        fallidos += 0 if ok else 1
        print(f"[{'ok' if ok else 'X '}] {nombre}")
        print(f"        muere en {len(propios)}: " + ", ".join(
            sorted(t.split("::")[-1] for t in propios)))
        if ajenos:
            print(f"        MAL APUNTADO, tambien mata {len(ajenos)}: " + ", ".join(
                sorted(t.split("::")[-1] for t in ajenos)))

    print("\nmal apuntados o supervivientes:", fallidos)
    return 1 if fallidos else 0


if __name__ == "__main__":
    raise SystemExit(main())
