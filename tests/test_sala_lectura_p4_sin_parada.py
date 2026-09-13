"""P4 — la sala de lectura deja de exigir una clasificación completa antes de existir.

Dos piezas separables, las dos sobre `core/sala_lectura.py`:

1. **`[APER-61]`: la identidad se enruta por PARTE, no a PBC.** `_KEYWORDS` mandaba
   `dni`/`nie`/`pasaporte`/`nota simple`/`titularidad` a `06. PBC`; el runbook
   (`[APER-61]`, `references/taxonomia_ev.md`) dice que la identidad del **vendedor** va
   a `01. ACTIVACIÓN`, la del **comprador** a `03. OFERTAS`, y que a `06. PBC` van
   **solo** los Anexos 1 y 2. El síntoma medido era «`03. OFERTAS` con 1 documento y
   `06. PBC` con 28». Sobre los 1.352 documentos de los diez expedientes reales, la
   corrección mueve **59** documentos de `06. PBC` a `01. ACTIVACIÓN`.

2. **La parada deja de ser una verja.** `organizar` abortaba antes de `render_indices` y
   `poblar_sala_lectura` en cuanto hubiera un documento sin clasificar, así que con
   residuo **no se montaba ninguna sala**: en W-030TZY el letrado tenía que clasificar 80
   documentos a mano *antes de que existiera nada que leer*, y en W-02NHNC, 21. Ahora el
   residuo recibe `08. PENDIENTE DE CLASIFICAR` con confianza 0.0 —la categoría existe en
   `TAXONOMIA_EV` desde siempre— y la sala se monta entera. La worklist se sigue
   escribiendo y el conteo se sigue diciendo: lo que cambia es que es un **aviso**, no una
   verja.

**Lo que esto NO es, y conviene no confundirlo** (medido sobre esos 1.352 documentos): no
mejora la clasificación. El 57 % que la regla por nombre no sabe clasificar sigue sin
saberse —los nombres no llevan la señal (`CaseDossierReport - …-V.pdf`, `DEVOLUCIO
CLAUS.pdf`)— y acaba en `08` en vez de en una parada. Lo que cambia es que la sala pasa de
**no existir** a existir con los 1.352 documentos nombrados y fechados, y el letrado
corrige leyendo, que es lo que el handoff pedía. Portar la regla de la skill
(`preclasificar.clasificar_por_patron`), que era la propuesta literal de P4, se midió y es
peor: manda el 90,5 % a `07. RECLAMACIONES` y deja **0** de las 123 fotos en `00. FOTOS`,
porque detecta imágenes solo por `screenshot|captura` y no por extensión.
"""
from __future__ import annotations

import importlib

import pytest

from core.config import UMBRAL_CONFIANZA_AUTOMOVE

PENDIENTE = "08. PENDIENTE DE CLASIFICAR"


def _reload():
    from core import case_manager, catalogo_documental, inventory, sala_lectura
    importlib.reload(case_manager)
    importlib.reload(inventory)
    importlib.reload(catalogo_documental)
    importlib.reload(sala_lectura)
    return case_manager, inventory, catalogo_documental, sala_lectura


def _caso_con_docs(case_manager, inventory, catalogo, docs, case_id="EV-2026-P4"):
    case_dir = case_manager.ensure_case(case_id)
    for sub, name, content in docs:
        p = case_dir / "00_Input" / sub / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8") if isinstance(content, str) else p.write_bytes(content)
    inventory.scan(case_id)
    catalogo.build_catalog(case_id)
    return case_id, case_dir


# ---------------------------------------------------------------------------
# Pieza 1 — [APER-61]: la identidad se enruta por parte
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nombre, esperado", [
    # Identidad y titularidad del VENDEDOR -> 01. ACTIVACIÓN (antes: 06. PBC).
    ("DNI Mercedes Loyo.pdf", "01. ACTIVACIÓN"),
    ("NIE del propietario.pdf", "01. ACTIVACIÓN"),
    ("Pasaporte titular.pdf", "01. ACTIVACIÓN"),
    ("NOTA SIMPLE TERRENO.pdf", "01. ACTIVACIÓN"),
    ("Certificado de titularidad.pdf", "01. ACTIVACIÓN"),
    # SOLO los Anexos 1 y 2 se quedan en PBC.
    ("Anexo 1 formulario PBC.pdf", "06. PBC"),
    ("Anexo 2 titular real.pdf", "06. PBC"),
    ("Declaracion PBC blanqueo.pdf", "06. PBC"),
])
def test_aper61_la_identidad_no_va_a_pbc(nombre, esperado):
    """`[APER-61]`: el motor mandaba a `06. PBC` toda la identidad y la nota simple.

    Es la causa codificada del síntoma que el runbook describe: `06. PBC` con 28
    documentos y `03. OFERTAS` con 1.
    """
    _, _, _, sala_lectura = _reload()
    assert sala_lectura._categoria_por_nombre(nombre) == esperado


def test_aper61_la_hoja_de_visita_es_del_comprador():
    """La hoja de visita la firma el comprador: `03. OFERTAS`, no `01. ACTIVACIÓN`."""
    _, _, _, sala_lectura = _reload()
    assert sala_lectura._categoria_por_nombre("Hoja de visita firmada.pdf") == "03. OFERTAS"


@pytest.mark.parametrize("nombre, token_espurio", [
    ("Companies_House_Jaime_appointments.md", "nie"),   # compa·nie·s
    ("2024-01-11_carrer_carrasco_formiguera.eml", "arras"),  # c·arras·co
])
def test_un_token_no_casa_dentro_de_otra_palabra(nombre, token_espurio):
    """Los tokens se comparaban con `in`, así que casaban en MEDIO de otra palabra.

    Los dos casos son reales, del catálogo de expedientes vivos: `Companies` clasificaba
    como `06. PBC` por llevar `nie` dentro, y `carrasco` como arras. La frontera no es
    «el token es una palabra entera» —eso rompería `oferta2.pdf` y `PBC1 ….pdf`, que son
    verdaderos positivos medidos—, sino **que el token empiece una palabra**.
    """
    _, _, _, sala_lectura = _reload()
    assert token_espurio in nombre.lower().replace("_", " ")
    assert sala_lectura._categoria_por_nombre(nombre) is None


@pytest.mark.parametrize("nombre, esperado", [
    ("oferta2.pdf", "03. OFERTAS"),
    ("ofertas recibidas.pdf", "03. OFERTAS"),
    ("PBC1 JOSEP GIRBAU.pdf", "06. PBC"),
    ("facturas del mes.pdf", "05. FACTURACIÓN - FINANZAS"),
])
def test_un_token_tolera_el_sufijo_de_su_palabra(nombre, esperado):
    """Numeración y plural NO rompen el reconocimiento: el token identifica el INICIO."""
    _, _, _, sala_lectura = _reload()
    assert sala_lectura._categoria_por_nombre(nombre) == esperado


def test_categoria_por_nombre_sigue_devolviendo_none_sin_pistas():
    """La REGLA sigue separada de la POLÍTICA.

    `_categoria_por_nombre` es la regla de keyword pura y sigue diciendo `None` cuando no
    sabe; quien decide qué hacer con ese `None` —antes parar, ahora `08`— es
    `clasificar_caso`. Fundirlas dejaría a la regla sin poder expresar «no lo sé».
    """
    _, _, _, sala_lectura = _reload()
    assert sala_lectura._categoria_por_nombre("Documento sin pistas.pdf") is None


# ---------------------------------------------------------------------------
# Pieza 2 — la parada deja de ser una verja
# ---------------------------------------------------------------------------


def test_el_residuo_recibe_pendiente_con_confianza_cero(tmp_casos_root):
    """Lo que la regla no sabe clasificar se marca `08`, no se deja sin tipo.

    La confianza 0.0 no es cosmética: es lo que hace que `clasificar_caso` lo reintente
    en la corrida siguiente y que `aplicar_clasificacion(solo_residuo=True)` pueda
    pisarlo. Con confianza >= UMBRAL_CONFIANZA_AUTOMOVE quedaría congelado como si
    alguien lo hubiera decidido.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, _ = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Factura honorarios 2025.pdf", "x"),
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    r = sala_lectura.clasificar_caso(case_id)

    assert r["n_residuo"] == 1, "el conteo del residuo se sigue diciendo"
    entries = {e.nombre_original: e for e in cat.load_catalog(case_id)}
    pendiente = entries["Documento sin pistas.pdf"]
    assert pendiente.tipo_documental == PENDIENTE
    assert pendiente.confianza == 0.0
    assert pendiente.confianza < UMBRAL_CONFIANZA_AUTOMOVE


def test_organizar_monta_la_sala_aunque_haya_residuo(tmp_casos_root):
    """El corazón de P4: con residuo, la sala SE MONTA.

    Antes `organizar` devolvía `detenido_por_residuo: True` y salía sin llamar a
    `render_indices` ni a `poblar_sala_lectura`: el letrado no tenía nada que leer hasta
    haber clasificado todo a mano.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Factura honorarios 2025.pdf", "x"),
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    r = sala_lectura.organizar(case_id)

    assert r["n_pendientes"] == 1, "el pendiente se cuenta y se dice"
    assert r["acciones"], "se pobló la sala: hubo acciones de copia"
    sala = case_dir / "01_Procesado" / "Sala lectura"
    # Solo los DOCUMENTOS: `INDICE.md` y `CRONOLOGIA.md` viven en la misma carpeta y
    # contarlos como copias hacía que este aserto midiera otra cosa.
    copiados = sorted(p.name for p in sala.rglob("*.pdf") if p.is_file())
    assert len(copiados) == 2, f"los DOS documentos están en la sala: {copiados}"
    assert any("_pendiente_" in n for n in copiados), copiados
    assert any("_factura_" in n for n in copiados), copiados
    assert (sala / "INDICE.md").exists()


def test_el_documento_pendiente_llega_a_la_sala_con_su_nombre(tmp_casos_root):
    """El pendiente no se queda fuera: entra con el slug `pendiente`, que lo hace visible.

    Es la diferencia entre «un índice que calla» y uno que señala: el propio nombre del
    fichero dice que nadie lo ha clasificado todavía.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    sala_lectura.organizar(case_id)

    sala = case_dir / "01_Procesado" / "Sala lectura"
    nombres = [p.name for p in sala.rglob("*") if p.is_file() and p.suffix == ".pdf"]
    assert len(nombres) == 1
    assert "_pendiente_" in nombres[0], nombres[0]


def test_el_pendiente_entra_con_su_fecha_no_con_ceros(tmp_casos_root):
    """Un pendiente conserva la fecha que se le pueda inferir; `0000-00-00` es el último
    recurso, no el trato por defecto.

    La fecha no depende de la categoría, así que el residuo se fecha con `_fecha_de` igual
    que las ramas resueltas. Sin esto, en un expediente donde el 55 % de los documentos
    cae a `08` —lo medido sobre diez expedientes reales—, ese 55 % entraría a la sala como
    `0000-00-00_pendiente_…` y la `CRONOLOGIA.md` quedaría inservible justo en los
    documentos que hay que leer.

    Lo levantó el mutante M10 del arnés, que sobrevivió a la primera pasada.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "2025-03-20 sin pistas.pdf", "y"),     # fecha en el nombre
        ("04_Manual", "Documento sin pistas.pdf", "z"),      # solo mtime
    ])
    sala_lectura.organizar(case_id)

    entries = {e.nombre_original: e for e in cat.load_catalog(case_id)}
    con_fecha = entries["2025-03-20 sin pistas.pdf"]
    assert con_fecha.tipo_documental == PENDIENTE
    assert con_fecha.fecha_doc == "2025-03-20"
    assert con_fecha.fecha_fuente == "contenido"

    solo_mtime = entries["Documento sin pistas.pdf"]
    assert solo_mtime.fecha_doc and solo_mtime.fecha_doc != "0000-00-00", (
        "el pendiente entró sin fecha pudiendo inferirla del mtime")

    sala = case_dir / "01_Procesado" / "Sala lectura"
    nombres = sorted(p.name for p in sala.rglob("*.pdf"))
    assert any(n.startswith("2025-03-20_pendiente_") for n in nombres), nombres
    assert not any(n.startswith("0000-00-00") for n in nombres), nombres


def test_la_worklist_se_sigue_escribiendo_con_el_residuo(tmp_casos_root):
    """Quitar la verja no quita el instrumento: la worklist sigue ahí para corregir."""
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    sala_lectura.organizar(case_id)

    worklist = case_dir / "01_Procesado" / "_revisar" / sala_lectura.WORKLIST_NAME
    assert worklist.exists()
    assert "Documento sin pistas.pdf" in worklist.read_text(encoding="utf-8")


def test_el_pendiente_no_se_congela_en_la_corrida_siguiente(tmp_casos_root):
    """Un `08` no es una decisión tomada: cada corrida vuelve a evaluarlo.

    Es LA propiedad que compra `_CONF_PENDIENTE = 0.0`. Con una confianza >= UMBRAL,
    `clasificar_caso` lo saltaría por «ya resuelto en una corrida previa» y el documento
    quedaría «pendiente» para siempre: la pieza 2 habría cambiado una parada ruidosa por
    un error permanente y silencioso.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, _ = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    primera = sala_lectura.clasificar_caso(case_id)
    segunda = sala_lectura.clasificar_caso(case_id)

    assert primera["n_residuo"] == 1
    assert segunda["n_residuo"] == 1, (
        "la segunda corrida lo saltó por 'ya resuelto': el 08 quedó congelado")


def test_un_pendiente_se_recupera_cuando_el_material_mejora(tmp_casos_root):
    """Repuesto con un nombre reconocible, el documento deja de ser `08`.

    El fichero repuesto lleva contenido distinto **a propósito**: `build_catalog` preserva
    las filas por hash, así que reponerlo con el mismo contenido conservaría la fila vieja
    con su `nombre_original` y este test mediría el hash, no la reclasificación.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    sala_lectura.clasificar_caso(case_id)
    assert cat.load_catalog(case_id)[0].tipo_documental == PENDIENTE

    (case_dir / "00_Input" / "04_Manual" / "Documento sin pistas.pdf").unlink()
    (case_dir / "00_Input" / "04_Manual" / "Burofax requerimiento.pdf").write_text(
        "otro contenido", encoding="utf-8")
    inv.scan(case_id)
    cat.build_catalog(case_id)
    sala_lectura.clasificar_caso(case_id)

    tipos = {e.nombre_original: e.tipo_documental for e in cat.load_catalog(case_id)}
    assert tipos["Burofax requerimiento.pdf"] == "07. RECLAMACIONES"


def test_la_worklist_rellenada_pisa_el_pendiente(tmp_casos_root):
    """`aplicar_clasificacion(solo_residuo=True)` corrige un `08`, que es su razón de ser.

    `solo_residuo` respeta «lo ya resuelto», y un `08` con confianza 0.0 no lo está: si
    lo respetase, el letrado no podría corregir desde la worklist y la pieza 2 habría
    roto el único camino de corrección que existe.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    sala_lectura.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash

    worklist = case_dir / "01_Procesado" / "_revisar" / sala_lectura.WORKLIST_NAME
    worklist.write_text(
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| {h} | x | manual | 01. ACTIVACIÓN | 2025-01-02 | propietario | encargo |\n",
        encoding="utf-8")
    sala_lectura.aplicar_clasificacion(case_id, solo_residuo=True)

    e = cat.load_catalog(case_id)[0]
    assert e.tipo_documental == "01. ACTIVACIÓN"
    assert e.confianza >= UMBRAL_CONFIANZA_AUTOMOVE


def test_organizar_ya_no_publica_detenido_por_residuo(tmp_casos_root):
    """La clave se RETIRA, no se deja en `False`.

    Dejarla siempre `False` sería una mentira silenciosa para cualquier consumidor que la
    leyera: diría «no me detuve» sin decir que ya no puede detenerse. Un `KeyError`
    ruidoso es preferible. Los únicos consumidores eran `scripts/sala_lectura.py` y estos
    tests (comprobado con `grep -rn detenido_por_residuo`).
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, _ = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    r = sala_lectura.organizar(case_id)
    assert "detenido_por_residuo" not in r
    assert "n_pendientes" in r


# ---------------------------------------------------------------------------
# La frontera: qué cuenta como «decidido». `08` NO cuenta, y hay varios sitios
# que lo preguntan por su cuenta.
# ---------------------------------------------------------------------------


def test_un_pendiente_sigue_siendo_residuo_para_preparar_residuo(tmp_casos_root):
    """`08` en la worklist NO es una clasificación: `preparar-residuo` lo sigue ofreciendo.

    Es la regresión que casi entra con la pieza 2. `_hashes_residuo` decidía «resuelto»
    preguntando si el `Tipo` está en `TAXONOMIA_EV`, y `08. PENDIENTE DE CLASIFICAR`
    **está** en la taxonomía: marcar el residuo con `08` lo hacía invisible para
    `preparar_residuo`, que habría respondido «todo el catálogo está clasificado» con el
    expediente entero sin clasificar. Es, literalmente, el defecto de W-02JSVZ que ese
    módulo aprendió a no cometer (`residuo_sin_texto`), resucitado por otra puerta.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    sala_lectura.clasificar_caso(case_id)

    h = cat.load_catalog(case_id)[0].hash
    # El espejo MD, para que `preparar_residuo` tenga texto que ofrecer.
    md = case_dir / "01_Procesado" / "02_Sala de máquina" / "03_MD"
    md.mkdir(parents=True, exist_ok=True)
    from core.utils import output_slug
    slug = output_slug(cat.load_catalog(case_id)[0].ruta_relativa, h)
    (md / f"{slug}.md").write_text("---\nchars: 9\n---\ntexto util", encoding="utf-8")

    assert h in sala_lectura._hashes_residuo(case_id), (
        "un 08 dejó de contar como residuo: el letrado pierde el camino de corrección")
    assert [d["hash"] for d in sala_lectura.preparar_residuo(case_id)] == [h]


def test_un_08_escrito_en_la_worklist_no_congela_el_documento(tmp_casos_root):
    """El letrado puede escribir `08` («lo miré y no sé») sin que eso cierre la pregunta.

    `aplicar_clasificacion` valida el tipo contra `TAXONOMIA_EV` y aplica con confianza
    1.0; como `08` está en la taxonomía, un `08` escrito a mano quedaría con confianza
    plena y **ningún** camino volvería a preguntarlo. `08` es la ausencia de decisión
    venga de donde venga: de la regla o del teclado.
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    sala_lectura.clasificar_caso(case_id)
    h = cat.load_catalog(case_id)[0].hash

    worklist = case_dir / "01_Procesado" / "_revisar" / sala_lectura.WORKLIST_NAME
    worklist.write_text(
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |\n"
        "|---|---|---|---|---|---|---|\n"
        f"| {h} | x | manual | {PENDIENTE} | 2025-01-02 |  | no se sabe |\n",
        encoding="utf-8")
    sala_lectura.aplicar_clasificacion(case_id)

    e = cat.load_catalog(case_id)[0]
    assert e.tipo_documental == PENDIENTE
    assert e.confianza < UMBRAL_CONFIANZA_AUTOMOVE, (
        "un 08 aplicado a mano quedó con confianza plena: pregunta cerrada en falso")
    # Los DOS caminos que vuelven a preguntar, no solo el de la confianza.
    assert h in sala_lectura._hashes_residuo(case_id), (
        "un 08 en la worklist lo hizo invisible para preparar-residuo")
    assert sala_lectura.clasificar_caso(case_id)["n_residuo"] == 1


def test_la_cli_no_declara_clasificado_un_catalogo_lleno_de_pendientes(tmp_casos_root):
    """La guarda de `preparar-residuo` no puede volverse INERTE al marcar el residuo.

    Ese bloque existe por un defecto medido y su comentario lo dice entero: «si el catálogo
    tiene documentos sin tipo, esta frase no se puede decir». La frase es *«Sin residuo:
    todo el catálogo está clasificado»*. La guarda preguntaba `not e.tipo_documental`, y
    con el residuo marcado `08` esa lista es **siempre vacía**: la guarda seguía ahí,
    seguía verde, y ya no podía dar el otro valor.

    El escenario que la activa es real, no de laboratorio: worklist **rancia** —el material
    de `00_Input` cambió y ningún hash casa—, con lo que `preparar_residuo` y
    `residuo_sin_texto` salen vacíos por la worklist mientras el catálogo tiene el
    expediente entero en `08`. Sin este test, el CLI lo declararía clasificado y saldría
    con código 0.
    """
    from typer.testing import CliRunner
    cm, inv, cat, sala_lectura = _reload()
    case_id, case_dir = _caso_con_docs(cm, inv, cat, [
        ("04_Manual", "Documento sin pistas.pdf", "y"),
    ])
    sala_lectura.clasificar_caso(case_id)

    # Worklist rancia: una fila cuyo hash no está en el catálogo.
    worklist = case_dir / "01_Procesado" / "_revisar" / sala_lectura.WORKLIST_NAME
    worklist.write_text(
        "| Hash | Origen | Fuente | Tipo | Fecha | Parte | Descripcion |\n"
        "|---|---|---|---|---|---|---|\n"
        "| 0000000000000000 | viejo.pdf | manual |  |  |  |  |\n",
        encoding="utf-8")

    import importlib
    import scripts.sala_lectura as cli
    importlib.reload(cli)
    res = CliRunner().invoke(cli.app, ["preparar-residuo", "--case", case_id])

    assert "todo el catálogo está clasificado" not in res.output, res.output
    assert res.exit_code == 1, (
        f"declaró clasificado un catálogo con pendientes, y con código 0:\n{res.output}")


def test_sin_material_sigue_sin_montar_nada(tmp_casos_root):
    """La guarda de «no había nada que hacer» no se toca: sigue siendo distinta del éxito.

    P4 quita la parada por residuo, no la distinción entre una sala vacía y una sala que
    no hacía falta montar (`MEJORAS #151`).
    """
    cm, inv, cat, sala_lectura = _reload()
    case_id = "EV-2026-P4-VACIO"
    cm.ensure_case(case_id)
    r = sala_lectura.organizar(case_id)
    assert r["sin_material"] is True
    assert r["motivo"] == "input_vacio"
