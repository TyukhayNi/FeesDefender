r"""Guard del DESPLIEGUE del plugin: lo que arranca Claude Code == lo canónico.

Por qué existe, medido el 2026-09-07. `feesdefender@despacho-tyukhay` llevaba
instalado en **0.4.0 desde el 2026-07-20**; la reparación de los conectores del
2026-08-31 (PR #253) estaba en `dist/plugin` como 0.4.1 y **nunca se instaló**.
Claude Code arrancaba los wrappers de junio y julio —el de `email-export` eran
136 bytes contra los 4.178 de la fuente— mientras la suite daba verde sobre los
de agosto. El día que se miró, `email-export` estaba caído con
`CONNECTION_CLOSED`.

**Y `tests/test_mcp_wrappers.py` no podía cazarlo por construcción**: recorre
`ROOT/plugins/*/run_server.bat`, que es la fuente. Lo que se ejecuta vive en
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. Aunque hubiera
estado verde del todo no habría visto nada: el fallo no está en la fuente sino
en el paso que la despliega, y ese paso no lo vigilaba nadie. La forma del
defecto es «tres copias» —fuente ✅, build ✅, instalado ❌— y la única de las
tres que le importa a quien usa el conector es la última.

**Contra qué se compara, que es la decisión de diseño de este fichero.** Contra
un **commit canónico**, no contra el árbol de trabajo. La propiedad es «lo que
corre es lo que el equipo da por bueno», y lo que uno tiene a medias en su rama
no es eso. Comparar contra el árbol pondría rojo cualquier rama que toque un
conector desde el primer minuto y hasta el despliegue — un rojo que no significa
nada acaba ignorado, y así muere una verja (`MEJORAS #171`). Al mergear, en
cambio, el guard SÍ se pone rojo hasta que se despliega de verdad: eso es la
presión que faltaba.

**Qué cubre, dicho a propósito.** Los conectores **y los metadatos que deciden
cómo arrancan** (`.mcp.json`, `.claude-plugin/plugin.json`). La primera versión
solo miraba los directorios de los conectores, y la R1 adversarial (H-01) midió
el agujero: sustituir el `.mcp.json` instalado por `{}` dejaba los guards en
verde, con el manifiesto ya sin declarar ningún MCP. **No** cubre las skills del
bundle: tienen otra vía de despliegue —el `.skill` que se importa a mano en
Cowork— y hay varias pendientes de reimportar a sabiendas, así que exigirlas
daría un rojo permanente sobre un estado aceptado.

**Sobre el `skip`.** Este guard mira el estado de UNA máquina, así que donde el
plugin no esté instalado no puede decir nada. Ahí hace `skip` con el motivo
escrito entero, porque «no lo sé» no es «no hay» y un `skip` mudo aquí
reproduciría el silencio que el guard viene a romper.

**Lo que sigue SIN CUBRIR, declarado y no disimulado:** que Claude Code elija de
verdad la instalación que este guard audita cuando hay varias, y la frescura de
`origin/main` respecto al remoto sin hacer `fetch`. Ninguna de las dos se puede
comprobar desde aquí.
"""
from __future__ import annotations

import json
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from scripts.package_plugin import CONECTORES, _IGNORE, SRC

ROOT = Path(__file__).resolve().parents[1]
REGISTRO = Path.home() / ".claude" / "plugins" / "installed_plugins.json"

_REDESPLIEGUE = (
    "Redesplegar, desde la RAÍZ del repo (el marketplace apunta a su `dist/`, "
    "no al de un worktree): `python -m scripts.package_plugin`, "
    "`claude plugin marketplace update <marketplace>`, "
    "`claude plugin update <plugin>@<marketplace>`. "
    "OJO, medido el 2026-09-07: `plugin update` compara por VERSIÓN, no por "
    "contenido — con la versión igual dice «already at the latest version» y no "
    "copia nada, dejando el rojo intacto. Si cambió el contenido de un conector, "
    "hay que BUMPEAR `plugin-src/.claude-plugin/plugin.json`; para arreglar un "
    "desfase dentro de una misma versión, `claude plugin uninstall` + `install` "
    "(no hay `--force`)"
)


# --------------------------------------------------------------------------
# La referencia canónica: UN commit, resuelto una sola vez
# --------------------------------------------------------------------------
def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, encoding="utf-8", errors="replace",
    )


@lru_cache(maxsize=1)
def _commit_canonico() -> tuple[str, str]:
    """`(etiqueta, sha)` del commit contra el que se compara TODO en este fichero.

    Se resuelve a un SHA y se cachea: la R1 (H-03) señaló que consultar la
    referencia por nombre en cada comprobación permite que se mueva a mitad de la
    corrida, y que «existe una rama local llamada main» no demuestra «es lo que el
    equipo da por bueno ahora». El revisor lo reprodujo con `main=A` e
    `origin/main=B` descendiente: se elegía la local y el despliegue obsoleto
    pasaba en verde.

    Política: **`origin/main` manda** cuando existe, porque es la copia compartida.
    `main` local solo se usa si no hay remoto, y entonces la falta de garantía de
    frescura se dice en el mensaje de fallo, no se calla.
    """
    for ref in ("origin/main", "main"):
        r = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if r.returncode == 0 and r.stdout.strip():
            return ref, r.stdout.strip()
    pytest.skip(
        "ni `origin/main` ni `main` resuelven desde este checkout: sin commit "
        "canónico no se puede decir si lo desplegado está rancio"
    )


def _leer_canonico(ruta: str) -> str | None:
    """Contenido de `ruta` en el commit canónico, normalizado. `None` si no está."""
    _, sha = _commit_canonico()
    r = _git("show", f"{sha}:{ruta}")
    return _normaliza(r.stdout) if r.returncode == 0 else None


def _ficheros_canonicos(subruta: str) -> list[str]:
    """Rutas (relativas a `subruta`) que el commit canónico tiene bajo ella."""
    _, sha = _commit_canonico()
    prefijo = subruta.rstrip("/") + "/"
    r = _git("ls-tree", "-r", "--name-only", sha, "--", prefijo)
    if r.returncode != 0:
        return []
    salida = []
    for linea in r.stdout.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        rel = Path(linea[len(prefijo):])
        if not _excluido(rel):
            salida.append(rel.as_posix())
    return sorted(salida)


def _excluido(rel: Path) -> bool:
    """Las MISMAS exclusiones que el empaquetador, reusando su `_IGNORE`.

    Reescribir la lista aquí sería un segundo sitio donde se puede quedar rancia:
    si el empaquetador deja de copiar algo, el guard tiene que dejar de exigirlo
    en el mismo commit, no en el que alguien se acuerde.
    """
    partes = list(rel.parts)
    return bool(set(_IGNORE("", partes)) & set(partes))


def _normaliza(texto: str) -> str:
    """Sin fin de línea: el empaquetador escribe LF y git deja CRLF.

    Medido el 2026-09-07: `dist/plugin` y el repo diferían solo en eso. Exigir
    bytes exactos daría un rojo permanente que nadie podría arreglar.
    """
    return texto.replace("\r\n", "\n")


def _leer_instalado(p: Path) -> str | None:
    try:
        return _normaliza(p.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None


# --------------------------------------------------------------------------
# Las instalaciones vivas — TODAS, no la primera
# --------------------------------------------------------------------------
def _identidad_del_plugin() -> tuple[str, str]:
    """`(nombre, marketplace)` leídos del COMMIT CANÓNICO, no del árbol.

    La R1 señaló que leerlos del árbol mientras el contenido viene de `main`
    rompe la promesa «se compara contra main». Con `SRC` como respaldo solo si el
    commit no los tuviera.
    """
    manif = _leer_canonico("plugin-src/.claude-plugin/plugin.json")
    mercado = _leer_canonico("plugin-src/marketplace.json")
    if manif is None or mercado is None:  # pragma: no cover - repo sin plugin-src
        manif = (SRC / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        mercado = (SRC / "marketplace.json").read_text(encoding="utf-8")
    return json.loads(manif)["name"], json.loads(mercado)["name"]


def _instalaciones() -> list[dict]:
    """TODAS las entradas de instalación del plugin, o `skip` explicado.

    La R1 (H-02) midió el defecto de devolver solo `entradas[0]`: con una segunda
    entrada de ámbito `project`, versión vieja y `installPath` inexistente, los
    guards pasaban en verde; bastaba invertir el orden para que fallaran. El
    resultado dependía del orden del registro, que no es una propiedad del
    despliegue.
    """
    nombre, marketplace = _identidad_del_plugin()
    clave = f"{nombre}@{marketplace}"
    if not REGISTRO.exists():
        pytest.skip(
            f"no hay registro de plugins en {REGISTRO}: esta máquina no instala "
            f"el plugin por marketplace, así que no hay despliegue que auditar"
        )
    datos = json.loads(REGISTRO.read_text(encoding="utf-8"))
    entradas = datos.get("plugins", {}).get(clave)
    if not entradas:
        pytest.skip(
            f"`{clave}` no está instalado en esta máquina ({REGISTRO}); el guard "
            f"no puede comparar lo desplegado con lo canónico. Instalarlo: "
            f"`claude plugin install {clave}`"
        )
    return list(entradas)


def _rotulo(inst: dict) -> str:
    return f"scope={inst.get('scope', '?')} version={inst.get('version', '?')}"


def _ruta_instalada(inst: dict) -> Path:
    ruta = Path(inst["installPath"])
    if not ruta.is_dir():
        pytest.fail(
            f"instalación {_rotulo(inst)}: el registro dice que está en {ruta} y "
            f"ese directorio no existe. La instalación está ROTA, que no es lo "
            f"mismo que ausente. {_REDESPLIEGUE}"
        )
    return ruta


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------
def test_el_registro_de_plugins_es_legible() -> None:
    """Hermano de los `test_hay_*_que_auditar`: si el registro deja de parsearse,
    todo lo de abajo se saltaría en verde sin que nadie se entere."""
    assert _instalaciones()


def test_hay_conectores_que_auditar() -> None:
    """Si `CONECTORES` se vaciara, los guards de contenido pasarían VACÍOS y verdes."""
    assert [d for _, d in CONECTORES], CONECTORES


def test_los_conectores_auditados_son_los_que_main_declara() -> None:
    """`CONECTORES` (del árbol) tiene que cuadrar con el `.mcp.json` de main.

    La R1 señaló que los SELECTORES —`CONECTORES`, `_IGNORE`, la identidad— se
    importan del árbol de trabajo mientras el contenido se lee de main, así que
    la promesa «se compara contra main» no los cubría. La identidad ya se lee de
    main; para `CONECTORES`, que es código y no se puede importar de un commit,
    esto ata la lista a lo que main declara arrancar.
    """
    crudo = _leer_canonico("plugin-src/.mcp.json")
    assert crudo is not None, "el commit canónico no tiene `plugin-src/.mcp.json`"
    declarados = json.loads(crudo).get("mcpServers", {})
    assert declarados, "`.mcp.json` canónico no declara ningún servidor"
    # `.mcp.json` nombra los servidores por su etiqueta y apunta al directorio en
    # los args; se compara por el directorio, que es lo que este fichero audita.
    # Solo cuentan los args que son una ruta DENTRO del bundle: el `/c` de `cmd`
    # también lleva barra y su penúltimo segmento es la cadena vacía.
    dirs_declarados = set()
    for cfg in declarados.values():
        for arg in cfg.get("args", []):
            if "CLAUDE_PLUGIN_ROOT" not in arg:
                continue
            partes = [p for p in arg.replace("\\", "/").split("/") if p]
            if len(partes) >= 2:
                dirs_declarados.add(partes[-2])
    dirs_auditados = {d for _, d in CONECTORES}
    assert dirs_declarados == dirs_auditados, (
        f"lo que main declara arrancar {sorted(dirs_declarados)} no coincide con "
        f"lo que este guard audita {sorted(dirs_auditados)}: habría conectores "
        f"corriendo sin que nadie compruebe su despliegue"
    )


def test_la_version_instalada_es_la_de_main() -> None:
    """Registro, manifiesto instalado y main dicen la MISMA versión, en todas las entradas.

    Tres sitios y no uno: la R1 (H-01) midió que el test leía la versión del
    registro y nunca del manifiesto instalado, así que un `plugin.json` desplegado
    vacío o rancio pasaba en verde. Y (H-02) que solo se miraba la primera entrada.
    """
    crudo = _leer_canonico("plugin-src/.claude-plugin/plugin.json")
    assert crudo is not None, "el commit canónico no tiene el manifiesto del plugin"
    esperada = json.loads(crudo)["version"]
    etiqueta, _ = _commit_canonico()

    for inst in _instalaciones():
        assert inst.get("version") == esperada, (
            f"instalación {_rotulo(inst)}: el registro dice {inst.get('version')!r} "
            f"y `{etiqueta}` dice {esperada!r}. Lo que arranca Claude Code no es lo "
            f"canónico. {_REDESPLIEGUE}"
        )
        manif = _leer_instalado(_ruta_instalada(inst) / ".claude-plugin" / "plugin.json")
        assert manif is not None, (
            f"instalación {_rotulo(inst)}: no tiene `.claude-plugin/plugin.json`. "
            f"{_REDESPLIEGUE}"
        )
        try:
            instalada = json.loads(manif)["version"]
        except (ValueError, KeyError) as exc:
            pytest.fail(
                f"instalación {_rotulo(inst)}: su `plugin.json` no declara versión "
                f"legible ({exc}). {_REDESPLIEGUE}"
            )
        assert instalada == esperada, (
            f"instalación {_rotulo(inst)}: su manifiesto dice {instalada!r} y "
            f"`{etiqueta}` dice {esperada!r}. {_REDESPLIEGUE}"
        )


def test_los_metadatos_de_arranque_desplegados_SON_los_de_main() -> None:
    """`.mcp.json` y `.claude-plugin/plugin.json` instalados == los de main.

    Son el contrato de arranque: `.mcp.json` lleva el comando y los argumentos con
    los que se lanza cada conector. La R1 (H-01) lo midió: con el `.mcp.json`
    instalado sustituido por `{}` —o sea, sin declarar ya ningún MCP— los guards
    seguían pasando, certificando copias que nadie ejecuta.
    """
    etiqueta, _ = _commit_canonico()
    metadatos = {
        ".mcp.json": "plugin-src/.mcp.json",
        ".claude-plugin/plugin.json": "plugin-src/.claude-plugin/plugin.json",
    }
    for inst in _instalaciones():
        raiz = _ruta_instalada(inst)
        for rel, en_main in metadatos.items():
            canonico = _leer_canonico(en_main)
            assert canonico is not None, f"`{etiqueta}` no tiene `{en_main}`"
            instalado = _leer_instalado(raiz / rel)
            assert instalado is not None, (
                f"instalación {_rotulo(inst)}: falta `{rel}`, que es el contrato de "
                f"arranque de los conectores. {_REDESPLIEGUE}"
            )
            assert instalado == canonico, (
                f"instalación {_rotulo(inst)}: `{rel}` desplegado != `{etiqueta}`. "
                f"Los conectores pueden estar arrancando con otro comando del que "
                f"declara el repo. {_REDESPLIEGUE}"
            )


@pytest.mark.parametrize("conector", [d for _, d in CONECTORES])
def test_el_conector_desplegado_ES_el_de_main(conector: str) -> None:
    """Fichero a fichero y en las DOS direcciones, el conector instalado == main.

    La versión sola no basta, y el ejemplo lo demuestra por partida doble: lo que
    rompía `email-export` no era el número sino que su `run_server.bat` instalado
    tenía 136 bytes y le faltaba el `--repo-root`; y la primera corrida de este
    guard, ya con 0.4.1 instalado, encontró además `tiers.py` rancio — sin
    `_apertura_v1.json` ni los temporales de escritura atómica en `PROTOCOL_EDIT`,
    que entraron con `MEJORAS #149` y `#146`.

    Las dos direcciones porque la R1 señaló que la comparación era unidireccional:
    exigía los ficheros canónicos pero no rechazaba sobrantes, y un fichero que
    main ya no tiene puede seguir instalado y seguir importándose.
    """
    etiqueta, _ = _commit_canonico()
    canonicos = _ficheros_canonicos(f"plugins/{conector}")
    assert canonicos, (
        f"`{etiqueta}` no tiene ficheros de `{conector}` -> el guard estaría "
        f"comparando contra nada"
    )

    for inst in _instalaciones():
        destino = _ruta_instalada(inst) / conector
        assert destino.is_dir(), (
            f"instalación {_rotulo(inst)}: el conector `{conector}` no está "
            f"({destino}). {_REDESPLIEGUE}"
        )

        faltan = [rel for rel in canonicos if not (destino / rel).is_file()]
        assert not faltan, (
            f"instalación {_rotulo(inst)}, `{conector}`: en `{etiqueta}` y NO "
            f"desplegados -> {faltan}. {_REDESPLIEGUE}"
        )

        presentes = {
            p.relative_to(destino).as_posix()
            for p in destino.rglob("*")
            if p.is_file() and not _excluido(p.relative_to(destino))
        }
        sobran = sorted(presentes - set(canonicos))
        assert not sobran, (
            f"instalación {_rotulo(inst)}, `{conector}`: desplegados y NO en "
            f"`{etiqueta}` -> {sobran}. Un fichero que el repo ya no tiene sigue "
            f"instalado y puede seguir importándose. {_REDESPLIEGUE}"
        )

        distintos = [
            rel for rel in canonicos
            if _leer_instalado(destino / rel) != _leer_canonico(f"plugins/{conector}/{rel}")
        ]
        assert not distintos, (
            f"instalación {_rotulo(inst)}, `{conector}`: desplegado != `{etiqueta}` "
            f"en {distintos}. Es el defecto del 2026-07-20 otra vez: se arregló la "
            f"fuente y no se instaló. {_REDESPLIEGUE}"
        )
