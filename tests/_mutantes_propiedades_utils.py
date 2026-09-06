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

import atexit
import dataclasses
import os
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
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
#: **Y sobre por que `test_normalize_es_phone_DEVUELVE_EL_NUMERO` aparece en CUATRO
#: mutantes (M01, M02, M10, M11).** Tampoco es laxitud, y es la misma leccion en su forma
#: mas util: esa propiedad **es el contrato entero** de `normalize_es_phone` —dado un
#: telefono espanol bien formado, devuelve sus nueve digitos—, asi que muere con
#: cualquier mutante que toque el recorte de prefijos. Una propiedad de contrato que
#: muriera con UN solo mutante seria una propiedad estrecha, no un mutante bien apuntado.
#:
#: **El patron que hay detras de las dos notas, y que me costo cinco veces verlo en una
#: sola sesion:** cada vez que el informe decia «MAL APUNTADO» yo ampliaba el `esperado`
#: del mutante concreto que aparecia, y el siguiente volvia a salir por lo mismo. Lo que
#: fallaba no era el caso: era que **un `esperado` describe la FRONTERA que el mutante
#: ataca, y varios tests pueden vigilar la misma frontera desde sitios distintos.**
#:
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
      "test_normalize_es_phone_nunca_devuelve_prefijo_de_pais",
      "test_normalize_es_phone_DEVUELVE_EL_NUMERO"}),

    ("M02 `normalize_es_phone` deja de reconocer el prefijo `0034`", U,
     '        elif s.startswith("0034"):\n            s = s[4:]\n',
     "",
     {"test_normalize_es_phone_nunca_devuelve_prefijo_de_pais",
      "test_normalize_es_phone_DEVUELVE_EL_NUMERO"}),

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
     # El segundo test lo añadio la R1 de Codex (H-02), y por la MISMA razon que M05 y
     # M07: al quitar el rechazo de vacio, `exigir_componente_de_ruta("")` devuelve `""` y
     # viola tambien la propiedad de lo aceptado. Arregle M05 y M07 cuando el informe
     # anterior me los señalo y **no arregle la propiedad de la que eran ejemplo**, asi
     # que M06 volvio a salir rojo por lo mismo. Remediar el ejemplo y no la frontera, por
     # cuarta vez en la misma sesion.
     {"test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas",
      "test_lo_que_pasa_el_guard_es_un_solo_componente"}),

    ("M07 la guarda de `.` / `..` desaparece", U,
     '    if valor.strip() in (".", ".."):',
     "    if False:",
     {"test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas",
      "test_lo_que_pasa_el_guard_es_un_solo_componente"}),

    ("M08 la guarda de espacios al borde desaparece (el H-03 del andamiaje parcial)", U,
     "    if valor != valor.strip():",
     "    if False:",
     # `test_el_guard_rechaza_el_vacio_y_las_posiciones_relativas` NO puede estar aqui, y
     # la R1 de Codex lo demostro ejecutandolo: sus ocho entradas
     # ("", " ", "   ", "\t", ".", "..", " . ", " .. ") las rechaza ANTES la guarda de
     # vacio o la de `.`/`..`, asi que ninguna llega a la de espacios. Era una expectativa
     # **imposible**, no solo improbable, y el arnes no la denunciaba porque exigia que
     # muriera ALGUNO de los esperados, no todos.
     {"test_lo_que_pasa_el_guard_es_un_solo_componente"}),

    ("M09 la guarda de caracteres de control desaparece", U,
     "    if any(ord(c) < 32 for c in valor):",
     "    if False:",
     {"test_lo_que_pasa_el_guard_es_un_solo_componente",
      "test_el_guard_rechaza_lo_que_no_puede_ser_un_componente"}),

    # --- Los tres que la R1 de Codex (H-04) encontro SOBREVIVIENDO ------------
    # No los invento el revisor: los ejecuto y midio que mis propiedades pasaban con la
    # funcion rota. Los tres atacan la misma frontera —**yo habia escrito solo la mitad
    # negativa del contrato**— y los tres mueren ahora contra las propiedades positivas.
    ("M10 `normalize_es_phone` devuelve SIEMPRE cadena vacia (la guarda inerte)", U,
     "    if not raw:\n        return raw\n"
     '    s = _TEL_SEPARADORES.sub("", raw)',
     '    return ""\n'
     "    if not raw:\n        return raw\n"
     '    s = _TEL_SEPARADORES.sub("", raw)',
     {"test_normalize_es_phone_DEVUELVE_EL_NUMERO"}),

    ("M11 desaparece la rama del prefijo `34` desnudo con once digitos", U,
     '        elif s.startswith("34") and len(s) == 11:\n            s = s[2:]\n',
     "",
     {"test_normalize_es_phone_nunca_devuelve_prefijo_de_pais",
      "test_normalize_es_phone_DEVUELVE_EL_NUMERO"}),

    ("M12 `exigir_componente_de_ruta` RECHAZA el universo entero", U,
     '    if not (valor or "").strip():\n'
     '        raise ValueError(f"{campo} no puede estar vacío.")\n',
     '    raise ValueError(f"{campo}: mutante que rechaza todo.")\n'
     '    if not (valor or "").strip():\n'
     '        raise ValueError(f"{campo} no puede estar vacío.")\n',
     {"test_el_guard_ACEPTA_un_componente_valido"}),

    # De R2 (H-10). El revisor lo aplico y **las diez propiedades pasaron**: mi generador
    # concatenaba siempre dos bordes, asi que nunca producia un nombre de un caracter y un
    # rechazo de todos ellos era invisible. El hueco no estaba en un aserto: estaba en la
    # forma de la estrategia, que es donde no se mira.
    ("M13 `exigir_componente_de_ruta` rechaza los nombres de UN caracter", U,
     '    if not (valor or "").strip():\n'
     '        raise ValueError(f"{campo} no puede estar vacío.")\n',
     "    if len(valor) == 1:\n"
     '        raise ValueError(f"{campo}: mutante que rechaza un solo caracter.")\n'
     '    if not (valor or "").strip():\n'
     '        raise ValueError(f"{campo} no puede estar vacío.")\n',
     {"test_el_guard_ACEPTA_un_componente_valido"}),
]


@dataclasses.dataclass(frozen=True)
class Corrida:
    """Una ejecucion, con los TRES estados que el arnes confundia en uno.

    La version anterior devolvia un `set` de nombres sacados de las lineas `FAILED ` del
    stdout, y eso hace **indistinguible** un verde legitimo de:

      - un fichero que no existe (pytest sale con 5, «no tests collected», y el set es
        vacio: identico a «todo verde»). Reproducido por la R1 (H-03, caso 1);
      - una ejecucion PARCIAL: con `PYTEST_ADDOPTS='-x'` heredado del entorno, pytest para
        en el primer rojo y los ejemplos que habrian matado al mutante **no llegan a
        correr**, asi que un mutante `AMBOS` se rotula `SOLO LA PROPIEDAD`. Reproducido
        por la R1 (H-03, caso 2) — y esa etiqueta es la medicion estrella del arnes;
      - un error de coleccion, que es lo que pasa si el mutante rompe la sintaxis.

    Se mide por **JUnit XML** y no por el stdout: da el conjunto ejecutado, su tamaño y el
    estado de cada test. Es ademas la convencion del repo para contar (`DEAD_ENDS.md`
    §«totales de la terminal»).
    """
    rojos: frozenset[str]
    total: int
    codigo: int
    valida: bool
    motivo: str = ""


def _corre(total_esperado: int | None = None) -> Corrida:
    """Ejecuta la seleccion y clasifica el resultado. `total_esperado` detecta lo parcial.

    El entorno se **neutraliza**: `PYTEST_ADDOPTS` heredado puede cambiar la seleccion sin
    que nada lo diga.
    """
    entorno = dict(os.environ)
    entorno.pop("PYTEST_ADDOPTS", None)
    entorno["PYTHONDONTWRITEBYTECODE"] = "1"

    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "r.xml"
        r = subprocess.run(
            [PY, "-m", "pytest", *FICHEROS, "-q", "--tb=no", "-p", "no:cacheprovider",
             "-p", "no:randomly", f"--junit-xml={xml}"],
            cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace", env=entorno)

        if r.returncode not in (0, 1) or not xml.exists():
            return Corrida(frozenset(), 0, r.returncode, False,
                           f"pytest salio con {r.returncode} y no hay resultados "
                           f"utilizables (5=no colecciono nada, 2=interrumpido, "
                           f"3=error interno, 4=uso incorrecto)")

        raiz = ET.parse(xml).getroot()
        suite = raiz if raiz.tag == "testsuite" else raiz[0]
        casos = list(suite.iter("testcase"))
        rojos = frozenset(
            f"{c.get('classname', '')}::{c.get('name', '')}"
            for c in casos
            if c.find("failure") is not None or c.find("error") is not None)

    if total_esperado is not None and len(casos) != total_esperado:
        return Corrida(rojos, len(casos), r.returncode, False,
                       f"ejecucion PARCIAL: {len(casos)} tests contra los "
                       f"{total_esperado} de la base. Un mutante solo se puede clasificar "
                       f"contra el MISMO conjunto ejecutado")
    return Corrida(rojos, len(casos), r.returncode, True)


def _modulo(ruta: str) -> str:
    """`tests/test_propiedades_utils.py` -> `tests.test_propiedades_utils`."""
    return ruta.removesuffix(".py").replace("/", ".").replace("\\", ".")


def _es_de_propiedades(identificador: str) -> str:
    """Si un `classname::name` de JUnit pertenece al fichero de propiedades.

    **La sospecha de la R1 sobre los separadores de Windows (`/` contra `\\`) no aplica
    ya**, y el revisor lo comprobo: la version anterior contemplaba las dos variantes. Pero
    el motivo real por el que ahora es solido es otro: JUnit da el `classname` en notacion
    de PUNTOS (`tests.test_propiedades_utils`), asi que no hay separadores de ruta de los
    que dudar. Comparar contra el modulo y no contra un trozo de ruta retira la pregunta
    en vez de contestarla.
    """
    return identificador.startswith(_modulo(PROPIEDADES) + "::")


#: Bytes originales de cada fichero mutable, leidos ANTES de la primera escritura.
#: **La restauracion ya no depende de git, y ese es el arreglo de H-05 de R2.** El revisor
#: construyo un caso en que el preflight pasaba y `git checkout` no podia deshacer nada:
#: `git rm --cached core/utils.py` + una linea en `.git/info/exclude` deja el `git status`
#: **vacio** y el fichero fuera del indice. El arnes mutaba, y tanto el `finally` como el
#: `atexit` morian con `pathspec did not match any file(s) known to git`, dejando produccion
#: rota.
#:
#: Estar dentro de un worktree y ver un `git status` limpio **no demuestra que cada fichero
#: sea restaurable**. Guardar los bytes si lo demuestra, y ademas no necesita git.
_BYTES_ORIGINALES: dict[str, bytes] = {}


def _memorizar_originales() -> None:
    for rel in FICHEROS_MUTABLES:
        _BYTES_ORIGINALES[rel] = (RAIZ / rel).read_bytes()


def _restaura() -> None:
    """Repone los bytes exactos. Idempotente, y no toca git.

    Escribe en binario a proposito: `write_text` normalizaria los finales de linea y
    dejaria el fichero «modificado» para git sin haber cambiado una coma — pasa en este
    repo, que tiene CRLF en el arbol y LF en el indice.
    """
    for rel, bytes_ in _BYTES_ORIGINALES.items():
        destino = RAIZ / rel
        if destino.read_bytes() != bytes_:
            destino.write_bytes(bytes_)


#: Ficheros que el arnes tiene permiso para mutar. `_restaura` se limita a ESTOS y no a
#: `.` como antes: restaurar el arbol entero desde el indice se lleva por delante trabajo
#: sin commitear de cualquier otro sitio, y el arnes no tiene por que poder hacer eso.
FICHEROS_MUTABLES: tuple[str, ...] = ("core/utils.py",)


def _preflight() -> str | None:
    """Comprueba ANTES de la primera escritura que la restauracion sera posible.

    **Defecto reproducido por la R1 (H-03, caso 3):** sobre una copia sin `.git`, el arnes
    imprimia «base: verde», **escribia el primer mutante** y solo entonces moria al
    intentar `git checkout`, dejando el fichero de produccion mutado. El `git status` de
    entrada habia fallado tambien, pero `main()` solo miraba su stdout vacio — y un stdout
    vacio es exactamente lo que devuelve un `git status` de un arbol limpio.

    Devuelve el motivo por el que NO se puede correr, o `None` si se puede.
    """
    for rel in FICHEROS_MUTABLES:
        ruta = RAIZ / rel
        if not ruta.is_file():
            return f"{rel} no existe: no hay nada que mutar ni que restaurar"
        try:
            ruta.read_bytes()
        except OSError as e:
            return f"no se pueden leer los bytes de {rel} ({e}), asi que no se podria repo"

    # El arbol limpio ya NO es la garantia de restauracion —esa la dan los bytes en
    # memoria— pero se sigue exigiendo por otra razon: si el fichero tuviera trabajo sin
    # commitear, una interrupcion entre la mutacion y la reposicion dejaria al autor
    # mirando un diff que no reconoce. Es una cortesia, y se dice que lo es.
    r = subprocess.run(["git", "status", "--porcelain", "--", *FICHEROS_MUTABLES],
                       cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode == 0 and (r.stdout or "").strip():
        return ("hay cambios sin commitear en los ficheros que este arnes muta:\n"
                + r.stdout.rstrip()
                + "\nLa restauracion los repondria, pero si el arnes muriera a mitad te "
                  "quedarias con un diff ajeno delante. Commitea antes de mutar")
    return None


def _armar_la_red_de_seguridad() -> None:
    """Restaura al salir. **Con su alcance declarado, que la primera version exageraba.**

    El 2026-09-06 el arnes se interrumpio a mitad (Ctrl-C) despues de escribir el primer
    mutante y antes de su `finally`. El arbol se quedo con `core/utils.py` **en su version
    buggy**, y solo se descubrio porque una corrida posterior se nego a arrancar. La guarda
    de ENTRADA existia; la de SALIDA no.

    ## Que cubre, y que NO

    - **Cubre:** salida normal, excepcion, y `SIGINT`/`SIGTERM` **entregadas al proceso**
      (Ctrl-C, `kill`). Medido.
    - **NO cubre:** una terminacion forzosa —`TerminateProcess` en Windows, `SIGKILL`,
      `os._exit`—. Ahi no corre ningun manejador de Python, ni de señal ni de `atexit`, y
      **no hay forma de que corra**: es una propiedad del sistema operativo, no un descuido.

    Mi docstring anterior decia «si el proceso muere **por donde sea**», y R2 de Codex
    (H-05) lo midio: con `Popen.terminate()` el arnes deja el fichero mutado. El revisor
    fue explicito en que **no exige** interceptar eso — lo que exige es que no se prometa.
    Un limite declarado se puede planificar; uno escondido bajo un «por donde sea» se
    descubre con produccion rota delante.

    El remedio practico para ese caso residual no es un manejador: es que la restauracion
    sea **trivial y sin dependencias** (bytes en memoria, ver `_restaura`) y que el
    preflight se niegue a arrancar sobre un arbol sucio, para que el rastro sea evidente.
    """
    def restaurar_y_avisar(*_args) -> None:
        try:
            _restaura()
            print("\n[arnes] mutaciones deshechas.", file=sys.stderr)
        except Exception as e:  # nunca ocultar el motivo real de la muerte
            print(f"\n[arnes] NO SE PUDO RESTAURAR: {e}\n"
                  f"        revisa a mano: git status && git checkout -- "
                  f"{' '.join(FICHEROS_MUTABLES)}", file=sys.stderr)
        raise SystemExit(130)

    atexit.register(lambda: _restaura())
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, restaurar_y_avisar)
        except (ValueError, OSError, AttributeError):
            pass  # sin señales disponibles (hilo secundario, plataforma): atexit basta


def main() -> int:
    motivo = _preflight()
    if motivo:
        print("NO SE MUTA NADA:\n  " + motivo)
        return 2

    base = _corre()
    if not base.valida:
        print(f"LA BASE NO ES MEDIBLE: {base.motivo}")
        return 2
    if base.rojos:
        print("EL ARBOL LIMPIO NO ESTA VERDE:", sorted(base.rojos))
        return 2
    print(f"base: verde ({base.total} tests)\n")

    # Los bytes se memorizan ANTES de armar la red y ANTES de la primera escritura: una red
    # que no sabe a que estado volver no es una red.
    _memorizar_originales()
    _armar_la_red_de_seguridad()

    fallidos = 0
    solo_propiedad = 0
    for nombre, fichero, viejo, nuevo, esperado in MUTANTES:
        p = RAIZ / fichero
        txt = p.read_text(encoding="utf-8")
        if txt.count(viejo) != 1:
            # No es «el mutante muere»: es que NUNCA SE APLICO. Confundirlos deja el
            # manifiesto lleno de parches muertos que nadie nota (R1/H-02, M06).
            print(f"[X ] {nombre}: el ancla aparece {txt.count(viejo)} veces, "
                  f"NO se aplico el mutante")
            fallidos += 1
            continue
        p.write_text(txt.replace(viejo, nuevo), encoding="utf-8", newline="")
        try:
            corrida = _corre(total_esperado=base.total)
        finally:
            _restaura()

        if not corrida.valida:
            print(f"[X ] {nombre}: MEDICION INVALIDA - {corrida.motivo}")
            fallidos += 1
            continue
        if not corrida.rojos:
            print(f"[X ] {nombre}: SOBREVIVE - el contrato no esta probado ahi")
            fallidos += 1
            continue

        por_propiedad = {t for t in corrida.rojos if _es_de_propiedades(t)}
        por_ejemplo = corrida.rojos - por_propiedad
        propios = {t for t in por_propiedad if any(m in t for m in esperado)}
        ajenos = por_propiedad - propios
        no_cumplidas = {m for m in esperado
                        if not any(m in t for t in por_propiedad)}

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
        if no_cumplidas:
            # AVISO y no fallo: algunas expectativas dependen de que la estrategia de
            # `hypothesis` genere el caso ofensivo (p. ej. exactamente "." para M07), asi
            # que exigirlas SIEMPRE seria brillante y flaky. Pero una que no se cumple
            # NUNCA es una expectativa imposible, como la de M08 que destapo la R1: hay
            # que verla para poder retirarla.
            print(f"        aviso: esperados que NO murieron: "
                  + ", ".join(sorted(no_cumplidas)))

    print(f"\nmal apuntados, supervivientes o mediciones invalidas: {fallidos}")
    print(f"mutantes que SOLO caza la propiedad: {solo_propiedad} de {len(MUTANTES)}")
    print(f"  ^ «solo» = frente a {EJEMPLOS}, que es lo unico que compara este arnes.")
    print("    NO significa que el resto de la suite los deje pasar: la R1 de Codex probo")
    print("    cinco de ellos contra `test_ensure_case_sumidero*.py` y los mata tambien.")
    return 1 if fallidos else 0


if __name__ == "__main__":
    raise SystemExit(main())
