"""Helper compartido de los sondeos de SOLO LECTURA contra el módulo de correo del CRM.

Lo usan `sondeo_copias_mail.py` y `sondeo_join_gmail_crm.py`. Aquí vive lo que los dos
necesitan y que no debe duplicarse: resolver el `.env`, abrir el cliente REST, y las dos
funciones puras que hacen las cuentas (que son las que se prueban sin red).

**Nada de este módulo escribe en el CRM.**

## Por qué `resolver_env` existe

`core.config` carga `.env` desde la raíz del árbol en el que corre. **Un worktree no tiene
`.env`** —está gitignored, no viaja—, así que cualquier script que necesite credenciales
falla ahí con un mensaje que no dice por qué. Esto lo resuelve mirando también el checkout
principal, y —lo importante— **devuelve de dónde cargó**: un cargador que no lo dice no
distingue «no había nada» de «no pude mirar». Misma lección que la blocklist de
`precommit_leak_guard` (`MEJORAS #161`), aplicada al `.env`.

La frontera completa —que TODO script que use credenciales tiene este problema, no solo
estos dos— está anotada en `docs/MEJORAS_FUTURAS.md`; aquí se remedia el ejemplo y se dice
que es un ejemplo.
"""
from __future__ import annotations

import subprocess
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Entorno
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnvCargado:
    """De dónde se cargó el `.env`, y de dónde se intentó. `rutas` nunca está vacía."""

    cargado: Path | None
    rutas: list[Path]

    @property
    def descripcion(self) -> str:
        if self.cargado is not None:
            return f"cargado de {self.cargado}"
        intentos = " · ".join(str(r) for r in self.rutas)
        return f"NO se encontró .env — se buscó en: {intentos}"


def _checkout_principal(repo: Path) -> Path | None:
    """El primer árbol de `git worktree list`, que es como git documenta el principal.

    Devuelve ``None`` si no se puede consultar o si este árbol ya ES el principal. No
    reimplementa la verificación completa de `precommit_leak_guard._resolver_principal`
    porque aquí un fallo solo cuesta un mensaje, no un falso verde de seguridad.
    """
    try:
        salida = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(repo), capture_output=True, encoding="utf-8",
            errors="replace", timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if salida.returncode != 0:
        return None
    lineas = (salida.stdout or "").splitlines()
    if not lineas or not lineas[0].startswith("worktree "):
        return None
    candidato = Path(lineas[0][len("worktree "):].strip())
    try:
        if candidato.resolve() == repo.resolve():
            return None
    except OSError:
        return None
    return candidato


def resolver_env(repo: Path = ROOT) -> EnvCargado:
    """Carga el primer `.env` que exista: este árbol, y si no, el checkout principal."""
    from dotenv import load_dotenv

    rutas = [repo / ".env"]
    principal = _checkout_principal(repo)
    if principal is not None:
        rutas.append(principal / ".env")
    for ruta in rutas:
        if ruta.is_file():
            load_dotenv(ruta, override=False)
            return EnvCargado(cargado=ruta, rutas=rutas)
    return EnvCargado(cargado=None, rutas=rutas)


# ---------------------------------------------------------------------------
# Transporte (solo lectura)
# ---------------------------------------------------------------------------

@contextmanager
def cliente_rest() -> Iterator[Any]:
    """Cede un cliente con la interfaz de ``httpx.Client``, ya con la `x-api-key`.

    Misma costura que `core.procurador_relate._transporte`: se abre un `SudespachoClient`
    y se cede su cliente interno. Se hace igual a propósito — si esa costura cambia, los
    dos sitios cambian juntos y no divergen en silencio.
    """
    from core.sync_sudespacho import SudespachoClient

    c = SudespachoClient()
    try:
        yield c._client
    finally:
        try:
            c.__exit__(None, None, None)
        except Exception:  # pragma: no cover — cierre best-effort
            pass


def filas_mail_por_uid(t: Any, uid: str, *, tope: int = 30) -> list[dict[str, Any]] | None:
    """Filas de `mail` cuyo `uid` es ese Message-ID. ``None`` si no se pudo leer.

    La distinción importa y es el motivo de que no devuelva ``[]`` en el fallo: «no hay
    filas» y «no pude preguntar» son estados distintos, y confundirlos es lo que convierte
    un sondeo en un informe tranquilizador.
    """
    from core.procurador_relate import _items, _valores

    uid = uid if uid.startswith("<") else f"<{uid}>"
    params = [
        ("properties[0]", "uid"), ("properties[1]", "cuenta"), ("properties[2]", "id"),
        ("filterGroup[condition]", "AND"),
        ("filterGroup[filterGroups][0][condition]", "AND"),
        ("filterGroup[filterGroups][0][filters][0][operator]", "equal"),
        ("filterGroup[filterGroups][0][filters][0][value]", uid),
        ("filterGroup[filterGroups][0][filters][0][property]", "uid"),
        ("itemsPerPage", str(tope)),
    ]
    r = t.get("/api/element_registries/mail", params=params)
    if r.status_code != 200:
        return None
    return [_valores(i) for i in _items(r.json())]


# ---------------------------------------------------------------------------
# Cuentas puras — lo que se prueba sin red
# ---------------------------------------------------------------------------

def distribucion_copias(
    pares: Sequence[tuple[str, str]], *, recortar_bordes: bool = True
) -> tuple[Counter[int], list[str]]:
    """`(distribución de nº de cuentas por uid, uids interiores)`.

    ``pares`` son `(uid, cuenta)` **en el orden en que los devolvió el servidor**, que se
    pide ordenado por `uid` para que las copias caigan adyacentes.

    **`recortar_bordes` descarta el primer y el último `uid` de la muestra**, cuyas copias
    pueden quedar fuera de ella. Sin eso el recuento **subestima**: un uid con cuatro
    copias del que solo entran dos en la página se cuenta como de dos. Con muestras de 0,
    1 o 2 uids no se recorta nada — no hay interior que valga.
    """
    cuentas: dict[str, set[str]] = {}
    orden: list[str] = []
    for uid, cuenta in pares:
        if not uid:
            continue
        if uid not in cuentas:
            cuentas[uid] = set()
            orden.append(uid)
        cuentas[uid].add(cuenta)
    interior = orden[1:-1] if (recortar_bordes and len(orden) > 2) else orden
    return Counter(len(cuentas[u]) for u in interior), interior


def control_positivo(observados: Iterable[Any]) -> bool:
    """¿Ha devuelto el instrumento algún valor NO vacío?

    Un sondeo cuyo resultado es siempre «cero» puede estar midiendo o puede estar roto, y
    las dos cosas se leen igual. Esta función es la línea que las separa, y existe porque
    el 2026-09-07 un conteo escrito contra un atributo inexistente devolvió «cero
    relaciones» para los 32 correos de la muestra y esa salida se publicó como refutación
    de un diseño. Todo sondeo de este paquete la imprime.
    """
    return any(bool(o) for o in observados)
