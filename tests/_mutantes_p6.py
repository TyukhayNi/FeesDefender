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
     '_buscar_registros(elemento, "email", (email or "").strip(), properties=(prop_nif,))',
     '_buscar_registros(elemento, "email", (email or "").strip())',
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
    ("M11 [H-08] los elementos inválidos se filtran en silencio", FICHA,
     "    fuera = [str(i) for i, e in enumerate(raw) if not isinstance(e, dict)]\n    if fuera:",
     "    raw = [e for e in raw if isinstance(e, dict)]\n    fuera = []\n    if fuera:",
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
     '        return IdPredefinido("sin_filas", motivo=f"ninguna actuación casa {asunto!r}")',
     '        return IdPredefinido("no_aplica", motivo="")',
     f"{T_ACT}::test_cero_filas_no_es_lo_mismo_que_filas_sin_campo"),

    ("M16 [H-06] el destino deja de contrastarse", ACT,
     "    if not esperados or not leidos or not (esperados & leidos):",
     "    if False:",
     f"{T_ACT}::test_un_expediente_de_OTRO_caso_con_el_mismo_numero_no_se_acredita"),

    ("M17 [H-06] no poder leer el destino pasa por acreditarlo", ACT,
     '        raise DestinoNoAcreditado(\n            f"no se pudo leer {elemento}/{exp_id} (HTTP {r.status_code}). No se escribe nada.")',
     '        return Destino(elemento=elemento, exp_id=str(exp_id), evidencia="(no leido)")',
     f"{T_ACT}::test_un_destino_que_no_se_puede_leer_tampoco_se_acredita"),

    ("M18 [H-04] el recibo pierde el id de la actuación creada", ACT,
     '        return Recibo("incompleta", act_id=act_id, paso=4, motivo=(',
     '        return Recibo("incompleta", act_id=None, paso=4, motivo=(',
     f"{T_ACT}::test_si_el_vinculo_falla_el_recibo_conserva_el_id_creado"),

    ("M19 [H-04] reanudar vuelve a crear una actuación", ACT,
     "    act_id = desde.act_id if (desde and desde.act_id) else None",
     "    act_id = None",
     f"{T_ACT}::test_reanudar_desde_el_recibo_no_crea_otra_actuacion"),

    ("M20 se declara éxito sin la verificación del paso 6", ACT,
     "    if not verificar_actuacion_vinculada(destino.elemento, destino.exp_id, act_id,\n                                         client=client):",
     "    if False:",
     f"{T_ACT}::test_no_declara_exito_sin_la_verificacion_del_paso_6"),

    ("M21 un POST sin respuesta se trata como incompleta y no como incierta", ACT,
     '            return Recibo("incierta", paso=4, motivo=(\n                f"el POST no dio recibo',
     '            return Recibo("incompleta", paso=4, motivo=(\n                f"el POST no dio recibo',
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
     "            if p != prefijo:\n                raise ValueError(",
     "            if False:\n                raise ValueError(",
     f"{T_ACT}::test_un_asunto_con_el_prefijo_de_OTRO_se_rechaza"),

    ("M25 [H-07] una ronda sin cerrar vale cero en vez de None", ACT,
     "    if ronda is None or not ronda.terminada:\n        return None",
     "    if ronda is None:\n        return None\n    if not ronda.terminada:\n        return 0",
     f"{T_ACT}::test_una_ronda_sin_cerrar_dice_None_y_no_supone_cero"),

    ("M26 [H-07] los extremos invertidos dan una duración negativa", ACT,
     "    if seg < 0:",
     "    if False:",
     f"{T_ACT}::test_extremos_invertidos_se_rechazan"),
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
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:randomly",
         "-p", "no:cacheprovider", test],
        cwd=RAIZ, capture_output=True, encoding="utf-8", errors="replace", env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    fallos: list[str] = []
    for nombre, fichero, viejo, nuevo, test in MUTANTES:
        objetivo = RAIZ / fichero
        s = io.open(objetivo, encoding="utf-8").read()
        if viejo not in s:
            print(f"[ARNES ROTO] {nombre}: el texto original ya no esta en {fichero}")
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
            rc, _ = _corre(test)
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
