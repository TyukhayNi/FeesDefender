"""El lector de ficheros de apertura de `session_close`.

Prueba la logica pura (`_leer_aperturas`) sobre un arbol sintetico en `tmp_path`.
Nunca toca el `%LOCALAPPDATA%` real: la raiz se INYECTA, que es justo para lo que
la pieza no tiene default.
"""

from pathlib import Path

import scripts.session_close as sc


def _escribir(raiz: Path, nombre: str, texto: str) -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / nombre).write_text(texto, encoding="utf-8")


_PENDIENTE = """---
caso: W-02UDC1
fecha: 2026-09-14
estado: pendiente
fichas: []
---

## El pull relleno con ceros
"""


def test_control_positivo_un_pendiente_se_ve(tmp_path):
    # Sin este test, todos los demas pasan con un lector que devuelve siempre vacio.
    _escribir(tmp_path, "2026-09-14_W-02UDC1.md", _PENDIENTE)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == [("2026-09-14_W-02UDC1.md", "W-02UDC1", "2026-09-14")]
    assert ilegibles == []


def test_fichado_y_descartado_no_avisan(tmp_path):
    _escribir(tmp_path, "a.md", _PENDIENTE.replace("estado: pendiente", "estado: fichado"))
    _escribir(tmp_path, "b.md", _PENDIENTE.replace("estado: pendiente", "estado: descartado"))

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert ilegibles == []


def test_frontmatter_roto_sale_por_ilegibles_y_no_revienta(tmp_path):
    _escribir(tmp_path, "roto.md", "---\ncaso: W-1\nestado: pendiente\nsin cierre\n")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert [f for f, _ in ilegibles] == ["roto.md"]
    assert "cierre" in ilegibles[0][1]


def test_sin_frontmatter_es_ilegible(tmp_path):
    _escribir(tmp_path, "plano.md", "solo prosa, ningun frontmatter\n")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert [f for f, _ in ilegibles] == ["plano.md"]


def test_estado_desconocido_es_ilegible_no_fichado(tmp_path):
    # La direccion del fallo importa: ante la duda, el aviso habla.
    _escribir(tmp_path, "x.md", _PENDIENTE.replace("estado: pendiente", "estado: archivado"))

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert "archivado" in ilegibles[0][1]


def test_carpeta_inexistente_no_lanza(tmp_path):
    pendientes, ilegibles = sc._leer_aperturas(tmp_path / "no-existe")

    assert (pendientes, ilegibles) == ([], [])


def test_solo_mira_md_de_la_carpeta_sin_recursion(tmp_path):
    _escribir(tmp_path, "notas.txt", "lo que sea")
    sub = tmp_path / "sub"
    _escribir(sub, "hondo.md", _PENDIENTE)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    # El .txt no es un fichero de apertura mal escrito: es que no es uno.
    assert (pendientes, ilegibles) == ([], [])


def test_caso_ausente_es_ilegible_aunque_el_nombre_lleve_el_wcode(tmp_path):
    # Impide que alguien "arregle" el lector derivando el caso del nombre.
    sin_caso = "---\nfecha: 2026-09-14\nestado: pendiente\n---\n"
    _escribir(tmp_path, "2026-09-14_W-02UDC1.md", sin_caso)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert "caso" in ilegibles[0][1]


def test_estado_se_normaliza_en_minusculas_y_sin_espacios(tmp_path):
    _escribir(tmp_path, "m.md", _PENDIENTE.replace("estado: pendiente", "estado:  Pendiente  "))

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert [c for _, c, _ in pendientes] == ["W-02UDC1"]
    assert ilegibles == []


def test_raiz_por_defecto_respeta_el_override(monkeypatch, tmp_path):
    monkeypatch.setenv("FEESDEFENDER_APERTURAS", str(tmp_path / "elegida"))

    assert sc.raiz_aperturas_por_defecto() == tmp_path / "elegida"


def test_raiz_por_defecto_cae_en_localappdata(monkeypatch, tmp_path):
    monkeypatch.delenv("FEESDEFENDER_APERTURAS", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert sc.raiz_aperturas_por_defecto() == tmp_path / "FeesDefender" / "aperturas"


def test_el_aviso_calla_cuando_no_hay_nada(tmp_path, capsys):
    # Silencio total: una cabecera vacia en cada cierre es el aviso que nadie lee.
    sc._avisar_aperturas_sin_fichar(tmp_path)

    assert capsys.readouterr().out == ""


def test_el_aviso_nombra_el_pendiente(tmp_path, capsys):
    _escribir(tmp_path, "2026-09-14_W-02UDC1.md", _PENDIENTE)

    sc._avisar_aperturas_sin_fichar(tmp_path)

    salida = capsys.readouterr().out
    assert "2026-09-14_W-02UDC1.md" in salida
    assert "W-02UDC1" in salida


def test_el_aviso_declara_los_ilegibles_aparte(tmp_path, capsys):
    _escribir(tmp_path, "roto.md", "---\nestado: pendiente\n")

    sc._avisar_aperturas_sin_fichar(tmp_path)

    salida = capsys.readouterr().out
    assert "roto.md" in salida
    assert "no interpretable" in salida


def test_el_aviso_no_rompe_el_cierre_si_el_lector_lanza(tmp_path, monkeypatch, capsys):
    def _explota(_raiz):
        raise RuntimeError("boom")

    monkeypatch.setattr(sc, "_leer_aperturas", _explota)

    # La garantia es la del resto de avisos: nunca rompe el cierre.
    try:
        sc._avisar_aperturas_sin_fichar(tmp_path)
    except RuntimeError:
        raise AssertionError("el aviso dejo escapar la excepcion")


def test_una_linea_en_blanco_dentro_del_frontmatter_no_estorba(tmp_path):
    con_hueco = "---\ncaso: W-1\n\nfecha: 2026-09-14\nestado: pendiente\n---\n"
    _escribir(tmp_path, "hueco.md", con_hueco)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert [c for _, c, _ in pendientes] == ["W-1"]
    assert ilegibles == []


def test_lo_que_no_se_puede_leer_se_declara_y_no_tumba_el_recorrido(tmp_path):
    # Un directorio llamado `x.md` casa el glob y revienta al leerse: es el caso
    # real de «no se pudo leer», y lo que importa es que el recorrido SIGA.
    (tmp_path / "roto.md").mkdir(parents=True)
    _escribir(tmp_path, "zbueno.md", _PENDIENTE)

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert [c for _, c, _ in pendientes] == ["W-02UDC1"], "el fallo de uno se llevo al otro"
    assert [f for f, _ in ilegibles] == ["roto.md"]
    assert "no se pudo leer" in ilegibles[0][1]


def test_sin_estado_es_ilegible(tmp_path):
    _escribir(tmp_path, "s.md", "---\ncaso: W-1\nfecha: 2026-09-14\n---\n")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert ilegibles == [("s.md", "falta estado:")]


def test_sin_fecha_es_ilegible(tmp_path):
    _escribir(tmp_path, "f.md", "---\ncaso: W-1\nestado: pendiente\n---\n")

    pendientes, ilegibles = sc._leer_aperturas(tmp_path)

    assert pendientes == []
    assert ilegibles == [("f.md", "falta fecha:")]
