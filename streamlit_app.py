"""FeesDefender — Motor de análisis y reclamación de honorarios. UI Streamlit.

La UI no contiene lógica de negocio: solo orquesta llamadas al `core` y
visualiza los `.md` resultantes. Pensada para uso local del abogado.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core import case_manager, llm, pipeline
from core.config import CASO_SUBDIRS, caso_path, settings

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
    st.subheader("Crear caso")
    with st.form("crear_caso"):
        case_id = st.text_input("Case ID", placeholder="EV-2026-001")
        titulo = st.text_input("Título", placeholder="Reclamación honorarios E&V — vivienda calle X")
        cliente = st.text_input("Cliente")
        contraparte = st.text_input("Contraparte")
        organo = st.text_input("Órgano (si conocido)")
        cuantia = st.number_input("Cuantía (€)", min_value=0.0, step=100.0)
        drive_remote_path = st.text_input(
            "Remoto rclone",
            placeholder=f"{settings.rclone_remote}:Casos/EV-2026-001",
        )
        drive_link = st.text_input("Enlace Drive (opcional)")
        submitted = st.form_submit_button("Crear / Asegurar caso")

    if submitted and case_id.strip():
        path = case_manager.ensure_case(
            case_id.strip(),
            titulo=titulo or None,
            cliente=cliente or None,
            contraparte=contraparte or None,
            organo=organo or None,
            cuantia=cuantia or None,
            drive_remote_path=drive_remote_path or None,
            drive_link=drive_link or None,
        )
        st.success(f"Caso disponible en `{path}`")


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
