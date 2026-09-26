"""Fase verify de `organizar-sala-lectura`: contrasta el `_MANIFIESTO.md`
contra lo REALMENTE copiado en disco, con criterios duros — no resume bonito,
lista problemas. Self-contained (sin `core/`), determinista.

Motivo (sesión 2026-07-21, W-02VUDR, fusión de `HANDOFF_sala-lectura.md`
§3.2): dos discrepancias reales de conteo pasaron el reporte final sin que
nada las detectara automáticamente. Esta fase es la red de seguridad.

Motivo del chequeo de fecha (misma sesión, hallazgo posterior): 7 binarios
opacos quedaron en `0000-00-00` pese a que su espejo MD en sala de máquina
ya tenía texto extraído con fecha inequívoca (p.ej. un burofax certificado
con "Fecha y hora del envío: 08/04/2025"). `texto_espejo_md()` existe desde
la v1.9 pero su consulta era opcional en el procedimiento — nada la
verificaba después. El propósito de la sala de lectura es el timeline;
`0000-00-00` sin motivo lo rompe.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_control  # noqa: E402  (copia exacta de core/intake_control.py)
import manifiesto_parser  # noqa: E402
import preclasificar  # noqa: E402

_CHARS_MINIMOS_SOSPECHOSO = 200
_UMBRAL_HOMOGENEO = 5
_EXCLUIR_NOMBRES = {"INDICE.md", "CRONOLOGIA.md", "_MANIFIESTO.md", "indice_documental.yaml"}
_EXCLUIR_DIRS_TOP = {"_plan"}


def verificar(
    manifiesto_filas: list[dict],
    ficheros_en_disco: set[str],
    cobertura_filas: list[dict] | None = None,
) -> list[str]:
    """Nunca arregla nada — solo detecta. Devuelve la lista de problemas (vacía
    si todo cuadra). Si ≥`_UMBRAL_HOMOGENEO` problemas son del MISMO tipo,
    antepone un aviso: la hipótesis por defecto es bug del CHECK, no de los
    datos (modo de fallo más caro observado: 21 filas parcheadas a mano por un
    falso positivo de parent_id, sesión anterior W-02VUDR)."""
    tipados: list[tuple[str, str]] = []
    nombres_lista = [f["nombre_canonico"] for f in manifiesto_filas]
    nombres_manifiesto = set(nombres_lista)

    for nombre, n in Counter(nombres_lista).items():
        if n > 1:
            tipados.append(("colision_nombre",
                f"{nombre}: nombre_canonico repetido en {n} filas — colisión, un "
                f"documento pisaría a otro en disco; desambigua con _2/_3"))

    for fila in manifiesto_filas:
        nombre = fila["nombre_canonico"]
        if nombre not in ficheros_en_disco:
            tipados.append(("sin_fichero", f"{nombre}: fila en manifiesto pero no existe en disco"))

    for nombre in sorted(ficheros_en_disco):  # sorted → salida determinista (ficheros_en_disco es un set)
        if nombre not in nombres_manifiesto:
            tipados.append(("huerfano_disco", f"{nombre}: fichero en disco sin fila en el manifiesto"))

    shas_manifiesto = {f.get("sha256") for f in manifiesto_filas}
    for fila in manifiesto_filas:
        parent = fila.get("parent_id") or ""
        if not parent:
            continue
        # parent_id resuelve por sha256, por nombre_canonico exacto, o —convención
        # real de bundles desde v1.1— por ser el nombre PELADO de la carpeta del
        # bundle (prefijo de directorio de algún nombre_canonico). (PR #114.)
        resuelve = (
            parent in shas_manifiesto
            or parent in nombres_manifiesto
            or any(n.startswith(parent + "/") for n in nombres_manifiesto)
        )
        if not resuelve:
            tipados.append(("parent_huerfano",
                f"{fila['nombre_canonico']}: parent_id {parent!r} no resuelve a "
                f"ningún documento del manifiesto (anexo huérfano)"))

    if cobertura_filas:
        chars_ok_por_origen: dict[str, int] = {}
        for c in cobertura_filas:
            if c.get("estado") not in ("ok", "low"):
                continue
            origen = c.get("parent_sha256") or c.get("sha256")
            chars = c.get("chars") or 0
            if chars > chars_ok_por_origen.get(origen, -1):
                chars_ok_por_origen[origen] = chars
        for fila in manifiesto_filas:
            if (fila.get("fecha") or "").replace("(*)", "").strip() != "0000-00-00":
                continue
            chars = chars_ok_por_origen.get(fila.get("sha256"))
            if chars is not None and chars >= _CHARS_MINIMOS_SOSPECHOSO:
                tipados.append(("fecha_0000",
                    f"{fila['nombre_canonico']}: fecha 0000-00-00 pero hay texto "
                    f"extraído ({chars} chars) en sala de máquina -- revisar si "
                    f"contiene una fecha real antes de dar por bueno el 0000-00-00"))

    por_tipo = Counter(t for t, _ in tipados)
    avisos = [
        f"ATENCIÓN: {n} problemas homogéneos del tipo '{t}' — sospecha del check, "
        f"no de los datos; contrasta 2-3 filas a mano antes de tocar nada"
        for t, n in por_tipo.items() if n >= _UMBRAL_HOMOGENEO
    ]
    return avisos + [msg for _, msg in tipados]


def _clave_ruta(ruta: str) -> str:
    """Una ruta de origen del MANIFIESTO (o de «## No copiados»), comparable con la cobertura:
    relativa a `00_Input/`, con `/` y en NFC. El manifiesto suele escribir `00_Input\\…` —457
    de las 2.596 filas reales— y se le quita ese prefijo, una vez; la forma Unicode de un
    nombre con tilde no es la misma en todos los lados."""
    r = (ruta or "").strip().replace("\\", "/")
    primero, _, resto = r.partition("/")
    if resto and primero.casefold() == "00_input":
        r = resto
    return unicodedata.normalize("NFC", r)


def _clave_cobertura(rel: str) -> str:
    """La `rel_path` de la cobertura, que YA es relativa a `00_Input/`: con `/` y NFC, sin
    quitarle nada. Un primer componente `00_Input` es una carpeta del cliente, y recortarlo
    convertía `00_Input/_caso.md` en el protocolo de la raíz (R1/H-06 del #408). Ninguna de
    las 24 coberturas reales lleva el prefijo."""
    return unicodedata.normalize("NFC", (rel or "").strip().replace("\\", "/"))


_RE_SHA256 = re.compile(r"[0-9a-f]{64}")


def _es_sha256(h: str) -> bool:
    """El manifiesto admite `md5:<hash>` (Modo 3) y vacío: no contradicen, solo no contrastan."""
    return bool(_RE_SHA256.fullmatch(h or ""))


def problemas_poblacion(manifiesto_filas: list[dict], cobertura_filas: list[dict],
                        no_copiados: list[dict]) -> list[str]:
    """Todo lo que procesó la sala de máquina tiene fila o declaración (MEJORAS #316).

    Una fuente de la cobertura —cada `rel_path`— da cuenta de sí:

    - por una fila con su **ruta** (`ruta_original`) que no la contradiga;
    - por su **contenido**: su sha256 está en una fila. Es el `dedup_por_sha`, la copia en
      otra carpeta; lo comprueba la verja y **no se declara**: un hecho que se puede medir no
      se acredita diciéndolo (R1/H-04 del #408);
    - o por una línea **`excluido`** en `## No copiados`: una decisión, con su motivo.

    **La unidad es el par ruta/sha256 de cada fila** (R1/H-03 del #408, la misma frontera que
    la C3 cerró en el #407): una fila con la ruta de una fuente y otro sha256 la CONTRADICE y
    no acredita a nadie, ni a su ruta ni, por su hash, a otra fuente. Una fila `md5:` o sin
    hash no contradice: da cuenta solo por la ruta. Una línea `duplicado` no da cuenta de
    nada (R1/H-09), y una ruta con fila no puede estar además en «No copiados».

    Solo dos cosas no piden nada, y las dos son reglas de su productor: el protocolo del
    registro por ubicación y el zip crudo que el intake de WhatsApp deja junto a su chat. La
    firma `_firma_*` de `email_export` no: el productor la marca, no la descarta (R1/H-01).

    **Contrasta lo que procesó la sala de máquina**, no el disco: un fichero de `00_Input` que
    ella no procesó no lo ve esta verja (R1/H-11). La lista del Paso 1 sigue siendo del agente.

    Medido el 2026-09-26: en W-02Y2J6 siete notas de voz, zips, vCards y un vídeo no estaban
    ni en la tabla ni en ninguna otra parte del manifiesto, y este verify decía OK — solo
    miraba lo copiado.
    """
    fuentes: dict[str, set[str]] = {}
    muestra: dict[str, str] = {}
    sin_ruta = 0
    for c in cobertura_filas:
        rel = c.get("rel_path") if isinstance(c, dict) else None
        if not isinstance(rel, str) or not rel.strip():
            sin_ruta += 1
            continue
        k = _clave_cobertura(rel)
        muestra.setdefault(k, rel)
        origen = c.get("parent_sha256") or c.get("sha256")
        fuentes.setdefault(k, set()).update(
            {origen.strip().lower()} if isinstance(origen, str) and origen.strip() else set())

    pares = [(_clave_ruta(f.get("ruta_original") or ""), (f.get("sha256") or "").strip().lower())
             for f in manifiesto_filas]

    def _contradice(ruta: str, h: str) -> bool:
        return (ruta in fuentes and _es_sha256(h) and h not in fuentes[ruta]
                and any(_es_sha256(s) for s in fuentes[ruta]))

    coherentes = [(r, h) for r, h in pares if not _contradice(r, h)]
    rutas_coherentes = {r for r, _ in coherentes} - {""}
    rutas_con_fila = {r for r, _ in pares} - {""}
    shas = {h for _, h in coherentes if _es_sha256(h)}
    declaradas = {m: {_clave_ruta(d.get("ruta") or "") for d in no_copiados
                      if d.get("motivo") == m} - {""} for m in ("excluido", "duplicado")}
    crudos = {c["ruta"] for c in preclasificar.emparejar_exports_whatsapp(sorted(fuentes))[1]}

    problemas: list[str] = []
    for k in sorted(fuentes):
        if k in rutas_coherentes:
            continue
        if k in rutas_con_fila:
            problemas.append(f"{muestra[k]}: la fila del manifiesto con esta ruta lleva otro "
                             "sha256 y contradice a la fuente —el sitio es el suyo y el "
                             "contenido no—")
            continue
        if fuentes[k] & shas or k in declaradas["excluido"]:
            continue
        if intake_control.es_fichero_de_protocolo(k) or k in crudos:
            continue
        nota = (" (la línea `duplicado` no basta: su sha256 no está en ninguna fila)"
                if k in declaradas["duplicado"] else "")
        problemas.append(f"{muestra[k]}: la sala de máquina la procesó y no tiene fila en el "
                         "manifiesto —ni por su ruta ni por su sha256— ni línea `excluido` en "
                         f"«## No copiados»{nota}")
    for k in sorted((declaradas["excluido"] | declaradas["duplicado"]) & rutas_con_fila):
        problemas.append(f"{k}: tiene fila en el manifiesto y está en «## No copiados» a la vez")
    if sin_ruta:
        problemas.insert(0, f"{sin_ruta} fila(s) de la cobertura sin `rel_path`: no se pueden "
                            "contrastar con el manifiesto")
    return problemas


def _listar_sala(sala_dir) -> set[str]:
    """Relpaths posix de los ficheros COPIADOS de la sala (bundles incluidos como
    `subcarpeta/fichero.ext`, que es como se escribe su `nombre_canonico`),
    excluyendo los índices generados y el directorio `_plan/`."""
    sala_dir = Path(sala_dir)
    encontrados: set[str] = set()
    for p in sala_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(sala_dir)
        if rel.parts and rel.parts[0] in _EXCLUIR_DIRS_TOP:
            continue
        if p.name in _EXCLUIR_NOMBRES:
            continue
        encontrados.add(rel.as_posix())
    return encontrados


def _sha256_fichero(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _problemas_hash(sala_dir, filas, ficheros_en_disco, modo) -> list[str]:
    """Contrasta el sha256 de la COPIA en disco contra el del manifiesto (que es
    el del ORIGEN; una copia byte-idéntica debe coincidir). `muestra` = 10%
    determinista; `completo` = todos. Filas sin sha256 de 64 hex (Modo 3 md5 o
    pendiente) no se pueden contrastar y se saltan."""
    if modo == "no":
        return []
    objetivo = sorted(ficheros_en_disco)
    if modo == "muestra":
        objetivo = objetivo[::10] or objetivo[:1]
    sha_por_nombre = {f["nombre_canonico"]: f.get("sha256") for f in filas}
    problemas: list[str] = []
    for rel in objetivo:
        esperado = sha_por_nombre.get(rel)
        if not esperado or len(esperado) != 64:
            continue
        real = _sha256_fichero(Path(sala_dir) / rel)
        if real != esperado:
            problemas.append(
                f"{rel}: sha256 en disco {real[:12]} != manifiesto {esperado[:12]} "
                f"(copia corrupta o alterada)")
    return problemas


def _cobertura_hermana(sala_dir: Path) -> Path:
    """Donde el layout del expediente pone la cobertura: `01_Procesado/02_Sala de máquina/`,
    hermana de `01_Procesado/Sala lectura/` (`SKILL.md` §estructura)."""
    return Path(sala_dir).parent / "02_Sala de máquina" / "_cobertura.json"


def _leer_cobertura(p: Path) -> tuple[list | None, str]:
    """`(filas, "")` o `(None, motivo)`: una cobertura que no se puede leer no es una vacía."""
    try:
        datos = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"la cobertura {p} no se puede leer ({type(exc).__name__})"
    if not isinstance(datos, list):
        return None, f"la cobertura {p} no es una lista sino {type(datos).__name__}"
    return datos, ""


def main(argv: list[str]) -> int:
    """Exit 0 = todo lo que se promete se ha comprobado y cuadra; 1 = hay problemas, o no se
    ha podido contrastar la población; 2 = uso incorrecto o fichero ilegible.

    **Un 0 no puede salir sin la verja de población** (R1/H-02 del #408): la primera versión
    avisaba y devolvía 0 sin cobertura, y quien mirase el código de salida daba por hecha una
    comprobación que no había corrido. La cobertura se deduce del layout si no se pasa; sin
    ella, el verify falla, salvo con `--sin-cobertura` —la sala que no tiene sala de
    máquina—, que da un OK que dice PARCIAL."""
    args = argv[1:]
    if not args:
        print("uso: verificar_sala.py <sala_dir> [--cobertura <ruta> | --sin-cobertura] "
              "[--hash {no|muestra|completo}]")
        return 2
    sala_dir = Path(args[0])
    cobertura_path = None
    sin_cobertura = False
    modo_hash = "no"
    i = 1
    while i < len(args):
        if args[i] == "--cobertura" and i + 1 < len(args):
            cobertura_path = Path(args[i + 1]); i += 2
        elif args[i] == "--sin-cobertura":
            sin_cobertura = True; i += 1
        elif args[i] == "--hash" and i + 1 < len(args):
            modo_hash = args[i + 1]; i += 2
        else:
            print(f"argumento no reconocido: {args[i]}"); return 2
    if modo_hash not in ("no", "muestra", "completo"):
        print(f"--hash debe ser no|muestra|completo, no {modo_hash!r}"); return 2
    manif = sala_dir / "_MANIFIESTO.md"
    if not manif.exists():
        print(f"no existe {manif}"); return 2
    if cobertura_path is None:
        if _cobertura_hermana(sala_dir).exists():
            cobertura_path = _cobertura_hermana(sala_dir)
    elif not cobertura_path.exists():
        print(f"no existe la cobertura {cobertura_path}"); return 2
    if sin_cobertura and cobertura_path is not None:
        print(f"--sin-cobertura, pero hay cobertura en {cobertura_path}: no se renuncia a "
              "contrastar lo que existe"); return 2
    cobertura = None
    if cobertura_path is not None:
        cobertura, err = _leer_cobertura(cobertura_path)
        if err:
            print(err); return 2
    texto = manif.read_text(encoding="utf-8")
    try:
        filas = manifiesto_parser.parse_manifiesto(texto, estricto=True)
        no_copiados = manifiesto_parser.parse_no_copiados(texto, estricto=True)
    except ValueError as exc:
        print(str(exc))
        return 1
    ficheros = _listar_sala(sala_dir)
    problemas = verificar(filas, ficheros, cobertura)
    problemas += _problemas_hash(sala_dir, filas, ficheros, modo_hash)
    if cobertura is not None:
        problemas += problemas_poblacion(filas, cobertura, no_copiados)
    elif not sin_cobertura:
        problemas.append("no hay cobertura con la que contrastar la población de la sala: pásala "
                         "con --cobertura <ruta>, o --sin-cobertura si la sala de máquina no ha "
                         f"corrido (se buscó en {_cobertura_hermana(sala_dir)})")
    for p in problemas:
        print(p)
    if problemas:
        print(f"\n{len(problemas)} problema(s).")
        return 1
    if cobertura is None:
        print("Verify PARCIAL: manifiesto y disco cuadran; la población NO se ha contrastado "
              "(--sin-cobertura).")
        return 0
    print(f"Verify OK: manifiesto y disco cuadran, y la sala da cuenta de lo que procesó la "
          f"sala de máquina ({cobertura_path}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
