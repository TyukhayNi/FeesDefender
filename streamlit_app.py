"""FeesDefender — Motor de análisis y reclamación de honorarios. UI Streamlit.

La UI no contiene lógica de negocio: solo orquesta llamadas al `core` y
visualiza los `.md` resultantes. Pensada para uso local del abogado.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core import case_manager, llm, pipeline, sudespacho_create as _sc
from core.config import (
    CASO_SUBDIRS,
    caso_path,
    settings,
    TIPOS_CASO_ALL,
    posicion_de_tipo,
    POSICION_ACTORA,
)

st.set_page_config(page_title="FeesDefender", layout="wide")

st.title("⚖️ FeesDefender")
st.caption("Motor de análisis y reclamación de honorarios inmobiliarios — análisis de viabilidad y preparación de reclamación")

# ---------------------------------------------------------------------------
# Estado del entorno
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Entorno")
    st.write(f"**CASOS_ROOT**\n\n`{settings.casos_root}`")
    st.write(f"**Modelo**: `{settings.ollama_model}` @ `{settings.ollama_host}`")
    ok = llm.healthcheck()
    if ok:
        st.success("Ollama disponible")
    else:
        st.warning("Ollama no responde o el modelo no está. Ejecuta `ollama pull <modelo>`.")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_casos, tab_nuevo, tab_pipeline, tab_visor = st.tabs(
    ["Casos", "Nuevo caso", "Pipeline", "Visor"]
)


with tab_casos:
    cases = case_manager.list_cases()
    if not cases:
        st.info("No hay casos. Crea uno desde la pestaña «Nuevo caso».")
    else:
        st.write(f"**{len(cases)}** casos en `{settings.casos_root}`")
        st.dataframe(
            [{"case_id": c, "ruta": str(caso_path(c))} for c in cases],
            use_container_width=True,
        )


with tab_nuevo:
    st.subheader("Nuevo caso")

    # ------------------------------------------------------------------
    # Diccionarios auxiliares para los selectores
    # ------------------------------------------------------------------
    _EQUIPOS: dict[str, str] = {
        # Barcelona
        "BaRR1  — BCN Residential Rentals 1":   _sc.TAG_ROJO_BaRR1,
        "BaRR3  — BCN Residential Rentals 3":   _sc.TAG_ROJO_BaRR3,
        "BaRR4  — BCN Residential Rentals 4":   _sc.TAG_ROJO_BaRR4,
        "BaRS1  — BCN Residential Sales 1":     _sc.TAG_ROJO_BaRS1,
        "BaRS2  — BCN Residential Sales 2":     _sc.TAG_ROJO_BaRS2,
        "BaRS3  — BCN Residential Sales 3":     _sc.TAG_ROJO_BaRS3,
        "BaRS4  — BCN Residential Sales 4":     _sc.TAG_ROJO_BaRS4,
        "BaRS5  — BCN Residential Sales 5":     _sc.TAG_ROJO_BaRS5,
        "BaRS6  — BCN Residential Sales 6":     _sc.TAG_ROJO_BaRS6,
        "BaRS7  — BCN Residential Sales 7":     _sc.TAG_ROJO_BaRS7,
        "BaRS8  — BCN Residential Sales 8":     _sc.TAG_ROJO_BaRS8,
        "BaRS9  — BCN Residential Sales 9":     _sc.TAG_ROJO_BaRS9,
        "BaRS10 — BCN Residential Sales 10":    _sc.TAG_ROJO_BaRS10,
        "BaRS11 — BCN Residential Sales 11":    _sc.TAG_ROJO_BaRS11,
        "BaRS12 — BCN Residential Sales 12":    _sc.TAG_ROJO_BaRS12,
        "BaCR1  — BCN Commercial Rentals 1":    _sc.TAG_ROJO_BaCR1,
        "BaCR10 — BCN Commercial Rentals 10":   _sc.TAG_ROJO_BaCR10,
        "BaCS1  — BCN Commercial Sales 1":      _sc.TAG_ROJO_BaCS1,
        "BaCS10 — BCN Commercial Sales 10":     _sc.TAG_ROJO_BaCS10,
        # Bilbao
        "BiRS1  — Bilbao Residential Sales 1":  _sc.TAG_ROJO_BiRS1,
        "BiRS2  — Bilbao Residential Sales 2":  _sc.TAG_ROJO_BiRS2,
        # Madrid
        "MaRR1  — MAD Residential Rentals 1":   _sc.TAG_ROJO_MaRR1,
        "MaRR2  — MAD Residential Rentals 2":   _sc.TAG_ROJO_MaRR2,
        "MaRR3  — MAD Residential Rentals 3":   _sc.TAG_ROJO_MaRR3,
        "MaRS1  — MAD Residential Sales 1":     _sc.TAG_ROJO_MaRS1,
        "MaRS2  — MAD Residential Sales 2":     _sc.TAG_ROJO_MaRS2,
        "MaRS3  — MAD Residential Sales 3":     _sc.TAG_ROJO_MaRS3,
        "MaRS4  — MAD Residential Sales 4":     _sc.TAG_ROJO_MaRS4,
        "MaRS5  — MAD Residential Sales 5":     _sc.TAG_ROJO_MaRS5,
        "MaRS6  — MAD Residential Sales 6":     _sc.TAG_ROJO_MaRS6,
        "MaRS7  — MAD Residential Sales 7":     _sc.TAG_ROJO_MaRS7,
        "MaRS8  — MAD Residential Sales 8":     _sc.TAG_ROJO_MaRS8,
        "MaRS9  — MAD Residential Sales 9":     _sc.TAG_ROJO_MaRS9,
        "MaRS10 — MAD Residential Sales 10":    _sc.TAG_ROJO_MaRS10,
        "MaRS13 — MAD Residential Sales 13":    _sc.TAG_ROJO_MaRS13,
        "MaRS14 — MAD Residential Sales 14":    _sc.TAG_ROJO_MaRS14,
        # Santander
        "SaRS1  — Santander Residential Sales 1":       _sc.TAG_ROJO_SaRS1,
        # San Sebastián
        "SSRR1  — San Sebastián Residential Rentals 1": _sc.TAG_ROJO_SSRR1,
        "SSRS1  — San Sebastián Residential Sales 1":   _sc.TAG_ROJO_SSRS1,
        # Sevilla
        "SeRS1  — Sevilla Residential Sales 1": _sc.TAG_ROJO_SeRS1,
        "SeRS6  — Sevilla Residential Sales 6": _sc.TAG_ROJO_SeRS6,
        # Valencia
        "VaCR1  — Valencia Commercial Rentals 1":  _sc.TAG_ROJO_VaCR1,
        "VaPD1  — Valencia (pendiente) 1":         _sc.TAG_ROJO_VaPD1,
        "VaRR1  — Valencia Residential Rentals 1": _sc.TAG_ROJO_VaRR1,
        "VaRS1  — Valencia Residential Sales 1":   _sc.TAG_ROJO_VaRS1,
        "VaRS2  — Valencia Residential Sales 2":   _sc.TAG_ROJO_VaRS2,
        "VaRS3  — Valencia Residential Sales 3":   _sc.TAG_ROJO_VaRS3,
        "VaRS4  — Valencia Residential Sales 4":   _sc.TAG_ROJO_VaRS4,
        "VaRS5  — Valencia Residential Sales 5":   _sc.TAG_ROJO_VaRS5,
    }

    _CIUDADES: dict[str, str | None] = {
        "— sin especificar —": None,
        "Barcelona":     _sc.TAG_AZUL_BARCELONA,
        "Madrid":        _sc.TAG_AZUL_MADRID,
        "Valencia":      _sc.TAG_AZUL_VALENCIA,
        "Sevilla":       _sc.TAG_AZUL_SEVILLA,
        "Bilbao":        _sc.TAG_AZUL_BILBAO,
        "San Sebastián": _sc.TAG_AZUL_SAN_SEBASTIAN,
        "Santander":     _sc.TAG_AZUL_SANTANDER,
    }

    _NOTAS: dict[str, str] = {
        "BAD_DEBT":                        _sc.NOTA_BAD_DEBT,
        "NEGATIVA_OFERTA":                 _sc.NOTA_NEGATIVA_OFERTA,
        "NEGATIVA_ARRAS":                  _sc.NOTA_NEGATIVA_ARRAS,
        "NEGATIVA_ESCRITURA":              _sc.NOTA_NEGATIVA_ESCRITURA,
        "NEGATIVA_CONTRATO_ARRENDAMIENTO": _sc.NOTA_NEGATIVA_CONTRATO_ARR,
        "VUELTA":                          _sc.NOTA_VUELTA,
        "INCUMPLIMIENTO_EXCLUSIVA":        _sc.NOTA_INCUMPLIMIENTO_EXCLUSIVA,
        "RESPONSABILIDAD_PROFESIONAL":     _sc.NOTA_RESPONSABILIDAD_PROF,
        "DEVOLUCION_RESERVA":              _sc.NOTA_DEVOLUCION_RESERVA,
        "LAU_20":                          _sc.NOTA_LAU_20,
    }

    # ------------------------------------------------------------------
    # Campos del formulario (sin st.form para poder mostrar preview live)
    # ------------------------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        equipo_label = st.selectbox(
            "Equipo comercial *",
            list(_EQUIPOS.keys()),
            key="nc_equipo",
        )
    with col2:
        tipo_caso = st.selectbox(
            "Tipo de caso *",
            list(TIPOS_CASO_ALL.keys()),
            format_func=lambda k: TIPOS_CASO_ALL[k][0].capitalize(),
            key="nc_tipo",
        )

    col3, col4 = st.columns([3, 1])
    with col3:
        direccion = st.text_input(
            "Dirección operación *",
            placeholder="Gran Via 40, 3º 1ª",
            key="nc_dir",
        )
    with col4:
        ref_mls = st.text_input(
            "ID GO *",
            placeholder="W-030LFT",
            key="nc_mls",
        )

    col5, col6 = st.columns(2)
    with col5:
        cuantia_nc = st.number_input(
            "Cuantía reclamada (€)",
            min_value=0.0,
            step=100.0,
            key="nc_cuantia",
        )
    with col6:
        ciudad_label = st.selectbox(
            "Ciudad *",
            list(_CIUDADES.keys()),
            key="nc_ciudad",
        )

    # ------------------------------------------------------------------
    # Preview del case_id (se actualiza en tiempo real)
    # ------------------------------------------------------------------
    _equipo_short = equipo_label.split("—")[0].strip()          # "BaRR3"
    _tipo_tag_crm = TIPOS_CASO_ALL[tipo_caso][0].capitalize()   # "Negativa arras"
    _dir_str = direccion.strip() or "‹dirección›"
    _mls_str = ref_mls.strip() or "W-XXXXXX"
    _case_id_auto = f"{_equipo_short} - {_dir_str} - ({_mls_str}) - {_tipo_tag_crm}"

    st.info(f"**ID del caso:** `{_case_id_auto}`")

    with st.expander("✏️ Editar ID del caso manualmente", expanded=False):
        _case_id_override = st.text_input(
            "Case ID (override)",
            value="",
            placeholder=_case_id_auto,
            key="nc_override",
        )

    final_case_id = _case_id_override.strip() if _case_id_override.strip() else _case_id_auto

    # ------------------------------------------------------------------
    # Botones de acción
    # ------------------------------------------------------------------
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        btn_local = st.button(
            "📁 Crear caso local",
            use_container_width=True,
            key="nc_btn_local",
        )
    with col_b:
        btn_sudespacho = st.button(
            "⚡ Crear caso + enviar a sudespacho",
            type="primary",
            use_container_width=True,
            key="nc_btn_sudespacho",
        )

    if btn_local or btn_sudespacho:
        # Validación
        _missing = []
        if not direccion.strip():
            _missing.append("dirección")
        if not ref_mls.strip():
            _missing.append("ID GO")
        if ciudad_label == "— sin especificar —":
            _missing.append("ciudad")

        if _missing:
            st.error(f"Completa los campos obligatorios: {', '.join(_missing)}.")
        else:
            # 1. Crear caso local (siempre)
            with st.spinner("Creando caso local…"):
                _path = case_manager.ensure_case(
                    final_case_id,
                    titulo=final_case_id,
                    referencia_crm=final_case_id,
                    cliente="EV MMC SPAIN, S.L.U.",
                    cuantia=cuantia_nc or None,
                )
            st.success(f"Caso local disponible en `{_path}`")

            # 2. Crear expediente en sudespacho (solo si se pulsó ese botón)
            if btn_sudespacho:
                # Tags: rojo (equipo) + verde/lila (tipo caso) + azul (ciudad si procede)
                _tags = [_EQUIPOS[equipo_label]] + _sc.tag_defaults_for_tipo_caso(tipo_caso)
                _ciudad_tag = _CIUDADES.get(ciudad_label)
                if _ciudad_tag:
                    _tags.append(_ciudad_tag)

                # Posición procesal
                _pos = (
                    _sc.POSICION_ACTOR
                    if posicion_de_tipo(tipo_caso) == POSICION_ACTORA
                    else _sc.POSICION_DEMANDADO
                )

                # Nota estándar del tipo de caso
                _nota = _NOTAS.get(tipo_caso, "")

                _datos = _sc.NuevoExpedienteExtrajudicial(
                    referencia_cliente=final_case_id,
                    cuantia=cuantia_nc,
                    tags=_tags,
                    posicion=_pos,
                    descripcion_html=_nota,
                )

                with st.spinner("Creando expediente en sudespacho…"):
                    try:
                        _exp_id = _sc.create_expediente(_datos)
                        case_manager.register_expediente(
                            final_case_id, _exp_id, "extrajudiciales"
                        )
                        st.success(
                            f"✅ Expediente creado en sudespacho — **ID: {_exp_id}**  \n"
                            f"Vinculado en `_caso.md`."
                        )
                    except _sc.SudespachoCreateError as exc:
                        st.error(f"Error al crear el expediente: {exc}")
                    except Exception as exc:
                        st.error(f"Error inesperado: {exc}")


with tab_pipeline:
    st.subheader("Ejecutar pipeline")
    cases = case_manager.list_cases()
    if not cases:
        st.info("Aún no hay casos.")
    else:
        case_id = st.selectbox("Caso", cases)
        col1, col2, col3 = st.columns(3)
        with col1:
            do_sync = st.checkbox("Sincronizar Drive (rclone)", value=False)
        with col2:
            do_demanda = st.checkbox("Generar demanda", value=True)
        with col3:
            drive_remote_path = st.text_input("Remoto rclone (override)")

        if st.button("Ejecutar pipeline", type="primary"):
            with st.spinner("Ejecutando..."):
                pr = pipeline.run(
                    case_id,
                    drive_remote_path=drive_remote_path or None,
                    do_sync=do_sync,
                    do_demanda=do_demanda,
                )
            st.write(f"**Inicio:** {pr.started_at} — **Fin:** {pr.finished_at}")
            st.dataframe(
                [
                    {
                        "paso": s.name,
                        "ok": "✅" if s.ok else "❌",
                        "detalle": s.detail or s.artifact or "",
                    }
                    for s in pr.steps
                ],
                use_container_width=True,
            )


with tab_visor:
    st.subheader("Visor de Markdown")
    cases = case_manager.list_cases()
    if not cases:
        st.info("Aún no hay casos.")
    else:
        case_id = st.selectbox("Caso", cases, key="visor_caso")
        sub = st.selectbox("Subcarpeta", list(CASO_SUBDIRS), key="visor_sub")
        sub_dir = caso_path(case_id) / sub
        files = sorted(sub_dir.rglob("*.md"))
        if not files:
            st.write("_(sin .md en esta fase)_")
        else:
            sel = st.selectbox("Archivo", [str(p.relative_to(sub_dir)) for p in files])
            target = sub_dir / sel
            st.markdown(f"`{target}`")
            st.markdown(target.read_text(encoding="utf-8"))
