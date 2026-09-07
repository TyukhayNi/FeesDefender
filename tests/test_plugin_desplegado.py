r"""Guard del DESPLIEGUE del plugin: lo que arranca Claude Code == lo canónico.

Por qué existe, medido el 2026-09-07. `feesdefender@despacho-tyukhay` llevaba
instalado en **0.4.0 desde el 2026-07-20**; la reparación de los conectores del
2026-08-31 (PR #253) estaba en `dist/plugin` como 0.4.1 y **nunca se instaló**.
Durante cinco semanas Claude Code arrancó los wrappers de junio y julio —el de
`email-export` eran 136 bytes contra los 4.178 de la fuente— mientras la suite
daba verde sobre los de agosto. El día que se miró, `email-export` estaba caído
con `CONNECTION_CLOSED` y nadie lo sabía.

**Y `tests/test_mcp_wrappers.py` no podía cazarlo por construcción**: recorre
`ROOT/plugins/*/run_server.bat`, que es la fuente. Lo que se ejecuta vive en
`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. Aunque hubiera
estado verde del todo no habría visto nada: el fallo no está en la fuente sino
en el paso que la despliega, y ese paso no lo vigilaba nadie. La forma del
defecto es «tres copias» —fuente ✅, build ✅, instalado ❌— y la única de las
tres que le importa a quien usa el conector es la última.

**Contra qué se compara, que es la decisión de diseño de este fichero.** Contra
`main`, no contra el árbol de trabajo. La propiedad que importa es «lo que corre
es lo que el equipo da por bueno», y lo que uno tiene a medias en su rama no es
eso. Comparar contra el árbol pondría rojo cualquier rama que toque un conector,
desde el primer minuto y hasta el despliegue — o sea, un rojo que no significa
nada. Y un rojo que no significa nada acaba ignorado, que es como muere una
verja (mismo razonamiento que `MEJORAS #171`). Al mergear a `main`, en cambio,
el guard SÍ se pone rojo hasta que se despliega: eso es la presión que faltaba.

**Dónde está la frontera, dicha a propósito.** Cubre los CONECTORES, que son lo
que se rompió y lo que falla en silencio (el server no arranca y el badge no lo
dice). NO cubre las skills del bundle: tienen otra vía de despliegue —el
`.skill` que se importa a mano en Cowork— y hay varias pendientes de reimportar
a sabiendas, así que exigirlas aquí daría un rojo permanente sobre un estado
aceptado. Es un límite declarado, no un olvido.

**Sobre el `skip`.** Este guard mira el estado de UNA máquina, así que donde el
plugin no esté instalado no puede decir nada. Ahí hace `skip` con el motivo
escrito entero, porque «no lo sé» no es «no hay» y un `skip` mudo aquí
reproduciría el silencio que el guard viene a romper.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.package_plugin import CONECTORES, _IGNORE, SRC

ROOT = Path(__file__).resolve().parents[1]
REGISTRO = Path.home() / ".claude" / "plugins" / "installed_plugins.json"


# --------------------------------------------------------------------------
# La referencia canónica: `main`
# --------------------------------------------------------------------------
def _rama_canonica() -> str:
    """`main` si existe, si no `origin/main`, y si ninguna, `skip` explicado."""
    for ref in ("main", "origin/main"):
        r = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        if r.returncode == 0:
            return ref
    pytest.skip(
        "ni `main` ni `origin/main` resuelven desde este checkout: sin referencia "
        "canónica no se puede decir si lo desplegado está rancio"
    )


def _ficheros_en_main(rama: str, conector: str) -> dict[str, str]:
    """Ruta relativa -> contenido, de los ficheros que `main` tiene del conector.

    Se enumeran desde git y no desde el disco: el árbol de trabajo puede tener
    ediciones a medias, y esas no son la referencia.
    """
    prefijo = f"plugins/{conector}/"
    r = subprocess.run(
        ["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", rama, "--", prefijo],
        capture_output=True, encoding="utf-8", errors="replace", check=True,
    )
    ficheros: dict[str, str] = {}
    for ruta in r.stdout.splitlines():
        ruta = ruta.strip()
        if not ruta:
            continue
        rel = Path(ruta[len(prefijo):])
        if _excluido(rel):
            continue
        contenido = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{rama}:{ruta}"],
            capture_output=True, encoding="utf-8", errors="replace", check=True,
        ).stdout
        ficheros[rel.as_posix()] = _normaliza(contenido)
    return ficheros


def _excluido(rel: Path) -> bool:
    """Las MISMAS exclusiones que el empaquetador, reusando su `_IGNORE`.

    Reescribir la lista aquí sería un segundo sitio donde se puede quedar
    rancia: si el empaquetador deja de copiar algo, el guard tiene que dejar de
    exigirlo en el mismo commit, no en el que alguien se acuerde.
    """
    partes = list(rel.parts)
    return bool(set(_IGNORE("", partes)) & set(partes))


def _normaliza(texto: str) -> str:
    """Contenido sin fin de línea: el empaquetador escribe LF y git deja CRLF.

    Medido el 2026-09-07: `dist/plugin` y el repo diferían solo en eso. Exigir
    bytes exactos daría un rojo permanente que nadie podría arreglar.
    """
    return texto.replace("\r\n", "\n")


# --------------------------------------------------------------------------
# La instalación viva
# --------------------------------------------------------------------------
def _identidad_del_plugin() -> tuple[str, str]:
    """`(nombre, marketplace)` leídos de la fuente, no escritos a mano aquí.

    Cablearlos sería un sitio más donde se puede quedar rancio el mismo dato.
    """
    nombre = json.loads(
        (SRC / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )["name"]
    marketplace = json.loads(
        (SRC / "marketplace.json").read_text(encoding="utf-8")
    )["name"]
    return nombre, marketplace


def _instalacion() -> dict:
    """La instalación viva del plugin, o `skip` con el motivo escrito entero."""
    nombre, marketplace = _identidad_del_plugin()
    clave = f"{nombre}@{marketplace}"
    if not REGISTRO.exists():
        pytest.skip(
            f"no hay registro de plugins en {REGISTRO}: esta máquina no instala "
            f"el plugin por marketplace, así que no hay despliegue que auditar"
        )
    entradas = json.loads(REGISTRO.read_text(encoding="utf-8")).get("plugins", {}).get(clave)
    if not entradas:
        pytest.skip(
            f"`{clave}` no está instalado en esta máquina ({REGISTRO}); el guard "
            f"no puede comparar lo desplegado con lo canónico. Instalarlo: "
            f"`claude plugin install {clave}`"
        )
    return entradas[0]


def _ruta_instalada() -> Path:
    ruta = Path(_instalacion()["installPath"])
    if not ruta.is_dir():
        pytest.fail(
            f"el registro dice que el plugin está en {ruta} y ese directorio no "
            f"existe: la instalación está ROTA, que no es lo mismo que ausente"
        )
    return ruta


_REDESPLIEGUE = (
    "Redesplegar, desde la RAÍZ del repo (el marketplace apunta a su `dist/`, "
    "no al de un worktree): `python -m scripts.package_plugin`, "
    "`claude plugin marketplace update <marketplace>`, "
    "`claude plugin update <plugin>@<marketplace>`. "
    "OJO, medido el 2026-09-07: `plugin update` compara por VERSIÓN, no por "
    "contenido — con la versión igual dice «already at the latest version» y no "
    "copia nada, dejando el rojo intacto. Si cambió el contenido de un conector, "
    "hay que BUMPEAR `plugin-src/.claude-plugin/plugin.json`; para arreglar un "
    "desfase ya existente sin bump, `claude plugin uninstall` + `install`"
)


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------
def test_el_registro_de_plugins_es_legible() -> None:
    """Hermano de los `test_hay_*_que_auditar`: si el registro deja de parsearse,
    todo lo de abajo se saltaría en verde sin que nadie se entere."""
    _instalacion()


def test_hay_conectores_que_auditar() -> None:
    """Si `CONECTORES` se vaciara, el guard de contenido pasaría VACÍO y verde."""
    assert [d for _, d in CONECTORES], CONECTORES


def test_la_version_instalada_es_la_de_main() -> None:
    """La versión desplegada es la que `main` declara en `plugin.json`.

    Es la comprobación barata, y es la que habría gritado el 2026-07-20:
    instalado 0.4.0, canónico 0.4.1. No basta por sí sola —se puede reconstruir
    sin bumpear la versión—, por eso existe también la de contenido.
    """
    rama = _rama_canonica()
    manifiesto = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{rama}:plugin-src/.claude-plugin/plugin.json"],
        capture_output=True, encoding="utf-8", errors="replace", check=True,
    ).stdout
    esperada = json.loads(manifiesto)["version"]
    instalada = _instalacion()["version"]
    assert instalada == esperada, (
        f"desplegado {instalada}, `{rama}` dice {esperada}. Lo que arranca "
        f"Claude Code no es lo canónico. {_REDESPLIEGUE}"
    )


@pytest.mark.parametrize("conector", [d for _, d in CONECTORES])
def test_el_conector_desplegado_ES_el_de_main(conector: str) -> None:
    """Fichero a fichero, el conector instalado coincide con el de `main`.

    La versión sola no basta, y el ejemplo lo demuestra por partida doble: lo que
    rompía `email-export` no era el número sino que su `run_server.bat` instalado
    tenía 136 bytes y le faltaba el `--repo-root`; y la primera corrida de este
    guard, ya con 0.4.1 instalado, encontró además `tiers.py` rancio — sin
    `_apertura_v1.json` ni los temporales de escritura atómica en `PROTOCOL_EDIT`,
    que entraron con `MEJORAS #149` y `#146`.
    """
    rama = _rama_canonica()
    destino = _ruta_instalada() / conector
    assert destino.is_dir(), (
        f"el conector `{conector}` no está en la instalación ({destino}): el "
        f"bundle desplegado no lleva lo que el repo declara en `.mcp.json`. "
        f"{_REDESPLIEGUE}"
    )

    canonicos = _ficheros_en_main(rama, conector)
    assert canonicos, (
        f"`{rama}` no tiene ficheros de `{conector}` -> el guard estaría "
        f"comparando contra nada"
    )

    faltan = [rel for rel in sorted(canonicos) if not (destino / rel).is_file()]
    assert not faltan, (
        f"`{conector}`: en `{rama}` y NO desplegados -> {faltan}. {_REDESPLIEGUE}"
    )

    distintos = [
        rel for rel in sorted(canonicos)
        if _normaliza((destino / rel).read_text(encoding="utf-8", errors="replace"))
        != canonicos[rel]
    ]
    assert not distintos, (
        f"`{conector}`: desplegado != `{rama}` en {distintos}. Es el defecto del "
        f"2026-07-20 otra vez: se arregló la fuente y no se instaló. {_REDESPLIEGUE}"
    )
