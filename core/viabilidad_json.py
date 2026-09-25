"""El JSON de la 1a pasada de viabilidad: su contrato, su productor y su validador.

**Por que existe este modulo y no una convencion.** `MEJORAS #262` publico el contrato
de este JSON «derivado POR EJECUCION», y salio mal en CUATRO campos: su corrida paso
listas VACIAS y claves desconocidas, que el consumidor sustituye o ignora sin avisar, asi
que el instrumento no podia dar el otro valor. Medido el 2026-09-15: con
`importes: {principal: 12000}` la celda del precio queda vacia y el script imprime `OK`.
Un contrato que solo vive en prosa vuelve a pasar por eso; este vive en `CAMPOS` y en
`validar`, y los tests lo fijan contra el consumidor real.

El consumidor es `.claude/skills/viabilidad-prerelleno/scripts/render_informe.py`, que
corre en el SERVIDOR (Cowork) y no puede importar de aqui. Por eso la validacion esta a
los dos lados: este modulo impide que la corrida escriba basura, y el aviso de claves
desconocidas del consumidor impide que una sesion la escriba a mano. No es duplicacion:
el defecto medido ocurre en el consumidor.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

#: Campo de primer nivel -> tipo que el consumidor espera. Derivado LEYENDO el consumidor
#: y comprobado CORRIENDOLO: `tests/test_render_informe_viabilidad.py`, que arranca
#: `render_informe.py` de verdad contra la plantilla real.
CAMPOS: dict[str, type | tuple[type, ...]] = {
    "case_id": str,
    "ref": str,
    "fecha": str,
    "equipo": dict,
    "observaciones": str,
    "importes": dict,
    "hitos": dict,
    "preguntas": dict,
    "actividades": dict,
    "motivos_impago": str,      # `.strip()` y `.upper()`: NO es una lista
    "avisos": list,             # de OBJETOS, no de cadenas
    "bitacora_inicial": bool,   # se usa como booleano; su texto se descarta
}

CLAVES_EQUIPO = ("director_captador", "asesor_captador",
                 "director_buscador", "asesor_buscador")
#: Las que el consumidor escribe en celdas. `principal`, `costas` e `intereses` —lo que
#: publico #262— NO estan aqui a proposito: no existen para el consumidor.
CLAVES_IMPORTES = ("precio", "pct_honorarios", "pagos_parciales", "propuesta_pago")
CLAVES_ACTIVIDADES = ("exposes_propiedad", "visitas_propiedad",
                      "exposes_buscador", "visitas_buscador")

#: Las claves de `importes` que #262 publico y que se tiran en silencio. Se nombran para
#: que el error DIGA cual es la buena en vez de solo decir que esa no vale.
_IMPORTES_DE_LA_262 = {
    "principal": "precio",
    "costas": None,
    "intereses": None,
}

#: El campo donde la corrida declara lo que no pudo derivar. Guion bajo, como el resto del
#: protocolo del expediente (`_ficha_crm.yaml`, `_recibo_actuacion.json`).
MARCA = "_residuo"


def _problema_de_tipo(nombre, valor, esperado) -> str | None:
    if isinstance(esperado, type) and esperado is bool:
        # `bool` antes que `int`: en Python `True` es `int`, y dejar pasar un 1 aqui
        # aceptaria un JSON que el consumidor interpreta distinto.
        if not isinstance(valor, bool):
            return (f"{nombre}: se espera bool y llego {type(valor).__name__} "
                    f"({valor!r}). El consumidor lo usa como booleano y descarta su "
                    f"contenido.")
        return None
    if not isinstance(valor, esperado):
        return (f"{nombre}: se espera {esperado.__name__} y llego "
                f"{type(valor).__name__} ({valor!r}).")
    return None


def validar(datos: dict) -> list[str]:
    """Los problemas de `datos` contra el contrato. Lista vacia = valido.

    Devuelve TODOS los problemas, no el primero: quien escribe un JSON a mano quiere
    verlos de una vez.
    """
    problemas: list[str] = []
    if not isinstance(datos, dict):
        return [f"el JSON de viabilidad debe ser un objeto y es "
                f"{type(datos).__name__}."]

    for nombre in datos:
        if nombre not in CAMPOS and nombre != MARCA:
            problemas.append(
                f"{nombre}: campo desconocido; el consumidor lo ignorara en silencio. "
                f"Conocidos: {', '.join(sorted(CAMPOS))}.")

    for nombre, esperado in CAMPOS.items():
        if nombre not in datos:
            continue
        p = _problema_de_tipo(nombre, datos[nombre], esperado)
        if p:
            problemas.append(p)

    problemas.extend(_problemas_de_importes(datos.get("importes")))
    problemas.extend(
        _claves_ajenas("equipo", datos.get("equipo"), CLAVES_EQUIPO))
    problemas.extend(
        _claves_ajenas("actividades", datos.get("actividades"), CLAVES_ACTIVIDADES))
    problemas.extend(_problemas_de_avisos(datos.get("avisos")))
    return problemas


def _claves_ajenas(nombre, valor, conocidas) -> list[str]:
    if not isinstance(valor, dict):
        return []
    return [f"{nombre}.{k}: clave desconocida; se ignorara en silencio. "
            f"Conocidas: {', '.join(conocidas)}."
            for k in valor if k not in conocidas]


#: Tipos que una celda de Excel puede recibir sin que `openpyxl` reviente al guardar
#: (`Cell.value = ...`: un `dict` o una lista lanzan `ValueError: Cannot convert ... to
#: Excel`, y lo hacen en el CONSUMIDOR, con el fichero ya escrito). `bool` esta incluido
#: aposta -es lo que espera `bitacora_inicial` en otro campo, y en Python `bool` ya es
#: `int`, asi que no hace falta nombrarlo aparte de `int`-. `None` no esta aqui: se
#: acepta por separado, es la ausencia que el consumidor ya sabe leer (`imp.get(k) is
#: not None`), no un tipo de celda.
_TIPOS_DE_CELDA = (str, int, float, bool)


def _problemas_de_importes(valor) -> list[str]:
    """Las claves de #262 llevan mensaje propio: el error tiene que decir cual es la
    buena, no solo que esa no vale.

    Tambien valida el TIPO del valor de cada clave conocida (R1/H-03): antes solo se
    miraba el NOMBRE de la clave, asi que `{"precio": {"cantidad": 12000}}` pasaba
    -"precio" es una clave valida- y `escribir` lo persistia; el consumidor moria
    despues con `ValueError: Cannot convert {...} to Excel`, ya con el fichero escrito.
    No se exige mas que eso: cualquier tipo que quepa en una celda vale, sin convertir
    esto en una validacion de negocio sobre lo que "tiene sentido" para un importe.
    """
    if not isinstance(valor, dict):
        return []
    problemas = []
    for k in valor:
        if k in CLAVES_IMPORTES:
            v = valor[k]
            if v is not None and not isinstance(v, _TIPOS_DE_CELDA):
                problemas.append(
                    f"importes.{k}: se espera un valor de celda (texto, numero o "
                    f"booleano) y llego {type(v).__name__} ({v!r}); el consumidor no "
                    "puede escribirlo en Excel.")
            continue
        buena = _IMPORTES_DE_LA_262.get(k, "")
        if k in _IMPORTES_DE_LA_262:
            extra = (f" Probablemente querias 'precio'." if buena
                     else " El informe no tiene celda para eso.")
            problemas.append(
                f"importes.{k}: clave que publico MEJORAS #262 y que el consumidor NO "
                f"lee: su valor se tira en silencio.{extra} "
                f"Validas: {', '.join(CLAVES_IMPORTES)}.")
        else:
            problemas.append(
                f"importes.{k}: clave desconocida; se ignorara en silencio. "
                f"Validas: {', '.join(CLAVES_IMPORTES)}.")
    return problemas


def _problemas_de_avisos(valor) -> list[str]:
    if not isinstance(valor, list):
        return []
    return [f"avisos[{i}]: se espera un objeto y llego {type(a).__name__} ({a!r}); "
            f"el consumidor hace .get() sobre cada aviso."
            for i, a in enumerate(valor) if not isinstance(a, dict)]


#: Vive en `00_Input/` y no junto al informe, aunque `#262` sugiriera lo segundo: hay
#: precedente exacto (`_recibo_actuacion.json`), `core/intake_control.py` ya mantiene ahi
#: la lista de ficheros de protocolo que no se inventarian como documento del cliente, y
#: este JSON es la ENTRADA del informe, no una version suya.
NOMBRE_FICHERO = "_viabilidad.json"

#: Lo que la corrida NO puede derivar, con la razon. `equipo` lleva una distinta de las
#: demas a proposito: las otras se resuelven leyendo el expediente y esa no se resuelve
#: leyendo nada, porque el dato no existe en la apertura.
_POR_QUE_FALTA = {
    "equipo": ("El rol (director/asesor x captador/buscador) NO EXISTE como dato en la "
               "apertura: `_ficha_crm.yaml` trae nombre, email, movil, telefono y nif, y "
               "ninguna clave de rol o lado (medido el 2026-09-15 sobre 10 fichas y 25 "
               "colaboradores). No se resuelve leyendo el expediente: hay que saberlo."),
    "importes": "Salen de la escritura, las arras o la hoja de encargo: hay que leerlas.",
    "hitos": "Los 14 hitos exigen leer la documental del expediente.",
    "preguntas": "Las 88 preguntas del cuestionario exigen leer la documental.",
    "avisos": "Salen de lo que se encuentre al leer.",
    "actividades": "Exposes y visitas salen del CRM de E&V o de la documental.",
    "motivos_impago": "Solo si consta la postura del deudor en la documental.",
}


def ruta(case_dir) -> Path:
    return Path(case_dir) / "00_Input" / NOMBRE_FICHERO


def preparar(ident, *, hoy: str) -> dict:
    """El JSON con lo que la corrida SI puede derivar, y el residuo marcado.

    El contrato (`CAMPOS`) tiene DOCE campos. Esta funcion deriva CUATRO con dato real
    (`case_id`, `ref`, `fecha`, `observaciones`: los cuatro vienen de `ident`/`hoy`) y
    deja SIETE marcados como residuo en `_POR_QUE_FALTA` (`equipo`, `importes`, `hitos`,
    `preguntas`, `actividades`, `motivos_impago`, `avisos`) -los 14 hitos y las 88
    preguntas siguen siendo trabajo de una sesion, y este modulo no finge lo contrario,
    por eso existe la marca-. `bitacora_inicial` queda FUERA de las dos cuentas: se fija
    a `True` sin leer el expediente (no viene de `ident`/`hoy`, no hay nada que derivar)
    y tampoco esta en `_POR_QUE_FALTA` (no se declara residuo pendiente de una sesion).
    4 + 7 + 1 = 12: quien recuente esto, que lo haga contra `CAMPOS` y `_POR_QUE_FALTA`,
    no de memoria.

    `hoy` se RECIBE, no se lee aqui: una fecha que el modulo saca del reloj no se puede
    fijar en un test, y la regla de la casa es que la fecha se toma del sistema en el
    punto que la escribe, nunca del contexto.
    """
    return {
        "case_id": ident.case_id,
        "ref": ident.w_code,
        "fecha": hoy,
        "observaciones": ident.tipo_caso,
        "equipo": {k: "" for k in CLAVES_EQUIPO},
        "importes": {},
        "hitos": {},
        "preguntas": {},
        "actividades": {},
        "motivos_impago": "",
        "avisos": [],
        "bitacora_inicial": True,
        MARCA: {
            "campos": sorted(_POR_QUE_FALTA),
            "por_que": dict(_POR_QUE_FALTA),
            "lo_remata": ("Una sesion que lea el expediente. Rellena estos campos y corre "
                          "render_informe.py de la skill `viabilidad-prerelleno`."),
        },
    }


def _mensaje_ya_existe(destino: Path) -> str:
    return (f"{destino} ya existe. Lo unico caro de este fichero es lo que puso la "
            f"sesion que lo remato: no se pisa.")


#: Los `winerror` con los que Windows dice «este sistema de ficheros no hace hard links»:
#: 1 (ERROR_INVALID_FUNCTION), que es lo que devuelve el montaje de Drive for Desktop
#: —medido en W-030A13 el 2026-09-16, en W-0462E1 el 2026-09-17 y en `G:` el
#: 2026-09-25—, y 50 (ERROR_NOT_SUPPORTED).
_WINERROR_SIN_ENLACE = frozenset({1, 50})


def _sin_enlace_duro(exc: OSError) -> bool:
    """¿El `os.link` falló porque el sistema de ficheros no admite hard links?

    Se decide por `winerror`, no por `errno`: en ese montaje el `errno` es 22 (EINVAL),
    que en POSIX significa muchas cosas y ninguna es esta. Un permiso denegado o un fallo
    de E/S NO son esto, y siguen propagándose como lo que son (MEJORAS #276).
    """
    return getattr(exc, "winerror", None) in _WINERROR_SIN_ENLACE


def escribir(case_dir, datos: dict) -> Path:
    """Escribe el JSON. **Nunca sobrescribe** y, si el destino llega a existir,
    **nunca esta a medias** -ni siquiera si el proceso muere de golpe en mitad de la
    operacion.

    Valida ANTES de abrir nada: un fichero incompleto bloquea el reintento sin contener
    el trabajo, que es lo peor de los dos mundos.

    Publicacion en dos pasos: el contenido completo se vuelca primero a un temporal en
    el MISMO directorio que el destino (el paso siguiente exige el mismo sistema de
    ficheros), y ese temporal se publica con `os.link` -no `os.rename`/`os.replace`; el
    porque, en el comentario junto a esa linea, mas abajo-. La exclusividad vive en el
    PROPIO acto de publicar: `os.link` falla si el destino ya existe, en el mismo paso
    que lo crea, sin hueco entre comprobar y escribir. La `destino.exists()` de aqui
    abajo es solo un atajo para el caso comun -falla rapido, sin tocar disco ni crear
    el temporal-; quien de verdad cierra la carrera es el `os.link` final, y por eso el
    test de la carrera abre la ventana parcheando la escritura del temporal, no esa
    comprobacion.

    Dos promesas, y hasta donde llega cada una:
      - GARANTIZADA siempre, incluso si el proceso muere sin avisar (`kill -9`) en
        cualquier instante: el destino nunca se pisa -si otra sesion ya lo
        remato, esta funcion falla con `FileExistsError` en vez de tocarlo- y, si esta
        funcion SI llega a crearlo, nunca queda con contenido parcial -nace de un
        `os.link` a un temporal que ya estaba completo, no de escribirse in situ, asi
        que no hay ningun instante en que el destino exista a medio llenar-.
      - NO GARANTIZADA: que no quede un `.tmp` huerfano en `00_Input/`. El `finally` de
        aqui abajo lo borra ante cualquier fallo que Python pueda interceptar -incluida
        una excepcion del propio `os.link`-, pero un `kill -9` justo entre el `os.link`
        de exito y ese `unlink` deja el temporal en disco. No es el destino -no lleva
        su nombre, nada lo confunde con el protocolo del caso- pero es litter que un
        reintento no limpia solo.

    **En un sistema de ficheros sin hard links** (el montaje de Drive for Desktop en
    Windows, `MEJORAS #276`) el temporal se publica con `os.rename`, que en Windows
    conserva las DOS promesas: no pisa un destino existente y publica de una vez lo que
    ya estaba completo. Fuera de Windows no hay esa vía y el error se propaga.

    **Lo que ninguna de las dos vías promete: sobrevivir a un corte de luz.** No hay
    `fsync` ni del contenido ni del nombre, así que la persistencia física no está
    acreditada. Hasta el 2026-09-25 este docstring la daba por garantizada; lo señaló la
    R2 de Codex sobre `#276`, y es anterior a ese cambio.
    """
    problemas = validar(datos)
    if problemas:
        raise ValueError(
            "el JSON de viabilidad no cumple el contrato, no se escribe nada:\n  - "
            + "\n  - ".join(problemas))
    destino = ruta(case_dir)
    if destino.exists():
        raise FileExistsError(_mensaje_ya_existe(destino))
    destino.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps(datos, ensure_ascii=False, indent=2) + "\n"
    # Escritura atomica: se vuelca a un temporal en el MISMO directorio que destino (el
    # `os.link` de mas abajo exige el mismo sistema de ficheros; el temp global del SO
    # puede vivir en otro volumen). `mkstemp` reserva el nombre de forma unica y sin
    # carrera; se cierra ese descriptor de inmediato porque el contenido se escribe con
    # `Path.write_text`, no con el fd crudo.
    fd, tmp_nombre = tempfile.mkstemp(dir=destino.parent, prefix=f"{destino.name}.",
                                       suffix=".tmp")
    tmp = Path(tmp_nombre)
    try:
        os.close(fd)
        tmp.write_text(contenido, encoding="utf-8")
        # PORTABLE a proposito, no "funciona en Windows y ya": en POSIX `os.rename` y
        # `os.replace` SOBRESCRIBEN en silencio si el destino existe -no hay flag
        # portable para evitarlo desde el modulo `os`; el `RENAME_NOREPLACE` de Linux
        # no esta expuesto ahi-. En Windows si fallan -medido: `os.rename` contra un
        # destino existente lanza `FileExistsError`-, pero el desarrollo es Windows y
        # la CI (`.github/workflows/leak-scan.yml`) corre en `ubuntu-latest`: hoy esa
        # CI no ejecuta pytest sobre este fichero -solo gitleaks y leak-guard-, y
        # apostar la exclusividad a que eso siga asi es justo la suposicion que este
        # bug ya penalizo una vez. `os.link` en cambio falla con `FileExistsError` si
        # el destino existe TANTO en POSIX -`link(2)`: si el nuevo nombre ya existe,
        # falla; es parte del estandar, no un detalle de implementacion- COMO en
        # Windows -medido aqui: `CreateHardLink` devuelve WinError 183 y Python lo
        # traduce al mismo `FileExistsError`, errno 17-: mismo comportamiento, misma
        # excepcion, en los dos mundos. Efecto lateral que interesa: como el temporal
        # ya esta COMPLETO antes de este paso, un `os.link` de exito nunca publica un
        # destino a medias.
        try:
            os.link(tmp, destino)
        except FileExistsError:
            raise FileExistsError(_mensaje_ya_existe(destino)) from None
        except OSError as exc:
            # MEJORAS #276. El montaje de Drive for Desktop —donde vive TODO expediente de
            # `CASOS_ROOT`— no implementa hard links y devuelve `WinError 1`; la etapa
            # `viabilidad` tumbaba entera la corrida V1. En Windows hay una primitiva que
            # da las DOS promesas del docstring: `os.rename` (MoveFileEx sin
            # REPLACE_EXISTING) falla si el destino existe y publica de una vez un
            # temporal ya completo. Medido en `G:` el 2026-09-25: con el destino
            # presente, `FileExistsError` (`WinError 183`) y el destino intacto. Fuera de
            # Windows `os.rename` PISA en silencio, así que ahí no hay vía de repuesto y
            # el error se propaga como antes.
            if not (os.name == "nt" and _sin_enlace_duro(exc)):
                raise
            try:
                os.rename(tmp, destino)
            except FileExistsError:
                raise FileExistsError(_mensaje_ya_existe(destino)) from None
    finally:
        # A diferencia de `os.replace` (que renombra: el nombre `tmp` deja de existir
        # tras el exito), `os.link` AÑADE un nombre nuevo sin tocar el viejo: tras un
        # `link` de exito, `tmp` sigue existiendo como entrada separada que apunta al
        # mismo contenido. Este `unlink` la retira en TODOS los casos -exito, fallo de
        # `os.link`, o fallo de la escritura de mas arriba-. `missing_ok=True` es
        # NECESARIO, no defensivo: tras el `os.rename` de exito de la via sin hard link
        # (`MEJORAS #276`) el nombre `tmp` ya no existe.
        tmp.unlink(missing_ok=True)
    return destino
