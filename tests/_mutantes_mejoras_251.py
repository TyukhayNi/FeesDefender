"""Arnés de mutación de `MEJORAS #251` y `#252` — la clave de cruce y el lazo de V1.

Incluye como `M17` y `M18` **las dos mutaciones que Codex construyó en la R1 y que
sobrevivían** (H-07): el streaming limitado a un bloque y la desconexión desde `main`.

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
     'return unicodedata.normalize("NFC", ruta)',
     "return ruta",
     f"{T_VA}::test_n1_c1_no_acusa_a_un_fichero_que_solo_difiere_en_la_FORMA_unicode"),

    ("M02 C2 vuelve a cruzar por la ruta cruda", "core/verificar_apertura.py",
     "        por_clave.setdefault(clave_de_cruce(f.ruta), set()).add(f.sha256 or \"\")",
     "        por_clave.setdefault(f.ruta, set()).add(f.sha256 or \"\")",
     f"{T_VA}::test_n2_c2_CONTRASTA_ese_fichero_en_vez_de_decir_que_no_puede"),

    # --- Los 8 hallazgos de la R1 de Codex (2026-09-13) ---
    ("M03 [R1/H-01] la clave vuelve a TRADUCIR el encoding de rclone",
     "core/verificar_apertura.py",
     '    return unicodedata.normalize("NFC", ruta)' + chr(10),
     '    return unicodedata.normalize("NFC", ruta).replace("␠", " ")' + chr(10),
     f"{T_VA}::test_r1_h01_no_se_cruzan_dos_nombres_que_rclone_NUNCA_habria_escrito_asi"),

    ("M12 [R1/H-02] el descuadre con marcas de rclone deja de explicarse",
     "core/verificar_apertura.py",
     "    con_marcas = sorted({r for r in faltan + sobran if tiene_marcas_de_encoding(r)})",
     "    con_marcas = []",
     f"{T_VA}::test_r1_h02_un_descuadre_con_marcas_de_rclone_se_EXPLICA_en_vez_de_confundir"),

    ("M13 [R1/H-02] la explicacion sale SIEMPRE y deja de explicar",
     "core/verificar_apertura.py",
     "    con_marcas = sorted({r for r in faltan + sobran if tiene_marcas_de_encoding(r)})",
     "    con_marcas = sorted(set(faltan + sobran))",
     f"{T_VA}::test_r1_h02b_un_descuadre_LIMPIO_no_se_disfraza_de_problema_de_encoding"),

    ("M14 [R1/H-04] C2 vuelve a quedarse con el ULTIMO hash de una clave repetida",
     "core/verificar_apertura.py",
     "    ambiguas = sorted(k for k, shas in por_clave.items() if len(shas) > 1)",
     "    ambiguas = []",
     f"{T_VA}::test_r1_h04_c2_no_atribuye_a_un_fichero_el_checksum_de_OTRO"),

    ("M15 [R1/H-05] la cola del relleno vuelve a poder medir 512 o mas",
     "core/verificar_apertura.py",
     "        seguro = max(0, tam - (_MAX_COLA_RELLENO - 1))",
     "        seguro = max(0, tam - _MAX_COLA_RELLENO * 2)",
     f"{T_VA}::test_r1_h05b_la_cola_examinada_no_pasa_del_bloque_que_el_comentario_promete"),


    ("M17 [R1/H-07, U2 de Codex] el streaming solo rehashea el primer bloque",
     "core/verificar_apertura.py",
     "            while leidos < seguro:",
     "            if leidos < seguro:",
     f"{T_VA}::test_r1_h07_el_relleno_se_rehashea_ENTERO_aunque_pase_de_un_bloque"),

    ("M18 [R1/H-07, U1 de Codex] main deja de encadenar la verificacion",
     "scripts/abrir_caso.py",
     "        _informar_v1_y_verificar(resultado_v1, case_dir, ident.w_code)",
     "        _informar_v1(resultado_v1)",
     f"{T_V1}::test_r1_h07_main_LLAMA_al_verificador_y_lo_hace_FUERA_del_mutex"),

    ("M19 [R1/H-08] la orden impresa vuelve al case_id completo",
     "scripts/abrir_caso.py",
     "               f\"--case-id {w_code} --con-red\")",
     "               f\"--case-id {case_dir.name} --con-red\")",
     f"{T_VA}::test_r1_h08_la_orden_que_se_imprime_lleva_el_W_CODE_no_el_case_id"),

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
     "        _verificar_expediente(case_dir, w_code)",
     "        pass",
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

#: Supervivientes DECLARADOS: mutaciones que la suite no mata y que no se disfrazan de
#: muertas. El precedente de la casa es `[GITIGNORE-REGLAS-INERTES]`, donde un superviviente
#: se declaró y se le **retiró la garantía** en vez de enviar una línea inerte.
SUPERVIVIENTES_DECLARADOS = [
    ("M16 [R1/H-05] `if len(cola) != tam - seguro or f.read(1)` retirado",
     "Defensa en profundidad cuyo caso discriminante **no supe construir**. Si el fichero "
     "encoge entre el `stat` y la lectura, la aritmética de la frontera casi siempre falla "
     "sola y devuelve `False` igual; para que la guarda fuese la diferencia haría falta un "
     "fichero que encoja lo justo y cuyo prefijo nuevo cuadre con el hash remoto — no lo "
     "consigo de forma determinista y fabricarlo a la fuerza no probaría nada. **No se le "
     "atribuye garantía**: se conserva porque hace el fallo temprano y explícito, no porque "
     "esté demostrado que atrapa algo."),
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
    for nombre, motivo in SUPERVIVIENTES_DECLARADOS:
        print()
        print("[DECLARADO, no matado] " + nombre)
        print("  " + motivo)
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
