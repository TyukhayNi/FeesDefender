# Stress-test — F4.D2: Orden parcial y comparación de intervalos temporales

> **Para:** revisor adversarial (Perplexity).
> **Formato:** handoff anonimizado. No hay datos reales de cliente; actores y cifras son genéricos.
> **Qué pido:** romper la decisión candidata con casos límite, contrastarla con los marcos de referencia citados, y señalar dónde introduce error, sesgo o falsa precisión. Busco fallos, no confirmación.

---

## 1. Contexto mínimo del sistema

Diseño una **cronología unificada de prueba**: fusiona en una sola línea de tiempo todas las fuentes de prueba de un expediente litigioso (correo, mensajería, registros de CRM, entrevistas grabadas/transcritas, documentos, asientos registrales). Es trabajo jurídico-forense: separa **lo que consta en la prueba** de **lo que se infiere**.

Piezas ya cerradas y **congeladas** (se respetan como invariantes, no se discuten):

- **Modelo B:** el átomo de la línea es un **acto datado anclado a un registro de fuente**, nunca un hecho del mundo inferido (eso vive en una capa derivada con semáforo 🟢🟡🔴).
- **Tiempo del acto (campos ya fijados):** `cuando.fecha` en **EDTF / ISO 8601-2** (precisa, aproximada `~`, incierta `?`, intervalos, dígitos `XX`); `cuando.fecha_fin` (durativos); `cuando.orden_relativo` (secuencia dentro de la fuente); `fecha_documento`; `modo_recuperacion`.
- **F4.D1 (decisión inmediatamente anterior, ya cerrada — Los tres tiempos):** un solo tiempo ancla la línea = **tiempo del hecho**. El tiempo de **enunciación** coincide con él salvo en declaraciones (donde el acto es la enunciación y el hecho narrado va por evento reconstruido provisional o por enlace de testimonio). El tiempo de **registro** (timestamp de log, fecha de extracción/soporte) **nunca es posición en la línea**: es procedencia; cuando es el único acotador de un hecho difuso, actúa como **techo** del intervalo.
- **Regla de no inflar fichas:** se prefieren reglas/derivados sobre campos manuales nuevos. Un valor calculado (no manual) sí es admisible.
- **Disciplina anti–sesgo de confirmación:** decisiones previas obligan al sistema a sacar también lo que rompe la tesis del litigante; no debe fabricar certeza donde la prueba no la da.

---

## 2. El problema de F4.D2

Las fechas llegan con precisión muy desigual (instante exacto en correo/mensajería; "en torno a la primavera" en una declaración; "antes de la firma" sin fecha; intervalos durativos). Falta el **operador que las compara y las ordena** en una sola línea, y decidir **qué naturaleza** tiene esa línea (¿secuencia única forzada, o estructura que admite pares sin orden?). Aguas abajo lo consumen el cálculo de **prescripción** y una **señal de proximidad temporal** del módulo de correlación.

---

## 3. DECISIÓN CANDIDATA a romper

**La cronología es un ORDEN PARCIAL, no total.**

1. **Proyección a intervalo.** Cada acto se proyecta mecánicamente a `[suelo, techo]` derivado de su EDTF:
   - instante preciso → intervalo degenerado (`suelo = techo`);
   - "~marzo 2024" → `[2024-03-01, 2024-03-31]`;
   - "antes de la firma (fecha F)" → `[−∞, F]`; "después de F" → `[F, +∞]`.
   `suelo`/`techo` son **derivados calculados**, no casillas manuales.

2. **Relación de orden — álgebra de Allen reducida a tres salidas operativas:**
   - **antes/después determinado** ⟺ `techo(A) < suelo(B)` (o viceversa) → se ordena automáticamente;
   - **solapamiento → `orden_indeterminado`**: el sistema **no elige**; marca el par como no ordenable y lo deja visible como tal;
   - (caso degenerado de igualdad/contención se trata como solapamiento → indeterminado).

3. **`orden_relativo` rompe empates SOLO intra-fuente.** Si A y B vienen de **la misma fuente** y esta da secuencia directa (mensajes consecutivos, turnos de una transcripción, asientos numerados), el `orden_relativo` **prevalece aunque los intervalos solapen** (hay evidencia directa de secuencia). **Entre fuentes distintas, `orden_relativo` no cruza**: solo deciden suelo/techo; si solapan, `orden_indeterminado`.

4. **Consumidores:**
   - **Prescripción:** usa suelo/techo; el *dies a quo* se toma del extremo que corresponda según la carga, con explicación expresa (no oculta en script).
   - **Señal de proximidad temporal (S4):** distancia = separación entre intervalos (solapados → distancia 0); S4 nunca empareja sola (ya cerrado), sobre todo descarta.
   - **Render humano:** los pares `orden_indeterminado` se muestran como un **haz** simultáneo, no como secuencia.

---

## 4. Invariantes que la solución NO puede violar

- (I1) Modelo B: no colar inferencia en la capa canónica.
- (I2) No inflar fichas: campos nuevos solo si imprescindibles; preferir derivados calculados.
- (I5) El tiempo de registro no contamina la ordenación material de los hechos.
- (I-orden) El sistema no fabrica orden donde la prueba no lo fija (anti–sesgo de confirmación): preferible `orden_indeterminado` honesto a una secuencia falsa.
- (I-traza) Toda relación de orden debe ser explicable y anclada a la fuente.

---

## 5. Marcos de referencia que pido contrastar explícitamente

1. **Álgebra de intervalos de Allen (13 relaciones) y su versión sobre intervalos imprecisos / borrosos.** Mi reducción a {antes, después, indeterminado} colapsa 13 relaciones en 3. **Pregunta dura:** ¿pierdo relaciones que importan jurídicamente — *meets* (un acto justo al terminar otro), *during* (un acto contenido en un periodo: "durante la negociación"), *overlaps*, *starts/finishes*? ¿Hay consultas (causalidad, simultaneidad, contención en un periodo) que mi colapso a "indeterminado" vuelve imposibles o engañosas?

2. **Razonamiento temporal cualitativo con incertidumbre** (point algebra, redes de restricciones temporales, fuzzy/probabilistic Allen). ¿Tratar todo solapamiento como "indeterminado" binario tira información de **grado** de solapamiento que un modelo de restricciones propagaría (p. ej. deducir un orden por transitividad A<B, B<C ⟹ A<C aunque A y C solapen aparentemente)? ¿Debería propagar restricciones transitivas antes de declarar indeterminado?

3. **EDTF / ISO 8601-2 → suelo/techo.** ¿La derivación mecánica de `[suelo, techo]` cubre todos los casos (estaciones, décadas, fechas con `?`/`~`/`%`, conjuntos `[..]`/`{..}`, intervalos abiertos)? ¿Dónde produce un suelo/techo incorrecto o demasiado laxo?

4. **Tiempo abierto `[−∞, F]` / `[F, +∞]`.** Las cotas abiertas ("antes de la firma") son frecuentes en prueba. ¿Mi aritmética de orden las maneja sin patologías (dos eventos ambos `[−∞, F]`, comparación de infinitos, ordenación estable en el render)?

5. **`orden_relativo` intra-fuente vs fecha absoluta — conflicto.** ¿Qué pasa si dentro de **una misma fuente** el `orden_relativo` dice A→B pero las **fechas absolutas** de esa fuente dicen techo(A) > suelo(B) (reloj saltado, mensaje editado, reordenación de export)? Mi regla da prioridad al orden relativo intra-fuente. **¿Es correcto, o debería detectar y señalar la contradicción** en lugar de elegir?

6. **Derecho — prescripción y secuencia indiciaria (España).** (a) *Dies a quo* (arts. 1969 y 1964 CC): para que el cómputo sea **defendible y no autolesivo**, ¿basta "tomar el extremo según la carga", o hay un criterio jurídico sobre qué extremo del intervalo usar (el más favorable a quien alega prescripción vs a quien la combate)? (b) Prueba por presunciones (art. 386 LEC) y secuencias indiciarias: ¿el estado `orden_indeterminado` debe **bloquear** un enlace indiciario que dependa del orden, o degradarlo? ¿Qué umbral de orden exige una inferencia "precisa y directa"?

---

## 6. Casos límite diseñados para romper la candidata

- **C1 — "Durante la negociación".** Un acto cuya fecha es "en algún momento durante la negociación" (intervalo amplio) y varios actos precisos dentro de ese intervalo. Mi modelo diría "indeterminado" frente a cada uno; pero jurídicamente el acto **contiene** a los otros (*during*). ¿Pierdo la relación de contención, que puede ser justo la relevante?

- **C2 — Transitividad rescatable.** A `[ene, mar]`, B preciso `15-feb`, C `[abr, may]`. A vs C: techo(A)=mar < suelo(C)=abr → A antes de C (determinado). Pero A vs B y B vs C solapan/limitan. ¿El sistema deduce correctamente A<C por las cotas, o se pierde en "indeterminado" por no propagar? ¿Y si solo la transitividad (A<B<C) permite ordenar A y C que individualmente solapan?

- **C3 — Cota abierta doble.** Dos actos ambos "antes de la firma" (`[−∞, F]`). Solapan totalmente → indeterminado. Correcto, pero ¿el render y el módulo de prescripción se comportan bien con `−∞`? ¿Y si uno es "bastante antes" (declaración) y otro "justo antes" (documento)? ¿Tiro información recuperable?

- **C4 — Orden relativo intra-fuente que contradice las fechas.** Export de mensajería reordenado o con timestamps inconsistentes: orden_relativo dice A→B, fechas dicen lo contrario. Mi regla elige orden_relativo. ¿Debería en cambio levantar bandera de inconsistencia de fuente?

- **C5 — Acto durativo con un extremo preciso y otro difuso (heredado de C7 de F4.D1).** Negociación que empieza fecha exacta y "termina en algún momento de la primavera". `[F_inicio_preciso, techo_difuso]`. ¿Cómo se compara con un acto puntual que cae en la zona difusa del final? ¿`fecha_fin` entra en la aritmética de suelo/techo o se trata aparte?

- **C6 — Timecode SMPTE relativo.** Entrevista grabada: los fragmentos llevan timecode HH:MM:SS:FF relativo al inicio, no reloj de pared. La entrevista es **un** acto con fecha (la del día). ¿El orden **interno** entre fragmentos (quién dijo qué antes dentro de la sesión) se modela como `orden_relativo` intra-fuente, dejando el acto-entrevista como un punto único en la línea global? ¿O hay un riesgo en no situar cada fragmento en la línea global?

- **C7 — Falsa simultaneidad por imprecisión.** Dos actos de fuentes distintas, ambos "marzo 2024", que en realidad ocurrieron en días distintos y su orden es el hecho controvertido. Mi modelo: indeterminado (correcto, anti-sesgo). Pero, ¿y si existe una tercera prueba precisa que **acota** uno de ellos al 5-mar y el otro queda "marzo"? ¿El sistema reestrecha el intervalo del primero al integrar esa prueba (propagación de restricciones), o se queda con el EDTF original?

- **C8 — Zona horaria + medianoche.** Dos mensajes a ambos lados de medianoche en husos distintos: tras normalizar a UTC cambian de día/orden. ¿La comparación de orden opera sobre instantes normalizados a UTC con offset guardado, y el render muestra la hora local? ¿Riesgo de ordenar mal por no normalizar?

---

## 7. Preguntas concretas al revisor

1. ¿Colapsar las 13 relaciones de Allen a {antes, después, indeterminado} es una simplificación **segura** para uso forense, o debo conservar al menos *during/contains* (contención en periodo) y *meets* (contigüidad)? Da el caso donde el colapso engaña.
2. ¿Debo **propagar restricciones transitivas** (estrechar intervalos y deducir órdenes) antes de declarar `orden_indeterminado`, o eso es sobreingeniería que introduce más riesgo del que evita?
3. Ante conflicto **orden_relativo intra-fuente vs fechas absolutas de la misma fuente**: ¿prioridad al orden relativo (mi candidata) o **señalar inconsistencia**? ¿Regla mínima?
4. Prescripción: ¿hay un criterio jurídico claro sobre **qué extremo** del intervalo `[suelo, techo]` usar como *dies a quo* según quién alega/combate la prescripción?
5. ¿`orden_indeterminado` debe **bloquear** o solo **degradar** una inferencia indiciaria (386 LEC) que dependa del orden?
6. ¿Algún marco que no he citado y que debería gobernar esto?

Sé escueto y quirúrgico: qué **rompe**, con qué caso, y qué cambio mínimo lo arregla. Evita validar por validar y evita arquitectura pesada si una regla basta.
