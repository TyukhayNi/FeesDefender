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
FICHEROS = ("tests/test_email_export_filtro_ruido.py",)

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

    ("M04 la conjuncion del repositorio se rompe: el buzon solo ya excluye", EE,
     '        if m and not any(m.group(g).strip() for g in ("sr", "mr", "contrario")):',
     "        if True:",
     {"test_repositorio_con_refs_LLENAS_no_se_excluye"}),

    ("M05 la regex del CRM pierde el separador « · »", EE,
     r'    r"S/R:(?P<sr>[^·]*)·\s*M/R:(?P<mr>[^·]*)·.*?Contrario:(?P<contrario>.*)$",',
     r'    r"S/R:(?P<sr>[^|]*)\|\s*M/R:(?P<mr>[^|]*)\|.*?Contrario:(?P<contrario>.*)$",',
     {"test_repositorio_con_refs_vacias_se_excluye"}),

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
