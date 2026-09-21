"""El criterio del jurídico para expedir una comunicación certificada.

Spec: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
El transporte vive en `core/codicert.py` y no sabe qué es un expediente.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import threading
import uuid

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from core import codicert as _cod


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


def _movil_match(bruto: str | None):
    """El `Match` de `_MOVIL` sobre `bruto` limpio de espacios/puntos/guiones, o
    `None` si no es un móvil español. Compartido por `movil_normalizado` (forma
    internacional, "34"+nueve dígitos) y `movil_postal` (nueve dígitos a secas,
    hallazgo H-10, revisión adversarial r2) para que las dos formas salgan SIEMPRE
    del mismo match y no puedan desincronizarse entre sí.
    """
    if not bruto:
        return None
    return _MOVIL.match(re.sub(r"[\s.\-()]", "", str(bruto)))


def movil_normalizado(bruto: str | None) -> str | None:
    """`34` + nueve dígitos, o `None` si no es un móvil español.

    El prefijo se pega porque es lo que la plataforma registra: el destinatario SMS de
    producción es `34645508869`. Un fijo devuelve `None` y el canal se declara ausente.

    Es la forma para el destinatario ELECTRÓNICO (`DestinatarioVerificable`, que usa
    `destinatarios_de` para correo/SMS): ese campo no tiene patrón y sí admite el
    prefijo (spec §1.1, líneas 154-161). Para el destinatario POSTAL del burofax, que
    SÍ tiene patrón (`^[67]\\d{8}$`, sin prefijo), usa `movil_postal`.
    """
    m = _movil_match(bruto)
    return f"34{m.group(1)}" if m else None


def movil_postal(bruto: str | None) -> str | None:
    """Nueve dígitos SIN prefijo, para el `telefono` del destinatario POSTAL
    (hallazgo H-10, revisión adversarial r2).

    El contrato aporta el patrón `^[67]\\d{8}$` para `DestinatarioPostal.telefono` --
    el teléfono de incidencia del burofax -- DISTINTO del destinatario electrónico
    (`DestinatarioVerificable`), que no tiene patrón y sí admite el prefijo
    internacional (spec §1.1, líneas 154-161). `ficha_postal` reutilizaba antes
    `movil_normalizado` tal cual para los dos canales: "600000001" salía como
    "34600000001" en el campo postal -- once dígitos, que incumple el patrón
    documentado para ESE campo. El comportamiento real del servidor ante un
    teléfono con prefijo en este campo NO se ha verificado contra Codicert: lo que
    se corrige aquí es el incumplimiento del contrato aportado, no una medición
    nueva.
    """
    m = _movil_match(bruto)
    return m.group(1) if m else None


_CAMPOS_NOMBRE_COMPLETO = ("nombre", "1apellido", "2apellido")


def nombre_completo_de(parte: dict) -> str:
    """Nombre completo de una parte tal como la devuelve el CRM (hallazgo H-06).

    `clientes_contrarios` separa el nombre en tres campos independientes —``nombre``,
    ``1apellido``, ``2apellido``—, confirmado en el atlas del repositorio
    (`docs/CRM_SUDESPACHO_ATLAS.md` § clientes_contrarios) y en
    `core/sudespacho_relations.NuevoClienteContrario`; el CRM nunca junta el nombre
    completo en un solo campo. Leer solo ``nombre`` sacaba al requerido con únicamente
    su nombre de pila en una comunicación jurídica irreversible.

    Para una persona física compone "nombre 1apellido 2apellido" con los apellidos que
    haya —el segundo puede faltar, como campo ausente o como cadena vacía—, en el mismo
    orden que ya usa el CRM: no se inventa uno distinto. Para una razón social, la
    convención de la casa deja ``nombre`` con la razón social completa en mayúsculas y
    los dos apellidos vacíos: no hay nada que concatenar y el resultado es ``nombre``
    tal cual. Cualquier espacio sobrante, interno o de borde, se normaliza a uno solo.
    """
    trozos = [" ".join(str(parte.get(campo) or "").split()) for campo in _CAMPOS_NOMBRE_COMPLETO]
    return " ".join(t for t in trozos if t)


_OBLIGATORIOS_POSTAL = ("nombre", "direccion", "poblacion", "provincia", "cp")

# Formas en que puede llegar "España" en el dato de entrada (el CRM, cuando lo trae).
# `clientes_contrarios` no declara hoy un campo `pais` propio (docs/CRM_SUDESPACHO_
# ATLAS.md § clientes_contrarios): la ausencia se resuelve como España -- es el caso
# de todos los contrarios reales de hoy --, y un valor explícito que no case con
# ninguna de estas formas se rechaza (hallazgo H-10, revisión adversarial r2).
_PAIS_ESPANA_VALIDOS = frozenset({"ESPAÑA", "ESPANA", "SPAIN", "ES"})


def _pais_postal_de(parte: dict) -> str:
    """`pais` del destinatario POSTAL: Codicert solo admite `"España"` en el burofax
    (hallazgo H-10, revisión adversarial r2; contrato: `pais` solo "España", spec
    §1.1, y regla 5 del §5).

    Antes se escribía siempre "España" sin mirar el dato de entrada: una ficha con
    país Francia, población y provincia extranjeras y CP francés se convertía en un
    envío dirigido a España, sin ningún aviso. Aquí se resuelve explícitamente: sin
    `pais` (el caso de hoy, porque el CRM no lo declara) se sigue asumiendo España;
    con un `pais` que NO lo sea, se para en el plan en vez de fabricar el envío
    erróneo.
    """
    bruto = str(parte.get("pais") or "").strip()
    if not bruto or bruto.upper() in _PAIS_ESPANA_VALIDOS:
        return "España"
    raise ExpedicionError(
        f"la ficha postal de {(parte.get('nombre') or '').strip() or '(sin nombre)'} "
        f"tiene país {bruto!r}: el burofax de Codicert solo admite España (spec §1.1). "
        "No se puede resolver un domicilio extranjero -- corrígelo en el CRM o "
        "exclúyelo del canal postal antes de planificar."
    )


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
    pais = _pais_postal_de(parte)
    nombre = nombre_completo_de(parte)
    return {"nombre": nombre, "a_atencion": parte.get("a_atencion") or nombre,
            "pais": pais, "direccion": parte["direccion"], "poblacion": parte["poblacion"],
            "provincia": provincia_codicert(parte["provincia"]), "cp": parte["cp"],
            **({"telefono": m} if (m := movil_postal(parte.get("movil"))) else {})}


# Tarifa «80», leída del portal de producción el 2026-09-17. Cada línea incluye la
# notificación: la entrega electrónica son 0,3867 € más el canal.
TARIFA: dict[str, Decimal] = {
    "burofax": Decimal("16.9716"),
    "correo": Decimal("0.3867") + Decimal("0.4064"),
    "sms": Decimal("0.3867") + Decimal("0.0834"),
}

# Límites de preflight (hallazgo H-09, revisión adversarial r2), medidos en el spec
# §1.4 y §7: el motor se ciñe al SUELO SEGURO donde la UI y el contrato discrepan
# (p. ej. la EEC declara 1..10 en el contrato pero la UI -- y el motor -- se paran en
# 6). "MB" se cuenta en mebibytes (1 MiB = 1_048_576 bytes): el spec no fija la base y
# el modo de fallo medido usa "MiB"; ningún tamaño de este módulo se ha verificado
# contra el servidor real.
_BYTES_POR_MB = 1_048_576
MAX_FICHEROS_BUROFAX = 10
MAX_PAGINAS_BUROFAX = 200
MAX_FICHEROS_EEC = 6
MAX_BYTES_EEC = 60 * _BYTES_POR_MB
# 1 MB incluido en sandbox, 6 en producción (spec §1.4): el sobrecoste por MB se paga
# por envío EEC, no una sola vez por expedición -- cada envío lleva el mismo juego de
# adjuntos completo.
_MB_INCLUIDOS_EEC: dict[str, int] = {"sandbox": 1, "produccion": 6}
PRECIO_MB_ADICIONAL = Decimal("0.0288")


@dataclass(frozen=True)
class EnvioPrevisto:
    """Un envío del plan: un canal y un destinatario ya resuelto.

    `destinatario` sigue siendo un `dict` corriente, mutable, a propósito
    (hallazgo H-01, revisión adversarial r2): `frozen=True` congela la
    instancia, no lo que cuelga de ella, así que congelarlo aquí sería
    cosmético -- `ejecutar` nunca vuelve a leer `plan.envios` para decidir a
    quién manda. Lee `envios_ahora`, la instantánea que acaba de resolver y
    sellar contra el CRM dentro de la propia llamada, así que mutar este
    `dict` después de aprobar el plan ya no tiene ningún efecto sobre el
    envío real.
    """

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

    Se rechaza un requerido SIN canales (más abajo), pero eso no cubre la AUSENCIA de
    requeridos (hallazgo H-16, revisión adversarial r2): `get_relaciones` puede
    devolver legítimamente ninguna relación —un expediente sin contrarios vinculados
    en el CRM—, y `partes_de` lo convierte en `[]`. Sin este control, `destinatarios_de
    ([])` devolvía `([], [])` sin avisar: coste cero y cero envíos se aceptaban como un
    plan ejecutable, y ejecutarlo salía con éxito imprimiendo "ENVIADO: " vacío -- no
    hay ningún envío previo que lo explique, es que nunca hubo a quién mandarlo.
    """
    if not partes:
        raise ExpedicionError(
            "no hay ningún requerido: el expediente no tiene contrarios vinculados en "
            "el CRM (get_relaciones devolvió una lista vacía de 'clientes_contrarios'). "
            "No se puede planificar una comunicación sin destinatarios -- vincula al "
            "contrario en el CRM antes de expedir."
        )
    envios: list[EnvioPrevisto] = []
    ausencias: list[str] = []
    for p in partes:
        nombre = nombre_completo_de(p) or "(sin nombre)"
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
        # Se captura ANTES de sobrescribir "nombre" (y de vaciar los apellidos): si no,
        # el fallback de ficha_postal (a_atencion or nombre completo) recupera el
        # nombre YA conjunto, no la persona de contacto (regla del jurídico: "nombre"
        # lleva a los dos, "a_atencion" a uno).
        contacto = base.get("a_atencion") or nombre_completo_de(base)
        base["nombre"] = " Y ".join(nombre_completo_de(g) for g in grupo)
        # Los apellidos que trae "base" son los del PRIMER miembro del grupo (heredados
        # de dict(grupo[0])) y ya están dentro del "nombre" conjunto de arriba: si se
        # dejan, ficha_postal() los concatenaría una segunda vez (H-06 al cuadrado).
        # Vacíos, nombre_completo_de(base) devuelve "nombre" tal cual -- el mismo camino
        # que ya usa una razón social.
        base["1apellido"] = ""
        base["2apellido"] = ""
        base["a_atencion"] = contacto
        ficha = ficha_postal(base)
        etiqueta = f"{ficha['nombre']} · {ficha['direccion']}, {ficha['poblacion']}"
        if len(grupo) > 1:
            etiqueta += "  ⚠ sobre conjunto: acredita entrega EN EL DOMICILIO, no a cada uno"
        envios.append(EnvioPrevisto("burofax", ficha, etiqueta))
    return envios, ausencias


def coste_de(envios: list[EnvioPrevisto], *,
             sobrecoste_eec_por_envio: Decimal = Decimal("0")) -> Decimal:
    """Suma la tarifa por canal de cada envío previsto, más el sobrecoste por volumen
    documental de los envíos EEC (correo/SMS) (hallazgo H-09, revisión adversarial
    r2). Antes ignoraba los bytes: un documento de pocos bytes y otro de más de 7
    MiB costaban EXACTAMENTE lo mismo. `sobrecoste_eec_por_envio` lo calcula
    `_preflight_documentos` -- el mismo para cada envío EEC, porque todos llevan el
    mismo juego de adjuntos completo -- y por defecto es cero: quien no lo pase (los
    tests que ejercitan solo la tarifa base, y el coste residual de `ejecutar`)
    sigue viendo la suma de siempre.
    """
    base = sum((TARIFA[e.canal] for e in envios), Decimal("0"))
    if not sobrecoste_eec_por_envio:
        return base
    return base + sum(
        (sobrecoste_eec_por_envio for e in envios if e.canal in ("correo", "sms")),
        Decimal("0"))


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
    """Asunto y cuerpo de la comunicación. Nunca nombran los términos de la oferta.

    `_asegurar_sin_prohibidos` se aplica aquí, dentro de la función pública que
    compone el texto real -- no solo se acredita como lógica aislada (hallazgo H-14,
    revisión adversarial r2): `test_H14_texto_de_recorre_la_guarda_de_verdad_no_solo_
    el_helper` (tests/test_expedicion_plan.py) recorre esta conexión de verdad, y la
    mutación que sustituye la línea de abajo por `pass` se acreditó en rojo -- y se
    deshizo -- durante el remedio de ese hallazgo.
    """
    _asegurar_sin_prohibidos(f"{_ASUNTO_TPL} {_CUERPO_TPL}")
    return _ASUNTO_TPL.format(w_code=w_code), _CUERPO_TPL.format(w_code=w_code)


def _huella(contenido: str | dict) -> str:
    """Huella corta y no reversible del CONTENIDO aprobado (hallazgo H-04, r2).

    Antes se calculaba sobre la ETIQUETA de presentación (`EnvioPrevisto.etiqueta`),
    pensada solo para que la lea un humano en el plan: en el burofax ni siquiera
    incluye el código postal, la provincia o la persona de atención. Cambiar el
    código postal y aprobar el plan nuevo daba "ya está completa" con el domicilio
    VIEJO, porque la etiqueta -- y por tanto la huella -- no cambiaba. `ejecutar` le
    pasa ahora el `dict` `destinatario` completo, resuelto DE NUEVO contra el CRM: se
    canonicaliza con las claves ordenadas antes de hashear, así que cualquier campo
    que cambie -- código postal incluido -- produce una huella distinta y el envío
    vuelve a contar como pendiente. Sigue aceptando una cadena simple para los tests
    que ejercitan `RegistroIntencion` de forma aislada, sin pasar por `ejecutar`.

    `RegistroIntencion.anotar` la usa para no persistir el dato en claro
    (`docs/SEGURIDAD_DATOS.md` §7), y `ejecutar` la reutiliza para saber, al reanudar
    una expedición a medias, qué par (canal, huella) ya consta cerrado.
    """
    crudo = (json.dumps(contenido, sort_keys=True, ensure_ascii=False)
             if isinstance(contenido, dict) else contenido)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:12]


def _reloj_utc() -> datetime:
    """Reloj por defecto de `RegistroIntencion`: UTC real, como siempre.

    `ejecutar` inyecta `entorno_exp.ahora` en su lugar: todo lo no determinista de este
    módulo entra por el puerto único de `EntornoExpedicion`, y sin esta conexión el
    docstring de `ahora` sería de boquilla.
    """
    return datetime.now(timezone.utc)


#: Los tres estados que reconoce el registro. "en_vuelo" es el único ABIERTO; los
#: otros dos son cierres -- distintos entre sí porque significan cosas distintas
#: para quien reanuda (hallazgo H-07, revisión adversarial r2): "hecho" es un envío
#: real con `IdEnvio`, "rechazado" es la certeza de que NO salió (un 422 del
#: servidor), sin inventar un identificador que no existe.
_ESTADO_EN_VUELO = "en_vuelo"
_ESTADO_HECHO = "hecho"
_ESTADO_RECHAZADO = "rechazado"
_ESTADOS_RECONOCIDOS = (_ESTADO_EN_VUELO, _ESTADO_HECHO, _ESTADO_RECHAZADO)

#: Campos que exige cada tipo de fila, más allá de `clave` y `estado` (comunes a las
#: tres). `entorno`/`usuario` NO están aquí a propósito: una fila sin ellos es
#: "formato antiguo" (hallazgo H-04), un problema distinto de un esquema inválido, y
#: `_exigir_formato_reconocido` ya lo declara por separado -- exigirlos aquí
#: convertiría cualquier registro anterior a H-04 en corrupción semántica.
_CAMPOS_APERTURA = ("id_personalizado", "canal", "destinatario_huella", "timestamp")
_CAMPOS_CIERRE: dict[str, tuple[str, ...]] = {
    _ESTADO_HECHO: ("id_envio",),
    _ESTADO_RECHAZADO: ("motivo",),
}


class RegistroIntencion:
    """Rastro append-only de que *nosotros* llamamos, antes de que el servidor responda.

    No es una segunda fuente de verdad sobre los envíos —esa es Codicert— sino sobre un
    hecho nuestro que la plataforma no puede contarnos. Sin él, un timeout deja un
    burofax pagado cuyo `IdEnvio` no se puede reencontrar: `GET /envios` no filtra por
    `id_personalizado`.

    Todas las plazas y cuentas comparten hoy el mismo fichero bajo el directorio de
    trabajo (`entorno_exp.raiz`): sin `entorno`/`usuario` en cada anotación (hallazgo
    H-04, revisión adversarial r2), un cierre de sandbox se confundía con uno de
    producción, o el de una cuenta con el de otra, porque `id_personalizado` por sí
    solo no distingue de dónde vino cada cierre -- el mismo w_code puede expedirse en
    los dos. Ver `__init__`, `_coincide_entorno` y `_exigir_formato_reconocido`.
    """

    def __init__(self, ruta: Path, *, entorno: str | None = None, usuario: str | None = None,
                ahora: Callable[[], datetime] = _reloj_utc) -> None:
        """`entorno` y `usuario` identifican DE QUIÉN es cada anotación (hallazgo
        H-04, r2): todas las plazas y todas las cuentas escribían en el mismo
        fichero bajo el directorio de trabajo, así que un cierre de sandbox se
        confundía con uno de producción, o el de una cuenta con el de otra. Van en
        claro -- ninguno de los dos es un dato personal del destinatario, que es lo
        que protege `docs/SEGURIDAD_DATOS.md` §7 -- y viajan en la fila `en_vuelo`
        para que las consultas puedan filtrar por ellos (`ejecutar` los rellena con
        `entorno_exp.entorno`/`entorno_exp.usuario`). `None` por defecto: los tests
        que ejercitan este primitivo de forma aislada, sin pasar por `ejecutar`, no
        necesitan declarar ninguno de los dos para seguir funcionando como siempre
        -- solo importa que quien escribe y quien lee compartan el mismo par.
        """
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.entorno = entorno
        self.usuario = usuario
        self._ahora = ahora

    def _coincide_entorno(self, fila: dict) -> bool:
        """¿Esta fila 'en_vuelo' pertenece al entorno/cuenta de ESTA instancia?

        Por IGUALDAD exacta, no por ausencia: una fila sin campo `entorno` (formato
        viejo, anterior a H-04) nunca coincide con una instancia que tiene un
        entorno concreto -- no se puede sostener que sea de este entorno, así que
        no cuenta como si lo fuera. `_exigir_formato_reconocido` es quien declara
        ese caso en vez de dejarlo pasar en silencio.
        """
        return fila.get("entorno") == self.entorno and fila.get("usuario") == self.usuario

    def _lineas_numeradas(self) -> list[tuple[int, dict]]:
        """Cada línea no vacía, parseada, con su número (base 1, como en el fichero).

        Un corte a mitad de `write` puede dejar la última línea truncada. Tragarla en
        silencio perdería el rastro de un envío que ya se pagó, así que se declara con
        fichero y número de línea para que un humano la revise -- igual que hace
        `_estados_por_clave` con la corrupción SEMÁNTICA (hallazgo H-15): esto cubre
        solo que cada línea, aislada, sea JSON legible; no dice nada de si su
        `estado` se reconoce ni de si la transición que propone es válida.
        """
        if not self.ruta.is_file():
            return []
        filas: list[tuple[int, dict]] = []
        for numero, l in enumerate(
                self.ruta.read_text(encoding="utf-8").splitlines(), start=1):
            if not l.strip():
                continue
            try:
                filas.append((numero, json.loads(l)))
            except json.JSONDecodeError as exc:
                raise ExpedicionError(
                    f"{self.ruta}: la línea {numero} del registro de intención no es "
                    f"JSON válido ({exc}). No se ignora: puede ser el rastro de un "
                    "envío ya pagado. Revísala a mano antes de continuar."
                ) from exc
        return filas

    def _lineas(self) -> list[dict]:
        return [fila for _, fila in self._lineas_numeradas()]

    def _error_linea(self, numero: int, mensaje: str) -> ExpedicionError:
        return ExpedicionError(
            f"{self.ruta}: la línea {numero} del registro de intención {mensaje}")

    def _estados_por_clave(self) -> dict[str, dict]:
        """Reconstruye el estado de CADA clave, validando esquema, estado y la
        secuencia de transiciones (hallazgo H-15, revisión adversarial r2).

        Antes se aceptaba cualquier JSON sintácticamente válido sin mirar su
        CONTENIDO: en `en_vuelo()`, cualquier `estado` distinto de `"en_vuelo"` se
        interpretaba como un cierre -- así que un typo (`"hehco"`) hacía
        desaparecer el pendiente de `en_vuelo()` SIN que apareciera en `hechos()`
        (que exige la cadena exacta `"hecho"`): el rastro del envío se esfumaba de
        los dos controles a la vez, sin ningún aviso. Y los cierres duplicados solo
        se impedían llamando a `cerrar()`/`rechazar()` -- si el fichero ya traía
        dos líneas de cierre para la misma clave (reparado a mano, o importado),
        `_cerrados_de` las devolvía las dos como envíos explicados.

        Se para, con fichero y línea -- igual que ya hace el JSON ilegible --, ante
        cualquiera de estos, en el orden en que aparecen en el fichero:

        - un `estado` que no es ninguno de los tres reconocidos (`en_vuelo`,
          `hecho`, `rechazado`): un estado que no se entiende NO puede consumirse
          como si cerrara una intención;
        - una fila a la que le falta un campo que su propio estado exige (esquema
          inválido) -- `entorno`/`usuario` quedan fuera de esta lista a propósito,
          ver `_CAMPOS_APERTURA`;
        - un cierre (`hecho` o `rechazado`) para una clave sin apertura `en_vuelo`
          previa en el fichero (cierre huérfano);
        - un cierre para una clave que ya estaba cerrada (cierre duplicado);
        - una apertura `en_vuelo` para una clave que el fichero ya conocía (una
          clave es un `uuid4`, irrepetible: no debe volver a abrirse).

        Devuelve, por clave, `{"estado", "apertura", "linea_apertura"}` y, si ya
        cerró, además `{"cierre", "linea_cierre"}`. `en_vuelo`, `hechos`,
        `_anotaciones_de` y `_cerrados_de` leen todas de aquí: es la validación
        COMPARTIDA que pide el hallazgo, la misma que usa `cerrar`/`rechazar` para
        comprobar que una clave sigue abierta antes de escribir su cierre.
        """
        estados: dict[str, dict] = {}
        for numero, fila in self._lineas_numeradas():
            clave = fila.get("clave")
            if not clave or not isinstance(clave, str):
                raise self._error_linea(numero, "no tiene una 'clave' válida (esquema inválido).")
            estado = fila.get("estado")
            if estado is None:
                raise self._error_linea(
                    numero, f"no tiene 'estado' para la clave {clave!r} (esquema inválido).")
            if estado not in _ESTADOS_RECONOCIDOS:
                raise self._error_linea(
                    numero,
                    f"tiene estado {estado!r} desconocido para la clave {clave!r}; los "
                    f"reconocidos son {_ESTADOS_RECONOCIDOS}. Un estado que no se "
                    "entiende no se puede tratar como si cerrara la intención.")

            if estado == _ESTADO_EN_VUELO:
                faltan = [c for c in _CAMPOS_APERTURA if not fila.get(c)]
                if faltan:
                    raise self._error_linea(
                        numero,
                        f"abre la clave {clave!r} sin {', '.join(faltan)} (esquema "
                        "inválido).")
                if clave in estados:
                    raise self._error_linea(
                        numero,
                        f"reabre la clave {clave!r}, que ya tenía una fila previa en "
                        f"el registro (estado {estados[clave]['estado']!r}): una "
                        "clave -- uuid4, irrepetible -- no debe volver a abrirse.")
                estados[clave] = {"estado": _ESTADO_EN_VUELO, "apertura": fila,
                                  "linea_apertura": numero}
            else:  # "hecho" | "rechazado": un cierre
                faltan = [c for c in _CAMPOS_CIERRE[estado] if not fila.get(c)]
                if faltan:
                    raise self._error_linea(
                        numero,
                        f"cierra la clave {clave!r} como {estado!r} sin "
                        f"{', '.join(faltan)} (esquema inválido).")
                previo = estados.get(clave)
                if previo is None:
                    raise self._error_linea(
                        numero,
                        f"cierra como {estado!r} la clave {clave!r}, que no tiene "
                        "ninguna apertura 'en_vuelo' previa en el registro (cierre "
                        "huérfano).")
                if previo["estado"] != _ESTADO_EN_VUELO:
                    raise self._error_linea(
                        numero,
                        f"cierra OTRA VEZ, como {estado!r}, la clave {clave!r}: ya "
                        f"estaba cerrada como {previo['estado']!r} (cierre "
                        "duplicado).")
                estados[clave] = {**previo, "estado": estado, "cierre": fila,
                                  "linea_cierre": numero}
        return estados

    def _escribir(self, fila: dict) -> None:
        with self.ruta.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")

    def anotar(self, id_personalizado: str, canal: str, contenido: str | dict) -> str:
        """Anota la intención SIN persistir datos personales del destinatario.

        El diseño (§4.3) exige `(id_personalizado, canal, destinatario, timestamp,
        en_vuelo)` antes de cada POST: sin ellos, el humano que lee un "SIN VERIFICAR"
        no sabe de qué expedición era el pendiente ni cuándo se quedó abierto, que es
        justo lo que necesita para ir al portal a comprobarlo.

        `contenido` lleva nombre, dirección, correo o móvil de un tercero, y este
        fichero se queda en disco: `docs/SEGURIDAD_DATOS.md` §7 prohíbe volcar ahí a
        una persona por su nombre. Se guarda una **huella corta** (hallazgo H-04: del
        `dict` destinatario completo, no de la etiqueta de presentación -- ver
        `_huella`) que basta para casar la anotación con su cierre, para que un
        humano distinga dos envíos del mismo canal, y para detectar que el contenido
        cambió entre dos ejecuciones -- y no permite reconstruir el dato.
        `id_personalizado` no es un dato personal —es un código de expediente—, y
        `entorno`/`usuario` tampoco —es la cuenta propia del jurídico, no la del
        destinatario—: los tres van en claro.
        """
        clave = uuid.uuid4().hex
        huella = _huella(contenido)
        marca = self._ahora().isoformat()
        self._escribir({"clave": clave, "id_personalizado": id_personalizado, "canal": canal,
                        "destinatario_huella": huella, "entorno": self.entorno,
                        "usuario": self.usuario, "timestamp": marca, "estado": "en_vuelo"})
        return clave

    def _exigir_clave_en_vuelo(self, clave: str, *, gerundio: str) -> None:
        """Comparte el candado de `cerrar` y `rechazar`: la clave debe seguir abierta.

        Cerrar o rechazar una `clave` que no está en vuelo —porque ya se resolvió
        antes, o porque nunca se abrió— dejaría dos transiciones para el mismo
        envío, como si fueran dos hechos legítimos: exactamente lo que este
        registro existe para detectar. Se para aquí, en el propio punto de
        escritura, en vez de en una lectura posterior -- `_estados_por_clave`
        (hallazgo H-15) es la red que atrapa esa misma corrupción si, en vez de
        pasar por aquí, ya viene escrita en el fichero.
        """
        if clave not in {f["clave"] for f in self.en_vuelo()}:
            raise ExpedicionError(
                f"la clave {clave!r} no tiene una anotación en vuelo: ya se resolvió "
                f"(cerrada o rechazada), o nunca se abrió. {gerundio} ahora simularía "
                "un segundo desenlace para un envío que no lo tuvo.")

    def cerrar(self, clave: str, id_envio: str) -> None:
        """Cierra una anotación en vuelo con un envío REAL: la plataforma lo aceptó
        y le dio un `IdEnvio`. Ver `rechazar` para el otro cierre posible."""
        self._exigir_clave_en_vuelo(clave, gerundio="Cerrarla")
        self._escribir({"clave": clave, "estado": "hecho", "id_envio": id_envio})

    def rechazar(self, clave: str, motivo: str) -> None:
        """Cierra una anotación en vuelo con un RECHAZO DEFINITIVO (hallazgo H-07,
        revisión adversarial r2): la plataforma respondió, y respondió que NO.

        Antes, el registro solo sabía resolver una intención con un `IdEnvio` real
        (`cerrar`): cualquier excepción posterior a `anotar` -- incluido un 422,
        `CodicertDatosInvalidosError`, del que sabemos con CERTEZA que el envío no
        salió -- dejaba la anotación `en_vuelo` para siempre. El registro solo
        permite cerrar con un identificador de envío, así que no había forma
        auditada de dejar constancia de "esto no salió": borrar la línea, inventar
        un `IdEnvio` o cambiar de ordinal no son una reanudación trazable, y
        `exigir_sin_pendientes` bloqueaba cualquier intento futuro de esa
        expedición, incluso después de corregir el dato que Codicert rechazó.

        Esta transición resuelve la intención SIN inventar un identificador: dado
        que nunca hubo un envío real, no hay `IdEnvio` que guardar. Al cerrar,
        `en_vuelo()` deja de contarla -- ya no bloquea una reanudación -- pero
        `hechos()`/`pares_cerrados()` tampoco la cuentan como enviada (ambas exigen
        `estado == "hecho"`): el par (canal, huella) vuelve a aparecer como
        pendiente en la siguiente llamada a `ejecutar`, y se reintenta -- una vez
        corregido el dato, no en bucle -- igual que un envío que nunca se llegó a
        intentar.

        Un DESENLACE DESCONOCIDO -- un timeout, un error de transporte -- es
        justo lo contrario: pudo salir. Esos NUNCA llegan aquí (`ejecutar` solo
        llama a `rechazar` ante `CodicertDatosInvalidosError`); se quedan
        `en_vuelo`, bloqueados hasta que un humano reconcilie mirando el portal --
        no se propone reintentarlos solos.

        `motivo` es diagnóstico para el humano que lee este cierre, NUNCA texto
        libre del servidor ni del destinatario: `ejecutar` pasa una cadena fija
        derivada del TIPO de excepción, nunca el cuerpo de la respuesta de
        Codicert, que podría (aunque no se ha observado) traer de vuelta un dato
        del payload rechazado. El registro sigue sin poder contener datos
        personales del destinatario (`docs/SEGURIDAD_DATOS.md` §7): ese límite no
        distingue de qué transición viene la fila.
        """
        self._exigir_clave_en_vuelo(clave, gerundio="Rechazarla")
        self._escribir({"clave": clave, "estado": "rechazado", "motivo": motivo})

    def en_vuelo(self, id_personalizado: str | None = None) -> list[dict]:
        """Anotaciones sin cerrar de ESTE entorno/cuenta. Con `id_personalizado`, solo
        las de esa expedición (hallazgo H-04: una anotación de otro entorno u otra
        cuenta no pertenece a esta instancia, así que no cuenta ni bloquea aquí).

        Lee de `_estados_por_clave` (hallazgo H-15): una clave cuenta como en vuelo
        solo si su ÚLTIMA transición validada sigue siendo `"en_vuelo"` -- un
        estado que no se reconoce, o un cierre huérfano/duplicado, para la lectura
        entera antes de llegar aquí, nunca se cuela como si cerrara la intención.
        """
        filas = [info["apertura"] for info in self._estados_por_clave().values()
                if info["estado"] == _ESTADO_EN_VUELO]
        filas = [f for f in filas if self._coincide_entorno(f)]
        if id_personalizado is None:
            return filas
        return [f for f in filas if f.get("id_personalizado") == id_personalizado]

    def hechos(self) -> set[str]:
        """`IdEnvio` de las claves cerradas como `"hecho"` -- nunca `"rechazado"`,
        que por definición nunca tuvo un envío real (hallazgo H-07)."""
        return {info["cierre"]["id_envio"] for info in self._estados_por_clave().values()
               if info["estado"] == _ESTADO_HECHO}

    def _anotaciones_de(self, id_personalizado: str) -> list[dict]:
        """Filas 'en_vuelo' -- origen, sigan abiertas o ya cerradas (con cualquiera
        de los dos cierres) -- de esta expedición, SIN filtrar por entorno/cuenta:
        es la base para detectar formato antiguo (hallazgo H-04) antes de decidir
        si una anotación cuenta o no."""
        return [info["apertura"] for info in self._estados_por_clave().values()
               if info["apertura"].get("id_personalizado") == id_personalizado]

    def primera_anotacion_de(self, id_personalizado: str) -> datetime | None:
        """El `timestamp` más antiguo anotado para esta expedición, o `None`.

        Lo usa `refrescar` para abrir la ventana de `GET /envios` por el sitio
        correcto: el registro es nuestro y sabe CUÁNDO se expidió, mientras que la
        ventana por defecto solo adivina.

        Traga las fechas ilegibles en vez de parar, al revés que `_fecha_exigida`:
        esta fecha solo ABRE una ventana de consulta, y una anotación con el
        `timestamp` roto no debe impedir releer la expedición. El peor efecto de
        ignorarla es consultar una ventana más corta, y para eso está el suelo de
        `ventana_dias`. Público —y no `_privado`— porque `refrescar` lo consume
        desde fuera de la clase: un módulo que hurga en los privados de otro es
        exactamente cómo se pierde el contrato.
        """
        fechas: list[datetime] = []
        for fila in self._anotaciones_de(id_personalizado):
            try:
                f = datetime.fromisoformat(str(fila.get("timestamp")))
            except (TypeError, ValueError):
                continue
            if f.tzinfo is not None:
                fechas.append(f)
        return min(fechas) if fechas else None

    def _exigir_formato_reconocido(self, id_personalizado: str) -> None:
        """Para y declara si `id_personalizado` tiene anotaciones en FORMATO ANTIGUO.

        Un registro escrito antes de H-04 no lleva `entorno` ni `usuario`: no se puede
        sostener si esa anotación es de este entorno/cuenta o de otro -- ni incluirla
        ni excluirla en silencio es defendible, así que se declara y se para, igual
        que cualquier otra ausencia que no se sostiene sobre algo inmediato (spec
        §5.2, mismo criterio que `sin_explicar` en `ejecutar`).
        """
        viejas = [f for f in self._anotaciones_de(id_personalizado)
                 if "entorno" not in f or "usuario" not in f]
        if viejas:
            claves = ", ".join(sorted(f["clave"] for f in viejas))
            raise ExpedicionError(
                f"{self.ruta}: el registro local tiene {len(viejas)} anotación(es) de "
                f"{id_personalizado!r} en FORMATO ANTIGUO -- sin entorno ni cuenta "
                f"emisora (clave(s): {claves}). No se puede sostener si son de este "
                "entorno/cuenta o de otro. Queda SIN VERIFICAR: reconcílialas a mano "
                "(compruébalas en el portal y añádeles entorno/usuario, o ciérralas) "
                "antes de continuar.")

    def _cerrados_de(self, id_personalizado: str) -> list[dict]:
        """Anotaciones de `id_personalizado`, DE ESTE ENTORNO/CUENTA, que ya se
        cerraron con un envío REAL (`"hecho"`, nunca `"rechazado"` -- hallazgo
        H-07: un rechazo no explica ni completa nada, porque no salió), con su
        `id_envio` añadido.

        La línea "hecho" solo lleva `clave` e `id_envio` (spec §4.3): no dice de qué
        expedición era, por qué canal, ni de qué entorno/cuenta. Se cruza con la
        anotación "en_vuelo" que la abrió —única por `clave`, la genera `uuid4()`,
        y `_estados_por_clave` (hallazgo H-15) ya garantiza que sea EXACTAMENTE una—
        para recuperar `id_personalizado`, `canal`, `destinatario_huella`, `entorno`
        y `usuario`. El cruce exige además que esa anotación de origen sea de ESTE
        entorno/cuenta (hallazgo H-04): un cierre de sandbox no debe explicar ni
        completar una expedición de producción, aunque compartan `id_personalizado`
        -- el mismo w_code puede expedirse en los dos.
        """
        salida: list[dict] = []
        for info in self._estados_por_clave().values():
            if info["estado"] != _ESTADO_HECHO:
                continue
            apertura = info["apertura"]
            if not self._coincide_entorno(apertura):
                continue
            if apertura.get("id_personalizado") != id_personalizado:
                continue
            salida.append({**apertura, "id_envio": info["cierre"]["id_envio"]})
        return salida

    def pares_cerrados(self, id_personalizado: str) -> set[tuple[str, str]]:
        """Pares (canal, huella) ya cerrados para esta expedición.

        `ejecutar` los usa para saltar, al reanudar, los envíos que ya se hicieron y
        mandar solo los que faltan: nunca repetir lo hecho.
        """
        return {(f["canal"], f["destinatario_huella"]) for f in self._cerrados_de(id_personalizado)}

    def ids_hechos_de(self, id_personalizado: str) -> set[str]:
        """`IdEnvio` que el registro local explica para esta expedición.

        `ejecutar` contrasta esto contra lo que la plataforma diga tener: si la
        plataforma sabe de un envío que este conjunto no explica, la ausencia no se
        puede sostener sobre algo inmediato y el flujo se para (spec §5.2): pudo
        expedirse desde otra máquina o desde el portal.
        """
        return {f["id_envio"] for f in self._cerrados_de(id_personalizado)}

    def exigir_sin_pendientes(self, id_personalizado: str | None = None) -> None:
        """Para el flujo en vez de arriesgar un duplicado. Puede acotarse a una expedición.

        Acotada a una expedición, primero comprueba que el registro no tenga
        anotaciones de ESA expedición en formato antiguo (hallazgo H-04): sin esa
        comprobación, una anotación sin entorno/cuenta se colaría en `en_vuelo()` (si
        coincide por casualidad, `None == None`) o se descartaría en silencio, en vez
        de declararse.
        """
        if id_personalizado is not None:
            self._exigir_formato_reconocido(id_personalizado)
        if (p := self.en_vuelo(id_personalizado)):
            raise ExpedicionError(
                f"hay {len(p)} envío(s) anotados y sin confirmar: "
                + ", ".join(f"{f['canal']}/{f['destinatario_huella']} (clave {f['clave']}, "
                            f"anotado {f['timestamp']})" for f in p)
                + ". Queda SIN VERIFICAR si salieron. Compruébalo en el portal antes de "
                  "reintentar: un censo negativo del listado no autoriza a gastar.")


class RegistroCosecha:
    """Rastro append-only de qué certificados se han subido ya al CRM.

    **Es el instrumento que autoriza a NO subir**, y existe por el mismo motivo que
    `RegistroIntencion` existe para los envíos: un censo del gestor documental no
    puede sostener una ausencia. El listado filtrado del CRM tiene latencia medida y
    ya duplicó un certificado el 2026-09-09 (`INTEGRACION_SUDESPACHO.md` §17.4); este
    fichero es nuestro, se escribe antes de la llamada y no tiene latencia ninguna.

    **La clave es el `IdEnvio`, no el `sha256` del certificado.** El PDF es estable
    entre dos descargas seguidas (medido el 2026-09-21), pero se regenera cuando el
    estado avanza, así que su huella no identifica «el certificado de este envío»:
    identifica «el certificado de este envío en este estado». Como clave de
    idempotencia sería inestable justo cuando importa.

    Lleva `entorno` y `usuario` por la misma razón que `RegistroIntencion` (hallazgo
    H-04 de su R2): todas las cuentas comparten fichero bajo el directorio de
    trabajo, y sin ellos un cierre de sandbox explicaría uno de producción.
    """

    def __init__(self, ruta: Path, *, entorno: str | None = None,
                 usuario: str | None = None,
                 ahora: Callable[[], datetime] = _reloj_utc) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.entorno, self.usuario, self._ahora = entorno, usuario, ahora

    def _lineas(self) -> list[dict]:
        """Cada línea no vacía, parseada. Una línea rota para la lectura entera."""
        if not self.ruta.is_file():
            return []
        filas: list[dict] = []
        for numero, linea in enumerate(
                self.ruta.read_text(encoding="utf-8").splitlines(), start=1):
            if not linea.strip():
                continue
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError as exc:
                raise ExpedicionError(
                    f"{self.ruta}: la línea {numero} del registro de cosecha no es "
                    f"JSON válido ({exc}). No se ignora: puede ser el rastro de un "
                    "documento ya creado en el CRM. Revísala a mano."
                ) from exc
        return filas

    def _mias(self) -> list[dict]:
        """Las filas de ESTE entorno y ESTA cuenta, por igualdad exacta."""
        return [f for f in self._lineas()
                if f.get("entorno") == self.entorno and f.get("usuario") == self.usuario]

    def _escribir(self, fila: dict) -> None:
        with self.ruta.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")

    def reservar(self, id_envio: str, origen_id: str) -> None:
        """Anota, ANTES del `POST` que crea, que vamos a subir este certificado.

        Es el gancho que `sudespacho_documentos.subir_documento` llama por
        `al_reservar`. Si el `POST` sale y su respuesta se pierde, esta línea es lo
        único que permite reencontrar el documento por `origen_id`.
        """
        self._escribir({"clave": id_envio, "estado": "reservado",
                        "origen_id": origen_id, "entorno": self.entorno,
                        "usuario": self.usuario,
                        "timestamp": self._ahora().isoformat()})

    def cerrar(self, id_envio: str, *, doc_id: str, sha256: str) -> None:
        """Cierra la reserva con el `doc_id` y la huella de lo verificado."""
        if not any(f.get("clave") == id_envio and f.get("estado") == "reservado"
                   for f in self._mias()):
            raise ExpedicionError(
                f"cierre huérfano: se intenta cerrar la cosecha de {id_envio!r} sin "
                "reserva previa de este entorno y cuenta. El registro se escribe "
                "SIEMPRE antes de la llamada; un cierre sin reserva significa que "
                "algo escribió fuera de este camino.")
        self._escribir({"clave": id_envio, "estado": "hecho", "doc_id": doc_id,
                        "sha256": sha256, "entorno": self.entorno,
                        "usuario": self.usuario,
                        "timestamp": self._ahora().isoformat()})

    def hecho(self, id_envio: str) -> dict | None:
        """La fila de cierre de este envío, o `None`. Solo cuenta lo CERRADO."""
        for fila in reversed(self._mias()):
            if fila.get("clave") == id_envio and fila.get("estado") == "hecho":
                return fila
        return None

    def abiertas(self) -> list[dict]:
        """Reservas sin cerrar: hubo un intento y no se sabe cómo acabó.

        No se reintentan solas. `cosechar` las resuelve buscando por `origen_id` —que
        es inmediato— y, si tampoco así, para y lo declara: el mismo criterio que
        `RegistroIntencion.exigir_sin_pendientes` aplica a los envíos. Un desenlace
        desconocido pide humano, no reintento.
        """
        cerradas = {f["clave"] for f in self._mias() if f.get("estado") == "hecho"}
        return [f for f in self._mias()
                if f.get("estado") == "reservado" and f.get("clave") not in cerradas]


def ya_expedido(listado: list[dict], id_personalizado: str) -> set[str]:
    """`IdEnvio` que la plataforma ya tiene con ese identificador exacto."""
    return {e["id"] for e in listado if e.get("id_personalizado") == id_personalizado}


# ---------------------------------------------------------------------------
# F2 — la lectura: qué acredita cada envío
# ---------------------------------------------------------------------------

#: Las cinco familias en que cae un estado certificado. No son títulos de la
#: plataforma: son lo que cada estado significa PARA NOSOTROS, que es lo que el
#: motor necesita decidir.
EN_CURSO = "en_curso"          #: el envío progresa; nada acreditado todavía
RECEPCION = "recepcion"        #: recepción acreditada (art. 17.2, spec §6.2)
ACCESO = "acceso"              #: acceso al contenido íntegro (art. 10.2)
SIN_ENTREGA = "sin_entrega"    #: cerrado sin entrega (el 28 con valor afirmativo, §6.3)
DESCONOCIDO = "desconocido"    #: medido por nadie — se declara, nunca se asume

#: Códigos de la plataforma, por familia. Los nueve del spec §1.3 MÁS los seis
#: medidos en producción el 2026-09-21 (M-2 del plan de F2): 3, 8, 11, 12, 14 y 31,
#: que existen, aparecen en envíos reales y el spec no clasificaba.
_FAMILIA_DE: dict[int, str] = {
    # en curso — el envío se mueve, pero no hay hecho que acreditar
    3: EN_CURSO,    # Enviado a imprenta para su impresión (burofax)
    5: EN_CURSO,    # Procesado — «Procesado» NO es «Entregado» (spec §1.3)
    8: EN_CURSO,    # Pendiente de recogida (burofax)
    11: EN_CURSO,   # En tránsito a la ciudad de destino
    12: EN_CURSO,   # En reparto
    14: EN_CURSO,   # Recordatorio lectura ENVIADO (el 21 es el entregado)
    27: EN_CURSO,   # Entregado en el SERVIDOR: llegó al servidor, no al destinatario
    31: EN_CURSO,   # Incidencia — «se está gestionando»; acaba en 17/19 o en 42
    # recepción acreditada (spec §6.2: «Estado 17, 20 o 21 con su fecha»)
    17: RECEPCION,  # Entregado
    19: RECEPCION,  # Entregado con albarán — terminal del burofax
    21: RECEPCION,  # Recordatorio lectura entregado, sin acceso al contenido
    # acceso al contenido íntegro (art. 10.2)
    20: ACCESO,     # Leído · Documentación accedida
    # cerrado sin entrega
    28: SIN_ENTREGA,  # Rechazado — valor afirmativo, art. 7.4 y 395.1 LEC (§6.3)
    40: SIN_ENTREGA,  # Caducado
    42: SIN_ENTREGA,  # Fallido
}


def clasificar(codigo: int) -> str:
    """La familia de un código de estado. Lo no medido se declara DESCONOCIDO.

    No hay `EN_CURSO` por defecto, y esa es la decisión del diseño: un código que
    la plataforma añada mañana —o uno de los 37 documentados que aquí no están—
    caería en «aún en camino» y sería indistinguible de un envío que progresa. Si
    resultara ser un cierre nuevo, la expedición no terminaría nunca y nadie se
    enteraría. La regla de la casa es que «no lo sé» no es «no hay».
    """
    return _FAMILIA_DE.get(codigo, DESCONOCIDO)


@dataclass(frozen=True)
class EstadoCertificado:
    """Una entrada del histórico de `GET /envios/{id}/estados`.

    Forma medida el 2026-09-21: `{codigo, titulo, fecha, detalle}`, en orden
    cronológico ascendente. El `detalle` del 20 identifica a quien leyó y desde qué
    IP, lo que matiza el hallazgo API-01 de la R1 del spec («campos_verificacion
    vacío: Leído no identifica a nadie»): por esta vía sí identifica.
    """

    codigo: int
    titulo: str
    fecha: datetime
    detalle: str | None = None

    @property
    def familia(self) -> str:
        return clasificar(self.codigo)


def estado_de(crudo: dict) -> EstadoCertificado:
    """`EstadoCertificado` desde el JSON de la API, validando la forma.

    Exige zona horaria en la fecha. Un instante sin offset no se puede comparar con
    otro que sí lo tiene —Python lanza `TypeError` al restarlos— y asumir UTC sobre
    un servidor que responde en `+02:00` desplazaría dos horas todas las fechas de
    entrega. Con plazos de procedibilidad de por medio, se para.
    """
    codigo = crudo.get("codigo")
    if not isinstance(codigo, int) or isinstance(codigo, bool):
        raise ExpedicionError(
            f"estado sin `codigo` entero: {crudo.get('codigo')!r}. No se convierte "
            "en silencio: el codigo decide si un envío está entregado.")
    bruto = crudo.get("fecha")
    try:
        fecha = datetime.fromisoformat(str(bruto))
    except (TypeError, ValueError) as exc:
        raise ExpedicionError(f"estado {codigo}: fecha ilegible {bruto!r}") from exc
    if fecha.tzinfo is None:
        raise ExpedicionError(
            f"estado {codigo}: la fecha {bruto!r} no trae zona horaria (offset). No "
            "se asume UTC: el servidor responde en +02:00 y dos horas de desvío "
            "mueven un plazo de procedibilidad.")
    return EstadoCertificado(codigo=codigo, titulo=str(crudo.get("titulo") or ""),
                             fecha=fecha, detalle=crudo.get("detalle"))


#: `tipo` del listado -> canal nuestro. Medido el 2026-09-21 (M-7): la API usa una
#: letra y `tipo_titulo` la traduce ('b' -> "Burofax", 'c' -> "Entrega Electrónica
#: Certificada"). El canal interno NO distingue correo de SMS: los dos son 'c' para
#: la plataforma, y lo que los separa —`tipo_entrega`— es del envío, no de la
#: lectura. Quien necesite esa distinción la tiene en el registro de intención.
CANAL_DE_TIPO: dict[str, str] = {"b": "burofax", "c": "electronico"}

#: El estado en que cada canal culmina. Mientras no se alcance, el hecho acreditado
#: PUEDE MEJORAR y el certificado bajado hoy quedaría corto: el burofax pasa de 17
#: a 19 (medido: tres días después) y la entrega electrónica de 21 a 20.
_CULMINACION: dict[str, int] = {"burofax": 19, "electronico": 20}


@dataclass(frozen=True)
class EnvioObservado:
    """Un envío tal como la plataforma lo cuenta, con los hechos ya derivados.

    Los hechos se derivan del HISTÓRICO completo, nunca del estado del listado
    (M-1): el listado da el último evento, y el último no es ni el más temprano ni
    el más fuerte. Las dos cosas importan y son ejes distintos.
    """

    id_envio: str
    tipo: str
    asunto: str
    destinatario: str
    id_personalizado: str
    fecha_envio: datetime
    historico: tuple[EstadoCertificado, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "historico", tuple(self.historico))

    @property
    def canal(self) -> str:
        return CANAL_DE_TIPO.get(self.tipo, f"desconocido:{self.tipo}")

    def _primera(self, *familias: str) -> datetime | None:
        """La fecha MÁS TEMPRANA de las entradas de esas familias.

        `min`, no «la última»: el art. 17.2 cuenta desde la recepción, y la primera
        recepción acreditada es la que abre el plazo. Tomar la última desplazaría el
        mes del art. 17.4 — medido, tres días en el burofax 006catfpdv6 (M-1).
        """
        fechas = [e.fecha for e in self.historico if e.familia in familias]
        return min(fechas) if fechas else None

    @property
    def recibido_en(self) -> datetime | None:
        """Recepción acreditada (art. 17.2). El acceso también es recepción."""
        return self._primera(RECEPCION, ACCESO)

    @property
    def accedido_en(self) -> datetime | None:
        """Acceso al contenido íntegro (art. 10.2). Solo el 20."""
        return self._primera(ACCESO)

    @property
    def cerrado_en(self) -> datetime | None:
        """Cierre sin entrega. El 28 es un hecho con valor afirmativo, no un error."""
        return self._primera(SIN_ENTREGA)

    @property
    def desconocidos(self) -> tuple[int, ...]:
        """Códigos del histórico que nadie ha clasificado. Se declaran."""
        return tuple(sorted({e.codigo for e in self.historico
                             if e.familia == DESCONOCIDO}))

    @property
    def cosechable(self) -> bool:
        """¿El certificado de este envío ya es DEFINITIVO?

        Lo es cuando el envío alcanzó la culminación de su canal (19 el burofax, 20
        la entrega electrónica) o se cerró sin entrega (28/40/42). Antes no: un
        certificado bajado con el envío en 17 o en 21 acredita menos de lo que
        acabará acreditando, y como el nombre canónico del spec §7.1 no lleva el
        estado, el provisional ocuparía el sitio del bueno.

        Un código desconocido NO hace cosechable: no se sabe si culmina algo.
        """
        if self.desconocidos:
            return False
        codigos = {e.codigo for e in self.historico}
        if _CULMINACION.get(self.canal) in codigos:
            return True
        return any(clasificar(c) == SIN_ENTREGA for c in codigos)


@dataclass(frozen=True)
class Expedicion:
    """Los envíos de un `id_personalizado`, leídos de la plataforma.

    El nivel de expedición es **comodidad de informe y no tiene efecto jurídico**
    (spec §6.1): aquí no se calcula ninguna fecha agregada, justamente para que
    nadie la use. El nivel que manda es el requerido, y lo arma `por_requerido`.
    """

    id_personalizado: str
    entorno: str
    envios: tuple[EnvioObservado, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "envios", tuple(self.envios))

    @property
    def cosechables(self) -> tuple[EnvioObservado, ...]:
        return tuple(e for e in self.envios if e.cosechable)

    @property
    def pendientes(self) -> tuple[EnvioObservado, ...]:
        return tuple(e for e in self.envios if not e.cosechable)

    @property
    def completa(self) -> bool:
        """Todos los envíos culminaron.

        Con cero envíos es `False`: no hay nada que dar por completo, y devolver
        `True` sobre el vacío sería el mismo censo negativo que el spec §5.2
        prohíbe — «no encuentro envíos» no es «la expedición terminó».
        """
        return bool(self.envios) and not self.pendientes

    def por_requerido(self, partes: list[dict]) -> tuple[Requerido, ...]:
        """Agrupa los envíos por requerido, casando `destinatarios` con las partes.

        Es el nivel que manda para los plazos (§6.1): dos requeridos que reciben en
        fechas distintas tienen DOS relojes, y agregarlos en uno puede llevar a
        demandar a quien aún tiene vivo su mes del art. 17.4.

        **Lo que no casa va al cajón `SIN_CASAR` y se declara.** Atribuirlo a la
        primera parte inventaría un reloj sobre alguien a quien quizá no se le
        entregó nada; dejarlo fuera del resultado lo escondería. Pasa de verdad: el
        burofax lleva en `destinatarios` la razón social, que no tiene por qué
        coincidir con el nombre compuesto de la ficha del CRM.
        """
        grupos: dict[str, list[EnvioObservado]] = {}
        etiquetas: dict[str, str] = {}
        indice: dict[str, str] = {}
        for i, parte in enumerate(partes):
            clave = f"parte:{i}"
            etiquetas[clave] = nombre_completo_de(parte)
            grupos[clave] = []
            for contacto in _claves_de_contacto(parte):
                indice.setdefault(contacto, clave)
        for envio in self.envios:
            clave = indice.get(envio.destinatario.strip().lower(), SIN_CASAR)
            grupos.setdefault(clave, []).append(envio)
        etiquetas[SIN_CASAR] = "(sin casar)"
        return tuple(Requerido(clave=c, etiqueta=etiquetas.get(c, c), envios=tuple(v))
                     for c, v in grupos.items())


#: Clave del cajón de los envíos que no casan con ninguna parte del CRM.
SIN_CASAR = "__sin_casar__"

#: Días hacia atrás que se consultan cuando el registro local no sabe cuándo se
#: expidió. No es un número mágico con pretensiones: es holgura para que una
#: expedición vieja siga apareciendo, y `GET /envios` acotado por fecha cuesta una
#: o dos páginas (spec, hueco 6: 1.954 envíos históricos en la plaza más activa).
VENTANA_DIAS = 180


@dataclass(frozen=True)
class Requerido:
    """Un requerido con sus canales y sus dos fechas. El nivel que manda (§6.1)."""

    clave: str
    etiqueta: str
    envios: tuple[EnvioObservado, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "envios", tuple(self.envios))

    @property
    def recibido_en(self) -> datetime | None:
        """La más temprana entre sus canales: al requerido le basta cualquiera.

        Simétrico de la regla del spec §6.1: «un canal fallido no resta si otro del
        mismo requerido acreditó recepción».
        """
        fechas = [e.recibido_en for e in self.envios if e.recibido_en]
        return min(fechas) if fechas else None

    @property
    def accedido_en(self) -> datetime | None:
        fechas = [e.accedido_en for e in self.envios if e.accedido_en]
        return min(fechas) if fechas else None


def _claves_de_contacto(parte: dict) -> set[str]:
    """Con qué cadenas puede aparecer esta parte en `destinatarios` del listado.

    El listado devuelve `destinatarios` como UN STRING (M-7): el email en la entrega
    electrónica, el móvil en el SMS, la razón social en el burofax. Se normaliza todo
    a minúsculas; el móvil, además, con y sin el prefijo `34`, porque el destinatario
    SMS real de producción es `34645508869` (spec §1.1).
    """
    claves: set[str] = set()
    email = (parte.get("email") or "").strip().lower()
    if email:
        claves.add(email)
    movil = movil_normalizado(parte.get("movil"))
    if movil:
        desnudo = movil.removeprefix("34")
        claves.update({movil, desnudo, f"34{desnudo}"})
    nombre = nombre_completo_de(parte).strip().lower()
    if nombre:
        claves.add(nombre)
    return claves


def _fecha_exigida(bruto: Any, *, que: str) -> datetime:
    """Una fecha con zona, o `ExpedicionError`. Mismo criterio que `estado_de`."""
    try:
        f = datetime.fromisoformat(str(bruto))
    except (TypeError, ValueError) as exc:
        raise ExpedicionError(f"{que}: fecha ilegible {bruto!r}") from exc
    if f.tzinfo is None:
        raise ExpedicionError(f"{que}: la fecha {bruto!r} no trae zona horaria")
    return f


def refrescar(w_code: str, tipo: str, *, entorno_exp: EntornoExpedicion,
              ordinal: int = 1, ventana_dias: int = VENTANA_DIAS) -> Expedicion:
    """Relee en Codicert el estado de una expedición. No escribe nada.

    Dos decisiones que el spec fija y conviene no perder de vista al leer el código:

    1. **La consulta se acota siempre por fecha** (§4.3). Quien pagina `GET /envios`
       no ve los envíos del jurídico: ve los de la cuenta compartida de la plaza, por
       la que sale todo el bad debt. La ventana arranca en la anotación más antigua
       del registro de intención —que es nuestra y sabe cuándo se expidió— y solo
       cuando no hay registro cae en `ventana_dias`.
    2. **El filtro por `id_personalizado` es igualdad exacta.** La API no filtra por
       ese campo (spec §1.2), así que se filtra en casa; y no se intenta reconocer los
       identificadores que alguien tecleó a mano en el portal, que existen y no siguen
       la gramática del §3 (medido: `W-04A8PU`, `W-02XE7E/W-046HM4`). Adivinarlos
       mezclaría expediciones distintas, que es justo lo que el §3 existe para evitar.

    El histórico se pide envío a envío: el estado del listado es el último evento y no
    sirve ni para la fecha más temprana ni para el hecho más fuerte (medido, M-1 del
    plan de F2 — tres días de diferencia en un burofax real).
    """
    id_personalizado = componer_id(w_code, tipo, ordinal)
    registro = RegistroIntencion(entorno_exp.raiz / "_codicert_intencion.jsonl",
                                 entorno=entorno_exp.entorno,
                                 usuario=entorno_exp.usuario, ahora=entorno_exp.ahora)
    ahora = entorno_exp.ahora()
    candidatas = [ahora - timedelta(days=ventana_dias)]
    primera = registro.primera_anotacion_de(id_personalizado)
    if primera is not None:
        candidatas.append(primera)
    desde = min(candidatas)

    crudos = entorno_exp.codicert.listar(
        fecha_inicio=desde.date().isoformat(), fecha_fin=ahora.date().isoformat())
    envios: list[EnvioObservado] = []
    for crudo in crudos:
        if crudo.get("id_personalizado") != id_personalizado:
            continue
        id_envio = str(crudo.get("id") or "")
        if not id_envio:
            raise ExpedicionError(
                f"{id_personalizado}: el listado trae un envío sin `id` — {crudo!r}. "
                "Sin identificador no se puede leer su histórico ni cosechar su "
                "certificado: se para en vez de saltárselo en silencio.")
        envios.append(EnvioObservado(
            id_envio=id_envio, tipo=str(crudo.get("tipo") or ""),
            asunto=str(crudo.get("asunto") or ""),
            destinatario=str(crudo.get("destinatarios") or ""),
            id_personalizado=id_personalizado,
            fecha_envio=_fecha_exigida(crudo.get("fecha"), que=f"envío {id_envio}"),
            historico=tuple(estado_de(e)
                            for e in entorno_exp.codicert.estados(id_envio))))
    return Expedicion(id_personalizado=id_personalizado, entorno=entorno_exp.entorno,
                      envios=tuple(envios))


@dataclass(frozen=True)
class EntornoExpedicion:
    """Puerto único de inyección: transporte, CRM, reloj, raíz de escritura y entorno.

    Sin él no hay dónde enchufar un doble y los tests escribirían en el árbol real, que
    la regla de `CLAUDE.md` §Tests prohíbe sin escotilla. Todo lo no determinista de
    `planificar`/`ejecutar` entra por aquí.

    `plaza` y `entorno` describen DÓNDE y CONTRA QUÉ se ejecuta de verdad (la plaza
    resuelta y "sandbox"/"produccion"): `ejecutar` los contrasta contra los mismos
    campos del `Plan` y para si no coinciden, para que un plan leído como sandbox no
    pueda ejecutarse por error contra producción.

    `usuario` es el emisor YA resuelto por `entorno_real` (hallazgo 5 de la
    revisión adversarial del frontal, 2026-09-17): antes, el llamador (`main()`)
    volvía a invocar `codicert.credenciales(...)` con los mismos argumentos solo
    para enseñarlo en la cabecera del plan. Queda `None` por defecto porque los
    tests de este módulo nunca construyen `entorno_real` y no tienen un emisor
    real que exponer.
    """

    codicert: Any
    partes_de: Callable[[str], list[dict]]
    ahora: Callable[[], datetime]
    raiz: Path
    plaza: str
    entorno: str
    usuario: str | None = None

    # --- puertos que solo usa F2 (`cosechar`) --------------------------------
    # Los cuatro son `None` por defecto a propósito: los tests de F1 construyen
    # este dataclass con los siete campos de arriba y no deben cambiar. `cosechar`
    # exige los cuatro y para si falta alguno, en vez de caer en un default que
    # escribiría en el árbol real.
    #
    #: Carpeta donde se archiva el certificado íntegro, dada del w_code.
    #: `entorno_real` la resuelve contra el árbol del caso; los tests pasan un
    #: lambda a `tmp_path`, que es lo que hace cumplible la regla de `CLAUDE.md`
    #: §Tests sin escotilla.
    carpeta_certificados: Callable[[str], Path] | None = None
    #: Puerto del gestor documental del CRM (`core.sudespacho_documentos`).
    gestor: Any = None
    #: `w_code -> (element, exp_id)` del expediente CRM al que colgar el documento.
    exp_crm: Callable[[str], tuple[str, str]] | None = None
    #: Lector del emisor de un certificado PDF (`core.certificado_lectura`).
    leer_emisor: Callable[[bytes], Any] | None = None


@dataclass(frozen=True)
class Confirmacion:
    """Lo que el CLI construye a partir del plan leído por un humano.

    Un `bool` no distingue «alguien leyó» de «alguien puso `True`»; el digest sí,
    porque solo se puede producir a partir del plan concreto que se aprobó (spec §5.1).
    """

    digest: str


@dataclass(frozen=True)
class Plan:
    """El plan de una expedición: lo que un humano lee y aprueba antes de gastar.

    `usuario` es la cuenta emisora YA resuelta (hallazgo H-01, revisión
    adversarial r2): antes `Plan` ni siquiera la guardaba, así que cambiar el
    emisor resuelto entre planificar y ejecutar -- manteniendo plaza y entorno
    -- no invalidaba nada. `None` por defecto porque los tests de este módulo
    nunca construyen `entorno_real` y no tienen un emisor real que exponer
    (mismo criterio que `EntornoExpedicion.usuario`).
    """

    w_code: str
    tipo: str
    id_personalizado: str
    plaza: str
    entorno: str
    envios: tuple[EnvioPrevisto, ...]
    ausencias: tuple[str, ...]
    coste: Decimal
    credito: Decimal
    documentos: tuple[Path, ...]
    documentos_sha256: tuple[str, ...]
    asunto: str
    cuerpo: str
    usuario: str | None = None
    digest: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        """Congela las cuatro listas del plan en tuplas (hallazgo H-01).

        `frozen=True` impide `plan.envios = otra_cosa`, pero NO impide
        `plan.envios.append(...)` ni `plan.envios[0] = otra_cosa`: una lista
        sigue siendo mutable por dentro aunque el atributo que la referencia
        esté congelado. Una tupla no admite ninguna de las dos operaciones, así
        que esto es lo que de verdad inmoviliza `envios`, `ausencias`,
        `documentos` y `documentos_sha256` tras construir el plan. Se coacciona
        aquí -- con `object.__setattr__`, el único modo de asignar un atributo
        en un dataclass `frozen` -- para que `planificar()` y los tests puedan
        seguir pasando listas corrientes sin cambiar ninguna llamada.

        No congela `EnvioPrevisto.destinatario` (ver su propio docstring): ese
        mutable queda inerte porque `ejecutar` ya no lo consulta para mandar,
        no porque esté protegido estructuralmente.
        """
        object.__setattr__(self, "envios", tuple(self.envios))
        object.__setattr__(self, "ausencias", tuple(self.ausencias))
        object.__setattr__(self, "documentos", tuple(Path(d) for d in self.documentos))
        object.__setattr__(self, "documentos_sha256", tuple(self.documentos_sha256))

    @property
    def ejecutable(self) -> bool:
        """`False` si el crédito disponible al planificar no cubre el coste estimado."""
        return self.credito >= self.coste


def _digest_de(*, id_personalizado: str, plaza: str, entorno: str, usuario: str | None,
              asunto: str, cuerpo: str, coste: Decimal,
              envios: list[EnvioPrevisto] | tuple[EnvioPrevisto, ...],
              shas: list[str] | tuple[str, ...]) -> str:
    """Huella de TODO lo que autoriza el gasto (hallazgo H-01, revisión adversarial r2).

    Antes cubría expediente, tipo, plaza, entorno, documentos y destinatarios, y
    dejaba fuera el ORDINAL del identificador, el asunto, el cuerpo, el coste y la
    cuenta emisora. Cuatro vías de fallo medidas con esa huella incompleta:

    1. Dos planes iguales salvo el ordinal ("W-04AKM2 - REQ" y "W-04AKM2 - REQ 2")
       compartían digest: la confirmación de uno autorizaba el otro, vía pública
       `--ordinal`. `id_personalizado` los distingue porque ya los compone
       (`componer_id`) junto con w_code y tipo — cubrirlo cubre a los tres a la vez.
    2. Sustituir asunto/cuerpo con `dataclasses.replace` no invalidaba nada: no
       entraban en la huella.
    3. Poner el coste a un céntimo con `dataclasses.replace` permitía ejecutar con
       saldo insuficiente para el coste real: `ejecutar` comprobaba el crédito
       contra `plan.coste`, pero nada sellaba que ESE coste fuera el aprobado.
    4. Cambiar la cuenta emisora resuelta, manteniendo plaza y entorno, tampoco
       invalidaba la confirmación: nada la sellaba ni se comprobaba en ejecución.

    `ejecutar` recalcula esta huella con los valores propios del plan (que pudo
    mutarse con `dataclasses.replace` entre aprobar y ejecutar) MÁS los destinatarios
    y documentos leídos DE NUEVO — nunca los de `plan.envios`/`plan.documentos_sha256`
    — y la compara contra la `Confirmacion` que trae el humano, nunca contra
    `plan.digest`: ese campo también viaja en el `Plan` y `dataclasses.replace` lo
    copia tal cual si no se toca, así que confiar en él sería el mismo agujero con
    otro nombre.

    Ninguna contraseña entra aquí: `usuario` es el nombre de la cuenta emisora
    (el `.bd` del Market Center) que resuelve `entorno_real`, nunca la clave.
    """
    crudo = "|".join([
        id_personalizado, plaza, entorno, usuario or "", asunto, cuerpo, str(coste),
        *shas,
        *sorted(f"{e.canal}:{sorted(e.destinatario.items())}" for e in envios),
    ])
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()


def _leer_documentos(documentos: list[Path] | tuple[Path, ...]) -> list[bytes]:
    """Lee cada documento del plan AHORA, desde disco, UNA SOLA VEZ.

    `ejecutar` calcula la huella (`shas_ahora`) y construye los adjuntos a partir de
    ESTOS MISMOS bytes (hallazgo H-02, revisión adversarial r2): antes se leía aquí
    solo para hashear y, mucho más abajo —después de paginar el listado remoto, una
    ventana larga—, se releía la MISMA ruta para construir el adjunto. Un documento
    sobrescrito en esa ventana pasaba el hash validado contra el contenido viejo y
    salía con el nuevo. Ninguna ruta se vuelve a abrir después de esta función.

    Un documento que ya no existe se declara aquí con un mensaje claro, no con el
    `FileNotFoundError` crudo de leerlo al construir los adjuntos, varias líneas
    más abajo.

    `planificar` reutiliza esta misma función (antes leía por su cuenta, solo para
    hashear) para que el preflight de H-09 valide EXACTAMENTE los bytes que se
    hashean, sin una segunda lectura del disco.
    """
    contenidos: list[bytes] = []
    for d in documentos:
        ruta = Path(d)
        try:
            contenidos.append(ruta.read_bytes())
        except FileNotFoundError as exc:
            raise ExpedicionError(
                f"el documento {ruta} ya no existe en su ruta: no se puede comprobar que "
                "es el mismo que aprobó el humano. Vuelve a planificar."
            ) from exc
    return contenidos


def _paginas_pdf(datos: bytes, *, nombre: str) -> int:
    """Páginas de un PDF ya leído en memoria (hallazgo H-09, revisión adversarial
    r2). Lanza `ExpedicionError` si `datos` no es un PDF de verdad -- ni de
    cabecera (magic bytes) ni de contenido (`pypdf` no lo puede abrir) --, en vez de
    dejarlo pasar sin comprobar como hacía `planificar` antes de este hallazgo.

    La comprobación de cabecera es barata y da un mensaje claro para el caso más
    común (un `.txt` con la extensión cambiada, sin ninguna estructura de PDF). Un
    documento que SÍ empieza por `%PDF-` pero que `pypdf` no puede abrir -- corrupto,
    truncado -- tampoco dice de cuántas páginas o de qué tamaño real se trata: el
    presupuesto no puede estimarlo, así que se bloquea en vez de fingir que cabe
    ("declarar que no puede estimarlo", que pide el remedio del hallazgo).
    """
    if not datos.startswith(b"%PDF-"):
        raise ExpedicionError(
            f"{nombre} no es un PDF: no empieza por la cabecera %PDF- que exige "
            "Codicert (adjuntos solo PDF, spec §1.1). Se para en el plan, no en el "
            "422 del servidor."
        )
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(datos)).pages)
    except Exception as exc:
        raise ExpedicionError(
            f"{nombre}: no se puede abrir como PDF para contar sus páginas ni "
            f"validar su tamaño ({type(exc).__name__}: {exc}). El presupuesto no "
            "puede estimar un documento que no se puede leer; corrígelo antes de "
            "planificar."
        ) from exc


def _preflight_documentos(documentos: list[Path] | tuple[Path, ...], contenidos: list[bytes], *,
                          envios: list[EnvioPrevisto] | tuple[EnvioPrevisto, ...],
                          entorno: str) -> Decimal:
    """Valida los documentos contra los canales PREVISTOS y devuelve el sobrecoste
    por volumen que corresponde a CADA envío EEC (hallazgo H-09, revisión
    adversarial r2).

    Antes, `planificar` solo leía los ficheros para hashearlos: todos se
    etiquetaban como PDF sin comprobarlo, y no se validaba número, formato, tamaño
    ni páginas. Reproducido: once `.txt` con contenido "no es PDF" generaban un
    plan ejecutable y llegaban a los tres métodos de envío del doble; un fichero
    pequeño y otro de más de 7 MiB costaban exactamente lo mismo.

    Se acota a los canales que este plan de verdad usa -- un burofax-only no debe
    rechazarse por el límite de ficheros de la EEC, y viceversa --, pero el FORMATO
    (¿es un PDF de verdad?) se exige siempre, use el canal que use: un documento que
    no se puede leer no se puede mandar por ningún canal.
    """
    nombres = [Path(d).name for d in documentos]
    paginas = [_paginas_pdf(c, nombre=n) for c, n in zip(contenidos, nombres)]
    bytes_totales = sum(len(c) for c in contenidos)

    usa_burofax = any(e.canal == "burofax" for e in envios)
    usa_eec = any(e.canal in ("correo", "sms") for e in envios)

    if usa_burofax:
        if len(documentos) > MAX_FICHEROS_BUROFAX:
            raise ExpedicionError(
                f"el burofax admite como máximo {MAX_FICHEROS_BUROFAX} ficheros y "
                f"el plan lleva {len(documentos)}. Reduce los adjuntos antes de "
                "planificar.")
        total_paginas = sum(paginas)
        if total_paginas > MAX_PAGINAS_BUROFAX:
            raise ExpedicionError(
                f"el burofax admite como máximo {MAX_PAGINAS_BUROFAX} páginas en "
                f"total y los documentos suman {total_paginas}. Recorta o divide el "
                "envío antes de planificar.")

    sobrecoste_eec = Decimal("0")
    if usa_eec:
        if len(documentos) > MAX_FICHEROS_EEC:
            raise ExpedicionError(
                "la entrega electrónica certificada admite como máximo "
                f"{MAX_FICHEROS_EEC} ficheros (suelo seguro: la UI la limita a "
                f"{MAX_FICHEROS_EEC} aunque el contrato declare hasta 10) y el plan "
                f"lleva {len(documentos)}. Reduce los adjuntos antes de planificar.")
        if bytes_totales > MAX_BYTES_EEC:
            raise ExpedicionError(
                "la entrega electrónica certificada admite como máximo "
                f"{MAX_BYTES_EEC // _BYTES_POR_MB} MB en total y los documentos "
                f"suman {bytes_totales / _BYTES_POR_MB:.2f} MB. Reduce el tamaño "
                "antes de planificar.")
        incluidos_mb = _MB_INCLUIDOS_EEC.get(entorno, min(_MB_INCLUIDOS_EEC.values()))
        exceso = bytes_totales - incluidos_mb * _BYTES_POR_MB
        if exceso > 0:
            mb_extra = -(-exceso // _BYTES_POR_MB)  # división entera hacia arriba
            sobrecoste_eec = PRECIO_MB_ADICIONAL * mb_extra
    return sobrecoste_eec


def planificar(w_code: str, tipo: str, documentos: list[Path], *,
              entorno_exp: EntornoExpedicion, plaza: str, entorno: str = "sandbox",
              ordinal: int = 1) -> Plan:
    """Construye el plan de la expedición. **No envía nada.**"""
    envios, ausencias = destinatarios_de(entorno_exp.partes_de(w_code))
    contenidos = _leer_documentos(documentos)
    shas = [hashlib.sha256(c).hexdigest() for c in contenidos]
    # H-09 (medio, acotado; revisión adversarial r2): preflight de formato, límites
    # y presupuesto de bytes ANTES de que el plan se declare ejecutable -- un
    # rechazo descubierto aquí no cuesta nada; descubierto en el envío, deja la
    # expedición a medias.
    sobrecoste_eec = _preflight_documentos(documentos, contenidos, envios=envios, entorno=entorno)
    coste = coste_de(envios, sobrecoste_eec_por_envio=sobrecoste_eec)
    asunto, cuerpo = texto_de(w_code)
    id_personalizado = componer_id(w_code, tipo, ordinal)
    return Plan(w_code=w_code, tipo=tipo,
                id_personalizado=id_personalizado,
                plaza=plaza, entorno=entorno, envios=envios, ausencias=ausencias,
                coste=coste, credito=entorno_exp.codicert.credito(),
                documentos=[Path(d) for d in documentos], documentos_sha256=shas,
                asunto=asunto, cuerpo=cuerpo, usuario=entorno_exp.usuario,
                digest=_digest_de(id_personalizado=id_personalizado, plaza=plaza,
                                  entorno=entorno, usuario=entorno_exp.usuario,
                                  asunto=asunto, cuerpo=cuerpo, coste=coste,
                                  envios=envios, shas=shas))


#: Un `threading.Lock` por expedición (clave = `clave_mutex_expedicion`). Ver
#: `_candado_de`: protege DENTRO de este proceso, que es un hueco distinto del que
#: cierra el mutex de casos.
_CANDADOS_POR_EXPEDICION: dict[str, threading.Lock] = {}
#: Protege la creación de una entrada nueva en `_CANDADOS_POR_EXPEDICION`. No protege
#: la expedición en sí -- eso lo hace el `Lock` que guarda, una vez obtenido.
_CANDADO_DEL_REGISTRO = threading.Lock()


def clave_mutex_expedicion(plan: Plan) -> str:
    """Identidad de la exclusión de H-05 (revisión adversarial r2): cuenta + entorno + expedición.

    El recurso que hay que proteger no es un expediente -- el mutex de casos
    (`case_mutex`/`mutex_sesion`) protege el árbol de UNO -- sino la CUENTA de
    Codicert: dos expediciones con el mismo (usuario emisor, entorno,
    id_personalizado) no pueden admitirse ni ejecutarse a la vez, vengan de dos
    hilos del mismo proceso o de dos terminales distintos ("bastan dos terminales",
    dice el hallazgo -- no hace falta un actor malicioso).

    Se reutiliza la MISMA primitiva de exclusión entre procesos que protege los
    casos -- mismo lock nativo, misma reentrancia de `mutex_sesion` dentro de un
    proceso -- con una clave derivada por hash de esos tres campos, en la forma
    `^W-[A-Z0-9]{3,20}$` que exige `case_mutex._w_code_valido`. NO es un W-code
    real: no nombra ningún expediente del catálogo, y su longitud (18 caracteres
    tras `W-`, frente a los 6 habituales de un código real) evita cualquier
    colisión con uno -- vive en el mismo directorio de locks que los casos, pero
    ninguna clave sintética puede confundirse con una real.
    """
    crudo = "|".join([plan.usuario or "", plan.entorno, plan.id_personalizado])
    return "W-COD" + hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:15].upper()


def _candado_de(clave: str) -> threading.Lock:
    """El `threading.Lock` DE ESTE PROCESO para la expedición `clave`.

    No es el mutex de casos, y hace falta ADEMÁS de él (H-05, revisión adversarial
    r2, reproducido por el revisor con una barrera de dos hilos): `mutex_sesion.
    sostenido` protege entre PROCESOS, pero es deliberadamente REENTRANTE dentro de
    uno -- dos hilos del mismo proceso que pidan la misma sesión se UNEN a ella y
    corren a la vez (así tiene que ser: es lo que permite que la secuencia de V1 y
    las etapas que invoca no choquen contra su propio lease, ver el docstring de
    `mutex_sesion.sostenido`). Sin este candado, dos hilos de un mismo proceso que
    llamaran a `ejecutar` para la MISMA expedición pasarían los dos la comprobación
    de mutex entre procesos -- el proceso SÍ lo sostiene -- y reproducirían
    exactamente el hallazgo: los dos leen "sin pendientes", los dos ven el listado
    remoto vacío, los dos mandan. Este candado cierra ESE hueco; `_exigir_mutex_de_
    expedicion` cierra el de verdad entre procesos. Bloquear cada escritura del
    fichero por separado (`RegistroIntencion._escribir`) no basta: hace falta que
    el CHEQUEO Y EL ENVÍO enteros sean atómicos frente a otro ejecutor, y por eso
    `ejecutar` sostiene este candado durante todo su cuerpo, no solo al escribir.
    """
    with _CANDADO_DEL_REGISTRO:
        candado = _CANDADOS_POR_EXPEDICION.setdefault(clave, threading.Lock())
    return candado


def _exigir_mutex_de_expedicion(plan: Plan, *, clave: str) -> None:
    """`ejecutar` EXIGE el mutex entre procesos de esta expedición; nunca lo adquiere.

    Regla dura del proyecto: `core/` exige la exclusión y nunca la adquiere -- eso
    lo hace `scripts/` (guard permanente `tests/test_entrypoints_mutex.py::
    test_e5_ningun_modulo_de_core_adquiere_el_mutex`, que prohíbe llamar aquí a
    `sostenido`/`tomado`/`adquirir`). Esta función solo COMPRUEBA con
    `mutex_sesion.vigente` -- nunca `.sostenido()` -- que el proceso que llama ya
    sostiene la sesión de `clave`. `scripts/codicert.py` es quien la adquiere,
    envolviendo la llamada a `ejecutar` con `scripts/_mutex_cli.sostener`.

    `vigente()` puede lanzar `MutexPerdido` si la sesión se sostuvo y se perdió
    DURANTE la operación (lease vencido, reloj movido): eso NO se captura aquí a
    propósito, igual que en `core/casos/escritura.py` -- perder el mutex a mitad no
    es lo mismo que no haberlo tenido nunca, y degradarlo a "no lo tengo" ocultaría
    justo el escenario en que otro proceso pudo haber entrado mientras tanto.
    """
    from core.casos import mutex_sesion
    from core.casos.workspace_model import CaseRef

    if mutex_sesion.vigente(CaseRef(w_code=clave)) is None:
        raise ExpedicionError(
            f"ejecutar() exige el mutex de la expedición {plan.id_personalizado!r} "
            f"(entorno={plan.entorno!r}, usuario={plan.usuario!r}) sostenido ANTES "
            "de llamar: core/ nunca lo adquiere por su cuenta (H-05, revisión "
            "adversarial r2). En la CLI ya lo hace `scripts/codicert.py`; si llamas "
            "a ejecutar() desde otro sitio, envuélvelo con `mutex_sesion.sostenido("
            "CaseRef(w_code=clave_mutex_expedicion(plan)), ahora_fn=...)` antes de "
            "invocarlo."
        )


def ejecutar(plan: Plan, confirmacion: Confirmacion, *,
            entorno_exp: EntornoExpedicion) -> list[str]:
    """Ejecuta el plan aprobado.

    Antes de gastar: comprueba que el entorno de llamada —plaza, entorno y cuenta
    emisora— es el que produjo el plan; lee los documentos UNA sola vez y resuelve
    los destinatarios DE NUEVO contra el CRM; recalcula con eso el sello completo
    (identificador con su ordinal, textos, coste, cuenta emisora, destinatarios y
    huellas de documento — hallazgo H-01) y lo compara contra la `Confirmacion` que
    trae el humano; determina qué falta por mandar y solo entonces comprueba que
    el crédito EN VIVO cubre el coste RESIDUAL de lo pendiente -- nunca el coste
    del plan entero, que incluiría pagar otra vez lo ya cerrado (hallazgo H-08) --
    y que lo que la plataforma ya tenga lo explica el registro local. Reanuda
    completando lo que falte; nunca repite lo hecho (spec §5.1, §5.2).

    Lo que se manda es SIEMPRE la instantánea que acaba de revalidar dentro de ESTA
    llamada —`envios_ahora`, resuelto fresco contra el CRM, y los bytes que acaba de
    leer de cada documento—, nunca `plan.envios` ni una segunda lectura de disco: un
    `Plan` es `frozen`, pero eso no inmoviliza lo que cuelga de sus listas (H-01), y
    una ruta reabierta más tarde puede haber cambiado de contenido mientras dura
    `listar()` (H-02). Mandar solo lo que el sello acaba de certificar en esta misma
    llamada hace que mutar `plan.envios` después de aprobarlo, o sobrescribir un
    documento durante la consulta remota, no tengan ningún efecto sobre lo que sale.

    El registro local de cierres (`RegistroIntencion`) cuenta SIEMPRE al decidir qué
    falta, también si el listado remoto vuelve vacío (hallazgo H-03): un censo
    negativo no es evidencia de que no se mandó nada. Y cuenta solo si es DE ESTE
    entorno y cuenta emisora, sobre el contenido de destinatario que acaba de
    resolverse DE NUEVO (hallazgo H-04): un cierre de otro entorno, de otra cuenta, o
    sobre un destinatario que ya cambió, no explica ni completa esta llamada. Si el
    registro tiene, para esta expedición, alguna anotación en formato antiguo (sin
    entorno/cuenta), el flujo se para y lo declara -- no se puede sostener de quién
    es esa anotación.

    **H-05 (alto, estructural; revisión adversarial r2):** comprobar los pendientes,
    consultar el listado remoto y reservar la intención eran, hasta este hallazgo,
    operaciones separadas y SIN exclusión entre ejecutores -- dos invocaciones
    simultáneas del mismo plan podían leer las dos "sin pendientes", ver las dos el
    listado remoto vacío, y anotar y mandar las dos: 2 envíos para 1 aprobado, sin
    ningún error, bastando dos terminales. Todo el cuerpo de esta función -- desde
    aquí hasta el envío -- corre ahora bajo `_candado_de(clave)` (exclusión DENTRO de
    este proceso) y exige `_exigir_mutex_de_expedicion` (exclusión ENTRE procesos,
    comprobada, nunca adquirida aquí): el estado se vuelve a comprobar DENTRO de esa
    doble exclusión, no fuera de ella.

    **H-07 (medio, estructural; revisión adversarial r2):** un rechazo DEFINITIVO
    del servidor (422, `CodicertDatosInvalidosError`) durante el envío se cierra con
    `registro.rechazar` -- nunca deja la anotación `en_vuelo` para siempre, que
    bloquearía cualquier reanudación futura sin que hubiera forma auditada de
    resolverla. Un desenlace DESCONOCIDO (timeout, error de transporte) no se
    captura: sigue `en_vuelo`, bloqueado hasta que un humano reconcilie mirando el
    portal. Ver el docstring de `RegistroIntencion.rechazar`.

    **H-15 (medio, acotado; revisión adversarial r2):** `RegistroIntencion` valida
    ahora, al leer, el esquema, el `estado` y la secuencia de transiciones de CADA
    clave (`_estados_por_clave`) -- comparte esa validación `en_vuelo`, `hechos`,
    `pares_cerrados`/`ids_hechos_de` (esta función, vía ellas) y la recuperación de
    H-07. Un estado que no se reconoce, o un cierre huérfano o duplicado, para la
    lectura entera con fichero y línea: nunca se consume como si cerrara una
    intención.
    """
    clave = clave_mutex_expedicion(plan)
    with _candado_de(clave):
        _exigir_mutex_de_expedicion(plan, clave=clave)
        return _ejecutar_bajo_candado(plan, confirmacion, entorno_exp=entorno_exp)


def _ejecutar_bajo_candado(plan: Plan, confirmacion: Confirmacion, *,
                           entorno_exp: EntornoExpedicion) -> list[str]:
    """El cuerpo de `ejecutar`, YA dentro de la doble exclusión de la expedición.

    Separado de `ejecutar` para que el candado y la comprobación del mutex no
    obliguen a reindentar el resto: nada de lo que sigue cambia de comportamiento,
    solo de a qué función pertenece.
    """
    if (entorno_exp.plaza != plan.plaza or entorno_exp.entorno != plan.entorno
            or entorno_exp.usuario != plan.usuario):
        raise ExpedicionError(
            f"el entorno de ejecución (plaza={entorno_exp.plaza!r}, "
            f"entorno={entorno_exp.entorno!r}, usuario={entorno_exp.usuario!r}) no "
            f"coincide con el que produjo el plan (plaza={plan.plaza!r}, "
            f"entorno={plan.entorno!r}, usuario={plan.usuario!r}): no se manda nada. "
            "Vuelve a planificar en el entorno correcto.")

    envios_ahora, _ = destinatarios_de(entorno_exp.partes_de(plan.w_code))
    contenidos = _leer_documentos(plan.documentos)
    shas_ahora = [hashlib.sha256(c).hexdigest() for c in contenidos]
    digest_ahora = _digest_de(
        id_personalizado=plan.id_personalizado, plaza=plan.plaza, entorno=plan.entorno,
        usuario=plan.usuario, asunto=plan.asunto, cuerpo=plan.cuerpo, coste=plan.coste,
        envios=envios_ahora, shas=shas_ahora)
    if digest_ahora != confirmacion.digest:
        raise ExpedicionError(
            "la confirmación no corresponde a lo que se va a mandar ahora mismo: el "
            "expediente ha cambiado desde que se aprobó el plan (destinatarios, "
            "domicilios, documento, identificador, cuenta emisora, texto o coste), o "
            "la confirmación es de otro plan. No se manda nada. Vuelve a planificar y "
            "revísalo.")

    registro = RegistroIntencion(entorno_exp.raiz / "_codicert_intencion.jsonl",
                                 entorno=entorno_exp.entorno, usuario=entorno_exp.usuario,
                                 ahora=entorno_exp.ahora)
    # Acotado a ESTA expedición: un pendiente de otro expediente no debe bloquearla. Y
    # es incondicional: una anotación en vuelo sin cerrar es, por definición, un envío
    # cuyo desenlace no se puede sostener sobre nada inmediato (spec §5.2) — jamás se
    # reintenta solo, así que bloquea aunque la plataforma no muestre nada todavía.
    # `registro` queda ligado a `entorno_exp.entorno`/`.usuario` (hallazgo H-04): una
    # anotación de otro entorno o de otra cuenta no pertenece a esta instancia.
    registro.exigir_sin_pendientes(plan.id_personalizado)

    ids_en_plataforma = ya_expedido(list(entorno_exp.codicert.listar()), plan.id_personalizado)
    # El censo positivo tampoco autoriza por sí solo a completar: solo si el
    # registro local explica CADA envío que la plataforma dice tener se puede
    # sostener qué falta. Si no, para y declara SIN VERIFICAR — pudo expedirse
    # desde otra máquina o desde el portal, y completar a ciegas duplicaría.
    sin_explicar = ids_en_plataforma - registro.ids_hechos_de(plan.id_personalizado)
    if sin_explicar:
        raise ExpedicionError(
            f"la plataforma tiene {len(sin_explicar)} envío(s) con "
            f"{plan.id_personalizado!r} que el registro local no explica (¿se "
            "expidió desde otra máquina o desde el portal?). Queda SIN VERIFICAR "
            "qué falta: no se manda nada. Compruébalo en el portal antes de "
            "continuar.")

    # H-03: los cierres locales cuentan SIEMPRE, también ante un censo remoto VACÍO.
    # Antes, `ids_en_plataforma` vacío tomaba la rama "pendientes = todos los envíos"
    # sin consultar `pares_cerrados` ni una sola vez: un listado que no refleja esta
    # expedición -- latencia, paginación, un fallo transitorio -- no es evidencia de
    # que no se mandó nada, y el registro local SÍ es un hecho inmediato. La huella
    # de cada par (canal, huella) sale del `destinatario` YA resuelto DE NUEVO
    # (hallazgo H-04): si el contenido aprobado cambió -- p. ej. el código postal --
    # la huella cambia con él y el envío vuelve a contar como pendiente.
    pares_hechos = registro.pares_cerrados(plan.id_personalizado)
    pendientes = [e for e in envios_ahora if (e.canal, _huella(e.destinatario)) not in pares_hechos]
    if not pendientes:
        raise ExpedicionError(
            f"la expedición {plan.id_personalizado!r} ya está completa en "
            f"entorno={plan.entorno!r}, usuario={plan.usuario!r}: sus "
            f"{len(pares_hechos)} envío(s) ya constan cerrados en el registro local "
            "-- cuentan aunque el listado remoto no los muestre. No hay nada "
            "pendiente que mandar.")

    # H-09 (medio, acotado; revisión adversarial r2): se revalida el preflight de
    # documentos AQUÍ también -- "antes del primer POST", que es lo que pide el
    # remedio del hallazgo --, no solo en `planificar`. `planificar` ya lo exige
    # para producir un Plan, así que en el camino normal esto es una repetición
    # sobre los MISMOS bytes (el digest de arriba ya certificó que no cambiaron) y
    # no rechaza nada nuevo; es la red que evita que un Plan construido por otra vía
    # -- sin pasar por `planificar` -- llegue a un envío real sin haberse validado.
    sobrecoste_eec = _preflight_documentos(
        plan.documentos, contenidos, envios=envios_ahora, entorno=entorno_exp.entorno)

    # H-08 (medio, acotado; revisión adversarial r2): el crédito se compara contra
    # el COSTE RESIDUAL -- lo que falta por mandar, `pendientes` -- nunca contra
    # `plan.coste`, que es el coste del plan ENTERO e incluye los envíos que ya se
    # cerraron y no se van a volver a pagar. Antes se comprobaba el crédito ANTES
    # de determinar los pendientes: reanudar cuando solo faltaba el canal más
    # barato exigía saldo para pagar OTRA VEZ el correo y el SMS ya enviados y
    # explicados -- un saldo vivo de exactamente 16,9716 € (lo que cuesta un
    # burofax suelto) se rechazaba porque el motor pedía 18,2348 € (los tres
    # canales), y volver a planificar no ayudaba: vuelve a presupuestar el total.
    coste_residual = coste_de(pendientes, sobrecoste_eec_por_envio=sobrecoste_eec)
    credito_ahora = entorno_exp.codicert.credito()
    if credito_ahora < coste_residual:
        coste_hecho = plan.coste - coste_residual
        raise ExpedicionError(
            f"crédito insuficiente para ejecutar: quedan {len(pendientes)} envío(s) "
            f"por mandar, que cuestan {coste_residual} € en total, y hay "
            f"{credito_ahora} € disponibles ahora (plan completo {plan.coste} €; ya "
            f"gastado {coste_hecho} €; al planificar había {plan.credito} €). No se "
            "manda nada.")

    # Los adjuntos salen de los MISMOS bytes que se acaban de leer y hashear arriba
    # (hallazgo H-02): ninguna ruta se reabre aquí, así que la ventana larga de
    # `listar()` -- justo encima -- no puede colar una sustitución entre "se
    # comprobó" y "se mandó". Misma forma que `core.codicert.adjunto`, que sí
    # releería del disco.
    adjuntos = [{"nombre": Path(d).name, "datos": base64.b64encode(c).decode("ascii"),
                "mime": "application/pdf"}
               for d, c in zip(plan.documentos, contenidos)]
    asunto, cuerpo = plan.asunto, plan.cuerpo   # ya sellados en el digest de arriba

    ids: list[str] = []
    for e in pendientes:
        # `e.destinatario`, no `e.etiqueta` (hallazgo H-04): la huella tiene que
        # ligarse al contenido aprobado -- lo que de verdad viaja en el envío --,
        # no a una etiqueta pensada solo para que la lea un humano en el plan.
        clave = registro.anotar(plan.id_personalizado, e.canal, e.destinatario)
        try:
            if e.canal == "burofax":
                i = entorno_exp.codicert.enviar_burofax(
                    destinatario=e.destinatario, adjuntos=adjuntos, asunto=asunto, cuerpo=cuerpo,
                    id_personalizado=plan.id_personalizado)
            else:
                i = entorno_exp.codicert.enviar_eec(
                    destinatarios=[e.destinatario], adjuntos=adjuntos, asunto=asunto, cuerpo=cuerpo,
                    tipo_entrega="correo" if e.canal == "correo" else "sms",
                    id_personalizado=plan.id_personalizado)
        except _cod.CodicertDatosInvalidosError as exc:
            # H-07 (medio, estructural; revisión adversarial r2): un 422 es un
            # RECHAZO DEFINITIVO -- sabemos, con certeza, que ESTE envío concreto
            # no salió --, a diferencia de un timeout o cualquier otro error de
            # transporte, donde pudo salir. Se cierra con su propia transición
            # (`rechazar`, nunca `cerrar`): no se inventa un `IdEnvio` que no
            # existe, y no se deja `en_vuelo` -- eso bloquearía CUALQUIER
            # reanudación futura de esta expedición para siempre, aunque el humano
            # comprobara en el portal que este envío concreto no existe. `motivo`
            # es diagnóstico fijo, derivado del TIPO de excepción -- nunca el texto
            # del servidor, que podría (aunque no se ha observado) reflejar un dato
            # del payload rechazado y violar la prohibición de PII en el registro.
            #
            # El resto de `pendientes` de ESTA llamada NO se intenta: se para
            # aquí, igual que antes de este arreglo -- lo único que cambia es que
            # la reanudación deja de estar bloqueada para siempre. Un desenlace
            # DESCONOCIDO (timeout, error de transporte) no se captura aquí a
            # propósito: sigue `en_vuelo`, bloqueado hasta que un humano
            # reconcilie mirando el portal; no se propone reintentarlo solo.
            registro.rechazar(clave, motivo=f"{type(exc).__name__} (422): rechazo del servidor")
            raise ExpedicionError(
                f"Codicert rechazó el envío por {e.canal} de {plan.id_personalizado!r} "
                f"(422, rechazo definitivo): {exc}. Este envío concreto queda marcado "
                "como rechazado en el registro local, así que NO bloqueará una "
                "reanudación futura: corrige el dato que Codicert rechazó y vuelve a "
                "planificar y ejecutar. No se manda nada más en esta llamada."
            ) from exc
        registro.cerrar(clave, i)
        ids.append(i)
    return ids


_ELEMENT_EXTRAJUDICIAL = "extrajudiciales"


def partes_de(w_code: str) -> list[dict]:
    """Las partes contrarias del expediente, leídas del CRM.

    Resuelve primero el ``case_id`` CANÓNICO del ``w_code`` desnudo con
    ``case_locator.resolve_ref`` —igual que hace ``scripts/crm_ficha.py::main``
    antes de tocar el índice—. Sin este paso, TODA invocación con la sintaxis que
    este módulo documenta (``codicert plan W-04AKM2 ...``) fallaba: las carpetas
    reales se llaman por su nombre canónico completo (p. ej. "BaRS11 - Falsa 1
    (W-000AAA) - Vuelta"), nunca por el W-code a secas, y
    ``case_manager.get_case_status`` busca la carpeta por NOMBRE EXACTO. Un caso
    perfectamente indexado, con su expediente extrajudicial registrado, se
    reportaba como "no encontrado" (hallazgo 1 CRÍTICO, revisión adversarial del
    frontal, 2026-09-17).

    Distingue además dos causas de fallo, cada una con remedio distinto (hallazgo
    3, misma revisión): que el caso no esté indexado en el catálogo local (falta
    checkout, o el W-code está mal escrito), o que SÍ lo esté pero no tenga
    expediente ``extrajudiciales`` registrado en su ``_caso.md`` (falta darlo de
    alta en el CRM). Confundirlas —el código de antes las lanzaba con el mismo
    mensaje— deja al operador sin saber qué comando ejecutar.

    Lee el ``exp_id`` numérico del elemento CRM ``extrajudiciales`` por el índice
    local del caso, y sus relaciones con `sudespacho_relations.get_relaciones`.
    `clientes_contrarios` ya trae los campos que `destinatarios_de` necesita (spec
    §5): nombre, 1apellido, 2apellido, dirección, población, provincia, cp, email,
    móvil. El nombre y los apellidos llegan SEPARADOS (hallazgo H-06, revisión
    adversarial r2) -- `nombre_completo_de` los compone antes de usarlos.
    """
    from core import case_manager
    from core.casos import case_locator

    resuelto = case_locator.resolve_ref(w_code)
    estado = case_manager.get_case_status(resuelto)
    if not estado["local_exists"]:
        raise ExpedicionError(
            f"{w_code}: el caso no está indexado en el catálogo local (resuelto a "
            f"{resuelto!r}, no encontrado en CASOS_ROOT). Puede que el W-code esté "
            "mal escrito o que falte hacerle un checkout. No se puede resolver a "
            "quién notificar."
        )

    exp_id = next(
        (
            str(elemento.get("id"))
            for elemento in estado["expedientes"]
            if isinstance(elemento, dict) and elemento.get("element") == _ELEMENT_EXTRAJUDICIAL
        ),
        None,
    )
    if exp_id is None:
        raise ExpedicionError(
            f"{resuelto}: el caso está indexado pero no tiene expediente "
            "'extrajudiciales' registrado en su _caso.md. Date de alta en el CRM "
            f"primero: python -m scripts.crm_ficha --case-id {w_code}. No se puede "
            "resolver a quién notificar."
        )

    from core import sudespacho_relations
    relaciones = sudespacho_relations.get_relaciones(_ELEMENT_EXTRAJUDICIAL, exp_id)
    return relaciones.get("clientes_contrarios", [])


def entorno_real(*, plaza: str, entorno: str) -> EntornoExpedicion:
    """Montaje de producción del puerto. Los tests de este módulo NUNCA lo usan.

    Resuelve credenciales, pide la `Ficha` UNA sola vez y envuelve el transporte
    con la superficie reducida que `ejecutar` consume (`credito()`, `listar()`,
    `enviar_burofax(**kw)`, `enviar_eec(**kw)`), sin exponer la `Ficha` misma.
    Rellena también `plaza`, `entorno` y `usuario` —el emisor YA resuelto (hallazgo
    5): antes, `main()` volvía a llamar `codicert.credenciales(...)` con los mismos
    argumentos solo para tener qué enseñar en la cabecera del plan, cuando esta
    función ya lo había resuelto para montar el transporte—, que `ejecutar`
    contrasta `plaza`/`entorno` contra el plan para no ejecutar en un entorno
    distinto del que se planificó.

    En sandbox se usa la credencial del sandbox (`plaza=None` en `credenciales`);
    en producción, la de la plaza.

    Vive aquí y no en `scripts/codicert.py` (hallazgo 4): es lógica de dominio
    —cómo resolver un expediente del CRM desde un W-code y qué hacer si falta, no
    cómo parsear los argumentos de una orden— y la arquitectura de 3 capas del
    proyecto dice que la lógica vive en el core; la UI (el CLI) solo orquesta.
    """
    usuario, clave = _cod.credenciales(None if entorno == "sandbox" else plaza, entorno=entorno)
    ficha = _cod.acceso(usuario, clave, entorno=entorno)

    class _Transporte:
        """Superficie mínima que `ejecutar` consume. No expone la `Ficha`."""

        def credito(self) -> Decimal:
            return _cod.credito(ficha, entorno=entorno)

        def listar(self, **filtros: Any) -> list[dict]:
            return list(_cod.listar(ficha, entorno=entorno, **filtros))

        def enviar_burofax(self, **kw: Any) -> str:
            return _cod.enviar_burofax(ficha, entorno=entorno, **kw)

        def enviar_eec(self, **kw: Any) -> str:
            return _cod.enviar_eec(ficha, entorno=entorno, **kw)

    return EntornoExpedicion(
        codicert=_Transporte(),
        partes_de=partes_de,
        ahora=lambda: datetime.now(timezone.utc),
        raiz=Path.cwd(),
        plaza=plaza,
        entorno=entorno,
        usuario=usuario,
        carpeta_certificados=_carpeta_certificados,
        gestor=_GestorDocumental(),
        exp_crm=_exp_crm_de,
        leer_emisor=_leer_emisor_de,
    )


# ---------------------------------------------------------------------------
# F2 — la cosecha: del envío a la prueba archivada
# ---------------------------------------------------------------------------

#: Caracteres que Windows no admite en un nombre de fichero. El asunto viene del
#: CRM y puede traerlos: medido, hay identificadores de producción con `/` dentro
#: (`W-02XE7E/W-046HM4`), y una barra sin sanear convierte el nombre en una ruta.
_PROHIBIDOS_EN_NOMBRE = '<>:"/\\|?*'


def nombre_canonico(asunto: str, w_code: str, id_envio: str) -> str:
    """`<ASUNTO> - <REF>-<codigo>.pdf`, la convención del despacho (spec §7.1).

    Medida sobre el certificado del W-04A6LI:
    `RESPUESTA REQUERIMIENTO - W-04A6LI-006casm113n.pdf`. `REF` es el W-code, no el
    `id_personalizado` completo: el asunto ya suele llevar el tipo dentro.

    Un asunto vacío no produce ` - W-...pdf`: cae en `CERTIFICADO`. Un nombre que
    empieza por separador es difícil de teclear y de leer en una lista.
    """
    limpio = "".join(" " if c in _PROHIBIDOS_EN_NOMBRE else c for c in asunto)
    limpio = " ".join(limpio.split()).strip(". ") or "CERTIFICADO"
    return f"{limpio} - {w_code}-{id_envio}.pdf"


@dataclass(frozen=True)
class CertificadoCosechado:
    """Un certificado ya archivado y colgado del expediente en el CRM."""

    id_envio: str
    ruta_local: Path
    sha256: str
    doc_id: str
    razon_social_emisor: str
    usuario_emisor: str | None = None
    ya_estaba: bool = False


def cosechar(w_code: str, tipo: str, *, entorno_exp: EntornoExpedicion,
             ordinal: int = 1, emisor_esperado: str | None = None,
             verificar_plaza: bool = True) -> list[CertificadoCosechado]:
    """Baja el certificado de cada envío culminado, lo verifica, lo archiva y lo sube.

    El orden importa y es el único seguro: **verificar el emisor ANTES de escribir
    nada**. Un certificado que no firmó nuestro emisor no es nuestra prueba (art.
    17.2) y no tiene por qué entrar ni en el expediente ni en el CRM.

    **Solo se cosecha lo culminado** (`EnvioObservado.cosechable`). Un envío en 17 o
    en 21 todavía puede mejorar, y como el nombre canónico del spec §7.1 no lleva el
    estado, el certificado provisional ocuparía el sitio del definitivo. Lo pendiente
    no es un error: se queda fuera de la lista y el frontal lo enseña aparte.

    **La idempotencia se sostiene sobre el registro local**, que es nuestro y no tiene
    latencia — nunca sobre un censo del gestor documental, cuya latencia ya duplicó un
    certificado (`INTEGRACION_SUDESPACHO.md` §17.4). Una reserva abierta (hubo intento
    y no se sabe cómo acabó) se resuelve buscando por `origen_id`, que es inmediato; si
    tampoco así se puede sostener, **se para y se declara SIN VERIFICAR**, nunca se
    reintenta a ciegas.
    """
    for nombre, valor in (("carpeta_certificados", entorno_exp.carpeta_certificados),
                          ("gestor", entorno_exp.gestor),
                          ("exp_crm", entorno_exp.exp_crm),
                          ("leer_emisor", entorno_exp.leer_emisor)):
        if valor is None:
            raise ExpedicionError(
                f"el entorno no trae `{nombre}`: `cosechar` escribe en el expediente "
                "y en el CRM, y sin ese puerto no hay dónde. Usa `entorno_real`.")
    esperado = emisor_esperado or EMISOR_ESPERADO
    expedicion = refrescar(w_code, tipo, entorno_exp=entorno_exp, ordinal=ordinal)
    registro = RegistroCosecha(entorno_exp.raiz / "_codicert_cosecha.jsonl",
                               entorno=entorno_exp.entorno, usuario=entorno_exp.usuario,
                               ahora=entorno_exp.ahora)
    element, exp_id = entorno_exp.exp_crm(w_code)
    carpeta = Path(entorno_exp.carpeta_certificados(w_code))
    cosechados: list[CertificadoCosechado] = []

    for envio in expedicion.cosechables:
        destino = carpeta / nombre_canonico(envio.asunto, w_code, envio.id_envio)
        hecho = registro.hecho(envio.id_envio)

        if hecho is None:
            abierta = next((a for a in registro.abiertas()
                            if a.get("clave") == envio.id_envio), None)
            if abierta is not None:
                # Hubo un intento cuyo desenlace no consta. Se resuelve por
                # `origen_id`, que es inmediato (§17.4); si el documento no
                # aparece, NO se reintenta: queda sin verificar y lo mira un humano.
                doc_id = entorno_exp.gestor.buscar_por_origen_id(
                    abierta["origen_id"], element=element, exp_id=exp_id)
                if doc_id is None:
                    raise ExpedicionError(
                        f"{envio.id_envio}: hay una cosecha reservada el "
                        f"{abierta.get('timestamp')} (origen_id "
                        f"{abierta['origen_id']!r}) que no consta cerrada, y el "
                        "documento tampoco aparece en el CRM por ese origen_id. "
                        "Queda SIN VERIFICAR si la subida salió: compruébalo a mano "
                        "antes de reintentar. No se sube nada.")
                registro.cerrar(envio.id_envio, doc_id=doc_id, sha256="")
                hecho = registro.hecho(envio.id_envio)

        if hecho is not None:
            cosechados.append(CertificadoCosechado(
                id_envio=envio.id_envio, ruta_local=destino,
                sha256=hecho.get("sha256") or "", doc_id=str(hecho.get("doc_id") or ""),
                razon_social_emisor=esperado, usuario_emisor=None, ya_estaba=True))
            continue

        pdf = entorno_exp.codicert.certificado(envio.id_envio)
        emisor = entorno_exp.leer_emisor(pdf)
        plaza = entorno_exp.usuario if verificar_plaza else None
        if not _emisor_coincide(emisor, razon_social=esperado, usuario=plaza):
            raise ExpedicionError(
                f"{envio.id_envio}: el certificado declara como emisor "
                f"{emisor.razon_social!r} (usuario {emisor.usuario!r}) y se esperaba "
                f"{esperado!r} (usuario {plaza!r}). El art. 17.2 exige constancia de "
                "la identidad del oferente: no se archiva ni se sube un certificado "
                "que no acredita al nuestro.")

        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(pdf)
        subido = entorno_exp.gestor.subir(
            pdf, nombrefinal=destino.name, mime="application/pdf",
            related=f"{element}:{exp_id}:left",
            al_reservar=lambda oid, _id=envio.id_envio: registro.reservar(_id, oid))
        registro.cerrar(envio.id_envio, doc_id=subido.doc_id, sha256=subido.sha256)
        cosechados.append(CertificadoCosechado(
            id_envio=envio.id_envio, ruta_local=destino, sha256=subido.sha256,
            doc_id=subido.doc_id, razon_social_emisor=emisor.razon_social,
            usuario_emisor=emisor.usuario))
    return cosechados


def _emisor_coincide(emisor: Any, *, razon_social: str, usuario: str | None) -> bool:
    from core.certificado_lectura import es_emisor_esperado

    return es_emisor_esperado(emisor, razon_social=razon_social, usuario=usuario)


def _carpeta_certificados(w_code: str) -> Path:
    """`<caso>/04_Output predemanda/Certificados`.

    El certificado de un requerimiento o una OVC **es** output predemanda: no es
    material que entra (eso es `00_Input` y la sala de lectura) ni work-product de
    un litigio en curso (`05_Procedimiento`). Decisión del plan de F2, no del spec,
    que no dice dónde se archiva en local.
    """
    from core.casos import case_locator

    return (case_locator.localizar(case_locator.resolve_ref(w_code))
            / "04_Output predemanda" / "Certificados")


def _exp_crm_de(w_code: str) -> tuple[str, str]:
    """`(element, exp_id)` del expediente extrajudicial al que colgar el documento."""
    from core import case_manager
    from core.casos import case_locator

    estado = case_manager.get_case_status(case_locator.resolve_ref(w_code))
    exp_id = next((str(e.get("id")) for e in estado["expedientes"]
                   if isinstance(e, dict)
                   and e.get("element") == _ELEMENT_EXTRAJUDICIAL), None)
    if exp_id is None:
        raise ExpedicionError(
            f"{w_code}: sin expediente 'extrajudiciales' en su _caso.md; no hay de "
            "qué colgar el certificado en el CRM. Date de alta primero: "
            f"python -m scripts.crm_ficha --case-id {w_code}")
    return _ELEMENT_EXTRAJUDICIAL, exp_id


class _GestorDocumental:
    """Puerto del gestor documental. Los tests inyectan un doble en su lugar."""

    def subir(self, contenido: bytes, **kw: Any) -> Any:
        from core import sudespacho_documentos

        return sudespacho_documentos.subir_documento(contenido, **kw)

    def buscar_por_origen_id(self, origen_id: str, **kw: Any) -> str | None:
        from core import sudespacho_documentos

        return sudespacho_documentos.buscar_por_origen_id(origen_id, **kw)


def _leer_emisor_de(pdf: bytes) -> Any:
    from core import certificado_lectura

    return certificado_lectura.leer_emisor(pdf)


#: Reexportados para que quien use `cosechar` no tenga que importar dos módulos más
#: solo para tipar un doble. Son alias, no copias.
from core.certificado_lectura import (  # noqa: E402
    EMISOR_ESPERADO,
    EmisorCertificado as EmisorLeido,
)
from core.sudespacho_documentos import DocumentoSubido as DocumentoEnCrm  # noqa: E402
