"""Auditoria READ-ONLY: correos incrustados en el cuerpo de un atom que NO tienen
fichero-atom propio ("no separados").

Detector tolerante sobre los .md renderizados (recall-first, para revision humana):
el render mete lineas en blanco entre cabeceras y parte direcciones <\\nx\\n>, asi que
no se usa el segmentador del motor (pensado para las fuentes HTML). Se reutilizan solo
el parser de fechas (_parse_fecha) y el slug de asunto del motor para no derivar.

Cruza cada cabecera incrustada contra corpus.jsonl (lista canonica de atoms) por
remitente + dia + asunto (prefijos RE:/RV:/Fwd: normalizados). No escribe en el
expediente: vuelca el informe a scripts/_out_correos_no_separados.md + resumen stdout.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\Users\tnm33\Dev\FeesDefender")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.email_atomize.inline import _parse_fecha  # noqa: E402
from core.email_export import _slug_descripcion  # noqa: E402

BASE = Path(
    r"G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS\Barcelona"
    r"\BaRS1 - Tibidabo 8 - (W-02VND1) - Vuelta\01_Procesado\Emails"
)
MENSAJES = BASE / "mensajes"
CORPUS = BASE / "corpus.jsonl"
COLA = BASE / "_revision" / "cola.md"
OUT = Path(r"C:\Users\tnm33\Dev\FeesDefender\scripts\_out_correos_no_separados.md")

_RE_PREFIX = re.compile(r"(?i)^\s*(?:re|rv|fwd|fw|tr|aw|wg)\s*:\s*")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")

RE_FWD = re.compile(
    r"(?i)^\s*-{2,}\s*(?:forwarded message|mensaje reenviado|reenviado|begin forwarded"
    r" message|original message|mensaje original)\b")
RE_APPLE = re.compile(r"(?i)^\s*(?:el|on)\b.{0,90}?(?:escribi[oó]|wrote|va\s+escriure)\s*:\s*$")
RE_DEFROM = re.compile(r"(?i)^\s*(?:de|from)\s*:\s*(.*)$")
RE_SENT = re.compile(r"(?i)^\s*(?:enviado(?:\s+el)?|sent|fecha|date)\s*:\s*(.*)$")
RE_SUBJ = re.compile(r"(?i)^\s*(?:asunto|subject)\s*:\s*(.*)$")
RE_TO = re.compile(r"(?i)^\s*(?:para|to|cc|cco|bcc)\s*:")
RE_ANYLABEL = re.compile(
    r"(?i)^\s*(?:de|from|enviado|sent|fecha|date|para|to|asunto|subject|cc|cco|bcc)\s*:")


def strip_prefix(s: str) -> str:
    prev, s = None, (s or "")
    while prev != s:
        prev, s = s, _RE_PREFIX.sub("", s).strip()
    return s


def subj_key(s: str) -> str:
    s = strip_prefix(s or "")
    if not s.strip():
        return ""
    sk = _slug_descripcion(s)
    return "" if sk == "sin_asunto" else sk   # el centinela vacio no debe casar nada


def day(iso: str) -> str:
    return (iso or "")[:10] if iso and iso != "0000-00-00" else ""


def normaliza_render(body: str) -> str:
    """Repara los artefactos del render: une <\\n email \\n> y quita lineas en blanco
    (asi las cabeceras De/Enviado/Para/Asunto quedan contiguas)."""
    body = re.sub(r"<\s*\n\s*([\w.+-]+@[\w.-]+)\s*\n\s*>", r"<\1>", body)
    body = re.sub(r"\n\s*<\s*\n", r" <", body)
    lines = [l.rstrip() for l in body.splitlines()]
    return "\n".join(l for l in lines if l.strip())


# --------------------------------------------------------------------------- #
# 1) Atoms canonicos
# --------------------------------------------------------------------------- #
atoms = []
for line in CORPUS.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    o = json.loads(line)
    if "_README" in o or o.get("_tipo") == "corpus":
        continue
    atoms.append(o)

by_de_day = defaultdict(list)
by_de_day_subj = set()
by_de_subj = set()
for a in atoms:
    de = (a.get("de") or "").strip().lower()
    d = day(a.get("fecha"))
    sk = subj_key(a.get("asunto"))
    if de and d:
        by_de_day[(de, d)].append(a)
    if de and d and sk:
        by_de_day_subj.add((de, d, sk))
    if de and sk:
        by_de_subj.add((de, sk))

# --------------------------------------------------------------------------- #
# 2) Cola de revision del motor (para marcar solapamiento)
# --------------------------------------------------------------------------- #
cola_portadores = set()
if COLA.exists():
    for line in COLA.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(MSG-\d+)\s*\|", line)
        if m:
            cola_portadores.add(m.group(1))

# --------------------------------------------------------------------------- #
# 3) Detector de cabeceras incrustadas
# --------------------------------------------------------------------------- #
_FM = {k: re.compile(p) for k, p in {
    "msg_id": r"(?m)^msg_id:\s*(\S+)",
    "fecha": r"(?m)^fecha:\s*(\S+)",
    "capa": r"(?m)^capa:\s*(\S+)",
}.items()}


def split_front(text: str):
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if l.strip() == "---"]
    if len(starts) >= 2:
        return "\n".join(lines[starts[0] + 1:starts[1]]), "\n".join(lines[starts[1] + 1:])
    return "", text


def fm_get(fm, key):
    m = _FM[key].search(fm)
    return (m.group(1).strip() if m else "")


def _es_inicio(lines, i):
    """Estilo de cabecera incrustada que empieza en lines[i], o None."""
    l = lines[i]
    if RE_FWD.match(l):
        return "fwd"
    if RE_APPLE.match(l):
        return "apple"
    if RE_DEFROM.match(l):
        for j in range(i + 1, min(i + 4, len(lines))):
            if RE_SENT.match(lines[j]) or RE_SUBJ.match(lines[j]) or RE_TO.match(lines[j]):
                return "outlook"
    if RE_SENT.match(l):                       # forward que arranca por Fecha/Date
        for j in range(i + 1, min(i + 3, len(lines))):
            if RE_SUBJ.match(lines[j]):
                return "sent_subj"
    return None


def _extrae(window_lines, estilo):
    """(de, fecha_iso, asunto) desde la ventana de cabecera."""
    wl = window_lines
    full = " ".join(wl)
    # --- remitente ---
    de = ""
    if estilo == "apple":
        m = RE_EMAIL.search(wl[0])
        de = m.group(0).lower() if m else ""
    else:
        # texto desde el primer De/From hasta el primer Para/To (excluye destinatarios)
        de_idx = next((k for k, l in enumerate(wl) if RE_DEFROM.match(l)), None)
        if de_idx is not None:
            zona = []
            for l in wl[de_idx:]:
                if RE_TO.match(l):
                    break
                zona.append(l)
            m = RE_EMAIL.search(" ".join(zona))
            de = m.group(0).lower() if m else ""
        if not de:                              # fwd sin De claro: 1er email antes de To
            pre = full
            mto = RE_TO.search(full)
            if mto:
                pre = full[:mto.start()]
            m = RE_EMAIL.search(pre)
            de = m.group(0).lower() if m else ""
    # --- fecha ---
    fecha = "0000-00-00"
    for l in wl:
        ms = RE_SENT.match(l)
        if ms and ms.group(1).strip():
            fecha, _ = _parse_fecha(ms.group(1))
            if fecha != "0000-00-00":
                break
    if fecha == "0000-00-00":
        fecha, _ = _parse_fecha(full)
    # --- asunto ---
    asunto = ""
    for l in wl:
        msj = RE_SUBJ.match(l)
        if msj:
            asunto = msj.group(1).strip()
            break
    return de, fecha, asunto


def detectar(body: str):
    lines = normaliza_render(body).splitlines()
    out, i, n = [], 0, len(lines)
    while i < n:
        estilo = _es_inicio(lines, i)
        if not estilo:
            i += 1
            continue
        # ventana de cabecera: hasta Asunto/Subject inclusive, o hasta 8 lineas / fin de etiquetas
        win = [lines[i]]
        j, visto_subj = i + 1, False
        while j < min(i + 9, n):
            win.append(lines[j])
            if RE_SUBJ.match(lines[j]):
                visto_subj = True
                j += 1
                break
            # apple/sent sin mas etiquetas: corta tras 1-2 lineas no-etiqueta
            if estilo == "apple" and not RE_ANYLABEL.match(lines[j]) and not RE_FWD.match(lines[j]):
                break
            j += 1
        de, fecha, asunto = _extrae(win, estilo)
        out.append({"estilo": estilo, "de": de, "fecha": fecha, "asunto": asunto,
                    "extract": re.sub(r"\s+", " ", " ".join(win)).strip()[:150]})
        i = j if j > i else i + 1
    return out


# --------------------------------------------------------------------------- #
# 4) Escaneo
# --------------------------------------------------------------------------- #
findings = []
total_citas = 0
md_files = sorted(MENSAJES.glob("*.md"))
for md in md_files:
    text = md.read_text(encoding="utf-8", errors="replace")
    fm, body = split_front(text)
    portador = fm_get(fm, "msg_id") or md.stem
    p_capa = fm_get(fm, "capa")
    for h in detectar(body):
        if not (h["de"] or day(h["fecha"]) or h["asunto"]):
            continue
        total_citas += 1
        de, d, sk = h["de"], day(h["fecha"]), subj_key(h["asunto"])
        matched = ""
        if de and d and sk and (de, d, sk) in by_de_day_subj:
            matched = "de+dia+asunto"
        elif de and sk and (de, sk) in by_de_subj:
            matched = "de+asunto"
        elif de and d and not sk and (de, d) in by_de_day:
            matched = "de+dia (sin asunto)"
        if matched:
            continue
        conf = "alta" if (de and d) else ("media" if (de or d or sk) else "baja")
        findings.append({
            "portador": portador, "p_capa": p_capa, "estilo": h["estilo"],
            "de": de, "fecha": d or "?", "asunto": h["asunto"].strip(),
            "conf": conf, "extract": h["extract"],
            "dedup": (de, d, sk),
        })

# --------------------------------------------------------------------------- #
# 5) Dedup por (de,dia,asunto) -> mismo correo citado en varios portadores
# --------------------------------------------------------------------------- #
distintos = {}
for f in findings:
    k = f["dedup"]
    if any(k):
        if k not in distintos:
            distintos[k] = dict(f, portadores=[f["portador"]])
        else:
            distintos[k]["portadores"].append(f["portador"])
    else:
        distintos[id(f)] = dict(f, portadores=[f["portador"]])

orden = {"alta": 0, "media": 1, "baja": 2}
dist = sorted(distintos.values(), key=lambda f: (orden[f["conf"]], f["fecha"], f["de"]))


# --------------------------------------------------------------------------- #
# 6) Informe
# --------------------------------------------------------------------------- #
def esc(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


n_alta = sum(1 for f in dist if f["conf"] == "alta")
n_media = sum(1 for f in dist if f["conf"] == "media")
n_baja = sum(1 for f in dist if f["conf"] == "baja")

L = []
L.append("# Correos incrustados SIN atom propio (no separados)\n")
L.append("Detector tolerante sobre los 366 .md renderizados, cruzado contra corpus.jsonl.")
L.append("Cruce dia-granular (remitente + dia + asunto sin prefijos). Recall-first: revisar a mano.\n")
L.append(f"- Atoms en corpus.jsonl: **{len(atoms)}**  ·  .md escaneados: **{len(md_files)}**")
L.append(f"- Cabeceras incrustadas identificables: **{total_citas}**")
L.append(f"- Sin atom equivalente -> ocurrencias: **{len(findings)}**  ·  correos distintos: **{len(dist)}**")
L.append(f"- Distintos por confianza: alta {n_alta} · media {n_media} · baja {n_baja}\n")
L.append("Confianza: **alta** = cabecera con remitente y fecha; **media** = cabecera parcial.\n")
L.append("| # | Conf | Remitente | Fecha | Asunto | Estilo | Portador(es) | ¿portador en cola motor? | Extracto |")
L.append("| - | ---- | --------- | ----- | ------ | ------ | ------------ | ------------------------ | -------- |")
for idx, f in enumerate(dist, 1):
    ports = ", ".join(sorted(set(f["portadores"])))
    encola = "sí" if any(p in cola_portadores for p in f["portadores"]) else "no"
    L.append("| {n} | {c} | {de} | {fe} | {asu} | {es} | {po} | {ec} | {ex} |".format(
        n=idx, c=f["conf"], de=esc(f["de"] or "—"), fe=f["fecha"],
        asu=esc(f["asunto"] or "—"), es=f["estilo"], po=esc(ports), ec=encola,
        ex=esc(f["extract"])))
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"Atoms: {len(atoms)} | .md: {len(md_files)} | cabeceras identificables: {total_citas}")
print(f"Sin atom -> ocurrencias: {len(findings)} | distintos: {len(dist)} "
      f"(alta {n_alta} / media {n_media} / baja {n_baja})")
print(f"Informe -> {OUT}\n")
print("-- Correos NO separados, confianza ALTA (remitente+fecha) --")
for f in dist:
    if f["conf"] != "alta":
        continue
    print(f"  [{f['fecha']}] {f['de'] or '—':38s} | {strip_prefix(f['asunto'])[:46] or '—':46s}"
          f" | en {', '.join(sorted(set(f['portadores'])))}")
