"""Arnés de mutación de P6 — la identidad de una parte, la ficha y las actuaciones.

Mismo contrato que `tests/_mutantes_p4.py`, **incluidas sus dos correcciones**, que son del
arnés y no de la pieza que revisaba: la restauración se arma ANTES de mutar (un fallo al
escribir dejaba el árbol mutado) y el `rc=4` de pytest —«el test no existe»— se distingue de
un rojo, porque leerlo como «ya estaba rojo» manda a investigar un defecto inexistente.

Dos cosas por mutante, y la segunda es la que importa:

1. que el mutante **mate al test al que se le apunta**, y
2. que ese test estuviera **verde antes de mutar**.

Sin la segunda, un mutante que muere por un test cualquiera cuenta como muerto y la guarda que
venía a fijar puede no haber mordido nunca.

No es un test de pytest y no corre en la suite (el nombre empieza por `_`): muta ficheros del
árbol. Se ejecuta a mano, **con el árbol limpio**:

    python -m tests._mutantes_p6
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

REL = "core/sudespacho_relations.py"
FICHA = "core/crm_ficha.py"
ACT = "core/sudespacho_actuaciones.py"
CLI = "scripts/crm_ficha.py"
T_71 = "tests/test_resolver_parte_aper71.py"
T_63 = "tests/test_crm_ficha_n_contrarios.py"
T_ACT = "tests/test_sudespacho_actuaciones.py"
T_R2 = "tests/test_sudespacho_actuaciones_r2.py"
T_R3 = "tests/test_sudespacho_actuaciones_r3.py"
VAL = "core/crm_ficha_validacion.py"

#: (nombre, fichero a mutar, texto original, texto mutado, test que DEBE ponerse rojo).
MUTANTES: list[tuple[str, str, str, str, str]] = [
    # --- Pieza 2: la identidad de una parte -----------------------------------------
    ("M01 [H-01] un documento vuelve a tener DOS estados", REL,
     '    return "utilizable" if _canonizar_documento(valor) else "no_interpretable"',
     '    return "utilizable"',
     f"{T_71}::test_h01_un_nif_no_interpretable_no_cae_a_la_politica_de_email"),

    ("M02 [H-01] el NIF no interpretable vuelve a caer a la política de email", REL,
     '    if estado_nif == "no_interpretable":',
     "    if False:",
     f"{T_71}::test_h01_un_nif_no_interpretable_no_cae_a_la_politica_de_email"),

    ("M03 [H-03] la multiplicidad del email vuelve a tapar al NIF único", REL,
     "    if len(ids_nif) == 1:\n        unico = next(iter(ids_nif))",
     "    if len(ids_nif) == 1 and len(ids_mail) <= 1:\n        unico = next(iter(ids_nif))",
     f"{T_71}::test_h03_el_nif_unico_manda_aunque_el_email_devuelva_varias"),

    ("M04 el NIF único fuera del buzón deja de ser conflicto", REL,
     "        if ids_mail and unico not in ids_mail:",
     "        if False:",
     f"{T_71}::test_el_nif_unico_fuera_del_conjunto_del_email_sigue_siendo_conflicto"),

    ("M05 [H-02] la comparación de documentos vuelve a ser textual", REL,
     '        if estado == "utilizable" and _canonizar_documento(suyo) != mio:',
     '        if estado == "utilizable" and suyo != nif:',
     f"{T_71}::test_h02_un_nif_igual_escrito_de_otra_forma_para_en_vez_de_duplicar"),

    ("M06 una ficha del buzón sin documento deja de parar: se crea igual", REL,
     '        return ResolucionParte(motivo=(\n            f"la ficha {fid} comparte el email y no tiene un documento comparable',
     '        continue\n        return ResolucionParte(motivo=(\n            f"la ficha {fid} comparte el email y no tiene un documento comparable',
     f"{T_71}::test_la_ficha_del_buzon_sin_nif_para_en_vez_de_crear"),

    ("M07 la consulta por email deja de pedir el documento", REL,
     "                          properties=(prop_nif,), limite=_LIMITE_BUZON)",
     "                          limite=_LIMITE_BUZON)",
     f"{T_71}::test_la_consulta_por_email_pide_tambien_el_nif"),

    ("M08 `resuelta` deja de mirar el motivo", REL,
     "        return not (self.conflicto or self.ambiguo or self.sin_comprobar or self.motivo)",
     "        return not (self.conflicto or self.ambiguo or self.sin_comprobar)",
     f"{T_71}::test_h01_un_nif_no_interpretable_no_cae_a_la_politica_de_email"),

    ("M09 el error vuelve a hablar de VARIAS fichas para un motivo que no lo es", REL,
     "    if r.motivo:\n        # **El mensaje tiene que decir la verdad.**",
     "    if False:\n        # **El mensaje tiene que decir la verdad.**",
     f"{T_71}::test_el_error_de_un_nif_no_interpretable_no_habla_de_varias_fichas"),

    ("M10 la consulta fallida pierde su precedencia", REL,
     "    if sin:\n        return ResolucionParte(sin_comprobar=tuple(sin))",
     "    if False:\n        return ResolucionParte(sin_comprobar=tuple(sin))",
     f"{T_71}::test_una_consulta_fallida_manda_sobre_todo_lo_demas"),

    # --- Pieza 3: la ficha ------------------------------------------------------------
    # Re-apuntado en la Task 2 de crm_ficha (plan rev. 2): la comprobación de elementos vive
    # ahora en `validar_ficha`, que valida la colección entera antes de construir; la de
    # `_contrarios_de` sería código muerto y haría sobrevivir a cualquier mutante de las dos.
    ("M11 [H-08] un elemento inválido deja de abortar con su índice", FICHA,
     '                  else [f"contrario[{i}]: tiene que ser un mapping, y es {_forma(e)}"])',
     "                  else [])",
     f"{T_63}::test_un_elemento_invalido_aborta_con_su_indice"),

    ("M12 una lista deja de leerse entera: solo el primero", FICHA,
     "    return [_contrario_de(e) for e in raw]",
     "    return [_contrario_de(raw[0])] if raw else []",
     f"{T_63}::test_una_lista_de_dos_contrarios_produce_dos"),

    ("M13 el CLI vuelve a vincular solo el primer contrario", CLI,
     "        for contrario in ficha.contrarios:",
     "        for contrario in ficha.contrarios[:1]:",
     "tests/test_crm_ficha_cli.py::test_el_cli_vincula_TODOS_los_contrarios_no_solo_el_primero"),

    # --- Pieza 1: las actuaciones -----------------------------------------------------
    ("M14 el paso 1 colapsa «no pude mirar» en «no aplica»", ACT,
     '        return IdPredefinido("sin_comprobar", motivo=f"HTTP {r.status_code}")',
     '        return IdPredefinido("no_aplica", motivo=f"HTTP {r.status_code}")',
     f"{T_ACT}::test_una_consulta_fallida_no_es_ausencia"),

    ("M15 el paso 1 colapsa «cero filas» en «no aplica»", ACT,
     '        return IdPredefinido("sin_filas", motivo=(\n'
     '            f"ninguna de las {len(filas)} fila(s) que devolvió el filtro tiene el asunto "\n'
     '            f"{pedido!r} exacto: heredar el id de una variante sería inventarlo"))',
     '        return IdPredefinido("no_aplica", motivo="")',
     f"{T_ACT}::test_cero_filas_no_es_lo_mismo_que_filas_sin_campo"),

    ("M17 [H-06] no poder leer el destino pasa por acreditarlo", ACT,
     '        raise DestinoNoAcreditado(\n            f"no se pudo leer {elemento}/{exp_id} (HTTP {r.status_code}). No se escribe nada.")',
     '        return Destino(elemento=elemento, exp_id=str(exp_id), evidencia="(no leido)")',
     f"{T_ACT}::test_un_destino_que_no_se_puede_leer_tampoco_se_acredita"),

    ("M18 [H-04] el recibo pierde el id de la actuación creada", ACT,
     "    recibo = dict(act_id=act_id, elemento=destino.elemento, exp_id=destino.exp_id)",
     "    recibo = dict(act_id=None, elemento=destino.elemento, exp_id=destino.exp_id)",
     f"{T_ACT}::test_si_el_vinculo_falla_el_recibo_conserva_el_id_creado"),

    ("M19 [H-04] reanudar vuelve a crear una actuación", ACT,
     "    act_id = _act_id_reanudable(desde, destino) if desde is not None else None",
     "    act_id = None",
     f"{T_ACT}::test_reanudar_desde_el_recibo_no_crea_otra_actuacion"),

    ("M20 se declara éxito sin la verificación del paso 6", ACT,
     "    if not vinculada:",
     "    if False:",
     f"{T_ACT}::test_no_declara_exito_sin_la_verificacion_del_paso_6"),

    ("M21 un POST sin respuesta se trata como incompleta y no como incierta", ACT,
     '            return Recibo("incierta", paso=4, elemento=destino.elemento,\n'
     '                          exp_id=destino.exp_id, motivo=(\n'
     '                              f"el POST no dio recibo',
     '            return Recibo("incompleta", paso=4, elemento=destino.elemento,\n'
     '                          exp_id=destino.exp_id, motivo=(\n'
     '                              f"el POST no dio recibo',
     f"{T_ACT}::test_un_post_sin_recibo_deja_el_estado_INCIERTO"),

    ("M22 el asunto canónico gana un defecto de firmante", ACT,
     '    f = (firmante or "").strip()\n    if not f:',
     '    f = (firmante or "Nikolai_Tyukhay").strip()\n    if not f:',
     f"{T_ACT}::test_el_asunto_exige_el_firmante"),

    ("M23 un firmante desconocido elige tarifa por su cuenta", ACT,
     "    prefijo = _PREFIJO_POR_FIRMANTE.get(f)\n    if not prefijo:",
     '    prefijo = _PREFIJO_POR_FIRMANTE.get(f, "ABOGADO")\n    if not prefijo:',
     f"{T_ACT}::test_un_firmante_desconocido_no_elige_tarifa_por_su_cuenta"),

    ("M24 el prefijo de OTRO se corrige en silencio", ACT,
     "        if hallado != prefijo:",
     "        if False:",
     f"{T_ACT}::test_un_asunto_con_el_prefijo_de_OTRO_se_rechaza"),

    ("M25 [H-07] una ronda sin cerrar vale cero en vez de None", ACT,
     "    if ronda is None or not ronda.terminada:\n        return None",
     "    if ronda is None:\n        return None\n    if not ronda.terminada:\n        return 0",
     f"{T_ACT}::test_una_ronda_sin_cerrar_dice_None_y_no_supone_cero"),

    ("M26 [H-07] los extremos invertidos dan una duración negativa", ACT,
     "    if seg < 0:",
     "    if False:",
     f"{T_ACT}::test_extremos_invertidos_se_rechazan"),
    # --- [R2] Los remedios de la segunda ronda, cada uno con su mutante -----------------
    # R3: el `try` de `_items` ya cubre la iteracion, asi que «el parseo vuelve a quedar
    # fuera» dejo de ser matable — el propio remedio lo absorbio. Lo que SI decide algo es
    # la comprobacion de forma: sin ella `{"items": "texto"}` vuelve a salir como lista
    # vacia, o sea «el CRM dice que no hay», que es una afirmacion que nadie hizo.
    ("M27 [R3] una forma imposible vuelve a pasar por lista vacia", ACT,
     "        if not isinstance(crudo, list):",
     "        if False:",
     f"{T_R3}::test_un_cuerpo_json_con_forma_imposible_sale_como_CuerpoIlegible"),

    # La invariante nueva de la pieza, que ningun mutante cubria: en cuanto se ha escrito,
    # el llamador recibe el `act_id` pase lo que pase en el paso 6 (R3/H-01).
    ("M39 [R3] una excepcion del paso 6 vuelve a llevarse el recibo", ACT,
     "    try:\n        vinculada = verificar_actuacion_vinculada(destino.elemento, destino.exp_id, act_id,\n                                                  client=client)\n    except Exception as exc:  # noqa: BLE001",
     "    if True:\n        vinculada = verificar_actuacion_vinculada(destino.elemento, destino.exp_id, act_id,\n                                                  client=client)\n    elif False:",
     f"{T_R3}::test_tras_vincular_SIEMPRE_vuelve_un_recibo_aunque_verificar_reviente"),

    ("M28 [R2] el destino vuelve a leer la PRIMERA fila", ACT,
     '    propia = [f for f in filas if str(f.get("id") or "").strip() == str(exp_id)]',
     "    propia = filas",
     f"{T_R2}::test_el_destino_se_acredita_con_LA_FILA_pedida_no_con_la_primera"),

    # **Este mutante estuvo MAL APUNTADO una ronda entera** (R3/H-08). Llamaba a `_RE_WCODE`,
    # que la R2 había retirado del módulo: el mutante moría con `NameError`, el arnés lo
    # contaba como muerto y no acreditaba nada. La sustitución tiene que ser **ejecutable**,
    # o el rojo prueba que el programa está roto y no que el test detecte la decisión mala.
    # Ahora usa `re`, que sí está importado, y lo mata el segundo caso parametrizado del test
    # —`W-0XXXXX (relacionado W-02VEKE)`—, que es el que ejercita «PRINCIPAL, no de pasada».
    ("M29 [R2] el W-code vuelve a compararse por subcadena", ACT,
     "    if not wcode_match(referencia_esperada, leida):",
     "    if not (set(re.findall(r'W-[A-Z0-9]{5,8}', (referencia_esperada or '').upper()))\n"
     "            & set(re.findall(r'W-[A-Z0-9]{5,8}', (leida or '').upper()))):",
     f"{T_R2}::test_el_w_code_se_compara_ENTERO_y_como_principal"),

    # M16 vuelve: la R2 lo retiró declarando que M29 lo absorbía, y M29 no acreditaba nada.
    # Son además propiedades distintas — «no se contrasta» y «se contrasta mal» — y la
    # absorción era una afirmación sobre cobertura hecha sin comprobarla.
    ("M16 [H-06] el destino deja de contrastarse", ACT,
     "    if not wcode_match(referencia_esperada, leida):",
     "    if False:",
     f"{T_R2}::test_el_w_code_se_compara_ENTERO_y_como_principal"),

    ("M30 [R2] un recibo incierto vuelve a ser reanudable", ACT,
     '    if desde.estado == "incierta" or not desde.act_id:',
     "    if False:",
     f"{T_R2}::test_reanudar_un_recibo_INCIERTO_no_crea_otra_actuacion"),

    ("M31 [R2] el recibo de otro expediente vuelve a aceptarse", ACT,
     "    if (desde.elemento or desde.exp_id) and \\\n            (desde.elemento, desde.exp_id) != (destino.elemento, destino.exp_id):",
     "    if False:",
     f"{T_R2}::test_reanudar_con_el_recibo_de_OTRO_expediente_se_rechaza"),

    ("M32 [R2] el paso 1 vuelve a consultar el asunto crudo", ACT,
     "        pre = aprender_id_predefinido(canonico, client=client)",
     "        pre = aprender_id_predefinido(asunto, client=client)",
     f"{T_R2}::test_el_paso_1_consulta_el_asunto_QUE_SE_VA_A_ESCRIBIR"),

    ("M33 [R2] «no pude mirar el catálogo» vuelve a seguir adelante", ACT,
     '        if pre.estado in ("sin_comprobar", "no_interpretable"):',
     "        if False:",
     f"{T_R2}::test_no_poder_mirar_el_catalogo_NO_sigue_adelante"),

    ("M34 [R2] `extra` vuelve a pisar lo validado", ACT,
     "    invasores = sorted(set(extra or {}) & _CAMPOS_DECIDIDOS)",
     "    invasores = []",
     f"{T_R2}::test_extra_no_puede_sobrescribir_lo_que_se_acaba_de_validar"),

    ("M35 [R2] el prefijo vuelve a exigir formato exacto", ACT,
     "    m = _RE_PREFIJO.match(texto)",
     '    m = re.match(r"^(SENIOR|ABOGADO) - ", texto)',
     f"{T_R2}::test_un_prefijo_contradictorio_se_detecta_aunque_varie_el_formato"),

    ("M36 [R2] la duración vuelve a aceptar fechas sin zona", ACT,
     '    sin_zona = [c for c, v in (("iniciada", ini), ("terminada", fin)) if v.tzinfo is None]',
     "    sin_zona = []",
     f"{T_R2}::test_la_duracion_exige_zona_en_LOS_DOS_extremos"),

    ("M37 [R2] el buzón truncado vuelve a autorizar la creación", REL,
     "    if len(c_mail.registros) >= _LIMITE_BUZON:",
     "    if False:",
     f"{T_71}::test_r2_un_buzon_truncado_no_autoriza_a_crear"),

    ("M38 [R2] el validador vuelve a anclar solo el primer contrario", VAL,
     "    for idx, c in enumerate(ficha.contrarios):",
     "    for idx, c in enumerate(ficha.contrarios[:1]):",
     f"{T_63}::test_r2_el_validador_ancla_TODOS_los_contrarios"),
]

#: (nombre, motivo). Mutantes que se conservan sin exigirles muerte, con su razón escrita.
SUPERVIVIENTES_DECLARADOS: list[tuple[str, str]] = []


def _escribir(path: Path, texto: str, *, intentos: int = 5) -> None:
    """Escribe `path`, reintentando el fallo TRANSITORIO de Windows.

    `OSError: [Errno 22] Invalid argument` y `PermissionError` aparecen cuando otro proceso
    —un indexador, un antivirus, el pytest que acaba de importar el módulo— aún tiene un
    handle abierto sobre el fichero que se acaba de reescribir. Medido en P4: abortó el arnés
    entre dos mutantes. Un arnés que se cae a mitad **deja el árbol mutado**, así que esta
    función y el `finally` de `main` son las dos mitades de la misma garantía.
    """
    ultimo: OSError | None = None
    for i in range(intentos):
        try:
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(texto)
            return
        except OSError as exc:            # incluye PermissionError
            ultimo = exc
            time.sleep(0.2 * (i + 1))
    raise RuntimeError(
        f"no se pudo restaurar {path} tras {intentos} intentos: {ultimo!r}. "
        "COMPRUEBA EL ARBOL antes de seguir: puede haber quedado mutado.") from ultimo


#: Código de salida de pytest para «error de uso»: aquí significa, casi siempre, que el nodo
#: de test **no existe** — un mutante apuntado a un fichero o a un nombre equivocado.
_PYTEST_USAGE_ERROR = 4


def _corre(test: str) -> tuple[int, str]:
    """Corre un test en subproceso y devuelve `(rc, salida)`.

    **La salida se devuelve porque el código solo no distingue los dos fallos que importan.**
    Un mutante apuntado a un test que no existe da `rc=4`, y leerlo como «el test YA estaba
    rojo sin mutar» es un diagnóstico equivocado que manda a buscar un defecto donde no lo
    hay. Pasó en P4 con un mutante apuntado al fichero equivocado. `main` los separa.
    """
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    # `--tb=line` en vez de `--tb=no`: una línea por fallo, y **con el tipo de excepción**,
    # que es lo que permite distinguir un rojo semántico de un programa roto (`_ROTO`).
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line", "-p", "no:randomly",
         "-p", "no:cacheprovider", test],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace", env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


#: Excepciones que NO pueden ser la detección de una decisión mala: significan que el módulo
#: mutado está roto. Un rojo así cuenta como muerte y **no acredita nada** — el test no ha
#: detectado nada, simplemente el programa no llega a funcionar.
#:
#: R3/H-08: M29 sustituía `wcode_match` por una llamada a `_RE_WCODE`, una regex que la ronda
#: anterior había retirado del módulo. Moría con `NameError`, el arnés lo contaba como muerto,
#: y sobre esa muerte falsa se había retirado otro mutante «porque este lo absorbe». El 37/37
#: era 36 muertes y una coartada.
#:
#: La lista es CORTA a propósito: `AttributeError` y `TypeError` se quedan fuera porque sí
#: pueden ser una detección legítima, y un arnés que grita de más acaba desactivado.
_ROTO = ("NameError", "UnboundLocalError", "ImportError", "ModuleNotFoundError",
         "SyntaxError", "IndentationError")


def main() -> int:
    fallos: list[str] = []
    for nombre, fichero, viejo, nuevo, test in MUTANTES:
        objetivo = RAIZ / fichero
        s = io.open(objetivo, encoding="utf-8").read()
        if viejo not in s:
            print(f"[ARNES ROTO] {nombre}: el texto original ya no esta en {fichero}")
            fallos.append(nombre)
            continue
        # **Que la mutación COMPILE se comprueba antes de gastar dos corridas de pytest.** Es
        # el caso más básico de «murió por estar roto, no por la propiedad» (R3/H-08), y el
        # `rc=4` ya lo cazaba — pero tarde y diciendo solo «dejó de coleccionar». Aquí sale la
        # línea exacta. Lo destapó una re-apuntada propia: un `if False:` copiado con la
        # indentación del sitio del que venía dejaba el `raise` menos indentado que su `if`.
        try:
            compile(s.replace(viejo, nuevo, 1), fichero, "exec")
        except SyntaxError as exc:
            print(f"[ARNES ROTO] {nombre}: la mutación no compila "
                  f"(línea {exc.lineno}: {exc.msg}). Revisa su indentación")
            fallos.append(nombre)
            continue
        rc_previo, salida = _corre(test)
        if rc_previo == _PYTEST_USAGE_ERROR:
            # **«No existe» no es «está rojo».** Son dos defectos distintos del arnés y el
            # remedio de cada uno es otro: aquí se corrige la REFERENCIA del mutante; allí,
            # el test o el código. Decirlos igual manda a buscar donde no está.
            print(f"[ARNES ROTO] {nombre}: el test al que apunta NO EXISTE → {test}")
            fallos.append(nombre)
            continue
        if rc_previo != 0:
            print(f"[ARNES ROTO] {nombre}: {test.split('::')[-1]} YA estaba rojo sin mutar")
            fallos.append(nombre)
            continue
        # **La restauración se arma ANTES de mutar, no después.**
        try:
            _escribir(objetivo, s.replace(viejo, nuevo, 1))
            rc, salida_mut = _corre(test)
        finally:
            _escribir(objetivo, s)
        if rc == _PYTEST_USAGE_ERROR:
            # Mutar no puede hacer desaparecer un test que existía hace un segundo: si pasa,
            # la mutación rompió la COLECCIÓN del fichero, y entonces el rojo no prueba la
            # propiedad — prueba que Python no puede leer el módulo.
            print(f"[ARNES ROTO] {nombre}: mutado, el test dejó de COLECCIONAR (rc=4): la "
                  "mutación rompe el módulo, no la propiedad")
            fallos.append(nombre)
        elif rc == 0:
            print(f"[SUPERVIVIENTE] {nombre}  <- no lo mata {test.split('::')[-1]}")
            fallos.append(nombre)
        elif (roto := next((e for e in _ROTO if e in salida_mut), None)):
            # **Morir no es ser detectado.** El test se pone rojo porque el programa mutado no
            # funciona, no porque haya cazado la decisión que se quería introducir: ese rojo no
            # acredita la propiedad y contarlo como muerte es una garantía falsa.
            print(f"[ARNES ROTO] {nombre}: el mutante murió por {roto}, no por la propiedad. "
                  "La sustitución tiene que ser EJECUTABLE")
            fallos.append(nombre)
        else:
            print(f"[muerto] {nombre}")

    print()
    print(f"{len(MUTANTES)} mutantes, {len(MUTANTES) - len(fallos)} muertos.")
    print("SUPERVIVIENTES/ROTOS:", ", ".join(fallos) if fallos else "ninguno")
    for nombre, motivo in SUPERVIVIENTES_DECLARADOS:
        print()
        print("[DECLARADO, no matado] " + nombre)
        print("  " + motivo)
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
