"""Comprueba que los datos del `_ficha_crm.yaml` ESTAN en la documental del expediente.

Puro y sin red: recibe el corpus ya leido y devuelve un veredicto por dato. El IO —leer
la cobertura y los espejos MD— vive en `scripts/crm_ficha_validar.py`.

**Por que existe.** El `_ficha_crm.yaml` es la unica fuente de los datos personales que
FeesDefender escribe en el CRM del cliente, y **nada lo genera**: lo teclea a mano quien
prepara el caso. Un NIF con un digito cambiado lo acepta el CRM tal cual, y desde ese
momento la deduplicacion por NIF —la del PR #272— falla por la razon mas tonta: el dato
de partida es falso. Esto no arregla el tecleo; hace que un tecleo malo se vea.

**Los tres veredictos, y por que no bastan dos.** Medido sobre W-02Q38C: de 58 documentos
de la sala de maquina, los cinco con OCR vacio o pobre son **los DNI**, o sea justo donde
vive el NIF. Decir ahi «NIF no encontrado» seria mentir: la verdad es «no pude mirar donde
estaria». `SIN_COMPROBAR` no es un caso raro de manual, es el caso frecuente.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from core.crm_ficha import FichaCRMInput

ENCONTRADO = "ENCONTRADO"
NO_ENCONTRADO = "NO_ENCONTRADO"
SIN_COMPROBAR = "SIN_COMPROBAR"

#: Extensiones de ficheros de CONTROL del expediente. No son documental: ni se buscan en
#: ellos ni su ausencia de texto significa «no pude mirar». Y uno de ellos es el propio
#: `_ficha_crm.yaml`: incluirlo en el corpus haria que el validador se validara a si
#: mismo y devolviera «0 problemas» siempre.
_EXT_CONTROL = {".json", ".yaml", ".yml"}

#: Estados de `_cobertura.json` en los que el texto del documento NO es de fiar.
_ESTADOS_ILEGIBLES = {"low", "empty", "sin_soporte"}


@dataclass(frozen=True)
class Dato:
    """Un valor del YAML que debe poder rastrearse hasta un documento."""

    campo: str
    valor: str
    #: "documento" (NIF/NIE/CIF) | "email" | "telefono" | "texto"
    clase: str = "texto"

    @property
    def discriminante(self) -> bool:
        """Si encontrarlo prueba algo sobre ESTA parte, o podria ser de cualquiera.

        Medido sobre W-02Q38C: el apellido `MARTINEZ` aparece en diez lineas del
        expediente **y es el del comprador**, no el del contrario. `BARCELONA` como
        poblacion sale en 34 documentos. Encontrar un dato de una sola palabra no
        acredita nada: casa con cualquier tercero que lo comparta, y en un expediente
        inmobiliario hay muchos.

        Un NIF, un email o un telefono si identifican; un nombre COMPLETO tambien.
        """
        if self.clase != "texto":
            return True
        return len([p for p in re.split(r"[^0-9A-Za-z]+", self.valor) if p]) >= 2


@dataclass(frozen=True)
class Hallazgo:
    dato: Dato
    veredicto: str
    #: Documentos donde aparece. Solo con `ENCONTRADO`.
    documentos: tuple[str, ...] = ()
    #: Documentos que no se pudieron leer. Solo con `SIN_COMPROBAR`, y es lo que hace
    #: accionable el veredicto: dice DONDE habria que mirar a mano.
    ilegibles: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.veredicto == ENCONTRADO

    @property
    def acredita(self) -> bool:
        """Encontrado **y** con un valor que identifique a esta parte.

        Un `ENCONTRADO` sobre un dato no discriminante no se cuenta como verificado:
        contarlo infla el informe con aciertos que no lo son.
        """
        return self.ok and self.dato.discriminante


# ---------------------------------------------------------------------------
# Normalizacion: el documento y el YAML no escriben igual
# ---------------------------------------------------------------------------

def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _patron(valor: str, clase: str) -> re.Pattern[str] | None:
    """Expresion que reconoce `valor` tal y como puede aparecer en un documento.

    Se construye a partir de los caracteres significativos y se permite basura entre
    ellos —puntos, guiones, espacios— porque un NIF se escribe de cinco maneras y un
    telefono de otras tantas. **La tolerancia no llega a cambiar ningun caracter
    significativo**: un documento con el ultimo digito distinto no puede casar.
    """
    # leak-guard:allow — los NIF de este modulo y sus tests son sinteticos.
    valor = (valor or "").strip()
    if not valor:
        return None

    if clase == "documento":
        sig = [c for c in valor.upper() if c.isalnum()]
        if not sig:
            return None
        cuerpo = r"[\s.\-]*".join(re.escape(c) for c in sig)
        # Sin `\b` por delante: en los documentos aparece pegado a «NIF:» o «DNI».
        return re.compile(cuerpo + r"(?![A-Za-z0-9])", re.IGNORECASE)

    if clase == "telefono":
        digitos = [c for c in valor if c.isdigit()][-9:]
        if len(digitos) < 9:
            return None
        cuerpo = r"[\s.\-]*".join(re.escape(c) for c in digitos)
        return re.compile(r"(?<![0-9])" + cuerpo + r"(?![0-9])")

    if clase == "email":
        return re.compile(re.escape(valor.strip()), re.IGNORECASE)

    # texto: tildes, caja, espacios de mas **y puntuacion** son irrelevantes.
    #
    # Medido sobre W-02Q38C: la ficha dice `PASSEIG GARCIA FARIA 81, ATICO` y el correo
    # dice `Passeig García Faria 81 , ático` — con espacio ANTES de la coma. Partir por
    # espacios deja el token `81,` con la coma pegada, que no casa, y el validador
    # devolvia SIN_COMPROBAR sobre un dato que estaba a la vista en dos documentos.
    # **Un SIN_COMPROBAR falso es peor que inutil: entrena a ignorar el informe.**
    #
    # Se tokeniza por palabras alfanumericas y se une con «uno o mas caracteres no
    # alfanumericos», asi que la puntuacion y los saltos de linea dejan de importar. La
    # exigencia que queda —todas las palabras, en orden— es la que evita falsos
    # positivos.
    palabras = [p for p in re.split(r"[^0-9A-Za-z]+", _sin_tildes(valor)) if p]
    if not palabras:
        return None
    return re.compile(r"[^0-9A-Za-z]+".join(re.escape(p) for p in palabras), re.IGNORECASE)


def _texto_comparable(texto: str, clase: str) -> str:
    return _sin_tildes(texto) if clase == "texto" else texto


# ---------------------------------------------------------------------------
# Que datos se validan
# ---------------------------------------------------------------------------

def datos_de_ficha(ficha: FichaCRMInput) -> list[Dato]:
    """Los valores de la ficha que deben poder rastrearse a un documento.

    `notas_html` queda fuera **a proposito**: es narrativo redactado por el despacho, no
    un dato extraido del expediente. Validarlo daria un `NO_ENCONTRADO` permanente que
    entrenaria a ignorar el informe entero.
    """
    datos: list[Dato] = []

    c = ficha.contrario
    if c is not None:
        for campo, valor, clase in (
            ("nombre", c.nombre, "texto"),
            # `apellido1`/`apellido2` NO se validan sueltos: son una sola palabra y
            # casan con cualquier tercero del expediente. El apellido va cubierto por
            # `nombre`, que en la ficha lleva el nombre completo.
            ("nif", c.nif, "documento"),
            ("email", c.email, "email"),
            ("movil", c.movil, "telefono"),
            ("direccion", c.direccion, "texto"),
            ("poblacion", c.poblacion, "texto"),
        ):
            if (valor or "").strip():
                datos.append(Dato(f"contrario.{campo}", valor.strip(), clase))

    for i, col in enumerate(ficha.colaboradores):
        for campo, valor, clase in (
            ("nombre", col.nombre, "texto"),
            ("email", col.email, "email"),
            ("movil", col.movil, "telefono"),
            ("telefono", col.telefono, "telefono"),
            ("nif", col.nif, "documento"),
        ):
            if (valor or "").strip():
                datos.append(Dato(f"colaboradores[{i}].{campo}", valor.strip(), clase))

    return datos


# ---------------------------------------------------------------------------
# El corpus
# ---------------------------------------------------------------------------

def corpus_legible(entradas: Iterable[dict]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Parte el inventario de `_cobertura.json` en (slugs legibles, rutas ilegibles).

    Tres categorias, no dos, y la tercera es la que evita el defecto tonto:

    - **legible**: `estado == "ok"`. Su MD entra en el corpus.
    - **ilegible**: `low`, `empty` o `sin_soporte` sobre un documento de verdad. No se
      puede buscar en el, y su lista es lo que convierte un `NO_ENCONTRADO` en
      `SIN_COMPROBAR`.
    - **control**: `.json`/`.yaml` del propio expediente. Ni corpus ni ilegible: no son
      documental. Incluye **`_ficha_crm.yaml`**, y meterlo en el corpus haria que el
      validador se leyera a si mismo y aprobara cualquier dato.
    """
    legibles: list[str] = []
    ilegibles: list[str] = []

    for e in entradas:
        if not isinstance(e, dict):
            continue
        rel = str(e.get("rel_path") or "")
        slug = str(e.get("slug") or "")
        estado = str(e.get("estado") or "")

        punto = rel.rfind(".")
        if punto != -1 and rel[punto:].lower() in _EXT_CONTROL:
            continue

        if estado == "ok":
            if slug:
                legibles.append(slug)
        elif estado in _ESTADOS_ILEGIBLES and rel:
            ilegibles.append(rel)

    return tuple(legibles), tuple(ilegibles)


# ---------------------------------------------------------------------------
# La validacion
# ---------------------------------------------------------------------------

def validar(
    datos: Iterable[Dato],
    corpus: dict[str, str],
    *,
    ilegibles: tuple[str, ...] = (),
) -> list[Hallazgo]:
    """Un veredicto por dato. No escribe nada y no lee nada de disco.

    `corpus` es `{nombre_documento: texto}` — solo documentos LEGIBLES. `ilegibles` son
    los que no se pudieron leer; su presencia es lo que impide afirmar `NO_ENCONTRADO`.
    """
    salida: list[Hallazgo] = []

    for dato in datos:
        patron = _patron(dato.valor, dato.clase)
        if patron is None:
            # Un valor que no produce patron (vacio, o telefono de menos de 9 digitos)
            # no se puede buscar: no es ausencia.
            salida.append(Hallazgo(dato, SIN_COMPROBAR, ilegibles=ilegibles))
            continue

        donde = tuple(
            nombre for nombre, texto in corpus.items()
            if patron.search(_texto_comparable(texto or "", dato.clase))
        )
        if donde:
            salida.append(Hallazgo(dato, ENCONTRADO, documentos=donde))
        elif ilegibles:
            salida.append(Hallazgo(dato, SIN_COMPROBAR, ilegibles=ilegibles))
        else:
            salida.append(Hallazgo(dato, NO_ENCONTRADO))

    return salida


def resumen(hallazgos: Iterable[Hallazgo]) -> dict[str, int]:
    """Recuento por veredicto. Las tres claves salen siempre, aunque valgan 0.

    Que `NO_ENCONTRADO` y `SIN_COMPROBAR` aparezcan aunque sean cero es deliberado: un
    resumen que omite la categoria vacia se lee como si no existiera.
    """
    cuenta = {ENCONTRADO: 0, NO_ENCONTRADO: 0, SIN_COMPROBAR: 0, "no_discriminantes": 0}
    for h in hallazgos:
        cuenta[h.veredicto] = cuenta.get(h.veredicto, 0) + 1
        if h.ok and not h.dato.discriminante:
            cuenta["no_discriminantes"] += 1
    return cuenta
