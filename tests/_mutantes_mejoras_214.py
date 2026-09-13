"""Arnés de mutación de `MEJORAS #214` — el recorrido tolerante de custodia.

**Por qué vive en el repo y no en un scratchpad.** En la R1 del 2026-09-13 el autor
afirmó «14 mutantes, 14 muertos» y el revisor **no pudo verificarlo**: las definiciones
estaban fuera del objeto revisado, así que la cifra quedó declarada `SIN VERIFICAR`. Una
afirmación que nadie puede comprobar no es un dato. Aquí sí lo es: cualquiera corre este
módulo y ve morir a cada mutante, o lo ve sobrevivir.

Precedente en la casa: `tests/_mutantes_mejoras_136.py`.

**Qué comprueba, y el segundo punto es el que suele faltar:**

1. que cada mutante mate al test que se le apunta;
2. que ANTES de mutar ese test estuviera **verde** — si no, el rojo no lo causó el
   mutante y el arnés se estaría acreditando a sí mismo. Es el defecto que ya se midió en
   `feedback-el-arnes-de-mutacion-tiene-sus-propios-defectos`.

**No es un test de pytest y no corre en la suite** (el nombre empieza por `_`): muta
ficheros de producción en el árbol, lo cual es exactamente lo que la casa prohíbe a un
test. Se ejecuta a mano, con el árbol limpio:

    python -m tests._mutantes_mejoras_214

Restaura siempre el fichero en un `finally`, y sale con código 1 si algún mutante
sobrevive o si el arnés se encuentra roto.
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
T = "tests/test_hash_tree_tolerante.py"
OBJETIVO = "scripts/abrir_caso.py"

#: (nombre, texto original, texto mutado, test que DEBE ponerse rojo).
#: M01-M14 son del autor (pre-R1). M15-M22 salen de los hallazgos de la R1 de Codex:
#: **M15 y M16 son literalmente los dos mutantes que Codex construyó y que sobrevivían**
#: a los 23 tests de entonces (H-10 y H-11), o sea el control positivo de que su hallazgo
#: está cerrado. Los demás cubren los remedios de H-01 a H-09 y H-12.
MUTANTES: list[tuple[str, str, str, str]] = [
    ("M01 el evento no lleva `sin_verificar`",
     '        if sin_verificar:\n            details["sin_verificar"] = [',
     '        if False:\n            details["sin_verificar"] = [',
     "test_a13_un_sin_verificar_llega_al_evento_forense"),

    ("M02 la etapa no emite el Pendiente",
     "    sin_verificar = getattr(res, \"custodia_sin_verificar\", ()) or ()\n    if not sin_verificar:",
     "    sin_verificar = getattr(res, \"custodia_sin_verificar\", ()) or ()\n    if True:",
     "test_a15_un_sin_verificar_llega_al_Pendiente_de_la_etapa"),

    ("M03 la custodia no ADJUNTA al resultado",
     "    return dataclasses.replace(res, custodia_sin_verificar=arbol.sin_verificar)",
     "    return res",
     "test_a19_la_custodia_ADJUNTA_lo_no_verificado_al_resultado_que_devuelve"),

    ("M04 la ambiguedad elige el primero",
     "    if len(candidatos) > 1:\n        return (",
     "    if False:\n        return (",
     "test_a7_dos_candidatos_al_renombrado_son_ambiguedad_y_no_se_elige"),

    ("M05 el recorrido vuelve a tragarse los errores de directorio",
     "    for dirpath, dirnames, filenames in os.walk(root, onerror=_anotar_dir_ilegible):",
     "    for dirpath, dirnames, filenames in os.walk(root):",
     "test_a8_un_directorio_irrecorrible_se_declara_y_no_cuenta_cero"),

    ("M06 adopta un candidato que YA estaba listado",
     "                  and os.path.normcase(str(q)) not in listadas]",
     "                  ]",
     "test_a4_el_candidato_tiene_que_ser_NUEVO_no_uno_que_ya_estaba_listado"),

    ("M07 un fichero ilegible se omite en silencio",
     "            except OSError as err:\n                sin_verificar.append(brain.FicheroSinVerificar(\n                    clave=clave, motivo=repr(err)))",
     "            except OSError:\n                pass",
     "test_a6_un_error_de_lectura_que_no_es_ausencia_tambien_se_declara"),

    ("M08 el renombrado no se anota",
     "                renombrados.append((clave, clave_efectiva))",
     "                pass",
     "test_a2_el_renombrado_queda_anotado_con_las_dos_claves"),

    ("M09 el protocolo se decide sobre la clave VIEJA",
     "                if es_fichero_de_protocolo(clave_efectiva):\n                    continue",
     "                if es_fichero_de_protocolo(clave):\n                    continue",
     "test_a11_el_protocolo_se_decide_sobre_la_clave_EFECTIVA"),

    ("M10 el evento se ensucia con listas vacias",
     '        if sin_verificar:\n            details["sin_verificar"] = [\n                {"clave": f.clave, "motivo": f.motivo} for f in sin_verificar]',
     '        details["sin_verificar"] = [\n            {"clave": f.clave, "motivo": f.motivo} for f in sin_verificar]',
     "test_a14_sin_incidencias_el_evento_no_se_ensucia"),

    ("M11 la etapa inventa un Pendiente siempre",
     "    if not sin_verificar:\n        return ()",
     "    if False:\n        return ()",
     "test_a16_sin_incidencias_la_etapa_no_inventa_pendientes"),

    ("M12 la relectura fallida se traga el error",
     '    except OSError as err:\n        return f"no se pudo releer el directorio tras el renombrado: {err!r}"',
     "    except OSError:\n        return None",
     "test_a20_si_no_se_puede_releer_el_directorio_se_declara"),

    ("M13 el reaparecido ilegible se declara con la clave VIEJA",
     "                except OSError as err2:\n                    sin_verificar.append(brain.FicheroSinVerificar(\n                        clave=clave_efectiva, motivo=repr(err2)))",
     "                except OSError as err2:\n                    sin_verificar.append(brain.FicheroSinVerificar(\n                        clave=clave, motivo=repr(err2)))",
     "test_a21_si_el_reaparecido_tampoco_se_deja_leer_se_declara_bajo_su_clave_efectiva"),

    ("M14 la raiz ilegible se nombra con el relative_to ingenuo",
     "        clave = prefijo if ruta == root else _clave(ruta)",
     "        clave = _clave(ruta)",
     "test_a22_si_la_RAIZ_entera_es_irrecorrible_se_declara_con_su_propia_clave"),

    # --- Los dos de Codex, que sobrevivian a los 23 tests originales (R1/H-10, H-11) ---
    ("M15 [Codex R1/H-10] solo viaja la PRIMERA incidencia",
     "        sin_verificar=tuple(sin_verificar),",
     "        sin_verificar=tuple(sin_verificar)[:1],",
     "test_r1_h10_las_incidencias_viajan_TODAS_no_solo_la_primera"),

    ("M16 [Codex R1/H-11] el motivo se borra al escribir el evento del pull fallido",
     '                details["sin_verificar"] = [\n                    {"clave": f.clave, "motivo": f.motivo} for f in arbol.sin_verificar]',
     '                details["sin_verificar"] = [\n                    {"clave": f.clave, "motivo": ""} for f in arbol.sin_verificar]',
     "test_r1_h11_el_evento_del_pull_fallido_CONSERVA_el_motivo"),

    # --- Los remedios de la R1 ---
    ("M17 [R1/H-01] la comparacion del listado vuelve a ser sensible a la caja",
     "        listadas = {os.path.normcase(str(d / n)) for n in filenames}",
     "        listadas = {str(d / n) for n in filenames}",
     "test_r1_h01_un_candidato_YA_LISTADO_no_se_adopta_aunque_cambie_la_caja"),

    ("M18 [R1/H-09] el criterio del candidato vuelve al stem",
     "                  if os.path.normcase(q.name).startswith(prefijo_nombre)",
     "                  if q.stem == p.name",
     "test_r1_h09b_un_renombrado_con_DOS_extensiones_tambien_se_reconoce"),

    ("M19 [R1/H-02] el evento vuelve a exigir depositables",
     "    if plan.con_sha or sin_verificar or renombrados:",
     "    if plan.con_sha:",
     "test_r1_h02_el_evento_se_escribe_aunque_NO_haya_ni_un_depositable"),

    ("M20 [R1/H-03] el stat vuelve a no tolerar la carrera",
     "        try:\n            size = (raiz / k).stat().st_size\n        except OSError as err:",
     "        try:\n            size = (raiz / k).stat().st_size\n        except ZeroDivisionError as err:",
     "test_r1_h03_la_carrera_en_el_STAT_posterior_no_tumba_la_etapa"),

    ("M21 [R1/H-04] una raiz ilegible vuelve a ser una raiz vacia",
     "    except OSError as err:\n        return brain.ArbolLocal(hashes={}, sin_verificar=(\n            brain.FicheroSinVerificar(clave=prefijo, motivo=repr(err)),))",
     "    except OSError:\n        return brain.ArbolLocal(hashes={})",
     "test_r1_h04_una_raiz_que_NO_SE_PUDO_MIRAR_no_es_una_raiz_vacia"),

    ("M22 [R1/H-07, H-08] la etapa vuelve a calcular los pendientes al final",
     "    pendientes = _pendientes_de_custodia(res)",
     "    pendientes = ()",
     "test_r1_h07_un_fallo_del_RECUENTO_no_borra_las_incidencias_ya_conocidas"),

    ("M23 [R1/H-12] el aviso vuelve a afirmar el hash",
     'f"la custodia usa el nombre efectivo")',
     'f"se hasheo bajo el nombre efectivo")',
     "test_r1_h12_el_aviso_no_afirma_haber_hasheado_lo_que_no_se_leyo"),
]


def _corre(test: str) -> int:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:randomly",
         f"{T}::{test}"],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    return r.returncode


def main() -> int:
    objetivo = RAIZ / OBJETIVO
    fallos: list[str] = []
    for nombre, viejo, nuevo, test in MUTANTES:
        s = io.open(objetivo, encoding="utf-8").read()
        if viejo not in s:
            print(f"[ARNES ROTO] {nombre}: el texto original ya no esta en {OBJETIVO}")
            fallos.append(nombre)
            continue
        if _corre(test) != 0:
            print(f"[ARNES ROTO] {nombre}: {test} YA estaba rojo sin mutar")
            fallos.append(nombre)
            continue
        io.open(objetivo, "w", encoding="utf-8", newline="\n").write(
            s.replace(viejo, nuevo, 1))
        try:
            rc = _corre(test)
        finally:
            io.open(objetivo, "w", encoding="utf-8", newline="\n").write(s)
        if rc == 0:
            print(f"[SUPERVIVIENTE] {nombre}  <- {test} no lo mata")
            fallos.append(nombre)
        else:
            print(f"[muerto] {nombre}")

    print()
    print(f"{len(MUTANTES)} mutantes, {len(MUTANTES) - len(fallos)} muertos.")
    print("SUPERVIVIENTES/ROTOS:", ", ".join(fallos) if fallos else "ninguno")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
