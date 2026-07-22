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
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifiesto_parser  # noqa: E402

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
            if fila.get("fecha") != "0000-00-00":
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


def main(argv: list[str]) -> int:
    args = argv[1:]
    if not args:
        print("uso: verificar_sala.py <sala_dir> [--cobertura <ruta>] [--hash {no|muestra|completo}]")
        return 2
    sala_dir = Path(args[0])
    cobertura_path = None
    modo_hash = "no"
    i = 1
    while i < len(args):
        if args[i] == "--cobertura" and i + 1 < len(args):
            cobertura_path = Path(args[i + 1]); i += 2
        elif args[i] == "--hash" and i + 1 < len(args):
            modo_hash = args[i + 1]; i += 2
        else:
            print(f"argumento no reconocido: {args[i]}"); return 2
    if modo_hash not in ("no", "muestra", "completo"):
        print(f"--hash debe ser no|muestra|completo, no {modo_hash!r}"); return 2
    manif = sala_dir / "_MANIFIESTO.md"
    if not manif.exists():
        print(f"no existe {manif}"); return 2
    try:
        filas = manifiesto_parser.parse_manifiesto(
            manif.read_text(encoding="utf-8"), estricto=True)
    except ValueError as exc:
        print(str(exc))
        return 1
    cobertura = None
    if cobertura_path and cobertura_path.exists():
        cobertura = json.loads(cobertura_path.read_text(encoding="utf-8"))
    ficheros = _listar_sala(sala_dir)
    problemas = verificar(filas, ficheros, cobertura)
    problemas += _problemas_hash(sala_dir, filas, ficheros, modo_hash)
    for p in problemas:
        print(p)
    if problemas:
        print(f"\n{len(problemas)} problema(s).")
        return 1
    print("Verify OK: manifiesto y disco cuadran.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
