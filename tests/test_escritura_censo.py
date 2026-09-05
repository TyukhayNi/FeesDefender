"""El trinquete del write-set — Plan 3A, Task 7. Censo (b) del §4 del plan.

Dos guards permanentes y un contador con techo:

1. **Producción entra por `mutex_sesion`**, no por `case_mutex.tomado`/`adquirir` en crudo.
   Sin esto, la reentrancia se puede rodear sin querer y dos etapas de la misma corrida
   sostendrían leases distintos sobre el mismo caso.
2. **El censo de escrituras que no pasan por la costura solo puede BAJAR.** No es una
   prohibición —hoy son casi todas— es un trinquete: 3B y 3C lo bajan, y nada lo sube.

**Lo que este censo NO prueba, dicho aquí y no en una nota al pie:** mide **llamadas**, no
flujo de datos. Un llamador que use la costura y luego escriba por su cuenta lo pasa. Eso
lo cierran las pruebas por fila del §25.4, no un contador — y por eso el criterio de salida
de 3A exige las dos cosas.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

#: Los 11 productores que la tabla del §25 nombra. La lista es explícita a propósito: un
#: barrido de `core/**` crecería en silencio y el número dejaría de comparar lo mismo.
PRODUCTORES = (
    "core/case_manager.py", "core/intake_drive.py", "core/intake_manifest.py",
    "core/intake_log.py", "core/sync_sudespacho.py",
    "core/email_atomize/pipeline.py", "core/adjuntos_contenido/pipeline.py",
    "core/sala_maquina.py", "core/split_documental.py",
    "scripts/abrir_caso.py", "scripts/sala_maquina.py",
    # Anadido el 2026-09-03 (Plan 5, Task 8b): `core/apertura_v1_estado.py`
    # escribe el estado durable por ronda y NO pasa por la costura. Dejarlo fuera
    # de esta lista habria mantenido el techo en 84 con una escritura nueva sin
    # contar, que es el «techo con hueco» contra el que avisa el comentario de abajo.
    "core/apertura_v1_estado.py",
    # Anadido el 2026-09-05 (accion 10, ruta `ofimatica`): `core/ofimatica_a_pdf.py`
    # convierte con LibreOffice y escribe donde le dicen (dos `mkdir`: el `--outdir`
    # temporal y el padre del destino). Su llamador publica el buscable en `01_OCR/`.
    # Dejarlo fuera —«como `core/anon/ocr.py`»— fue mi primera version y la R1 la llamo
    # por su nombre (H-04): un escritor nuevo fuera del conjunto medido no baja el censo,
    # lo esconde. Se declara.
    "core/ofimatica_a_pdf.py",
)

#: Las primitivas del barrido del §25 que NO son ambiguas: su nombre solo existe en el
#: sistema de ficheros.
PRIMITIVAS = frozenset({
    "write_text", "write_bytes", "mkdir", "unlink", "copy2", "append_event",
    # `mkstemp` anadido el 2026-09-03 (R-B/L1-17 y L5-02). El Plan 5 estreno el patron
    # de escritura atomica —`mkstemp` + `os.fdopen` + `os.replace`— y con el un hueco:
    # la escritura PRINCIPAL de ese patron no la contaba nadie, asi que una funcion de
    # escritura nueva que lo usara pasaba el trinquete sin mover el numero.
    "mkstemp",
})

#: Las AMBIGUAS, que comparten nombre con métodos de `str`, `dict` y `dataclasses`.
#:
#: Medido el 2026-08-26: contarlas por el nombre inflaba el censo en **12** sitios —
#: `path.replace("\\", "/")`, `dt.replace(tzinfo=...)`, `dataclasses.replace(ident, ...)`—
#: y un techo inflado es un techo con hueco: deja entrar escrituras nuevas de verdad sin
#: que el trinquete muerda. Es el defecto que `test_el_techo_no_esta_holgado` decía
#: prevenir, cometido en el detector que ese mismo test comprueba.
AMBIGUAS = frozenset({"replace", "copy", "dump"})

#: **Techo del censo, medido el 2026-08-26. Solo puede bajar.**
#:
#: 82 sitios de escritura en los 11 productores, y **cero** ficheros entrando por la
#: costura. Bajarlo es el trabajo de 3B (los derivados) y 3C (la poda). Si un cambio lo
#: sube, o es una escritura nueva sin costura —y entonces falta migrarla— o la lista de
#: productores creció y hay que decirlo, no absorberlo.
#:
#: **Decía 93, y era un techo con 11 huecos.** El detector contaba `replace`/`copy`/`dump`
#: por el nombre, así que `path.replace("\\", "/")`, `dt.replace(tzinfo=...)` y
#: `dataclasses.replace(...)` entraban como si escribieran en disco. Un techo inflado deja
#: entrar escrituras nuevas de verdad sin que el trinquete muerda — exactamente lo que
#: `test_el_techo_no_esta_holgado` dice prevenir, cometido dentro del detector que ese test
#: comprueba. Lo encontré al preparar la ronda del diff, mirando el desglose por primitiva
#: en vez del total: **un número agregado esconde su propia composición.**
#:
#: **82 -> 83 el 2026-08-26, y es la PRIMERA vez que el trinquete sube.** Lo permite su
#: propia regla —«o es una escritura nueva sin costura, y entonces falta migrarla, o la
#: lista creció y hay que decirlo, **no absorberlo**»— y este es el primer caso: la
#: remediación de **R15/H15-06** añadió un `append_event` en `scripts/abrir_caso.py` para
#: que un pull fallido deje constancia de sus bytes parciales en vez de perderlos.
#:
#: Es una escritura de **protocolo** (fila #13) y **no pasa por la costura**, porque las
#: filas de protocolo son precisamente las que el Task 6 dejó declaradas como diferidas.
#: Así que este +1 es **deuda declarada, no cobertura**: baja cuando se migre la #13.
#: Subirlo sin esta explicación sería justo lo que la regla prohíbe — y el trinquete me lo
#: cazó a mí, con mi propio cambio, que es la única prueba de que sirve.
#: **83 -> 84 el 2026-09-03, y es la SEGUNDA vez que sube.** El cableado de V1 (Plan 5)
#: añade `apertura_v1_terminada` en `scripts/abrir_caso.py`: el estado con que termina la
#: secuencia tiene que quedar en el log forense, o la unica constancia de una apertura es
#: la pantalla, que se pierde. Misma clase que el +1 anterior —escritura de **protocolo**,
#: fila #13— y misma condicion de bajada: se migra con la #13.
#:
#: **Lo que NO se hizo, y era tentador:** mover `registrar_cierre_v1` a `core/apertura_v1.py`,
#: que no esta en `PRODUCTORES`. El censo habria bajado a 83 sin que la escritura
#: desapareciera. Eso es absorber la deuda, que es justo lo que la regla de arriba prohibe.
#: Lo cazo la R-A del Plan 5 (HA-11) antes de escribir una linea.
#: **84 -> 87 el 2026-09-03, y las tres son de la MISMA pieza.** El Plan 5 anade
#: `core/apertura_v1_estado.py` —el estado durable por ronda que la spec §11 hace
#: obligatorio «desde la primera entrega»— con `mkdir`, `os.replace` y el `unlink` del
#: temporal de su escritura atomica. Es escritura de **protocolo**: un fichero de control
#: en `00_Input`, no un documento del caso.
#:
#: **La lista de PRODUCTORES creció, y eso se declara aqui.** Lo alternativo era dejar el
#: modulo fuera de la lista: el techo se habria quedado en 84 con tres escrituras nuevas
#: sin contar, que es literalmente el «techo con hueco» que el comentario de abajo dice
#: prevenir. Un censo que no cuenta lo nuevo no es un censo, es un numero.
#: **87 -> 88 el 2026-09-03, y esta subida NO es una escritura nueva.** Es el `mkstemp`
#: que el detector no contaba: al anadirlo a `PRIMITIVAS` aparecio una escritura que ya
#: existia y estaba invisible. Subir el techo aqui es *reconocer* deuda, no contraerla —
#: y es exactamente lo que la regla de arriba pide cuando el detector mejora.
#: **88 -> 91 el 2026-09-05 (accion 10, `MEJORAS #61`), y esta vez la subida es de un
#: DOCUMENTO del caso, no de protocolo.** La ruta `ofimatica` publica el PDF buscable de un
#: `.doc`/`.odt`/`.ppt` en `01_OCR/` (+1 `mkdir` en `core/sala_maquina.py`, la misma clase de
#: escritura que `ocr_pdf` hace por su cuenta), y `core/ofimatica_a_pdf.py` entra en
#: `PRODUCTORES` con sus dos `mkdir` (+2). La primera version de la pieza dejaba el censo en
#: 88 haciendo que el conversor escribiera directamente en `01_OCR/` —fuera de la lista— y
#: la R1 de Codex lo cazo (H-04) junto con la ventana que abria (H-03: publicar antes de
#: decidir). Condicion de bajada: cuando los derivados de la sala de maquina pasen por la
#: costura (3B), estas tres bajan con los otros 13 de `sala_maquina`.
TECHO_CENSO = 91


def _nombre_llamado(n: ast.Call) -> str | None:
    f = n.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _es_escritura(n: ast.Call) -> bool:
    nombre = _nombre_llamado(n)
    if nombre in PRIMITIVAS:
        return True
    if nombre == "open":
        modos = [a.value for a in n.args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        return any("a" in m or "w" in m for m in modos)
    if nombre in AMBIGUAS:
        return _ambigua_es_de_ficheros(n, nombre)
    return False


def _ambigua_es_de_ficheros(n: ast.Call, nombre: str) -> bool:
    """¿Este `replace`/`copy`/`dump` toca el disco, o es de `str`/`dict`/`dataclasses`?

    Se decide por la **forma de la llamada**, que es lo único que un análisis estático
    tiene: quién es el receptor y cuántos argumentos lleva.

    - `os.replace(a, b)` y `shutil.copy(a, b)` → el receptor es el módulo. Escritura.
    - `p.replace(destino)` → `Path.replace` toma **un** argumento y nada más. Escritura.
    - `s.replace("a", "b")` → dos argumentos y receptor que no es `os`. Cadena.
    - `dt.replace(tzinfo=...)` → keywords y ningún posicional. No es de ficheros.
    - `dataclasses.replace(x, k=v)` y el `replace(x, k=v)` importado → receptor `dataclasses`
      o función suelta. No es de ficheros.
    """
    f = n.func
    if isinstance(f, ast.Name):
        # `replace(obj, campo=...)` suelto es el de `dataclasses`, importado por nombre.
        return False
    receptor = f.value if isinstance(f, ast.Attribute) else None
    modulo = receptor.id if isinstance(receptor, ast.Name) else None
    if modulo in ("os", "shutil"):
        return True
    if modulo == "dataclasses":
        return False
    if nombre == "dump":
        # `json.dump(obj, fh)` escribe; `yaml.dump(obj)` sin stream devuelve una cadena.
        return modulo in ("json", "yaml", "pickle") and len(n.args) >= 2
    if nombre == "copy":
        return False            # sin `shutil` delante, es `dict.copy`/`list.copy`
    # `replace` con UN posicional y sin keywords es `Path.replace`.
    return len(n.args) == 1 and not n.keywords


def censar(ruta: str | Path) -> tuple[int, bool]:
    """`(sitios de escritura, entra por la costura)`.

    El import se detecta por **AST**, nunca por subcadena. Contarlo por texto es cómo se
    cuelan los falsos positivos: al escribir este censo la primera vez, `"casos.escritura"
    in texto` casó con un **comentario** en el que yo mismo nombraba el módulo, y el
    fichero salió declarado como migrado sin haberlo migrado. Es literalmente el defecto
    que R10/H10-10 castigó con `filelock` en este repo.
    """
    arbol = ast.parse(io.open(ruta, encoding="utf-8").read(), filename=str(ruta))
    sitios, usa_costura = 0, False
    for n in ast.walk(arbol):
        if isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            if mod.endswith("casos.escritura"):
                usa_costura = True
            elif mod.endswith("casos") and any(a.name == "escritura" for a in n.names):
                usa_costura = True
        elif isinstance(n, ast.Import):
            if any(a.name.endswith("casos.escritura") for a in n.names):
                usa_costura = True
        elif isinstance(n, ast.Call) and _es_escritura(n):
            sitios += 1
    return sitios, usa_costura


# ------------------------------------------------------- el detector no es vacuo

def test_el_detector_encuentra_lo_que_dice_encontrar(tmp_path):
    """Prueba de que el censo MUERDE. Un guard sin esto es una intención.

    Se le da un fichero con una escritura de cada forma y se comprueba que las cuenta
    todas; y uno con solo lecturas, para que un detector que devolviera un número
    constante no pasara.
    """
    escribe = tmp_path / "escribe.py"
    escribe.write_text(
        "from pathlib import Path\n"
        "import json\n"
        "def f(p, d):\n"
        "    Path(p).write_text('x')\n"
        "    Path(p).write_bytes(b'x')\n"
        "    Path(p).mkdir()\n"
        "    Path(p).unlink()\n"
        "    json.dump(d, open(p, 'w'))\n"
        "    open(p, 'a').close()\n",
        encoding="utf-8")
    sitios, usa = censar(escribe)
    assert sitios == 7, f"el detector no ve todas las formas de escritura: {sitios}"
    assert usa is False

    lee = tmp_path / "lee.py"
    lee.write_text(
        "from pathlib import Path\n"
        "def f(p):\n"
        "    return Path(p).read_text() + open(p, 'r').read()\n",
        encoding="utf-8")
    assert censar(lee) == (0, False), "el detector cuenta lecturas como escrituras"


def test_el_detector_no_se_cree_un_comentario(tmp_path):
    """El falso positivo REAL que tuvo la primera versión de este censo.

    Un fichero que solo *nombra* la costura en un comentario o en una cadena no la usa.
    """
    f = tmp_path / "solo_la_menciona.py"
    f.write_text(
        "# este modulo no puede pasar por core.casos.escritura todavia\n"
        "DOC = 'ver core.casos.escritura'\n"
        "from pathlib import Path\n"
        "def g(p):\n"
        "    Path(p).write_text('x')\n",
        encoding="utf-8")
    sitios, usa = censar(f)
    assert sitios == 1
    assert usa is False, (
        "el detector se creyó un comentario: es el defecto que R10/H10-10 castigó con "
        "`filelock`, y en el que caí al escribir este mismo censo")


# ------------------------------------------------------------------ el trinquete

def test_el_censo_solo_baja():
    """El techo del §4(b). Si sube, o falta migrar algo o la lista creció en silencio."""
    detalle = {p: censar(p)[0] for p in PRODUCTORES}
    total = sum(detalle.values())
    assert total <= TECHO_CENSO, (
        f"el censo de escrituras fuera de la costura SUBIÓ a {total} (techo "
        f"{TECHO_CENSO}). Reparto: {detalle}. O hay una escritura nueva sin migrar, o la "
        f"lista de productores creció y eso se declara, no se absorbe")


def test_el_techo_no_esta_holgado():
    """Que el techo sea el número REAL, no uno cómodo.

    Un techo por encima del censo deja sitio para que entren escrituras nuevas sin que
    nadie se entere — que es exactamente lo contrario de un trinquete.
    """
    total = sum(censar(p)[0] for p in PRODUCTORES)
    assert total == TECHO_CENSO, (
        f"el censo real es {total} y el techo dice {TECHO_CENSO}: si acabas de migrar "
        f"algo, BAJA el techo en el mismo commit")


# ---------------------------------------------- produccion entra por mutex_sesion

def test_produccion_no_llama_a_la_primitiva_en_crudo():
    """Guard permanente: `case_mutex.tomado`/`adquirir` no se llaman fuera de su capa.

    `mutex_sesion` es la única que puede, porque es la que implementa la reentrancia. Si
    otro sitio adquiriera en crudo, el anidamiento dejaría de ser un no-op revalidado y
    volvería a ser un `CaseBusy` contra uno mismo — el defecto que el Task 1 cierra.
    """
    exentos = {"mutex_sesion.py", "case_mutex.py"}
    infractores = []
    for base in ("core", "scripts"):
        for p in sorted(Path(base).rglob("*.py")):
            if p.name in exentos:
                continue
            arbol = ast.parse(io.open(p, encoding="utf-8").read(), filename=str(p))
            for n in ast.walk(arbol):
                if isinstance(n, ast.Call) and _nombre_llamado(n) in ("tomado", "adquirir"):
                    infractores.append(f"{p.as_posix()}:{n.lineno}")
    assert not infractores, (
        "producción llama a la primitiva del mutex en crudo, saltándose la reentrancia:\n  "
        + "\n  ".join(infractores))


@pytest.mark.parametrize("entrypoint", ["scripts/abrir_caso.py", "scripts/sala_maquina.py"])
def test_los_entrypoints_cableados_siguen_adquiriendo(entrypoint):
    """Trinquete de lo ya cableado: quien adquiere hoy no puede dejar de hacerlo.

    Es la regresión que nadie nota, porque quitar el `with` no rompe ninguna prueba
    funcional: simplemente se deja de proteger. Por eso el guard es estructural.
    """
    arbol = ast.parse(io.open(entrypoint, encoding="utf-8").read(), filename=entrypoint)
    assert any(isinstance(n, ast.Call) and _nombre_llamado(n) == "sostenido"
               for n in ast.walk(arbol)), (
        f"{entrypoint} ya no adquiere el mutex: el cableado del Task 5 se perdió")

def test_el_detector_distingue_replace_de_ficheros_del_de_cadenas(tmp_path):
    """El falso positivo que infló el techo en 11, ahora contratado.

    `replace`, `copy` y `dump` existen también en `str`, `dict`, `datetime` y `dataclasses`.
    Contarlos por el nombre convierte cualquier normalización de rutas en una «escritura», y
    el techo acaba con hueco para escrituras nuevas de verdad.
    """
    fuente = "\n".join([
        "import os, shutil, dataclasses, json",
        "from dataclasses import replace",
        "def g(p, d, s, dt, obj, fh):",
        "    os.replace(p, p)               # 1 escritura",
        "    p.replace(d)                   # 2 escritura (Path.replace)",
        "    shutil.copy(p, d)              # 3 escritura",
        "    json.dump(obj, fh)             # 4 escritura",
        "    s.replace('a', 'b')            # cadena, NO",
        "    dt.replace(tzinfo=None)        # datetime, NO",
        "    dataclasses.replace(obj, x=1)  # dataclass, NO",
        "    replace(obj, x=1)              # dataclass importado, NO",
        "    d.copy()                       # dict, NO",
        "    json.dumps(obj)                # no escribe, NO",
        "    return 0",
    ])
    f = tmp_path / "ambiguas.py"
    f.write_text(fuente, encoding="utf-8")

    sitios, _ = censar(f)
    assert sitios == 4, (
        f"el detector cuenta {sitios} y hay 4 escrituras reales: si sube, está contando "
        f"`replace`/`copy`/`dump` de str/dict/dataclasses y el techo se infla")


# ------------------------------------------------------------- R15/H15-09

def test_la_raiz_por_defecto_del_registro_sigue_teniendo_su_rama(tmp_path, monkeypatch):
    """R15/H15-09 — la fixture global aislaba el registro y dejaba el fallback sin cubrir.

    `_registro_y_locks_aislados` fija `FEESDEFENDER_WORKSPACE_REGISTRY` en **toda** la suite,
    que es lo correcto —ningún test debe escribir en el perfil real—. El efecto colateral es
    que ningún test ejercitaba ya la rama «sin override», y de ella cuelga la raíz de los
    lockfiles cuando no se pasa `raiz`: una regresión ahí habría quedado invisible.

    Aquí se retira la variable **dentro de `tmp_path`**, con `LOCALAPPDATA` redirigido, para
    ejercitar el fallback sin tocar nada del usuario.
    """
    from core.casos.workspace_registry import raiz_por_defecto

    monkeypatch.delenv("FEESDEFENDER_WORKSPACE_REGISTRY", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))

    raiz = raiz_por_defecto()
    assert raiz == tmp_path / "LocalAppData" / "FeesDefender" / "workspaces", raiz
    # Y sigue estando fuera del árbol de casos y del repo, que es su barrera de ubicación.
    from core.casos.case_mutex import raiz_de_locks
    assert raiz_de_locks(raiz) == raiz
