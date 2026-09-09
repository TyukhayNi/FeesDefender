---
tipo: revision-adversarial
objeto: docs/superpowers/specs/2026-09-07-f3-cableado-bandeja-y-verificacion-design.md
objeto_rev: "1"
commit: 221b4d4
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: k7wq
sha256_informe: 9e1c70119bda0e599c30546719bb7c0edcc2a1793a1bdc1ab3029c4b4f5b75be
adjudicado_en: docs/superpowers/specs/2026-09-07-f3-cableado-bandeja-y-verificacion-design.md §15
---

# Acta — R1 adversarial sobre el diseño del cableado de F3 (Codex, 2026-09-08)

Ronda sobre el **diseño**, antes de construir. El objeto fue la rev. v1 del spec, con el árbol
entero del repo a mano para que el revisor pudiera contrastar sus afirmaciones contra el código.

**Esta acta existe porque yo soy la parte revisada.** Sin el informe original archivado, nadie
puede contrastar **qué dijo el revisor** con **qué decidí yo que dijo** — y en esta ronda la
diferencia importa, porque adjudiqué **14 de 14 confirmados** y dos de ellos agravados por encima
de lo que él escribió.

## Cómo corrió, y las dos cosas del patrón que se ganaron el sueldo

Codex CLI **0.153.4**, en solo lectura sobre una **copia congelada** del commit `221b4d4` extraída
con `git archive` (1.249 ficheros, sin `.git`). El informe cayó en un directorio **fuera del repo**.

- **El binario se BUSCA, no se hardcodea.** El directorio con hash había cambiado otra vez
  (`d0097be4…` → `8e5b6932…`), que es lo que tumbó una ronda en agosto. El criterio sigue siendo
  tener `codex-code-mode-host.exe` al lado.
- **Los flags se comprobaron antes de gastar la corrida**, por el salto de versión desde la 0.149
  sobre la que se midió la receta. Siguen bajo `exec`.

**Cadena de custodia:** `sha256` del objeto **idéntico al abrir y al cerrar**
(`b3a79e287eeb63c8c5e26e0df708ae2c9a401e13c14af8a1a428941e8a71e718`), nada escrito bajo `head/`, y
el digest que el propio informe declara coincide con el del fichero. La señal de fin fue la
**salida del proceso**, no la aparición de `INFORME.md`.

**El revisor ejecutó.** 104 pruebas preexistentes y **12 reproducciones adversariales** que
afirman el comportamiento defectuoso: sus verdes **confirman los contraejemplos**. Se montó un
`conftest` propio que bloquea red y DNS con una excepción derivada de `BaseException` — la técnica
correcta, y la misma que este repo tiene escrita. Declaró con precisión lo que no corrió, incluida
una ejecución cuyo identificador de sesión perdió y a la que **no se atribuye cobertura**.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:k7wq -->
VEREDICTO: NO-SHIP

Objeto: `../head/docs/superpowers/specs/2026-09-07-f3-cableado-bandeja-y-verificacion-design.md`, revisión v1. Revisión adversarial R1 de DISEÑO, contrastada con el código congelado, no revisión de un diff.

- SHA-256 del objeto **al abrir**: `b3a79e287eeb63c8c5e26e0df708ae2c9a401e13c14af8a1a428941e8a71e718`
- SHA-256 del objeto **al cerrar**: `b3a79e287eeb63c8c5e26e0df708ae2c9a401e13c14af8a1a428941e8a71e718`
- Ambos coinciden. No se escribió bajo `../head/`. No existe `../head/.git`. El commit `221b4d42a6c1bac1574e55f79e1d505298344461` es la identificación aportada por el mandato: **no se acredita procedencia genealógica**.

**El diseño no es apto para construirse tal como está.** Puede confirmar correos sin archivar sus documentos; presenta como elección de copia un parámetro que no direcciona la escritura; conserva una escritura que rodea la verificación que pretende centralizar; y la traza no representa los tres hechos que promete separar.

Se ejecutaron, sobre copias locales, **104 pruebas preexistentes y 12 reproducciones adversariales**, todas con resultado satisfactorio para sus asertos. Los 12 verdes adversariales **confirman los contraejemplos**, no certifican seguridad. Comandos, resultados y límites de ejecución: `EVIDENCIA_EJECUCION.md`; reproducciones: `scratch/test_adversarial.py`. Se compararon después los 123 ficheros copiados de `core/` y los cinco ficheros originales de tests con la fuente: sin diferencias. No se implementó el diseño para revisarlo.

## H-01 — El cableado carece del inventario de adjuntos que necesita D3 y puede confirmar sin subir ninguno

- **Severidad:** CRÍTICO
- **Dónde:** spec §4, paso 6; §9 y §12; `core/gmail_source.py:72`; `core/procurador_runner.py:99`; `core/procurador_review.py:97`; `core/procurador_relate.py:458`.
- **Qué falla:** el diseño presupone una lista de originales anterior al clic que el flujo real no construye, y el cliente interpreta su ausencia como archivado completo.
- **Cómo se manifiesta:** llega un correo con `auto.pdf`; la respuesta Gmail contiene su `filename` y `attachmentId`, pero `gmail_message_to_email` solo conserva cabeceras y cuerpo. `process_email` construye `IntakeProposal(attachments=[])`, por lo que la tarjeta recibe `attachment_names={}`. Siguiendo §4, se llama a `archivar` sin pedidos. Aunque el relate devuelva un manifiesto con documentos, la rama `if not pedidos` devuelve `ok=True, verificado=True` y no llama a `adjuntar`. Una tarjeta con un campo por adjunto renderiza cero campos. La confirmación terminal saca el correo de pendientes; el dedup del runner tampoco lo vuelve a procesar. El documento permanece sin archivar en el gestor.
- **Evidencia:** `test_r01_ingesta_pierde_adjuntos_y_archivar_confirma` recorre Gmail sintético → runner real → cliente real con transporte falso, obtiene propuesta vacía y éxito sin POST de adjuntos. El §9 dice que el manifiesto lo da el relate, pero ese POST está después de que la persona deba ver y nombrar los documentos. No se define otra obtención del inventario ni su persistencia, incluida la cola ya existente. No es necesario descargar los bytes para observar el hueco; falta el contrato de metadatos.

## H-02 — `cuenta_usada` no identifica la copia escrita: la selección no llega al POST

- **Severidad:** ALTO
- **Dónde:** spec D6, §5, §7 y §12; `core/procurador_relate.py:290`, `:323`, `:332`, `:396`; contrato CRM §10.10, líneas 934–949.
- **Qué falla:** `account` selecciona la lectura previa, pero no direcciona ninguna de las dos escrituras REST; registrarlo como cuenta usada para escribir inventa una garantía.
- **Cómo se manifiesta:** para un mismo Message-ID existen copias en 15 y 20. El orquestador elige 20 por ser propia, o 15 por ser la menor. Con lecturas previas equivalentes, ambas elecciones producen exactamente el mismo POST `/relate/selected`: Message-ID, elemento, miembros y `cookies/dataHash` vacíos. No viajan cuenta ni id de fila elegida. El adjuntar usa el `mail_id` que devolvió el servidor, sin contrastarlo con una fila de esa cuenta. La traza puede decir «escribí sobre mi copia» sin evidencia de ello. La preferencia es **inerte como selector del destino de escritura**, aunque pueda cambiar el atajo por la lectura previa.
- **Evidencia:** `test_r02_cambiar_cuenta_no_cambia_escritura` compara los cuerpos emitidos para 15 y 20 y demuestra igualdad y ausencia de `account`. También coincide con el contrato escrito en §10.10. **SIN VERIFICAR:** qué fila elige el servidor y si opera globalmente en todos los casos. La medición de obtener el mismo `mail_id` «desde dos cuentas» no discrimina dos escrituras por cuenta si las solicitudes son idénticas. No afirmo que se haya escrito una copia equivocada en vivo; afirmo que el diseño no puede elegirla ni acreditar la elegida con esta interfaz.

## H-03 — El arreglo dentro de `relacionar()` deja un POST fuera y conserva un éxito sin verificación autoritativa

- **Severidad:** ALTO
- **Dónde:** spec §6.1–§6.2 y §4, pasos 6–7; `core/procurador_relate.py:302`, `:458`, `:463`; spec padre §5, paso 5.
- **Qué falla:** el diseño mantiene el atajo basado en `findRelations` y afirma que nada más depende de `ya_estaba`, cuando este activa una escritura directa fuera de la función que se pretende asegurar.
- **Cómo se manifiesta:** la previa dice que el correo ya está relacionado. `relacionar` sale en la línea 304 con `verificado=True`, sin `mail_id`. Si no hay pedidos, `archivar` confirma sin consultar el expediente. Si hay pedidos, `ya_estaba` dispara `_post_relate` directamente en la línea 468 para recuperar el manifiesto; después solo se verifica el censo de documentos. Corregir la relectura dentro de `relacionar` no cubre ese POST. Si la relación fue retirada entre lecturas y ese POST no la restaura, el documento puede aparecer en el gestor y `archivar` declarar éxito sin confirmar la relación.
- **Evidencia:** `test_r03_recuperar_manifiesto_postea_fuera_de_relacionar` sustituye únicamente el resultado del atajo y demuestra POST directo, dos GET de censo y ningún GET de relaciones, con resultado final positivo. Es evidencia del camino existente, no una simulación de una futura implementación completa. El spec padre documenta expresamente la llamada directa. **SIN VERIFICAR:** la concurrencia remota descrita; basta como contraejemplo de cobertura, no como incidente medido. El paso 7 externo de §4 podría cubrir al llamador de la bandeja, pero no cumple la promesa expresa de §6.2 de cerrar el defecto para cualquier llamador. El diseño tampoco resuelve de dónde sale el `mail_id` autoritativo en el atajo sin POST.

## H-04 — El censo por nombre puede omitir documentos distintos y confirmar una cardinalidad o carpeta falsas

- **Severidad:** CRÍTICO
- **Dónde:** spec §8, «adjunto ya en el censo»; §9.2–§9.3 y §11.2; `core/procurador_relate.py:257`, `:283`, `:386`, `:390`, `:417`.
- **Qué falla:** se usa el nombre final como identidad suficiente del documento, perdiendo carpeta, procedencia y multiplicidad.
- **Cómo se manifiesta:** (a) el expediente ya tiene `AUTO.pdf` de un correo anterior, incluso en otra carpeta; llega otro auto distinto al que se da ese nombre. El filtro lo considera presente, no sube los nuevos bytes y devuelve éxito. (b) Ana asigna `AUTO.pdf` a dos adjuntos distintos y el CRM solo incorpora uno: la diferencia de conjuntos contiene ese nombre, el código lo cuenta dos veces en `subidos` y confirma ambos. (c) el nuevo documento aparece en una carpeta distinta de la pedida: la comprobación acepta su nombre igual. Ninguno exige que las mediciones de idempotencia sean falsas.
- **Evidencia:** `test_r04_documento_homonimo_en_otra_carpeta_impide_subida` obtiene éxito y cero POST con un documento preexistente en carpeta 999 y destino pedido 312; `test_r05_dos_documentos_mismo_nombre_se_confirman_con_uno` obtiene dos subidos a partir de una sola entrada posterior. `_censo_gestor_documental` solicita `id_carpeta`, pero devuelve exclusivamente nombres en la línea 283. La frase de §11.2 «se verifica nombre y carpeta» es falsa para el cliente que se va a cablear. No se atribuye sustitución destructiva de bytes al CRM: el daño demostrado es omisión silenciosa y certificación falsa.

## H-05 — La guarda anti-duplicado solo examina los primeros 100 documentos

- **Severidad:** ALTO
- **Dónde:** spec §8–§9.3; `core/procurador_relate.py:264`–`:283`, `:390`, `:410`.
- **Qué falla:** el censo se trata como completo pese a fijar `itemsPerPage=100` y no comprobar totales ni paginar.
- **Cómo se manifiesta:** un expediente tiene 101 documentos y el que se intenta completar ya está fuera de la primera página. La previa no lo ve y se repite el POST del mismo adjunto. Si el nuevo registro tampoco aparece en la primera página posterior, se devuelve error y el siguiente intento puede repetirlo otra vez. Si aparece, se confirma el nuevo duplicado. Una sola máquina y un nombre estable no evitan esta secuencia.
- **Evidencia:** `test_r06_censo_omite_paginacion_y_repostea_documento_existente` entrega 100 entradas con `totalItems=101`: el cliente postea y no pide ninguna página adicional. **SIN VERIFICAR:** existencia actual de un expediente real que active ese límite y duplicación efectiva en ese tenant. La segunda consecuencia depende del comportamiento duplicador citado por el contrato; la lectura truncada y el POST innecesario están reproducidos. Si el servidor limitara o ordenara de otra manera, el diseño tampoco detectaría que su censo no es completo.

## H-06 — La traza prometida no tiene el tercer hecho y el resultado destruye evidencia parcial

- **Severidad:** ALTO
- **Dónde:** spec §7 y §8; `core/procurador_relate.py:86`, `:454`, `:474`, `:480`; `core/procurador_review.py:176`.
- **Qué falla:** extender el log con los campos enumerados no permite distinguir efecto de relación, verificación de relación y resultado documental porque esa información no existe separada en la salida del cliente.
- **Cómo se manifiesta:** el relate se verifica y luego falla el adjuntar. `ArchivoResult.verificado` se sustituye por `res.verificado=False` y se pierde el positivo de la relación. Con un fallo de emparejamiento, en cambio, ese mismo campo es `True` aunque falten todos los documentos. Además `AdjuntarResult.ya_presentes` se descarta al construir `ArchivoResult`, pese a que §7 exige registrarlo. El `mail_id` no prueba «escribí»: puede identificar una fila previa y el contrato acepta 200 sin relación con el destino. F6 no puede reconstruir los tres hechos a partir de estos campos.
- **Evidencia:** `test_r07_relacion_verificada_se_pierde_si_falla_adjunto` verifica la relación con el transporte falso, provoca HTTP 500 en adjuntar y obtiene `ok=False, verificado=False`, sin un campo de relación verificada ni `ya_presentes`. La lista de §7 no contiene el tercer hecho que su párrafo siguiente asegura guardar. Tampoco define fases de intento o efecto desconocido. El mutante `ok = verificado` no basta para probar esa distinción: detectar diferencia entre dos booleanos no crea un tercer dato ausente.

## H-07 — La tabla «completa» omite excepciones y permite escribir sin llegar al registro de la decisión

- **Severidad:** ALTO
- **Dónde:** spec §4, pasos 6–9; §8 y §12; `core/procurador_relate.py:148`, `:340`, `:343`, `:405`; `core/sudespacho_relations.py:1870`–`:1906`; `core/procurador_review.py:212`–`:226`.
- **Qué falla:** registrar únicamente después de toda la operación deja sin traza las escrituras que terminan en excepción, caída del proceso o fallo del propio log.
- **Cómo se manifiesta:** el servidor acepta el relate y se pierde la respuesta; `httpx.ReadTimeout` sale de `_post_relate` y de `archivar`, antes del paso 8. No queda resultado ni actor registrado para ese intento y la cola sigue pendiente. También un JSON inválido tras un POST o una excepción al leer las relaciones del expediente puede interrumpir el flujo. Si todas las escrituras acabaron y falla abrir/escribir el JSONL, se produce el mismo hueco de autoría aunque el CRM esté correcto. «No hay línea en el log» no distingue «no escribí» de «escribí y morí antes de registrar».
- **Evidencia:** `test_r08_timeout_despues_de_escribir_no_devuelve_resultado` registra un commit simulado y lanza `ReadTimeout`; el cliente propaga la excepción. La caída entre pasos se deduce del orden explícito, no se presenta como un proceso real matado. Los 19 tests existentes de `get_relaciones` pasan y confirman que errores HTTP, ausencia de clave y esquemas inesperados se comunican por excepciones, no por el booleano que parece asumir §8. También faltan en la tabla cuenta ilegible por HTTP/JSON, manifiesto malformado y join ambiguo. El spec padre §8.5 ya declara el timeout sin reconciliación; esa declaración no satisface la nueva promesa de trazabilidad al habilitar el clic real. No es un hallazgo de red caída durante esta revisión.

## H-08 — D4 no hace inalcanzable la carrera del censo

- **Severidad:** ALTO
- **Dónde:** spec D4, §4 y §11.3; `core/procurador_relate.py:380`–`:405`; `core/procurador_review.py:357`; `streamlit_app.py:2707`, `:2817`.
- **Qué falla:** restringir las instalaciones con escritura no impide dos ejecuciones concurrentes ni excluye a quien archiva desde Roundcube.
- **Cómo se manifiesta:** Ana abre dos sesiones de la bandeja en su propio ordenador, ambas cargan el mismo pendiente y confirman antes de que se persista el estado terminal. Las dos leen el censo sin el documento y las dos postean. El append/upsert de la cola se produce después y no reserva la operación. D4 permite además la máquina de Nikolai para pruebas, sin imponer en el diseño un destino de pruebas, y no restringe a los escritores del webmail. La carrera existe sin desplegar la app en Paola o Sergio.
- **Evidencia:** `test_r11_dos_ejecuciones_pueden_leer_censo_vacio_y_postear` sincroniza dos ejecuciones reales de `adjuntar` en una sola máquina: ambas leen vacío, se observan dos POST y ambas devuelven éxito. **SIN VERIFICAR:** duplicado persistido por el servidor real; el escenario aplica el comportamiento duplicador declarado en CRM §10.10. La afirmación «D4 lo hace inalcanzable hoy» es falsa incluso concediendo todas las mediciones.

## H-09 — Guardar el nombre en el log no implementa la mitigación de reintento con otro nombre

- **Severidad:** ALTO
- **Dónde:** spec §9.3, §7, §4 y §12; `core/procurador_relate.py:390`, `:433`; `core/procurador_review.py:231`.
- **Qué falla:** el diseño promete comparar una segunda pasada con lo efectivamente subido, pero no define ni cablea esa lectura ni su asociación con el adjunto concreto.
- **Cómo se manifiesta:** una primera pasada sube un documento como `AUTO A.pdf` y otro adjunto falla, por lo que el correo sigue requiriendo revisión. En la siguiente pasada el campo se prerellena con el original, o Ana lo cambia a `AUTO B.pdf`. El censo contiene A, no B, y el cliente vuelve a postear el mismo `att_id`. Que una línea previa conserve A no interviene en ningún paso del flujo de §4. Si el primer POST quedó indeterminado o el log no llegó a escribirse, ni siquiera existe esa línea.
- **Evidencia:** `test_r12_nombre_distinto_repostea_mismo_att_id` reproduce la segunda pasada y confirma el POST con nombre B. `archivar` no recibe decisiones previas; §4 tampoco las consulta. §12 exige que se guarde el nombre usado, pero no un test de reanudación que pruebe que esa información impide el segundo POST. **SIN VERIFICAR:** persistencia duplicada remota. El hueco está reconocido en §9.3 y en el padre §8.2; lo defectuoso aquí es presentar una escritura de log como mitigación operativa ya especificada.

## H-10 — El protocolo de estados invoca una transición inexistente y no define cómo se recupera una revisión

- **Severidad:** MEDIO
- **Dónde:** spec §4, paso 9; §7–§8; `core/procurador_review.py:258`, `:294`, `:301`; `core/procurador_runner.py:146`; `streamlit_app.py:2707`.
- **Qué falla:** el diseño usa `revisar`, `revisión`, `bloqueado` y `archivado_en_crm` sin especificar su integración con una cola que solo admite pendiente, confirmado y descartado.
- **Cómo se manifiesta:** se archiva la relación y falla un adjunto; el paso 9 intenta `transicionar(item, "revisar")` y la máquina actual lanza `TransicionInvalida`. Si el constructor añade un estado revisión sin definir su carga en UI, la bandeja solo lee pendientes y descartados y puede ocultar el trabajo incompleto. Un dry-run, por su parte, termina en confirmado y el runner omite ese correo en futuras ingestas; no hay transición descrita para pedir una nueva confirmación viva. No debe inferirse permiso retroactivo del dry-run, pero el diseño debe distinguir ese estado de archivo real y definir su tratamiento.
- **Evidencia:** `test_r09_cola_no_admite_revisar` reproduce la excepción y comprueba que `archivado_en_crm` no existe. Se señala un contrato de transición incompleto, no se exige que el módulo nuevo ya esté construido. §7 habla de extender `record_decision`, pero no fija una tabla de transiciones ni la recuperación operativa de los estados que §8 manda producir.

## H-11 — La autoría local heredada puede atribuir a otra persona el clic

- **Severidad:** ALTO
- **Dónde:** spec D6, §4 y §7; `streamlit_app.py:2701`–`:2705`, `:2826`; `core/intake_log.py:121`–`:163`; §11.1 del diseño.
- **Qué falla:** el mecanismo existente para obtener `quien` es un selector con un valor inicial ajeno a Ana y un singleton global, no una identidad fijada por operación y sesión.
- **Cómo se manifiesta:** Ana abre la bandeja y confirma sin cambiar «Yo soy», cuyo primer valor es Nikolai: se registra Nikolai. En dos sesiones, A ejecuta `set_actor("Ana")`; B ejecuta `set_actor("Paola")`; A llega a `get_actor()` y registra Paola. El lock protege cada acceso, no la pertenencia del valor a una sesión. Pasar `quien` como argumento solo ayuda si se define una fuente estable, que el diseño no concreta. La cuenta de servicio del CRM no repara esa atribución local.
- **Evidencia:** lectura del radio y del singleton; `test_r10_actor_de_otra_sesion_sustituye_al_primero` demuestra la intercalación, sin afirmar que se haya ejecutado Streamlit. D6 deposita expresamente la autoría en este log. Además la prueba propuesta en §11.1 —leer `id_creador` después de archivar— puede leer simplemente el creador anterior de una fila que §2.1 exige que ya exista; no identifica por sí sola al autor del nuevo vínculo o del nuevo documento. **SIN VERIFICAR:** qué registros/campos de auditoría cambia realmente el CRM al relacionar; el diseño no define el objeto cuya autoría medirá.

## H-12 — Al corregir un match alto, la tarjeta puede mostrar un expediente y confirmar otro

- **Severidad:** ALTO
- **Dónde:** spec §4, `destino_efectivo`, y cableado al botón existente; `streamlit_app.py:2753`–`:2768`, `:2796`–`:2805`, `:2822`.
- **Qué falla:** el encabezado de éxito conserva el id propuesto mientras el clic usa el id reasignado en la sesión.
- **Cómo se manifiesta:** una tarjeta alta propone el judicial 683. Ana selecciona «Cambiar expediente» y usa el 800. El rerun conserva `exp_id=683`, carga `sel_exp_id=800` y datos del 800, pero sigue mostrando «Expediente #683». Al confirmar, `HumanAction.expediente_id=800` y el destino efectivo será el 800. El diseño habilita escrituras reales apoyándose en esa tarjeta sin corregir la incoherencia entre lo mostrado y lo enviado. Si la persona cree haber vuelto al expediente indicado en el encabezado, confirma una relación para otro asunto.
- **Evidencia:** lectura de las asignaciones, del `st.success(f"Expediente #{exp_id}...")` y del override del botón. **SIN VERIFICAR en navegador:** no se ejecutó la UI. La divergencia de variables es determinista en el código; no se afirma que el usuario haya cometido ya ese error. Es un defecto existente que el paso de dry-run a escritura de clientes vuelve material.

## H-13 — La igualdad de `hasAttachments` no verifica la igualdad del contenido entre copias

- **Severidad:** MEDIO
- **Dónde:** spec §11.4 y §5; `core/procurador_relate.py:206`–`:218`; contrato CRM §10.10, líneas 997–1006.
- **Qué falla:** se retira una incógnita sobre identidad/completitud documental usando una medida booleana que no puede resolverla.
- **Cómo se manifiesta:** una copia contiene dos adjuntos y otra solo uno, o un adjunto distinto, y ambas dan `hasAttachments=True`. También un inline puede dar True sin documentos archivables, según el propio contrato. Si, como dice §11.4, el booleano es propiedad del mensaje global, cambiar `account` ni siquiera garantiza estar midiendo cada copia. El ensayo de igualdad puede salir 10/10 sin observar diferencias de manifiesto o de bytes. Elegir cualquiera y dar por descartada la pérdida no se deduce del resultado.
- **Evidencia:** el cliente devuelve únicamente `bool(...hasAttachments)`; el documento reconoce que no cotejó `att_id`. **SIN VERIFICAR:** el 10/10, cualquier diferencia real de adjuntos entre copias y el alcance efectivo del endpoint. El escenario es un contraejemplo lógico, no un incidente observado. La conclusión no se sostiene ni siquiera suponiendo exacta la cifra citada; si la medición fuera errónea, tampoco hay una comprobación compensatoria del inventario que va a recibir el usuario.

## H-14 — Hay mandatos incompatibles sobre nombre final, visibilidad y activación de otra persona

- **Severidad:** MEDIO
- **Dónde:** spec §4, línea 92; D3 y §9/§12; D7, §5.1, §10, líneas 313–316; D4, §3, líneas 72–74, y D8/§5.2.
- **Qué falla:** un constructor no puede obedecer simultáneamente varias instrucciones vigentes del propio diseño sin decidir cuál descartar.
- **Cómo se manifiesta:** (a) implementa literalmente el paso 6 de §4 y envía `(original, original)`, ignorando los nombres humanos que D3 y §12 obligan a enviar. (b) aplica §10 al spec de entrega y escribe que la visibilidad está abierta y no se promete ninguna superficie, contradiciendo D7/§5.1/§11.5, que dicen que ambas superficies quedaron explicadas. (c) habilita la variable en otra máquina siguiendo «Se levanta poniendo la variable a quien la cubra», pero §5.2 exige que cuando escriba otra persona cambie la arquitectura a su buzón; D4 ya permite a Nikolai escribir para probar sin delimitar esa excepción al disparador.
- **Evidencia:** contradicciones textuales del objeto. No dependen de red. El mandato de revisión confirma que las decisiones deben contrastarse entre sí; no corresponde al revisor adjudicar cuál de estas frases expresa la última intención de Nikolai. La tensión D1/D2 también requiere un criterio: §4 sale del dry-run antes de consultar copias y §12 exige dry-run sin red, mientras D2 manda bloquear el correo no indexado sin limitar esa regla al modo vivo.

## Cobertura del mandato y límites: SIN VERIFICAR

| Pregunta del mandato | Resultado de revisión |
|---|---|
| Correspondencia diseño/código y afirmaciones falsas | H-01, H-02, H-03, H-04, H-10, H-12. Además §1 exagera el grep: hay imports de lectura en `scripts/sondeo_copias_mail.py`, `sondeo_join_gmail_crm.py` y `_sondeo_crm.py`; no encontré un llamador productivo de `archivar` en core/scripts/Streamlit. Esa precisión no cambia el veredicto. |
| Guardas con otro valor o inertes | H-02: cuenta inerte para direccionar escritura; H-04: comprobación inerte respecto a carpeta y multiplicidad; H-05: guarda incompleta; H-13: booleano no discrimina igualdad de contenido. El interruptor nuevo y la guarda judicial aún no existen: no se certifica su implementación futura. |
| Escritura sin verificación / éxito sin comprobación | H-01, H-03, H-04, H-06, H-07. |
| Pérdida, duplicación o corrupción | Omisión y falsos positivos en H-01/H-04; reenvíos duplicadores en H-05/H-08/H-09; riesgo de relación con destino distinto del mostrado en H-12. No se ha demostrado corrupción binaria ni borrado de documentos. |
| Estados de error | H-06, H-07, H-10. La lectura autoritativa distingue errores lanzando excepciones; el diseño debe conservar esa distinción. |
| Tres situaciones de escritura y autoría | H-02, H-06, H-07, H-11. |
| Coherencia D1–D8 | H-01/H-09 para D3; H-08 para D4; H-02 para D6; H-14 para contradicciones. No se cuestiona judicial-first ni mantener `procesal@` como decisión de producto. |
| Supuestos no expresados o no sostenidos | Inventario previo de adjuntos, identidad por nombre, censo completo, cuenta direccionable, exclusión por máquina, actor estable, equivalencia de contenido y atomicidad de escritura/log/cola: hallazgos anteriores. |

**Mediciones externas: todas SIN VERIFICAR.** No hubo red ni se intentó reproducir las cifras de los días 7 y 8: número de Message-ID y copias, censo de 4.000 documentos, ratios de renombrado, 10/10 de `hasAttachments`, identidad de cuentas, invariancia de Message-ID, visibilidad por sesión, creación de filas mediante Roundcube, espacio de ids o idempotencia del relate. No se declaran falsas. Los nombres de pruebas y fixtures del repo que dicen «medido» siguen siendo afirmaciones del autor, no observación de esta revisión.

La robustez ante su error sí se revisó: si el relate no fuera idempotente, degradar la previa a atajo y repetirlo para recuperar manifiestos expondría más escrituras; la presencia de un `mail_id` en el expediente no probaría ausencia de duplicados. Si el espacio de ids o la forma del bloque `mail` difirieran, faltaría una política explícita para ausencia de bloque/id y lecturas inciertas, con el hueco de traza de H-07. Si la igualdad de contenido entre copias fuera falsa, H-13 muestra que el ensayo citado no lo detecta. Las cifras de renombrado no reparan el inventario ausente ni las colisiones de nombres, sean o no exactas. No se propone cambiar D8 basándose en una cifra no contrastada.

**Cobertura ejecutada limitada al código existente y datos falsos.** No existen aún `procurador_archivo.py`, el interruptor ni el nuevo flujo de verificación del diseño; no se acredita ejecución end-to-end de esas piezas, D1–D8 implementadas ni los mutantes de §12. Los tests existentes se copiaron sin cambiar sus bytes; se usó un conftest propio con bloqueo de red. No se ejecutó la suite global ni su conftest, ni se atribuye a la revisión su cobertura. Las dos semillas exigidas por el repo quedan **SIN VERIFICAR** por ausencia de `pytest-randomly` indicada en el mandato; los módulos MCP y sus dependencias ausentes tampoco se evaluaron. No son defectos del objeto.

**UI y efectos remotos SIN VERIFICAR:** no se abrió Streamlit, no se hicieron POST reales, no se descargaron o cotejaron bytes, no se observaron permisos con sesiones personales ni se probó `id_creador`. Los escenarios de caída, selección visual y diferencias entre copias están identificados como deducciones o hipótesis donde corresponde. No se afirma haber producido daños en expedientes reales.

Este informe expresa el resultado del revisor. La adjudicación corresponde al autor contra las fuentes; no está incorporada aquí.
<!-- informe-literal:fin:k7wq -->

## 2. Evidencia verificada — lo que se comprobó contra la fuente, y lo que no

**Adjudicado en:** §15 del spec del cableado. Resumen: **14 confirmados · 0 rebajados ·
0 refutados**, con H-02, H-05 y H-11 **agravados** al verificarlos.

De los catorce, siete se comprobaron línea a línea contra el código congelado y los siete se
sostienen:

| Hallazgo | Qué se comprobó | Resultado |
|---|---|---|
| H-01 | `procurador_runner.py:103` pone `attachments=[]`; `procurador_review.py:98` lo consume; `procurador_relate.py:458` devuelve `ok=True` sin pedidos | confirmado |
| H-02 | el cuerpo de `_post_relate` no contiene `account` | confirmado, y **agravado** por medición propia (abajo) |
| H-04 | `_censo_gestor_documental` pide `id_carpeta` y devuelve **solo** `nombrefinal` | confirmado; el §11.2 de la v1 era falso |
| H-05 | `itemsPerPage=100`, sin paginar, **y pidiendo `return_totals=true`** | confirmado y **agravado**: el dato para detectar el truncamiento viene y se tira |
| H-10 | `transicionar` solo admite `confirmar\|descartar\|recuperar`; `"revisar"` lanza | confirmado |
| H-11 | `st.radio("Yo soy", ["Nikolai","Paola","Ana"])` | confirmado y **agravado**: el defecto es Nikolai **y Sergio no está en la lista**, aunque D4/D6 lo contemplen |
| H-12 | `st.success(f"Expediente #{exp_id}…")` frente al `sel_exp_id` del botón | confirmado |

**La medición que H-02 provocó, y que cambió el diseño más que el propio hallazgo.** El revisor
dijo que `account` no direcciona la escritura y dejó SIN VERIFICAR qué fila elige el servidor.
Se midió el 2026-09-09: correo con copias en las cuentas 2 y 15, relate hacia
`extrajudiciales:636` **pasando `account=2`**; después, **la copia de la 15 ve la relación y la de
la 2 sigue vacía**. Con control positivo hecho (`findRelations(account=2)` devuelve relaciones para
5 de 5 correos suyos con `estarelacionado=1`, así que no está muda). Conclusiones:
**la relación NO es global**, **`account` no dirige la escritura**, y **la copia la elige el
servidor** con una regla no medida. Eso **retira el §5 entero** y obligó a corregir la afirmación
«la relación es global» en tres sitios donde yo la había escrito el 2026-09-07, incluido
`INTEGRACION_SUDESPACHO §10.10`, que es el SSOT del contrato del CRM.

**Lo que el revisor NO pudo verificar, y está bien que lo dijera:** todas las mediciones contra el
CRM y Gmail de los días 7 y 8 (sin red), la UI de Streamlit (no la abrió), las dos semillas del
repo (su Python de sistema no trae `pytest-randomly`), y los módulos MCP. Nada de eso es defecto
del objeto. **Y su cautela fue productiva**: en vez de asumir o descartar las cifras, evaluó si los
razonamientos **se sostendrían si fueran erróneas**, que es lo que produjo H-13.

**Una precisión suya sobre mi propio texto, y tiene razón:** el §1 decía que `git grep
procurador_relate` «devuelve solo su propio test». Es falso desde el 2026-09-08, **por mis propios
commits**: los tres sondeos que promoví ese día importan del módulo. No cambia el veredicto —sigue
sin haber llamador de producción— pero la frase quedó rancia en un día.

## 3. Evidencia de ejecución declarada por el revisor, literal

Se archiva porque es la parte que acredita que la ronda **corrió** en vez de leer:

```text
# Evidencia local R1

Objeto ejecutado: copia de `../head/core/` en `scratch/core/`, sin cambios de implementación.
Python: `C:/Users/tnm33/AppData/Local/Python/pythoncore-3.14-64/python.exe`.
Entorno: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`.
Los tests usan `scratch/pytest.ini` y un `scratch/conftest.py` propio que bloquea conexiones y resolución DNS con una excepción derivada de `BaseException`. No se cargó el conftest del repositorio.

## Ejecuciones con resultado recuperado

Desde `scratch/`:

```text
python -m pytest -c pytest.ini -q --tb=short --basetemp=../t test_adversarial.py test_original_relate.py test_original_review.py test_original_gmail.py test_original_runner.py
97 passed in 9.49s
exit_code: 0
```

Desde el directorio del informe:

```text
python -m pytest -c ./scratch/pytest.ini -q --tb=short --basetemp=./tr ./scratch/test_original_relaciones.py
19 passed in 8.26s
exit_code: 0
```

Total: 104 pruebas preexistentes y 12 reproducciones adversariales, en dos invocaciones con salida recuperada. Los 12 tests adversariales afirman el comportamiento defectuoso existente: su verde confirma el contraejemplo. No son tests de una implementación del diseño nuevo.

Hubo un lanzamiento anterior del primer comando cuyo identificador de sesión no se conservó al extraer solo el campo `output` del resultado. No se atribuye cobertura a esa ejecución. Se recuperó la salida completa y el código de salida de la invocación posterior, indicados arriba.

Las bases temporales están dentro del directorio autorizado, con nombres `t` y `tr`. No se utilizó `C:/t/rev` porque no está entre las rutas autorizadas. No hubo fallos MAX_PATH en estas ejecuciones.

No se ejecutó la suite entera, las dos semillas con pytest-randomly, los módulos MCP ni el arnés de mutación del diseño futuro. No se llamó a CRM, Gmail, OAuth ni servicios externos.
```
