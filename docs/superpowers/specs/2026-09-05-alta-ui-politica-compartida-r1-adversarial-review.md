---
tipo: revision-adversarial
objeto: "diff origin/main...450d61b del PR #285 — «el formulario de alta comparte con la CLI la política de duplicados del CRM» (acciones 3-4)"
objeto_rev: "2"
commit: "450d61b"
ronda: "1"
revisor: Claude Code (sesión independiente)
veredicto: REQUIERE-REVISION
marcador_nonce: zkqv
sha256_informe: 36ee2f796faa7aaa378e326f76c6f4c728dee19d50aff719b816114fc25eab73
adjudicado_en: docs/superpowers/specs/2026-09-05-alta-ui-politica-compartida-design.md §7
adjudicador: Claude Code
independencia_adjudicacion: "más débil — autor y revisor son el mismo modelo (AGENTS.md §Revisor sustituto)"
---

> **Acta de revisión adversarial R1 sobre el DIFF del PR #285.** Única ronda de la pieza (no
> decide quién escribe sobre qué copia ni destruye datos; decide si se crea un registro en el CRM
> del cliente). El §0 es el mandato literal, el §1 la voz del revisor sin una coma cambiada, el §2
> mi evidencia y el §3 el mapa.
>
> **Dónde vive la adjudicación:** en la **rev. 3 del diseño**
> (`2026-09-05-alta-ui-politica-compartida-design.md`, §7).
>
> **Revisor sustituto, independencia MÁS DÉBIL.** Codex sin cupo; subagente de Claude Code sin el
> contexto de autoría (`AGENTS.md` §«Revisor sustituto»). Dos cosas la refuerzan aquí: el código
> del formulario lo escribió **otro** subagente (la sesión orquestadora lo revisó y lo commiteó),
> y el revisor ejecutó la CLI en sus dos versiones y diez mutantes de la política. Se registra como
> `revisor: Claude Code (sesión independiente)`, nunca como «Codex».
>
> **Higiene del workdir:** creado vacío para esta ronda; el revisor lo declaró limpio en su primera
> línea. El digest se recalculó al recibirlo (`36ee2f79…`) y coincide.

## 0. Mandato, literal

# MANDATO — Revisión adversarial R1 sobre el DIFF del PR #285 (FeesDefender, acciones 3-4)

## Higiene, primero

- **Solo lectura.** No editas, creas ni borras nada dentro del repo. Nada de `git checkout`, `stash`, `commit`, `merge`, `rebase`. No arranques Streamlit contra ningún caso real ni con credenciales.
- Tu único fichero de salida es `INFORME.md` en el directorio de trabajo indicado (sondas en `probes/` dentro de él, declaradas). Si encuentras allí cualquier fichero distinto de `MANDATO.md`, no lo leas y decláralo en la primera línea.
- Fecha del sistema: 2026-09-05. Escribe en castellano.
- No has visto la conversación del autor y no debes buscarla.

## Objeto

- Repo (worktree, solo lectura): `C:\Users\tnm33\Dev\FeesDefender\.claude\worktrees\alta-ui-politica-compartida`, HEAD `450d61b` (compruébalo). Diff: `git diff origin/main...HEAD` (base `2b32c32`). Cinco ficheros: `core/alta_crm_politica.py` (nuevo), `tests/test_alta_crm_politica.py` (nuevo), `scripts/abrir_caso.py`, `streamlit_app.py`, `docs/superpowers/specs/2026-09-05-alta-ui-politica-compartida-design.md` (rev. 2).
- Contrato: el §3 y el §5 del diseño rev. 2. Léelo primero; después ataca el código. Contexto: `core/sudespacho_relations.py` (`DuplicadosExpediente`, `buscar_expedientes_duplicados`, `_normalize_element`), `core/case_manager.py` (`register_expediente`, `get_case_status`), `tests/test_crm_dedup_expediente.py` (sin modificar, debe seguir verde).

## Qué se te pide

Nada se da por bueno sin abrir el fichero y, cuando sea ejecutable, sin ejecutarlo (`C:\Users\tnm33\Dev\FeesDefender\.venv\Scripts\python.exe`, `CASOS_ROOT` temporal fuera del repo; nada de red: las funciones del CRM se mockean con `monkeypatch`).

Lentes, en orden de daño:

1. **Un expediente duplicado en el CRM del cliente.** ¿Queda algún camino del formulario que llame a `create_expediente`/`create_expediente_judicial` cuando el W-code ya está en el CRM, o cuando el caso local ya tiene un expediente? Sigue cada rama de `if btn_sudespacho:` en `streamlit_app.py`. Piensa en: el token `_nc_relanzar` (¿puede quedar armado y disparar una creación en un rerun posterior sin clic?), la casilla «crear igualmente» (`_alta_forzar_*`: ¿se consume de verdad por intento? ¿puede quedar `True` de un caso a otro?), el radio de frentes cuando el usuario cambia de `case_id` con el token vivo, y el orden entre `expediente_local_para_alta` y la política.
2. **Vincular el frente equivocado.** `_nc_cb_vincular` registra en `_caso.md` lo que el radio diga: ¿puede registrar sin elección explícita? ¿Puede registrar un `element` en alias (`judiciales`) que luego `elemento_canonico` no reconozca, o al revés? Comprueba qué `element` escribe `register_expediente` y qué lee `expediente_local_para_alta`.
3. **La CLI no cambia de comportamiento salvo lo declarado.** Corre `tests/test_crm_dedup_expediente.py` sobre HEAD. Compara `_alta_crm` antes (`git show origin/main:scripts/abrir_caso.py`) y después: mensajes, códigos de salida, orden de los avisos, el caso `por_wcode`+`sin_comprobar` que la rev. 2 declara como cambio querido. ¿Hay algún otro cambio observable no declarado?
4. **La política pura.** `decidir`: ¿es total (entradas vacías, `None`, ids numéricos, duplicados en `por_wcode`)? ¿`DecisionAltaCRM` es inmutable de verdad (tuplas)? ¿`expediente_local_para_alta` puede devolver una entrada de otro caso o sin `id`? ¿La prioridad «W-code manda sobre incertidumbre» es defendible cuando `por_wcode` viene de un `like` que `wcode_match` no pudo confirmar (lee cómo se llena `por_wcode` en `buscar_expedientes_duplicados`)?
5. **Arquitectura.** ¿Queda lógica de decisión en `streamlit_app.py` que debería estar en el core? ¿Hay estado de Streamlit que sustituya a estado que debería vivir en `_caso.md`?
6. **Tests.** ¿Cada mutante P1-P10 del §5 tiene test y muere con el código de `origin/main` (el módulo no existía: distingue «muere porque falta el import» de «muere porque la regla es distinta»)? ¿Falta el mutante de algo que el diff hace (p. ej. el consumo de `forzar`, el token de relanzamiento: si no es testeable, dilo)?
7. **Documentos.** ¿El §5 «Verificado el 2026-09-05» afirma algo que el diff no sostiene? ¿El diseño cita algún fichero inexistente (guard G2: `tests/test_docs_gobernanza.py::test_citas_a_specs_y_plans_existen`)? Córrelo sobre el árbol del worktree.

## Formato del informe

`INFORME.md`:
1. Primera línea: higiene del workdir.
2. Hallazgos `H-01`, `H-02`… por severidad (CRÍTICO / ALTO / MEDIO / BAJO): título, severidad, evidencia (`fichero:línea`, salida de la sonda), por qué importa, remedio breve.
3. Lo verificado y correcto, con evidencia.
4. Lo que no pudiste verificar y por qué (la UI no se ejecuta en esta ronda: dilo).
5. Veredicto: `SHIP` · `LISTA-CON-CAMBIOS` · `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE`, con una frase.

Al terminar, calcula el `sha256` del informe canonicalizado (UTF-8, `\r\n`→`\n`, sin saltos al borde, un único `\n` final) y devuelve en tu respuesta final SOLO: ruta, sha256, veredicto y recuento por severidad.

## 1. Informe recibido de Claude Code (sesión independiente), sin modificar

<!-- informe-literal:inicio:zkqv -->
# INFORME — Revisión adversarial R1 sobre el diff del PR #285 (acciones 3-4)

Higiene del workdir: al empezar solo contenía `MANDATO.md`. Sondas y salidas en `probes/` (declaradas en §4). Repo no tocado: `git status` limpio en `450d61b` antes y después (solo lectura; el árbol de `origin/main` se extrajo con `git archive` a `probes/main_tree/`, fuera del repo).

- Revisor: Claude Code (sesión independiente, sin la conversación del autor).
- Objeto: worktree `alta-ui-politica-compartida`, HEAD `450d61b` (comprobado), base `2b32c32` (= `merge-base origin/main HEAD`). Cinco ficheros, 811+/145−.
- Fecha del sistema: 2026-09-05.

## 1. Hallazgos

### H-01 · ALTO · El token de relanzamiento del camino `vincular` convierte CUALQUIER rerun en una pulsación del botón, y hay dos caminos por los que esa pulsación fantasma acaba en `create_expediente`

**Evidencia.** `streamlit_app.py:2072-2073` (`if st.session_state.pop("_nc_relanzar", None) == final_case_id: btn_sudespacho = True`) y `streamlit_app.py:2330-2331`: al final del bloque `vincular`, en cada run, `st.session_state["_nc_relanzar"] = final_case_id` seguido de `st.stop()`. El token no lo arma solo un callback (un acto): lo rearma el propio render del bloque, así que queda vivo entre runs mientras el operador no vincule. Cualquier rerun —cambiar el radio de frentes, tocar cualquier widget de cualquier tab, cambiar la cuantía o un email— vuelve a ejecutar el alta entera con los valores ACTUALES de los widgets: validación, `ensure_case`, 1b, 2a y **2b con una nueva consulta al CRM y una nueva `decidir`**. Si esa nueva decisión es `crear`, se llama a `create_expediente` (`:2397/2399`) sin que nadie haya pulsado nada.

Dos caminos concretos por los que la decisión cambia de `vincular` a `crear` con el token vivo:

1. **Override del case_id + edición del W-code.** `final_case_id` (`:1992-1994`) es el override si está relleno; entonces cambiar `ref_mls` NO cambia `final_case_id`, pero sí lo que se busca: `_buscar_dup(w_code=ref_mls.strip(), …)` (`:2262-2264`). Secuencia: pantalla `vincular` para `W-AAAA` (token armado) → el operador corrige el W-code a `W-BBBB` en el formulario → rerun → token == case_id → `btn_sudespacho=True` → `ensure_case` actualiza `meta.id_go` (documentado en `case_manager.py:285-287`) → 2b busca `W-BBBB`, no está → `crear` → **expediente creado en el CRM del cliente sin clic**, desde una pantalla cuyo único botón dice «Vincular» y cuyo comentario dice «No hay botón de crear de todos modos, a propósito».
2. **Respuesta transitoria del CRM.** El bloque `vincular` existe porque el W-code SÍ está en el CRM. Si en un rerun posterior `_buscar_registros` contesta `ok` con cero registros (índice rezagado, respuesta parcial) sin caer en `sin_comprobar`, `decidir` devuelve `crear` y se crea el duplicado que la pantalla anterior había detectado. Improbable, pero la propiedad que el diseño promete («crear a ciegas exige un acto por intento», rev. 2 nota 2; §3.2.3 «crear exige un acto separado») no depende de la probabilidad: la estructura la incumple.

Además, mientras el token está vivo el botón «📁 Crear caso local» tampoco escapa (`btn_local or btn_sudespacho` con `btn_sudespacho` forzado a `True`), y los gates `disabled=_btn_disabled` (`:2055`, `:2064`) quedan sin efecto porque el token se lee DESPUÉS de renderizar los botones.

**Por qué importa.** Es la lente 1 del mandato: un camino del formulario que llama a `create_expediente` sin acto del operador. El §5 del diseño registra como «defecto medido y corregido» que el bloque desaparecía al cambiar el radio; el remedio elegido (rearmar la pulsación) cambia un defecto de usabilidad por uno de escritura en el CRM del cliente.

**Remedio breve.** No reutilizar la «pulsación» para mantener viva la pantalla. Persistir la DECISIÓN (`_decision.candidatos`, `motivo`) en `session_state` bajo una clave ligada al `case_id` **y al W-code buscado**, y pintar el bloque `vincular` desde esa decisión guardada en los reruns sin volver a ejecutar el alta; solo el callback del botón «Vincular» arma `_nc_relanzar`. Alternativa mínima: que el relanzamiento provocado por el rearme lleve una marca (`_nc_relanzar_origen = "vincular"`) y que, si en ese relanzamiento la decisión ya no es `vincular`, se pinte la nueva decisión y se exija un clic real antes de crear. Y ligar el token también al W-code, no solo al `case_id`.

### H-02 · MEDIO · Con varios frentes, el radio pre-selecciona el primero: «Vincular» registra sin elección explícita y la rama «No se eligió ningún frente» es inalcanzable

**Evidencia.** `streamlit_app.py:2305-2311`: `st.radio(..., list(_opciones), key=_radio_key, ...)` sin `index=None`. En Streamlit 1.57.0 (versión del venv, medida) el radio arranca con `index=0`: `st.session_state[_radio_key]` vale la primera etiqueta desde el primer render. En `_nc_cb_vincular` (`:2087-2091`) `etiqueta = st.session_state.get(radio_key)` nunca es `None` y `par` nunca es `None`: el aviso «⚠️ No se eligió ningún frente» es código muerto. El orden de `candidatos` es el de `_PROP_REFERENCIA` (extrajudicial primero) y dentro de él el del CRM, no el del operador.

**Por qué importa.** Lente 2: un clic distraído en «Vincular» registra en `_caso.md` el frente que el sistema puso primero, y desde ahí la corrida completa cliente/colaboradores/pull sobre ese expediente (3a avisa de la referencia, pero `link_ev_mmc` y `ensure_colaborador_*` ya han escrito en el CRM sobre ese ID). El §3.2.3 dice «nunca … se elige por el usuario»; con `index=0` el sistema elige por él.

**Remedio.** `st.radio(..., index=None)` (soportado desde 1.26) y deshabilitar el botón «Vincular» mientras `st.session_state.get(_radio_key) is None`. La rama «No se eligió ningún frente» pasa a ser alcanzable y su test manual, posible.

### H-03 · MEDIO · Mientras el token está vivo, `st.stop()` deja en blanco los tabs Pipeline/Visor/Bandeja y cada interacción de la app relanza el alta y dos consultas al CRM; no hay forma de cancelar salvo cambiar el `case_id`

**Evidencia.** `streamlit_app.py:441` define los tabs; `tab_pipeline` (`:2547`), `tab_visor` (`:2609`) y `tab_bandeja` (`:2638`) se ejecutan DESPUÉS de `tab_nuevo`. Streamlit ejecuta el cuerpo de todos los tabs en cada run, y `st.stop()` en `:2331` corta el script: mientras `_nc_relanzar` esté armado (H-01), esos tres tabs no se pintan y cualquier clic en ellos (o en cualquier sitio) reejecuta `ensure_case` + `register_drive_ev` + `buscar_expedientes_duplicados` (dos `like` al CRM) y vuelve a parar. El único escape es alterar `final_case_id` (`:2072`), que con override activo es precisamente el vector 1 de H-01. El comentario del código lo declara («hasta que vincule o cambie de caso»), pero declarar el bloqueo no lo hace aceptable para Paola y Ana, que no saben que «cambiar de caso» es la salida.

**Remedio.** Con el remedio de H-01 (decisión persistida, sin relanzar) desaparece la mitad; añadir un botón «Cancelar: no vincular ahora» que borre la decisión guardada. Y no hacer `st.stop()`: bastan `return`/estructura condicional para no pintar el resto del alta, dejando el resto de la app viva.

### H-04 · BAJO · `_nc_cb_vincular` anuncia «vinculado en `_caso.md`» sin comprobar que `register_expediente` escribió, y sin `try/except`

**Evidencia.** `streamlit_app.py:2093-2098`; `case_manager.register_expediente` (`case_manager.py:172-178`) devuelve en silencio, sin escribir, si `buscar(case_id)` es `None` o si `00_Input/_caso.md` no existe. En ese caso el callback muestra «🔗 … vinculado» y relanza; 2a no encuentra nada; 2b vuelve a `vincular`; bucle con un banner de éxito falso en cada vuelta. Cualquier excepción dentro del callback (YAML corrupto, `PermissionError` en Drive) sale como traceback rojo, justo lo que el punto 1 del §3.2 arregló para `ensure_case`.

**Remedio.** Tras `register_expediente`, releer `get_case_status(case_id)["expedientes"]` y confirmar que el `id` está antes de anunciar y de armar el token; envolver en `try/except` y volcar el error a `_nc_aviso`.

### H-05 · BAJO · Tres cambios observables en la CLI que la rev. 2 no declara (declara solo uno)

**Evidencia.** `probes/cli_matrix.py` corre `_alta_crm` de `origin/main` (copia `probes/abrir_caso_OLD.py`) y de HEAD con las mismas entradas mockeadas, 8 escenarios × `force` ∈ {False, True}: 12 celdas idénticas byte a byte (stdout, stderr, código, nº de creaciones), 4 distintas:

| Escenario | Antes | Ahora | ¿Declarado? |
|---|---|---|---|
| `wcode+incierto`, sin force | «No se pudo comprobar…» exit 1 | «El CRM ya tiene un expediente con el id GO…» exit 1 | Sí (rev. 2 nota 4) |
| `incierto`, force | `[AVISO] --force: se da de alta SIN comprobar W-code en…` | `[AVISO] --force: se da de alta SIN COMPROBAR: W-code en…` | No |
| `direccion+incierto`, force | ídem | ídem | No |
| `wcode+incierto`, force | imprime la línea «--force: se da de alta SIN comprobar…» y aborta | aborta sin esa línea | No |

Códigos de salida y número de creaciones: idénticos en las 16 celdas. El tercer cambio es una mejora (no se anuncia un alta que no ocurre), pero la rev. 2 afirma «la CLI conserva sus mensajes de hoy» (nota 3) y «Mismo código de salida, otro mensaje» solo para el caso sin force.

**Remedio.** Declararlos en la nota 4 del diseño (o restaurar el literal «SIN comprobar » en `abrir_caso.py:693` quitando el prefijo antes de imprimir). Ningún test fija estos literales, así que la suite no lo detecta (`test_con_force_…` solo exige `"--force"` y `"HTTP 500"`).

### H-06 · BAJO · `_alta_forzar_<case_id>` puede sobrevivir a un relanzamiento abortado antes de 2b y consumirse en un clic posterior, saltándose la pantalla `bloquear`

**Evidencia.** El flag lo arma el callback (`:2080-2082`) y lo consume solo `st.session_state.pop(_forzar_key, None)` en `:2270`, que está DESPUÉS de `ensure_case` (`:2184-2201`) y de 1b. Si el relanzamiento muere antes (excepción no-`ValueError` de `ensure_case` sobre un Drive con hipo → traceback; o `st.stop()` por `ValueError`), el flag queda `True`. En el siguiente clic real del botón para el mismo `case_id`, 2b entra con `forzar=True` y crea directamente (con los `st.warning` de SIN COMPROBAR, pero sin la pantalla roja ni la casilla). Es el mismo operador y el mismo caso, así que el intento anterior existió; pero la rev. 2 dice «`forzar` se consume en esa misma corrida, salga lo que salga» y no es cierto si la corrida no llega a 2b.

**Remedio.** Consumir el flag al PRINCIPIO del bloque `if btn_sudespacho:` (leerlo a una variable local y `pop` inmediato), no tras la consulta.

### H-07 · BAJO · Deuda documental: el cuerpo del §3 sigue diciendo lo que la rev. 2 corrige, y «queda escrito» solo es cierto de la pantalla/consola

**Evidencia.** (a) `…-design.md:108-110` (§3.2.2) sigue diciendo «una entrada del elemento elegido»; la nota 1 de la rev. 2 lo desmiente pero el cuerpo no se tocó; ídem §3.2.3 «la corrida sigue con el pull» sin el token (nota 2). Un lector que entre por el §3 lee la regla vieja. (b) §3.1.3 y `alta_crm_politica.py:67-69` prometen que con `forzar` «quede escrito qué se dio por bueno a ciegas»: en la CLI es `typer.echo` y en la UI `st.warning`; ni `_caso.md` ni `_intake_log.jsonl` reciben nada. Predata al diff (la CLI vieja también solo imprimía), pero el diseño lo presenta como garantía. (c) `decidir` no deduplica `por_wcode` (`probes/decidir_totalidad.py`: `[(E,"648"),(E,"648")]` → dos candidatos iguales; la CLI imprime «#648, #648»; la UI colapsa por etiqueta del dict). Menor.

**Remedio.** Alinear el cuerpo del §3 con la rev. 2; matizar «queda escrito» a «queda en pantalla/consola» o emitir un evento `alta_crm_forzada` al intake log; `dict.fromkeys` sobre `candidatos`.

### H-08 · BAJO · La CLI sigue reconociendo solo `extrajudiciales` como «ya registrado»: un judicial vinculado desde el formulario la manda a abortar con un mensaje que pide hacer lo que ya está hecho

**Evidencia.** `scripts/abrir_caso.py:663-672` (sin cambios): `e.get("element") == _ELEMENT_EXTRAJUDICIAL`. Si el formulario vincula `expedientes_judiciales #700` (H-02/§3.2.3) y luego alguien corre la CLI sobre el mismo caso, el chequeo local no lo ve, va al CRM, encuentra el W-code y aborta con «vincula el existente con `register_expediente`». Seguro (no crea) pero contradictorio, y ahora más alcanzable porque el formulario escribe el slug canónico mientras el camino `crear` de la UI sigue escribiendo el alias `judiciales` (`:2230`): dos vocabularios en el mismo `_caso.md`, que `expediente_local_para_alta` absorbe pero `scripts/sync_sudespacho.py:347` y `scripts/scheduled_sync.py:188` pasan crudos a `pull_expediente_v2` (sin normalizar; `core/sync_sudespacho.py` no importa `_normalize_element`). Fuera del alcance declarado; se anota.

**Remedio.** Que la CLI use `expediente_local_para_alta(expedientes, "extrajudiciales")` para su chequeo local (ya existe, y es la misma regla); y que el camino `crear` de la UI registre el canónico.

## 2. Lo verificado y correcto

- **HEAD y base.** `450d61b`; `merge-base origin/main HEAD = 2b32c32`; 5 ficheros en el diff (`git diff --stat origin/main...HEAD`).
- **La política es pura, total sobre lo que el productor emite, e inmutable.** `probes/decidir_totalidad.py`: ids numéricos → `str`; `frozen` → `FrozenInstanceError`; `candidatos/avisos/sin_comprobar` son `tuple`; `hash()` funciona. Solo lanza con `por_wcode=None`/`sin_comprobar=None` o tuplas de 3, que `buscar_expedientes_duplicados` nunca produce (`field(default_factory=list)`, `sudespacho_relations.py:1266-1271`; pares `(elemento, rid)` en `:1339`).
- **La prioridad «W-code manda» es defendible.** `por_wcode` solo recibe registros cuya referencia devuelta casa con `wcode_match` (`sudespacho_relations.py:1333-1339`); un `like` sin referencia va a `sin_comprobar`, nunca a `por_wcode`. Así que «hay W-code» es un hecho confirmado, no un `like` sin confirmar.
- **Los diez mutantes mueren y cada P-test mata el suyo** (`probes/mutants_plugin.py`, `MUTANT=<nombre>`, 10 corridas): M1 prioridad invertida → solo P5; M2 forzar ignorado → P4; M3 sin prefijo → P4; M4 solo primer candidato → P2; M5 nunca vincular → P1, P2, P5; M6 reutilizar sin fallback → `test_si_no_hay_del_elemento_pedido…`; M7 sin filtro de `id` → `test_ignora_entradas…`; M8 ignora preferencia → `test_prefiere…`; M9 `elemento_canonico` sin alias → 3 tests; M10 dataclass mutable → `test_la_decision_es_inmutable`. P6 y P7 no matan ningún mutante mío pero fijan el camino `crear` (los mutantes M1-M5 no lo alteran).
- **Contra `origin/main`, distinguido.** `probes/main_tree/` (árbol de `origin/main` por `git archive`): el fichero de tests de HEAD muere en colección por `ImportError` (módulo ausente) — los 19 mueren «porque falta el import». Copiando además `core/alta_crm_politica.py` de HEAD al árbol viejo: 18 pasan (son del módulo nuevo) y **P9 falla por `AttributeError: module 'scripts.abrir_caso' has no attribute 'alta_crm_politica'`**: mata «la CLI no consume la política», pero por ausencia del import, no por regla distinta. Es lo esperable y es suficiente: no hay versión de `_alta_crm` con la regla distinta que testear.
- **P9 comprueba de verdad la inyección.** Con `dup` limpio y `decidir` sustituida por «bloquear», `_alta_crm` aborta y `create_expediente` no se llama; `forzar=True` llega (`vistas == [True]`).
- **La CLI: 12 de 16 celdas idénticas, códigos de salida y nº de creaciones idénticos en las 16** (H-05 para las 4 distintas). Orden de avisos conservado: primero dirección/contrario, luego los `SIN COMPROBAR`.
- **`tests/test_crm_dedup_expediente.py` sin modificar y verde** en HEAD (14/14; `git diff` no lo toca).
- **Los conteos del §5 son ciertos.** Con el comando del §5 (glob expandido; PowerShell no lo expande solo): HEAD **177**/0/0 por `--junit-xml` (`probes/junit_objetivo.xml`), de ellos **19** en `test_alta_crm_politica` (8+5+5+1). `origin/main` (mismo comando sin el fichero nuevo): **158**/0/0 (`probes/junit_main.xml`). 158 → 177 = +19, cuadra.
- **Guard G2 y todo `tests/test_docs_gobernanza.py`: 46/46 verdes** sobre el árbol del worktree. El diseño no cita ficheros inexistentes.
- **`expediente_local_para_alta` no puede devolver otro caso**: recibe `get_case_status(final_case_id)["expedientes"]` (`:2237-2238`), que lee solo el `_caso.md` de ese `case_id`; exige `id` no vacío y `element` reconocible; prefiere el pedido y cae al otro; ignora basura.
- **Alias.** `elemento_canonico` delega en `_ELEMENT_ALIASES` (`sudespacho_relations.py:2868-2880`): reconoce `judiciales` (lo que escribe el camino `crear` de la UI, `:2230`) y `expedientes_judiciales` (lo que escribe `vincular`, que toma el elemento de `_PROP_REFERENCIA`). `verify_expediente_referencia` acepta ambos (`:3010`). Lente 2, segunda mitad: sin desajuste.
- **Orden 2a → 2b correcto**: si hay local, no hay consulta ni creación; 3a-3c son idempotentes por contrato (`verify` lee; `ensure_*`/`link_*` deduplican).
- **`forzar` se consume tras `decidir` salga lo que salga** (`:2270`), y la casilla vive en un bloque que solo se pinta en el run del botón: sin token propio, un rerun ajeno la hace desaparecer (con su estado). Correcto salvo H-06.
- **El token está ligado al `case_id` y se consume con `pop`** (`:2072`); al cambiar `case_id` se descarta. Correcto salvo que el `case_id` no cambie cuando cambia el W-code (H-01).
- **`ensure_case` → `ValueError` → `st.error` + `st.stop()`** (`:2196-2201`); el sumidero no crea nada antes de validar (PR #280, no re-verificado aquí).
- **No queda camino «Confirmar de todos modos»**: `grep` de `Confirmar de todos modos|_find_exp_|_dup_confirm` en `streamlit_app.py` → 0; las dos únicas llamadas a `create_expediente*` están en `:2397/2399`, bajo `_decision.accion == CREAR`.
- **Ayuda de `--hasta` corregida** (`abrir_caso.py:893-897`), como anuncia el §6.

## 3. Lo que no pude verificar y por qué

- **La UI no se ejecutó en esta ronda.** Todo lo de `streamlit_app.py` (H-01 a H-04, H-06) es lectura del código más la semántica documentada de Streamlit 1.57 (reruns, callbacks antes del script, `index=0` por defecto en `st.radio`, limpieza del estado de widgets no renderizados, `st.stop()` corta el script). El vector 1 de H-01 es reproducible en pantalla con un doble de `buscar_expedientes_duplicados` como el que el §5 fila 4 describe; no lo hice porque exige arrancar Streamlit.
- **El consumo de `forzar` y el token no son testeables con pytest** (`streamlit_app.py` no se importa): el §5 lo reconoce. Mutante ausente que sí sería posible: extraer el pequeño orquestador (decidir → qué pintar → qué armar) a una función del core con `session_state` inyectado; hoy esa lógica (2a/2b, consumo de `forzar`, rearme del token, `_exp_es_judicial`) vive en la UI, en contra del §2 «la UI solo orquesta» en su sentido estricto (lente 5).
- **El camino `crear` con CRM real y el pull tras vincular**: no procede sin tenant de prueba; el §5 lo declara igual.
- **PR #280 («el sumidero no crea nada si el `case_id` es inválido»)**: no re-verificado; se toma del diseño.

## 4. Sondas (todas en `probes/`)

- `abrir_caso_OLD.py` — `git show origin/main:scripts/abrir_caso.py`, base del contraste CLI.
- `cli_matrix.py` — matriz 8×2 antes/después de `_alta_crm` (salida en §1 H-05 y §2).
- `mutants_plugin.py` — plugin pytest con 10 mutantes de `core.alta_crm_politica`.
- `decidir_totalidad.py` — entradas raras a `decidir` y `expediente_local_para_alta`.
- `junit_objetivo.xml`, `junit_main.xml` — conteos 177 y 158.
- `main_tree/` — árbol de `origin/main` extraído con `git archive` (más `tests/test_alta_crm_politica.py` y `core/alta_crm_politica.py` copiados de HEAD para la prueba de §2).
- `casos_tmp/`, `casos_tmp_main/` — `CASOS_ROOT` temporales de las corridas.

## 5. Veredicto

**REQUIERE-REVISION.** La política del core es correcta, pura y bien mutada, y la CLI no pierde ninguna protección; pero el formulario, que es la pieza que esta entrega existe para proteger, tiene un camino sin clic hasta `create_expediente` (H-01) y un radio que elige por el operador (H-02) — los dos en la frontera exacta que el diseño declara cerrada («crear exige un acto», «nunca se elige por el usuario»). Con H-01 y H-02 remediados y el resto declarado, es LISTA-CON-CAMBIOS.

Recuento: CRÍTICO 0 · ALTO 1 (H-01) · MEDIO 2 (H-02, H-03) · BAJO 5 (H-04 a H-08).
<!-- informe-literal:fin:zkqv -->

## 2. Evidencia verificada por mí al adjudicar

| Hallazgo | Qué comprobé | Dónde |
|---|---|---|
| H-01 | al final del bloque `vincular` el diff hacía `st.session_state["_nc_relanzar"] = final_case_id` seguido de `st.stop()` en **cada** render, y el token se consume al principio del tab como `btn_sudespacho = True`; `final_case_id` es el override si está relleno, mientras `_buscar_dup` busca por `ref_mls`, así que editar el W-code no cambiaba el `case_id` al que estaba ligado el token | `streamlit_app.py` (diff `450d61b`), bloque `vincular` y cabecera del tab |
| H-02 | `st.radio(..., key=_radio_key)` sin `index=None`; `_nc_cb_vincular` leía `st.session_state.get(radio_key)`, nunca `None` | ídem |
| H-03 | dos `st.stop()` dentro de `if btn_sudespacho:` y los tabs Pipeline/Visor/Bandeja definidos después de `tab_nuevo` | ídem |
| H-04 | `register_expediente` devuelve `input_dir_name` sin escribir si `buscar` da `None` o falta `_caso.md`; el callback no releía | `core/case_manager.py::register_expediente`, `streamlit_app.py::_nc_cb_vincular` |
| H-05 | la CLI imprimía `f"... se da de alta {aviso}"` con el prefijo `SIN COMPROBAR: ` del core en vez del literal «SIN comprobar » | `scripts/abrir_caso.py::_alta_crm` |
| H-06 | `st.session_state.pop(_forzar_key, None)` estaba después de la consulta al CRM, no al principio del bloque | `streamlit_app.py` |
| H-08 | `ya_registrado` solo comparaba con `_ELEMENT_EXTRAJUDICIAL` | `scripts/abrir_caso.py::_alta_crm` |

H-07 lo comprobé contra el texto del diseño (§3.2 decía la regla de la rev. 1) y contra `decidir`
(sin `dict.fromkeys`).

Digest del informe recalculado al recibirlo: `36ee2f796faa7aaa378e326f76c6f4c728dee19d50aff719b816114fc25eab73`
(UTF-8, `LF`, un único salto final), igual al declarado.

## 3. Mapa hallazgo → remedio (la adjudicación completa está en el §7 del diseño)

| # | Sev. | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 | ALTO | confirmado | decisión `vincular` guardada (`_nc_vincular_pend`, case_id + W-code) y pintada sin ejecutar el alta; token armado solo por callbacks |
| H-02 | MEDIO | confirmado | `st.radio(index=None)`; botón deshabilitado sin selección |
| H-03 | MEDIO | confirmado | `_alta_detenida` en vez de `st.stop()`; botón «Cancelar» |
| H-04 | BAJO | confirmado | el callback relee `get_case_status` y envuelve en `try/except` |
| H-05 | BAJO | confirmado | literal «SIN comprobar » restaurado; el tercer cambio se conserva y se declara |
| H-06 | BAJO | confirmado | `forzar` consumido al principio del alta |
| H-07 | BAJO | confirmado | §3.2 alineado; docstring; `dict.fromkeys`; P11 |
| H-08 | BAJO | confirmado | la CLI usa `expediente_local_para_alta`; P12; el doble vocabulario de `element` se deja anotado |

Recuento: 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar. La UI no se
ejecutó en esta ronda; la rev. 3 se verifica en pantalla igual que la rev. 2 y el §5 del diseño
dice qué se vio.
