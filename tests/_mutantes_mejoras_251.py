"""Arnés de mutación de `MEJORAS #251` y `#252` — la clave de cruce y el lazo de V1.

Mismo contrato que `tests/_mutantes_mejoras_214.py`, y por la misma razón: en la R1 del
2026-09-13 el revisor **no pudo verificar** una cifra de mutantes porque las definiciones
vivían fuera del objeto revisado, y la declaró SIN VERIFICAR. Una afirmación que nadie
puede comprobar no es un dato.

Comprueba dos cosas por mutante, y la segunda es la que suele faltar: que mate al test que
se le apunta, **y** que ese test estuviera verde antes de mutar.

No es un test de pytest y no corre en la suite (el nombre empieza por `_`): muta ficheros
de producción en el árbol. Se ejecuta a mano, con el árbol limpio:

    python -m tests._mutantes_mejoras_251
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
T_VA = "tests/test_verificar_apertura.py"
T_V1 = "tests/test_apertura_v1_etapas.py"

#: (nombre, fichero, texto original, texto mutado, test que DEBE ponerse rojo).
MUTANTES: list[tuple[str, str, str, str, str]] = [
    ("M01 la clave de cruce deja de normalizar Unicode", "core/verificar_apertura.py",
     'return unicodedata.normalize("NFC", ruta).translate(_DESHACER_ENCODING_RCLONE)',
     "return ruta.translate(_DESHACER_ENCODING_RCLONE)",
     f"{T_VA}::test_n1_c1_no_acusa_a_un_fichero_que_solo_difiere_en_la_FORMA_unicode"),

    ("M02 C2 vuelve a cruzar por la ruta cruda", "core/verificar_apertura.py",
     "con_hash = {clave_de_cruce(f.ruta): f.sha256 for f in censo.ficheros if f.sha256}",
     "con_hash = {f.ruta: f.sha256 for f in censo.ficheros if f.sha256}",
     f"{T_VA}::test_n2_c2_CONTRASTA_ese_fichero_en_vez_de_decir_que_no_puede"),

    ("M03 la clave deja de deshacer el encoding de rclone", "core/verificar_apertura.py",
     'return unicodedata.normalize("NFC", ruta).translate(_DESHACER_ENCODING_RCLONE)',
     'return unicodedata.normalize("NFC", ruta)',
     f"{T_VA}::test_n4_un_nombre_que_EMPIEZA_POR_ESPACIO_cruza_con_el_del_remoto"),

    ("M04 las colisiones de clave se funden en silencio", "core/verificar_apertura.py",
     "    if colisiones:\n        return Resultado(\"censo_remoto\", titulo, FALLO,",
     "    if False:\n        return Resultado(\"censo_remoto\", titulo, FALLO,",
     f"{T_VA}::test_n6_dos_ficheros_del_remoto_que_colapsan_a_la_MISMA_clave_se_declaran"),

    ("M05 el relleno de #225 no se confirma nunca", "core/verificar_apertura.py",
     "            if _es_el_relleno_de_225(raiz / rel, esperado):",
     "            if False:",
     f"{T_VA}::test_n7_c2_CONFIRMA_el_relleno_de_225_rehasheando_sin_la_cola_de_ceros"),

    ("M06 el relleno se da por confirmado sin rehashear", "core/verificar_apertura.py",
     "    return h.hexdigest().lower() == sha_remoto.lower()",
     "    return True",
     # Apuntado a n10 y NO a n8: el fichero de n8 mide 20 bytes, asi que sale por la
     # guarda del multiplo de 512 ANTES del re-hash y no ejercita este mutante. Un
     # mutante apuntado a un test que no lo alcanza sobrevive por el motivo equivocado.
     f"{T_VA}::test_n10_el_relleno_NO_se_confirma_sin_rehashear_de_verdad"),

    ("M07 el multiplo de 512 deja de exigirse", "core/verificar_apertura.py",
     "        if tam == 0 or tam % 512 != 0:",
     "        if tam == 0:",
     f"{T_VA}::test_n11_un_tamano_que_NO_es_multiplo_de_512_no_es_el_relleno_de_225"),

    ("M08 una discrepancia REAL deja de reportarse", "core/verificar_apertura.py",
     "        if real.lower() != esperado.lower():\n            discrepan.append(rel)",
     "        if False:\n            discrepan.append(rel)",
     f"{T_VA}::test_n3_y_una_discrepancia_REAL_bajo_ese_mismo_nombre_sigue_saliendo"),

    ("M09 V1 deja de verificar el expediente al terminar", "scripts/abrir_caso.py",
     "    _informar_v1(resultado)\n    try:\n        _verificar_expediente(case_dir, case_id)",
     "    _informar_v1(resultado)\n    try:\n        pass",
     f"{T_V1}::test_e1_al_terminar_v1_se_verifica_el_expediente"),

    ("M10 un fallo de la verificacion tumba la apertura", "scripts/abrir_caso.py",
     "    except Exception as exc:  # noqa: BLE001 — informar no puede tumbar la apertura",
     "    except ZeroDivisionError as exc:",
     f"{T_V1}::test_e2_si_la_verificacion_revienta_la_apertura_NO_se_cae"),

    ("M11 ese fallo se traga en silencio", "scripts/abrir_caso.py",
     '        typer.echo(f"[AVISO] no se pudo verificar el expediente: {exc}", err=True)',
     "        pass",
     f"{T_V1}::test_e3_y_ese_fallo_se_DICE_en_vez_de_tragarse"),
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
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
