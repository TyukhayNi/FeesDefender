"""El criterio del despacho para expedir una comunicación certificada.

Spec: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
El transporte vive en `core/codicert.py` y no sabe qué es un expediente.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


class ExpedicionError(RuntimeError):
    """El plan no se puede construir o el envío no se puede ejecutar."""


TIPOS_COMUNICACION: tuple[str, ...] = ("REQ", "OVC")
MAX_ID = 20  # límite del campo `id_personalizado` en cuatro de los cinco productos


def componer_id(w_code: str, tipo: str, ordinal: int = 1) -> str:
    """`W-04AKM2 - OVC`, y `W-04AKM2 - REQ 2` desde la segunda expedición del tipo.

    La convención no se inventa: es la que ya usan los envíos vivos, y el equipo la lee
    en el portal. Sin el tipo dentro, la OVC que sale quince días después del
    requerimiento se confundiría con él y no saldría (spec §3).
    """
    if tipo not in TIPOS_COMUNICACION:
        raise ExpedicionError(f"tipo {tipo!r}; son {TIPOS_COMUNICACION}")
    if ordinal < 1:
        raise ExpedicionError(f"ordinal {ordinal}: empieza en 1")
    ident = f"{w_code} - {tipo}" + ("" if ordinal == 1 else f" {ordinal}")
    if len(ident) > MAX_ID:
        raise ExpedicionError(
            f"el identificador {ident!r} son {len(ident)} caracteres y el máximo es {MAX_ID}")
    return ident


# Las siete de 52 en que el CRM escribe en castellano lo que Codicert escribe en la
# lengua cooficial. Medido el 2026-09-17 cruzando los dos catálogos. El servidor NO
# valida este campo contra lista —`ZZZZZ` pasa—, así que esto es higiene: la provincia
# se IMPRIME en el sobre y conviene mandar la etiqueta que la plataforma usa.
PROVINCIA_CODICERT: dict[str, str] = {
    "Alicante": "Alacant",
    "Valencia": "València",
    "Castellón": "Castelló",
    "Álava": "Araba",
    "Guipúzcoa": "Gipuzkoa",
    "Vizcaya": "Bizkaia",
    "Baleares (Illes)": "Islas Baleares",
}

_MOVIL = re.compile(r"^(?:\+?34|0034)?([67]\d{8})$")


def provincia_codicert(nombre: str) -> str:
    """Traducción de la provincia si no casa entre el CRM y Codicert."""
    return PROVINCIA_CODICERT.get(nombre, nombre)


def movil_normalizado(bruto: str | None) -> str | None:
    """`34` + nueve dígitos, o `None` si no es un móvil español.

    El prefijo se pega porque es lo que la plataforma registra: el destinatario SMS de
    producción es `34645508869`. Un fijo devuelve `None` y el canal se declara ausente.
    """
    if not bruto:
        return None
    m = _MOVIL.match(re.sub(r"[\s.\-()]", "", str(bruto)))
    return f"34{m.group(1)}" if m else None


_OBLIGATORIOS_POSTAL = ("nombre", "direccion", "poblacion", "provincia", "cp")


def ficha_postal(parte: dict) -> dict:
    """Destinatario del burofax, validado **antes** de gastar.

    Un 422 a mitad de expedición deja las electrónicas mandadas y el burofax no, así que
    lo que el servidor rechazaría se para aquí.
    """
    faltan = [c for c in _OBLIGATORIOS_POSTAL if not str(parte.get(c) or "").strip()]
    if faltan:
        raise ExpedicionError(
            f"la ficha postal de {(parte.get('nombre') or '').strip() or '(sin nombre)'} no tiene: "
            + ", ".join(faltan))
    return {"nombre": parte["nombre"], "a_atencion": parte.get("a_atencion") or parte["nombre"],
            "pais": "España", "direccion": parte["direccion"], "poblacion": parte["poblacion"],
            "provincia": provincia_codicert(parte["provincia"]), "cp": parte["cp"],
            **({"telefono": m} if (m := movil_normalizado(parte.get("movil"))) else {})}


# Tarifa «80», leída del portal de producción el 2026-09-17. Cada línea incluye la
# notificación: la entrega electrónica son 0,3867 € más el canal.
TARIFA: dict[str, Decimal] = {
    "burofax": Decimal("16.9716"),
    "correo": Decimal("0.3867") + Decimal("0.4064"),
    "sms": Decimal("0.3867") + Decimal("0.0834"),
}


@dataclass(frozen=True)
class EnvioPrevisto:
    """Un envío del plan: un canal y un destinatario ya resuelto."""

    canal: str            # "burofax" | "correo" | "sms"
    destinatario: dict    # ficha postal, o {"correo": ...} / {"telefono": ...}
    etiqueta: str         # para que el humano lo lea en el plan


def _clave_domicilio(p: dict) -> tuple:
    """Clave de agrupación por domicilio.

    Colapsa también los espacios internos (no solo los de borde): un doble espacio de
    captura del CRM —"C Mayor 1" frente a "C  Mayor 1"— no debe partir en dos un
    domicilio que es el mismo (17 € de burofax y un certificado de más).
    """
    return tuple(" ".join(str(p.get(c) or "").split()).upper()
                 for c in ("direccion", "poblacion", "provincia", "cp"))


def destinatarios_de(partes: list[dict]) -> tuple[list[EnvioPrevisto], list[str]]:
    """Los envíos previstos y las ausencias declaradas.

    Correo y SMS van **uno por requerido**: agrupar no ahorra —la plataforma cobra un
    envío por destinatario— y cada uno necesita su propio acuse, del que cuelgan sus
    plazos. El burofax va **uno por domicilio distinto**.
    """
    envios: list[EnvioPrevisto] = []
    ausencias: list[str] = []
    for p in partes:
        nombre = p.get("nombre") or "(sin nombre)"
        tiene = False
        if (correo := str(p.get("email") or "").strip()):
            envios.append(EnvioPrevisto("correo", {"correo": correo, "nombre": nombre},
                                        f"{nombre} · {correo}"))
            tiene = True
        else:
            ausencias.append(f"{nombre}: sin canal CORREO (el CRM no tiene email)")
        if (movil := movil_normalizado(p.get("movil"))):
            envios.append(EnvioPrevisto(
                "sms",
                {"telefono": movil, "nombre": nombre, **({"correo": correo} if correo else {})},
                f"{nombre} · {movil}"))
            tiene = True
        else:
            ausencias.append(f"{nombre}: sin canal SMS (el CRM no tiene un móvil español)")
        if all(str(p.get(c) or "").strip() for c in _OBLIGATORIOS_POSTAL):
            tiene = True
        else:
            ausencias.append(f"{nombre}: sin canal BUROFAX (domicilio incompleto)")
        if not tiene:
            raise ExpedicionError(
                f"{nombre} no tiene ningún canal: ni domicilio, ni email, ni móvil. "
                "Complétalo en el CRM antes de expedir.")

    por_domicilio: dict[tuple, list[dict]] = {}
    for p in partes:
        if all(str(p.get(c) or "").strip() for c in _OBLIGATORIOS_POSTAL):
            por_domicilio.setdefault(_clave_domicilio(p), []).append(p)
    for grupo in por_domicilio.values():
        base = dict(grupo[0])
        # Se captura ANTES de sobrescribir "nombre": si no, el fallback de ficha_postal
        # (a_atencion or nombre) recupera el nombre YA conjunto, no la persona de
        # contacto (regla del despacho: "nombre" lleva a los dos, "a_atencion" a uno).
        contacto = base.get("a_atencion") or base["nombre"]
        base["nombre"] = " Y ".join(str(g["nombre"]) for g in grupo)
        base["a_atencion"] = contacto
        ficha = ficha_postal(base)
        etiqueta = f"{ficha['nombre']} · {ficha['direccion']}, {ficha['poblacion']}"
        if len(grupo) > 1:
            etiqueta += "  ⚠ sobre conjunto: acredita entrega EN EL DOMICILIO, no a cada uno"
        envios.append(EnvioPrevisto("burofax", ficha, etiqueta))
    return envios, ausencias


def coste_de(envios: list[EnvioPrevisto]) -> Decimal:
    """Suma la tarifa por canal de cada envío previsto."""
    return sum((TARIFA[e.canal] for e in envios), Decimal("0"))


# El asunto y el cuerpo son LITERAL CERRADO y viajan en el Plan, para que la puerta
# humana los lea antes de gastar (spec §5 regla 6). Pueden nombrar el objeto de la
# controversia y la remisión de una comunicación —el art. 9.1 exceptúa el objeto y el
# art. 17.4 exige la manifestación— pero NO pueden contener términos de la oferta: ni
# importe (€, %), ni calendario, ni quita, ni plazo —a secas, no solo la frase «plazo de
# aceptación»—. El acta del certificado los reproduce, y el acta no se recorta.
PROHIBIDO_EN_TEXTO = ("oferta vinculante", "ovc", "€", "%", "quita", "plazo", "calendario")

# Plantillas SIN interpolar: la guarda de términos prohibidos se aplica AQUÍ, nunca al
# texto ya compuesto con el w_code. El w_code es un identificador de expediente, no
# prosa del motor, y puede llevar por azar una subcadena vetada —p. ej. "ovc" dentro de
# "W-0OVC12"— sin que eso sea una infracción de la regla.
_ASUNTO_TPL = "Comunicación certificada · expediente {w_code}"
_CUERPO_TPL = ("<p>Se le remite comunicación certificada relativa al expediente {w_code}. "
               "Consulte el documento adjunto.</p>")


def _asegurar_sin_prohibidos(texto: str) -> None:
    """Lanza `ExpedicionError` si `texto` contiene algún término vetado por la regla."""
    texto_l = texto.lower()
    for prohibido in PROHIBIDO_EN_TEXTO:
        if prohibido in texto_l:
            raise ExpedicionError(
                f"el asunto o el cuerpo contienen {prohibido!r}: el acta los reproduce y "
                "no se puede recortar (art. 17.4).")


def texto_de(w_code: str) -> tuple[str, str]:
    """Asunto y cuerpo de la comunicación. Nunca nombran los términos de la oferta."""
    _asegurar_sin_prohibidos(f"{_ASUNTO_TPL} {_CUERPO_TPL}")
    return _ASUNTO_TPL.format(w_code=w_code), _CUERPO_TPL.format(w_code=w_code)


class RegistroIntencion:
    """Rastro append-only de que *nosotros* llamamos, antes de que el servidor responda.

    No es una segunda fuente de verdad sobre los envíos —esa es Codicert— sino sobre un
    hecho nuestro que la plataforma no puede contarnos. Sin él, un timeout deja un
    burofax pagado cuyo `IdEnvio` no se puede reencontrar: `GET /envios` no filtra por
    `id_personalizado`.
    """

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)

    def _lineas(self) -> list[dict]:
        """Cada línea no vacía, parseada. Una línea ilegible se declara, no se oculta.

        Un corte a mitad de `write` puede dejar la última línea truncada. Tragarla en
        silencio perdería el rastro de un envío que ya se pagó, así que se declara con
        fichero y número de línea para que un humano la revise.
        """
        if not self.ruta.is_file():
            return []
        filas: list[dict] = []
        for numero, l in enumerate(
                self.ruta.read_text(encoding="utf-8").splitlines(), start=1):
            if not l.strip():
                continue
            try:
                filas.append(json.loads(l))
            except json.JSONDecodeError as exc:
                raise ExpedicionError(
                    f"{self.ruta}: la línea {numero} del registro de intención no es "
                    f"JSON válido ({exc}). No se ignora: puede ser el rastro de un "
                    "envío ya pagado. Revísala a mano antes de continuar."
                ) from exc
        return filas

    def _escribir(self, fila: dict) -> None:
        with self.ruta.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")

    def anotar(self, id_personalizado: str, canal: str, etiqueta: str) -> str:
        """Anota la intención SIN persistir datos personales del destinatario.

        El diseño (§4.3) exige `(id_personalizado, canal, destinatario, timestamp,
        en_vuelo)` antes de cada POST: sin ellos, el humano que lee un "SIN VERIFICAR"
        no sabe de qué expedición era el pendiente ni cuándo se quedó abierto, que es
        justo lo que necesita para ir al portal a comprobarlo.

        La etiqueta lleva nombre, correo o móvil de un tercero, y este fichero se
        queda en disco: `docs/SEGURIDAD_DATOS.md` §7 prohíbe volcar ahí a una persona
        por su nombre. Se guarda una **huella corta** que basta para casar la anotación
        con su cierre y para que un humano distinga dos envíos del mismo canal, y no
        permite reconstruir el dato. El `id_personalizado` no es un dato personal —es
        un código de expediente— y ese sí va en claro.
        """
        clave = uuid.uuid4().hex
        huella = hashlib.sha256(etiqueta.encode("utf-8")).hexdigest()[:12]
        marca = datetime.now(timezone.utc).isoformat()
        self._escribir({"clave": clave, "id_personalizado": id_personalizado, "canal": canal,
                        "destinatario_huella": huella, "timestamp": marca, "estado": "en_vuelo"})
        return clave

    def cerrar(self, clave: str, id_envio: str) -> None:
        """Cierra una anotación en vuelo.

        Cerrar una `clave` que no está en vuelo —porque ya se cerró antes, o porque
        nunca se abrió— dejaría `hechos()` con dos ids como si fueran dos envíos
        legítimos: exactamente lo que este registro existe para detectar. Se para
        aquí, en el propio punto de cierre, en vez de en una lectura posterior.
        """
        if clave not in {f["clave"] for f in self.en_vuelo()}:
            raise ExpedicionError(
                f"la clave {clave!r} no tiene una anotación en vuelo: ya se cerró, o "
                "nunca se abrió. Cerrarla ahora simularía un segundo envío que no "
                "existió.")
        self._escribir({"clave": clave, "estado": "hecho", "id_envio": id_envio})

    def en_vuelo(self, id_personalizado: str | None = None) -> list[dict]:
        """Anotaciones sin cerrar. Con `id_personalizado`, solo las de esa expedición."""
        abiertas: dict[str, dict] = {}
        for fila in self._lineas():
            if fila.get("estado") == "en_vuelo":
                abiertas[fila["clave"]] = fila
            else:
                abiertas.pop(fila["clave"], None)
        filas = list(abiertas.values())
        if id_personalizado is None:
            return filas
        return [f for f in filas if f.get("id_personalizado") == id_personalizado]

    def hechos(self) -> set[str]:
        return {f["id_envio"] for f in self._lineas() if f.get("estado") == "hecho"}

    def exigir_sin_pendientes(self, id_personalizado: str | None = None) -> None:
        """Para el flujo en vez de arriesgar un duplicado. Puede acotarse a una expedición."""
        if (p := self.en_vuelo(id_personalizado)):
            raise ExpedicionError(
                f"hay {len(p)} envío(s) anotados y sin confirmar: "
                + ", ".join(f"{f['canal']}/{f['destinatario_huella']} (clave {f['clave']}, "
                            f"anotado {f['timestamp']})" for f in p)
                + ". Queda SIN VERIFICAR si salieron. Compruébalo en el portal antes de "
                  "reintentar: un censo negativo del listado no autoriza a gastar.")


def ya_expedido(listado: list[dict], id_personalizado: str) -> set[str]:
    """`IdEnvio` que la plataforma ya tiene con ese identificador exacto."""
    return {e["id"] for e in listado if e.get("id_personalizado") == id_personalizado}
