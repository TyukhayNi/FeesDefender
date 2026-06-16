#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consolidar_biblioteca.py - Consolidacion SUPERVISADA de la biblioteca de
jurisprudencia de la skill `oposicion-alegacion-nulidad`.

Lo ejecuta el MANTENEDOR (no cada companero). Reune las cosechas de las sesiones y
valida la biblioteca, pero NO descarga ni modifica el indice automaticamente: solo
informa. La descarga + verificacion (cendoj-bot / EUR-Lex) y la promocion al indice
son pasos manuales y gateados por el letrado, para no degradar la calidad.

Arquitectura (multi-usuario, via conector Google Drive):
  - Cada sesion sube UN fichero .json propio a la carpeta `cosecha/` del Drive
    compartido (un fichero por sesion = sin colisiones; Drive no permite append
    atomico). Las verbatim sugeridas van a `candidatas_verbatim/`.
  - El mantenedor, bajo demanda, DESCARGA esas carpetas a local (con el conector,
    desde una sesion) y ejecuta ESTE script sobre ellas.

Reporta: 1) integridad de archivos del indice; 2) ECLI citadas no presentes en el
indice; 3) citas con aplica=no/parcial; 4) huerfanas; 5) candidatas (dedup);
6) (opc.) regenera README.

Esquema de cada fichero de sesion (cosecha/<AAAA-MM-DD>_<usuario>_<expediente>.json):
  {"fecha","usuario","expediente","ecli_citadas":[...],"nuevas":[...],
   "candidatas_verbatim":[...],"resultado","notas"}

Uso:
  python consolidar_biblioteca.py --cosecha-dir <carpeta> [--candidatas-dir <carpeta>] [--regenerar-readme]
  python consolidar_biblioteca.py --cosecha <ruta.jsonl>   # legado
"""
import argparse, json, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
JURIS = os.path.join(REPO, "references", "jurisprudencia")
INDICE = os.path.join(JURIS, "indice_jurisprudencia.json")
COSECHA_DEFAULT = os.environ.get("COSECHA_PATH", os.path.join(REPO, "logs", "cosecha.jsonl"))


def cargar_indice():
    with open(INDICE, encoding="utf-8") as f:
        return json.load(f)["resoluciones"]


def leer_cosecha_jsonl(ruta):
    eventos = []
    if not ruta or not os.path.exists(ruta):
        return eventos
    with open(ruta, encoding="utf-8") as f:
        for i, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            try:
                eventos.append(json.loads(linea))
            except json.JSONDecodeError as e:
                print("  [aviso] linea %d ilegible: %s" % (i, e))
    return eventos


def leer_cosecha_dir(carpeta):
    eventos = []
    if not carpeta or not os.path.isdir(carpeta):
        return eventos
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.lower().endswith(".json"):
            continue
        try:
            with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
                ev = json.load(f)
            ev.setdefault("_fichero", nombre)
            eventos.append(ev)
        except (json.JSONDecodeError, OSError) as e:
            print("  [aviso] %s ilegible: %s" % (nombre, e))
    return eventos


def main():
    ap = argparse.ArgumentParser(description="Consolidacion de la biblioteca de jurisprudencia.")
    ap.add_argument("--cosecha-dir", default=None, help="Carpeta con .json de sesion (recomendado).")
    ap.add_argument("--cosecha", default=COSECHA_DEFAULT, help="Legado: ruta a un unico cosecha.jsonl.")
    ap.add_argument("--candidatas-dir", default=None, help="Carpeta con verbatim de candidatas_verbatim/.")
    ap.add_argument("--regenerar-readme", action="store_true", help="Regenerar README.md desde el indice")
    args = ap.parse_args()

    res = cargar_indice()
    by_ecli = {r["ecli"]: r for r in res}
    fuente = args.cosecha_dir if args.cosecha_dir else args.cosecha
    print("Indice: %d resoluciones | cosecha: %s" % (len(res), fuente))

    faltan = []
    for r in res:
        for k in ("archivo_md", "archivo_oficial"):
            p = r.get(k)
            if p and not os.path.exists(os.path.join(JURIS, p)):
                faltan.append((r["id"], k, p))
    print("\n[1] Integridad de archivos:", "OK" if not faltan else ("%d faltan" % len(faltan)))
    for x in faltan:
        print("   FALTA", x)

    eventos = leer_cosecha_dir(args.cosecha_dir) if args.cosecha_dir else leer_cosecha_jsonl(args.cosecha)
    citadas = {}
    for ev in eventos:
        for ecli in ev.get("ecli_citadas", []):
            citadas[ecli] = citadas.get(ecli, 0) + 1
    print("\n[cosecha] %d sesiones | %d ECLI distintas citadas" % (len(eventos), len(citadas)))

    nuevas = sorted(e for e in citadas if e not in by_ecli)
    print("\n[2] ECLI citadas NO en el indice (descargar+verificar+promover):", "ninguna" if not nuevas else "")
    for e in nuevas:
        print("   PENDIENTE %s  (citada %dx)" % (e, citadas[e]))

    avisos = [(e, by_ecli[e]["aplica"]) for e in citadas if e in by_ecli and by_ecli[e]["aplica"] in ("no", "parcial")]
    print("\n[3] Resoluciones citadas con aplica=no/parcial:", "ninguna" if not avisos else "")
    for e, a in avisos:
        print("   AVISO %s  aplica=%s  (%s)" % (e, a, by_ecli[e]["id"]))

    usadas = set(citadas)
    huerfanas = [r["id"] for r in res if r["ecli"] not in usadas and r["aplica"] != "no"]
    print("\n[4] Resoluciones del indice nunca citadas en cosecha: %d" % len(huerfanas))
    if huerfanas:
        print("   ", ", ".join(huerfanas))

    if args.candidatas_dir and os.path.isdir(args.candidatas_dir):
        files = [f for f in os.listdir(args.candidatas_dir) if f.lower().endswith(".md")]
        c = Counter(files)
        print("\n[5] Candidatas verbatim depositadas: %d (%d distintas)" % (len(files), len(c)))
        dups = {k: v for k, v in c.items() if v > 1}
        if dups:
            print("    duplicadas:", ", ".join("%s x%d" % (k, v) for k, v in dups.items()))

    if args.regenerar_readme:
        try:
            from generar_readme_jurisprudencia import generar
            generar(INDICE, os.path.join(JURIS, "README.md"))
            print("\n[6] README.md regenerado.")
        except Exception as e:
            print("\n[6] No se pudo regenerar README (%s)." % e)

    print("\nHecho. Recuerda: descarga/verificacion y promocion al indice son MANUALES.")


if __name__ == "__main__":
    main()
