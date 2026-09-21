"""El criterio del despacho para expedir una comunicación certificada.

Spec: `docs/superpowers/specs/2026-09-17-envio-certificado-codicert-design.md`.
El transporte vive en `core/codicert.py` y no sabe qué es un expediente.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


def movil_normalizado(bruto: str | None) -> str | None:
    """`34` + nueve dígitos, o `None` si no es un móvil español.

    El prefijo se pega porque es lo que la plataforma registra: el destinatario SMS de
    producción es `34645508869`. Un fijo devuelve `None` y el canal se declara ausente.
    """
    if not bruto:
        return None
    m = _MOVIL.match(re.sub(r"[\s.\-()]", "", str(bruto)))
    return f"34{m.group(1)}" if m else None


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
    nombre = nombre_completo_de(parte)
    return {"nombre": nombre, "a_atencion": parte.get("a_atencion") or nombre,
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
    """
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
        # nombre YA conjunto, no la persona de contacto (regla del despacho: "nombre"
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
        `entorno`/`usuario` tampoco —es la cuenta propia del despacho, no la del
        destinatario—: los tres van en claro.
        """
        clave = uuid.uuid4().hex
        huella = _huella(contenido)
        marca = self._ahora().isoformat()
        self._escribir({"clave": clave, "id_personalizado": id_personalizado, "canal": canal,
                        "destinatario_huella": huella, "entorno": self.entorno,
                        "usuario": self.usuario, "timestamp": marca, "estado": "en_vuelo"})
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
        """Anotaciones sin cerrar de ESTE entorno/cuenta. Con `id_personalizado`, solo
        las de esa expedición (hallazgo H-04: una anotación de otro entorno u otra
        cuenta no pertenece a esta instancia, así que no cuenta ni bloquea aquí)."""
        abiertas: dict[str, dict] = {}
        for fila in self._lineas():
            if fila.get("estado") == "en_vuelo":
                abiertas[fila["clave"]] = fila
            else:
                abiertas.pop(fila["clave"], None)
        filas = [f for f in abiertas.values() if self._coincide_entorno(f)]
        if id_personalizado is None:
            return filas
        return [f for f in filas if f.get("id_personalizado") == id_personalizado]

    def hechos(self) -> set[str]:
        return {f["id_envio"] for f in self._lineas() if f.get("estado") == "hecho"}

    def _anotaciones_de(self, id_personalizado: str) -> list[dict]:
        """Filas 'en_vuelo' -- origen, sigan abiertas o ya cerradas -- de esta
        expedición, SIN filtrar por entorno/cuenta: es la base para detectar formato
        antiguo (hallazgo H-04) antes de decidir si una anotación cuenta o no."""
        return [f for f in self._lineas()
               if f.get("estado") == "en_vuelo" and f.get("id_personalizado") == id_personalizado]

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
        cerraron, con su `id_envio` añadido.

        La línea "hecho" solo lleva `clave` e `id_envio` (spec §4.3): no dice de qué
        expedición era, por qué canal, ni de qué entorno/cuenta. Se cruza con la
        anotación "en_vuelo" que la abrió —única por `clave`, la genera `uuid4()`—
        para recuperar `id_personalizado`, `canal`, `destinatario_huella`, `entorno`
        y `usuario`. El cruce exige además que esa anotación de origen sea de ESTE
        entorno/cuenta (hallazgo H-04): un cierre de sandbox no debe explicar ni
        completar una expedición de producción, aunque compartan `id_personalizado`
        -- el mismo w_code puede expedirse en los dos.
        """
        filas = self._lineas()
        anotaciones = {f["clave"]: f for f in filas
                       if f.get("estado") == "en_vuelo" and self._coincide_entorno(f)}
        salida: list[dict] = []
        for f in filas:
            if f.get("estado") != "hecho":
                continue
            origen = anotaciones.get(f["clave"])
            if origen is not None and origen.get("id_personalizado") == id_personalizado:
                salida.append({**origen, "id_envio": f["id_envio"]})
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


def ya_expedido(listado: list[dict], id_personalizado: str) -> set[str]:
    """`IdEnvio` que la plataforma ya tiene con ese identificador exacto."""
    return {e["id"] for e in listado if e.get("id_personalizado") == id_personalizado}


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


def planificar(w_code: str, tipo: str, documentos: list[Path], *,
              entorno_exp: EntornoExpedicion, plaza: str, entorno: str = "sandbox",
              ordinal: int = 1) -> Plan:
    """Construye el plan de la expedición. **No envía nada.**"""
    envios, ausencias = destinatarios_de(entorno_exp.partes_de(w_code))
    shas = [hashlib.sha256(Path(d).read_bytes()).hexdigest() for d in documentos]
    coste = coste_de(envios)
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


def ejecutar(plan: Plan, confirmacion: Confirmacion, *,
            entorno_exp: EntornoExpedicion) -> list[str]:
    """Ejecuta el plan aprobado.

    Antes de gastar: comprueba que el entorno de llamada —plaza, entorno y cuenta
    emisora— es el que produjo el plan; lee los documentos UNA sola vez y resuelve
    los destinatarios DE NUEVO contra el CRM; recalcula con eso el sello completo
    (identificador con su ordinal, textos, coste, cuenta emisora, destinatarios y
    huellas de documento — hallazgo H-01) y lo compara contra la `Confirmacion` que
    trae el humano; solo entonces comprueba que el crédito EN VIVO cubre el coste y
    que lo que la plataforma ya tenga lo explica el registro local. Reanuda
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

    credito_ahora = entorno_exp.codicert.credito()
    if credito_ahora < plan.coste:
        raise ExpedicionError(
            f"crédito insuficiente para ejecutar: {credito_ahora} € ahora para un coste "
            f"de {plan.coste} € (al planificar había {plan.credito} €). No se manda nada.")

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
        if e.canal == "burofax":
            i = entorno_exp.codicert.enviar_burofax(
                destinatario=e.destinatario, adjuntos=adjuntos, asunto=asunto, cuerpo=cuerpo,
                id_personalizado=plan.id_personalizado)
        else:
            i = entorno_exp.codicert.enviar_eec(
                destinatarios=[e.destinatario], adjuntos=adjuntos, asunto=asunto, cuerpo=cuerpo,
                tipo_entrega="correo" if e.canal == "correo" else "sms",
                id_personalizado=plan.id_personalizado)
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
    )
