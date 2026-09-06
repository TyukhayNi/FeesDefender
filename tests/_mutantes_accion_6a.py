"""Manifiesto de mutacion del filtro de ruido (accion 6a) y de `MEJORAS #168`.

    python -m tests._mutantes_accion_6a

Ejecutable, no una afirmacion: decir «ocho mutantes mueren cada uno por su frontera»
en un mensaje de commit no es verificable. Aqui estan los parches, el comando y los
tests que deben ponerse rojos.

## Como se lee

- **SOBREVIVE** = el contrato NO esta probado ahi. Es el hallazgo, no un fallo del arnes.
- **MAL APUNTADO** = mata tests de OTRA frontera. Salvo que los muertos «de mas»
  dependan todos de la MISMA propiedad, en cuyo caso lo estrecho era la expectativa.

## Las dos fronteras que este arnes existe para separar

`M01` (no excluye) y `M03` (excluye pero marca el gid como exportado) atacan
propiedades DISTINTAS que un solo mutante confundiria: *excluir* y *poder deshacerlo*.
Sin `M03`, un filtro que perdiera correo para siempre pasaria los mismos tests.

**Trampa heredada del arnes de `#136`:** `git checkout -- .` restaura desde el INDICE,
asi que el arbol tiene que estar limpio antes de correr o se pierde lo no commiteado.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PY = sys.executable
FICHEROS = ("tests/test_email_export_filtro_ruido.py",
            "tests/test_email_export_r1_remediaciones.py")

EE = "core/email_export.py"

#: `(nombre, fichero, ancla, sustituto, tests que DEBEN morir)`.
MUTANTES = [
    ("M01 el filtro no excluye nada", EE,
     "                if regla is not None:",
     "                if False:",
     {"test_el_ruido_no_se_escribe_y_lo_del_caso_si",
      "test_lo_excluido_queda_en_el_report_con_su_regla",
      "test_la_exclusion_es_REVERSIBLE_el_gid_no_entra_en_el_indice",
      "test_el_evento_durable_dice_que_se_excluyo_y_por_que",
      "test_el_buzon_de_facturacion_EN_COPIA_se_caza_end_to_end"}),

    ("M02 `parse_headers` vuelve a ser ciego al `cc`", EE,
     '    for name in ("date", "subject", "from", "to", "cc", "message-id"):',
     '    for name in ("date", "subject", "from", "to", "message-id"):',
     {"test_el_buzon_de_facturacion_EN_COPIA_se_caza_end_to_end"}),

    ("M03 excluye, pero marca el gid como EXPORTADO (pierde el correo)", EE,
     '                        "regla": regla,\n                    })\n                    continue',
     '                        "regla": regla,\n                    })\n'
     "                    nuevos_gids.append(gid)\n                    continue",
     {"test_la_exclusion_es_REVERSIBLE_el_gid_no_entra_en_el_indice"}),

    # --- Fronteras que la R1 destapo (una por hallazgo remediado) ------------
    ("M10 los excluidos contaminan `vistos` (R1/H-06)", EE,
     '                    continue

            mid = (cabeceras',
     '                    vistos.add((cabeceras.get("message-id") or "").strip().strip("<>"))
'
     '                    continue

            mid = (cabeceras',
     {"test_el_ruido_no_contamina_la_dedup_del_correo_legitimo"}),

    ("M11 el destinatario vuelve a ser una SUBCADENA (R1/H-05)", EE,
     "    return any(addr.strip().lower() == buzon
"
     "               for _, addr in getaddresses(crudos) if addr)",
     "    return buzon in ' '.join(crudos).lower()",
     {"test_H05_el_buzon_en_el_NOMBRE_MOSTRADO_no_excluye"}),

    ("M12 `gobernanza_interna` deja de exigir `legal` (R1/H-03)", EE,
     r'_RE_GOBERNANZA = re.compile(r"acta.{0,40}?cfo\s*[+y&/-]?\s*legal")',
     r'_RE_GOBERNANZA = re.compile(r"acta.*cfo")',
     {"test_H03_asuntos_PROBATORIOS_que_se_excluian_ya_no"}),

    ("M13 `auditoria` pierde la frontera de palabra (R1/H-03)", EE,
     r'    r"|cartas?\s+(?:de|a|para)\s+(?:los\s+|las\s+)?auditor(?:es)?",',
     r'    r"|cartas?\s+(?:de|a|para)\s+(?:los\s+|las\s+)?auditor",',
     {"test_H03_asuntos_PROBATORIOS_que_se_excluian_ya_no"}),

    ("M14 el lote vuelve a ser cualquier DESCENDIENTE de 00_Input (R1/H-02)", EE,
     "    return fisico.parent == raiz and fisico == raiz / dest.name",
     "    return raiz in fisico.parents",
     {"test_H02_un_lote_ANIDADO_bajo_00_Input_no_se_traza"}),

    ("M15 el evento vuelve a salir de la raiz FISICA (R1/H-04)", EE,
     "            _raiz_logica_de(case_id) or case_id,",
     "            (_input_root_de(case_id) or Path(case_id)).parent,",
     {"test_H04_el_evento_llega_al_caso_aunque_la_raiz_se_resuelva_a_otro_sitio"}),

    ("M16 el aplanado vuelve a ser una puerta sin filtro (R1/H-01)", EE,
     "        regla = clasificar_ruido(cab_hijo)
        if regla is not None:",
     "        regla = clasificar_ruido(cab_hijo)
        if False:",
     {"test_H01_el_hijo_anidado_de_ruido_NO_se_extrae_como_fichero",
      "test_H01_el_padre_entra_INTEGRO_y_se_avisa",
      "test_H01_transportado_y_excluido_son_LISTAS_DISTINTAS"}),

    ("M17 el rescate por enlace vuelve a depositar sin filtrar (R1/H-01)", EE,
     "    regla = clasificar_ruido(cabeceras)
    if regla is not None:
"
     "        # R1/H-01: era la otra puerta trasera.",
     "    regla = clasificar_ruido(cabeceras)
    if False:
"
     "        # R1/H-01: era la otra puerta trasera.",
     {"test_H01_un_mensaje_rescatado_por_ENLACE_pasa_por_el_filtro"}),

    ("M04 la conjuncion del repositorio se rompe: el buzon solo ya excluye", EE,
     '        if m and not any(m.group(g).strip() for g in ("sr", "mr", "contrario")):',
     "        if True:",
     {"test_repositorio_con_refs_LLENAS_no_se_excluye"}),

    ("M05 la regex del CRM pierde el separador « · »", EE,
     r'    r"S/R:(?P<sr>[^·]*)·\s*M/R:(?P<mr>[^·]*)·.*?Contrario:(?P<contrario>.*)$",',
     r'    r"S/R:(?P<sr>[^|]*)\|\s*M/R:(?P<mr>[^|]*)\|.*?Contrario:(?P<contrario>.*)$",',
     # Los cuatro de integracion entran en la expectativa tras verlo correr: NO es un
     # mutante mal apuntado, es que la expectativa era estrecha. Los cuatro usan
     # `_raws_mixtos()`, que lleva un `g-repo`; sin el separador esa regla deja de
     # disparar y los cuatro cuentan 2 exclusiones donde esperaban 3. Todos dependen
     # de la MISMA propiedad que el mutante ataca, que es el criterio del arnes de #136.
     {"test_repositorio_con_refs_vacias_se_excluye",
      "test_el_ruido_no_se_escribe_y_lo_del_caso_si",
      "test_lo_excluido_queda_en_el_report_con_su_regla",
      "test_la_exclusion_es_REVERSIBLE_el_gid_no_entra_en_el_indice",
      "test_el_evento_durable_dice_que_se_excluyo_y_por_que"}),

    ("M06 `gobernanza_interna` se conforma con la palabra «acta»", EE,
     r'_RE_GOBERNANZA = re.compile(r"\bacta\b.*\bcfo\b")',
     r'_RE_GOBERNANZA = re.compile(r"\bacta\b")',
     {"test_asuntos_del_caso_que_rozan_las_reglas_NO_se_excluyen"}),

    ("M07 el evento durable no se emite", EE,
     "    if case_id and report.excluidos_ruido:",
     "    if False:",
     {"test_el_evento_durable_dice_que_se_excluyo_y_por_que"}),

    # `MEJORAS #168`
    ("M08 `_cae_bajo` compara NOMBRES en vez de la ruta fisica", EE,
     "        rel = hijo.resolve().relative_to(raiz)",
     "        rel = Path(hijo.name)",
     {"test_destino_externo_con_nombre_de_lote_no_entra_en_el_M9"}),

    ("M09 el destino externo se traza igual (la omision no se declara)", EE,
     "    if case_id and dest.exists() and bajo_input:",
     "    if case_id and dest.exists():",
     {"test_destino_externo_con_nombre_de_lote_no_entra_en_el_M9"}),
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
