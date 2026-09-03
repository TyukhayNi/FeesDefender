"""Arnes de mutacion del Plan 5: un mutante por frontera del §3 del plan.

Uso: python -m tests._mutantes_plan5

Cada entrada muta UNA linea de produccion y declara el conjunto EXACTO de nodeids que
debe ponerse rojo. Se ejecuta el conjunto contractual completo y se comparan los
conjuntos: un mutante que mata de MENOS no prueba su frontera; uno que mata de MAS esta
mal apuntado y prueba otra cosa.

La rev. 1 de este arnes leia un booleano de un solo nodeid, asi que por construccion no
podia medir su propia regla — y con ella el mutante F12 sobrevivio (HA-09 de la R-A).

Restaura con `git checkout -- <fichero>`, que lee del INDICE: **commitea antes de correr.**
"""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: El conjunto contractual. Se ejecuta ENTERO por mutante, incluido el E2E: los caminos
#: por defecto de las etapas (sin inyeccion) solo se ejercitan alli.
SUITE = ("tests/test_apertura_v1_secuenciador.py",
         "tests/test_apertura_v1_etapas.py",
         "tests/test_apertura_v1_cableado.py",
         "tests/test_apertura_v1_estado.py",
         "tests/test_apertura_v1_e2e.py")

SEC = "tests/test_apertura_v1_secuenciador.py"
ETA = "tests/test_apertura_v1_etapas.py"
CAB = "tests/test_apertura_v1_cableado.py"
EST = "tests/test_apertura_v1_estado.py"
E2E = "tests/test_apertura_v1_e2e.py"

AV1 = "core/apertura_v1.py"
EST_MOD = "core/apertura_v1_estado.py"
CLI = "scripts/abrir_caso.py"
LOG = "core/intake_log.py"

# (id, fichero, texto_original, texto_mutado, {nodeids que DEBEN morir})
MUTANTES: list[tuple[str, str, str, str, set[str]]] = [
    ("F1", AV1,
     "            hubo_fallo = True\n            break",
     "            hubo_fallo = True",
     {f"{SEC}::test_f1_un_fallo_detiene_la_secuencia",
      f"{E2E}::test_e2e_un_fallo_del_crm_bloquea_y_la_sala_no_corre"}),

    ("F2", AV1,
     "    if hubo_fallo:\n        return EstadoV1.BLOQUEADO",
     "    if False:\n        return EstadoV1.BLOQUEADO",
     {f"{SEC}::test_un_fallo_bloquea_aunque_no_haya_pendientes",
      f"{SEC}::test_f2_un_fallo_deja_el_resultado_bloqueado",
      f"{E2E}::test_e2e_un_fallo_del_crm_bloquea_y_la_sala_no_corre"}),

    ("F3", AV1,
     "    pendientes: list[Pendiente] = [PENDIENTE_FUENTES_V3]",
     "    pendientes: list[Pendiente] = []",
     {f"{SEC}::test_f3_una_corrida_impecable_sigue_siendo_preparado_con_pendientes",
      f"{CAB}::test_una_corrida_completa_toca_TODAS_las_fases_de_v1",
      f"{E2E}::test_e2e_la_secuencia_recorre_las_tres_etapas_y_las_LLAMA",
      # Sin el pendiente permanente el estado pasa a `completo`, y el evento lo dice.
      f"{E2E}::test_e2e_el_evento_de_cierre_queda_en_el_log"}),

    ("F4", AV1,
     "        if hasta is not None and etapa.nombre == hasta:\n"
     "            parada = etapa.nombre\n            break",
     "        if hasta is not None and etapa.nombre == hasta:\n"
     "            parada = etapa.nombre",
     {f"{SEC}::test_f4_hasta_para_DESPUES_de_la_etapa_nombrada",
      f"{CAB}::test_f24_una_parada_pedida_enumera_las_etapas_que_no_corrieron",
      f"{E2E}::test_e2e_hasta_drive_no_consulta_el_crm_ni_el_ocr"}),

    ("F5", AV1,
     "    if hasta is not None and hasta not in nombres:\n        raise EtapaDesconocida(",
     "    if False:\n        raise EtapaDesconocida(",
     {f"{SEC}::test_f5_un_hasta_desconocido_es_error_y_no_corre_nada"}),

    ("F6", CLI,
     '            detalle="la consulta remota no se hizo: el pull devolvio `skipped` pese a "',
     '            detalle="`.pulled` presente, no se re-descargo: "',
     {f"{ETA}::test_f6_un_skipped_en_v1_es_fallo_porque_la_consulta_no_se_hizo"}),

    ("F7", CLI,
     '            res = _pull(ident.case_id, str(link["id"]), element=link["element"])',
     '            res = _pull(ident.case_id, str(link["id"]),\n'
     '                        element="expedientes_judiciales")',
     {f"{ETA}::test_f7_el_element_sale_del_link_y_nunca_del_default",
      f"{E2E}::test_e2e_la_secuencia_recorre_las_tres_etapas_y_las_LLAMA",
      f"{E2E}::test_e2e_el_evento_de_cierre_queda_en_el_log",
      f"{E2E}::test_e2e_es_punto_fijo_MATERIAL_y_no_solo_de_estado"}),
      # `test_e2e_un_fallo_del_crm...` NO muere aqui: su doble ignora el `element`, asi
      # que la rama del pull no cambia nada para el. Prediccion mia corregida al medir.

    ("F8", CLI,
     '        el = link.get("element")\n        if not el:',
     '        el = link.get("element") or _ELEMENT_JUDICIAL\n        if not el:',
     {f"{ETA}::test_f8_un_link_sin_element_es_fallo_y_no_se_adivina"}),

    ("F9", CLI,
     '            nombre="crm", estado="saltada",\n'
     '            detalle="sin expediente CRM registrado en _caso.md",',
     '            nombre="crm", estado="fallo",\n'
     '            detalle="sin expediente CRM registrado en _caso.md",',
     {f"{ETA}::test_f9_un_caso_sin_expediente_registrado_es_saltada_con_pendiente"}),

    ("F10", CLI,
     '    if status == "parcial":',
     '    if False:',
     {f"{ETA}::test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente[parcial-hecha-True]"}),

    ("F11", CLI,
     '    if status == "fallo":',
     '    if False:',
     {f"{ETA}::test_f11_atomizacion_en_fallo_bloquea_la_etapa"}),

    ("F12", CLI,
     '        detalle=("OCR hecho; sin correo que atomizar" if status is None\n'
     '                 else "OCR hecho; atomizacion ok"))',
     '        detalle=("OCR hecho; sin correo que atomizar" if status is None\n'
     '                 else "OCR hecho; atomizacion ok"),\n'
     '        pendientes=(av1.Pendiente(codigo="x", detalle="x"),))',
     {f"{ETA}::test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente[None-hecha-False]",
      f"{ETA}::test_f10_f12_el_status_de_atomizacion_gobierna_el_pendiente[ok-hecha-False]"}),

    ("F13", LOG,
     '    "apertura_v1_terminada",         # cierre de la secuencia de V1 con estado y pendientes\n',
     "",
     {f"{CAB}::test_f13_el_evento_de_cierre_esta_en_el_set_cerrado",
      f"{CAB}::test_el_evento_de_cierre_lleva_el_estado_y_los_pendientes",
      f"{E2E}::test_e2e_el_evento_de_cierre_queda_en_el_log"}),

    ("F14", CLI,
     "    return 1 if estado == av1.EstadoV1.BLOQUEADO else 0",
     "    return 0",
     {f"{CAB}::test_f14_un_resultado_bloqueado_sale_con_codigo_no_cero"}),

    ("F15", CLI,
     "    _intake = intake or _intake_drive_ev",
     "    _intake = intake or (\n"
     "        lambda i, c, f, t, **k: intake_drive.pull_drive_ev(i.case_id, f, t))",
     {f"{ETA}::test_f15_bis_el_camino_POR_DEFECTO_pasa_por_la_custodia",
      f"{E2E}::test_e2e_la_secuencia_recorre_las_tres_etapas_y_las_LLAMA",
      f"{E2E}::test_e2e_el_evento_de_cierre_queda_en_el_log",
      f"{E2E}::test_e2e_es_punto_fijo_MATERIAL_y_no_solo_de_estado",
      f"{E2E}::test_e2e_un_fallo_del_crm_bloquea_y_la_sala_no_corre",
      f"{E2E}::test_e2e_hasta_drive_no_consulta_el_crm_ni_el_ocr"}),

    ("F16", CLI,
     "        res = _intake(ident, case_dir, folder_id, team_id, dry_run=False, force=True)",
     "        res = _intake(ident, case_dir, folder_id, team_id, dry_run=False, force=False)",
     {f"{ETA}::test_f16_en_v1_el_pull_consulta_en_cada_ronda",
      f"{E2E}::test_e2e_la_secuencia_recorre_las_tres_etapas_y_las_LLAMA",
      f"{E2E}::test_e2e_el_evento_de_cierre_queda_en_el_log",
      f"{E2E}::test_e2e_es_punto_fijo_MATERIAL_y_no_solo_de_estado",
      f"{E2E}::test_e2e_un_fallo_del_crm_bloquea_y_la_sala_no_corre",
      f"{E2E}::test_e2e_hasta_drive_no_consulta_el_crm_ni_el_ocr"}),

    ("F17", CLI,
     '    if errores:\n        return "fallo", f"el pull devolvio errores: {errores}", ()',
     '    if False:\n        return "fallo", f"el pull devolvio errores: {errores}", ()',
     {f"{ETA}::test_f17_f20_el_resultado_del_pull_gobierna_la_etapa[kw0-fallo-None]",
      f"{E2E}::test_e2e_un_fallo_del_crm_bloquea_y_la_sala_no_corre"}),

    ("F18", CLI,
     '    if getattr(res, "blocked_legacy_v1", False):',
     '    if False:',
     {f"{ETA}::test_f17_f20_el_resultado_del_pull_gobierna_la_etapa[kw1-fallo-None]"}),

    ("F19", CLI,
     "    if fallidos:",
     "    if False:",
     {f"{ETA}::test_f17_f20_el_resultado_del_pull_gobierna_la_etapa[kw2-hecha-crm_documentos_fallidos]"}),

    ("F20", CLI,
     '    if int(getattr(res, "documents_total_crm", 0) or 0) == 0:',
     '    if False:',
     {f"{ETA}::test_f17_f20_el_resultado_del_pull_gobierna_la_etapa[kw3-saltada-crm_gestor_vacio]"}),

    ("F21", CLI,
     "        if el not in ELEMENTS_CRM:",
     "        if False:",
     {f"{ETA}::test_f21_un_element_fuera_del_vocabulario_es_fallo"}),

    ("F22", CLI,
     "        if el == _ELEMENT_JUDICIAL:",
     "        if False:",
     {f"{ETA}::test_f22_un_element_judicial_aborta_en_v1"}),

    ("F23", CLI,
     "    if hasta is not None and hasta not in ETAPAS_V1:",
     "    if False:",
     {f"{CAB}::test_f23_el_vocabulario_de_hasta_se_valida_antes_de_todo_efecto"}),

    ("F24", AV1,
     "    pendientes.extend(\n"
     '        Pendiente(codigo=f"etapa_no_ejecutada:{n}",',
     "    _ = (\n"
     '        Pendiente(codigo=f"etapa_no_ejecutada:{n}",',
     {f"{CAB}::test_f24_una_parada_pedida_enumera_las_etapas_que_no_corrieron"}),

    ("F25", CLI,
     "                registrar_cierre_v1(case_dir, ident, resultado_v1)",
     "                registrar_cierre_v1(case_dir, ident, resultado_v1)\n"
     "                raise typer.Exit(code=0)",
     {f"{CAB}::test_f25_la_rama_v1_no_sale_del_proceso_dentro_del_bloque_de_mutex"}),

    ("F26", CLI,
     "    except (CaseBusy, MutexPerdido) as exc:\n"
     "        return av1.EstadoV1.BLOQUEADO, str(exc)",
     "    except (CaseBusy, MutexPerdido):\n        raise",
     {f"{CAB}::test_f26_case_busy_se_traduce_a_bloqueado_y_no_a_una_traza"}),

    ("F27", EST_MOD,
     "        os.replace(tmp, f)",
     '        f.write_text(cuerpo, encoding="utf-8")',
     {f"{EST}::test_f27_la_escritura_es_atomica_y_lleva_id_de_ronda",
      f"{EST}::test_no_queda_temporal_tras_una_escritura_correcta"}),

    ("F28", EST_MOD,
     "    def sin_cerrar(self) -> bool:\n        return self.terminada is None",
     "    def sin_cerrar(self) -> bool:\n        return False",
     {f"{EST}::test_f28_una_ronda_sin_cerrar_se_detecta"}),
]


def _rojos() -> set[str]:
    """Conjunto de nodeids en rojo tras correr la suite entera.

    Por JUnit XML y no por el resumen: el resumen no sobrevive a una tuberia, y este repo
    ya tiene esa leccion escrita.
    """
    xml = RAIZ / ".mutantes.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", *SUITE, "-q", "--no-header",
         "-p", "no:randomly", "-p", "no:cacheprovider", f"--junit-xml={xml}"],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    if not xml.exists():
        raise RuntimeError("pytest no genero el XML: el arnes no puede medir nada")
    rojos = set()
    for tc in ET.parse(xml).iter("testcase"):
        if tc.find("failure") is None and tc.find("error") is None:
            continue
        # Por `classname` y NO por `file`: en este pytest el atributo `file` viene VACIO,
        # asi que los nodeids salian como "::test_x" y NINGUN conjunto podia coincidir.
        # El arnes declaraba 28 mutantes mal apuntados cuando los 28 mataban lo correcto:
        # un arnes roto que dictamina sobre tests buenos.
        modulo = (tc.get("classname") or "").split(".")
        archivo = "/".join(modulo) + ".py" if modulo != [""] else ""
        rojos.add(f"{archivo}::{tc.get('name')}")
    xml.unlink()
    return rojos


def main() -> int:
    base = _rojos()
    if base:
        print(f"ARNES INUTIL: la suite ya tiene {len(base)} rojo(s) sin mutar: "
              f"{sorted(base)}")
        return 1

    malos = []
    for ident, rel, viejo, nuevo, esperados in MUTANTES:
        f = RAIZ / rel
        original = f.read_text(encoding="utf-8")
        if viejo not in original:
            print(f"{ident}: ARNES ROTO - el texto a mutar no esta en {rel}")
            malos.append(ident)
            continue
        f.write_text(original.replace(viejo, nuevo, 1), encoding="utf-8")
        try:
            rojos = _rojos()
        finally:
            f.write_text(original, encoding="utf-8")
        if rojos == esperados:
            print(f"{ident}: MUERTO por su frontera ({len(rojos)} rojo/s)")
            continue
        if not rojos:
            print(f"{ident}: VIVO - nada se puso rojo")
        else:
            faltan = sorted(esperados - rojos)
            sobran = sorted(rojos - esperados)
            if faltan:
                print(f"{ident}: MATA DE MENOS - no murio {faltan}")
            if sobran:
                print(f"{ident}: MAL APUNTADO - mata de mas: {sobran}")
        malos.append(ident)

    if malos:
        print(f"\n{len(malos)} mutante(s) con problema: {malos}")
        return 1
    print(f"\n{len(MUTANTES)}/{len(MUTANTES)} mutantes muertos, cada uno SOLO por su "
          f"frontera.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
