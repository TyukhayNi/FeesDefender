"""El criterio del despacho para expedir una comunicación certificada.

Spec: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
El transporte vive en `core/codicert.py` y no sabe qué es un expediente.
"""
from __future__ import annotations

import re

from dataclasses import dataclass
from decimal import Decimal


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
