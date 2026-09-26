"""La población de la sala de lectura (MEJORAS #316): todo lo de `00_Input` tiene fila o
declaración.

Medido el 2026-09-26 con la C3 por identidad de `verificar_apertura`: en 14 de 23
expedientes, documentos que la sala de máquina procesó no llegaron al catálogo. En W-02Y2J6
—audiencia previa el 14/10— eran siete notas de voz de WhatsApp, zips, vCards y un vídeo, y
**no figuraban en ninguna parte del manifiesto**: la ejecución de la skill no los listó.
Nada lo comprobaba. Ahora el verify de la propia skill lo mira, con la cobertura que ya
recibía para las fechas.

Las exclusiones automáticas son tres, y las tres son reglas de su productor: el registro de
protocolo por ubicación (`core/intake_control`), el zip crudo de WhatsApp junto a su chat
(`emparejar_exports_whatsapp`) y la firma incrustada que `email_export` marca y nombra con
`_firma_`. Lo demás tiene fila o línea en `## No copiados`.

Ningún test escribe fuera de `tmp_path`.
"""
from importlib import import_module
from pathlib import Path
import hashlib
import json
import sys

import pytest

_SCRIPTS = Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"
sys.path.insert(0, str(_SCRIPTS))
verificar_sala = import_module("verificar_sala")
preclasificar = import_module("preclasificar")

_A, _B = "a" * 64, "b" * 64


def _fila(ruta, sha=""):
    return {"sha256": sha, "ruta_original": ruta, "nombre_canonico": "x", "tipo": "", "fecha": "",
            "parte": "", "parent_id": ""}


def _cob(rel, sha="", **kw):
    return {"slug": rel, "rel_path": rel, "sha256": sha, **kw}


# --- Las reglas automáticas ------------------------------------------------------------


def test_la_firma_de_correo_es_la_que_email_export_nombra_en_un_lote_de_correo():
    assert preclasificar.es_firma_de_correo("2026-09-23_email_01/2025-01-02_aviso/_firma_image.png")
    assert preclasificar.es_firma_de_correo("00_Input\\03_Email\\hilo\\_firma_logo.jpg")


@pytest.mark.parametrize("ruta", [
    "01_Drive EV/Fotos/_firma_image.png",                 # fuera de un lote de correo
    "2026-09-23_whatsapp_01/chat/_firma_image.png",       # lote de WhatsApp, no de correo
    "2026-09-23_email_01/2025-01-02_aviso/firma.png",     # sin el prefijo del productor
    "2026-09-23_email_01/_firma_image.png" + "x",         # sigue siendo firma: prefijo y lote
])
def test_la_firma_de_correo_no_se_adivina_por_el_nombre_en_otro_sitio(ruta):
    """CONTROL POSITIVO: un `_firma_` fuera de un lote de correo es un documento del cliente,
    y un fichero de correo sin el prefijo es un adjunto que alguien envió."""
    esperado = ruta.startswith("2026-09-23_email_01/_firma_")
    assert preclasificar.es_firma_de_correo(ruta) is esperado


def test_prefijo_de_firma_sin_deriva_con_email_export():
    from core.email_export import PREFIJO_FIRMA
    assert preclasificar.PREFIJO_FIRMA_CORREO == PREFIJO_FIRMA


def test_el_registro_de_protocolo_de_la_skill_es_COPIA_EXACTA_del_de_core():
    """La skill corre en Cowork, sin `core/`, así que lleva su copia del registro por
    ubicación. Byte a byte: cualquier cambio en `core/intake_control.py` pone esto en rojo
    hasta que se vuelva a copiar."""
    core = (Path(__file__).parent.parent / "core" / "intake_control.py").read_bytes()
    skill = (_SCRIPTS / "intake_control.py").read_bytes()
    assert skill == core


# --- La verja de población ------------------------------------------------------------


def test_una_fuente_SIN_fila_ni_declaracion_es_un_problema():
    """W-02Y2J6: la nota de voz estaba en la cobertura y en ningún sitio del manifiesto."""
    audio = "2026-09-25_whatsapp_03/Chat/00000028-AUDIO-2025-03-22-17-11-57.opus"
    problemas = verificar_sala.problemas_poblacion(
        [_fila("2026-09-25_whatsapp_03/Chat/_chat.txt", _A)],
        [_cob("2026-09-25_whatsapp_03/Chat/_chat.txt", _A), _cob(audio, _B)], [])
    assert len(problemas) == 1 and audio in problemas[0], problemas
    assert "No copiados" in problemas[0]


def test_una_fuente_con_FILA_por_ruta_o_por_sha256_no_es_problema():
    """La ruta del manifiesto puede venir con `00_Input\\` y barras invertidas; y una copia
    en otra carpeta es el `dedup_por_sha`: está en la sala por su contenido."""
    filas = [_fila("00_Input\\01_Drive EV\\a.pdf", _A)]
    cob = [_cob("01_Drive EV/a.pdf", _A), _cob("01_Drive EV/OTRA/a.pdf", _A)]
    assert verificar_sala.problemas_poblacion(filas, cob, []) == []


def test_una_fuente_DECLARADA_en_no_copiados_no_es_problema():
    declaradas = [{"motivo": "excluido", "ruta": "00_Input\\2026-09-23_email_01\\c\\x.zip",
                   "detalle": "crudo de un chat ya extraído"}]
    problemas = verificar_sala.problemas_poblacion(
        [], [_cob("2026-09-23_email_01/c/x.zip", _B)], declaradas)
    assert problemas == []


def test_las_tres_reglas_de_productor_no_piden_declaracion():
    cob = [_cob("_caso.md"),                                             # protocolo, raíz
           _cob("2026-09-10_email_01/_manifiesto.yaml"),                 # protocolo, lote
           _cob("2026-09-25_whatsapp_01/Chat/_chat.txt", _A),
           _cob("2026-09-25_whatsapp_01/Chat/_export_original.zip", _B),  # crudo con su chat
           _cob("2026-09-23_email_01/aviso/_firma_image.png", _B)]       # firma de email_export
    filas = [_fila("2026-09-25_whatsapp_01/Chat/_chat.txt", _A)]
    assert verificar_sala.problemas_poblacion(filas, cob, []) == []


def test_un_homonimo_de_protocolo_o_un_zip_crudo_sin_chat_SI_piden_fila():
    """CONTROL POSITIVO de las reglas: por ubicación, y con las dos condiciones de la skill."""
    cob = [_cob("CarpetaRara/_manifiesto.yaml", _A),
           _cob("2026-09-25_whatsapp_02/Chat/_export_original.zip", _B)]
    problemas = verificar_sala.problemas_poblacion([], cob, [])
    assert len(problemas) == 2, problemas


def test_una_fila_de_cobertura_sin_rel_path_no_se_da_por_contrastada():
    problemas = verificar_sala.problemas_poblacion([], [{"slug": "x", "sha256": _A}], [])
    assert problemas and "rel_path" in problemas[0], problemas


# --- El CLI: la verja se corre en el verify de la skill -------------------------------


_CABECERA = ("| sha256 | ruta_original | nombre_canonico | tipo | fecha | parte | parent_id |\n"
             "|---|---|---|---|---|---|---|\n")


def _sala(tmp_path, manifiesto, cobertura):
    sala = tmp_path / "Sala lectura"
    sala.mkdir()
    contenido = b"el chat"
    (sala / "2025-03-01_chat.txt").write_bytes(contenido)
    sha = hashlib.sha256(contenido).hexdigest()
    (sala / "_MANIFIESTO.md").write_text(
        _CABECERA + f"| {sha} | 2026-09-25_whatsapp_03/Chat/_chat.txt | 2025-03-01_chat.txt | "
        f"08. PENDIENTE DE CLASIFICAR | 2025-03-01 | propietario |  |\n" + manifiesto,
        encoding="utf-8")
    cob = tmp_path / "_cobertura.json"
    cob.write_text(json.dumps([_cob("2026-09-25_whatsapp_03/Chat/_chat.txt", sha)] + cobertura),
                   encoding="utf-8")
    return sala, cob


def test_cli_con_cobertura_FALLA_si_falta_una_fuente(tmp_path, capsys):
    audio = "2026-09-25_whatsapp_03/Chat/00000028-AUDIO-2025-03-22-17-11-57.opus"
    sala, cob = _sala(tmp_path, "", [_cob(audio, _B)])
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--cobertura", str(cob)]) == 1
    assert audio in capsys.readouterr().out


def test_cli_con_la_fuente_declarada_en_no_copiados_da_ok(tmp_path, capsys):
    audio = "2026-09-25_whatsapp_03/Chat/00000028-AUDIO-2025-03-22-17-11-57.opus"
    sala, cob = _sala(tmp_path, f"\n## No copiados\n\n- excluido: `{audio}` — prueba del test\n",
                      [_cob(audio, _B)])
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--cobertura", str(cob)]) == 0


def test_cli_una_declaracion_en_TEXTO_LIBRE_es_un_error(tmp_path, capsys):
    sala, cob = _sala(tmp_path, "\n## No copiados\n\n- excluidos: los zips del correo\n", [])
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--cobertura", str(cob)]) == 1
    assert "No copiados" in capsys.readouterr().out


def test_cli_sin_cobertura_DICE_que_no_ha_contrastado_la_poblacion(tmp_path, capsys):
    """No poder mirar no es «no hay»: sin `--cobertura`, el OK no puede sonar a completo."""
    sala, _ = _sala(tmp_path, "", [])
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 0
    assert "sin --cobertura" in capsys.readouterr().out
