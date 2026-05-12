"""Deanonimizador de documentos.

Versión adaptada del original de Expedientes Seguros para uso embebido en
FeesDefender. Aporta una función pura ``deanonimizar_texto(texto, mapa)``
sin I/O, consumida desde el resto del core y desde tests.

Mejora sobre el original: las etiquetas se procesan ordenadas por longitud
descendente, evitando que ``[NOMBRE]`` matchee dentro de hipotéticas
etiquetas más largas que la contengan como subcadena. Con el formato
actual (etiquetas siempre terminadas en ``]``) el problema no se materializa,
pero el orden defensivo cuesta cero y previene futuras regresiones.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from core.anon.exceptions import AnonError


# ---------------------------------------------------------------------------
# API pura — sin I/O
# ---------------------------------------------------------------------------

def deanonimizar_texto(texto: str, mapa: dict[str, str]) -> str:
    """Sustituye las etiquetas del texto por sus valores reales.

    Args:
        texto: Texto anonimizado (contiene etiquetas tipo ``[NOMBRE]``,
            ``[DNI]``, ``[NOMBRE_3]``, etc.).
        mapa: Diccionario ``etiqueta -> valor_real``. Acepta tanto la
            estructura ``mapa_inverso`` de ``MapaEntidades`` como el
            ``"mapa"`` del JSON exportado.

    Returns:
        El texto con las etiquetas sustituidas por su valor real.

    Notas:
        - Iteración por longitud descendente: defensa frente a etiquetas
          que sean subcadena de otras. Cuesta O(n log n) sobre el conjunto
          de etiquetas, despreciable.
        - Si una etiqueta del mapa no aparece en el texto, simplemente se
          ignora (comportamiento gracious heredado del original).
    """
    for etiqueta in sorted(mapa, key=len, reverse=True):
        if etiqueta in texto:
            texto = texto.replace(etiqueta, mapa[etiqueta])
    return texto


# ---------------------------------------------------------------------------
# I/O — operación sobre fichero (uso CLI / scripts)
# ---------------------------------------------------------------------------

#: Nombre canónico de la subcarpeta de output anonimizado en FeesDefender.
#: Replicado aquí en lugar de importado desde ``core.anon.mapa_caso`` para
#: mantener este módulo libre de dependencias del resto del core (lo
#: consume el CLI standalone y los tests rápidos).
_SUBDIR_ANONIMIZADO = "06_Anonimizado"
_MAPA_CASO_FILENAME = "_mapa_caso.json"


def _localizar_mapa(ruta_md: Path, nombre_base: str) -> Path | None:
    """Busca el JSON con el mapa de entidades asociado al .md anonimizado.

    Orden de búsqueda (devuelve el primero que existe en disco):

      1. **Legacy adyacente** — ``<ruta_md>.parent / "{nombre_base}_mapa.json"``.
         Estructura plana del Anonimizador original de Expedientes Seguros:
         un ``_mapa.json`` por documento, en la misma carpeta que el .md.

      2. **Legacy ``_para_IA``** — carpeta hermana ``_anonimizados/`` cuando
         el .md vive en ``_para_IA/``. Layout antiguo de Expedientes Seguros.

      3. **Mapa de caso FeesDefender** — ``06_Anonimizado/_mapa_caso.json``
         del ancestro inmediato. Formato nuevo introducido en la absorción
         del Anonimizador (2026-05-07): un único mapa compartido por caso,
         escrito por ``core.anon.api.anonimizar_caso`` vía
         ``core.anon.mapa_caso.guardar_mapa_caso``.

      4. **Fallback por frontmatter** — si el .md declara ``mapa_caso_path``
         (o el alias ``mapa_entidades``) en su frontmatter YAML, ese path
         se usa tal cual. Sirve para cualquier .md que no esté en el árbol
         canónico ``…/06_Anonimizado/…`` pero quiera referenciar un mapa
         arbitrario. Acepta rutas absolutas o relativas al directorio del
         .md.

    Los formatos 1 y 2 tienen prioridad sobre el 3 por retrocompatibilidad
    estricta: si un .md trae su mapa adyacente, ese manda aunque viva
    dentro de un caso FeesDefender. El nivel 4 es el último recurso.

    Devuelve ``None`` si ninguno de los cuatro niveles localiza un mapa
    existente.
    """
    # Nivel 1 — legacy adyacente (estructura plana).
    legacy_adyacente = ruta_md.parent / f"{nombre_base}_mapa.json"
    if legacy_adyacente.exists():
        return legacy_adyacente

    # Nivel 2 — legacy `_para_IA` ↔ `_anonimizados`.
    partes = ruta_md.parts
    for i, p in enumerate(partes):
        if p == "_para_IA":
            nuevas = list(partes)
            nuevas[i] = "_anonimizados"
            candidato = Path(*nuevas).parent / f"{nombre_base}_mapa.json"
            if candidato.exists():
                return candidato
            break

    # Nivel 3 — `_mapa_caso.json` del ancestro `06_Anonimizado/`.
    for ancestro in ruta_md.parents:
        if ancestro.name == _SUBDIR_ANONIMIZADO:
            candidato = ancestro / _MAPA_CASO_FILENAME
            if candidato.exists():
                return candidato
            break

    # Nivel 4 — fallback por frontmatter del propio .md.
    candidato_fm = _mapa_desde_frontmatter(ruta_md)
    if candidato_fm is not None and candidato_fm.exists():
        return candidato_fm

    return None


def _mapa_desde_frontmatter(ruta_md: Path) -> Path | None:
    """Devuelve el path del mapa declarado en el frontmatter, si lo hay.

    Lee el frontmatter YAML del .md con ``core.utils.read_md`` (import
    diferido para no acoplar el módulo a ``core.utils`` en el resto de
    rutas). Acepta dos campos:

      - ``mapa_caso_path``: path absoluto o relativo al directorio del .md.
      - ``mapa_entidades``: alias semántico (mismo contrato).

    Si la lectura falla por cualquier motivo (fichero inexistente,
    frontmatter ausente, YAML malformado, etc.), devuelve ``None`` —
    nunca propaga la excepción, es un fallback opcional.
    """
    try:
        from core.utils import read_md  # import diferido
        meta, _ = read_md(ruta_md)
    except Exception:
        return None

    if not isinstance(meta, dict):
        return None

    declarado = meta.get("mapa_caso_path") or meta.get("mapa_entidades")
    if not declarado:
        return None

    candidato = Path(str(declarado))
    if not candidato.is_absolute():
        candidato = (ruta_md.parent / candidato).resolve()
    return candidato


def deanonimizar(ruta_md: str | Path) -> Path:
    """Deanonimiza un .md generado por el módulo y devuelve la ruta del .md
    deanonimizado resultante.

    Lanza ``FileNotFoundError`` si el .md o su mapa no existen.
    """
    ruta = Path(ruta_md)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encuentra el .md anonimizado: {ruta}")

    # Python 3.9+: removesuffix ancla al final, evitando el bug del
    # `replace("_anonimizado", "")` original cuando el sufijo aparece
    # dentro del nombre.
    nombre_base = ruta.stem.removesuffix("_anonimizado")
    ruta_mapa = _localizar_mapa(ruta, nombre_base)
    if ruta_mapa is None:
        raise FileNotFoundError(
            f"No se encuentra el mapa para {ruta.name}. "
            f"Esperado: {nombre_base}_mapa.json en la carpeta del .md."
        )

    print(f"\n{'='*55}")
    print(f"Deanonimizando: {ruta.name}")
    print(f"Usando mapa:    {ruta_mapa.name}")
    print(f"{'='*55}")

    datos = json.loads(ruta_mapa.read_text(encoding="utf-8"))
    mapa = datos.get("mapa", {})  # etiqueta -> valor_real
    print(f"  Entidades en mapa: {len(mapa)}")

    texto = ruta.read_text(encoding="utf-8")
    texto = deanonimizar_texto(texto, mapa)

    # Actualizar cabecera del .md
    texto = re.sub(
        r'> \*\*Documento anonimizado\*\*.*\n',
        f'> **Documento deanonimizado** | {datetime.now().strftime("%d/%m/%Y %H:%M")}\n',
        texto,
    )

    ruta_salida = ruta.parent / f"{nombre_base}_deanonimizado.md"
    ruta_salida.write_text(texto, encoding="utf-8")

    print(f"  Generado: {ruta_salida.name}")
    print(f"{'='*55}\n")
    return ruta_salida


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    # UTF-8 wrap solo en uso CLI (Windows). En uso embebido (Streamlit /
    # pipeline / tests) este bloque no se ejecuta.
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    if len(sys.argv) < 2:
        print("Uso: python -m core.anon.deanonimizar <archivo_anonimizado.md>")
        sys.exit(1)

    for archivo in sys.argv[1:]:
        if archivo.startswith("--"):
            continue
        try:
            deanonimizar(archivo)
        except (FileNotFoundError, AnonError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    if "--pipeline" not in sys.argv:
        try:
            input("Pulsa Enter para cerrar...")
        except EOFError:
            pass
