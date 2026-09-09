"""Tests de `scripts/transcribir_audio.py` — las piezas puras, que es donde estuvo el bug.

El módulo se importa sin `faster-whisper` ni `sherpa-onnx` (sus `import` están dentro de
las funciones), así que estos tests corren en la suite normal del repo, con su venv.

El grupo que más vale es `TestAgruparPorTurno`: la primera versión agrupaba por segmento
del ASR y atribuía a un solo hablante lo que decían tres. Estos tests fallan con esa
versión y pasan con la de ahora.
"""
from __future__ import annotations

import pytest

from scripts import transcribir_audio as ta


class TestMmss:
    def test_formatea_minutos_y_segundos(self):
        assert ta.mmss(0) == "00:00"
        assert ta.mmss(61.4) == "01:01"
        assert ta.mmss(3599) == "59:59"

    def test_pasa_de_la_hora_sin_reiniciar(self):
        # Un juicio de dos horas: el minuto sigue creciendo, no se envuelve a 00.
        assert ta.mmss(3600) == "60:00"
        assert ta.mmss(7325) == "122:05"

    def test_un_negativo_no_produce_un_timestamp_absurdo(self):
        assert ta.mmss(-3) == "00:00"


class TestHablanteDe:
    TURNOS = [(0.0, 5.0, "HABLANTE_01"), (5.5, 9.0, "HABLANTE_02")]

    @pytest.mark.parametrize("t,esperado", [
        (0.0, "HABLANTE_01"), (2.5, "HABLANTE_01"), (5.0, "HABLANTE_01"),
        (5.5, "HABLANTE_02"), (9.0, "HABLANTE_02"),
    ])
    def test_dentro_de_un_turno(self, t, esperado):
        assert ta.hablante_de(self.TURNOS, t) == esperado

    def test_en_el_hueco_entre_turnos_no_inventa_hablante(self):
        assert ta.hablante_de(self.TURNOS, 5.2) is None

    def test_fuera_de_todo_turno(self):
        assert ta.hablante_de(self.TURNOS, 99.0) is None
        assert ta.hablante_de([], 1.0) is None


class TestSuavizar:
    """La costura de las fronteras. Cada caso es un defecto observado el 2026-09-09."""

    def test_palabra_huerfana_hereda_del_siguiente_no_del_anterior(self):
        # El corte del diarizador va desplazado, así que "Sí," (inicio del turno de 02)
        # cae en la cola de 01 y sale sin hablante. Debe ir a 02, no a 01.
        palabras = [(0.0, 1.0, "Hable.", "HABLANTE_01"),
                    (1.1, 1.3, "Sí,", None),
                    (1.4, 2.0, "firmé", "HABLANTE_02")]
        assert [p[3] for p in ta.suavizar(palabras)] == [
            "HABLANTE_01", "HABLANTE_02", "HABLANTE_02"]

    def test_huerfana_al_final_hereda_del_anterior_porque_no_hay_siguiente(self):
        palabras = [(0.0, 1.0, "Nada", "HABLANTE_03"), (1.1, 1.4, "más.", None)]
        assert [p[3] for p in ta.suavizar(palabras)] == ["HABLANTE_03", "HABLANTE_03"]

    def test_todas_huerfanas_se_quedan_en_none_sin_reventar(self):
        palabras = [(0.0, 1.0, "a", None), (1.0, 2.0, "b", None)]
        assert [p[3] for p in ta.suavizar(palabras)] == [None, None]

    def test_isla_de_una_palabra_va_al_hablante_que_viene_despues(self):
        # "Y" atribuida a 02 entre 01 y 03: es el arranque del turno de 03.
        palabras = [(0.0, 1.0, "Continúe.", "HABLANTE_01"),
                    (1.1, 1.2, "Y", "HABLANTE_02"),
                    (1.3, 2.0, "consta", "HABLANTE_03")]
        assert [p[3] for p in ta.suavizar(palabras)] == [
            "HABLANTE_01", "HABLANTE_03", "HABLANTE_03"]

    def test_no_toca_una_intervencion_corta_pero_legitima(self):
        # 02 dice una sola palabra ENTRE dos intervenciones del MISMO 01: es un turno
        # real (un "Sí" del testigo), no una frontera mal puesta. Debe conservarse.
        palabras = [(0.0, 1.0, "¿Firmó?", "HABLANTE_01"),
                    (1.1, 1.3, "Sí.", "HABLANTE_02"),
                    (1.4, 2.0, "Continúe.", "HABLANTE_01")]
        assert [p[3] for p in ta.suavizar(palabras)] == [
            "HABLANTE_01", "HABLANTE_02", "HABLANTE_01"]

    def test_conserva_tiempos_y_texto_intactos(self):
        palabras = [(0.0, 1.0, "hola", None), (1.0, 2.0, "adiós", "HABLANTE_01")]
        assert [(p[0], p[1], p[2]) for p in ta.suavizar(palabras)] == [
            (0.0, 1.0, "hola"), (1.0, 2.0, "adiós")]

    def test_lista_vacia(self):
        assert ta.suavizar([]) == []


class TestLineaRacha:
    def test_formato_citable(self):
        racha = [(65.0, 66.0, " No", "HABLANTE_03"), (66.0, 70.2, " es cierto.", "HABLANTE_03")]
        assert ta.linea_racha(racha) == (
            "- `[01:05–01:10]` **HABLANTE_03** · No es cierto.")

    def test_sin_hablante_lo_declara_en_vez_de_callarlo(self):
        assert "**HABLANTE_?**" in ta.linea_racha([(0.0, 1.0, "algo", None)])


class TestAgruparPorTurno:
    """La unidad de salida es el turno, no el segmento del ASR.

    Whisper devolvió un bloque de 27 s que cubría seis intervenciones de tres personas.
    Agrupar por segmento atribuía las seis a un solo hablante.
    """

    def test_tres_hablantes_alternando_dan_una_linea_por_intervencion(self):
        palabras = [
            (0.0, 1.0, "Se", "HABLANTE_01"), (1.0, 2.0, " abre.", "HABLANTE_01"),
            (2.5, 3.0, " Me", "HABLANTE_02"), (3.0, 4.0, " llamo.", "HABLANTE_02"),
            (4.5, 5.0, " Diga.", "HABLANTE_03"),
            (5.5, 6.0, " Firmé.", "HABLANTE_02"),
        ]
        lineas = ta.agrupar_por_turno(palabras)
        assert len(lineas) == 4, "una línea por cambio de hablante, no una por bloque"
        assert [l.split("**")[1] for l in lineas] == [
            "HABLANTE_01", "HABLANTE_02", "HABLANTE_03", "HABLANTE_02"]

    def test_el_texto_de_cada_turno_no_se_mezcla_con_el_de_otro(self):
        palabras = [(0.0, 1.0, "pago", "HABLANTE_01"),
                    (1.5, 2.0, " no pago", "HABLANTE_02")]
        lineas = ta.agrupar_por_turno(palabras)
        assert lineas[0].endswith("· pago")
        assert lineas[1].endswith("· no pago")

    def test_un_turno_seguido_no_se_parte(self):
        palabras = [(0.0, 1.0, "a", "HABLANTE_01"), (1.0, 2.0, " b", "HABLANTE_01"),
                    (2.0, 3.0, " c", "HABLANTE_01")]
        assert len(ta.agrupar_por_turno(palabras)) == 1

    def test_las_huerfanas_de_frontera_no_generan_lineas_de_una_palabra(self):
        # Reproduce el defecto real: la primera palabra de cada turno venía sin hablante.
        palabras = [
            (0.0, 1.0, "Hable.", "HABLANTE_01"),
            (1.1, 1.2, " Sí,", None), (1.3, 2.0, " firmé.", "HABLANTE_02"),
            (2.1, 2.2, " Y", None), (2.3, 3.0, " consta.", "HABLANTE_03"),
        ]
        lineas = ta.agrupar_por_turno(palabras)
        assert len(lineas) == 3
        assert lineas[1].endswith("· Sí, firmé."), "la huérfana va con SU turno"
        assert lineas[2].endswith("· Y consta.")

    def test_vacio(self):
        assert ta.agrupar_por_turno([]) == []


class TestLocalizarModelos:
    def _arbol_modelos(self, raiz):
        """Árbol sintético con los dos ficheros que la diarización necesita."""
        seg = raiz / ta._SEG_REL
        seg.parent.mkdir(parents=True, exist_ok=True)
        seg.write_bytes(b"onnx-falso")
        (raiz / ta._EMB_REL).write_bytes(b"onnx-falso")
        return raiz

    def test_encuentra_por_variable_de_entorno(self, tmp_path, monkeypatch):
        d = self._arbol_modelos(tmp_path / "modelos")
        monkeypatch.setenv(ta.ENV_MODELOS, str(d))
        assert ta.localizar_modelos() == d

    def test_devuelve_none_si_la_carpeta_esta_incompleta(self, tmp_path, monkeypatch):
        # Solo el modelo de segmentación: media instalación NO vale.
        seg = tmp_path / ta._SEG_REL
        seg.parent.mkdir(parents=True)
        seg.write_bytes(b"onnx-falso")
        monkeypatch.setenv(ta.ENV_MODELOS, str(tmp_path))
        monkeypatch.setattr(ta, "_MODELOS_DEFECTO", tmp_path / "no-existe")
        assert ta.localizar_modelos() is None

    def test_devuelve_none_si_no_hay_nada(self, tmp_path, monkeypatch):
        monkeypatch.delenv(ta.ENV_MODELOS, raising=False)
        monkeypatch.setattr(ta, "_MODELOS_DEFECTO", tmp_path / "no-existe")
        assert ta.localizar_modelos() is None

    def test_la_variable_apuntando_a_nada_cae_al_defecto(self, tmp_path, monkeypatch):
        d = self._arbol_modelos(tmp_path / "defecto")
        monkeypatch.setenv(ta.ENV_MODELOS, str(tmp_path / "fantasma"))
        monkeypatch.setattr(ta, "_MODELOS_DEFECTO", d)
        assert ta.localizar_modelos() == d


class TestHeaderSha:
    """La regex que da la idempotencia: si no engancha, se reprocesan 5 h de audio."""

    def test_engancha_la_linea_que_el_propio_script_escribe(self):
        sha = "a" * 64
        cabecera = f"- `origen_sha256`: `{sha}`\n- `bytes`: 1.000\n"
        m = ta.HEADER_SHA.search(cabecera)
        assert m and m.group(1) == sha

    def test_no_engancha_un_sha_de_otro_campo(self):
        assert ta.HEADER_SHA.search(f"- `text_sha256`: `{'b' * 64}`") is None

    def test_no_engancha_algo_que_no_sea_un_sha256(self):
        assert ta.HEADER_SHA.search("- `origen_sha256`: `cafe`") is None


class TestFicherosDe:
    def test_un_fichero_suelto_se_devuelve_tal_cual(self, tmp_path):
        f = tmp_path / "nota.opus"
        f.write_bytes(b"x")
        assert ta.ficheros_de(f) == [f]

    def test_una_carpeta_recorre_recursivo_y_filtra_por_extension(self, tmp_path):
        (tmp_path / "sub").mkdir()
        for n in ("a.opus", "b.mp4", "c.pdf", "sub/d.m4a", "sub/e.docx"):
            (tmp_path / n).write_bytes(b"x")
        nombres = [p.name for p in ta.ficheros_de(tmp_path)]
        assert nombres == ["a.opus", "b.mp4", "d.m4a"], "orden estable y sin no-audio"

    def test_mayusculas_en_la_extension(self, tmp_path):
        (tmp_path / "GRABACION.MP4").write_bytes(b"x")
        assert len(ta.ficheros_de(tmp_path)) == 1

    def test_carpeta_sin_audio_devuelve_lista_vacia(self, tmp_path):
        (tmp_path / "escrito.pdf").write_bytes(b"x")
        assert ta.ficheros_de(tmp_path) == []


class TestExtensiones:
    def test_cubre_lo_que_llega_de_verdad(self):
        # `.opus` es el códec de las notas de voz de WhatsApp y `.mp4` el de sus vídeos:
        # los 67 ficheros de W-02USSI son 65 `.opus` + 2 `.mp4`.
        assert ".opus" in ta.EXTS_AUDIO
        assert ".mp4" in ta.EXTS_VIDEO
        assert ta.EXTS >= ta.EXTS_AUDIO | ta.EXTS_VIDEO

    def test_no_se_solapan(self):
        assert not (ta.EXTS_AUDIO & ta.EXTS_VIDEO)

    def test_todas_empiezan_por_punto_y_van_en_minuscula(self):
        for e in ta.EXTS:
            assert e.startswith(".") and e == e.lower()


class TestMain:
    def test_entrada_inexistente_sale_con_2_y_no_carga_ningun_modelo(self, tmp_path, capsys):
        assert ta.main([str(tmp_path / "fantasma.opus")]) == 2
        assert "no existe" in capsys.readouterr().err

    def test_carpeta_sin_audio_sale_con_2(self, tmp_path, capsys):
        (tmp_path / "x.pdf").write_bytes(b"x")
        assert ta.main([str(tmp_path)]) == 2
        assert "ningún audio" in capsys.readouterr().err

    def test_diarizar_sin_modelos_aborta_en_alto_antes_de_procesar(
            self, tmp_path, monkeypatch, capsys):
        """Fallo de VALERO: avisar ANTES, no dejar 67 transcripciones sin hablantes."""
        (tmp_path / "a.opus").write_bytes(b"x")
        monkeypatch.delenv(ta.ENV_MODELOS, raising=False)
        monkeypatch.setattr(ta, "_MODELOS_DEFECTO", tmp_path / "no-existe")
        assert ta.main([str(tmp_path), "--diarizar"]) == 2
        err = capsys.readouterr().err
        assert "--diarizar" in err and "INSTALACION_ASR" in err

    def test_el_modelo_por_defecto_es_turbo(self):
        # `small` sirve para triaje pero es flojo en catalán, y el corpus es bilingüe.
        assert ta._construir_parser().parse_args(["x"]).modelo == "large-v3-turbo"

    def test_no_diariza_salvo_que_se_pida(self):
        # Las notas de voz son de un hablante y su autor consta en el chat: diarizarlas
        # solo puede empeorar la atribución.
        assert ta._construir_parser().parse_args(["x"]).diarizar is False


def test_el_limite_del_instrumento_va_escrito_en_cada_transcripcion():
    """Una transcripción ASR no es peritaje, y eso tiene que viajar con el documento."""
    assert "no peritaje" in ta.LIMITE
    assert "PROVISIONALES" in ta.NOTA_DIARIZACION
