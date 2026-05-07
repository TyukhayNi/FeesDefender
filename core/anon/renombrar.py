# -*- coding: utf-8 -*-
"""
renombrar.py
============
Aplica prefijo YYYYMMDD a los .md anonimizados segun la fecha detectada en
el contenido del documento.

Renombra en pareja:
  - _anonimizados/<stem>_anonimizado.md   -> _anonimizados/<YYYYMMDD> - <stem>.md
  - _anonimizados/<stem>_mapa.json        -> _anonimizados/<YYYYMMDD> - <stem>_mapa.json
  - _para_IA/<stem>_anonimizado.md        -> _para_IA/<YYYYMMDD> - <stem>.md

Logica de deteccion:
  - Busca en cabecera (primeros 5000 chars) y cola (ultimos 5000)
  - Prioridad: texto en cabecera > texto en cola > numerica mas antigua
  - Descarta fechas de los ultimos 30 dias (ruido de anonimizacion/OCR/hoy)
  - Descarta fechas futuras
  - Si no hay fecha, solo quita el sufijo _anonimizado
"""
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def extraer_fechas(texto):
    resultados = []
    for m in re.finditer(
        r"(\d{1,2})\s+de\s+([a-zA-Zñ]+)\s+de[l]?\s+(\d{4})",
        texto,
        re.IGNORECASE,
    ):
        dia, mes_str, anio = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        if mes_str in MESES_ES:
            try:
                d = date(anio, MESES_ES[mes_str], dia)
                resultados.append((d, m.group(0), "texto"))
            except ValueError:
                pass
    for m in re.finditer(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", texto):
        dia, mes, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= dia <= 31 and 1990 <= anio <= 2030:
            try:
                d = date(anio, mes, dia)
                resultados.append((d, m.group(0), "numerico"))
            except ValueError:
                pass
    return resultados


def mejor_fecha(texto, hoy=None, dias_umbral: int = 30):
    """Busca fecha en cabecera (primeros 5000 chars) y cola (ultimos 5000).
    Prioridad: texto en cabecera > texto en cola > numerica mas antigua.

    FeesDefender 2026-05-07: parametrizado ``dias_umbral`` (antes hardcoded
    a 30) para que la fachada pueda ajustarlo según el escenario. Para
    documentos en preparación (demanda que se procesa el día siguiente del
    evento) conviene un umbral más corto, e.g. 7 días.
    """
    if hoy is None:
        hoy = date.today()
    umbral_reciente = hoy - timedelta(days=dias_umbral)

    def filtrar(lst):
        return [f for f in lst if f[0] <= umbral_reciente and f[0] <= hoy]

    fechas_cabecera = filtrar(extraer_fechas(texto[:5000]))
    # Cola: segmento no solapado con la cabecera
    if len(texto) > 10000:
        cola = texto[-5000:]
    elif len(texto) > 5000:
        cola = texto[5000:]
    else:
        cola = ""
    fechas_cola = filtrar(extraer_fechas(cola)) if cola else []

    en_texto_cab = [f for f in fechas_cabecera if f[2] == "texto"]
    if en_texto_cab:
        return en_texto_cab[0]
    en_texto_cola = [f for f in fechas_cola if f[2] == "texto"]
    if en_texto_cola:
        return en_texto_cola[0]
    todas_num = fechas_cabecera + fechas_cola
    if todas_num:
        return min(todas_num, key=lambda f: f[0])
    return None


def quitar_sufijo_anonimizado(stem: str) -> str:
    if stem.endswith("_anonimizado"):
        return stem[: -len("_anonimizado")]
    return stem


def tiene_prefijo_fecha(stem: str) -> bool:
    """Detecta si el stem ya empieza por YYYYMMDD - """
    return bool(re.match(r"^\d{8}\s*-\s*", stem))


def renombrar_expediente(carpeta_expediente: Path, log=print):
    """Renombra los .md y _mapa.json en _anonimizados/ y _para_IA/."""
    anonim_dir = carpeta_expediente / "_anonimizados"
    para_ia_dir = carpeta_expediente / "_para_IA"

    if not anonim_dir.exists():
        return 0

    renombrados = 0
    saltados = 0

    # Itera todos los .md en _anonimizados/; acepta tanto '<x>_anonimizado.md'
    # (recien salidos del pipeline) como '<x>.md' (ya pasaron por una version
    # anterior del renombrador que dejo sin prefijo por no encontrar fecha)
    for md in sorted(anonim_dir.glob("*.md")):
        stem_original = md.stem
        stem_base = quitar_sufijo_anonimizado(stem_original)

        if tiene_prefijo_fecha(stem_base):
            # Ya tiene prefijo, no tocar
            saltados += 1
            continue

        texto = md.read_text(encoding="utf-8", errors="replace")
        mf = mejor_fecha(texto)
        if mf:
            prefijo = mf[0].strftime("%Y%m%d") + " - "
            nuevo_base = prefijo + stem_base
        else:
            nuevo_base = stem_base  # sin prefijo, pero quita _anonimizado

        if nuevo_base == stem_original:
            # Noop: el nombre ya es el final (ya se proceso sin fecha antes)
            saltados += 1
            continue

        # Renombrar .md
        nuevo_md = anonim_dir / (nuevo_base + ".md")
        if nuevo_md.exists() and nuevo_md != md:
            log(f"  [COLISION] {nuevo_md.name} ya existe, salto {md.name}")
            saltados += 1
            continue
        md.rename(nuevo_md)

        # Renombrar _mapa.json
        viejo_mapa = anonim_dir / (stem_base + "_mapa.json")
        if viejo_mapa.exists():
            nuevo_mapa = anonim_dir / (nuevo_base + "_mapa.json")
            if nuevo_mapa.exists() and nuevo_mapa != viejo_mapa:
                log(f"  [COLISION] {nuevo_mapa.name} ya existe")
            else:
                viejo_mapa.rename(nuevo_mapa)

        # Renombrar/copiar en _para_IA/
        if para_ia_dir.exists():
            viejo_para_ia = para_ia_dir / md.name  # el nombre antiguo
            if viejo_para_ia.exists():
                nuevo_para_ia = para_ia_dir / (nuevo_base + ".md")
                if nuevo_para_ia.exists() and nuevo_para_ia != viejo_para_ia:
                    log(f"  [COLISION] en _para_IA: {nuevo_para_ia.name}")
                else:
                    viejo_para_ia.rename(nuevo_para_ia)

        log(f"  {stem_original}.md -> {nuevo_base}.md")
        renombrados += 1

    return renombrados


def procesar_raiz(raiz: Path, log=print):
    """Recorre todas las carpetas expediente bajo raiz y renombra."""
    total_renombrados = 0
    total_expedientes = 0
    for anonim_dir in raiz.rglob("_anonimizados"):
        if not anonim_dir.is_dir():
            continue
        exp = anonim_dir.parent
        total_expedientes += 1
        log("")
        log(f"=== {exp.relative_to(raiz)} ===")
        r = renombrar_expediente(exp, log=log)
        total_renombrados += r
        log(f"  renombrados: {r}")
    log("")
    log(f"TOTAL: {total_renombrados} ficheros renombrados en {total_expedientes} expedientes")
    return total_renombrados


# ══════════════════════════════════════════════════════════════════════════════
# API PARA ESTRUCTURA PLANA (FeesDefender — Fase 2)
# ══════════════════════════════════════════════════════════════════════════════
#
# Diferencia respecto al original: en Expedientes Seguros cada expediente
# tenía dos subcarpetas (``_anonimizados/`` y ``_para_IA/``) y el renombrador
# trabajaba sobre las dos en paralelo. En FeesDefender la estructura es
# plana — los .md anonimizados viven directamente en ``06_Anonimizado/`` —
# y el mapa es uno solo por caso (``_mapa_caso.json``), no uno por documento.

def renombrar_carpeta(
    carpeta: Path,
    log=print,
    *,
    dias_umbral: int = 30,
) -> list[tuple[Path, Path]]:
    """Aplica prefijo YYYYMMDD a los .md de una carpeta plana.

    Usa la misma lógica de ``mejor_fecha`` que ``renombrar_expediente``,
    pero opera sobre una estructura sin ``_anonimizados/`` ni ``_para_IA/``.

    Args:
        carpeta: Carpeta plana con ``*.md`` y, opcionalmente, ``*_mapa.json``
            asociados (legacy de docs migrados de Expedientes Seguros).
        log: Función para reportar progreso (``print`` por defecto).
        dias_umbral: Días "recientes" a descartar (default 30, igual que
            el original; usa 7 para documentos en preparación).

    Returns:
        Lista de tuplas ``(origen, destino)`` con los renombres realizados.
        Vacía si nada cambió (todos ya tenían prefijo o no había fechas).
    """
    carpeta = Path(carpeta)
    renombrados: list[tuple[Path, Path]] = []

    if not carpeta.is_dir():
        return renombrados

    for md in sorted(carpeta.glob("*.md")):
        # Saltar índices y archivos auxiliares (empiezan por '_')
        if md.name.startswith("_"):
            continue

        stem_original = md.stem
        stem_base = quitar_sufijo_anonimizado(stem_original)

        if tiene_prefijo_fecha(stem_base):
            continue  # ya tiene prefijo

        try:
            texto = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        mf = mejor_fecha(texto, dias_umbral=dias_umbral)
        if mf:
            nuevo_base = mf[0].strftime("%Y%m%d") + " - " + stem_base
        else:
            nuevo_base = stem_base  # sin prefijo, pero quita _anonimizado

        if nuevo_base == stem_original:
            continue  # noop

        nuevo_md = carpeta / (nuevo_base + ".md")
        if nuevo_md.exists() and nuevo_md != md:
            log(f"  [COLISION] {nuevo_md.name} ya existe, salto {md.name}")
            continue
        md.rename(nuevo_md)

        # Renombrar también el _mapa.json asociado (legacy: 1 mapa por doc)
        viejo_mapa = carpeta / (stem_base + "_mapa.json")
        if viejo_mapa.exists():
            nuevo_mapa = carpeta / (nuevo_base + "_mapa.json")
            if not nuevo_mapa.exists():
                viejo_mapa.rename(nuevo_mapa)

        log(f"  {stem_original}.md -> {nuevo_base}.md")
        renombrados.append((md, nuevo_md))

    return renombrados


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python renombrar.py <carpeta_raiz>")
        sys.exit(1)
    raiz = Path(sys.argv[1])
    if not raiz.exists():
        print(f"ERROR: no existe {raiz}")
        sys.exit(1)
    procesar_raiz(raiz)
