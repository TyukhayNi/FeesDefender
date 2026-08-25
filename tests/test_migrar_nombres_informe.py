"""Tests del renombrado de informes de viabilidad (2026-07-28).

El nombre pasó de llevar el ``case_id`` completo a llevar solo el ID GO porque
la ruta se salía de los 260 caracteres que tolera Excel. Estos tests cubren el
plan (qué se decide) y la aplicación (qué se mueve), con los tres casos reales
que había en el Drive: nombre largo del pipeline, nombre puesto a mano en
mayúsculas y caso sin ID GO (``SIN REFERENCIA``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.migrar_nombres_informe import (
    AMBIGUO,
    COLISION,
    RENOMBRAR,
    RUTA_OFFICE_MAX,
    YA_CORRECTO,
    Entrada,
    aplicar,
    plan_renombrado,
    resumen,
)

# Geometría de PRODUCCIÓN, como referencia fija: los expedientes viven en
# `G:\Unidades compartidas\EXPEDIENTES - TYUKHAY LEGAL\CASOS` (57 car.), una raíz
# que NO contiene `%USERPROFILE%` y por tanto no cambia entre perfiles de Windows.
# Se declara aquí porque el presupuesto de ruta hay que medirlo contra ESA raíz y
# no contra la de `tmp_path`, que depende de dónde ponga pytest sus temporales.
# Medido el 2026-08-25: con la raíz de `tmp_path`, este fichero pasaba en el perfil
# `tnm33` (basetemp de 61 car.) y fallaba en `Nikolai Tyukhay 1` (85 car.), porque
# el nombre de cuenta entra DOS veces en la ruta temporal —`%USERPROFILE%` y
# `pytest-of-<usuario>`— y suma 24 caracteres. El umbral estaba en 70: `tnm33`
# pasaba por NUEVE caracteres de margen. El veredicto lo decidía el entorno.
LARGO_RAIZ_PRODUCCION = 57

# Los case_id reales llevan la dirección del inmueble. Aquí se sustituye por
# relleno conservando la longitud (81 car.), que es lo que reproduce el bug; la
# identidad la da el W-code (`docs/SEGURIDAD_DATOS.md`).
CASE_LARGO = f"BaRS8 - {'X' * 35} (W-02XOR7) - Negativa oferta aceptada"


def _montar(root: Path, ciudad: str, case_id: str, ficheros: list[str]) -> Path:
    """Monta un caso mínimo. ``00_Input`` es lo que marca la raíz de un caso."""
    case_dir = root / ciudad / case_id
    (case_dir / "00_Input").mkdir(parents=True)
    analisis = case_dir / "02_Analisis"
    analisis.mkdir()
    for nombre in ficheros:
        (analisis / nombre).write_bytes(b"xlsx")
    return analisis


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------

def test_renombra_el_nombre_largo_al_id_go(tmp_path):
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO,
                       [f"Informe viabilidad - {CASE_LARGO}.xlsx"])
    plan = plan_renombrado(tmp_path)
    assert len(plan) == 1
    assert plan[0].estado == RENOMBRAR
    assert plan[0].destino == analisis / "Informe viabilidad - W-02XOR7.xlsx"


def test_el_nombre_ya_corto_no_se_toca(tmp_path):
    _montar(tmp_path, "Barcelona", CASE_LARGO, ["Informe viabilidad - W-02XOR7.xlsx"])
    plan = plan_renombrado(tmp_path)
    assert [e.estado for e in plan] == [YA_CORRECTO]


def test_caso_sin_id_go_va_al_fallback(tmp_path):
    """SaRS1 real: formato CRM nuevo pero ``(SIN REFERENCIA)``."""
    case_id = f"SaRS1 - {'X' * 29} - (SIN REFERENCIA) - Otros"
    analisis = _montar(tmp_path, "Santander", case_id,
                       [f"Informe viabilidad - {case_id}.xlsx"])
    plan = plan_renombrado(tmp_path)
    assert plan[0].estado == RENOMBRAR
    assert plan[0].destino == analisis / "_informe_viabilidad.xlsx"


def test_dos_informes_humanos_se_marcan_ambiguos_y_no_se_tocan(tmp_path):
    """Caso real de BaRS8: uno del pipeline y otro puesto a mano en mayúsculas."""
    nombres = [
        f"Informe viabilidad - {CASE_LARGO}.xlsx",
        f"INFORME VIABILIDAD {CASE_LARGO}.xlsx",
    ]
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO, nombres)
    plan = plan_renombrado(tmp_path)
    assert {e.estado for e in plan} == {AMBIGUO}
    assert len(plan) == 2
    assert all(e.destino is None for e in plan)

    aplicar(plan)
    assert sorted(p.name for p in analisis.iterdir()) == sorted(nombres)


def test_informe_llm_se_renombra_en_su_propio_grupo(tmp_path):
    """Humano y LLM conviven: son grupos distintos, ninguno es ambiguo."""
    analisis = _montar(tmp_path, "Valencia", CASE_LARGO, [
        f"Informe viabilidad - {CASE_LARGO}.xlsx",
        f"Informe viabilidad LLM - {CASE_LARGO}.xlsx",
    ])
    plan = plan_renombrado(tmp_path)
    destinos = {e.destino.name for e in plan if e.estado == RENOMBRAR}
    assert destinos == {
        "Informe viabilidad - W-02XOR7.xlsx",
        "Informe viabilidad LLM - W-02XOR7.xlsx",
    }
    aplicar(plan)
    assert sorted(p.name for p in analisis.iterdir()) == [
        "Informe viabilidad - W-02XOR7.xlsx",
        "Informe viabilidad LLM - W-02XOR7.xlsx",
    ]


def test_colision_no_sobrescribe(tmp_path):
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO, [
        f"Informe viabilidad - {CASE_LARGO}.xlsx",
        "Informe viabilidad - W-02XOR7.xlsx",
    ])
    plan = plan_renombrado(tmp_path)
    # Dos informes humanos → ambiguo antes incluso de mirar la colisión
    assert {e.estado for e in plan} == {AMBIGUO}
    assert len(list(analisis.iterdir())) == 2


def test_colision_de_grupo_unico_se_detecta(tmp_path):
    """Un solo informe humano cuyo destino lo ocupa el cuestionario renombrado
    a mano: no se sobrescribe."""
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO,
                       [f"Informe viabilidad - {CASE_LARGO}.xlsx"])
    (analisis / "Informe viabilidad - W-02XOR7.xlsx").mkdir()  # ocupa el nombre
    plan = plan_renombrado(tmp_path)
    assert [e.estado for e in plan] == [COLISION]
    aplicar(plan)
    assert (analisis / f"Informe viabilidad - {CASE_LARGO}.xlsx").is_file()


def test_ignora_cuestionario_y_otros_xlsx(tmp_path):
    _montar(tmp_path, "Barcelona", CASE_LARGO, [
        "_cuestionario_viabilidad.xlsx",
        "Bitacora de la entrevista.xlsx",
    ])
    assert plan_renombrado(tmp_path) == []


def test_alcanza_los_casos_archivados_a_mas_profundidad(tmp_path):
    """Los casos vivos cuelgan de ``<ciudad>/<case_id>/`` pero los archivados de
    ``_ARCHIVO/<carpeta>/<año>/<case_id>/``. Caso real que un glob de
    profundidad fija se dejaba fuera."""
    case_id = "BaRS3 - Art 79, Bajos 3ª (W-046G2R) - Negativa escritura"
    case_dir = tmp_path / "_ARCHIVO" / "01. EXTRAJUDICIALES" / "2026" / case_id
    (case_dir / "00_Input").mkdir(parents=True)
    (case_dir / "02_Analisis").mkdir()
    (case_dir / "02_Analisis" /
     "Informe viabilidad - BaRS3 - Art 79, Bajos 3ª (W-046G2R) - Devolucion arras.xlsx"
     ).write_bytes(b"xlsx")

    plan = plan_renombrado(tmp_path)
    assert [e.estado for e in plan] == [RENOMBRAR]
    assert plan[0].destino.name == "Informe viabilidad - W-046G2R.xlsx"


def test_ignora_un_02_analisis_dentro_de_un_espejo(tmp_path):
    """El crudo de E&V en ``00_Input/01_Drive EV/`` replica su propia estructura;
    un ``02_Analisis`` de ahí dentro no es la carpeta de análisis del caso y su
    contenido es intocable (el pipeline nunca escribe en ``00_Input``)."""
    _montar(tmp_path, "Barcelona", CASE_LARGO, [])
    espejo = (tmp_path / "Barcelona" / CASE_LARGO / "00_Input" / "01_Drive EV"
              / "_DEMANDA" / "02_Analisis")
    espejo.mkdir(parents=True)
    (espejo / f"INFORME VIABILIDAD {CASE_LARGO}.xlsx").write_bytes(b"crudo")

    assert plan_renombrado(tmp_path) == []
    assert (espejo / f"INFORME VIABILIDAD {CASE_LARGO}.xlsx").is_file()


def test_id_go_del_frontmatter_manda_sobre_el_del_case_id(tmp_path):
    case_id = f"BaRS8 - {'X' * 35} (W-000000) - Negativa oferta"
    analisis = _montar(tmp_path, "Barcelona", case_id,
                       [f"Informe viabilidad - {case_id}.xlsx"])
    entrada = analisis.parent / "00_Input"
    (entrada / "_caso.md").write_text(
        "---\nmeta:\n  id_go: W-02XOR7\n---\n\n# caso\n", encoding="utf-8"
    )
    plan = plan_renombrado(tmp_path)
    assert plan[0].destino.name == "Informe viabilidad - W-02XOR7.xlsx"


def test_frontmatter_ilegible_cae_al_id_go_del_case_id(tmp_path):
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO,
                       [f"Informe viabilidad - {CASE_LARGO}.xlsx"])
    (analisis.parent / "00_Input" / "_caso.md").write_text(
        "---\n: : no es yaml : :\n", encoding="utf-8")
    plan = plan_renombrado(tmp_path)
    assert plan[0].destino.name == "Informe viabilidad - W-02XOR7.xlsx"


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------

def test_aplicar_mueve_y_es_idempotente(tmp_path):
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO,
                       [f"Informe viabilidad - {CASE_LARGO}.xlsx"])
    aplicadas = aplicar(plan_renombrado(tmp_path))
    assert len(aplicadas) == 1
    assert (analisis / "Informe viabilidad - W-02XOR7.xlsx").is_file()
    assert not (analisis / f"Informe viabilidad - {CASE_LARGO}.xlsx").exists()

    # Segunda pasada: nada que hacer
    plan2 = plan_renombrado(tmp_path)
    assert [e.estado for e in plan2] == [YA_CORRECTO]
    assert aplicar(plan2) == []


def test_aplicar_preserva_el_contenido(tmp_path):
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO, [])
    origen = analisis / f"Informe viabilidad - {CASE_LARGO}.xlsx"
    origen.write_bytes(b"TRABAJO DEL ABOGADO")
    aplicar(plan_renombrado(tmp_path))
    assert (analisis / "Informe viabilidad - W-02XOR7.xlsx").read_bytes() == \
        b"TRABAJO DEL ABOGADO"


def test_aplicar_no_pisa_un_destino_aparecido_entre_plan_y_aplicacion(tmp_path):
    analisis = _montar(tmp_path, "Barcelona", CASE_LARGO,
                       [f"Informe viabilidad - {CASE_LARGO}.xlsx"])
    plan = plan_renombrado(tmp_path)
    assert plan[0].estado == RENOMBRAR
    # El Drive sincroniza algo con ese nombre justo después de planificar
    (analisis / "Informe viabilidad - W-02XOR7.xlsx").write_bytes(b"OTRA COSA")
    assert aplicar(plan) == []
    assert (analisis / "Informe viabilidad - W-02XOR7.xlsx").read_bytes() == b"OTRA COSA"
    assert (analisis / f"Informe viabilidad - {CASE_LARGO}.xlsx").is_file()


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

def test_resumen_cuenta_por_estado(tmp_path):
    _montar(tmp_path, "Barcelona", CASE_LARGO, [f"Informe viabilidad - {CASE_LARGO}.xlsx"])
    _montar(tmp_path, "Madrid", "MaRS8 - Pontevedra 80 - (W-02OMTG) - Negativa oferta",
            ["Informe viabilidad - W-02OMTG.xlsx"])
    conteo = resumen(plan_renombrado(tmp_path))
    assert conteo[RENOMBRAR] == 1
    assert conteo[YA_CORRECTO] == 1


def test_el_renombrado_deja_las_rutas_dentro_del_presupuesto_de_produccion(tmp_path):
    """Lo que de verdad se quiere saber: tras renombrar, ¿cabe en Excel?

    Se mide contra `LARGO_RAIZ_PRODUCCION`, no contra la longitud de `tmp_path`.
    Es la misma pregunta que hacía `test_resumen_cuenta_por_estado` con
    `fuera_de_presupuesto == 0`, pero sin que la conteste el sitio donde pytest
    montó el temporal. El contador en sí se contrata aparte, con rutas sintéticas.
    """
    _montar(tmp_path, "Barcelona", CASE_LARGO, [f"Informe viabilidad - {CASE_LARGO}.xlsx"])
    _montar(tmp_path, "Madrid", "MaRS8 - Pontevedra 80 - (W-02OMTG) - Negativa oferta",
            ["Informe viabilidad - W-02OMTG.xlsx"])
    plan = plan_renombrado(tmp_path)
    assert plan, "sin plan no hay nada que medir y el test seria vacuo"
    for entrada in plan:
        final = entrada.destino or entrada.origen
        largo_en_produccion = (
            LARGO_RAIZ_PRODUCCION + 1 + len(str(final.relative_to(tmp_path)))
        )
        assert largo_en_produccion <= RUTA_OFFICE_MAX, (
            f"{final.name}: {largo_en_produccion} car. sobre la raiz de produccion"
        )


# ---------------------------------------------------------------------------
# El contador de presupuesto, con rutas sintéticas: sus tres fronteras
# ---------------------------------------------------------------------------

def _ruta_de(largo: int) -> Path:
    """Ruta absoluta de longitud EXACTA, para contratar el contador sin disco."""
    ruta = Path("C:/" + "x" * (largo - 3))
    assert len(str(ruta)) == largo, f"esperaba {largo}, salio {len(str(ruta))}"
    return ruta


def _entrada(largo_origen: int, largo_destino: int | None = None) -> Entrada:
    return Entrada(
        case_id="W-00TEST",
        origen=_ruta_de(largo_origen),
        destino=_ruta_de(largo_destino) if largo_destino is not None else None,
        estado=RENOMBRAR if largo_destino is not None else YA_CORRECTO,
    )


def test_el_presupuesto_es_exclusivo_no_inclusivo():
    """Frontera 1: `RUTA_OFFICE_MAX` justo es válido; uno más, no."""
    assert resumen([_entrada(300, RUTA_OFFICE_MAX)])["fuera_de_presupuesto"] == 0
    assert resumen([_entrada(300, RUTA_OFFICE_MAX + 1)])["fuera_de_presupuesto"] == 1


def test_el_presupuesto_mide_el_destino_no_el_origen():
    """Frontera 2: lo que importa es la ruta DESPUÉS de renombrar.

    Un origen desbordado que el renombrado mete en presupuesto no cuenta: si
    contara, el informe diría que la migración no sirvió justo cuando sí sirvió.
    """
    conteo = resumen([_entrada(RUTA_OFFICE_MAX + 60, RUTA_OFFICE_MAX - 40)])
    assert conteo["fuera_de_presupuesto"] == 0


def test_sin_destino_el_presupuesto_cae_al_origen():
    """Frontera 3: `ya_correcto` no tiene destino, y aun así puede desbordar."""
    assert resumen([_entrada(RUTA_OFFICE_MAX + 1)])["fuera_de_presupuesto"] == 1
    assert resumen([_entrada(RUTA_OFFICE_MAX)])["fuera_de_presupuesto"] == 0


def test_raiz_vacia_no_revienta(tmp_path):
    assert plan_renombrado(tmp_path) == []
    assert resumen([])[RENOMBRAR] == 0
