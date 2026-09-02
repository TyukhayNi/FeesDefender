"""Manifiesto de mutacion de `MEJORAS #136`. Ejecutable, no una afirmacion.

    python -m tests._mutantes_mejoras_136

Existe porque R23/H23-07 tenia razon: decir «catorce mutantes mueren cada uno por su
frontera» en un mensaje de commit **no es verificable**. Aqui estan los parches, el
comando y el test que debe ponerse rojo por cada uno; quien quiera comprobarlo lo corre.

## Como se lee el resultado

- **SOBREVIVE** = el contrato NO esta probado ahi. Es el hallazgo, no un fallo del arnes.
- **MAL APUNTADO** = el mutante mata tests de OTRA frontera, normalmente porque revienta
  el montaje en vez de violar el contrato. Con un matiz que costo una vuelta: si los
  muertos «de mas» dependen todos de la MISMA propiedad que el mutante ataca, el mutante
  esta bien y lo estrecho era la expectativa.

## Dos trampas medidas al construirlo

- **Muta desde el INDICE**: `git checkout -- .` restaura lo commiteado, asi que el arbol
  tiene que estar limpio antes de correr. Sin eso se pierde trabajo sin commitear.
- **Un mutante que retira una LLAMADA** (y no una comparacion) mata los tests que
  parchean esa llamada, y parece mal apuntado sin serlo. Muta la condicion, no la
  invocacion.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PY = sys.executable
FICHEROS = ("tests/test_registro_no_admite_el_canon.py",
            "tests/test_guard_copia_prestada.py",
            "tests/test_workspace_registry.py",
            "tests/test_workspace_resolver.py",
            "tests/test_workspace_adopcion.py")

#: FUERA del repo a proposito: el constructor del registro rechaza una raiz
#: bajo el proyecto, asi que un `--basetemp` dentro del arbol tumba 50 tests
#: que estan bien. Y CORTO, o MAX_PATH tumba otros que tambien lo estan.
_BASETEMP = "C:/t/m136"

CC = "core/casos/case_catalog.py"
WR = "core/casos/workspace_registry.py"
WA = "core/casos/workspace_adopcion.py"
WS = "core/casos/workspace_resolver.py"

#: `(nombre, fichero, ancla, sustituto, tests que DEBEN morir)`.
MUTANTES = [
    ("M01 la invariante de `_escribir` no muerde", WR,
     "            if clasificar_bajo(Path(e.local_path), raiz) == DENTRO:",
     "            if False:",
     {"test_la_invariante_muerde_aunque_la_politica_no_haya_mirado"}),

    ("M02 `alta` no exige clasificable", WR,
     "        self._exigir_clasificable(entrada)\n        for otra in self.cargar():",
     "        for otra in self.cargar():",
     {"test_alta_rechaza_lo_que_no_puede_clasificar"}),

    ("M03 `revalidar` no exige clasificable", WR,
     "        self._exigir_clasificable(dataclasses.replace(\n"
     "            halladas[0], local_path=Path(local_path)))\n",
     "",
     {"test_revalidar_rechaza_lo_que_no_puede_clasificar"}),

    ("M04 `verificar_adopcion` no rechaza el canon", WA,
     "    if bajo_catalogo(case_dir):",
     "    if False:",
     {"test_verificar_adopcion_rechaza_el_canon",
      "test_adoptar_el_canon_lanza_y_no_escribe_ni_entrada_ni_evento"}),

    ("M05 `_visibles` no oculta nada", WR,
     "        return [e for e in entradas\n"
     "                if clasificar_bajo(Path(e.local_path), raiz) != DENTRO]",
     "        return list(entradas)",
     {"test_cargar_descarta_la_entrada_canonica_heredada",
      "test_buscar_tampoco_la_devuelve", "test_el_resolver_no_la_ve",
      "test_es_copia_prestada_vuelve_a_ser_falsa"}),

    ("M06 `_visibles` oculta TAMBIEN lo indeterminado (la perdida de datos)", WR,
     "                if clasificar_bajo(Path(e.local_path), raiz) != DENTRO]",
     "                if clasificar_bajo(Path(e.local_path), raiz) == FUERA]",
     {"test_pero_NO_se_oculta_al_leer_el_registro",
      "test_el_registro_CONSERVA_lo_indeterminado"}),

    ("M07 el predicado compara CADENAS y no componentes", CC,
     "    if len(c) >= len(r) and c[:len(r)] == r:",
     "    if os.sep.join(c).startswith(os.sep.join(r)):",
     {"test_un_hermano_con_el_mismo_prefijo_sigue_estando_fuera"}),

    ("M08 el predicado no sanea el prefijo extendido", CC,
     '    if s.startswith("\\\\\\\\?\\\\"):\n        return s[4:]\n    return s',
     "    return s",
     {"test_con_el_CATALOGO_inexistente_solo_lo_salva_el_saneado_del_prefijo",
      "test_el_prefijo_extendido_clasifica_igual_que_la_ruta_normal",
      "test_un_destino_inexistente_con_prefijo_extendido_se_clasifica_dentro",
      "test_el_nombre_Volume_GUID_de_la_misma_carpeta"}),

    ("M09 el predicado no resuelve fisicamente (junction, GUID, 8.3)", CC,
     "        c = _componentes(os.path.realpath(str(candidata)))\n"
     "        r = _componentes(os.path.realpath(str(raiz)))",
     # Conserva la LLAMADA a `realpath` y descarta su resultado. Retirarla mataba
     # ademas al test del fallo cerrado, que la parchea para provocar el error: un
     # mutante que quita una invocacion parece mal apuntado sin serlo.
     "        c = _componentes(os.path.realpath(str(candidata)) and str(candidata))\n"
     "        r = _componentes(os.path.realpath(str(raiz)) and str(raiz))",
     {"test_junction_a_la_RAIZ", "test_junction_a_un_DESCENDIENTE",
      "test_y_un_hijo_DENTRO_de_esa_junction", "test_el_alias_tampoco_entra_por_alta",
      "test_el_nombre_Volume_GUID_de_la_misma_carpeta",
      "test_una_junction_al_catalogo_no_lo_saca_de_el",
      "test_una_junction_que_apunta_al_catalogo_tambien"}),

    ("M10 `_dentro_fisicamente` no falla cerrado", CC,
     "    except (OSError, ValueError):\n        return None\n"
     "    return len(c) >= len(r) and c[:len(r)] == r",
     "    except (OSError, ValueError):\n        return False\n"
     "    return len(c) >= len(r) and c[:len(r)] == r",
     {"test_si_no_se_puede_determinar_donde_cae_se_RECHAZA"}),

    ("M11 `bajo_catalogo` deja pasar lo indeterminado", CC,
     "    return clasificar_bajo(path, Path(config.settings.casos_root)) != FUERA",
     "    return clasificar_bajo(path, Path(config.settings.casos_root)) == DENTRO",
     {"test_indeterminado_cuenta_como_DENTRO_para_quien_autoriza",
      "test_si_no_se_puede_determinar_donde_cae_se_RECHAZA",
      "test_alta_rechaza_lo_que_no_puede_clasificar",
      "test_revalidar_rechaza_lo_que_no_puede_clasificar"}),

    ("M12 el resolver no filtra el registro INYECTADO", WS,
     "        locales = self._sin_canonicos(self.registry.buscar(ref))",
     "        locales = self.registry.buscar(ref)",
     {"test_un_registro_inyectado_no_cuela_el_canon",
      "test_pero_el_resolver_NO_lo_autoriza"}),

    ("M13 el resolver conserva en vez de AUTORIZAR (`!= DENTRO`)", WS,
     "                if clasificar_bajo(Path(e.local_path), raiz) == FUERA]",
     '                if clasificar_bajo(Path(e.local_path), raiz) != "dentro"]',
     {"test_pero_el_resolver_NO_lo_autoriza"}),

    ("M14 el constructor del registro vuelve a su definicion propia", WR,
     "            if clasificar_bajo(raiz, prohibida) != FUERA:",
     "            if _bajo(raiz, prohibida):",
     {"test_una_raiz_relativa_bajo_el_catalogo_se_rechaza",
      "test_una_junction_que_apunta_al_catalogo_tambien"}),
]


def _corre() -> set[str]:
    r = subprocess.run(
        [PY, "-m", "pytest", *FICHEROS, "-q", "--tb=no", "-p", "no:cacheprovider",
         "--basetemp=" + _BASETEMP, "-p", "no:randomly"],
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
