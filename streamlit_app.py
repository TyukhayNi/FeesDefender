"""FeesDefender — Motor de análisis y reclamación de honorarios. UI Streamlit.

La UI no contiene lógica de negocio: solo orquesta llamadas al `core` y
visualiza los `.md` resultantes. Pensada para uso local del abogado.
"""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

import os as _os

from core import case_manager, llm, pipeline, sudespacho_create as _sc
from core import local_organizer as _org
from core.local_organizer import OrganizadorError as _OrgError
from core.intake_drive import (
    DriveIntakeError,
    DriveFolderInfo as _DriveFolderInfo,
    get_drive_folder_info as _get_drive_folder_info,
    parse_drive_url,
    parse_ev_folder_name as _parse_ev_folder_name,
    pull_drive_ev,
)
from core import intake_log
from core import intake_manual
from core.judicial_intake import intake_demanda_contestacion as _intake_judicial
from core.sync_sudespacho import SudespachoError as _SudespachoError
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
    verify_expediente_referencia as _verify_exp_ref,
    list_expedientes_judiciales_candidatos as _list_exp_judicial_candidatos,
    wcode_match as _wcode_match,
)
from core.config import (
    ACTORES_DESPACHO,
    CASO_SUBDIRS,
    CRM_TREE,
    caso_path,
    settings,
    TIPOS_CASO_ALL,
    TIPOS_CASO_OTROS,
    posicion_de_tipo,
    POSICION_ACTORA,
    DRIVE_EV_TEAM_IDS,
    CLIENTES_PROPIOS_EV,
    CLIENTE_PROPIO_DEFAULT,
    cliente_propio_id,
)
from core.ciudades import (
    EQUIPOS_POR_CIUDAD_EXTRAJUDICIAL as _EQUIPOS_POR_CIUDAD_EXT,
    EQUIPOS_EXTRAJUDICIAL            as _EQUIPOS_EXT,
    TAG_AZUL_CIUDAD_EXTRAJUDICIAL    as _TAG_AZUL_CIUDAD_EXT,
    EQUIPOS_POR_CIUDAD_JUDICIAL      as _EQUIPOS_POR_CIUDAD_JUD,
    EQUIPOS_JUDICIAL                 as _EQUIPOS_JUD,
    TAG_AZUL_CIUDAD_JUDICIAL         as _TAG_AZUL_CIUDAD_JUD,
    ciudad_de_equipo                 as _ciudad_de_equipo,
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

# ---------------------------------------------------------------------------
# Sidebar — selector de actor (M10)
# ---------------------------------------------------------------------------
#
# El actor identifica quién está usando la app en este momento. Se sincroniza
# con `intake_log.set_actor` para que cada evento del log forense
# (`_intake_log.jsonl`) quede etiquetado con la persona responsable. Set
# cerrado (`ACTORES_DESPACHO`) + escape "Otros…" para becarios o sustitutos.

with st.sidebar:
    st.markdown("**¿Quién eres?**")

    # Default: si os.getlogin() coincide (substring case-insensitive) con
    # algún actor, ese; si no, el primero de la lista (Nikolai).
    try:
        _login = (_os.getlogin() or "").lower()
    except (OSError, AttributeError):
        _login = ""
    _default_actor = next(
        (a for a in ACTORES_DESPACHO if _login and _login in a.lower()),
        ACTORES_DESPACHO[0],
    )

    _actor_options = list(ACTORES_DESPACHO) + ["Otros…"]
    _actor_prev = st.session_state.get("_actor_selected", _default_actor)
    if _actor_prev not in _actor_options:
        _actor_prev = _default_actor
    _actor_sel = st.selectbox(
        "Actor",
        _actor_options,
        index=_actor_options.index(_actor_prev),
        key="_actor_selected",
        label_visibility="collapsed",
        help=(
            "Tu nombre se registra en `00_Input/_intake_log.jsonl` junto a "
            "cada acción sobre los casos (subir documentos, vincular "
            "expedientes, hacer pull del CRM, etc.). Sirve para auditoría "
            "forense — selecciona quién está usando la app."
        ),
    )

    if _actor_sel == "Otros…":
        _actor_custom = st.text_input(
            "Nombre completo",
            key="_actor_custom",
            placeholder="Nombre Apellido",
            help=(
                "Becario, sustituto u otro perfil no listado. Usa nombre + "
                "primer apellido para identificación inequívoca en el log."
            ),
        ).strip()
        _actor_final = _actor_custom or "Otros"
    else:
        _actor_final = _actor_sel

    st.session_state["actor"] = _actor_final
    intake_log.set_actor(_actor_final)

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
        with st.expander("📂 Subir al árbol CRM"):
            _caso_crm = st.selectbox(
                "Caso",
                cases,
                key="casos_crm_sel",
                help=(
                    "Selecciona el caso al que vas a subir documentos "
                    "procesales organizados por jurisdicción (Civil / Penal / "
                    "General). Los documentos genéricos recibidos por email "
                    "siguen yendo al expander «Demanda / documentos judiciales»."
                ),
            )

            # ── Selector jerárquico sobre CRM_TREE ─────────────────────────
            _branch_parts: list[str] = []
            _cur_tree = CRM_TREE
            _level = 0
            while isinstance(_cur_tree, dict) and _cur_tree:
                _opts = ["—"] + list(_cur_tree.keys())
                _sel_branch = st.selectbox(
                    f"Rama (nivel {_level + 1})",
                    _opts,
                    key=f"casos_crm_branch_{_level}",
                    help=(
                        "Elige la rama del gestor documental sudespacho donde "
                        "guardar el documento. Selecciona «—» para fijar la "
                        "rama actual como destino (puedes subir a un nodo "
                        "intermedio sin bajar más)."
                    ),
                )
                if _sel_branch == "—":
                    break
                _branch_parts.append(_sel_branch)
                _cur_tree = _cur_tree[_sel_branch]
                _level += 1

            if not _branch_parts:
                st.caption(
                    "_Selecciona la rama de destino para activar el uploader._"
                )
            else:
                _branch_path = "/".join(_branch_parts)
                st.caption(f"Destino: `00_Input/05_CRM/{_branch_path}/`")

                # ── Archivos ya presentes ──────────────────────────────────
                _existing_crm = intake_manual.list_crm_branch_files(
                    _caso_crm, _branch_path,
                )
                if _existing_crm:
                    st.caption(
                        f"**{len(_existing_crm)}** archivo/s en la rama:"
                    )
                    for _ef in _existing_crm:
                        _size_kb = _ef.stat().st_size // 1024
                        st.caption(f"· {_ef.name}  ({_size_kb} KB)")
                else:
                    st.caption("_(rama vacía)_")

                st.divider()

                # ── Uploader ───────────────────────────────────────────────
                _uploaded_crm = st.file_uploader(
                    "Subir archivos a la rama seleccionada",
                    accept_multiple_files=True,
                    type=[
                        "pdf", "docx", "doc",
                        "jpg", "jpeg", "png",
                        "txt", "eml", "msg",
                    ],
                    key="casos_crm_uploader",
                    help=(
                        "Sube uno o varios documentos. Se guardan en "
                        "`00_Input/05_CRM/<rama seleccionada>/`. Los ZIP no "
                        "se descomprimen — sube los archivos sueltos. Si un "
                        "archivo con el mismo nombre ya existe en la rama, "
                        "se sobrescribe."
                    ),
                )

                if st.button(
                    "⬆️ Guardar en rama CRM",
                    key="casos_crm_btn",
                    disabled=not _uploaded_crm,
                    help="Guarda los archivos seleccionados en la rama elegida.",
                ):
                    _saved_crm = 0
                    _errors_crm: list[str] = []
                    for _uf in _uploaded_crm:
                        try:
                            _raw = _uf.read()
                            intake_manual.save_file_crm_branch(
                                _caso_crm, _branch_path, _uf.name, _raw,
                            )
                            intake_log.append_event(
                                _caso_crm,
                                "upload_manual",
                                details={
                                    "destination": f"05_CRM/{_branch_path}/{_uf.name}",
                                    "filename": _uf.name,
                                    "size_bytes": len(_raw),
                                },
                            )
                            _saved_crm += 1
                        except Exception as _exc:
                            _errors_crm.append(f"{_uf.name}: {_exc}")

                    if _saved_crm:
                        st.success(
                            f"✅ **{_saved_crm}** archivo/s guardados en "
                            f"`05_CRM/{_branch_path}/`."
                        )
                    for _err in _errors_crm:
                        st.error(f"❌ {_err}")

        st.divider()
        with st.expander("⚖️ Intake judicial automático (demanda + contestación)"):
            st.caption(
                "Localiza, clasifica y deposita los documentos procesales del "
                "expediente judicial en el árbol CRM del caso (con dedup y "
                "registro). Por defecto baja **solo** la demanda y la "
                "contestación; marca la casilla de abajo para bajar el "
                "expediente completo. Los roles ambiguos se marcan para tu "
                "revisión, sin adivinar."
            )
            _caso_ij = st.selectbox(
                "Caso", cases, key="casos_ij_sel",
                help="Caso local al que pertenece el expediente judicial.",
            )

            # --- Resolución del expediente por referencia (W-code) ------------
            # El sufijo de la referencia puede divergir entre Drive y CRM
            # (p. ej. «… - Bad debt» vs «… - Vuelta - COMPRADOR»); se buscan
            # candidatos por W-code y el letrado confirma cuál bajar, en lugar
            # de teclear un ID a ciegas (que arriesga bajar OTRA finca).
            if st.button(
                "🔎 Buscar expediente en el CRM por la referencia del caso",
                key="casos_ij_buscar",
                help="Lista los expedientes judiciales del CRM cuya referencia "
                     "comparte el W-code de este caso.",
            ):
                try:
                    with st.spinner("Buscando en el CRM…"):
                        st.session_state["casos_ij_cands"] = (
                            _list_exp_judicial_candidatos(_caso_ij)
                        )
                except _SRelError as _eb:
                    st.session_state["casos_ij_cands"] = []
                    st.error(f"❌ No se pudo buscar en el CRM: {_eb}")

            _cands = st.session_state.get("casos_ij_cands") or []
            if _cands:
                _opts = {f"#{c['id']} — {c['label']}": c["id"] for c in _cands}
                _sel_label = st.radio(
                    "Candidatos en el CRM (elige y pulsa «usar»):",
                    list(_opts.keys()),
                    key="casos_ij_cand_sel",
                )
                if st.button("📥 Usar este ID", key="casos_ij_cand_use"):
                    st.session_state["casos_ij_exp"] = _opts[_sel_label]
                    st.rerun()
            elif "casos_ij_cands" in st.session_state:
                st.caption(
                    "Sin expedientes judiciales en el CRM con el W-code de este "
                    "caso. Comprueba la referencia o introduce el ID a mano."
                )

            _exp_ij = st.text_input(
                "ID del expediente judicial en sudespacho",
                key="casos_ij_exp",
                placeholder="p. ej. 487",
                help="ID numérico del expediente JUDICIAL en el CRM (no el "
                     "extrajudicial). Usa «Buscar» arriba para resolverlo desde "
                     "la referencia del caso y no teclear un ID equivocado.",
            ).strip()
            _full_ij = st.checkbox(
                "Descargar expediente completo (no solo demanda+contestación)",
                key="casos_ij_full",
                value=False,
                help="Baja TODO el gestor documental del expediente, dejando "
                     "`05_CRM` físicamente completo. La demanda y la contestación "
                     "se etiquetan igualmente; los roles ambiguos se avisan sin "
                     "bloquear la descarga. Útil para tener todos los procesales "
                     "(p. ej. de cara al juicio).",
            )
            _pipe_ij = st.checkbox(
                "Encadenar pipeline (anon → MD → frontier) tras el intake",
                key="casos_ij_pipe",
                value=False,
            )
            _force_ij = st.checkbox(
                "He verificado el ID a mano — descargar aunque el W-code no coincida",
                key="casos_ij_force",
                value=False,
                help="Solo para casos excepcionales en que la referencia del CRM "
                     "no incluye el W-code del caso. Por defecto, si no coincide, "
                     "la descarga se bloquea para no mezclar expedientes de fincas "
                     "distintas.",
            )

            if not _exp_ij:
                st.caption(
                    "✏️ Escribe o resuelve (botón «Buscar» arriba) el ID del "
                    "expediente para activar la descarga."
                )

            if st.button(
                "⚖️ Traer expediente completo" if _full_ij else "⚖️ Traer demanda + contestación",
                key="casos_ij_btn",
                disabled=not _exp_ij,
                help=(
                    "Descarga todo el expediente del CRM."
                    if _full_ij else
                    "Descarga únicamente los dos documentos procesales clave."
                ),
            ):
                if case_manager.is_legacy_intake_v1(_caso_ij):
                    st.error(
                        "⛔ Este caso tiene estructura antigua (`sudespacho_*/`). "
                        "El intake v2 está bloqueado hasta migrarlo manualmente."
                    )
                else:
                    # --- Guard: el ID debe pertenecer a ESTE caso -------------
                    # Verifica contra el CRM que el expediente tecleado comparte
                    # el W-code del caso. Evita el fallo del 649 (que era otra
                    # finca, W-030LFT) que se bajó sin avisar.
                    _chk = _verify_exp_ref(
                        _exp_ij, "expedientes_judiciales",
                        expected_referencia=_caso_ij,
                    )
                    _crm_ref = _chk["crm_referencia"]
                    _proceed = True
                    if _chk["crm_unreachable"]:
                        if not _force_ij:
                            _proceed = False
                            st.error(
                                "⛔ No se pudo verificar el expediente en el CRM "
                                "(¿PHPSESSID caducada? renuévala con `/renovar-php`). "
                                "Marca el override solo si estás seguro del ID."
                            )
                    elif not _chk["found"]:
                        if not _force_ij:
                            _proceed = False
                            st.error(
                                f"⛔ El expediente #{_exp_ij} no existe (o no tiene "
                                "referencia) en el CRM judicial. Revisa el ID."
                            )
                    elif not (_chk["match"] or _wcode_match(_crm_ref, _caso_ij)):
                        if not _force_ij:
                            _proceed = False
                            st.error(
                                f"⛔ El expediente #{_exp_ij} es **«{_crm_ref}»**, que "
                                f"NO corresponde a este caso (`{_caso_ij}`). "
                                "Descargarlo mezclaría fincas distintas. Si es "
                                "intencional, marca el override y reintenta."
                            )
                    elif not _chk["match"]:
                        st.info(
                            f"ℹ️ El nombre en el CRM («{_crm_ref}») difiere del caso "
                            "local, pero el W-code coincide: misma finca. Se descarga."
                        )

                    _rij = None
                    if _proceed:
                        case_manager.register_expediente(
                            _caso_ij, _exp_ij, "expedientes_judiciales",
                        )
                        with st.spinner("Localizando, clasificando y descargando…"):
                            try:
                                _rij = _intake_judicial(
                                    _caso_ij, _exp_ij, element="expedientes_judiciales",
                                    full=_full_ij,
                                )
                            except _SudespachoError as _eij:
                                _rij = None
                                st.error(f"❌ {_eij}")

                    if _rij is not None:
                        _written = _rij.pull.documents_written if _rij.pull else 0
                        _total_crm = _rij.pull.documents_total_crm if _rij.pull else 0
                        _overlap = _rij.pull.documents_overlap if _rij.pull else 0
                        if _written or _overlap:
                            _msg = (
                                f"✅ **{_written}** documento(s) depositados en "
                                f"`00_Input/05_CRM/`"
                            )
                            if _rij.full:
                                _msg += f" (de **{_total_crm}** en el CRM)"
                            if _overlap:
                                _msg += (
                                    f". **{_overlap}** copia(s) byte-idéntica(s) a "
                                    "documentos ya presentes, escritas igualmente "
                                    "para dejar el expediente completo"
                                )
                            st.success(_msg + ".")
                        if _rij.classification:
                            for _rr in (
                                _rij.classification.demanda,
                                _rij.classification.contestacion,
                            ):
                                if _rr.status == "ok":
                                    st.write(f"✅ **{_rr.role}**: `{_rr.selected.filename}`")
                                elif _rr.status == "ambiguous":
                                    st.warning(
                                        f"⚠️ **{_rr.role}** ambigua — "
                                        f"[PENDIENTE revisión letrado]. Candidatos:"
                                    )
                                    for _c in _rr.candidates:
                                        st.caption(f"· {_c.doc_id}: {_c.filename}")
                                else:
                                    st.info(
                                        f"— **{_rr.role}**: no encontrada por nombre "
                                        "[PENDIENTE revisión letrado]."
                                    )
                        if _rij.pendientes:
                            st.caption(
                                "Sube los documentos pendientes a mano con el "
                                "expander «📂 Subir al árbol CRM» si procede."
                            )
                        for _eij_err in _rij.errors:
                            st.caption(f"⚠️ {_eij_err}")

                        if _pipe_ij and (_written or _overlap):
                            with st.spinner("Ejecutando pipeline (OCR → MD → anon)…"):
                                _prij = pipeline.run(
                                    _caso_ij, do_sync=False, do_demanda=False,
                                    do_anonimizar=True,
                                    politica_anonimizar="SALTAR",
                                    tipo_proc_anonimizar="Juicio Ordinario",
                                )
                            for _s in _prij.steps:
                                st.write(
                                    f"{'✅' if _s.ok else '❌'} {_s.name}: "
                                    f"{_s.detail or _s.artifact or ''}"
                                )

        st.divider()
        with st.expander("🤖 Organizar localmente"):
            st.caption(
                "Clasifica y reordena los documentos del Drive E&V con IA local "
                "(Ollama) — **coste 0** y sin que ningún dato salga del equipo. "
                "Genera una vista navegable en `00_Input/01_Drive EV/_organizado/`. "
                "Los originales nunca se mueven ni se modifican."
            )

            _caso_org = st.selectbox(
                "Caso",
                cases,
                key="casos_org_sel",
                help="Selecciona el caso cuyos documentos quieres organizar.",
            )

            _pre = _org.estado_precondiciones(_caso_org)

            # ── Semáforo de precondiciones ─────────────────────────────────
            if _pre.drive_ok:
                st.caption(f"✅ Drive E&V: **{_pre.n_docs}** documento(s) descargados.")
            else:
                st.warning(
                    "Faltan documentos en `00_Input/01_Drive EV/`. "
                    "Descárgalos primero desde «📥 Pull Drive E&V»."
                )

            if _pre.anon_ok:
                st.caption("✅ Material anonimizado (`06_Anonimizado/`) disponible.")
            else:
                st.warning(
                    "Falta el material anonimizado (`06_Anonimizado/`). "
                    "Ejecútalo primero desde la pestaña «Pipeline» marcando "
                    "«Anonimizar», o con `python -m scripts.anonimizar_caso`."
                )

            if _pre.drive_ok and _pre.anon_ok:
                if _pre.ollama_ok:
                    st.caption(f"✅ IA local lista (modelo `{_pre.modelo}`).")
                else:
                    st.warning(
                        "La IA local (Ollama) no está disponible. Arráncala y "
                        "descarga el modelo desde una terminal:\n\n"
                        f"```\nollama serve\nollama pull {_pre.modelo}\n```"
                    )

            st.divider()

            # ── Paso 1: Proponer ───────────────────────────────────────────
            st.markdown("**Paso 1 — Proponer organización**")
            if st.button(
                "🔍 Proponer organización",
                key="casos_org_plan_btn",
                disabled=not _pre.listo_para_planificar,
                help=(
                    "La IA local clasifica cada documento y escribe una propuesta "
                    "editable en `07_AI cowork/_plan_reorganizacion.md`. No mueve "
                    "ni copia nada todavía. La primera ejecución puede tardar un "
                    "poco mientras se carga el modelo en memoria."
                ),
            ):
                with st.spinner("Clasificando documentos con la IA local…"):
                    try:
                        _res_plan = _org.planificar(_caso_org)
                    except _OrgError as _oe:
                        st.error(f"❌ {_oe}")
                    except Exception as _exc:
                        st.error(f"❌ Error inesperado al planificar: {_exc}")
                    else:
                        _c1, _c2, _c3, _c4 = st.columns(4)
                        _c1.metric("Documentos", _res_plan["n_documentos"])
                        _c2.metric("Alta confianza", _res_plan["n_alta_confianza"])
                        _c3.metric("Pendientes", _res_plan["n_pendientes"])
                        _c4.metric("Confianza media", f"{_res_plan['confianza_media']:.0%}")
                        st.success(
                            "✅ Propuesta generada. Revísala y corrige las columnas "
                            "**Categoría**, **Subgrupo** y **Nombre** si hace falta; "
                            "luego pulsa «Aplicar» abajo."
                        )
                        st.caption("Abre este archivo en tu editor para revisarlo:")
                        st.code(_res_plan["plan_reorganizacion"], language=None)

            # ── Paso 2: Aplicar ────────────────────────────────────────────
            st.markdown("**Paso 2 — Aplicar organización**")
            if not _pre.plan_existe:
                st.caption("_(Genera primero una propuesta en el Paso 1.)_")
            if st.button(
                "✅ Aplicar organización",
                key="casos_org_exec_btn",
                disabled=not _pre.plan_existe,
                help=(
                    "Materializa la vista organizada en `_organizado/` a partir de "
                    "la propuesta (ya revisada). Copia los documentos con nombre "
                    "limpio — los originales quedan intactos. Es idempotente: "
                    "aplicarlo dos veces no duplica nada. Tus correcciones "
                    "alimentan el aprendizaje del clasificador."
                ),
            ):
                with st.spinner("Aplicando la organización…"):
                    try:
                        _res_exec = _org.ejecutar_plan(_caso_org)
                    except _OrgError as _oe:
                        st.error(f"❌ {_oe}")
                    except Exception as _exc:
                        st.error(f"❌ Error inesperado al aplicar: {_exc}")
                    else:
                        _acc = _res_exec["acciones"]
                        _resumen_acc = "  ·  ".join(
                            f"**{_n}** {_a}" for _a, _n in sorted(_acc.items())
                        ) or "_(sin cambios)_"
                        st.success(
                            f"✅ Organización aplicada — {_res_exec['n_documentos']} "
                            f"documento(s).  \n{_resumen_acc}"
                        )
                        if _res_exec["correcciones_registradas"]:
                            st.caption(
                                f"📝 {_res_exec['correcciones_registradas']} corrección/es "
                                "registrada(s) para el aprendizaje del clasificador."
                            )
                        st.caption("Vista organizada (ábrela en el explorador de archivos):")
                        st.code(_res_exec["organizado_dir"], language=None)
                        st.info(
                            "⚠️ La carpeta `_organizado/` contiene **copias con datos "
                            "personales** (PII) de los originales. Es material interno "
                            "del despacho — no la compartas con terceros."
                        )

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

        st.divider()
        with st.expander("🏙️ Reasignar ciudad"):
            from core.casos import case_locator as _cl
            from core.ciudades import CIUDADES as _ALL_CIUDADES

            _caso_rs = st.selectbox(
                "Caso",
                cases,
                key="casos_reasig_sel",
                help="Selecciona el caso que quieres mover a otra ciudad.",
            )

            _path_actual_rs = _cl.path_for(_caso_rs)
            _ciudad_actual_rs = (
                _path_actual_rs.parent.name
                if _path_actual_rs.parent != settings.casos_root
                else "(raíz)"
            )
            st.caption(f"Ciudad actual: **{_ciudad_actual_rs}**")

            _equipo_rs = _caso_rs.split(" - ")[0].strip() if _caso_rs else ""
            _ciudad_esperada_rs = _ciudad_de_equipo(_equipo_rs)
            if _ciudad_esperada_rs and _ciudad_esperada_rs != _ciudad_actual_rs:
                st.warning(
                    f"El prefijo `{_equipo_rs}` pertenece a "
                    f"**{_ciudad_esperada_rs}**, pero el caso está en "
                    f"**{_ciudad_actual_rs}**."
                )

            _ciudad_destino_rs = st.selectbox(
                "Ciudad destino",
                ["— selecciona —"] + list(_ALL_CIUDADES) + ["_Sin clasificar"],
                key="casos_reasig_dest",
                help="Catálogo cerrado. Para añadir una ciudad nueva, hablar con Nikolai.",
            )

            _motivo_rs = st.text_area(
                "Motivo (mínimo 10 caracteres)",
                key="casos_reasig_motivo",
                help=(
                    "Explica brevemente por qué reasignas el caso. Queda "
                    "registrado en `_audit/relocations.jsonl` junto a tu actor."
                ),
                placeholder="Ej: prefijo SaRS1 asignado por error; el inmueble está en Bilbao",
            )

            _can_reasig = (
                _ciudad_destino_rs != "— selecciona —"
                and _ciudad_destino_rs != _ciudad_actual_rs
                and len((_motivo_rs or "").strip()) >= 10
            )
            if st.button(
                "🏙️ Reasignar caso",
                key="casos_reasig_btn",
                disabled=not _can_reasig,
                help=(
                    "Mueve la carpeta a la ciudad destino, actualiza el "
                    "metadato `ciudad` en `_caso.md` y registra la operación "
                    "en el audit log. Atómico: si falla la actualización "
                    "del metadato, revierte el movimiento de carpeta."
                ),
            ):
                with st.spinner("Reasignando…"):
                    try:
                        _new_path_rs = _cl.move_to_city(
                            _caso_rs,
                            _ciudad_destino_rs,
                            _motivo_rs.strip(),
                            _actor_final,
                        )
                        try:
                            _rel_rs = _new_path_rs.relative_to(settings.casos_root)
                        except ValueError:
                            _rel_rs = _new_path_rs
                        st.success(
                            f"✅ Reasignado a **{_ciudad_destino_rs}** "
                            f"(`{_rel_rs}`)."
                        )
                        st.cache_data.clear()
                    except FileNotFoundError as _fnf:
                        st.error(f"❌ Caso no encontrado: {_fnf}")
                    except ValueError as _ve:
                        st.error(f"❌ {_ve}")
                    except Exception as _exc:
                        st.error(f"❌ Error inesperado: {_exc}")

        # ── Admin: histórico relocations.jsonl (solo Nikolai) ──────────
        if _actor_final == "Nikolai Tyukhay":
            st.divider()
            with st.expander("🔐 Admin — Histórico de reasignaciones"):
                import json as _json_admin

                _log_path_adm = settings.casos_root / "_audit" / "relocations.jsonl"
                if not _log_path_adm.exists():
                    st.caption("_(sin entradas todavía)_")
                else:
                    _entries_adm: list[dict] = []
                    try:
                        with _log_path_adm.open(encoding="utf-8") as _fadm:
                            for _line_adm in _fadm:
                                _line_adm = _line_adm.strip()
                                if _line_adm:
                                    _entries_adm.append(_json_admin.loads(_line_adm))
                    except (OSError, _json_admin.JSONDecodeError) as _exc_adm:
                        st.error(f"No se pudo leer el log: {_exc_adm}")
                    else:
                        st.caption(
                            f"**{len(_entries_adm)}** entradas en "
                            f"`_audit/relocations.jsonl`"
                        )
                        _col_fa1, _col_fa2 = st.columns(2)
                        with _col_fa1:
                            _ops_adm = sorted(
                                {e.get("operacion", "") for e in _entries_adm}
                            )
                            _filter_op_adm = st.selectbox(
                                "Operación",
                                ["(todas)"] + _ops_adm,
                                key="admin_log_filter_op",
                            )
                        with _col_fa2:
                            _filter_case_adm = st.text_input(
                                "Caso contiene…",
                                key="admin_log_filter_case",
                                placeholder="ej: BaRS1",
                            ).strip().lower()
                        _filtered_adm = [
                            e for e in _entries_adm
                            if (
                                _filter_op_adm == "(todas)"
                                or e.get("operacion") == _filter_op_adm
                            )
                            and (
                                not _filter_case_adm
                                or _filter_case_adm in e.get("case_id", "").lower()
                            )
                        ]
                        if _filtered_adm:
                            st.dataframe(
                                list(reversed(_filtered_adm)),
                                use_container_width=True,
                            )
                        else:
                            st.caption("_(sin coincidencias con los filtros)_")


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
    #
    # El catálogo de ciudades y equipos vive en `core/ciudades.py` (única
    # fuente de verdad). Aquí solo se anteponen los placeholders propios
    # del `st.selectbox` y se mantiene el dict de notas (no migrado a
    # `core/ciudades.py` porque no pertenece a la subdivisión por
    # ciudad — son tags verdes de tipo de operación).

    _PLACEHOLDER_CIUDAD = "— selecciona ciudad —"

    # Extrajudicial
    _EQUIPOS_POR_CIUDAD: dict[str, dict[str, str]] = _EQUIPOS_POR_CIUDAD_EXT
    _EQUIPOS:            dict[str, str]            = _EQUIPOS_EXT
    _CIUDADES:           dict[str, str | None]     = {
        _PLACEHOLDER_CIUDAD: None,
        **_TAG_AZUL_CIUDAD_EXT,
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
        "DEVOLUCION_HONORARIOS":           _sc.NOTA_DEVOLUCION_HONORARIOS,
        "OTROS":                           _sc.NOTA_OTROS,
    }

    # Judicial
    _J_EQUIPOS_POR_CIUDAD: dict[str, dict[str, str]] = _EQUIPOS_POR_CIUDAD_JUD
    _J_EQUIPOS:            dict[str, str]            = _EQUIPOS_JUD
    _J_CIUDADES:           dict[str, str | None]     = {
        _PLACEHOLDER_CIUDAD: None,
        **_TAG_AZUL_CIUDAD_JUD,
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
            # Solo intentamos auto-fill si NO se ha resuelto ya para este folder_id
            # con éxito (sentinel `_nc_drive_autofilled_fid` se marca abajo SOLO
            # tras éxito — un fallo no queda cacheado y se reintenta en el
            # siguiente rerun automáticamente).
            if st.session_state.get("_nc_drive_autofilled_fid") != _fid_cached:
                with st.spinner("Obteniendo metadatos de carpeta…"):
                    _folder_info_top = _get_drive_folder_info(_fid_cached)
                if _folder_info_top:
                    # Marcar éxito SOLO si la llamada devolvió info útil.
                    st.session_state["_nc_drive_autofilled_fid"] = _fid_cached
                    st.session_state["_nc_autofill_folder_name"] = _folder_info_top.name
                    st.session_state.pop("_nc_drive_autofill_failed", None)
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
                else:
                    # Fallo: NO marcar sentinel — así un rerun posterior reintenta.
                    # Sí marcar flag de fallo para que la UI muestre warning.
                    st.session_state["_nc_drive_autofill_failed"] = _fid_cached
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # § 0 — Fuente documental Drive E&V (campo principal — va al inicio)
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="ev-section-label">Drive E&amp;V — carpeta de la operación</div>',
        unsafe_allow_html=True,
    )

    drive_url_input = st.text_input(
        "URL carpeta W-XXXXXX",
        placeholder="https://drive.google.com/drive/folders/1BxiMV…",
        key="nc_drive_url",
        help=(
            "Opcional. Pega la URL de la carpeta de la operación en el Drive "
            "engelvoelkers.com. Si se rellena, ciudad, equipo, dirección e "
            "ID GO se autorellenan y los documentos pueden sincronizarse vía "
            "rclone. Si se deja vacía, se completarán los campos manualmente "
            "y no habrá pull automático del Drive."
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
            elif st.session_state.get("_nc_drive_autofill_failed") == _fid_preview:
                # La llamada a Drive API falló para este folder_id (rate-limit,
                # token caducado, permisos, etc.). Avisamos al usuario y le
                # ofrecemos reintentar — el flag no es sticky: en cada rerun
                # se vuelve a intentar la llamada y, si funciona, este aviso
                # desaparece.
                st.warning(
                    "No se pudieron obtener los metadatos del Drive para esta URL. "
                    "Causa habitual: cuota de Google Drive API saturada (compartida con "
                    "otros usuarios de rclone) — suele restablecerse en 1-2 min. "
                    "También puede ser token caducado de gdrive_ev o falta de permisos "
                    "sobre la carpeta. Puedes rellenar los campos manualmente o "
                    "reintentar pulsando el botón.",
                    icon="⚠️",
                )
                if st.button("🔄 Reintentar auto-fill", key="nc_drive_retry_autofill"):
                    # Limpiar flag de fallo: el bloque de auto-fill se ejecuta
                    # en el siguiente render y reintentará la llamada.
                    st.session_state.pop("_nc_drive_autofill_failed", None)
                    st.rerun()
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
            help=(
                "Tipo de incumplimiento o reclamación. Determina los tags CRM, "
                "la posición procesal y la nota estándar del expediente. "
                "La categoría 'Otros' cubre casos genéricos de E&V no "
                "relacionados con defensa o reclamación de honorarios."
            ),
        )

    # ------------------------------------------------------------------
    # § 1b — Cliente propio E&V (solo para "Otros casos")
    # ------------------------------------------------------------------
    # Por defecto, los casos de honorarios (actora + defensiva) se vinculan
    # a EV MMC SPAIN, S.L.U. (sociedad operativa). Para "Otros casos" puede
    # interesar vincular a la matriz ENGEL & VÖLKERS SPAIN, S.L.U. — se
    # ofrece un selector visible solo cuando tipo_caso ∈ TIPOS_CASO_OTROS.
    if tipo_caso in TIPOS_CASO_OTROS:
        cliente_propio_clave = st.selectbox(
            "Cliente propio E&V *",
            list(CLIENTES_PROPIOS_EV.keys()),
            format_func=lambda k: CLIENTES_PROPIOS_EV[k][1],
            key="nc_cliente_propio",
            help=(
                "Sociedad del grupo E&V que figura como cliente del expediente. "
                "EV MMC SPAIN, S.L.U. (operativa, ID=2) o ENGEL & VÖLKERS "
                "SPAIN, S.L.U. (matriz, ID=27)."
            ),
        )
    else:
        cliente_propio_clave = CLIENTE_PROPIO_DEFAULT

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
            f"⚠️ Este caso ya tiene expediente/s registrado/s **localmente**: {_exp_resumen}. "
            "Al enviar a sudespacho se verificará primero en el CRM si ya existe un "
            "expediente con esta referencia.",
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

        # URL Drive E&V: opcional para judiciales y extrajudiciales (2026-05-11 s10).
        # Si se rellena, habilita auto-fill + pull rclone; si se omite, los
        # campos de operación se rellenan a mano y no hay pull automático.

        # Email Consultor Buscador (opcional — solo validar formato si se rellena)
        if mail_buscador.strip() and not _valid_email(mail_buscador):
            _missing.append("Mail Consultor Buscador — formato inválido")

        # Email Otros implicados (opcional — solo validar formato si se rellena)
        if mail_otros.strip() and not _valid_email(mail_otros):
            _missing.append("Mail Otros implicados — formato inválido")

        # Validación blanda de coherencia prefijo↔ciudad (Fase 2 subdivisión)
        _ciudad_esperada = _ciudad_de_equipo(_equipo_code_resolved)
        _prefijo_coherente = (
            _ciudad_esperada is None
            or _ciudad_esperada == ciudad_label
        )
        _coherencia_key = f"_coherencia_ok_{final_case_id}"
        if (
            not _prefijo_coherente
            and not st.session_state.get(_coherencia_key, False)
        ):
            _missing.append(
                f"El equipo **{_equipo_code_resolved}** pertenece a "
                f"**{_ciudad_esperada}** pero has seleccionado "
                f"**{ciudad_label}**"
            )

        if _missing:
            st.error(
                "Completa o corrige los siguientes campos: **"
                + "**, **".join(_missing)
                + "**."
            )
            if not _prefijo_coherente:
                _confirm = st.checkbox(
                    f"Confirmo: crear el caso en **{ciudad_label}** aunque "
                    f"el equipo {_equipo_code_resolved} sea de "
                    f"{_ciudad_esperada}",
                    key=_coherencia_key,
                )
                if _confirm:
                    st.rerun()
        else:
            # 1. Crear caso local (siempre)
            # tipo_caso gobierna la copia condicional del cuestionario de
            # viabilidad (paso 7a). direccion + id_go pre-rellenan el REF de
            # la ficha de operación si los tres componentes (equipo del
            # case_id + estos dos) están presentes.
            if not _prefijo_coherente:
                from core.casos.case_locator import append_audit_log
                append_audit_log({
                    "operacion": "alta_caso_incoherente",
                    "case_id": final_case_id,
                    "ciudad_seleccionada": ciudad_label,
                    "ciudad_esperada": _ciudad_esperada,
                    "equipo": _equipo_code_resolved,
                    "usuario": "streamlit_ui",
                })
            with st.spinner("Creando caso local…"):
                _path = case_manager.ensure_case(
                    final_case_id,
                    titulo=final_case_id,
                    referencia_crm=final_case_id,
                    cliente="EV MMC SPAIN, S.L.U.",
                    cuantia=cuantia_nc or None,
                    tipo_caso=tipo_caso,
                    direccion=direccion.strip() or None,
                    id_go=ref_mls.strip() or None,
                    ciudad=ciudad_label,
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
                    _af_name = st.session_state.get("_nc_autofill_folder_name")
                    _af_drive_id = st.session_state.get("_nc_autofill_team_id")
                    if _af_name and _af_drive_id:
                        case_manager.cache_drive_folder_info(final_case_id, _af_name, _af_drive_id)
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

                # Posición procesal (común a ambos tipos).
                # Para "OTROS" se asume ACTOR por defecto: E&V suele consultar
                # al despacho desde la posición de cliente que reclama; el
                # abogado puede cambiarla manualmente en el CRM si procede.
                _pos_de_tipo = posicion_de_tipo(tipo_caso)
                _pos = (
                    _sc.POSICION_DEMANDADO
                    if _pos_de_tipo == "defensiva"
                    else _sc.POSICION_ACTOR
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

                        # 3a. Validación preventiva — referencia local ↔ CRM.
                        # Tras el incidente BaRR3 (ID 648 mal vinculado a Roser
                        # — sesión 2026-05-11): tras vincular un expediente al
                        # caso local, leemos del CRM su `referencia_cliente` y
                        # la comparamos con el case_id. Mismatch ≠ aborto: el
                        # caller decide. Aquí mostramos un st.warning visible.
                        try:
                            _ref_check = _verify_exp_ref(
                                _exp_id,
                                _tipo_registro,
                                expected_referencia=final_case_id,
                            )
                        except Exception as _ve:  # noqa: BLE001 — nunca debería ocurrir, defensivo
                            st.info(
                                f"ℹ️ Validación de referencia CRM no ejecutada: {_ve}"
                            )
                        else:
                            if _ref_check["crm_unreachable"]:
                                st.info(
                                    "ℹ️ Validación referencia CRM omitida — "
                                    "endpoint no accesible (API key vacía o red caída)."
                                )
                            elif not _ref_check["match"]:
                                _crm_ref_str = _ref_check.get("crm_referencia") or "(vacía)"
                                st.warning(
                                    f"⚠️ **Referencia desalineada CRM ↔ caso local**.  \n"
                                    f"Expediente CRM **ID {_exp_id}** tiene `referencia_cliente` = "
                                    f"`{_crm_ref_str}`, pero el caso local es `{final_case_id}`.  \n"
                                    "Revisa que el expediente recién creado es el correcto antes "
                                    "de descargar documentos. Si el ID está mal vinculado, edita "
                                    "`_caso.md` o desvincula desde sudespacho."
                                )
                            else:
                                st.caption(
                                    f"✓ Referencia CRM coincide con caso local."
                                )
                        # 3b. Vincular cliente propio E&V (EV MMC por defecto;
                        #     ENGEL & VÖLKERS SPAIN para "Otros casos" si el
                        #     usuario lo eligió en el selector § 1b).
                        _cli_id = cliente_propio_id(cliente_propio_clave)
                        _cli_label = CLIENTES_PROPIOS_EV[cliente_propio_clave][1]
                        try:
                            if es_judicial:
                                link_ev_mmc_judicial(_exp_id, cliente_propio_id=_cli_id)
                            else:
                                link_ev_mmc(_exp_id, cliente_propio_id=_cli_id)
                            st.success(f"✅ Cliente **{_cli_label}** vinculado.")
                        except _SRelError as exc:
                            st.warning(f"⚠️ No se pudo vincular {_cli_label}: {exc}")

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
