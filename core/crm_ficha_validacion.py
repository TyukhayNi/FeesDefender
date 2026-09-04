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
#: El valor de la ficha no se puede buscar (vacio, o un telefono que no llega a 9
#: digitos). R1/H-11: antes salia como SIN_COMPROBAR y el informe decia «no se pudo
#: mirar en estos documentos» listando **ninguno**. No es un problema del corpus: es un
#: dato mal formado, y el remedio es otro.
NO_BUSCABLE = "NO_BUSCABLE"

#: Ficheros de CONTROL del expediente, **por su nombre**, no por su extension. No son
#: documental: ni se buscan en ellos ni su falta de texto significa «no pude mirar».
#:
#: Por que por nombre y no por extension (R1/H-02 y H-06): excluir todo `.json`/`.yaml`
#: dejaba fuera **documental real** —un export probatorio `evidencia.json`— y a la vez
#: **dejaba dentro `_caso.md`**, que es el indice administrativo del caso y contiene
#: contraparte y ciudad. Un nombre tecleado ahi se acreditaba a si mismo. La extension no
#: dice la naturaleza del fichero; el nombre de control, si.
_NOMBRES_CONTROL = frozenset({
    "_caso.md", "_ficha_crm.yaml", "_intake_log.jsonl", "_intake_hashes.json",
    "_exported_ids.json", "_resolved_links.json", "_ocurrencias_crm.json",
    "_inventory.json", "_manifiesto.yaml", "_apertura_v1.json", "_cobertura.json",
    "_cobertura.md", "_sala_maquina_state.json", "_registro.json", "_tiempos.jsonl",
})

#: Estados de `_cobertura.json` en los que el texto del documento NO es de fiar.
_ESTADOS_ILEGIBLES = {"low", "empty", "sin_soporte"}

#: El unico estado que autoriza a buscar en un documento. Cualquier otro —incluido uno
#: que este codigo no conozca— cuenta como ilegible: un estado desconocido no puede
#: silenciarse, porque desaparecer del recuento es justo lo que convierte un «no lo se»
#: en un «no hay».
_ESTADO_LEGIBLE = "ok"


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
        # Un documento de menos de cuatro caracteres significativos no identifica nada:
        # R1/H-03 midio que `Z` acreditaba contra `LOPEZ`. No es que no case: es que no
        # se puede buscar.
        if len(sig) < 4:
            return None
        cuerpo = r"[\s.\-]*".join(re.escape(c) for c in sig)
        # Limites por los DOS lados. Sin el izquierdo, un NIF casaba dentro de otro
        # identificador mas largo que lo contuviera como sufijo (R1/H-03). Los
        # separadores admitidos no cuentan como frontera, para que «NIF: nn.nnn.nnn-X»
        # siga casando.
        return re.compile(r"(?<![A-Za-z0-9])" + cuerpo + r"(?![A-Za-z0-9])",
                          re.IGNORECASE)

    if clase == "telefono":
        digitos = [c for c in valor if c.isdigit()]
        if len(digitos) < 9:
            return None
        # Se usan los nueve ULTIMOS, que es el numero nacional; el prefijo, si viene, es
        # opcional en el documento. R1/H-04: truncar a nueve sin mas hacia que
        # `+442079460958` casara con un numero espanol distinto, asi que si el valor
        # traia MAS de nueve digitos, los de delante se exigen tambien.
        nacional = digitos[-9:]
        prefijo = digitos[:-9]
        cuerpo = r"[\s.\-]*".join(re.escape(c) for c in nacional)
        if prefijo:
            cuerpo = (r"\+?[\s.\-]*"
                      + r"[\s.\-]*".join(re.escape(c) for c in prefijo)
                      + r"[\s.\-]*" + cuerpo)
            return re.compile(r"(?<![0-9])" + cuerpo + r"(?![0-9])")
        # Sin prefijo en el valor: el documento puede traerlo pegado (`+34600111222`),
        # asi que el limite izquierdo admite un prefijo internacional opcional en vez de
        # exigir que no haya digito ninguno (R1/H-04).
        return re.compile(r"(?:(?<![0-9])|(?<=\+34)|(?<=\+ 34))" + cuerpo
                          + r"(?![0-9])")

    if clase == "email":
        # Limites: una direccion casaba DENTRO de otra que la contuviera —un prefijo
        # de mas por delante y un TLD de mas por detras— y son buzones distintos
        # (R1/H-03).
        return re.compile(r"(?<![0-9A-Za-z_.+\-])" + re.escape(valor.strip())
                          + r"(?![0-9A-Za-z_.\-])", re.IGNORECASE)

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
    # Limites de palabra por los dos lados: sin ellos `ANA LOPEZ` casaba dentro de
    # `MARIANA LOPEZA` (R1/H-03), que es otra persona.
    cuerpo = r"[^0-9A-Za-z]+".join(re.escape(p) for p in palabras)
    return re.compile(r"(?<![0-9A-Za-z])" + cuerpo + r"(?![0-9A-Za-z])", re.IGNORECASE)


def cuerpo_del_espejo(texto: str) -> str:
    """El texto del documento, **sin el frontmatter YAML** del espejo.

    R1/H-01, y es el hallazgo mas importante de la ronda: los espejos que genera la sala
    de maquina empiezan por un frontmatter con `source_path`, o sea **el nombre y la ruta
    del fichero original**. En un expediente real hay ficheros llamados
    `DNI ALBERTO FRONTAL.pdf` o `Certificado titularidad Bancaria <apellidos>.pdf`, asi
    que buscar sobre el texto completo acredita datos **por como se llama el PDF**, no
    por lo que dice. El validador estaria probando el nombre del fichero.
    """
    if not texto.startswith("---"):
        return texto
    fin = texto.find("\n---", 3)
    if fin == -1:
        return texto
    return texto[fin + 4:]


def _texto_comparable(texto: str, clase: str) -> str:
    cuerpo = cuerpo_del_espejo(texto)
    return _sin_tildes(cuerpo) if clase == "texto" else cuerpo


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
        # TODOS los campos del contrario. R1/H-05: quitar `apellido1`/`apellido2` los
        # hacia desaparecer del denominador —una errata en ellos no salia ni como
        # encontrada ni como faltante—, y ademas `cp`, `provincia` y `telefono` se
        # anadieron al DTO en un commit y no aqui en el siguiente. Un dato de una sola
        # palabra **se valida y se marca como que no acredita**; eso ya lo resuelve
        # `Dato.discriminante`, y omitirlo era resolver dos veces la misma cosa mal.
        for campo, valor, clase in (
            ("nombre", c.nombre, "texto"),
            ("apellido1", c.apellido1, "texto"),
            ("apellido2", c.apellido2, "texto"),
            ("nif", c.nif, "documento"),
            ("email", c.email, "email"),
            ("movil", c.movil, "telefono"),
            ("telefono", c.telefono, "telefono"),
            ("direccion", c.direccion, "texto"),
            ("poblacion", c.poblacion, "texto"),
            ("cp", c.cp, "texto"),
            ("provincia", c.provincia, "texto"),
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
            # Una fila que no se entiende no se puede clasificar: cuenta como no mirada.
            ilegibles.append("(fila de cobertura ilegible)")
            continue
        rel = str(e.get("rel_path") or "")
        slug = str(e.get("slug") or "")
        estado = str(e.get("estado") or "")

        if es_fichero_de_control(rel):
            continue

        if estado == _ESTADO_LEGIBLE and slug:
            legibles.append(slug)
        elif rel:
            # TODO lo que no sea `ok` es ilegible, incluido un estado que este codigo no
            # conozca (R1/H-06): antes un estado desconocido caia fuera de las dos
            # listas y desaparecia del recuento, que es como se convierte un «no lo se»
            # en un «no hay».
            ilegibles.append(rel)
        elif slug:
            ilegibles.append(f"{slug} (sin rel_path)")

    return tuple(legibles), tuple(ilegibles)


def es_fichero_de_control(rel_path: str) -> bool:
    """Si `rel_path` es un fichero de protocolo del expediente y no documental.

    Por **nombre**, no por extension. Un `evidencia.json` aportado como prueba es
    documental; `_caso.md` no lo es aunque sea `.md` (R1/H-02, H-06).
    """
    nombre = (rel_path or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    return nombre in _NOMBRES_CONTROL


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
            # R1/H-11: esto salia como SIN_COMPROBAR y el informe decia «no se pudo
            # mirar en estos documentos» **listando ninguno**. No es un problema del
            # corpus: el valor de la ficha esta mal formado (un telefono de ocho
            # digitos, un NIF de una letra) y el remedio es corregir la ficha.
            salida.append(Hallazgo(dato, NO_BUSCABLE))
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
    cuenta = {ENCONTRADO: 0, NO_ENCONTRADO: 0, SIN_COMPROBAR: 0, NO_BUSCABLE: 0,
              "no_discriminantes": 0}
    for h in hallazgos:
        cuenta[h.veredicto] = cuenta.get(h.veredicto, 0) + 1
        if h.ok and not h.dato.discriminante:
            cuenta["no_discriminantes"] += 1
    return cuenta
