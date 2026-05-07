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

def _localizar_mapa(ruta_md: Path, nombre_base: str) -> Path | None:
    """Busca el ``_mapa.json`` asociado a un .md anonimizado.

    Orden de búsqueda:
      1. Misma carpeta que el .md (estructura plana de FeesDefender).
      2. Carpeta hermana ``_anonimizados/`` (estructura legacy de Expedientes
         Seguros, cuando el .md vive en ``_para_IA/``).

    Devuelve ``None`` si no encuentra el fichero en ninguna ubicación.
    """
    candidatos = [ruta_md.parent / f"{nombre_base}_mapa.json"]
    partes = ruta_md.parts
    for i, p in enumerate(partes):
        if p == "_para_IA":
            nuevas = list(partes)
            nuevas[i] = "_anonimizados"
            candidatos.append(Path(*nuevas).parent / f"{nombre_base}_mapa.json")
            break
    return next((c for c in candidatos if c.exists()), None)


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
