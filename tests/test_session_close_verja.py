"""La verja de dos semillas de `session_close`, incluida su rama de ROJO.

## Por qué existe este fichero

`diff-cover` señaló el 2026-09-06 que las líneas nuevas de la verja —justamente el bloque
que se ejecuta **cuando algo falla**— no las cubría ningún test. Es la peor clase de código
sin probar: solo corre el día que hay un rojo, o sea el peor momento posible para descubrir
que el mensaje que te dice cómo reproducirlo está mal escrito.

Se probó en vez de bajar el umbral hasta que el instrumento dejara de quejarse. Para
probarlo hubo que extraer `correr_la_verja` de `main()`, que es el mismo movimiento que
`tests/conftest.py` hizo con `restaurar_config_si_secuestrada` y por la misma razón.

## Lo que se contrata

- Que corra **las dos** semillas cuando todo va bien, y ninguna de más.
- Que **pare en la primera que falle** y no siga gastando dos minutos en la segunda.
- Que el mensaje del rojo diga **la semilla concreta** y una orden **que de verdad
  reproduzca**: sin eso, «tests fallando» con orden aleatorio es un callejón sin salida.
  R2 de Codex (H-09) midió que esa receta perdía `--runslow`, así que ante el rojo de un
  test lento imprimía una orden que no lo ejecuta. La orden impresa y la ejecutada salen
  ahora de la misma función.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _modulo():
    """`scripts/session_close.py` como módulo, sin ejecutar su `main()`."""
    spec = importlib.util.spec_from_file_location(
        "session_close_bajo_prueba", RAIZ / "scripts" / "session_close.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@dataclass
class _Resultado:
    returncode: int


class _CorredorFalso:
    """Sustituye a `subprocess.run`. Guarda cada orden y devuelve los códigos que se le den."""

    def __init__(self, codigos: list[int]):
        self.codigos = list(codigos)
        self.ordenes: list[list[str]] = []

    def __call__(self, orden, **_kw):
        self.ordenes.append(list(orden))
        return _Resultado(self.codigos.pop(0) if self.codigos else 0)


def test_verde_corre_las_dos_semillas_y_no_mas(capsys):
    sc = _modulo()
    corredor = _CorredorFalso([0, 0])

    motivo = sc.correr_la_verja([], corredor=corredor)

    assert motivo is None
    assert len(corredor.ordenes) == len(sc.SEMILLAS_DE_ACEPTACION) == 2
    for orden, semilla in zip(corredor.ordenes, sc.SEMILLAS_DE_ACEPTACION):
        assert f"--randomly-seed={semilla}" in orden
    assert "verdes con las 2 semillas" in capsys.readouterr().out


def test_el_rojo_de_la_PRIMERA_semilla_no_gasta_la_segunda(capsys):
    """Parar en el primer rojo no es una optimización: seguir dos minutos más con la
    suite ya rota solo retrasa el diagnóstico."""
    sc = _modulo()
    corredor = _CorredorFalso([1, 0])

    motivo = sc.correr_la_verja([], corredor=corredor)

    assert motivo == f"semilla {sc.SEMILLAS_DE_ACEPTACION[0]}"
    assert len(corredor.ordenes) == 1, "siguió corriendo con la suite ya en rojo"


def test_el_rojo_de_la_SEGUNDA_semilla_tambien_para_la_verja(capsys):
    """La segunda semilla existe precisamente para cazar lo que la primera no ve. Si su
    rojo no parara el cierre, la regla de las dos semillas sería decorativa."""
    sc = _modulo()
    corredor = _CorredorFalso([0, 1])

    motivo = sc.correr_la_verja([], corredor=corredor)

    assert motivo == f"semilla {sc.SEMILLAS_DE_ACEPTACION[1]}"
    assert len(corredor.ordenes) == 2


def test_el_mensaje_del_rojo_dice_la_semilla_y_como_reproducirlo(capsys):
    """Un «tests fallando» a secas, con el orden aleatorio activo, no es accionable."""
    sc = _modulo()
    semilla = sc.SEMILLAS_DE_ACEPTACION[0]

    sc.correr_la_verja([], corredor=_CorredorFalso([1]))

    salida = capsys.readouterr().out
    assert f"--randomly-seed={semilla}" in salida, "no dice con qué semilla reproducirlo"
    assert "Reproducelo con:" in salida


def test_la_orden_de_reproducir_CONSERVA_los_extras(capsys):
    """H-09 de R2: la receta se escribía a mano en un `print` y perdía `--runslow`.

    O sea que ante el rojo de un test lento —justo el caso en que `--runslow` está
    puesto— imprimía una orden que **no ejecuta ese test**. El diagnóstico llevaba a un
    verde y a la conclusión de que el rojo era fantasma.

    El arreglo no fue añadir `--runslow` al `print`: fue que la orden impresa salga de
    `orden_de_pytest`, la misma que se ejecuta. Dos textos que hay que mantener a mano
    sincronizados terminan divergiendo; uno solo no puede.
    """
    sc = _modulo()

    sc.correr_la_verja(["--runslow"], corredor=_CorredorFalso([1]))

    salida = capsys.readouterr().out
    assert "--runslow" in salida, (
        "la orden de reproducción no lleva `--runslow`: con un test lento en rojo, "
        "ejecutarla daría verde y el rojo parecería un fantasma")


def test_toda_orden_lanza_en_paralelo():
    """Ya no se comprueba `--dist loadgroup`: la escotilla de grupos se retiró entera.

    Existía para que `test_guard_localizador.py` corriera en un solo worker, porque
    escribía sondas dentro de `core/` vivo. Desde que monta su árbol en `tmp_path` no hay
    nada que agrupar, y `tests/test_guard_aislamiento_paralelo.py` impide que vuelva a
    haberlo. Menos piezas: la marca, el flag y su guard se fueron juntos.
    """
    sc = _modulo()
    corredor = _CorredorFalso([0, 0])

    sc.correr_la_verja([], corredor=corredor)

    for orden in corredor.ordenes:
        i = orden.index("-n")
        assert orden[i + 1] == "auto", f"orden sin paralelismo: {orden}"


def test_durations_solo_en_la_primera_corrida():
    """Quince líneas de perfil por corrida son útiles; treinta en cada cierre son ruido."""
    sc = _modulo()
    corredor = _CorredorFalso([0, 0])

    sc.correr_la_verja([], corredor=corredor)

    con = [o for o in corredor.ordenes if any(a.startswith("--durations") for a in o)]
    assert len(con) == 1 and con[0] is corredor.ordenes[0]


def test_la_cobertura_solo_se_mide_en_la_primera_corrida():
    """Es la misma con cualquier orden; medirla dos veces solo cuesta los 8 s otra vez."""
    sc = _modulo()
    corredor = _CorredorFalso([0, 0])

    sc.correr_la_verja([], corredor=corredor)

    con_cov = [o for o in corredor.ordenes if "--cov=core" in o]
    assert len(con_cov) == 1 and con_cov[0] is corredor.ordenes[0]


def test_cobertura_del_diff_lee_el_porcentaje():
    sc = _modulo()
    salida = ("-------------\nDiff Coverage\nDiff: origin/main...HEAD\n-------------\n"
              "core/utils.py (100%)\n-------------\nTotal:   46 lines\n"
              "Missing: 3 lines\nCoverage: 93%\n-------------\n")
    assert sc.cobertura_del_diff(salida) == 93


def test_cobertura_del_diff_lee_un_porcentaje_DECIMAL():
    """R2 (H-08): `--total-percent-float` imprime `Coverage: 92.73%` y el parser devolvía
    `None`. Una medición perfectamente válida se presentaba como «no se pudo medir», y
    bastaba con que alguien cambiara un flag o subiera de versión."""
    sc = _modulo()
    assert sc.cobertura_del_diff("Coverage: 92.73%\n") == 92
    assert sc.cobertura_del_diff("Coverage: 100.0%\n") == 100


def test_cobertura_del_diff_con_DOS_resumenes_no_elige_el_primero():
    """Dos resúmenes no son una medición: no se sabe cuál es.

    R2 midió que `Coverage: 100%\\nCoverage: 0%` se leía como **100** porque `re.search`
    se queda con el primero. Ante la ambigüedad, la respuesta honesta es «no se pudo
    medir», no el que venga antes.
    """
    sc = _modulo()
    assert sc.cobertura_del_diff("Coverage: 100%\nCoverage: 0%\n") is None


def test_cobertura_del_diff_desconfia_de_un_proceso_que_FALLO():
    """Si `diff-cover` sale con error, lo que haya en stdout no es de fiar.

    R2: un corredor con `returncode=2` y `stdout='Coverage: 100%'` producía `[OK] 100%`.
    """
    sc = _modulo()
    assert sc.cobertura_del_diff("Coverage: 100%\n", 2) is None
    assert sc.cobertura_del_diff("Coverage: 100%\n", 0) == 100


def test_cobertura_del_diff_distingue_NO_PUDE_MEDIR_de_CERO():
    """La distinción que H-05 enseñó a golpes: «no pude medir» no es «está mal».

    Un diff que no toca código medido, un `coverage.xml` ausente o una rama base que git no
    conoce dan los tres una salida sin porcentaje. Devolver `0` ahí convertiría un hueco
    del instrumento en una acusación al autor — y el aviso diría «0%» sobre un diff
    perfectamente cubierto.
    """
    sc = _modulo()
    assert sc.cobertura_del_diff("No lines with coverage information in this diff.") is None
    assert sc.cobertura_del_diff("") is None
    assert sc.cobertura_del_diff("fatal: bad revision 'origin/main'") is None
    # Y el 0% REAL sí se lee como 0, que es lo que lo hace distinto de `None`.
    assert sc.cobertura_del_diff("Coverage: 0%\n") == 0


@dataclass
class _SalidaDeProceso:
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


def _diff_cover_falso(stdout: str = "", stderr: str = ""):
    return lambda *a, **kw: _SalidaDeProceso(stdout=stdout, stderr=stderr)


def _xml_presente(tmp_path) -> Path:
    x = tmp_path / "coverage.xml"
    x.write_text("<coverage/>", encoding="utf-8")
    return x


def test_aviso_de_cobertura_por_encima_del_umbral(tmp_path, capsys):
    sc = _modulo()
    sc._avisar_cobertura_del_diff(corredor=_diff_cover_falso("Coverage: 97%\n"),
                                  xml=_xml_presente(tmp_path))
    salida = capsys.readouterr().out
    assert "[OK] 97%" in salida
    assert "Son lineas que acabas de escribir" not in salida


def test_aviso_de_cobertura_por_debajo_dice_QUE_lineas(tmp_path, capsys):
    """Un porcentaje solo no es accionable: hay que decir dónde."""
    sc = _modulo()
    sc._avisar_cobertura_del_diff(
        corredor=_diff_cover_falso("scripts/x.py (50.0%): Missing lines 10-12\n"
                                   "Coverage: 50%\n"),
        xml=_xml_presente(tmp_path))
    salida = capsys.readouterr().out
    assert "[!] 50%" in salida
    assert "Missing lines 10-12" in salida
    assert "Son lineas que acabas de escribir" in salida


def test_aviso_de_cobertura_sin_xml_no_inventa_un_numero(tmp_path, capsys):
    sc = _modulo()
    sc._avisar_cobertura_del_diff(corredor=_diff_cover_falso("Coverage: 99%\n"),
                                  xml=tmp_path / "no_existe.xml")
    salida = capsys.readouterr().out
    assert "no hay coverage.xml" in salida
    assert "99%" not in salida, "usó el corredor pese a no haber medición"


def test_aviso_de_cobertura_cuando_NO_SE_PUEDE_MEDIR(tmp_path, capsys):
    """El caso que H-05 enseñó: no se puede decir «0%» cuando lo que pasa es que no se
    pudo mirar. Un cero acusa al autor; un «no se pudo medir» acusa al instrumento, que es
    lo que de verdad ocurrió."""
    sc = _modulo()
    sc._avisar_cobertura_del_diff(
        corredor=_diff_cover_falso(stderr="fatal: bad revision 'origin/main'"),
        xml=_xml_presente(tmp_path))
    salida = capsys.readouterr().out
    assert "no se pudo medir" in salida
    assert "0%" not in salida


def test_los_argumentos_extra_viajan(capsys):
    """`--runslow` lo añade `main()` cuando `core/anon/` está tocado. Si no llegara a la
    orden, la red de la anonimización dejaría de correr **en silencio**."""
    sc = _modulo()
    corredor = _CorredorFalso([0, 0])

    sc.correr_la_verja(["--runslow"], corredor=corredor)

    assert all("--runslow" in orden for orden in corredor.ordenes)
