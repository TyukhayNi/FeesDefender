---
tipo: handoff
estado: historico
creado: 2026-06-12
origen: sesión Cowork (diseño con Nikolai — control de calidad del archivo, check 2)
destino: Claude Code — incorporar a PLAN.md bajo [SIGUIENTE-INTAKE-PROCURADORES-EMAIL]
consumido_por: "diseño intake-procuradores (PLAN_INTAKE_PROCURADORES_EMAIL.md; F3 / PR #81)"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# Handoff → PLAN.md · bloque "Control de calidad del archivo (check 2)"

> **Para Claude Code.** Incorporar este bloque a `PLAN.md` dentro del backlog
> `[SIGUIENTE-INTAKE-PROCURADORES-EMAIL]`. Diseño cerrado con Nikolai el
> 2026-06-12. Extiende `docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md` (§4.7 log de
> auditoría y §10 store de aprendizaje). Coherente con *El Auditor* (solo lectura,
> reporta no conformidades a Nikolai, traza desde el día uno).

---

## 1. Modelo: control por excepción en tres capas

El archivo NO se revisa dos veces entero. El tiempo de empleados se concentra
donde hay riesgo:

1. **Capa 1 — Ana Velástegui (secretaria) confirma todo.** Es la bandeja de
   revisión actual (F2). 100% humano. Sin cambios.
2. **Capa 2 — auto-chequeo del programa.** Repasa lo archivado sin consumir tiempo
   humano y aparta lo sospechoso.
3. **Capa 3 — Paola Barreto adjudica solo lo apartado** (a diario) + una muestra
   aleatoria. Nikolai lee un resumen semanal de solo lectura.

Beneficio lateral: cada corrección humana es señal de aprendizaje de primera
calidad (§10), y la tasa de error medida es lo que autoriza, más adelante, a
auto-aprobar la confianza alta sin confirmación de Ana (menos tiempo de empleados).

## 2. Qué vigila el auto-chequeo (capa 2)

Prioridad a lo determinista e independiente del criterio humano (sin LLM), que es
donde está el valor real:

- **Invariante de referencia:** *Su ref* extraída del correo ≠ num/serie del
  expediente donde se relacionó → candidato a **expediente equivocado** (error más
  grave y difícil de ver a ojo).
- **Coherencia de campos:** juzgado / nº autos del correo que no casan con los
  campos del expediente.
- **Cobertura:** correos de procurador en los buzones sin apunte de "procesado"
  → hueco. Independiente de la calidad del archivo; es el riesgo de
  responsabilidad puro.
- **Carpeta por defecto:** documento caído en "General" (fallback) siendo una
  actuación clasificable.
- **Adjuntos:** nº de adjuntos del correo ≠ subidos, descontando logos/firmas.

El LLM se reserva para lo semántico (¿el nombre/carpeta encaja con el contenido?)
y solo sobre el subconjunto ya marcado o muestreado — una segunda pasada de LLM
"que relee" añade poco porque comparte el sesgo de la primera.

## 3. Cola de Paola (diaria) — pestaña "Control de archivo" en Streamlit

NO un informe: Paola corrige, así que necesita una pestaña operativa donde ya
trabaja. Cola corta, priorizada:

1. Rupturas de invariante (expediente equivocado).
2. Huecos de cobertura.
3. **Documentos importantes / con plazo → revisión del 100%** (ver §4).
4. Divergencias: Ana sobrescribió un match de confianza alta, o confirmó un
   "dudoso / sin expediente".
5. Muestra aleatoria **~10%** del resto (lo que parece correcto) — para medir la
   tasa real de error, no para cazar fallos concretos. Bajable cuando la tasa se
   confirme baja.

Cada ítem se muestra lado a lado: **correo → propuesta del robot → acción de Ana
→ invariante roto**. Paola da el visto bueno o corrige en el sitio (expediente /
carpeta / nombre). Cada corrección alimenta el store de aprendizaje (§10) y cuenta
para la métrica. Si un día la cola está limpia, son dos minutos.

## 4. Documentos importantes (revisión 100%)

Sentencias, autos, emplazamientos, traslados **y cualquier correo donde se
mencione o se deduzca un plazo, sea del tipo que sea** (una diligencia de
ordenación o una notificación normal también abren plazo). El programa debe pecar
de marcar de más: un falso positivo cuesta segundos a Paola; un plazo que se
escapa cuesta un caso.

## 5. Tres velocidades de revisión

La regla de fondo: **el hueco de revisión nunca puede ser mayor que el margen del
plazo más corto** que pueda venir en un correo.

- **Continua:** "¿hay un correo de procurador sin procesar?" — lo más peligroso,
  no espera a la noche.
- **Mismo día:** lo que trae plazo (§4) — vía rápida + aviso el mismo día en que
  se archiva. Reacción en horas, no en un día.
- **Día hábil siguiente:** todo lo demás — cola matinal de Paola. Hueco máximo
  ~1 día laborable, suficiente para lo que no tiene plazo.

## 6. Resumen semanal (Nikolai) — solo lectura

Tarea programada → llega a `procesal@tyukhay.legal` (o donde se decida). Nikolai
supervisa, no opera. Contiene:

- Tasa de error de la semana (ítems corregidos por Paola / total archivado) y
  tendencia.
- Nº de excepciones por tipo, y cuántas siguen sin resolver o son de alta
  gravedad.
- Huecos de cobertura no cerrados (correos que nadie procesó).
- Quién archivó / quién revisó cada día y si algún día quedó sin revisar.
- Veredicto en una línea: ¿el archivo fue de fiar este periodo, sí/no?

Cuando la tasa de error baje y se estabilice → habilita auto-aprobar la confianza
alta sin confirmación de Ana.

## 7. Suplencias / ausencias

- **Dos papeles que cubrir, nunca cero de ninguno:** archivador (Ana) y revisor
  (Paola).
- **Independencia:** quien archiva un lote no lo revisa. Si Ana está fuera y
  archiva Paola, esos días la revisión pasa a Nikolai o Sergio.
- **Sin reasignación anticipada** (calendario de ausencias descartado por ahora):
  el trabajo no procesado se queda en la cola y, pasado su plazo sin que nadie lo
  toque, **escala solo hacia Nikolai**. El aviso por antigüedad sustituye al
  calendario — reacciona en vez de anticipar, pero la red de seguridad se mantiene.

## 8. Trazabilidad ("quién hace qué")

- **Login propio por persona en Streamlit. NADA de cuentas compartidas** (o el
  rastro se rompe). Cada acción queda sellada: "archivado por X / revisado por Y,
  fecha y hora".
- Las **suplencias se trazan solas:** el login recoge quién hizo, no quién debería
  — si cubre Paola o Sergio, queda su nombre sin que nadie lo declare.
- **Regla de independencia automática:** el programa compara el sello del
  archivador con el del revisor y no deja que coincidan en el mismo ítem.
- **Las omisiones (lo que nadie hizo) NO las ve el login** → las caza la cola por
  antigüedad + escalado a Nikolai.
- Sin calendario, el resumen semanal dice quién revisó y si algún día quedó sin
  revisar; **el "porqué" del hueco lo interpreta Nikolai** al leerlo.

## 9. Requisito duro de diseño

La traza debe capturar, **desde F2/F3**, la terna **propuesta-del-robot vs.
acción-confirmada vs. quién-y-cuándo**. Sin ese registro el check 2 no tiene
contra qué comparar. Diseñar dentro de F2/F3, no atornillar después.

## 10. Decisiones cerradas (2026-06-12)

1. Control por excepción en tres capas (Ana 100% → auto-chequeo → Paola
   excepciones + muestra → Nikolai resumen).
2. Auto-chequeo prioriza invariantes deterministas + cobertura; LLM solo para lo
   semántico del subconjunto marcado.
3. Cola de Paola diaria en Streamlit, priorizada; muestra aleatoria 10% (ajustable).
4. Importantes = sentencias/autos/emplazamientos/traslados **+ todo lo que tenga
   plazo**; revisión 100%; sobre-marcar mejor que omitir.
5. Tres velocidades: continua (no procesado) / mismo día (plazo) / día siguiente
   (resto). Hueco < margen del plazo más corto.
6. Resumen semanal a Nikolai, solo lectura, estilo *El Auditor*.
7. Suplencias: nunca cero revisores; archivador ≠ revisor del mismo lote; sin
   reasignación anticipada, escalado automático a Nikolai por antigüedad de cola.
8. Trazabilidad por login propio por persona; sin cuentas compartidas; omisiones
   por cola, no por login.
9. **Calendario de ausencias = MEJORA FUTURA** (solo si los avisos llegan tarde o
   demasiado a menudo durante ausencias).
10. Requisito duro: traza propuesta-vs-acción-vs-quién desde F2/F3.

## 11. Pendientes / a decidir al construir

- Plazos concretos de la cola antes de escalar (definir las X horas/días por tipo).
- Mecanismo de aviso del "mismo día" para plazos (¿correo? ¿notificación en la
  bandeja?).
- Tamaño definitivo de la muestra aleatoria (default 10%).
- Cadencia del resumen (default semanal; Nikolai puede pasarlo a diario).
- Lista de "tipos con plazo" + detección de plazo explícito en el cuerpo del LLM.
