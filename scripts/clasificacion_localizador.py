"""Clasificación FIRMADA de los llamadores del localizador (Fase 1, Task 6).

El inventario (`scripts/inventario_localizador.py`) **propone**; esto **firma**. La
distinción no es ceremonia: la heurística ya se equivocó una vez en un cubo confiado
—clasificó como puerta de alta tres sitios de `case_manager` que solo mencionaban
`ensure_case` en un comentario— y un falso positivo ahí deja el fallback donde no toca
sin que nadie vuelva a mirarlo. Por eso la decisión vive aquí, leída una a una, y el
guard compara **propuesta contra firma** en vez de fiarse de la propuesta.

## La regla que se aplicó al leerlos

- **`destino_de_alta`** — solo `ensure_case`. Es la única puerta por la que se crea, y
  admite la ausencia porque es su caso normal.
- **`buscar`** — los detectores de ausencia: los que preguntan si el caso está y siguen
  por otra rama. Migrarlos a `localizar()` cambiaría un error legible por una traza.
  Y de paso deshace una confusión vieja: con el fallback, «el caso no existe» y «el
  fichero que buscaba dentro del caso no existe» dan el mismo `False`.
- **`localizar`** — todo lo demás. Es la mayoría, y tiene sentido: casi todo el sistema
  opera sobre un caso ya abierto.

## Los constructores de rutas

La lectura de los 42 dudosos destapó que la mayoría no son decisiones independientes
sino **una capa de helpers** —`log_path`, `manifest_path`, `_sala_dir`, `_revisar_dir`,
`registro_path`, `_catalog_path`, `_manual_dir`, `_drive_ev_dir`…— que componen una
subruta y la devuelven, delegando la decisión en su llamador. Firmarlos a ellos decide
por todos sus llamadores de golpe, que es lo que hace la migración abordable.
"""
from __future__ import annotations

#: Intención firmada por fichero:línea, con la llave que emite el inventario.
#:
#: **Esto es la LISTA DE TRABAJO de esta migración, no un guard permanente.** Las
#: líneas se mueven en cuanto se migra un fichero, así que una firma indexada por
#: línea caduca por construcción — y un guard que caduca solo se desactiva o se
#: reajusta a mano, que es peor que no tenerlo. El guard permanente llega en el
#: paso 5 y tiene otra forma: «no queda ningún llamador de producción de
#: `path_for`/`caso_path` salvo las escotillas legacy declaradas», que no depende
#: de números de línea.
#:
#: `None` significa **firmado como sin migrar**: se queda en `path_for`/`caso_path`
#: con la escotilla legacy, y el motivo va al lado. No es lo mismo que «pendiente».
FIRMA: dict[str, str] = {
    # --- la única puerta de alta -------------------------------------------
    "core/case_manager.py:266": "destino_de_alta",

    # --- constructores de rutas: la capa que decide por sus llamadores ------
    "core/intake_log.py:153": "localizar",
    "core/intake_manifest.py:88": "localizar",
    "core/intake_manifest.py:98": "localizar",
    "core/intake_manifest.py:109": "localizar",
    "core/intake_manual.py:52": "localizar",
    "core/catalogo_documental.py:58": "localizar",
    "core/ocurrencias_crm.py:72": "localizar",
    "core/sala_lectura.py:93": "localizar",
    "core/sala_lectura.py:485": "localizar",
    "core/local_organizer.py:123": "localizar",
    "core/local_organizer.py:131": "localizar",
    "core/local_organizer.py:135": "localizar",
    "core/email_atomize/pipeline.py:433": "localizar",
    "core/email_atomize/pipeline.py:438": "localizar",

    # --- consumidores directos de un caso que debe existir ------------------
    "core/anon/api.py:189": "localizar",
    "core/anon/api.py:521": "localizar",
    "core/anon/api.py:626": "localizar",
    "core/case_manager.py:425": "localizar",
    "core/case_manager.py:527": "localizar",
    "core/case_manager.py:745": "localizar",
    "core/case_manager.py:981": "localizar",
    "core/casos/case_locator.py:159": "localizar",
    "core/linker.py:43": "localizar",
    "core/markdown_generator.py:25": "localizar",
    "core/sala_lectura.py:641": "localizar",
    "core/scorer.py:107": "localizar",
    "core/sync_sudespacho.py:1014": "localizar",
    "core/sync_sudespacho.py:1413": "localizar",
    "core/whatsapp_atomize/propuesta_identidades.py:16": "localizar",
    "scripts/abrir_caso.py:573": "localizar",
    "scripts/limpieza_post_audit.py:205": "localizar",
    "scripts/migrar_layout_intake.py:72": "localizar",
    "scripts/migrate_05crm_buckets.py:264": "localizar",
    "scripts/migrate_to_city_structure.py:159": "localizar",
    "scripts/ocr_textless_pdfs.py:72": "localizar",
    "scripts/scheduled_sync.py:134": "localizar",
    "streamlit_app.py:1419": "localizar",
    "streamlit_app.py:2497": "localizar",

    # --- el wrapper: se decide cuando se invierta el default ----------------
    # `config.caso_path` es la fachada que propaga. No se migra a una de las
    # tres: se le invierte el default al final (paso 5), que es lo que la spec
    # pide («`caso_path` deja de devolver rutas inexistentes»).
    "core/config.py:550": None,
}

#: Motivo de cada firma `None`, para que «sin migrar» nunca sea silencioso.
SIN_MIGRAR: dict[str, str] = {
    "core/config.py:550": (
        "es la fachada `caso_path`, no un llamador: se le invierte el default en "
        "el paso 5 y por eso no elige una de las tres intenciones"),
}
