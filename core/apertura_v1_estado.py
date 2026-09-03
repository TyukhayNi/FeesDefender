"""Estado durable por ronda de la apertura V1 — Plan 5, Task 8b.

La spec lo hace obligatorio «desde la primera entrega» (§11, tabla de riesgos:
«reanudacion sin generacion comun -> fase verde sobre inputs obsoletos»). Sin esto,
«reanudar tras un corte» es una afirmacion del autor y no una propiedad del sistema — que
es exactamente lo que la R-A del Plan 5 senalo (HA-01) sobre la rev. 1 de ese plan.

**Lo que NO es:** el `operations` completo del bloque 2 de la spec. No reconcilia dos
escritores ni versiona artefactos. Lo que da es que una ronda muerta a mitad se DETECTE,
en vez de que la siguiente corrida trate su salida como buena.
"""
from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from pathlib import Path

_FICHERO = "_apertura_v1.json"

#: Lo que este modulo deposita en `00_Input` y que **no es documento del caso**. Se
#: declara aqui, junto a quien lo escribe, para que el guard
#: `tests/test_apertura_v1_control_files.py` lo compruebe contra TODOS los registros que
#: clasifican ficheros de esa carpeta. La R-B midio que sin esa comprobacion el fichero
#: entraba en el inventario probatorio y provocaba CONFLICT en un checkin.
FICHEROS_CONTROL: tuple[str, ...] = (_FICHERO,)
PREFIJOS_CONTROL: tuple[str, ...] = (".apertura_v1.",)


@dataclasses.dataclass(frozen=True)
class RondaV1:
    ronda_id: str
    iniciada: str
    terminada: str | None = None
    estado: str | None = None
    etapas: dict[str, str] = dataclasses.field(default_factory=dict)

    def sin_cerrar(self) -> bool:
        return self.terminada is None


def _ruta(case_dir: Path) -> Path:
    return Path(case_dir) / "00_Input" / _FICHERO


def leer(case_dir: Path) -> RondaV1 | None:
    """`None` si no hay, o si el fichero esta roto.

    Un estado ilegible se trata como ausente, que es el lado seguro: lo contrario seria
    decidir sobre datos inventados. Y se exigen las dos claves minimas —un JSON valido
    con otra forma no es una ronda—, porque «se pudo parsear» no es «es lo que espero».
    """
    f = _ruta(case_dir)
    if not f.is_file():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(d, dict) or "ronda_id" not in d or "iniciada" not in d:
        return None
    etapas = d.get("etapas")
    return RondaV1(
        ronda_id=str(d["ronda_id"]),
        iniciada=str(d["iniciada"]),
        terminada=d.get("terminada"),
        estado=d.get("estado"),
        etapas=dict(etapas) if isinstance(etapas, dict) else {},
    )


def _escribir(case_dir: Path, ronda: RondaV1) -> None:
    """Atomica: temporal en el MISMO directorio + `os.replace`.

    Escribir en sitio deja un JSON truncado si el proceso muere a mitad, y entonces la
    ronda siguiente no sabe que hubo una — que es justo la propiedad que este fichero
    existe para dar. El temporal va al mismo directorio porque `os.replace` solo es
    atomico dentro del mismo sistema de ficheros.
    """
    f = _ruta(case_dir)
    f.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = json.dumps(dataclasses.asdict(ronda), ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(f.parent), prefix=".apertura_v1.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(cuerpo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, f)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def abrir(case_dir: Path, *, ronda_id: str, ahora: str) -> RondaV1:
    """Marca el inicio de una ronda. Se escribe ANTES de correr nada: si la corrida
    muere, lo que queda en disco dice que empezo y no termino."""
    r = RondaV1(ronda_id=ronda_id, iniciada=ahora)
    _escribir(case_dir, r)
    return r


def cerrar(case_dir: Path, ronda: RondaV1, *, estado: str,
           etapas: dict[str, str], ahora: str) -> None:
    """Marca el cierre con el estado alcanzado y el resultado por etapa."""
    _escribir(case_dir, dataclasses.replace(
        ronda, terminada=ahora, estado=estado, etapas=dict(etapas)))
