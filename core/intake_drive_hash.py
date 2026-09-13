"""¿Los bytes que el expediente guarda son los del Drive de E&V? — vía (a) de `MEJORAS #225`.

El pull (`core.intake_drive.pull_drive_ev`) copia con `--ignore-size --ignore-checksum
--inplace`, tres banderas que **apagan la verificación post-transferencia**. Existen por una
razón medida (el destino vive en un montaje de Google Drive for Desktop y el rename
`.partial → final` disparaba falsos «corrupted on transfer»), y su efecto colateral también
está medido: los ficheros llegan **rellenados con ceros** hasta el siguiente múltiplo de 512,
así que su `sha256` **no es el del original** y nada lo dice. Medido el 2026-09-10: 34 de 35
ficheros en el pull de W-02V48N, 224 de 242 en W-02VEKE.

Este módulo no arregla el relleno —eso es la vía (b), quitar `--inplace`, que exige volver a
medir los falsos positivos con el control que nunca se corrió—. Hace lo que convierte el
defecto en **visible**: contrasta el `sha256` de cada fichero del destino contra el que la
propia API de Drive declara para el original, y grita fichero a fichero.

**Por qué se le pregunta a rclone las dos veces, en vez de leer el disco y llamar a la API.**
Dos razones, y las dos son de población:

1. **La misma dirección.** El listado del origen usa el MISMO remote, el mismo
   `--drive-team-drive`, el mismo `--drive-root-folder-id` y el mismo `--drive-skip-shortcuts`
   que la copia. Lo que se verifica es, por construcción, lo que se copió — no una carpeta
   parecida.
2. **El mismo namespace de nombres.** El pull escribe con `--local-encoding` (set Windows +
   `LeftSpace,LeftPeriod`), porque las carpetas de E&V traen ficheros cuyo nombre empieza por
   un espacio y el sistema de ficheros virtual de Drive Desktop los rechaza: en disco, ese
   fichero se llama `␠NIE Pasaporte.jpg` (U+2420). Un cruce de nombres escrito a mano falla
   **justo en esos ficheros y en silencio**, que es la forma de fallo que este módulo existe
   para no repetir. Preguntándole al listado local con el MISMO `--local-encoding`, rclone
   decodifica y las dos listas hablan el mismo idioma.

El contraste distingue cuatro veredictos, y el cuarto es el que impide confundir «cuadra» con
«no pude mirar». Un documento nativo de Google (Hoja de cálculo, Documento) **no tiene bytes
canónicos**: Drive lo publica sin `size` ni checksum y lo convierte al descargarlo, así que su
copia local nunca puede cuadrar contra nada. Eso es `no_verificable`, no un hallazgo — y
contarlo como «ok» sería la mentira simétrica.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .intake_control import es_fichero_de_protocolo

#: Nombre del informe, escrito junto al `.pulled` del mismo directorio. Declarado en
#: `intake_control.ENTREGA` para que el inventario probatorio no lo tome por un documento
#: del cliente (`MEJORAS #149`: el protocolo se reconoce por su UBICACIÓN, no por su nombre).
INFORME = ".verificacion_hash.json"

#: Veredictos. Cerrados a propósito: un quinto valor obligaría a decidir qué hace el grito.
VERIFICADO = "ok"                  # el sha256 del destino es el que el origen declara
DISCREPA = "discrepa"              # ambos sha256 existen y son distintos
AUSENTE = "ausente"                # el origen lo lista y el destino no lo tiene
NO_VERIFICABLE = "no_verificable"  # no hay dos sha256 que contrastar

_MOTIVO_SIN_CHECKSUM = (
    "el origen no declara sha256 (documento nativo de Google, que se convierte al "
    "descargarlo, o fichero cuyo checksum Drive no publica): no hay contra qué cuadrarlo"
)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FicheroVerificado:
    """Un fichero del ORIGEN y su suerte en el destino."""
    ruta: str                        # relativa al directorio del pull, con `/`
    veredicto: str
    sha256_origen: str | None = None
    sha256_local: str | None = None
    bytes_origen: int | None = None
    bytes_local: int | None = None
    motivo: str = ""

    @property
    def delta(self) -> int | None:
        """Bytes que el destino tiene DE MÁS (negativo si tiene de menos), o None.

        `None` cuando falta alguno de los dos tamaños o cuando el origen publica `-1`, que es
        lo que Drive devuelve para un documento nativo: ahí la resta no significaría nada.
        """
        if self.bytes_origen is None or self.bytes_local is None:
            return None
        if self.bytes_origen < 0:
            return None
        return self.bytes_local - self.bytes_origen

    @property
    def compatible_con_relleno(self) -> bool:
        """El destino es más grande Y múltiplo de 512: la forma del defecto de `MEJORAS #225`.

        **Es compatibilidad, no diagnóstico.** La firma completa del relleno son dos cosas
        —múltiplo de 512 *y* cola de ceros— y la segunda exige abrir el fichero, que aquí no
        se hace. Un fichero alterado de otra manera cuyo tamaño caiga por azar en un múltiplo
        de 512 (1 de cada 512) también daría True. El nombre dice lo que mide.
        """
        d = self.delta
        return bool(
            d and d > 0 and self.bytes_local is not None and self.bytes_local % 512 == 0
        )


@dataclass
class Verificacion:
    """El veredicto del pull entero.

    `ejecutada=False` es un valor de primera clase: significa **no pude mirar**, y no se lee
    como «cuadra». Sin él, un `rclone` caído o un token vencido devolverían cero
    discrepancias y el informe diría que el expediente está limpio.
    """
    ejecutada: bool
    motivo: str = ""                                       # por qué NO se ejecutó
    verificados: tuple[FicheroVerificado, ...] = ()
    discrepan: tuple[FicheroVerificado, ...] = ()
    ausentes: tuple[FicheroVerificado, ...] = ()
    no_verificables: tuple[FicheroVerificado, ...] = ()
    #: Ficheros del destino que el origen NO lista (excluido el protocolo). No es un fallo del
    #: pull —pueden venir de un pull anterior de otra carpeta, o de un renombrado en E&V—,
    #: pero es una pregunta de procedencia que conviene ver.
    sobrantes: tuple[str, ...] = ()

    @property
    def total_origen(self) -> int:
        return (len(self.verificados) + len(self.discrepan)
                + len(self.ausentes) + len(self.no_verificables))

    @property
    def hay_hallazgos(self) -> bool:
        return bool(self.discrepan or self.ausentes)

    def resumen(self) -> str:
        """Una línea. Cuando no se ejecutó, lo dice — no da un cero."""
        if not self.ejecutada:
            return f"verificación por hash NO EJECUTADA: {self.motivo}"
        partes = [f"{len(self.verificados)} de {self.total_origen} cuadran"]
        if self.discrepan:
            partes.append(f"{len(self.discrepan)} DISCREPAN")
        if self.ausentes:
            partes.append(f"{len(self.ausentes)} AUSENTES")
        if self.no_verificables:
            partes.append(f"{len(self.no_verificables)} no verificables")
        if self.sobrantes:
            partes.append(f"{len(self.sobrantes)} en destino que el origen no lista")
        return " · ".join(partes)

    def a_dict(self) -> dict:
        def fila(f: FicheroVerificado) -> dict:
            d: dict = {
                "ruta": f.ruta,
                "veredicto": f.veredicto,
                "sha256_origen": f.sha256_origen,
                "sha256_local": f.sha256_local,
                "bytes_origen": f.bytes_origen,
                "bytes_local": f.bytes_local,
            }
            if f.motivo:
                d["motivo"] = f.motivo
            if f.delta is not None:
                d["delta_bytes"] = f.delta
                d["compatible_con_relleno_512"] = f.compatible_con_relleno
            return d

        return {
            "ejecutada": self.ejecutada,
            "motivo": self.motivo,
            "resumen": self.resumen(),
            "total_origen": self.total_origen,
            "cuadran": len(self.verificados),
            "discrepan": [fila(f) for f in self.discrepan],
            "ausentes": [fila(f) for f in self.ausentes],
            "no_verificables": [fila(f) for f in self.no_verificables],
            "sobrantes_en_destino": list(self.sobrantes),
        }


# ---------------------------------------------------------------------------
# El contraste: función PURA, sin red ni disco
# ---------------------------------------------------------------------------

def _sha256_de(entrada: dict) -> str | None:
    """El sha256 de una entrada de `rclone lsjson`, normalizado, o None si no lo trae."""
    hashes = entrada.get("Hashes") or {}
    if not isinstance(hashes, dict):
        return None
    valor = hashes.get("sha256")
    if not isinstance(valor, str):
        return None
    valor = valor.strip().lower()
    return valor or None


def _bytes_de(entrada: dict) -> int | None:
    valor = entrada.get("Size")
    return valor if isinstance(valor, int) else None


def clave(ruta: str) -> str:
    """La clave con la que se cruzan las dos listas: separador `/` y Unicode en **NFC**.

    **La normalización no es cosmética; sin ella el cruce da un hallazgo falso.** Medido el
    2026-09-10 con este mismo módulo sobre W-02V48N: `FR_Elena_Verdejo_Álvarez_Firmado_A+B.pdf`
    salía a la vez como `ausente` (lo lista el origen) y como sobrante (está en disco), porque
    Drive publica la `Á` **descompuesta** (`A` + U+0301, NFD) y en `G:` está **precompuesta**
    (U+00C1, NFC). Las dos cadenas se imprimen idénticas y no son iguales: el falso hallazgo
    es indistinguible a la vista, y tapaba una discrepancia real de +326 bytes.

    Se conserva la `Path` original para mostrarla; lo que se normaliza es solo la clave.
    """
    import unicodedata

    return unicodedata.normalize("NFC", ruta.replace("\\", "/"))


def _indexar(entradas: list[dict]) -> tuple[dict[str, dict], tuple[str, ...]]:
    """`clave(Path)` → entrada, descartando directorios.

    Devuelve además las claves que aparecen MÁS DE UNA VEZ. Colapsarlas en silencio sería el
    mismo defecto por el otro lado: dos ficheros del origen que solo se distinguen por su
    forma Unicode no caben los dos en un sistema de ficheros Windows, así que uno de ellos
    falta de verdad — y eso se dice, no se esconde tras un «gana la última».
    """
    out: dict[str, dict] = {}
    colisiones: list[str] = []
    for e in entradas:
        if not isinstance(e, dict) or e.get("IsDir"):
            continue
        ruta = e.get("Path")
        if not isinstance(ruta, str) or not ruta:
            continue
        k = clave(ruta)
        if k in out:
            colisiones.append(k)
        out[k] = e
    return out, tuple(sorted(set(colisiones)))


def comparar(entradas_origen: list[dict], entradas_locales: list[dict]) -> Verificacion:
    """Contrasta dos listados de `rclone lsjson` (origen y destino) por `Path`.

    Pura: recibe los listados ya parseados y no toca red ni disco, así que se prueba con
    JSON sintético y sin montar nada.
    """
    origen = _indexar(entradas_origen)
    local = _indexar(entradas_locales)

    verificados: list[FicheroVerificado] = []
    discrepan: list[FicheroVerificado] = []
    ausentes: list[FicheroVerificado] = []
    no_verificables: list[FicheroVerificado] = []

    for ruta in sorted(origen):
        e_o = origen[ruta]
        sha_o = _sha256_de(e_o)
        bytes_o = _bytes_de(e_o)
        e_l = local.get(ruta)

        if e_l is None:
            ausentes.append(FicheroVerificado(
                ruta=ruta, veredicto=AUSENTE, sha256_origen=sha_o, bytes_origen=bytes_o,
                motivo="el origen lo lista y el destino no lo tiene"))
            continue

        sha_l = _sha256_de(e_l)
        bytes_l = _bytes_de(e_l)

        if sha_o is None:
            no_verificables.append(FicheroVerificado(
                ruta=ruta, veredicto=NO_VERIFICABLE, sha256_local=sha_l,
                bytes_origen=bytes_o, bytes_local=bytes_l, motivo=_MOTIVO_SIN_CHECKSUM))
            continue
        if sha_l is None:
            no_verificables.append(FicheroVerificado(
                ruta=ruta, veredicto=NO_VERIFICABLE, sha256_origen=sha_o,
                bytes_origen=bytes_o, bytes_local=bytes_l,
                motivo="no se pudo hashear la copia local (ilegible, o sin hidratar en G:)"))
            continue

        cuadra = sha_o == sha_l
        fila = FicheroVerificado(
            ruta=ruta, veredicto=VERIFICADO if cuadra else DISCREPA,
            sha256_origen=sha_o, sha256_local=sha_l,
            bytes_origen=bytes_o, bytes_local=bytes_l)
        (verificados if cuadra else discrepan).append(fila)

    return Verificacion(
        ejecutada=True,
        verificados=tuple(verificados),
        discrepan=tuple(discrepan),
        ausentes=tuple(ausentes),
        no_verificables=tuple(no_verificables),
        sobrantes=tuple(sorted(set(local) - set(origen))),
    )


# ---------------------------------------------------------------------------
# La cáscara: los dos `rclone lsjson` y el informe
# ---------------------------------------------------------------------------

def cmd_listar_origen(
    remote: str, folder_id: str, team_id: str, binario: str = "rclone"
) -> list[str]:
    """`rclone lsjson` del ORIGEN, con la misma dirección que usa el `copy` del pull."""
    return [
        binario, "lsjson", f"{remote}:",
        "--drive-team-drive", team_id,
        "--drive-root-folder-id", folder_id,
        "--drive-skip-shortcuts",
        "--recursive", "--files-only",
        "--hash-type", "sha256",
    ]


def cmd_listar_local(
    target_dir: Path, local_encoding: str, binario: str = "rclone"
) -> list[str]:
    """`rclone lsjson` del DESTINO, con el MISMO `--local-encoding` que escribió el pull.

    Sin ese flag, los ficheros cuyo nombre empieza por espacio vuelven con el `␠` (U+2420)
    que rclone les puso en disco, no casan con la `Path` del origen y saldrían por `ausente`:
    un falso hallazgo justo en los ficheros que motivaron el flag.
    """
    return [
        binario, "lsjson", str(target_dir),
        "--recursive", "--files-only",
        "--hash-type", "sha256",
        "--local-encoding", local_encoding,
    ]


def _lsjson(cmd: list[str], timeout: float) -> tuple[list[dict] | None, str]:
    """Ejecuta un `lsjson` y devuelve `(entradas, motivo_del_fallo)`.

    Verifica **por resultado, no por status**: un `returncode 0` cuyo stdout no parsea como
    lista de entradas es un fallo, no un listado vacío.
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None, f"rclone lsjson agotó el timeout de {timeout:g} s"
    except FileNotFoundError:
        return None, f"binario rclone no encontrado: {cmd[0]!r}"
    except OSError as exc:
        return None, f"no se pudo ejecutar rclone: {exc}"

    if proc.returncode != 0:
        cola = (proc.stderr or "")[-500:].strip()
        return None, f"rclone lsjson exit {proc.returncode}: {cola}"
    try:
        datos = json.loads(proc.stdout or "")
    except (json.JSONDecodeError, TypeError) as exc:
        return None, f"la salida de rclone lsjson no es JSON ({exc})"
    if not isinstance(datos, list):
        return None, "la salida de rclone lsjson no es una lista de entradas"
    return [e for e in datos if isinstance(e, dict)], ""


def verificar_pull_por_hash(
    target_dir: Path,
    folder_id: str,
    team_id: str,
    *,
    remote: str,
    local_encoding: str,
    binario: str = "rclone",
    timeout: float = 600.0,
) -> Verificacion:
    """Contrasta el destino del pull contra el origen y devuelve el veredicto.

    **No lanza nunca.** Cualquier fallo —rclone ausente, token vencido, red caída, salida
    ilegible— vuelve como `Verificacion(ejecutada=False, motivo=...)`: la verificación es una
    red de calidad sobre el pull, no una condición de su éxito, y un expediente ya depositado
    no se aborta porque no se haya podido verificar. Quien la consume decide qué hacer con el
    `motivo`; lo que no puede es leerlo como cero discrepancias.
    """
    entradas_origen, motivo = _lsjson(
        cmd_listar_origen(remote, folder_id, team_id, binario), timeout)
    if entradas_origen is None:
        return Verificacion(ejecutada=False, motivo=f"listado del origen: {motivo}")

    entradas_locales, motivo = _lsjson(
        cmd_listar_local(target_dir, local_encoding, binario), timeout)
    if entradas_locales is None:
        return Verificacion(ejecutada=False, motivo=f"listado del destino: {motivo}")

    # El protocolo que el propio repo escribe en el directorio del pull (`.pulled`, este
    # mismo informe) no viene del Drive de E&V: sin este filtro saldría como `sobrante`.
    # La pregunta se le hace a `intake_control` por la UBICACIÓN, con el nombre REAL del
    # directorio (`MEJORAS #149`), nunca contra una lista de nombres escrita aquí.
    nombre_dir = target_dir.name
    entradas_locales = [
        e for e in entradas_locales
        if not es_fichero_de_protocolo(f"{nombre_dir}/{e.get('Path', '')}")
    ]
    return comparar(entradas_origen, entradas_locales)


def escribir_informe(target_dir: Path, verificacion: Verificacion) -> Path | None:
    """Deja el veredicto en `<target_dir>/.verificacion_hash.json`. None si no se pudo."""
    destino = target_dir / INFORME
    try:
        destino.write_text(
            json.dumps(verificacion.a_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        return None
    return destino


def lineas_del_grito(verificacion: Verificacion, *, maximo: int = 20) -> list[str]:
    """El grito, fichero a fichero, para que un llamador lo imprima.

    Vive en el core y no en el CLI porque el mismo texto lo necesitan el comando de apertura
    y la UI, y una segunda redacción divergiría. El core no imprime: devuelve las líneas.
    """
    if not verificacion.ejecutada:
        return [
            f"[AVISO] {verificacion.resumen()}",
            "        no se puede afirmar que los bytes del expediente sean los del origen",
        ]
    if not verificacion.hay_hallazgos:
        lineas = [f"[OK] hash contra el Drive de E&V: {verificacion.resumen()}"]
        if verificacion.no_verificables:
            lineas.append(
                f"     {len(verificacion.no_verificables)} sin checksum en origen "
                "(nativos de Google): no cuadran ni descuadran")
        return lineas

    lineas = [f"[AVISO] hash contra el Drive de E&V: {verificacion.resumen()}"]
    hallazgos = list(verificacion.discrepan) + list(verificacion.ausentes)
    for f in hallazgos[:maximo]:
        if f.veredicto == AUSENTE:
            lineas.append(f"  AUSENTE   {f.ruta}")
            continue
        detalle = ""
        if f.delta is not None:
            detalle = f" ({f.delta:+d} bytes"
            detalle += (", compatible con el relleno de #225)"
                        if f.compatible_con_relleno else ")")
        lineas.append(f"  DISCREPA  {f.ruta}{detalle}")
    if len(hallazgos) > maximo:
        lineas.append(f"  … y {len(hallazgos) - maximo} más (todos en {INFORME})")
    lineas.append(
        f"  el sha256 de estos ficheros NO acredita procedencia; detalle en {INFORME}")
    return lineas
