# Tics de IA en escritura jurídica española — Capa (a) NO-IA

**Fuentes destiladas (sin pérdida):**
- **blader/humanizer** (MIT) — 33 patrones + calibración de voz + alma + guardarraíles + bucle draft→audit→final. Base: *Wikipedia, Signs of AI writing*.
- **LawyerScrib / Humanizer Juridique** (MIT, G. Haas) — 17 patrones del mismo fenómeno aplicados a Derecho (adaptación francesa que aquí se reexpresa al foro español).
- **Persuasive Legal Writing, Parte III** (AGPL-3.0, L. Meredith-Flister) — tics legal-analíticos del «escrito que habla de sí mismo». Reexpresado en español propio; sus referentes anglosajones se han hecho genéricos.

**Convención de marcado:**
- `[YA EN CLARIDAD]` — el patrón ya está cubierto en `claridad_es.md`; aquí solo se cruza la referencia y, si la fuente aporta un matiz, se conserva el matiz sin reproducir el desarrollo.
- `[NUEVO]` — aporte no presente en `claridad_es.md`.
- `(blader §N / LawyerScrib §N / Persuasive III)` — origen, para auditar la fusión.

**Idea-fuerza común a las tres fuentes:** un LLM reproduce los *tics de forma* del lenguaje (jurídico o no) sin la *sustancia* que lo justifica. Reescribir no es solo limpiar: es devolver al texto una posición, un ritmo y una concreción que solo tiene un humano que sabe lo que dice. El objetivo no es un texto «neutro», sino un texto **comprometido y preciso**.

---

## 1. Principios rectores (con su porqué)

1. **Reescribir, no borrar; cubrir todo lo que cubría el original.** (blader) Se sustituye el tic por su alternativa natural, sin amputar contenido: si el original tenía cinco párrafos, la versión final tiene cinco. *Por qué:* la limpieza anti-IA no puede convertirse en una excusa para perder argumento; el riesgo del humanizado es vaciar.

2. **Preservar el fondo: razonamiento, jerarquía de argumentos y referencias.** (LawyerScrib) Se tocan las palabras, no la tesis ni el orden lógico ni las citas normativas. *Por qué:* en un escrito procesal, alterar el andamiaje argumental al «mejorar el estilo» introduce errores de fondo.

3. **Quedarse DENTRO del argumento.** `[NUEVO]` (Persuasive III) El defecto común de todos los tics legal-analíticos es que el autor se sale del razonamiento para comentarlo: anuncia su estructura, cuenta sus partes, etiqueta su método o acota su alcance. El lector debe *experimentar* el razonamiento, no recibir una visita guiada de él. *Por qué:* el meta-comentario delata a la máquina y, además, ralentiza; un juez con prisa quiere el argumento, no el índice del argumento.

4. **Tomar posición; un abogado argumenta, no «conviene».** (LawyerScrib) «El argumento de contrario es inoperante» vale más que «cabe sostener que esa tesis presenta ciertos límites». *Por qué:* la nitidez y el compromiso se leen como dominio del caso; el hedging, como debilidad de la posición. [YA EN CLARIDAD: pose / sin autobombo]

5. **Nombrar las cosas.** (LawyerScrib) No «la resolución precitada» sino «la STS 333/2021, de 12 de mayo». La especificidad es marca de competencia, no de pesadez. *Por qué:* lo concreto, en Derecho, además prueba. [YA EN CLARIDAD: concreción]

6. **Variar el ritmo.** (blader / LawyerScrib) Frase corta. Luego una más larga que desarrolla el razonamiento hasta su conclusión natural. Alternar. *Por qué:* la cadencia uniforme de longitud media es uno de los rasgos más fiables de la prosa de IA. [YA EN CLARIDAD: longitud media baja con variación]

7. **Dejar entrar la complejidad.** (blader / LawyerScrib) «Esta solución es favorable, pero expone a un riesgo de recalificación» es más honesto que apilar ventajas. *Por qué:* el LLM tiende a la tesis limpia y sin tensión; el matiz reconocido suena humano y resulta más creíble.

8. **Pasada final anti-IA obligatoria.** (blader / LawyerScrib) Tras el borrador, preguntarse: «¿qué sigue delatando a la IA aquí?», responder en pocas viñetas y revisar. *Por qué:* los tics estructurales sobreviven a las pasadas de estilo porque «parecen organizados»; hay que cazarlos en una pasada propia. [YA EN CLARIDAD: proceso de relectura]

9. **El alma solo donde el registro la pide.** `[NUEVO]` (blader) Inyectar opinión, primera persona o humor solo cuando el contenido y la voz lo piden (carta, nota de opinión). En texto enciclopédico, técnico, contractual o procesal, lo neutro y llano *es* la voz humana correcta; ahí no se inyecta personalidad. *Por qué:* confundir «con alma» con «con florituras» reintroduce justo lo que delata a la IA en el registro formal.

---

## 2. Reglas accionables (imperativas)

1. Sustituye toda inflación de trascendencia («marca un hito», «se inscribe en una tendencia más amplia») por lo que la cosa hace en el caso.
2. Cita fuente precisa (autor, obra, página; tribunal, sala, fecha, ROJ/ECLI) en lugar de atribuir a «la doctrina» o «la jurisprudencia» en abstracto.
3. Recupera el verbo **ser** y el verbo directo donde el LLM puso una copula artificial («reviste un carácter», «se erige como»).
4. Pon el sujeto delante: di quién hace qué; reserva la pasiva para cuando el agente sea irrelevante, desconocido o sea el propio tribunal.
5. Rompe la tríada y la lista en cascada cuando dos puntos bastan; no fuerces grupos de tres.
6. Suprime el conector de relleno; usa punto y seguido o un nexo con contenido.
7. Borra el énfasis hueco («sin lugar a dudas», «es incuestionable»): que hablen el hecho y la norma.
8. Quita el meta-comentario que narra el propio escrito; aplica la norma a los hechos en su sitio.
9. Cierra con posición tajante y recomendación concreta, no con una apertura difusa.
10. Elimina el em dash (—) y el guion doble usados al modo anglosajón; reescribe con punto, coma, dos puntos o paréntesis.
11. Quita el negrita decorativo sobre términos jurídicos y la lista de viñetas con encabezado en negrita + dos puntos.
12. Borra fórmulas de cortesía apiladas en correos y la apertura sicofántica.
13. Tras el borrador, corre la **pasada anti-IA** (§5) y la **auditoría de repetición** (no conviertas un buen arreglo en un tic repitiéndolo tres párrafos después).

---

## 3. Inventario consolidado y exhaustivo de patrones

> Fusión sin pérdidas de blader (33) + LawyerScrib (17) + tells de Persuasive III. Cuando dos fuentes cubren el mismo patrón se cita ambas y se conserva el tratamiento más rico.

### 3.1 Contenido y sustancia

| Patrón | Por qué falla | Alternativa breve |
|---|---|---|
| **Inflación de trascendencia, legado y tendencias amplias** (blader §1 / LawyerScrib §1) — «marca un hito», «se inscribe en una tendencia más amplia», «testimonia», «refleja una evolución». `[NUEVO matiz: la dimensión legado/tendencia]` | Hincha la importancia de cualquier cosa, incluso de una cláusula ordinaria. | Decir qué hace la cosa en el caso: «esta cláusula penal fija a tanto alzado los daños; su importe es manifiestamente desproporcionado (art. 1154 CC)». |
| **Énfasis en notoriedad y cobertura mediática** (blader §2) `[NUEVO]` | Apila menciones de relevancia o de fuentes sin contexto. | Dar el dato con contexto y fuente, una vez. |
| **Análisis superficial con gerundios** (blader §3) — «destacando…», «reflejando…», «garantizando…» colgados al final de la frase. `[NUEVO]` | El gerundio encadenado simula profundidad y esconde que no se añade nada. | Frase nueva con sujeto y verbo: «El arquitecto eligió esos colores por X». |
| **Lenguaje promocional / publicitario** (blader §4) — «destaca por», «vibrante», «en el corazón de», «de renombre». | El LLM no mantiene tono neutro, sobre todo en temas «de prestigio». | Descripción factual y sobria. [YA EN CLARIDAD: poesía barata / hipérbole — se conserva el matiz «registro publicitario»] |
| **Atribuciones vagas y comodín de autoridad** (blader §5 / LawyerScrib §2) — «la doctrina estima», «los autores coinciden», «la jurisprudencia tiende a», «expertos creen». | Simula autoridad sin fuente. En Derecho es grave: no acredita. | Fuente precisa con ratio: «Según Díez-Picazo (*Fundamentos*, t. II, 2008, p. X)…»; «STS, Sala 1ª, 3-11-2021, nº 20-15.656». [Cruza con regla §2.2] |
| **Sección «Retos y perspectivas» / «Balance y límites» / plan en II partes espejo** (blader §6 / LawyerScrib §8) — «pese a sus avances, persisten desafíos…», conclusión balanceada que no concluye. `[NUEVO]` | Estructura formularia que cierra en falso. | Decir la fragilidad concreta: «la cuestión no la ha resuelto el Pleno; CA Madrid y CA Barcelona divergen; cabría plantear cuestión». |

### 3.2 Lenguaje y gramática

| Patrón | Por qué falla | Alternativa breve |
|---|---|---|
| **Vocabulario IA postizo** (blader §7 / LawyerScrib §9) — «crucial, fundamental, primordial, incontournable→ineludible, paradigma, holístico, enjeux→envergadura, problemática (por “cuestión”), robusto»; en inglés «delve, tapestry, leverage, underscore». | Aparecen mucho más en texto post-2023 y coocurren. | Palabra precisa o ninguna. [YA EN CLARIDAD: comodín / verbo-comodín — se conserva la **lista** de palabras-IA como matiz nuevo] |
| **Evitación de «ser» / copula artificial** (blader §8 / LawyerScrib §4) — «reviste un carácter», «se erige como», «presenta las características de», «tiene por efecto». | Sustituye «es/son/tiene» por perífrasis que pesan sin añadir sentido. | «Esta obligación **es** esencial y constituye una obligación de resultado.» [YA EN CLARIDAD parcial: verbo-comodín; matiz nuevo: el principio sistemático de recuperar la copula] |
| **Paralelismos negativos y negación de cola** (blader §9 / LawyerScrib §13) — «no solo X, sino Y»; «no es una mera cláusula, es una declaración»; coletilla negativa («sin margen de duda») pegada al final. `[NUEVO]` | Construcción artificiosa y redundante; de cola, es un fragmento sin oración real. | Afirmar directo: «Este litigio versa sobre el equilibrio económico del contrato, no solo sobre una cláusula» (una sola vez). |
| **Regla de tres / listas en cascada** (blader §10 / LawyerScrib §7) — todo en triadas para parecer exhaustivo. `[NUEVO]` | Fuerza grupos de tres aunque dos basten. | «La cláusula es nula: crea un desequilibrio significativo (art. 82 TRLGDCU), lo que ya engloba los dos primeros reproches.» |
| **Variación elegante / sinónimos rotativos** (blader §11) — «el protagonista… el personaje principal… la figura central… el héroe». `[NUEVO]` | El penalty-anti-repetición del modelo cambia de sinónimo sin necesidad y confunde. | Mantener el mismo término: «el demandante… el demandante». En Derecho la coherencia terminológica es exactitud. |
| **Falsos rangos** (blader §12) — «desde X hasta Y» cuando X e Y no están en una escala real. `[NUEVO]` | Crea una gradación inexistente. | Enumerar lo que se cubre, sin el «de… a…» retórico. |
| **Pasiva y fragmentos sin sujeto** (blader §13 / LawyerScrib §5) — «fue sostenido por la demandante que…», «se preservan los resultados automáticamente». | Esconde al agente para parecer neutro. | «La demandante sostiene que…»; activa cuando aclara. [YA EN CLARIDAD: activa por defecto + «qué no trasladar: la pasiva legítima»] |
| **Nominalización abusiva** (LawyerScrib §6) — «la realización de la ejecución de la obligación». | Convierte verbos en sustantivos y alarga. | «Ejecutar la obligación». [YA EN CLARIDAD vía guía UE: verbo sobre nominalización] |
| **«Dicho/dicha, el referido, precitado, ut supra» abusivos** (LawyerScrib §12) — referencias circulares para simular rigor. | Economía falsa: pesan y no ahorran. | «El contrato de 3-1-2023 prevé en su art. 5…». [YA EN CLARIDAD parcial: «el mismo/la misma»; matiz nuevo: precitado/ut supra/supra] |

### 3.3 Estilo y formato

| Patrón | Por qué falla | Alternativa breve |
|---|---|---|
| **Em dash / raya larga al modo anglosajón** (blader §14 / LawyerScrib §14) — «La cláusula es nula —indiscutible— por dos razones —…—». | Uno de los delatores de IA más fiables; imita la prensa anglófona. | Punto, coma, dos puntos o paréntesis: «La cláusula es nula por dos razones: falta de contrapartida y desproporción». **Escaneo final:** ningún «—» ni «–». `[NUEVO para foro]` |
| **Negrita mecánica sobre términos jurídicos** (blader §15 / LawyerScrib §15) — «el **demandante** debe probar el **daño** y el **nexo causal**». `[NUEVO]` | Simula pedagogía; en escrito procesal distrae. | Sin negrita: «el demandante debe probar el daño y el nexo causal». |
| **Listas verticales con encabezado en negrita + dos puntos** (blader §16) — «- **Seguridad:** se ha reforzado la seguridad…». `[NUEVO]` | Cada ítem repite su propio encabezado y vacía la frase. | Prosa corrida que integra los puntos. |
| **Emojis** (blader §18) | Decoran encabezados y viñetas. | Ninguno. [YA EN CLARIDAD: nunca en foro] |

### 3.4 Comunicación (correos, consultas, trato)

| Patrón | Por qué falla | Alternativa breve |
|---|---|---|
| **Artefactos de chatbot** (blader §20) — «Aquí tienes…», «¡Por supuesto!», «Espero que esto ayude», «¿Quieres que amplíe?». `[NUEVO]` | Texto pensado como conversación con la máquina, pegado como contenido. | Borrar; entrar en el contenido. |
| **Fórmulas de cortesía IA apiladas en correos** (LawyerScrib §10) — «Espero que este mensaje le encuentre bien», «quedo a su entera disposición para cualquier aclaración». `[NUEVO]` | Suenan a plantilla y a falso. | «Como hablamos esta mañana, esta es nuestra posición. Si tiene dudas, llámeme.» |
| **Disclaimers de fecha de corte y relleno especulativo** (blader §21) — «hasta mi última actualización…», «aunque la información es limitada…», «mantiene un perfil bajo». `[NUEVO]` | Deja el aviso de corte en el texto o inventa relleno plausible para tapar el hueco. | Decir lo que no consta y citar fuente, o suprimir la frase. |
| **Tono sicofántico / servil** (blader §22 / LawyerScrib §17) — «¡Excelente pregunta! Tiene toda la razón…». | Lenguaje complaciente y hueco. | «Este es el análisis.» [YA EN CLARIDAD parcial: autobombo; matiz nuevo: la apertura servil] |
| **Conclusión genérica sin posición tajante** (LawyerScrib §11) — «la situación es compleja y requiere un análisis pormenorizado; hay argumentos en ambos sentidos». `[NUEVO]` | No compromete a nada; no es asesorar. | «La acción de nulidad tiene < 40 % de éxito; la vía sólida es la resolución (art. 1124 CC); actúe antes del 15-IX por la prescripción.» |

### 3.5 Relleno, hedging y cierres

| Patrón | Por qué falla | Alternativa breve |
|---|---|---|
| **Muletillas / fórmulas de relleno** (LawyerScrib §3 / blader §23) — «conviene señalar/recordar/precisar», «procede destacar», «a este respecto», «en todo caso» (sistemático), «huelga decir». | Llenan espacio sin aportar al razonamiento. | Suprimir y afirmar lo que sigue. [YA EN CLARIDAD: tabla §3 «conviene señalar»; matiz nuevo: catálogo forense ampliado] |
| **Frases-relleno** (blader §23) — «con el fin de lograr este objetivo»→«para»; «debido al hecho de que»→«porque»; «en este momento»→«ahora»; «tiene la capacidad de»→«puede». | Perífrasis que se reducen sin pérdida. | La forma breve. [YA EN CLARIDAD: economía; matiz nuevo: pares concretos] |
| **Hedging excesivo** (blader §24 / LawyerScrib §16) — «parecería que podría eventualmente sostenerse que…». | Sobre-cualifica para no comprometerse. | «Esta posición es contestable: lee contra legem el art. 1130 CC.» [YA EN CLARIDAD: sin hedging] |
| **Conclusiones positivas genéricas** (blader §25) — «el futuro es prometedor; tiempos apasionantes por delante». `[NUEVO]` | Cierre optimista vacío. | Dato concreto: «prevé abrir dos sedes el próximo año». |
| **Tropos de autoridad persuasiva** (blader §27) — «la verdadera cuestión es», «en el fondo», «lo que de verdad importa», «la raíz del asunto». `[NUEVO]` | Fingen cortar el ruido hacia una verdad profunda; tras ellos suele venir lo trivial con ceremonia. | «La cuestión es si…», y a continuación el contenido real. |
| **Señalización y anuncios** (blader §28) — «vamos a profundizar en», «desglosemos esto», «esto es lo que necesitas saber». `[NUEVO]` | Anuncia lo que va a hacer en vez de hacerlo; tono de tutorial. | Hacerlo directamente. [Conecta con Persuasive III §7] |
| **Encabezados fragmentados** (blader §29) — un epígrafe seguido de una línea que repite el epígrafe antes del contenido real. `[NUEVO]` | Calentamiento retórico que no aporta. | Pasar al contenido bajo el epígrafe. |
| **Escritura anclada al diff** (blader §30) — narrar un cambio en vez de describir la cosa: «esta cláusula se añadió para sustituir el anterior régimen…». `[NUEVO]` | Salvo en documentos de versión (control de cambios), debe leerse sin saber qué cambió. | Describir la cláusula como es. |
| **Remates fabricados y dramatismo staccato** (blader §31) — frases que aterrizan todas como cita célebre, fragmentos cortos apilados. `[NUEVO]` | Una corta para enfatizar está bien; una ráfaga suena fabricada. | Reconstruir con ritmo variado y dato concreto. |
| **Fórmulas-aforismo** (blader §32) — «X es el lenguaje de Y», «la arquitectura de», «se convierte en una trampa». `[NUEVO]` | Convierte una idea común en aforismo que suena profundo sin precisar. | La afirmación concreta que insinúa. [Cruza con «poesía barata», YA EN CLARIDAD] |
| **Aperturas retóricas conversacionales** (blader §33) — «¿Sinceramente?», «Mira», «La cosa es que», como gancho de falsa candidez. `[NUEVO]` | Pausa teatral para fabricar intimidad antes de un punto ordinario. | Decir la cosa directamente. |

---

## 4. Guardarraíles de blader (no sobre-corregir)

### 4.1 Qué NO marcar — falsos positivos
Un humano competente puede dar en varios de estos patrones sin IA alguna. Antes de reescribir, comprueba que no estás destripando prosa legítima. **No** son indicadores fiables por sí solos:

- **Gramática perfecta y estilo consistente.** Muchos redactores son profesionales o han sido editados; el pulido no es IA.
- **Mezcla de registro culto y llano.** Suele señalar a un técnico o a una pluma personal, no a un chatbot.
- **Prosa «sosa» o «robótica».** La IA tiene tics *específicos*; la sequedad genérica sin esos tics es solo prosa seca.
- **Vocabulario formal o cultismos legítimos.** La IA abusa de palabras *concretas* (§3.2), no de todo cultismo. No achates «ostensible», «prima facie» *técnico* o «constitutivo» por sonar doctos.
- **Fórmula de saludo o despedida** en una carta: anteceden a ChatGPT en siglos.
- **Conectores comunes aislados.** «Además», «por tanto», «sin embargo» solo delatan cuando se apilan; un «no obstante» suelto no es tic.
- **Comillas, em dash o un cultismo aislados.** Solo cuentan acumulados con otros tells.
- **Una frase corta enfática aislada.** Solo marca «dramatismo staccato» cuando hay varias seguidas.
- **«Sinceramente»/«mira» a mitad de frase** (no como gancho teatral autónomo).
- **Afirmaciones sin fuente.** La mayoría del texto del mundo no está citado; no prueba nada por sí solo.
- **Formato correcto y complejo.** Plantillas y editores visuales producen salida limpia sin IA.

*Regla:* busca **racimos** de tells, no tics aislados. Un em dash no dice nada; em dash + regla de tres + «vibrante tapiz» + sección «Conclusión» es una confesión.

### 4.2 Señales de escritura humana — preservar
Cuando aparezcan, deja la prosa tranquila; sobre-editar destruye lo que la hace humana:

- **Detalle específico, raro, difícil de fabricar.** Una dirección real, una cita extraña, «el procurador que tenía el despacho encima del de mi dentista». La IA redondea los específicos; el humano los atesora.
- **Sentimientos encontrados y tensión sin resolver.** «Creo que está bien, pero me incomoda y no sé explicar por qué.» La IA va a la tesis limpia.
- **Referencias datadas, de época.** Jerga o guiños que mapean a un año o subcultura concretos; los modelos van con retraso.
- **Decisiones editoriales en primera persona que el autor puede defender.** Si sabe *por qué* hizo ese corte, es señal humana fuerte.
- **Variedad de longitud de frase.** El humano alterna; la IA tiende a la cadencia media uniforme.
- **Incisos, paréntesis o autocorrecciones genuinas.** «(quería decir “casi”, pero era seguro)». Los modelos rara vez se interrumpen así.
- **(Adaptación foro)** Texto fechado **antes del 30-XI-2022** (salida pública de ChatGPT): salvo rarísima excepción, no es IA.

---

## 5. El bucle: borrador → auditoría → versión final

1. **Lee** el texto e identifica cada instancia de los patrones de §3.
2. **Borrador.** Reescribe cubriendo todo lo que cubría el original. Comprueba que se lee bien en voz alta, varía la longitud, prefiere lo concreto y las construcciones simples (ser/tener) y mantiene el registro.
3. **Auditoría — «¿qué sigue delatando a la IA aquí?»** Responde en pocas viñetas con los tells residuales (incluidos los de §7, los estructurales legal-analíticos).
4. **Versión final** que los corrige y **no contiene ningún em dash ni guion largo** (§3.3). Escanéala antes de cerrar.
5. **Auditoría de repetición** (de Persuasive): relee el conjunto; un buen arreglo repetido tres párrafos después se convierte en tic. Vigila la misma muletilla de entrada, la misma estructura retórica cinco veces y la misma palabra «de confianza» usada para sustituir hedgings distintos: varía las sustituciones.

**Entregable del bucle:** borrador + viñetas «sigue-IA» + versión final + (opcional) resumen de cambios.

---

## 6. Calibración de voz con muestras del despacho

Si se aporta una muestra de escritura real del despacho (escrito anterior del letrado, carta modelo), analízala **antes** de reescribir:

1. **Lee la muestra** y anota: patrón de longitud de frase; nivel léxico (¿culto?, ¿directo?); cómo arrancan los párrafos (¿al grano o con contexto?); hábitos de puntuación (¿dos puntos?, ¿incisos?); muletillas o tics recurrentes propios; cómo maneja las transiciones (¿conector explícito o entra sin más?).
2. **Replica esa voz** en la reescritura: no solo quitas el tic de IA, lo sustituyes por el patrón de la muestra. Si el letrado escribe frases cortas, no produzcas largas; si usa «cliente» no lo «mejores» a «mandante» salvo que la muestra lo haga.
3. **Sin muestra,** vuelve al comportamiento por defecto del registro (sobrio y preciso para el foro; claro y elegante para cliente; premium y corporativo para Engel & Völkers — ver §10).

*Cómo aportar la muestra:* en línea («reescribe esto; muestra de mi estilo: […]») o por archivo («usa como referencia mi estilo de [ruta]»).

---

## 7. Parte III de Persuasive, adaptada: tics legal-analíticos (el escrito que habla de sí mismo)

> Reexpresión propia en español; referentes anglosajones convertidos en genéricos del foro. **Defecto común:** el autor se sale del argumento para comentarlo. La cura siempre es la misma: vuelve a entrar y aplica la norma a los hechos.

**7.1 No anuncies la estructura de tu propio argumento.** No: «El argumento se limita en cuatro aspectos. Primero, no romantiza X. Segundo, … Tercero, … Y no trata Y como un estándar.» Es una lista numerada disfrazada de párrafo; nadie habla así. Si hay que enunciar límites, téjelos en el argumento o enúncialos sin el sistema de inventario.

**7.2 No uses meta-comentario para señalizar, anticipar o narrar la estrategia del escrito.** No: «el punto de la continuidad va primero»; «el contraste merece desarrollarse»; «el art. 227 importa de forma complementaria»; «si el escrito se organiza en torno a X…». Todas hablan del escrito en vez de argumentar. Di qué hace el art. 227; no que «importa». Y **el escrito jamás se refiere a sí mismo en tercera persona**.
- *Variante — narrar la arquitectura interna:* «conviene tratar aquí estas alegaciones como mecanismos explicativos que intensifican los tres daños primarios, más que como los ilícitos centrales». Es la IA dándote un organigrama de su propio argumento. Usa los conceptos donde tocan, sin anunciar su rol.
- *Variante — evaluar la propia fuerza:* «el encaje dogmático es más fuerte cuando hay un profesional, una práctica comercial y una decisión transaccional». No puntúes tu encaje; demuéstralo: «La norma se aplica cuando hay A, B y C. Los tres concurren aquí.»

**7.3 No escribas aforismos-axioma que suenan a entrada de manual de lógica.** No: «si la base se romantiza, el argumento que se erige sobre ella cae». Demasiado compacto, demasiado satisfecho de sí. Aterrízalo en los hechos o fúndelo en el argumento. Mejor aún: muestra la distorsión en vez de anunciarla.

**7.4 No uses el andamiaje de negación «Ni… Sí, en cambio…».** No: «Ese informe no prueba que los sistemas desplacen la búsqueda. Tampoco acredita dependencia ni cierre. Sí, en cambio, apoya un punto más estrecho: si…». Aplana la estructura: di qué no muestra y qué sí, sin el pivote triple negación-negación-concesión.

**7.5 No carraspees con pedantería antes de definiciones o reformulaciones.** No: «A los presentes efectos, “conocimiento” no debe tratarse filosóficamente. La formulación más útil es práctica:». Suena a lección y casi a arrogancia. Si necesitas definir un término en sentido práctico, defínelo y ya; o úsalo en contexto y deja que el uso lo defina.

**7.6 El repliegue de «la preocupación más estrecha».** No: «Toda interfaz orienta en algún sentido; eso, por sí solo, no prueba nada. La preocupación más estrecha es la orientación cuya lógica comercial no resulta razonablemente aparente.» Es uno de los movimientos de IA más característicos: enuncias algo amplio y te repliegas a «la preocupación es más estrecha». Suena a que el autor retrocede de su propio punto. Enúncialo directo; si hay que distinguir de un punto más amplio, hazlo con «más bien», «pero» o «lo que importa aquí», no anunciando que estrechas.

**7.7 Calificación valorativa de conceptos antes de engancharlos.** No: «Es una idea diagnóstica útil. Sería una mala regla jurídica si se dejara a ese nivel de generalidad»; «las Notas Explicativas son útiles porque dejan claro que el test es objetivo». Es la IA de profesor, poniendo nota antes de responder. El humano: «Las Notas Explicativas dejan claro que el test es objetivo.» Punto. El «útil» y el «porque» son el razonamiento interno de la IA filtrándose a la página.

**7.8 Atribución vaga a posiciones o fuentes sin nombre.** No: «eso encaja con los sistemas de respuesta más directamente de lo que algunos análisis suponen». ¿Qué análisis? ¿Quién supone? Nombra el análisis del que te distingues o suprime la comparación.

**7.9 Axiomas huecos que suenan autorizados y no dicen nada.** No: «no es una carta de equidad autónoma»; «aunque debe mantenerse en su sitio». Tienen la cadencia de un punto jurídico pero, si intentas extraer una proposición concreta, no hay nada. *Test:* ¿puedes decir en términos llanos qué significa la frase? Si la respuesta es solo «esto no lo hace todo» o «no te apoyes mucho en esto», dilo directo o suprime.

**7.10 Auto-evaluar el «uso correcto» o el alcance del propio argumento.** No: «el uso correcto del art. 229 aquí es modesto. Apoya la proposición de que… No autoriza un estándar errante de virtud informativa.» Varios tics a la vez: evalúa la ambición propia, narra qué hace el artículo en el escrito y suelta un negativo grandilocuente que desmiente algo que nadie defendía. Si el art. 229 apoya un punto, hazlo y cita el artículo.

**7.11 Tono paternalista o disciplinario hacia los conceptos jurídicos.** No: «debe mantenerse en su sitio»; «se gana su sustento, pero solo si se usa con cuidado»; «el uso correcto es modesto». Tratan a la norma como algo que hay que disciplinar. El abogado la aplica o no; si tiene relevancia limitada, dice qué hace y sigue.

**7.12 Etiquetar tus propios recursos retóricos.** No: «esa pregunta no es retórica; es el test que impone el art. 229»; «la analogía es deliberada»; «el punto no es académico». Si haces una pregunta y es el test legal, el lector lo entiende por contexto. No anotes tu propio texto desde fuera.

**7.13 Descargo de tus propias analogías.** No: «la analogía no debe forzarse. Los sistemas de respuesta no son editores de reseñas. Aun así, el régimen de reseñas falsas importa porque muestra que…». La IA acolcha antes y después de cada analogía. Funde la matización en la frase: «Aunque los sistemas de respuesta no son editores de reseñas, el régimen de reseñas falsas es relevante porque muestra que…». Una frase, no tres.

**7.14 Párrafos de «alcance» que solo reconocen límites.** No: «También debe enunciarse con claridad el límite del marco vigente. El Capítulo 1 es más fuerte donde… y más débil donde… Eso no significa que la ley no diga nada; significa que el encaje es más fino, y más vale reconocerlo abiertamente que enterrarlo en cautelas.» El párrafo entero no avanza nada: es la IA *escenificando* honestidad intelectual. Si el encaje es más fino en algún contexto, se verá al aplicar la ley. Suprímelo o redúcelo a una frase en su sitio.

**7.15 El escrito hablando de sí mismo: formato, fecha, título.** No: «la protección de datos es relevante, pero no central, para este escrito»; «para una ponencia de julio de 2026, eso hace el régimen inminente»; «el papel del Derecho de competencia debe mantenerse más estrecho de lo que el título podría tentar a hacerlo». El escrito no se refiere a «este escrito», ni discute qué le es central, ni comenta su propio calendario o su título. Escribe sobre el asunto: si algo no es el foco, dale poco espacio y el lector lo infiere.

**7.16 El «uno» impersonal para describir el estado del Derecho o del argumento.** No: «la consecuencia es que uno ya no puede escribir como si el Derecho de consumo fuera un régimen débil dependiente de los tribunales». Di qué hace ahora el Derecho: «Desde abril de 2025, el Derecho de consumo dispone de herramientas de ejecución más amplias». Enuncia el cambio directo; no lo describas como un cambio en lo que «uno» puede escribir.

**7.17 Otros patrones a vigilar.** Marco condicional formulario («si X, entonces se sigue Y» como axioma suelto); pares de negación simétrica repetidos a lo largo del texto («no es A, es B» en un párrafo; «la cuestión no es C, es D» tres después); listas de límites demasiado pulcras («este argumento no afirma X, no sugiere Y, no asume Z»: pregúntate si de verdad necesitas desmentir todo eso).

**7.18 Frases-delatoras (equivalentes españoles).** «en lo que sigue»; «la formulación más útil es…»; «a los presentes efectos»; «conviene observar que» (solo observa la cosa); «para ser claros» (si lo necesitas, la frase anterior no era clara: arréglala); «no es que… sino que» como muletilla defensiva; «el contraste merece desarrollarse» (desarróllalo); «X importa de forma complementaria» (di qué hace X); «conviene tratarlas aquí como…» (narras tu edición); «el encaje dogmático es más fuerte cuando…» (evalúas en vez de demostrar); «encaja más de lo que algunos suponen» (atribución vaga); «no es una X autónoma» (axioma hueco); «debe mantenerse en su sitio» (paternalista); «el uso correcto de X aquí es modesto» (auto-evaluación); «no autoriza un estándar errante de…» (negativo grandilocuente); «X es útil porque…» (razonamiento interno filtrado); «esa pregunta no es retórica» (etiqueta su recurso); «la analogía no debe forzarse» (descargo de analogía); «X es relevante, pero no central, para este escrito» (el escrito se acota); «para una ponencia de [fecha]…» (se sitúa en el tiempo); «la cuestión decisiva es funcional» (etiqueta axiomática: pregunta o afirma).

*Principio único de §7:* si una frase o un párrafo habla del escrito en vez de hablar del asunto, córtalo.

---

## 8. Antes / después en registro jurídico (ejemplos propios)

**A. Inflación de trascendencia + copula artificial (fundamento de derecho)**
- *Antes:* «La cláusula penal litigiosa se erige como pieza que se inscribe en el marco más amplio del auge de los mecanismos incentivadores en la contratación contemporánea, reviste un carácter esencial y testimonia una voluntad de seguridad jurídica creciente.»
- *Después:* «La cláusula penal fija a tanto alzado los daños por incumplimiento. Su importe es aquí manifiestamente desproporcionado respecto del perjuicio, lo que justifica la moderación del art. 1154 CC.»

**B. Atribución vaga → fuente precisa (fundamento de derecho)**
- *Antes:* «La doctrina mayoritaria coincide en reconocer que la responsabilidad contractual no puede comprometerse sin un nexo causal adecuado entre el incumplimiento y el perjuicio.»
- *Después:* «El nexo causal debe ser directo y certero (Díez-Picazo, *Fundamentos*, t. II). Aquí falta: el perjuicio invocado deriva de un hecho posterior al incumplimiento.»

**C. Chevilles + «dicho» + pasiva (contestación)**
- *Antes:* «Conviene a este respecto recordar que, en todo caso, fue sostenido por la actora que dicho contrato había sido concluido bajo el imperio de un dolo, cuyos elementos habrían sido reunidos por las maniobras imputadas a esta parte.»
- *Después:* «La actora sostiene que mi mandante obtuvo su consentimiento por dolo. Lo funda en las declaraciones de la nota informativa de 12 de marzo de 2022.»

**D. Conclusión genérica → posición tajante (consulta a cliente)**
- *Antes:* «En conclusión, la situación jurídica de su cliente es compleja y requiere un análisis pormenorizado. Existen argumentos en ambos sentidos. Habrá que ponderar todas las circunstancias para adoptar la estrategia más adecuada.»
- *Después:* «La acción de nulidad tiene menos del 40 % de éxito. La vía más sólida es la resolución por incumplimiento (art. 1124 CC), siempre que acreditemos el requerimiento desatendido. Recomiendo actuar antes del 15 de septiembre para no incurrir en prescripción.»

**E. Fórmulas de cortesía IA apiladas (correo a cliente)**
- *Antes:* «Espero que el presente mensaje le encuentre en perfecto estado. A raíz de nuestra conversación telefónica del día de hoy, me permito dirigirme a usted con el fin de confirmarle nuestra posición. No dude en contactarme para cualquier aclaración. Quedo a su entera disposición.»
- *Después:* «Como hablamos esta mañana, le confirmo nuestra posición. Si tiene dudas, llámeme directamente.»

**F. Párrafo de «alcance» y auto-evaluación (escrito procesal)**
- *Antes:* «También debe enunciarse con claridad el límite del marco aplicable. El art. 1124 CC es más fuerte cuando el incumplimiento es resolutorio y más débil cuando es parcial; ello no significa que la norma no diga nada, sino que su encaje es más fino, y más vale reconocerlo que sepultarlo en cautelas.»
- *Después:* «El incumplimiento es resolutorio: afecta a la obligación principal (entrega del inmueble) y frustra el fin del contrato. Concurre, pues, el supuesto del art. 1124 CC.»

---

## 9. Qué NO trasladar al foro / No aplica al castellano (mecánica solo inglesa)

**No aplica al castellano (equivalente español indicado para auditar la cobertura):**
- **Title case en encabezados** (blader §17). Mecánica del inglés. *Equivalente español:* el vicio paralelo es **capitalizar inicial de cada palabra del epígrafe** o abusar de mayúsculas; en español, mayúscula solo en la primera palabra y nombres propios.
- **Comillas curvas vs. rectas** (blader §19). Mecánica de teclado anglosajón. *Equivalente español:* usar la **comilla latina/angular «»** como primer nivel (y "" como segundo), no la inglesa "" por defecto; no es delator de IA, sino norma tipográfica del foro.
- **Pares con guion sobre-hifenados** (blader §26: «third-party», «data-driven», «high-quality» en posición predicativa). Fenómeno del inglés. *Equivalente español:* prácticamente inexistente; el castellano no encadena adjetivos con guion. Se recoge solo para auditar; sin acción en el foro.

**Qué NO trasladar (de blader, por chocar con el registro):**
- **Inyectar opinión, primera persona, humor o «dejar entrar el desorden»** (sección «Personality and Soul» de blader) en escrito procesal, contrato o nota técnica: ahí lo neutro y llano *es* la voz humana. Solo aplica a carta, opinión o comunicación con voz propia. [Coincide con «qué no trasladar» de claridad: el gusto por la prosa de autor]
- **Coloquialismos, emoticonos, signos múltiples, puntos suspensivos** (blader tolera lo casual entre iguales): nunca en foro ni ante marca premium. [YA EN CLARIDAD §6]
- **Los ejemplos de las fuentes** (periodísticos/anglosajones de blader; franceses de LawyerScrib; Kagan/Boies&Olson de Persuasive): no reproducirlos; generar siempre ejemplos jurídicos españoles propios.

**Del propio foro (recordatorio de claridad, se conserva):** la pasiva refleja («se declaró probado», «se acordó») es legítima y a veces preferible cuando el agente es el tribunal o es irrelevante; la frase larga bien construida, con un solo giro anunciado, es legítima para encadenar un razonamiento o un *petitum* complejo. El vicio no es la longitud, sino la subordinación que se atasca.

---

## 10. Calibración por registro

| Registro | Intensidad de poda anti-IA | Qué se conserva / cuidado especial |
|---|---|---|
| **Escrito procesal civil** | Alta sobre relleno, chevilles, meta-comentario (§7), negrita decorativa, em dash, tríadas y adjetivación; **moderada** en lo demás. | Precisión terminológica, citas normativas y jurisprudenciales íntegras, estructura y párrafos numerados, criterios Sala 1ª TS (Times New Roman 12, justificado, 25 págs.). Sin alma literaria. |
| **Requerimiento extrajudicial** | Alta. Firme y directo. | Obligación, importe, plazo y consecuencia inequívocos. Cero floritura. |
| **Carta a cliente particular (ruso/ex-URSS y alto poder adquisitivo)** | Máxima. Claridad y elegancia; cero artefacto de chatbot y cortesía apilada. | Precisión de lo que se compromete y los plazos; trato cortés. **Idioma: ruso por defecto** salvo indicación contraria. Aquí sí cabe primera persona y calidez (alma del registro carta). |
| **Comunicación corporativa Engel & Völkers** | Máxima en tics y pose; tono especialmente cuidado. | Registro premium, sobrio y corporativo; nombre de marca; cortesía formal sin grandilocuencia ni perífrasis. |
| **Memo / nota interna** | Alta. Telegráfico y concreto. | Conclusión por delante; datos y referencias verificables; posición tajante. |

---

## 11. Verificación de cobertura — tabla de trazabilidad

> Cada ítem de origen → dónde quedó. Único motivo admisible de no-traslado: mecánica exclusiva del inglés sin equivalente (marcada «solo-inglés», y aun así recogida en §9 para auditoría).

### 11.1 blader/humanizer

| Ítem de origen | Destino |
|---|---|
| Voice Calibration (opcional) | §6 |
| Personality and Soul (alma; solo donde el registro la pide; señales de texto sin alma; cómo dar voz) | §1.9 + §9 (qué no trasladar) + §10 (carta) |
| §1 Inflación de significado/legado/tendencias | §3.1 |
| §2 Notoriedad y cobertura mediática | §3.1 |
| §3 Análisis superficial con gerundios | §3.1 |
| §4 Lenguaje promocional | §3.1 |
| §5 Atribuciones vagas / weasel words | §3.1 + §2 (regla 2) |
| §6 Sección «Retos y perspectivas» | §3.1 |
| §7 Vocabulario IA | §3.2 |
| §8 Evitación de «is/are» (copula) | §3.2 |
| §9 Paralelismos negativos y negación de cola | §3.2 |
| §10 Regla de tres | §3.2 |
| §11 Variación elegante (sinónimos) | §3.2 |
| §12 Falsos rangos | §3.2 |
| §13 Pasiva y fragmentos sin sujeto | §3.2 |
| §14 Em dash / en dash | §3.3 + §2 (regla 10) + §5 (escaneo final) |
| §15 Abuso de negrita | §3.3 |
| §16 Listas verticales con encabezado en negrita | §3.3 |
| §17 Title case en encabezados | §9 (solo-inglés; equivalente español dado) |
| §18 Emojis | §3.3 |
| §19 Comillas curvas | §9 (solo-inglés; equivalente: comilla latina) |
| §20 Artefactos de comunicación colaborativa | §3.4 |
| §21 Disclaimers de corte + relleno especulativo | §3.4 |
| §22 Tono sicofántico/servil | §3.4 |
| §23 Frases-relleno | §3.5 |
| §24 Hedging excesivo | §3.5 |
| §25 Conclusiones positivas genéricas | §3.5 |
| §26 Pares con guion sobre-hifenados | §9 (solo-inglés) |
| §27 Tropos de autoridad persuasiva | §3.5 |
| §28 Señalización y anuncios | §3.5 |
| §29 Encabezados fragmentados | §3.5 |
| §30 Escritura anclada al diff | §3.5 |
| §31 Remates fabricados / staccato | §3.5 |
| §32 Fórmulas-aforismo | §3.5 |
| §33 Aperturas retóricas conversacionales | §3.5 |
| Detection: qué NO marcar (falsos positivos) | §4.1 |
| Detection: señales de escritura humana | §4.2 |
| Process and Output (bucle + entregable) | §5 |
| Full Example | §8 (ejemplos propios equivalentes) |
| Reference / key insight | Cabecera (idea-fuerza) |

### 11.2 LawyerScrib (17 + marco)

| Ítem de origen | Destino |
|---|---|
| Personnalité et substance (tomar posición, variar ritmo, nombrar, complejidad, presente activo) | §1.4–1.7 |
| §1 Inflación de portée | §3.1 (fusión con blader §1) |
| §2 Atribuciones vagas a doctrina/jurisprudencia | §3.1 (fusión con blader §5) + §2 (regla 2) |
| §3 Chevilles rhétoriques / fórmulas creuses | §3.5 |
| §4 Évitement du verbe «être» | §3.2 (fusión con blader §8) |
| §5 Passivation excessive | §3.2 (fusión con blader §13) |
| §6 Nominalisation abusive | §3.2 |
| §7 Règle des trois / listes | §3.2 (fusión con blader §10) |
| §8 Sections «Enjeux et perspectives» | §3.1 (fusión con blader §6) |
| §9 Vocabulaire IA juridique | §3.2 (fusión con blader §7) |
| §10 Fórmulas de cortesía IA en correos | §3.4 |
| §11 Conclusión genérica sin posición | §3.4 |
| §12 «Ledit/susmentionné/supra» abusivos | §3.2 |
| §13 Parallélismes négatifs | §3.2 (fusión con blader §9) |
| §14 Tiret long abusivo | §3.3 (fusión con blader §14) |
| §15 Gras mécanique | §3.3 (fusión con blader §15) |
| §16 Hedging excesivo | §3.5 (fusión con blader §24) |
| §17 Ouvertures sycophantiques | §3.4 (fusión con blader §22) |
| Processus / Format de sortie | §5 |
| Exemple complet | §8 (ejemplos propios) |
| Reference / key insight (forma sin sustancia) | Cabecera (idea-fuerza) |

### 11.3 Persuasive Legal Writing, Parte III

| Ítem de origen | Destino |
|---|---|
| Defecto común (salirse del argumento) | §1.3 + §7 (encabezado y principio único) |
| No anunciar la estructura del propio argumento | §7.1 |
| Meta-comentario que señaliza/narra la estrategia (+ tercera persona, + arquitectura interna, + evaluar fuerza) | §7.2 |
| Aforismos-axioma tipo manual de lógica | §7.3 |
| Andamiaje «Nor… It does, however…» | §7.4 |
| Carraspeo pedante antes de definiciones | §7.5 |
| Repliegue «the narrower concern» | §7.6 |
| Grading evaluativo de conceptos | §7.7 |
| Atribución vaga a posiciones/fuentes sin nombre | §7.8 |
| Axiomas huecos | §7.9 |
| Auto-evaluación del «uso correcto»/alcance | §7.10 |
| Tono paternalista/disciplinario hacia conceptos | §7.11 |
| Etiquetar los propios recursos retóricos | §7.12 |
| Descargo de las propias analogías | §7.13 |
| Párrafos de «scope» que solo reconocen límites | §7.14 |
| El escrito hablando de sí mismo (formato/fecha/título) | §7.15 |
| El «uno» impersonal | §7.16 |
| Otros patrones (condicional formulario, negación simétrica, listas de límites) | §7.17 |
| Lista de tell-tale phrases (equivalentes españoles) | §7.18 |
| Repetition audit | §5 (paso 5) |

**Recuento:** blader 40/40 (33 patrones + 7 secciones: calibración de voz, alma, falsos positivos, señales humanas, bucle, ejemplo completo, referencia) · LawyerScrib 21/21 (17 patrones + 4 secciones) · Persuasive III 20/20 → **81 de 81 ítems trasladados; 0 perdidos** (3 ítems solo-inglés —title case, comillas curvas, pares con guion— recogidos en §9 con su equivalente español, conforme al único motivo admisible).
