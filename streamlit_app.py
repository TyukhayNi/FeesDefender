"""FeesDefender — Motor de análisis y reclamación de honorarios. UI Streamlit.

La UI no contiene lógica de negocio: solo orquesta llamadas al `core` y
visualiza los `.md` resultantes. Pensada para uso local del abogado.
"""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from core import case_manager, llm, pipeline, sudespacho_create as _sc
from core.intake_drive import (
    DriveIntakeError,
    DriveFolderInfo as _DriveFolderInfo,
    get_drive_folder_info as _get_drive_folder_info,
    parse_drive_url,
    parse_ev_folder_name as _parse_ev_folder_name,
    pull_drive_ev,
)
from core import intake_manual
from core import share_drive as _sd
import zipfile as _zipfile
from core.sudespacho_relations import (
    NuevoColaborador,
    SudespachoRelationsError as _SRelError,
    ensure_colaborador_vinculado,
    ensure_colaborador_vinculado_judicial,
    find_expediente_judicial_by_referencia as _find_exp_judicial,
    find_expediente_by_referencia as _find_exp_extrajudicial,
    link_ev_mmc,
    link_ev_mmc_judicial,
    search_colaboradores_for_ui as _search_colabs,
    load_all_colaboradores as _load_all_colabs,
)
from core.config import (
    CASO_SUBDIRS,
    caso_path,
    settings,
    TIPOS_CASO_ALL,
    posicion_de_tipo,
    POSICION_ACTORA,
    DRIVE_EV_TEAM_IDS,
)

# ---------------------------------------------------------------------------
# Configuración de página + CSS corporativo Engel & Völkers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _colabs_cache() -> list[dict]:
    """Lista completa de colaboradores del CRM, cacheada 1 hora.

    Lanza excepción si el CRM no está disponible. Streamlit NO cachea
    excepciones, de modo que el próximo intento hará una nueva petición
    en lugar de devolver una lista vacía cacheada por error.
    """
    return _load_all_colabs()


st.set_page_config(
    page_title="FeesDefender · Engel & Völkers",
    page_icon="🏠",
    layout="wide",
)

st.markdown(
    """
<style>
/* ── Tipografía: Montserrat (similar a la fuente corporativa E&V) ── */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Montserrat', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
}

/* ── Header corporativo ── */
.ev-header {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 10px 0 22px 0;
    border-bottom: 2px solid #E2001A;
    margin-bottom: 28px;
}
.ev-logo-sq {
    background: #E2001A;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 1px;
    flex-shrink: 0;
}
.ev-header-text h1 {
    margin: 0 0 3px 0;
    font-size: 1.55rem;
    font-weight: 700;
    color: #1A1A1A;
    letter-spacing: -0.3px;
    line-height: 1.1;
}
.ev-header-text .ev-sub {
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: #888;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    border-right: 2px solid #E2001A;
    background-color: #FAFAFA;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {
    font-weight: 600 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    font-size: 0.72rem !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #E2001A !important;
    border-bottom-color: #E2001A !important;
}

/* ── Labels de campos ── */
.stSelectbox > label,
.stTextInput > label,
.stNumberInput > label {
    font-weight: 600 !important;
    font-size: 0.70rem !important;
    letter-spacing: 0.9px !important;
    text-transform: uppercase !important;
    color: #555 !important;
}

/* ── Botón primario (rojo E&V) ── */
.stButton > button[kind="primary"] {
    background-color: #E2001A !important;
    border-color: #E2001A !important;
    color: #fff !important;
    border-radius: 2px !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #B8001A !important;
    border-color: #B8001A !important;
}

/* ── Botón secundario (negro E&V) ── */
.stButton > button:not([kind="primary"]) {
    border: 2px solid #1A1A1A !important;
    color: #1A1A1A !important;
    background: #fff !important;
    border-radius: 2px !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: #E2001A !important;
    color: #E2001A !important;
    background: #FFF8F8 !important;
}

/* ── Separadores de sección ── */
.ev-section-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #E2001A;
    border-bottom: 1px solid #F0D0D0;
    padding-bottom: 5px;
    margin: 22px 0 14px 0;
}

/* ── Info box (ID del caso) ── */
div[data-testid="stInfoBox"],
.stAlert {
    border-radius: 1px !important;
}

/* ── Inputs: foco con rojo E&V ── */
input:focus, textarea:focus {
    border-color: #E2001A !important;
    box-shadow: 0 0 0 1px rgba(226,0,26,0.20) !important;
}

/* ── Divisor ── */
hr { border-color: #E8E8E8 !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Header corporativo ──────────────────────────────────────────────────────
st.markdown(
    """
<div class="ev-header">
  <div class="ev-logo-sq">
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M13 2L22 7V19L13 24L4 19V7L13 2Z" fill="white" fill-opacity="0.15"/>
      <path d="M13 2L22 7V19L13 24L4 19V7L13 2Z" stroke="white" stroke-width="1.5"/>
      <path d="M8 10H18M8 13H18M8 16H14" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
    </svg>
  </div>
  <div class="ev-header-text">
    <h1>FeesDefender</h1>
    <div class="ev-sub">Motor de honorarios &nbsp;·&nbsp; Engel &amp; Völkers</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Validación de email
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _valid_email(addr: str) -> bool:
    return bool(_EMAIL_RE.match(addr.strip()))


def _email_input_with_crm(
    label: str,
    key: str,
    placeholder: str = "",
    help: str = "",
) -> str:
    """Text input de email con autosugerencia del CRM.

    El usuario escribe y pulsa el botón 🔍 (o Enter) para ver sugerencias.
    Filtra localmente sobre la lista cacheada (_colabs_cache, TTL 1h).
    """
    sugg_key = f"{key}_sugg"
    _error_key = f"{key}_crm_err"

    def _run_search() -> None:
        val = st.session_state.get(key, "").strip().lower()
        if len(val) >= 2:
            try:
                all_colabs = _colabs_cache()
            except Exception as exc:
                st.session_state[_error_key] = str(exc)
                st.session_state.pop(sugg_key, None)
                return
            st.session_state.pop(_error_key, None)
            matches = [
                c for c in all_colabs
                if val in c["label"].lower() or val in c["email"].lower()
            ]
            st.session_state[sugg_key] = matches[:12]
        else:
            st.session_state.pop(sugg_key, None)
            st.session_state.pop(_error_key, None)

    # Preset injection: si "← Usar" escribió un valor en la sesión anterior,
    # copiarlo al widget ANTES de instanciarlo (única ventana válida para hacerlo).
    _preset_key = f"{key}_preset"
    if _preset_key in st.session_state:
        st.session_state[key] = st.session_state.pop(_preset_key)

    # Campo + botón en la misma fila
    _col_input, _col_btn = st.columns([5, 1])
    with _col_input:
        email_val = st.text_input(
            label,
            key=key,
            placeholder=placeholder,
            help=help + " Escribe y pulsa 🔍 (o Enter) para ver sugerencias del CRM.",
            on_change=_run_search,
        )
    with _col_btn:
        st.write("")  # alineación vertical
        if st.button(
            "🔍",
            key=f"{key}_search_btn",
            use_container_width=True,
            help="Buscar este texto en los colaboradores del CRM.",
        ):
            _run_search()
            st.rerun()

    if _crm_err := st.session_state.get(_error_key):
        st.caption(f"⚠️ CRM no disponible: {_crm_err}")

    _sugg = st.session_state.get(sugg_key, [])
    if _sugg:
        _sel_idx = st.selectbox(
            "Sugerencias CRM",
            range(len(_sugg)),
            format_func=lambda i: (
                _sugg[i]["label"]
                + (f"  ·  {_sugg[i]['email']}" if _sugg[i]["email"] else "")
            ),
            key=f"{key}_sel",
            label_visibility="collapsed",
            help="Colaborador encontrado en el CRM. Pulsa «← Usar» para rellenar el campo.",
        )
        _btn_c, _info_c = st.columns([1, 4])
        with _btn_c:
            if st.button(
                "← Usar",
                key=f"{key}_use",
                use_container_width=True,
                help="Rellena el campo con el email del colaborador seleccionado.",
            ):
                _sel = _sugg[_sel_idx]
                # No se puede escribir session_state[key] con widget ya instanciado.
                # Usamos preset_key: en el próximo render se inyecta antes del widget.
                st.session_state[_preset_key] = _sel["email"] or _sel["label"]
                st.session_state.pop(sugg_key, None)
                st.rerun()
        with _info_c:
            if not _sugg[_sel_idx]["email"]:
                st.caption("⚠️ Email no disponible en el CRM — cópialo manualmente.")

    return email_val


def _email_to_nombre(email: str) -> str:
    """Deriva el nombre de un email E&V: nombre.apellido@engelvoelkers.com → 'Nombre Apellido'.

    Funciona con cualquier email: capitaliza las partes del local-part separadas
    por puntos, guiones o guiones bajos. Devuelve cadena vacía si el email es vacío.
    """
    email = email.strip()
    if not email or "@" not in email:
        return ""
    local = email.split("@")[0]
    parts = re.split(r"[.\-_]", local)
    return " ".join(p.capitalize() for p in parts if p)


# Pre-calentamiento silencioso de caché de colaboradores al arrancar la app.
# Así el primer 🔍 es instantáneo sin necesidad de sidebar.
if "_colabs_prewarmed" not in st.session_state:
    try:
        _colabs_cache()
        st.session_state["_colabs_prewarmed"] = True
    except Exception:
        st.session_state["_colabs_prewarmed"] = False

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_nuevo, tab_casos, tab_pipeline, tab_visor = st.tabs(
    ["Nuevo caso", "Casos", "Pipeline", "Visor"]
)


# ── TAB: Casos ─────────────────────────────────────────────────────────────
with tab_casos:
    cases = case_manager.list_cases()
    if not cases:
        st.info("No hay casos. Crea uno desde la pestaña «Nuevo caso».")
    else:
        st.write(f"**{len(cases)}** casos en `{settings.casos_root}`")
        st.dataframe(
            [{"case_id": c} for c in cases],
            use_container_width=True,
        )

        st.divider()
        with st.expander("📥 Pull Drive E&V — caso existente"):
            _caso_sel = st.selectbox(
                "Caso", cases, key="casos_drive_sel",
                help="Selecciona el caso al que quieres vincular la carpeta del Drive E&V.",
            )
            _drive_url_cas = st.text_input(
                "URL carpeta W-XXXXXX",
                placeholder="https://drive.google.com/drive/folders/…",
                key="casos_drive_url",
                help="Pega la URL de la carpeta de la operación en el Drive engelvoelkers.com. El folder ID se extrae automáticamente.",
            )

            # Resolver team_id desde el código de equipo del case_id
            _equipo_code_cas = _caso_sel.split(" - ")[0].strip() if _caso_sel else ""
            _team_id_cas = DRIVE_EV_TEAM_IDS.get(_equipo_code_cas)
            if _team_id_cas:
                st.caption(f"Shared Drive: `{_team_id_cas}` · **{_equipo_code_cas}**")
            else:
                st.caption(f"Equipo `{_equipo_code_cas}` sin Shared Drive configurado.")
                _team_id_cas = st.text_input(
                    "Shared Drive ID (manual)",
                    placeholder="0ADxxxxxxxxxxxxx",
                    key="casos_drive_team_manual",
                    help="ID del Shared Drive raíz de la oficina E&V. Navega al Shared Drive en drive.google.com y copia el ID de la URL.",
                ).strip()

            _force_cas = st.checkbox(
                "Actualizar (re-sincronizar con Drive E&V)",
                key="casos_drive_force",
                help=(
                    "Por defecto el pull se omite si ya se hizo antes. "
                    "Marca esta opción para volver a sincronizar con el Drive E&V "
                    "y descargar documentos nuevos o modificados desde el último pull. "
                    "rclone solo transfiere los archivos que han cambiado, no descarga todo de nuevo."
                ),
            )

            if st.button("⬇️ Pull Drive E&V", key="casos_drive_btn",
                         help="Descarga los documentos de la carpeta W-XXXXXX al caso local. Solo transfiere archivos nuevos o modificados."):

                if not _drive_url_cas.strip():
                    st.error("Introduce la URL de la carpeta W-XXXXXX.")
                elif not _team_id_cas:
                    st.error("Shared Drive ID no disponible — introdúcelo manualmente.")
                else:
                    try:
                        _fid_cas = parse_drive_url(_drive_url_cas)
                    except ValueError as _ve:
                        st.error(f"URL no válida: {_ve}")
                    else:
                        with st.spinner("Descargando documentos del Drive E&V…"):
                            try:
                                _dr_cas = pull_drive_ev(
                                    _caso_sel,
                                    folder_id=_fid_cas,
                                    team_id=_team_id_cas,
                                    force=_force_cas,
                                )
                                if _dr_cas.skipped:
                                    st.info(
                                        f"Ya descargado previamente "
                                        f"({_dr_cas.files_after} archivo/s). "
                                        "Marca «Forzar re-descarga» si quieres actualizar."
                                    )
                                else:
                                    st.success(
                                        f"✅ **{_dr_cas.files_after}** archivo/s descargados "
                                        f"en `00_Input/01_Drive EV/`."
                                    )
                            except DriveIntakeError as _die:
                                st.error(
                                    "❌ Error rclone:  \n"
                                    + "  \n".join(_die.result.errors)
                                )

        st.divider()
        with st.expander("📄 Demanda / documentos judiciales"):
            _caso_dem = st.selectbox(
                "Caso",
                cases,
                key="casos_dem_sel",
                help=(
                    "Selecciona el caso al que quieres subir la demanda "
                    "y demás documentos judiciales."
                ),
            )

            # ── Archivos ya guardados ──────────────────────────────────────
            _dem_files = intake_manual.list_files(_caso_dem)
            if _dem_files:
                st.caption(
                    f"**{len(_dem_files)}** archivo/s en `04_Manual/`:"
                )
                for _df in _dem_files:
                    _size_kb = _df.stat().st_size // 1024
                    st.caption(f"· {_df.name}  ({_size_kb} KB)")
            else:
                st.caption("_(sin documentos judiciales todavía)_")

            st.divider()

            # ── Uploader ───────────────────────────────────────────────────
            _uploaded_dem = st.file_uploader(
                "Subir demanda y documentos judiciales",
                accept_multiple_files=True,
                type=["pdf", "docx", "doc", "jpg", "jpeg", "png", "txt", "eml", "msg", "zip"],
                key="casos_dem_uploader",
                help=(
                    "Sube la demanda y demás documentos judiciales "
                    "(autos, notificaciones, diligencias…). "
                    "Se guardan en `00_Input/04_Manual/`. "
                    "Los archivos **ZIP se descomprimen automáticamente** manteniendo "
                    "la estructura de carpetas interna."
                ),
            )

            if st.button(
                "⬆️ Guardar documentos",
                key="casos_dem_btn",
                disabled=not _uploaded_dem,
                help="Guarda los archivos seleccionados. Los ZIP se descomprimen automáticamente.",
            ):
                _saved_dem = 0
                _errors_dem: list[str] = []
                for _uf in _uploaded_dem:
                    try:
                        _raw = _uf.read()
                        if _uf.name.lower().endswith(".zip"):
                            _extracted = intake_manual.extract_zip(_caso_dem, _raw)
                            _saved_dem += len(_extracted)
                            st.success(
                                f"✅ **{_uf.name}** descomprimido — "
                                f"**{len(_extracted)}** archivo/s extraídos."
                            )
                        else:
                            intake_manual.save_file(_caso_dem, _uf.name, _raw)
                            _saved_dem += 1
                    except _zipfile.BadZipFile:
                        _errors_dem.append(
                            f"{_uf.name}: el archivo no es un ZIP válido."
                        )
                    except Exception as _exc:
                        _errors_dem.append(f"{_uf.name}: {_exc}")

                if _saved_dem and not any(_uf.name.lower().endswith(".zip") for _uf in _uploaded_dem):
                    # Mensaje global solo si no hay ZIPs (los ZIPs ya muestran su propio mensaje)
                    st.success(
                        f"✅ **{_saved_dem}** archivo/s guardados "
                        f"en `04_Manual/`."
                    )
                for _err_dem in _errors_dem:
                    st.error(f"❌ {_err_dem}")

        st.divider()
        with st.expander("🔗 Compartir carpeta E&V con el equipo"):
            _caso_share = st.selectbox(
                "Caso",
                cases,
                key="casos_share_sel",
                help="Selecciona el caso cuya carpeta E&V quieres compartir con el equipo.",
            )

            # ── Carpeta registrada en el caso ──────────────────────────────
            _share_team_id, _share_folder_id = case_manager.get_drive_ev_ids(_caso_share)
            if _share_folder_id:
                _share_folder_url = (
                    f"https://drive.google.com/drive/folders/{_share_folder_id}"
                )
                st.caption(f"Carpeta registrada: [{_share_folder_url}]({_share_folder_url})")
            else:
                st.warning(
                    "Este caso no tiene carpeta E&V registrada. "
                    "Vincúlala primero desde «Pull Drive E&V»."
                )
                _share_url_manual = st.text_input(
                    "URL carpeta W-XXXXXX (manual)",
                    placeholder="https://drive.google.com/drive/folders/…",
                    key="casos_share_url_manual",
                    help="Introduce la URL si aún no has hecho el pull de Drive E&V.",
                ).strip()
                if _share_url_manual:
                    try:
                        _share_folder_id = parse_drive_url(_share_url_manual)
                        _share_folder_url = (
                            f"https://drive.google.com/drive/folders/{_share_folder_id}"
                        )
                    except ValueError:
                        _share_folder_id = None
                        _share_folder_url = _share_url_manual
                else:
                    _share_folder_id = None
                    _share_folder_url = ""

            # ── Equipo al que compartir (fijo) ─────────────────────────────
            st.markdown('<div class="ev-section-label">Se compartirá con</div>', unsafe_allow_html=True)
            for _se in _sd.TEAM_EMAILS:
                st.caption(f"· {_se}")

            st.divider()

            # ── Botones ────────────────────────────────────────────────────
            _col_sh1, _col_sh2 = st.columns(2)

            with _col_sh1:
                _btn_share_direct = st.button(
                    "⚡ Compartir directamente",
                    key="casos_share_direct_btn",
                    disabled=not _share_folder_id,
                    use_container_width=True,
                    help=(
                        "Intenta compartir la carpeta usando las credenciales de "
                        "nikolai.tyukhay@engelvoelkers.com (token rclone.conf). "
                        "Puede fallar si el token está expirado o la política de dominio "
                        "lo impide — en ese caso usa el mensaje de solicitud."
                    ),
                )

            with _col_sh2:
                _btn_share_email = st.button(
                    "📋 Generar mensaje de solicitud",
                    key="casos_share_email_btn",
                    disabled=not _share_folder_url,
                    use_container_width=True,
                    help=(
                        "Genera el mensaje para pedir a un compañero de E&V "
                        "que comparta la carpeta con el equipo."
                    ),
                )

            if _btn_share_direct and _share_folder_id:
                # Aviso si el token puede estar expirado
                if not _sd.is_token_likely_valid():
                    st.warning(
                        "⚠️ El token de rclone parece expirado. "
                        "Ejecuta `rclone ls gdrive_ev:` para refrescarlo y vuelve a intentarlo."
                    )
                else:
                    with st.spinner("Compartiendo carpeta con el equipo…"):
                        try:
                            _share_res = _sd.share_folder_with_team(_share_folder_id)
                            for _r in _share_res.results:
                                if _r.success:
                                    st.success(f"✅ **{_r.email}** — acceso concedido.")
                                else:
                                    st.error(f"❌ **{_r.email}** — {_r.error}")
                            if not _share_res.all_ok:
                                st.info(
                                    "Algunos emails no pudieron compartirse directamente. "
                                    "Usa «Generar mensaje de solicitud» para los que fallaron."
                                )
                        except _sd.ShareDriveConfigError as _sce:
                            st.error(f"Error de configuración: {_sce}")

            if _btn_share_email and _share_folder_url:
                _email_text = _sd.build_request_email(_share_folder_url)
                st.code(_email_text, language=None)
                st.caption("Copia el texto y pégalo en un email a tus compañeros de E&V.")


# ── TAB: Nuevo caso ─────────────────────────────────────────────────────────
with tab_nuevo:
    st.subheader("Nuevo caso")

    _tipo_exp_sel = st.radio(
        "Tipo de expediente",
        ["Extrajudicial", "Judicial"],
        horizontal=True,
        key="nc_tipo_exp",
        help="Extrajudicial: fase previa o reclamación sin demanda interpuesta. Judicial: proceso ya iniciado ante el juzgado.",
    )
    es_judicial = _tipo_exp_sel == "Judicial"

    # ------------------------------------------------------------------
    # Datos maestros
    # ------------------------------------------------------------------

    # Equipos agrupados por ciudad — dict anidado ciudad → {label: tag_rojo}
    _EQUIPOS_POR_CIUDAD: dict[str, dict[str, str]] = {
        "Barcelona": {
            "BaRR1  — BCN Residential Rentals 1":  _sc.TAG_ROJO_BaRR1,
            "BaRR2  — BCN Residential Rentals 2":  _sc.TAG_ROJO_BaRR2,
            "BaRR3  — BCN Residential Rentals 3":  _sc.TAG_ROJO_BaRR3,
            "BaRR4  — BCN Residential Rentals 4":  _sc.TAG_ROJO_BaRR4,
            "BaRR10 — BCN Residential Rentals 10": _sc.TAG_ROJO_BaRR10,
            "BaRS1  — BCN Residential Sales 1":    _sc.TAG_ROJO_BaRS1,
            "BaRS2  — BCN Residential Sales 2":    _sc.TAG_ROJO_BaRS2,
            "BaRS3  — BCN Residential Sales 3":    _sc.TAG_ROJO_BaRS3,
            "BaRS4  — BCN Residential Sales 4":    _sc.TAG_ROJO_BaRS4,
            "BaRS5  — BCN Residential Sales 5":    _sc.TAG_ROJO_BaRS5,
            "BaRS6  — BCN Residential Sales 6":    _sc.TAG_ROJO_BaRS6,
            "BaRS7  — BCN Residential Sales 7":    _sc.TAG_ROJO_BaRS7,
            "BaRS8  — BCN Residential Sales 8":    _sc.TAG_ROJO_BaRS8,
            "BaRS9  — BCN Residential Sales 9":    _sc.TAG_ROJO_BaRS9,
            "BaRS10 — BCN Residential Sales 10":   _sc.TAG_ROJO_BaRS10,
            "BaRS11 — BCN Residential Sales 11":   _sc.TAG_ROJO_BaRS11,
            "BaRS12 — BCN Residential Sales 12":   _sc.TAG_ROJO_BaRS12,
            "BaCR1  — BCN Commercial Rentals 1":   _sc.TAG_ROJO_BaCR1,
            "BaCR2  — BCN Commercial Rentals 2":   _sc.TAG_ROJO_BaCR2,
            "BaCR10 — BCN Commercial Rentals 10":  _sc.TAG_ROJO_BaCR10,
            "BaCS1  — BCN Commercial Sales 1":     _sc.TAG_ROJO_BaCS1,
            "BaCS10 — BCN Commercial Sales 10":    _sc.TAG_ROJO_BaCS10,
            "BaDP1  — BCN (Pendiente) 1":          _sc.TAG_ROJO_BaDP1,
        },
        "Bilbao": {
            "BiRS1  — Bilbao Residential Sales 1": _sc.TAG_ROJO_BiRS1,
            "BiRS2  — Bilbao Residential Sales 2": _sc.TAG_ROJO_BiRS2,
        },
        "Madrid": {
            "MaRR1  — MAD Residential Rentals 1":  _sc.TAG_ROJO_MaRR1,
            "MaRR2  — MAD Residential Rentals 2":  _sc.TAG_ROJO_MaRR2,
            "MaRR3  — MAD Residential Rentals 3":  _sc.TAG_ROJO_MaRR3,
            "MaRS1  — MAD Residential Sales 1":    _sc.TAG_ROJO_MaRS1,
            "MaRS2  — MAD Residential Sales 2":    _sc.TAG_ROJO_MaRS2,
            "MaRS3  — MAD Residential Sales 3":    _sc.TAG_ROJO_MaRS3,
            "MaRS4  — MAD Residential Sales 4":    _sc.TAG_ROJO_MaRS4,
            "MaRS5  — MAD Residential Sales 5":    _sc.TAG_ROJO_MaRS5,
            "MaRS6  — MAD Residential Sales 6":    _sc.TAG_ROJO_MaRS6,
            "MaRS7  — MAD Residential Sales 7":    _sc.TAG_ROJO_MaRS7,
            "MaRS8  — MAD Residential Sales 8":    _sc.TAG_ROJO_MaRS8,
            "MaRS9  — MAD Residential Sales 9":    _sc.TAG_ROJO_MaRS9,
            "MaRS10 — MAD Residential Sales 10":   _sc.TAG_ROJO_MaRS10,
            "MaRS11 — MAD Residential Sales 11":   _sc.TAG_ROJO_MaRS11,
            "MaRS12 — MAD Residential Sales 12":   _sc.TAG_ROJO_MaRS12,
            "MaRS13 — MAD Residential Sales 13":   _sc.TAG_ROJO_MaRS13,
            "MaRS14 — MAD Residential Sales 14":   _sc.TAG_ROJO_MaRS14,
            "MaRS15 — MAD Residential Sales 15":   _sc.TAG_ROJO_MaRS15,
            "MaPD1  — MAD (Pendiente) 1":          _sc.TAG_ROJO_MaPD1,
        },
        "San Sebastián": {
            "SSRR1  — San Sebastián Residential Rentals 1": _sc.TAG_ROJO_SSRR1,
            "SSRS1  — San Sebastián Residential Sales 1":   _sc.TAG_ROJO_SSRS1,
        },
        "Santander": {
            "SaRS1  — Santander Residential Sales 1": _sc.TAG_ROJO_SaRS1,
        },
        "Sevilla": {
            "SeRS1  — Sevilla Residential Sales 1":  _sc.TAG_ROJO_SeRS1,
            "SeRS6  — Sevilla Residential Sales 6":  _sc.TAG_ROJO_SeRS6,
        },
        "Valencia": {
            "VaCR1  — Valencia Commercial Rentals 1":  _sc.TAG_ROJO_VaCR1,
            "VaCR2  — Valencia Commercial Rentals 2":  _sc.TAG_ROJO_VaCR2,
            "VaPD1  — Valencia (pendiente) 1":         _sc.TAG_ROJO_VaPD1,
            "VaRR1  — Valencia Residential Rentals 1": _sc.TAG_ROJO_VaRR1,
            "VaRR3  — Valencia Residential Rentals 3": _sc.TAG_ROJO_VaRR3,
            "VaRS1  — Valencia Residential Sales 1":   _sc.TAG_ROJO_VaRS1,
            "VaRS2  — Valencia Residential Sales 2":   _sc.TAG_ROJO_VaRS2,
            "VaRS3  — Valencia Residential Sales 3":   _sc.TAG_ROJO_VaRS3,
            "VaRS4  — Valencia Residential Sales 4":   _sc.TAG_ROJO_VaRS4,
            "VaRS5  — Valencia Residential Sales 5":   _sc.TAG_ROJO_VaRS5,
        },
    }

    # Dict plano completo (para lookup de tags al construir el expediente)
    _EQUIPOS: dict[str, str] = {
        k: v for equipos in _EQUIPOS_POR_CIUDAD.values() for k, v in equipos.items()
    }

    _CIUDADES: dict[str, str | None] = {
        "— selecciona ciudad —": None,
        "Barcelona":     _sc.TAG_AZUL_BARCELONA,
        "Bilbao":        _sc.TAG_AZUL_BILBAO,
        "Madrid":        _sc.TAG_AZUL_MADRID,
        "San Sebastián": _sc.TAG_AZUL_SAN_SEBASTIAN,
        "Santander":     _sc.TAG_AZUL_SANTANDER,
        "Sevilla":       _sc.TAG_AZUL_SEVILLA,
        "Valencia":      _sc.TAG_AZUL_VALENCIA,
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

    # Equipos judiciales — grupo 2 (J_TAG_* del módulo sudespacho_create)
    _J_EQUIPOS_POR_CIUDAD: dict[str, dict[str, str]] = {
        "Barcelona": {
            "BaRR1  — BCN Residential Rentals 1":  _sc.J_TAG_ROJO_BaRR1,
            "BaRR2  — BCN Residential Rentals 2":  _sc.J_TAG_ROJO_BaRR2,
            "BaRR3  — BCN Residential Rentals 3":  _sc.J_TAG_ROJO_BaRR3,
            "BaRR4  — BCN Residential Rentals 4":  _sc.J_TAG_ROJO_BaRR4,
            "BaRR10 — BCN Residential Rentals 10": _sc.J_TAG_AZUL_BaRR10,
            "BaRS1  — BCN Residential Sales 1":    _sc.J_TAG_ROJO_BaRS1,
            "BaRS2  — BCN Residential Sales 2":    _sc.J_TAG_ROJO_BaRS2,
            "BaRS3  — BCN Residential Sales 3":    _sc.J_TAG_ROJO_BaRS3,
            "BaRS4  — BCN Residential Sales 4":    _sc.J_TAG_AZUL_BaRS4,
            "BaRS5  — BCN Residential Sales 5":    _sc.J_TAG_ROJO_BaRS5,
            "BaRS6  — BCN Residential Sales 6":    _sc.J_TAG_ROJO_BaRS6,
            "BaRS7  — BCN Residential Sales 7":    _sc.J_TAG_ROJO_BaRS7,
            "BaRS8  — BCN Residential Sales 8":    _sc.J_TAG_ROJO_BaRS8,
            "BaRS9  — BCN Residential Sales 9":    _sc.J_TAG_ROJO_BaRS9,
            "BaRS10 — BCN Residential Sales 10":   _sc.J_TAG_ROJO_BaRS10,
            "BaRS11 — BCN Residential Sales 11":   _sc.J_TAG_ROJO_BaRS11,
            "BaRS12 — BCN Residential Sales 12":   _sc.J_TAG_ROJO_BaRS12,
            "BaCR1  — BCN Commercial Rentals 1":   _sc.J_TAG_ROJO_BaCR1,
            "BaCR10 — BCN Commercial Rentals 10":  _sc.J_TAG_ROJO_BaCR10,
            "BaCS1  — BCN Commercial Sales 1":     _sc.J_TAG_ROJO_BaCS1,
            "BaCS2  — BCN Commercial Sales 2":     _sc.J_TAG_AZUL_BaCS2,
            "BaDP1  — BCN (pendiente) 1":          _sc.J_TAG_ROJO_BaDP1,
        },
        "Bilbao": {
            "BiRS1  — Bilbao Residential Sales 1": _sc.J_TAG_ROJO_BiRS1,
            "BiRS2  — Bilbao Residential Sales 2": _sc.J_TAG_ROJO_BiRS2,
        },
        "Madrid": {
            "MaRR1  — MAD Residential Rentals 1":  _sc.J_TAG_ROJO_MaRR1,
            "MaRR2  — MAD Residential Rentals 2":  _sc.J_TAG_AZUL_MaRR2,
            "MaRR3  — MAD Residential Rentals 3":  _sc.J_TAG_ROJO_MaRR3,
            "MaRS1  — MAD Residential Sales 1":    _sc.J_TAG_ROJO_MaRS1,
            "MaRS2  — MAD Residential Sales 2":    _sc.J_TAG_ROJO_MaRS2,
            "MaRS3  — MAD Residential Sales 3":    _sc.J_TAG_ROJO_MaRS3,
            "MaRS4  — MAD Residential Sales 4":    _sc.J_TAG_ROJO_MaRS4,
            "MaRS5  — MAD Residential Sales 5":    _sc.J_TAG_ROJO_MaRS5,
            "MaRS6  — MAD Residential Sales 6":    _sc.J_TAG_ROJO_MaRS6,
            "MaRS7  — MAD Residential Sales 7":    _sc.J_TAG_ROJO_MaRS7,
            "MaRS8  — MAD Residential Sales 8":    _sc.J_TAG_ROJO_MaRS8,
            "MaRS9  — MAD Residential Sales 9":    _sc.J_TAG_ROJO_MaRS9,
            "MaRS10 — MAD Residential Sales 10":   _sc.J_TAG_ROJO_MaRS10,
            "MaRS11 — MAD Residential Sales 11":   _sc.J_TAG_ROJO_MaRS11,
            "MaRS12 — MAD Residential Sales 12":   _sc.J_TAG_ROJO_MaRS12,
            "MaRS13 — MAD Residential Sales 13":   _sc.J_TAG_ROJO_MaRS13,
            "MaRS14 — MAD Residential Sales 14":   _sc.J_TAG_ROJO_MaRS14,
            "MaRS15 — MAD Residential Sales 15":   _sc.J_TAG_ROJO_MaRS15,
            "MaPD1  — MAD (pendiente) 1":          _sc.J_TAG_ROJO_MaPD1,
        },
        "San Sebastián": {
            "SSRR1  — San Sebastián Residential Rentals 1": _sc.J_TAG_ROJO_SSRR1,
            "SSRS1  — San Sebastián Residential Sales 1":   _sc.J_TAG_ROJO_SSRS1,
        },
        "Santander": {
            "SaRS1  — Santander Residential Sales 1": _sc.J_TAG_ROJO_SaRS1,
        },
        "Sevilla": {
            "SeRS1  — Sevilla Residential Sales 1":  _sc.J_TAG_ROJO_SeRS1,
            "SeRS6  — Sevilla Residential Sales 6":  _sc.J_TAG_ROJO_SeRS6,
        },
        "Valencia": {
            "VaCR1  — Valencia Commercial Rentals 1":  _sc.J_TAG_ROJO_VaCR1,
            "VaCR2  — Valencia Commercial Rentals 2":  _sc.J_TAG_ROJO_VaCR2,
            "VaCS1  — Valencia Commercial Sales 1":    _sc.J_TAG_AZUL_VaCS1,
            "VaPD1  — Valencia (pendiente) 1":         _sc.J_TAG_ROJO_VaPD1,
            "VaRR1  — Valencia Residential Rentals 1": _sc.J_TAG_ROJO_VaRR1,
            "VaRR3  — Valencia Residential Rentals 3": _sc.J_TAG_ROJO_VaRR3,
            "VaRS1  — Valencia Residential Sales 1":   _sc.J_TAG_ROJO_VaRS1,
            "VaRS2  — Valencia Residential Sales 2":   _sc.J_TAG_ROJO_VaRS2,
            "VaRS3  — Valencia Residential Sales 3":   _sc.J_TAG_ROJO_VaRS3,
            "VaRS4  — Valencia Residential Sales 4":   _sc.J_TAG_ROJO_VaRS4,
            "VaRS5  — Valencia Residential Sales 5":   _sc.J_TAG_ROJO_VaRS5,
        },
    }
    _J_EQUIPOS: dict[str, str] = {
        k: v for equipos in _J_EQUIPOS_POR_CIUDAD.values() for k, v in equipos.items()
    }
    _J_CIUDADES: dict[str, str | None] = {
        "— selecciona ciudad —": None,
        "Barcelona":     _sc.J_TAG_AZUL_CIUDAD_BARCELONA,
        "Bilbao":        _sc.J_TAG_AZUL_CIUDAD_BILBAO,
        "Madrid":        _sc.J_TAG_AZUL_CIUDAD_MADRID,
        "San Sebastián": _sc.J_TAG_AZUL_CIUDAD_SAN_SEBASTIAN,
        "Santander":     _sc.J_TAG_AZUL_CIUDAD_SANTANDER,
        "Sevilla":       _sc.J_TAG_AZUL_CIUDAD_SEVILLA,
        "Valencia":      _sc.J_TAG_AZUL_CIUDAD_VALENCIA,
    }

    # Selección activa según tipo de expediente
    _EQUIPOS_ACTIVOS_POR_CIUDAD = _J_EQUIPOS_POR_CIUDAD if es_judicial else _EQUIPOS_POR_CIUDAD
    _EQUIPOS_ACTIVOS            = _J_EQUIPOS            if es_judicial else _EQUIPOS
    _CIUDADES_ACTIVAS           = _J_CIUDADES           if es_judicial else _CIUDADES

    # ------------------------------------------------------------------
    # Detectar cambio de modo judicial/extrajudicial y limpiar caché
    # Si el usuario cambia entre Judicial y Extrajudicial, los dicts de
    # equipos cambian y el auto-fill previo queda inválido. Limpiamos el
    # estado para que el bloque de auto-fill re-ejecute con el dict correcto.
    # ------------------------------------------------------------------
    _prev_judicial = st.session_state.get("_nc_prev_es_judicial")
    if _prev_judicial is not None and bool(_prev_judicial) != es_judicial:
        for _k in ("_nc_drive_autofilled_fid", "_nc_autofill_team_id",
                   "nc_ciudad", "nc_equipo", "nc_dir", "nc_mls"):
            st.session_state.pop(_k, None)
    st.session_state["_nc_prev_es_judicial"] = es_judicial

    # ------------------------------------------------------------------
    # Helper: driveId → (ciudad_label, equipo_label)
    # ------------------------------------------------------------------
    def _resolve_equipo_from_drive_id(
        drive_id: str,
        equipos_por_ciudad: dict,
    ) -> tuple[str, str] | None:
        """Devuelve (ciudad_label, equipo_label) dado un Shared Drive ID.

        Busca en DRIVE_EV_TEAM_IDS el equipo_code que corresponde al driveId,
        luego lo cruza con el diccionario equipos_por_ciudad para obtener las
        etiquetas de selectbox. Devuelve None si no se encuentra.
        """
        # Construir mapa inverso: drive_id → equipo_code
        # (varios equipos pueden compartir el mismo Shared Drive)
        _rev = {v: k for k, v in DRIVE_EV_TEAM_IDS.items()}
        equipo_code = _rev.get(drive_id)
        if not equipo_code:
            return None
        for ciudad, equipos in equipos_por_ciudad.items():
            for eq_label in equipos:
                if eq_label.startswith(equipo_code):
                    return ciudad, eq_label
        return None

    # ------------------------------------------------------------------
    # Auto-fill desde Drive E&V (antes de renderizar widgets)
    # Lee nc_drive_url del session_state (ya persistido del render anterior).
    # Sin st.rerun(): los valores se inyectan directamente en session_state.
    # ------------------------------------------------------------------
    _drive_url_cached = st.session_state.get("nc_drive_url", "").strip()
    if _drive_url_cached:
        try:
            _fid_cached = parse_drive_url(_drive_url_cached)
            if st.session_state.get("_nc_drive_autofilled_fid") != _fid_cached:
                with st.spinner("Obteniendo metadatos de carpeta…"):
                    _folder_info_top = _get_drive_folder_info(_fid_cached)
                st.session_state["_nc_drive_autofilled_fid"] = _fid_cached
                if _folder_info_top:
                    # Dirección e ID GO
                    _auto_dir_top, _auto_mls_top = _parse_ev_folder_name(_folder_info_top.name)
                    if _auto_dir_top and not st.session_state.get("nc_dir"):
                        st.session_state["nc_dir"] = _auto_dir_top
                    if _auto_mls_top and not st.session_state.get("nc_mls"):
                        st.session_state["nc_mls"] = _auto_mls_top
                    # Shared Drive ID (para el pull)
                    if _folder_info_top.drive_id:
                        st.session_state["_nc_autofill_team_id"] = _folder_info_top.drive_id
                        # Ciudad y equipo comercial
                        _eq_resolved = _resolve_equipo_from_drive_id(
                            _folder_info_top.drive_id, _EQUIPOS_ACTIVOS_POR_CIUDAD
                        )
                        if _eq_resolved:
                            _auto_ciudad, _auto_equipo = _eq_resolved
                            # Auto-fill ciudad y equipo solo si ciudad está todavía
                            # en el placeholder de selección (usuario no ha tocado nada)
                            if st.session_state.get("nc_ciudad", "— selecciona ciudad —") == "— selecciona ciudad —":
                                st.session_state["nc_ciudad"] = _auto_ciudad
                                st.session_state["nc_equipo"] = _auto_equipo
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # § 0 — Fuente documental Drive E&V (campo principal — va al inicio)
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="ev-section-label">Drive E&amp;V — carpeta de la operación</div>',
        unsafe_allow_html=True,
    )

    _drive_url_label = "URL carpeta W-XXXXXX *" if es_judicial else "URL carpeta W-XXXXXX"
    drive_url_input = st.text_input(
        _drive_url_label,
        placeholder="https://drive.google.com/drive/folders/1BxiMV…",
        key="nc_drive_url",
        help=(
            "Pega la URL de la carpeta de la operación en el Drive engelvoelkers.com. "
            "Ciudad, equipo, dirección e ID GO se autorellenan automáticamente."
            + (" Obligatorio para expedientes judiciales: es la fuente de los documentos del procedimiento." if es_judicial else "")
        ),
    )

    # Captions de feedback: folder_id + auto-fill aplicado
    if drive_url_input.strip():
        try:
            _fid_preview = parse_drive_url(drive_url_input)
            _preview_parts = [f"folder ID: `{_fid_preview}`"]
            _autofilled_team = st.session_state.get("_nc_autofill_team_id", "")
            if _autofilled_team:
                # Mostrar qué equipo/Shared Drive se detectó
                _eq_rev = {v: k for k, v in DRIVE_EV_TEAM_IDS.items()}
                _detected_code = _eq_rev.get(_autofilled_team, "")
                _preview_parts.append(f"Shared Drive: `{_autofilled_team}`" + (f" ({_detected_code})" if _detected_code else ""))
            _autofill_dir = st.session_state.get("nc_dir", "")
            _autofill_mls = st.session_state.get("nc_mls", "")
            _autofill_ciudad = st.session_state.get("nc_ciudad", "")
            if st.session_state.get("_nc_drive_autofilled_fid") == _fid_preview:
                _af_parts = []
                if _autofill_ciudad and _autofill_ciudad != "— selecciona ciudad —":
                    _af_parts.append(f"Ciudad: **{_autofill_ciudad}**")
                if _autofill_dir:
                    _af_parts.append(f"Dir: **{_autofill_dir}**")
                if _autofill_mls:
                    _af_parts.append(f"ID GO: **{_autofill_mls}**")
                if _af_parts:
                    _preview_parts.append("💡 " + " · ".join(_af_parts))
            st.caption(" · ".join(_preview_parts))
            if st.session_state.get("_nc_drive_autofilled_fid") == _fid_preview and _af_parts:
                st.info(
                    "Los campos marcados con 💡 se han rellenado automáticamente a partir "
                    "de la URL del Drive. Verifica que los datos son correctos antes de continuar.",
                    icon="ℹ️",
                )
        except ValueError:
            st.caption("⚠️ URL no reconocida — revisa el formato.")

    # ------------------------------------------------------------------
    # § 1 — Ciudad y tipo de caso
    # ------------------------------------------------------------------
    st.markdown('<div class="ev-section-label">Operación</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        ciudad_label = st.selectbox(
            "Ciudad *",
            list(_CIUDADES_ACTIVAS.keys()),
            key="nc_ciudad",
            help="Ciudad de la oficina E&V responsable de la operación. Filtra el selector de equipos.",
        )
    with col2:
        tipo_caso = st.selectbox(
            "Tipo de caso *",
            list(TIPOS_CASO_ALL.keys()),
            format_func=lambda k: TIPOS_CASO_ALL[k][0].capitalize(),
            key="nc_tipo",
            help="Tipo de incumplimiento o reclamación. Determina los tags CRM, la posición procesal y la nota estándar del expediente.",
        )

    # ------------------------------------------------------------------
    # § 2 — Equipo comercial (filtrado por ciudad)
    # ------------------------------------------------------------------
    if ciudad_label == "— selecciona ciudad —":
        _equipos_disp = _EQUIPOS_ACTIVOS
    else:
        _equipos_disp = _EQUIPOS_ACTIVOS_POR_CIUDAD.get(ciudad_label, _EQUIPOS_ACTIVOS)

    equipo_label = st.selectbox(
        "Equipo comercial *",
        list(_equipos_disp.keys()),
        key="nc_equipo",
        help="Selecciona primero la ciudad para filtrar los equipos disponibles.",
    )

    # ------------------------------------------------------------------
    # § 3 — Inmueble
    # ------------------------------------------------------------------
    st.markdown('<div class="ev-section-label">Inmueble</div>', unsafe_allow_html=True)

    col3, col4 = st.columns([3, 1])
    with col3:
        direccion = st.text_input(
            "Dirección operación *",
            placeholder="Gran Via 40, 3º 1ª",
            key="nc_dir",
            help="Dirección completa del inmueble. Se usa para construir el ID del caso.",
        )
    with col4:
        ref_mls = st.text_input(
            "ID GO *",
            placeholder="W-030LFT",
            key="nc_mls",
            help="Referencia de la operación en el MLS de E&V (formato W-XXXXXX). Identifica unívocamente la operación.",
        )

    col5, col6 = st.columns(2)
    with col5:
        cuantia_nc = st.number_input(
            "Cuantía reclamada (€)",
            min_value=0.0,
            step=100.0,
            key="nc_cuantia",
            help="Importe de los honorarios reclamados en euros. Se registra en el expediente del CRM. Déjalo en 0 si no se conoce todavía.",
        )
    # col6 libre — reservado para campo futuro

    # ------------------------------------------------------------------
    # § 3b — Datos judiciales (solo visible si tipo = Judicial)
    # ------------------------------------------------------------------
    if es_judicial:
        st.markdown(
            '<div class="ev-section-label">Datos judiciales</div>',
            unsafe_allow_html=True,
        )
        _TIPOS_PROC_LABELS: dict[str, str] = {
            _sc.TIPO_PROC_JUICIO_VERBAL:              "Juicio verbal",
            _sc.TIPO_PROC_JUICIO_ORDINARIO:           "Juicio ordinario",
            _sc.TIPO_PROC_MONITORIO:                  "Monitorio",
            _sc.TIPO_PROC_DESAHUCIO:                  "Desahucio",
            _sc.TIPO_PROC_APELACION:                  "Recurso de apelación",
            _sc.TIPO_PROC_CONCILIACION:               "Conciliación",
            _sc.TIPO_PROC_EJECUCION:                  "Ejecución de títulos judiciales",
            _sc.TIPO_PROC_RECLAMACION_EXTRAJUDICIAL:  "Reclamación extrajudicial",
        }
        tipo_proc_sel = st.selectbox(
            "Tipo de procedimiento *",
            list(_TIPOS_PROC_LABELS.keys()),
            format_func=lambda k: _TIPOS_PROC_LABELS[k],
            key="nc_tipo_proc",
            help=(
                "Tipo de procedimiento judicial. "
                "Juicio verbal es el más frecuente para reclamaciones E&V por cuantía < 6.000 €."
            ),
        )
    else:
        tipo_proc_sel = _sc.TIPO_PROC_JUICIO_VERBAL   # valor por defecto, no se envía

    # ------------------------------------------------------------------
    # § 4 — Contactos del equipo
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="ev-section-label">Contactos del equipo</div>',
        unsafe_allow_html=True,
    )

    # -- Campos de email con autosugerencia CRM -----------------------
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        mail_tl = _email_input_with_crm(
            "Mail Team Leader *",
            key="nc_mail_tl",
            placeholder="teamleader@engelvoelkers.com",
            help="Email corporativo del Team Leader. Se usará para crear o vincular el colaborador en el CRM. El nombre se deriva automáticamente del email.",
        )
    with col_m2:
        mail_captador = _email_input_with_crm(
            "Mail Consultor Captador *",
            key="nc_mail_captador",
            placeholder="captador@engelvoelkers.com",
            help="Email del consultor que captó la operación. Se vinculará como colaborador en el expediente del CRM.",
        )

    col_m3, col_m4 = st.columns(2)
    with col_m3:
        mail_buscador = _email_input_with_crm(
            "Mail Consultor Buscador",
            key="nc_mail_buscador",
            placeholder="buscador@engelvoelkers.com",
            help="Opcional. Se usa cuando hay consultor de la parte buscadora.",
        )
    with col_m4:
        mail_otros = _email_input_with_crm(
            "Mail Otros implicados",
            key="nc_mail_otros",
            placeholder="otros@engelvoelkers.com",
            help="Opcional. Cualquier otro interviniente en la operación.",
        )

    # Nombres derivados automáticamente de los emails (sin campos manuales)
    nombre_tl       = _email_to_nombre(mail_tl)
    nombre_captador = _email_to_nombre(mail_captador)
    nombre_buscador = _email_to_nombre(mail_buscador)
    nombre_otros    = _email_to_nombre(mail_otros)

    # ------------------------------------------------------------------
    # Resolución del Shared Drive ID para el pull
    # Prioridad: (1) auto-fill desde Drive API  (2) lookup por equipo  (3) fallback manual
    # ------------------------------------------------------------------
    _equipo_code_resolved  = equipo_label.split("—")[0].strip()
    _team_from_api         = st.session_state.get("_nc_autofill_team_id", "")
    _team_from_equipo      = DRIVE_EV_TEAM_IDS.get(_equipo_code_resolved, "")
    drive_team_id_resolved = _team_from_api or _team_from_equipo

    if not drive_team_id_resolved:
        with st.expander("⚙️ Shared Drive ID (manual)", expanded=False):
            drive_team_id_resolved = st.text_input(
                "Shared Drive ID",
                placeholder="0ADxxxxxxxxxxxxx",
                key="nc_drive_team_id_fallback",
                help="Abre el Shared Drive en drive.google.com y copia el ID alfanumérico de la URL. Solo es necesario si el equipo no aparece configurado.",
            ).strip()

    # ------------------------------------------------------------------
    # Preview del case_id (live)
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="ev-section-label">Identificador del caso</div>',
        unsafe_allow_html=True,
    )

    _equipo_short  = equipo_label.split("—")[0].strip()
    _tipo_tag_crm  = TIPOS_CASO_ALL[tipo_caso][0].capitalize()
    _dir_str       = direccion.strip() or "‹dirección›"
    _mls_str       = ref_mls.strip() or "W-XXXXXX"
    _case_id_auto  = f"{_equipo_short} - {_dir_str} - ({_mls_str}) - {_tipo_tag_crm}"

    st.info(f"**ID del caso:** `{_case_id_auto}`")

    with st.expander("✏️ Editar ID del caso manualmente", expanded=False):
        _case_id_override = st.text_input(
            "Case ID (override)",
            value="",
            placeholder=_case_id_auto,
            key="nc_override",
            help="Edita el ID del caso solo si el generado automáticamente no es correcto. Se usa como nombre de carpeta y referencia en el CRM.",
        )

    final_case_id = (
        _case_id_override.strip() if _case_id_override.strip() else _case_id_auto
    )

    # ------------------------------------------------------------------
    # Checks de existencia: carpeta local + expedientes CRM ya registrados
    # ------------------------------------------------------------------
    _case_status   = case_manager.get_case_status(final_case_id)
    _local_exists  = _case_status["local_exists"]
    _exp_existentes: list[dict] = _case_status["expedientes"]

    _block_local = False
    _block_crm   = False

    if _local_exists:
        st.warning(
            f"⚠️ La carpeta **`{final_case_id}`** ya existe en CASOS. "
            "Su contenido no se sobreescribirá.",
            icon="📁",
        )
        _confirmar_local = st.checkbox(
            "Entendido — continuar con la carpeta existente",
            key="nc_confirm_local",
            help=(
                "La carpeta local ya existe. Marca para confirmar que quieres "
                "usar la carpeta existente y proceder."
            ),
        )
        _block_local = not _confirmar_local

    if _exp_existentes:
        _exp_resumen = ", ".join(
            f"`{e.get('element', '?')}` ID **{e.get('id', '?')}**"
            for e in _exp_existentes
        )
        st.warning(
            f"⚠️ Este caso ya tiene expediente/s registrado/s en el CRM: {_exp_resumen}. "
            "Al enviar a sudespacho solo se actualizarán relaciones y se hará el pull "
            "(no se creará un expediente duplicado).",
            icon="🗂️",
        )
        _confirmar_crm = st.checkbox(
            "Entendido — continuar (actualizar relaciones y pull)",
            key="nc_confirm_crm",
            help=(
                "El expediente CRM ya existe. Marca para confirmar que quieres "
                "proceder: se actualizarán las relaciones y se realizará el pull del Drive."
            ),
        )
        _block_crm = not _confirmar_crm

    _btn_disabled = _block_local or _block_crm

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
            disabled=_btn_disabled,
            help="Crea la estructura de carpetas del caso en el Drive de Tyukhay Legal. No crea expediente en el CRM.",
        )
    with col_b:
        btn_sudespacho = st.button(
            "⚡ Crear caso + enviar a sudespacho",
            type="primary",
            use_container_width=True,
            key="nc_btn_sudespacho",
            disabled=_btn_disabled,
            help="Crea el caso local Y el expediente en el CRM sudespacho.net, vinculando EV MMC SPAIN como cliente y los consultores como colaboradores.",
        )

    if btn_local or btn_sudespacho:
        # ── Validación ─────────────────────────────────────────────────
        _missing: list[str] = []

        if not direccion.strip():
            _missing.append("Dirección")
        if not ref_mls.strip():
            _missing.append("ID GO")
        if ciudad_label == "— selecciona ciudad —":
            _missing.append("Ciudad")

        # Email Team Leader (obligatorio)
        if not mail_tl.strip():
            _missing.append("Mail Team Leader")
        elif not _valid_email(mail_tl):
            _missing.append("Mail Team Leader — formato inválido")

        # Email Consultor Captador (obligatorio)
        if not mail_captador.strip():
            _missing.append("Mail Consultor Captador")
        elif not _valid_email(mail_captador):
            _missing.append("Mail Consultor Captador — formato inválido")

        # URL Drive E&V (obligatoria para judiciales)
        if es_judicial and not drive_url_input.strip():
            _missing.append("URL carpeta Drive E&V (obligatoria para expedientes judiciales)")

        # Email Consultor Buscador (opcional — solo validar formato si se rellena)
        if mail_buscador.strip() and not _valid_email(mail_buscador):
            _missing.append("Mail Consultor Buscador — formato inválido")

        # Email Otros implicados (opcional — solo validar formato si se rellena)
        if mail_otros.strip() and not _valid_email(mail_otros):
            _missing.append("Mail Otros implicados — formato inválido")

        if _missing:
            st.error(
                "Completa o corrige los siguientes campos: **"
                + "**, **".join(_missing)
                + "**."
            )
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

            # 1b. Persistir IDs del Drive E&V en _caso.md antes del pull
            # — Si PS se cierra durante el pull, la URL queda guardada y no hay que reintroducirla.
            _pre_url = drive_url_input.strip()
            _pre_team = drive_team_id_resolved
            if _pre_url and _pre_team:
                try:
                    _pre_fid = parse_drive_url(_pre_url)
                    case_manager.register_drive_ev(final_case_id, team_id=_pre_team, folder_id=_pre_fid)
                except Exception:
                    pass  # No bloqueante — el pull lo reintentará si es necesario

            # 2. Crear expediente en sudespacho (solo si se pulsó ese botón)
            # — Va antes del pull para que un cierre inesperado no impida registrar el expediente en el CRM.
            if btn_sudespacho:
                # ── Guardia anti-duplicados ─────────────────────────────────
                # Busca en el CRM si ya existe un expediente con esta referencia.
                # Si existe, bloquea y muestra el ID salvo que el usuario haya
                # confirmado explícitamente en el render anterior.
                _dup_confirm_key = f"_dup_confirmed_{final_case_id}"
                _dup_id: str | None = None
                try:
                    with st.spinner("Verificando duplicados en el CRM…"):
                        _finder = (
                            _find_exp_judicial
                            if es_judicial
                            else _find_exp_extrajudicial
                        )
                        _dup_id = _finder(final_case_id)
                except _SRelError as _dup_err:
                    st.warning(
                        f"⚠️ No se pudo verificar duplicados en el CRM: {_dup_err}  \n"
                        "Puedes continuar bajo tu responsabilidad."
                    )

                if _dup_id and not st.session_state.get(_dup_confirm_key):
                    st.error(
                        f"⚠️ Ya existe un expediente con esta referencia en sudespacho "
                        f"(**ID: {_dup_id}**).  \n"
                        "Si quieres crearlo igualmente, pulsa **Confirmar de todos modos**."
                    )
                    if st.button(
                        "Confirmar de todos modos",
                        key=f"_dup_confirm_btn_{final_case_id}",
                        type="secondary",
                        help="Crea el expediente aunque ya exista uno con la misma referencia.",
                    ):
                        st.session_state[_dup_confirm_key] = True
                        st.rerun()
                    st.stop()

                # Limpiar flag de confirmación tras pasar la guardia
                st.session_state.pop(_dup_confirm_key, None)

                # Posición procesal (común a ambos tipos)
                _pos = (
                    _sc.POSICION_ACTOR
                    if posicion_de_tipo(tipo_caso) == POSICION_ACTORA
                    else _sc.POSICION_DEMANDADO
                )
                # Nota estándar del tipo de caso (común)
                _nota = _NOTAS.get(tipo_caso, "")

                if es_judicial:
                    # Tags grupo 2 (J_TAG_*)
                    _tags = (
                        [_EQUIPOS_ACTIVOS[equipo_label]]
                        + _sc.tag_defaults_for_tipo_caso_judicial(tipo_caso)
                    )
                    _ciudad_tag = _CIUDADES_ACTIVAS.get(ciudad_label)
                    if _ciudad_tag:
                        _tags.append(_ciudad_tag)
                    _datos = _sc.NuevoExpedienteJudicial(
                        referencia_cliente=final_case_id,
                        cuantia=cuantia_nc,
                        tags=_tags,
                        posicion=_pos,
                        tipo_procedimiento=tipo_proc_sel,
                        NIG="",
                        notas_html=_nota,
                    )
                    _tipo_registro = "judiciales"
                    _label_tipo    = "judicial"
                    _spinner_msg   = "Creando expediente judicial en sudespacho…"
                else:
                    # Tags grupo 1 (TAG_*)
                    _tags = (
                        [_EQUIPOS_ACTIVOS[equipo_label]]
                        + _sc.tag_defaults_for_tipo_caso(tipo_caso)
                    )
                    _ciudad_tag = _CIUDADES_ACTIVAS.get(ciudad_label)
                    if _ciudad_tag:
                        _tags.append(_ciudad_tag)
                    _datos = _sc.NuevoExpedienteExtrajudicial(
                        referencia_cliente=final_case_id,
                        cuantia=cuantia_nc,
                        tags=_tags,
                        posicion=_pos,
                        descripcion_html=_nota,
                    )
                    _tipo_registro = "extrajudiciales"
                    _label_tipo    = "extrajudicial"
                    _spinner_msg   = "Creando expediente en sudespacho…"

                with st.spinner(_spinner_msg):
                    try:
                        if es_judicial:
                            _exp_id = _sc.create_expediente_judicial(_datos)
                        else:
                            _exp_id = _sc.create_expediente(_datos)
                        case_manager.register_expediente(
                            final_case_id, _exp_id, _tipo_registro
                        )
                        st.success(
                            f"✅ Expediente {_label_tipo} creado en sudespacho — **ID: {_exp_id}**  \n"
                            f"Vinculado en `_caso.md`."
                        )
                        # 3b. Vincular EV MMC SPAIN, S.L.U. como cliente
                        try:
                            if es_judicial:
                                link_ev_mmc_judicial(_exp_id)
                            else:
                                link_ev_mmc(_exp_id)
                            st.success("✅ Cliente **EV MMC SPAIN, S.L.U.** vinculado.")
                        except _SRelError as exc:
                            st.warning(f"⚠️ No se pudo vincular EV MMC: {exc}")

                        # 3c. Vincular colaboradores del equipo
                        _colaboradores_ui: list[tuple[str, str]] = [
                            (nombre_tl.strip(),        mail_tl.strip()),
                            (nombre_captador.strip(),  mail_captador.strip()),
                            (nombre_buscador.strip(),  mail_buscador.strip()),
                            (nombre_otros.strip(),     mail_otros.strip()),
                        ]
                        _col_a_vincular = [
                            (n, m) for n, m in _colaboradores_ui if n and m
                        ]
                        if _col_a_vincular:
                            with st.spinner(
                                f"Vinculando {len(_col_a_vincular)} colaborador/es…"
                            ):
                                for _nc, _mc in _col_a_vincular:
                                    try:
                                        if es_judicial:
                                            _cid, _created = ensure_colaborador_vinculado_judicial(
                                                _exp_id,
                                                NuevoColaborador(nombre=_nc, email=_mc),
                                            )
                                        else:
                                            _cid, _created = ensure_colaborador_vinculado(
                                                _exp_id,
                                                NuevoColaborador(nombre=_nc, email=_mc),
                                            )
                                        _accion = "creado y vinculado" if _created else "vinculado"
                                        st.success(
                                            f"✅ **{_nc}** — {_accion} (ID: {_cid})"
                                        )
                                    except _SRelError as exc:
                                        st.warning(
                                            f"⚠️ {_nc} ({_mc}): {exc}"
                                        )

                    except _sc.SudespachoCreateError as exc:
                        st.error(f"Error al crear el expediente: {exc}")
                    except Exception as exc:
                        st.error(f"Error inesperado: {exc}")

            # 3. Pull Drive E&V (si el usuario rellenó la URL)
            # — Va al final: si se interrumpe, el caso local y el expediente CRM ya están creados.
            _drive_url_val = drive_url_input.strip()
            _drive_team_val = drive_team_id_resolved
            if _drive_url_val:
                try:
                    _folder_id = parse_drive_url(_drive_url_val)
                except ValueError as _ve:
                    st.error(f"URL Drive E&V no válida: {_ve}")
                else:
                    if not _drive_team_val:
                        st.warning(
                            "⚠️ No se pudo determinar el Shared Drive ID. "
                            "Introduce el ID manualmente en el expander '⚙️ Shared Drive ID' del formulario."
                        )
                    else:
                        with st.spinner("Descargando documentos del Drive E&V…"):
                            try:
                                _dr = pull_drive_ev(
                                    final_case_id,
                                    folder_id=_folder_id,
                                    team_id=_drive_team_val,
                                )
                                if _dr.skipped:
                                    st.info(
                                        f"Drive E&V ya estaba descargado "
                                        f"({_dr.files_after} archivo/s en `01_Drive EV/`)."
                                    )
                                else:
                                    st.success(
                                        f"✅ Drive E&V descargado — "
                                        f"**{_dr.files_after}** archivo/s en `00_Input/01_Drive EV/`."
                                    )
                            except DriveIntakeError as _die:
                                st.error(
                                    f"❌ Error al descargar el Drive E&V:  \n"
                                    + "  \n".join(_die.result.errors)
                                )


# ── TAB: Pipeline ──────────────────────────────────────────────────────────
with tab_pipeline:
    st.subheader("Ejecutar pipeline")
    cases = case_manager.list_cases()
    if not cases:
        st.info("Aún no hay casos.")
    else:
        case_id = st.selectbox(
            "Caso", cases,
            help="Caso sobre el que se ejecutará el pipeline completo de análisis.",
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            do_sync = st.checkbox(
                "Sincronizar Drive (rclone)", value=False,
                help="Ejecuta rclone antes del análisis para traer los últimos documentos del Drive E&V al caso local. Desactívalo si los documentos ya están actualizados.",
            )
        with col2:
            do_demanda = st.checkbox(
                "Generar demanda", value=True,
                help="Incluye el paso de generación del borrador de demanda al final del pipeline. Desactívalo si solo quieres ejecutar el análisis de viabilidad.",
            )
        with col3:
            do_anonimizar = st.checkbox(
                "Anonimizar (06_Anonimizado/)", value=False,
                help=(
                    "Aplica el motor de anonimización (Presidio + spaCy + reglas "
                    "contextuales) a los PDFs/DOCX de 00_Input/. Genera .md sin "
                    "PII en 06_Anonimizado/ y un mapa compartido por caso. La "
                    "primera ejecución carga ~1.5 GB de modelos NLP (20-40 s)."
                ),
            )
        with col4:
            drive_remote_path = st.text_input(
                "Remoto rclone (override)",
                help="Ruta remota rclone alternativa (p. ej. 'gdrive_ev:W-030LFT'). Déjalo vacío para usar la configuración del caso.",
            )

        if st.button("Ejecutar pipeline", type="primary",
                     help="Lanza el pipeline completo: extracción de documentos, análisis de viabilidad y (si está activado) borrador de demanda."):
            with st.spinner("Ejecutando..."):
                pr = pipeline.run(
                    case_id,
                    drive_remote_path=drive_remote_path or None,
                    do_sync=do_sync,
                    do_demanda=do_demanda,
                    do_anonimizar=do_anonimizar,
                )
            st.write(f"**Inicio:** {pr.started_at} — **Fin:** {pr.finished_at}")
            st.dataframe(
                [
                    {
                        "paso":    s.name,
                        "ok":      "✅" if s.ok else "❌",
                        "detalle": s.detail or s.artifact or "",
                    }
                    for s in pr.steps
                ],
                use_container_width=True,
            )


# ── TAB: Visor ─────────────────────────────────────────────────────────────
with tab_visor:
    st.subheader("Visor de Markdown")
    cases = case_manager.list_cases()
    if not cases:
        st.info("Aún no hay casos.")
    else:
        case_id = st.selectbox(
            "Caso", cases, key="visor_caso",
            help="Caso cuya documentación quieres consultar.",
        )
        sub = st.selectbox(
            "Subcarpeta", list(CASO_SUBDIRS), key="visor_sub",
            help="Fase del pipeline: 00 = documentos originales, 02 = análisis, 03 = decisión, 04 = borrador predemanda…",
        )
        sub_dir = caso_path(case_id) / sub
        files = sorted(sub_dir.rglob("*.md"))
        if not files:
            st.write("_(sin .md en esta fase)_")
        else:
            sel = st.selectbox(
                "Archivo", [str(p.relative_to(sub_dir)) for p in files],
                help="Archivo Markdown a visualizar. Selecciona el que quieres revisar.",
            )
            target = sub_dir / sel
            st.markdown(f"`{target}`")
            st.markdown(target.read_text(encoding="utf-8"))
