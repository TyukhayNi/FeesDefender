"""La población de la sala de lectura (MEJORAS #316): todo lo de `00_Input` tiene fila o
declaración.

Medido el 2026-09-26 con la C3 por identidad de `verificar_apertura`: en 14 de 23
expedientes, documentos que la sala de máquina procesó no llegaron al catálogo. En W-02Y2J6
—audiencia previa el 14/10— eran siete notas de voz de WhatsApp, zips, vCards y un vídeo, y
**no figuraban en ninguna parte del manifiesto**: la ejecución de la skill no los listó.
Nada lo comprobaba. Ahora el verify de la propia skill lo mira, con la cobertura que ya
recibía para las fechas.

Las exclusiones automáticas son dos, y las dos son reglas de su productor: el registro de
protocolo por ubicación (`core/intake_control`) y el zip crudo que el intake de WhatsApp
deja junto a su chat (`emparejar_exports_whatsapp`). La firma que `email_export` marca con
`_firma_` era la tercera y dejó de serlo en la R1 (H-01): el productor la marca, no la
descarta. Lo demás da cuenta de sí por una fila —su ruta, o su sha256 si es un duplicado—
o por una línea `excluido` en `## No copiados`.

Ningún test escribe fuera de `tmp_path`.
"""
from importlib import import_module
from pathlib import Path
import hashlib
import json
import sys

_SCRIPTS = Path(__file__).parent.parent / ".claude/skills/organizar-sala-lectura/scripts"
sys.path.insert(0, str(_SCRIPTS))
verificar_sala = import_module("verificar_sala")

_A, _B = "a" * 64, "b" * 64


def _sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _relleno(original: bytes) -> bytes:
    """`original` con la cola de ceros de `MEJORAS #225` hasta el siguiente múltiplo de 512."""
    return original + bytes(512 - len(original) % 512)


def _fila(ruta, sha=""):
    return {"sha256": sha, "ruta_original": ruta, "nombre_canonico": "x", "tipo": "", "fecha": "",
            "parte": "", "parent_id": ""}


def _cob(rel, sha="", **kw):
    return {"slug": rel, "rel_path": rel, "sha256": sha, **kw}


# --- Las reglas automáticas ------------------------------------------------------------


def test_la_firma_de_correo_es_un_adjunto_mas_y_pide_fila_o_linea():
    """R1/H-01 del #408: la primera versión dispensaba de fila al `_firma_*` de un lote de
    correo. Pero `email_export` lo MARCA, no lo descarta —«marca, no esconde», decisión de
    Nikolai del 2026-09-06, después de que un revisor colara una aceptación de honorarios
    escaneada que el filtro de firmas tiraba—, y el prefijo tampoco dice quién puso el nombre.
    La firma es un adjunto de su correo: fila, o una línea `excluido` con su motivo."""
    firma = "2026-09-23_email_01/2025-01-02_aviso/_firma_image.png"
    problemas = verificar_sala.problemas_poblacion([], [_cob(firma, _B)], [])
    assert len(problemas) == 1 and firma in problemas[0], problemas
    declarada = [{"motivo": "excluido", "ruta": firma, "detalle": "logotipo sin texto"}]
    assert verificar_sala.problemas_poblacion([], [_cob(firma, _B)], declarada) == []
    assert verificar_sala.problemas_poblacion([_fila(firma, _B)], [_cob(firma, _B)], []) == []


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


def test_una_fuente_con_FILA_por_su_ruta_no_es_problema():
    """La ruta del manifiesto puede venir con `00_Input\\` y barras invertidas. La fila no
    lleva sha256 a propósito: aquí da cuenta la RUTA, sola."""
    filas = [_fila("00_Input\\01_Drive EV\\a.pdf")]
    assert verificar_sala.problemas_poblacion(filas, [_cob("01_Drive EV/a.pdf", _A)], []) == []


def test_un_duplicado_por_sha256_no_necesita_fila_ni_linea():
    """Una copia en otra carpeta es el `dedup_por_sha`: su contenido está en la sala, y eso lo
    comprueba la verja sola, por el sha256. No se declara: un hecho que se puede medir no se
    acredita diciéndolo (R1/H-04 del #408)."""
    filas = [_fila("01_Drive EV/a.pdf", _A)]
    cob = [_cob("01_Drive EV/a.pdf", _A), _cob("2026-09-23_email_01/c/a.pdf", _A)]
    assert verificar_sala.problemas_poblacion(filas, cob, []) == []


def test_una_linea_duplicado_NO_da_cuenta_si_su_contenido_no_esta_en_ninguna_fila():
    """R1/H-09 del #408: si «duplicado» contara como declaración, bastaría escribirlo para
    sacar un documento de la sala. Lo que da cuenta de un duplicado es su sha256 en una fila."""
    declarada = [{"motivo": "duplicado", "ruta": "2026-09-23_email_01/c/b.pdf",
                  "detalle": "de `01_Drive EV/a.pdf`"}]
    problemas = verificar_sala.problemas_poblacion(
        [_fila("01_Drive EV/a.pdf", _A)],
        [_cob("01_Drive EV/a.pdf", _A), _cob("2026-09-23_email_01/c/b.pdf", _B)], declarada)
    assert len(problemas) == 1 and "2026-09-23_email_01/c/b.pdf" in problemas[0], problemas
    assert "duplicado" in problemas[0], problemas


def test_una_copia_con_el_relleno_de_225_da_cuenta_por_su_contenido(tmp_path):
    """El pull de Drive dejaba copias con una cola de ceros (`MEJORAS #225`): su sha256 no es
    el del original, pero su contenido está en la sala. Con el `00_Input` a mano la verja lo
    mide como C2 —un prefijo cuyo sha256 está en una fila— y no pide línea. Sin él no se
    puede medir, y no se da por visto."""
    original = b"encargo firmado"
    inp = tmp_path / "00_Input"
    (inp / "2026-09-23_email_01" / "c").mkdir(parents=True)
    copia = "2026-09-23_email_01/c/encargo.pdf"
    (inp / copia).write_bytes(_relleno(original))
    filas = [_fila("01_Drive EV/encargo.pdf", _sha(original))]
    cob = [_cob("01_Drive EV/encargo.pdf", _sha(original)), _cob(copia, _sha(_relleno(original)))]
    assert verificar_sala.problemas_poblacion(filas, cob, [], input_dir=inp) == []
    assert len(verificar_sala.problemas_poblacion(filas, cob, [])) == 1


def test_una_fila_con_la_ruta_de_la_fuente_y_otro_sha256_la_contradice():
    """R1/H-03 del #408: la unidad es el PAR ruta/sha256 de cada fila, como en la C3. Partido
    en dos conjuntos, una fila `a.pdf` con el hash de otro documento daba cuenta de `a.pdf`
    por su ruta: el sitio era el suyo y el contenido no."""
    problemas = verificar_sala.problemas_poblacion([_fila("a.pdf", _B)], [_cob("a.pdf", _A)], [])
    assert len(problemas) == 1 and "a.pdf" in problemas[0], problemas
    assert "contradice" in problemas[0], problemas


def test_una_fila_contradictoria_no_acredita_por_su_hash_a_otra_fuente():
    """La otra mitad del par: la fila `a.pdf` con el sha256 de `b.pdf` tampoco da cuenta de
    `b.pdf` por su contenido. Una fila que contradice no acredita a nadie."""
    problemas = verificar_sala.problemas_poblacion(
        [_fila("a.pdf", _B)], [_cob("a.pdf", _A), _cob("b.pdf", _B)], [])
    assert any("b.pdf" in p and "contradice" not in p for p in problemas), problemas


def test_una_fila_md5_da_cuenta_de_su_fuente_por_la_ruta():
    """CONTROL: el Modo 3 admite `md5:<hash>` en la columna sha256 (Paso 4). No es un sha256,
    así que no contradice nada: da cuenta de su fuente por la ruta, y solo por ella."""
    filas = [_fila("01_Drive EV/video.mp4", "md5:" + "c" * 32)]
    assert verificar_sala.problemas_poblacion(filas, [_cob("01_Drive EV/video.mp4", _A)],
                                              []) == []


def test_una_fuente_DECLARADA_en_no_copiados_no_es_problema():
    declaradas = [{"motivo": "excluido", "ruta": "00_Input\\2026-09-23_email_01\\c\\x.zip",
                   "detalle": "crudo de un chat ya extraído"}]
    problemas = verificar_sala.problemas_poblacion(
        [], [_cob("2026-09-23_email_01/c/x.zip", _B)], declaradas)
    assert problemas == []


def test_una_ruta_con_fila_y_declarada_no_copiada_es_una_contradiccion():
    """La sección se llama «No copiados»: si la ruta tiene fila, se copió, y una de las dos
    cosas que dice el manifiesto es falsa."""
    declarada = [{"motivo": "excluido", "ruta": "01_Drive EV/a.pdf", "detalle": "ajeno"}]
    problemas = verificar_sala.problemas_poblacion(
        [_fila("01_Drive EV/a.pdf", _A)], [_cob("01_Drive EV/a.pdf", _A)], declarada)
    assert len(problemas) == 1 and "01_Drive EV/a.pdf" in problemas[0], problemas


def test_la_ruta_de_la_cobertura_no_pierde_un_00_Input_del_cliente():
    """R1/H-06 del #408: la `rel_path` de la cobertura ya es relativa a `00_Input/`, así que su
    primer componente es del cliente. Si entregó una carpeta llamada `00_Input`, recortarla
    convertía `00_Input/_caso.md` en el `_caso.md` de la raíz —protocolo— y dejaba de pedir
    fila. El prefijo solo se le quita a la ruta del MANIFIESTO, que sí lo lleva."""
    problemas = verificar_sala.problemas_poblacion([], [_cob("00_Input/_caso.md", _A)], [])
    assert len(problemas) == 1 and "00_Input/_caso.md" in problemas[0], problemas


def test_las_dos_reglas_de_productor_no_piden_declaracion():
    cob = [_cob("_caso.md"),                                             # protocolo, raíz
           _cob("2026-09-10_email_01/_manifiesto.yaml"),                 # protocolo, lote
           _cob("2026-09-25_whatsapp_01/Chat/_chat.txt", _A),
           _cob("2026-09-25_whatsapp_01/Chat/_export_original.zip", _B)]  # crudo con su chat
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


def test_cli_sin_cobertura_FALLA_salvo_con_sin_cobertura(tmp_path, capsys):
    """R1/H-02 del #408: el primer diseño avisaba y devolvía 0, así que quien mirase el código
    de salida daba por contrastada una población que nadie había mirado. Sin cobertura el
    verify falla; `--sin-cobertura` —una sala sin sala de máquina— da un OK que dice PARCIAL."""
    sala, _ = _sala(tmp_path, "", [])
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 1
    assert "--sin-cobertura" in capsys.readouterr().out
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--sin-cobertura"]) == 0
    assert "PARCIAL" in capsys.readouterr().out


def test_cli_una_cobertura_que_no_existe_o_no_es_una_lista_es_un_error_de_uso(tmp_path):
    sala, cob = _sala(tmp_path, "", [])
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--cobertura",
                                str(tmp_path / "no_existe.json")]) == 2
    cob.write_text('{"no": "es una lista"}', encoding="utf-8")
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--cobertura", str(cob)]) == 2


def _en_su_sitio(tmp_path, cobertura):
    """La sala y la sala de máquina donde el layout del expediente las pone: hermanas dentro
    de `01_Procesado/` (`SKILL.md` §estructura)."""
    proc = tmp_path / "01_Procesado"
    proc.mkdir()
    sala, cob = _sala(proc, "", cobertura)
    sm = proc / "02_Sala de máquina"
    sm.mkdir()
    cob.replace(sm / "_cobertura.json")
    return sala


def test_cli_deduce_la_cobertura_de_la_sala_de_maquina_hermana(tmp_path, capsys):
    """Si la cobertura está donde el layout la pone, se usa sin que nadie tenga que acordarse
    de pasarla: el paso que se olvida es justo el que la verja no puede permitirse."""
    audio = "2026-09-25_whatsapp_03/Chat/00000028-AUDIO-2025-03-22-17-11-57.opus"
    sala = _en_su_sitio(tmp_path, [_cob(audio, _B)])
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 1
    assert audio in capsys.readouterr().out


def test_cli_mide_el_relleno_con_el_00_Input_del_layout(tmp_path, capsys):
    """La costura por defecto, sin inyectar nada: el verify deduce el `00_Input` del caso
    —hermano de `01_Procesado/`— y la copia con relleno de la sala no es un problema."""
    copia = "2026-09-23_email_01/c/_chat.txt"
    (tmp_path / "00_Input" / "2026-09-23_email_01" / "c").mkdir(parents=True)
    (tmp_path / "00_Input" / copia).write_bytes(_relleno(b"el chat"))
    sala = _en_su_sitio(tmp_path, [_cob(copia, _sha(_relleno(b"el chat")))])
    assert verificar_sala.main(["verificar_sala.py", str(sala)]) == 0, capsys.readouterr().out


def test_cli_sin_cobertura_con_una_cobertura_presente_es_un_error(tmp_path, capsys):
    """Renunciar a contrastar no vale cuando hay con qué: `--sin-cobertura` es para la sala
    que no tiene sala de máquina, no para saltarse la que sí la tiene."""
    sala = _en_su_sitio(tmp_path, [])
    assert verificar_sala.main(["verificar_sala.py", str(sala), "--sin-cobertura"]) == 2
    assert "--sin-cobertura, pero hay cobertura" in capsys.readouterr().out
