# Contrato de estilo de la casa — Tyukhay Legal

> **Fuente de verdad única del estilo del despacho.** Una fuente, muchos
> consumidores (mismo patrón que `indice_documental.yaml` o
> `verificacion-anclada-fuente`). Lo citan las skills productoras de texto **al
> redactar** (capa 1); la skill `pase-de-estilo` lo aplica **al revisar** (capa 2).
> Versión instrucción para modelo: imperativa, accionable, sin teoría. El detalle
> exhaustivo vive en los inventarios de `.claude/skills/pase-de-estilo/references/`
> (`claridad_es.md`, `tics_ia_es.md`, `persuasion_es.md`); este contrato es el
> resumen operativo con el que el borrador **nace** en estilo de la casa.

## Cómo se usa

- **Al redactar (toda skill productora):** antes de generar el texto, aplica este
  contrato. El borrador debe nacer claro, persuasivo y sin marcas de IA, no
  arreglarse después.
- **Al revisar:** `pase-de-estilo` revisa el borrador contra este contrato y sus
  inventarios, y entrega versión final + tabla de cambios + traza.

## Regla de oro — claridad ⟂ precisión jurídica

**Ante conflicto, gana la precisión técnica.** La claridad se busca en la
**sintaxis y la estructura**, nunca rebajando el término jurídico correcto. No
sustituyas «dolo», «saneamiento», «litisconsorcio» ni una cita literal por un
sinónimo «más claro». Primero el fondo y las citas verificadas; el estilo, dentro
de ellos.

## El estilo opera DENTRO del formato, no lo sustituye

- Formato Sala 1ª TS intacto (Times New Roman 12, citas 10 pt, márgenes 2,5 cm,
  interlineado 1,5, párrafos numerados, jerarquía 1./1.1./1.1.1., ≤25 págs.).
- Estructura procesal y orden de los escritos: intocables.
- `verificacion-anclada-fuente` corre antes o en paralelo. El estilo **no altera
  cifras, fechas, nombres ni citas literales ya verificadas**. Cita vaga o sin
  anclar: **márcala y remite a `verificacion-anclada-fuente`; nunca la inventes**.

---

## 1. Claridad (que se entienda a la primera)

1. **El lector manda.** El esfuerzo de comprensión lo asume quien escribe. Si no
   se entiende, la culpa es del autor, no del juez.
2. **La cabeza, ordenada antes de teclear.** Fija qué se pide y en qué orden
   lógico se llega. Lo importante primero.
3. **Economía.** Ante la duda, borra. Adjetivos en cuentagotas (deja que el hecho
   califique). Fuera los adverbios de cantidad (*muy, bastante*) y los `-mente` en
   serie. Palabra corta sobre larga, salvo que la larga sea más **precisa**.
   *implementar*→aplicar; *se erige como*→es; *en las inmediaciones de*→cerca de.
4. **Frase.** Media en torno a ≤20 palabras, **alternando** cortas y alguna larga.
   Si una frase se vuelve incomprensible por su extensión, **vuelve a empezar**, no
   la parchees. Una frase larga legítima lleva **un solo giro anunciado**
   («por el contrario», «de ahí que»).
5. **Voz activa y afirmativa por defecto.** «El arrendatario incumplió», no «el
   contrato fue incumplido». Reserva la pasiva (y la pasiva refleja: «se declaró
   probado») para cuando el agente sea irrelevante, desconocido o sea el tribunal.
6. **Párrafo = una idea.** Un fundamento, una cuestión.
7. **Concreción.** Nada de comodines («capacidades», «realidad», «en el marco
   de»). En Derecho lo concreto además prueba: «el 3 de abril no se entregó la
   llave pactada (cláusula 4ª)», no «se vulneraron sus derechos».
8. **Sin pose.** No tantees con introducciones de relleno; entra en materia. No
   exhibas vocabulario ni latín decorativo. Sin hedging ni autobombo: afirma o no
   afirmes.

## 2. Persuasión (que el lector llegue a tu conclusión)

1. **Enmarcar, no resumir.** El primer párrafo encuadra, no resume. Escríbelo **el
   último**, ya conocido tu mejor argumento.
   - *Apertura silogística* (informes, dictámenes, demanda): cuestión + posición
     contraria + principio que la derriba, en dos o tres frases.
   - *Apertura binaria* (alegato, requerimiento, correspondencia): obliga a elegir
     entre dos caracterizaciones; hornea la asimetría en el marco.
   - Evita abrir por los antecedentes procesales o con «El presente escrito versa
     sobre…».
2. **Ordenar por fuerza persuasiva, no por el articulado de la ley.** El argumento
   más potente primero, desarrollado hasta que parezca dispositivo. El segundo,
   como **confirmación independiente** («aun si no convenciera lo anterior, esto
   basta»).
3. **Cerrar la fundamentación con una consecuencia** concreta y verosímil de darle
   la razón al contrario; no con un suplico. La consecuencia es jurídica, no
   dramatismo.
4. **Lo abstracto no persuade.** Ancla cada principio en un ejemplo: hipótesis
   narrativa, analogía de intuición reclutada, o desfile de horrores (tres casos,
   en paralelo, cada uno más incómodo).
5. **Paralelismo y antítesis.** Da la misma forma gramatical a los fundamentos en
   serie; muestra el doble rasero con estructura paralela, no diciéndolo.
6. **Citar con bisturí.** Funde dos o tres palabras clave de la cita en tu propia
   frase sobre tu caso; reserva la cita en bloque para lo demoledor. Devuelve al
   adversario su propio término cuando lo delata.
7. **Sonar a persona, no a institución.** Pregunta y responde; pivota de la lógica
   a las consecuencias. Humano dentro de la formalidad (dosificado en el escrito
   procesal; pleno en alegato y carta).
8. **Cerrar con una idea-fuerza,** la frase con la que el juez resumirá tu
   posición, antes del suplico ritual.

## 3. No-IA (que no parezca generado por una máquina)

**Idea-fuerza:** un LLM reproduce los *tics de forma* sin la *sustancia*.
Reescribir es devolver posición, ritmo y concreción.

1. **Quédate DENTRO del argumento.** No anuncies tu estructura, no narres tu
   estrategia, no etiquetes tu método, no evalúes tu propia fuerza. El escrito
   **jamás se refiere a sí mismo**. Aplica la norma a los hechos en su sitio. (El
   defecto nº 1 de la IA legal-analítica; catálogo completo en `tics_ia_es.md §7`.)
2. **Toma posición.** «El argumento de contrario es inoperante», no «cabe sostener
   que esa tesis presenta ciertos límites».
3. **Nombra las cosas.** «La STS 333/2021, de 12 de mayo», no «la resolución
   precitada». Fuente precisa, no «la doctrina» / «la jurisprudencia» en abstracto.
4. **Recupera el verbo «ser» y el verbo directo.** «Es esencial», no «reviste un
   carácter esencial».
5. **Varía el ritmo.** La cadencia uniforme de longitud media es el delator más
   fiable.
6. **Rompe la tríada.** No fuerces grupos de tres cuando dos bastan. Mata el
   paralelismo negativo en serie («no solo X, sino Y» repetido).
7. **Fuera el relleno y el énfasis hueco.** «Conviene señalar», «en este sentido»,
   «sin lugar a dudas», «es incuestionable»: suprime y deja hablar al hecho y la
   norma.
8. **Sin em dash (—) ni guion largo al modo anglosajón.** Reescribe con punto,
   coma, dos puntos o paréntesis. **Escaneo final: cero rayas.**
9. **Sin negrita decorativa** sobre términos jurídicos ni listas con encabezado en
   negrita + dos puntos. Sin emojis. Sin cortesía apilada ni apertura servil en
   correos.
10. **Conclusión con posición tajante,** no «la situación es compleja y requiere un
    análisis pormenorizado».

### Guardarraíles — no sobre-corregir

- **Busca racimos de tics, no tics aislados.** Un em dash suelto, un conector
  común o un cultismo *técnico* no delatan nada. Em dash + regla de tres +
  vocabulario-marca + sección «Conclusión» sí.
- **Preserva las señales humanas:** el detalle específico y raro, la tensión sin
  resolver, el inciso genuino, la variación de longitud de frase. Sobre-editar las
  destruye.
- **Reescribe, no amputes.** Cubre todo lo que cubría el original: si tenía cinco
  párrafos, la versión final tiene cinco. La limpieza anti-IA no puede vaciar el
  argumento.
- **No achates cultismo legítimo.** La IA abusa de palabras *concretas* (ver
  lista en `tics_ia_es.md §3.2`), no de todo término culto.

## 4. Proceso (la claridad nace en la reescritura)

1. **Tres relecturas con foco distinto:** (1) ¿se sostiene el argumento y el
   orden?; (2) expresión —palabras que sobran, frases largas, muletillas—;
   (3) pulir lo retocado.
2. **Lee en voz alta.** Lo que no dirías hablando, no lo escribas.
3. **Pasada final anti-IA:** pregúntate «¿qué sigue delatando a la IA aquí?»,
   responde en pocas viñetas y corrige. Escanea: ningún em dash.
4. **Auditoría de repetición:** un buen arreglo repetido tres párrafos después se
   vuelve tic. Varía las sustituciones; no abuses de la misma estructura retórica.
5. **Ponte un plazo.** La autocrítica infinita no mejora el escrito más allá de un
   punto; cierra y entrega.

---

## 5. Calibración por registro

| Registro | Poda (tics, pose, relleno) | Qué se conserva siempre |
|---|---|---|
| **Escrito procesal civil** | Alta sobre relleno, meta-comentario, em dash, tríadas, adjetivación; moderada en lo demás. | Precisión terminológica, citas íntegras, estructura y párrafos numerados, criterios Sala 1ª TS. Interpelación dosificada; sin voz literaria. |
| **Requerimiento extrajudicial** | Alta. Firme y directo. Apertura binaria + consecuencia. | Obligación, importe, plazo y consecuencia inequívocos. Cero floritura. |
| **Alegato / informe oral** | Persuasión máxima: hipótesis narrativa, diálogo, antítesis. | Precisión; la escena al servicio del Derecho, no del efecto. |
| **Carta a cliente particular (ruso/ex-URSS, alto poder adquisitivo)** | Máxima. Claridad y elegancia; cero artefacto de chatbot y cortesía apilada. | Lo que se compromete y los plazos; trato cortés; cabe primera persona y calidez. **Idioma: ruso por defecto** salvo indicación contraria. |
| **Comunicación corporativa Engel & Völkers** | Máxima en tics y pose; tono especialmente cuidado. | Registro premium, sobrio, corporativo; nombre de marca; cortesía formal sin grandilocuencia ni perífrasis. |
| **Memo / nota interna** | Alta. Telegráfico y concreto. | Conclusión por delante; datos y referencias verificables; posición tajante. |

## 6. Voz del despacho

Cuando exista corpus, calíbrala con las muestras reales anotadas en
`.claude/skills/pase-de-estilo/references/registros.md` (analiza longitud de
frase, nivel léxico, arranque de párrafo, puntuación y muletillas propias, y
**replica** ese patrón al reescribir). Sin corpus, usa el comportamiento por
defecto de cada registro (tabla §5). **No inventes la voz**: a falta de muestra,
sé sobrio y preciso.
