# Handoff: stress test adversarial de F3.D4 + pseudocódigo + plantilla de estructura del soporte

Este handoff reúne tres piezas: (1) el stress test adversarial de F3.D4, la función que calcula el estatus de soporte de un hecho derivado a partir del grafo de enlaces; (2) una traducción operativa en pseudocódigo paso a paso para usar con Claude; y (3) una tabla plantilla que resume cómo distintas estructuras de soporte deberían mapearse a rangos posibles de 🟢🟡🔴. El foco es conservar el marco categórico y estructural del sistema sin perder controles sobre independencia, cadenas, rivales e indicio único. [cite:180][cite:94][cite:56][cite:95]

## Contexto resumido

El sistema distingue una capa canónica de actos datados anclados a fuente y una capa derivada de hechos inferidos. Los enlaces de prueba son binarios, tipados y curados por el letrado; la fuerza vive en el enlace, no en el hecho. F3.D4 no asigna magnitudes a enlaces ni decide contradicciones de detalle: sólo transforma el grafo ya curado en un estatus de soporte propuesto para cada hecho derivado. [cite:31][cite:151][cite:180]

La decisión que se somete a stress test evita suma ponderada de magnitudes para escapar de la falsa precisión y propone una regla estructural categórica: distinguir prueba directa, pluralidad de indicios, independencia real, diagnosticidad condicional a hipótesis, cadenas inferenciales y topes por rival seria, presunción, credibilidad o fiabilidad. [cite:94][cite:95][cite:56][cite:178]

## Tesis central del stress test

El diseño es conceptualmente sano, pero se rompe si se toma de forma demasiado rígida. Los puntos más delicados son cinco: la pérdida de matiz al no tener ningún score interno; la dificultad de decidir independencia real de orígenes; la degradación torpe cuando no hay hipótesis rival bien formulada; la infravaloración de rutas redundantes si se aplica el mínimo de forma global; y el riesgo de banalizar el “indicio único de gran fuerza” si no se imponen frenos muy duros. [cite:180][cite:94][cite:152][cite:178]

## Debilidades priorizadas

## 1) Regla categórica pura: robusta contra falsa precisión, pero pobre en fronteras

**Problema en una frase.** Un semáforo puramente estructural evita el espejismo de exactitud numérica, pero pierde matices importantes en soportes mixtos y dificulta distinguir entre un 🟡 alto y un 🟡 débil, o entre un 🟢 justo y un 🟢 muy sólido. [cite:180][cite:186]

**Fundamento.** Las redes de inferencia y la teoría de Schum muestran que la fuerza del soporte depende de interacción entre convergencia, cadenas y alternativas. Un sistema solo categórico corre el riesgo de tratar igual configuraciones cualitativamente distintas si ambas caen bajo la misma regla de color. [cite:94][cite:180]

**Corrección mínima.** Mantener la salida visible en 🟢🟡🔴, pero añadir un `indice_interno_cualitativo` o `borde_de_estado` usado solo para ordenar revisión y explicar sensibilidad. No es un score probabilístico ni debe alimentar la carga o el semáforo final de forma automática. [cite:180]

## 2) Colapso por independencia: el punto más frágil del sistema

**Problema en una frase.** La pluralidad real del art. 386 depende de contar orígenes verdaderamente independientes, pero esa independencia rara vez se deduce solo de la forma del grafo; requiere conocimiento de procedencia y, a menudo, juicio humano. [cite:179][cite:180]

**Fundamento.** La literatura de entity resolution y de análisis de evidencia insiste en que distintas apariciones pueden derivar de una misma fuente primaria aunque parezcan autónomas. Contarlas como pluralidad fuerte sobreinfla soporte; colapsarlas siempre, en cambio, puede infra-contar prueba realmente convergente. [cite:179][cite:183][cite:180]

**Corrección mínima.** Clasificar cada aportación en tres niveles: `independiente`, `probable_dependencia`, `fuente_comun`. Solo los `independiente` alimentan pluralidad fuerte; los de dependencia probable requieren revisión o computan de forma conservadora como uno. [cite:179]

## 3) Diagnosticidad condicional a hipótesis: se rompe si no hay rival usable

**Problema en una frase.** El paso ACH “solo cuenta lo que discrimina frente a una rival” es potente, pero falla mal cuando no existe hipótesis rival declarada o cuando la rival está formulada tan vagamente que no sirve para discriminar. [cite:152][cite:95]

**Fundamento.** ACH funciona comparando hipótesis concretas y rivales. Si la rival no está o es demasiado genérica, el sistema puede optar entre dos errores simétricos: asumir diagnóstico por defecto o bloquear indebidamente la subida a 🟢. [cite:152][cite:95]

**Corrección mínima.** Introducir un estado operativo intermedio: `diagnosticidad_no_evaluable`. Regla: sin rival usable, la vía indiciaria no sube a 🟢 salvo prueba directa robusta o estructura excepcionalmente fuerte; el sistema debe explicarlo. [cite:152]

## 4) Regla del eslabón más débil: correcta por ruta, errónea si se aplica al conjunto

**Problema en una frase.** La intuición de que una cadena vale lo que su eslabón más débil es buena para una ruta inferencial concreta, pero infravalora hechos sostenidos por varias rutas independientes cuando una de ellas es más robusta que las otras. [cite:180][cite:94]

**Fundamento.** Schum distingue inferencia catenada e inferencia convergente. El mínimo tiene sentido dentro de cada cadena; el conjunto de cadenas, en cambio, puede reforzarse por redundancia. [cite:94][cite:180]

**Corrección mínima.** Computar `min` por ruta y combinar luego rutas independientes con una regla de convergencia cualitativa. Por ejemplo: dos rutas independientes con base ≥🟡 fuerte pueden permitir 🟢 aunque una de ellas tenga un eslabón amarillo. [cite:94]

## 5) Tope por hipótesis rival no excluida: demasiado severo si se entiende en clave de certeza

**Problema en una frase.** Si toda rival no completamente excluida topa el hecho a 🟡, el sistema exige de facto una cuasi-certeza incompatible con la lógica probatoria civil y con el funcionamiento real de la prueba por indicios. [cite:178][cite:56]

**Fundamento.** El art. 386 LEC pide un enlace preciso y directo según las reglas del criterio humano, no la eliminación metafísica de toda hipótesis alternativa. La rival relevante es la que sigue siendo seriamente plausible, no la que sobrevive como posibilidad abstracta. [cite:56][cite:178]

**Corrección mínima.** Reformular el tope: solo limita a 🟡 si la hipótesis rival permanece `seriamente_sostenida` por enlaces confirmados o por una estructura alternativa coherente. Rival residual o meramente imaginable no debe impedir 🟢. [cite:56]

## 6) Indicio único de gran fuerza: excepción necesaria, pero muy fácil de inflar

**Problema en una frase.** La puerta al 🟢 por un solo indicio fuerte es dogmáticamente correcta, pero operativamente peligrosa: sin criterios objetivos y frenos institucionales, todo indicio importante tenderá a presentarse como “muy diagnóstico”. [cite:56][cite:178]

**Fundamento.** La doctrina sobre presunción judicial admite el indicio único excepcionalmente, cuando el enlace es preciso y directo y la fuerza del indicio es singular. Convertir esa excepción en rutina banaliza el estándar. [cite:56][cite:178]

**Corrección mínima.** Definir un checklist restrictivo para `indicio_unico_gran_fuerza`:  
- enlace `preciso_y_directo`;  
- alta credibilidad y fiabilidad;  
- independencia clara;  
- rival seria debilitada;  
- motivación expresa del letrado.  
El sistema puede sugerir “candidato a gran fuerza”, pero no cerrar automáticamente el 🟢 por esa vía. [cite:56]

## 7) Separar estatus objetivo de soporte y carga de la prueba es correcto, pero solo si la vista los vuelve a juntar

**Problema en una frase.** Separar soporte y carga evita contaminar la evaluación estructural de la prueba, pero si el usuario ve el semáforo sin el art. 217 LEC al lado, puede interpretar mal el riesgo procesal del hecho. [cite:23][cite:109]

**Fundamento.** En proceso civil, la fuerza del soporte y la carga de la prueba no son lo mismo, pero su combinación importa para saber qué hechos ponen en riesgo el caso. La separación de modelo es buena; la separación de interfaz puede ser engañosa. [cite:23][cite:109]

**Corrección mínima.** Mantener el cálculo de soporte neutral a la carga, pero obligar a que las vistas de trabajo (`HECHOS_X.md`) muestren siempre `estatus_soporte + clasificacion_217 + parte_con_carga + dispensa 281` como bloque conjunto. [cite:23][cite:19][cite:109]

## 8) Hechos negativos: el modelo general no les encaja bien

**Problema en una frase.** Hechos como “no consta que se informara de X” no se comportan bien bajo una lógica diseñada para indicios positivos, convergencia y pluralidad de apoyos afirmativos. [cite:23][cite:109]

**Fundamento.** La prueba de hechos negativos y la llamada prueba diabólica obligan a atender a facilidad probatoria, deber de documentar y contexto institucional. No basta con decir “faltan enlaces a favor”. [cite:23][cite:24][cite:69]

**Corrección mínima.** Crear una vía específica para `tipo_hecho = negativo`, donde el soporte se calcule sobre: ausencia esperable de rastro, obligación de registro, facilidad probatoria y presencia o no de indicios positivos contrarios. No aplicar mecánicamente 386 a estos casos. [cite:23][cite:69]

## Casos límite reforzados

### Soporte mixto contradictorio

Tres indicios fuertes, independientes y diagnósticos apoyan el hecho; un enlace socavador fuerte subsiste sin rebatir. Un tope rígido podría bajar todo a 🟡 cuando el balance real merecería un verde cauteloso o, al menos, un amarillo alto explicado. [cite:94][cite:95]

**Corrección mínima.** Tratar la contradicción como tope cualificado: no basta con que exista; debe ser seria, no rebatida y directamente incompatible con el núcleo del hecho. [cite:95]

### Redundancia de rutas en cadena

Dos cadenas separadas sostienen el hecho final; una es claramente verde, otra amarilla por un eslabón dudoso. Un uso burdo del mínimo global infravaloraría el soporte. [cite:180]

**Corrección mínima.** Evaluación por rutas y combinación posterior por convergencia. [cite:180]

### Rival mal formulada

Una rival como “todo fue formalmente regular” es demasiado difusa para ACH; seguirá “viva” siempre. [cite:152]

**Corrección mínima.** Requerir que las rivales sean concretas, excluyentes y operativas; si no, marcarlas como `rival_no_usable` para el paso de diagnosticidad. [cite:152]

### Presunción 386 con base amarilla

Se quiere presumir un hecho cuando el hecho base sólo alcanza 🟡. [cite:56]

**Corrección mínima.** No bloquear sin más, pero imponer tope fuerte: el hecho presumido no puede superar el soporte del hecho base y debe salir como máximo en 🟡 salvo motivación excepcional del letrado. [cite:56]

## Pseudocódigo paso a paso para F3.D4

El siguiente pseudocódigo intenta conservar la filosofía categórica del sistema, introduciendo solo las correcciones mínimas detectadas. [cite:94][cite:95][cite:56]

```text
function calcular_estatus_soporte(hecho H):

  ENL = enlaces_confirmados_entrantes(H)
  if ENL is empty:
      return resultado(estatus="🔴", motivo="sin enlaces confirmados")

  # Paso 0: filtrar por relevancia de contenido
  ENL_CONTENIDO = filtrar(ENL, signo in {apoya, socava} and funcion not in {menciona, contexto})
  ENL_CIRC = filtrar(ENL, funcion == documenta_circulacion or funcion == S1_circulacion)

  # Paso 1: colapso por independencia
  APORTES = agrupar_por_origen_primario(ENL_CONTENIDO)
  # cada aporte queda clasificado como independiente / probable_dependencia / fuente_comun
  APORTES_INDEP = colapsar(APORTES, regla="solo independientes cuentan por separado")

  # Paso 2: separar estructura del soporte
  DIRECTOS = seleccionar(APORTES_INDEP, funcion in {documenta, corrobora_directa} and signo == apoya)
  INDICIOS = seleccionar(APORTES_INDEP, funcion == indiciaria and signo == apoya)
  SOCAVA = seleccionar(APORTES_INDEP, signo == socava)

  # Paso 3: base inicial por tipo
  if existe_directo_robusto(DIRECTOS):
      estatus_base = "🟢"
      razon_base = "prueba directa robusta"
  else:
      estatus_base = evaluar_indicios_base(H, INDICIOS)
      razon_base = explicacion_indicios(H, INDICIOS)

  # evaluar_indicios_base:
  # - >=2 indicios independientes, convergentes y diagnósticos -> candidato 🟢
  # - 1 indicio único de gran fuerza -> candidato 🟢 solo si checklist estricto
  # - 1 indicio ordinario o varios dependientes/no diagnósticos -> 🟡
  # - ninguno o solo no diagnósticos -> 🔴

  # Paso 4: diagnosticidad condicional (ACH)
  RIVALES = hipotesis_rivales_usables(H)
  if usa_via_indiciaria(estatus_base):
      if RIVALES is empty:
          marcar("diagnosticidad_no_evaluable")
          estatus_base = min_categorico(estatus_base, "🟡")
      else:
          INDICIOS_DIAG = filtrar_indicios_que_discriminan(INDICIOS, RIVALES)
          estatus_base = recalcular_con_INDICIOS_DIAG(estatus_base, INDICIOS_DIAG)

  # Paso 5: cadenas inferenciales
  if H.funcion_inferencial in {final, intermedio} and depende_de_subhechos(H):
      RUTAS = rutas_inferenciales_hasta(H)
      ESTATUS_RUTAS = []
      for ruta in RUTAS:
          estatus_ruta = minimo_categorico(estatus_de_cada_eslabon(ruta))
          ESTATUS_RUTAS.append((ruta, estatus_ruta, independencia_de_ruta(ruta)))
      estatus_cadenas = combinar_rutas_por_convergencia(ESTATUS_RUTAS)
      estatus_base = min_o_refuerzo(estatus_base, estatus_cadenas)

  # combinar_rutas_por_convergencia:
  # - una sola ruta -> su mínimo
  # - dos o más rutas independientes con soporte al menos 🟡 fuerte -> puede reforzar a 🟢
  # - rutas dependientes no suman como pluralidad fuerte

  # Paso 6: presunciones
  if H.tipo_presuncion == "judicial_386":
      if not H.cumple_preciso_directo:
          estatus_base = min_categorico(estatus_base, "🟡")
      hecho_base_estatus = obtener_estatus_hechos_base(H)
      estatus_base = min_categorico(estatus_base, hecho_base_estatus)

  if H.tipo_presuncion == "legal_385":
      aplicar_regimen_presuncion_legal(H, estatus_base)

  # Paso 7: topes por rival seria
  if existe_rival_seriamente_sostenida(H):
      estatus_base = min_categorico(estatus_base, "🟡")

  # Paso 8: topes por socava y por ejes 2/3
  if existe_socava_significativo_no_rebatido(SOCAVA):
      estatus_base = degradar_por_socava(estatus_base)

  if credibilidad_o_fiabilidad_bajas(H):
      estatus_base = degradar_por_ejes(estatus_base)

  # Paso 9: hechos negativos
  if H.tipo_hecho == "negativo":
      estatus_base = recalcular_hecho_negativo(H, ENL_CONTENIDO)

  # Paso 10: circulación separada
  estatus_circulacion = calcular_circulacion(ENL_CIRC)

  return resultado(
      estatus=estatus_base,
      estatus_circulacion=estatus_circulacion,
      explicacion=generar_explicacion(H, DIRECTOS, INDICIOS, SOCAVA, RIVALES, RUTAS)
  )
```

## Tabla plantilla: “estructura del soporte” → rango posible de estatus

La tabla siguiente no pretende cerrar umbrales, sino servir como plantilla de diseño y discusión con Claude para pulir F3.D4 sin caer en falsa precisión. [cite:94][cite:56][cite:95]

| Estructura del soporte | Independencia | Diagnosticidad frente a rival | Cadenas / rutas | Resultado orientativo | Notas de tope |
|---|---|---|---|---|---|
| Prueba directa robusta (documenta/corrobora-directa) | No decisiva si la prueba es directa, pero importa para corroboración adicional | No imprescindible para base inicial, sí para resistir rival | Sin cadena o cadena corta | Candidato 🟢 | Puede bajar por socava serio, baja fiabilidad o rival seriamente sostenida |
| Dos o más indicios convergentes | Independientes | Alta | Sin cadena o con cadena simple sólida | Candidato 🟢 [cite:56] | Si la rival sigue seria → tope 🟡 |
| Un indicio único excepcional | Independencia clara | Muy alta | Sin cadena compleja | Candidato 🟢 solo excepcional [cite:56][cite:178] | Requiere checklist estricto y motivación |
| Un indicio ordinario | Cualquiera | Media o baja | No relevante | 🟡 | No debería subir a 🟢 sin apoyo adicional |
| Varios indicios dependientes (misma fuente primaria) | Baja / fuente común | Aunque altos en apariencia | No relevante | 🟡 o 🔴 | Colapsan como una sola aportación |
| Indicios compatibles por igual con hipótesis rival | Puede ser alta | Baja / no discrimina | No relevante | 🟡 o 🔴 [cite:152] | Señal existe, pero no cuenta fuerte por ACH |
| Cadena única con un eslabón 🟡 | Puede ser independiente | Variable | Ruta única | Máximo 🟡 [cite:94] | Regla del eslabón más débil |
| Dos rutas independientes: una 🟢 y otra 🟡 | Alta entre rutas | Media/alta | Redundancia de rutas | Puede sostener 🟢 [cite:94] | No aplicar min global al conjunto |
| Contradicción seria no rebatida + soporte favorable fuerte | Variable | Variable | Mixto | 🟡 alto o 🟡 plano | La mera existencia de contradicción no debería forzar siempre 🔴 |
| Presunción 386 con hecho base 🟢 y nexo preciso/directo | Base suficientemente sólida | Debe discriminar razonablemente | Cadena de presunción | Candidato 🟢 [cite:56] | Nunca supera el soporte del hecho base |
| Presunción 386 con hecho base 🟡 | Base insuficiente para cierre fuerte | Baja o media | Cadena de presunción | Máximo 🟡 [cite:56] | Debe salir explicado como soporte no cerrado |
| Hecho negativo con ausencia esperable de rastro + deber de documentar | N/A | Se juega en contexto, no solo rival | Ruta especial | 🟡 o 🟢 según contexto [cite:23][cite:69] | Requiere lógica separada, no solo pluralidad de indicios |
| Solo circulación por múltiples canales | Puede ser alta en canales | No prueba contenido | No relevante | 🔴 para contenido / soporte propio para “conocimiento” | Debe alimentar hecho distinto: que el contenido circuló |

## Recomendaciones mínimas para Claude

### 1) Mantener el semáforo como salida, pero con un índice interno cualitativo

La regla estructural categórica es útil y evita falsa precisión, pero necesita un apoyo interno para ordenar fronteras y explicar sensibilidad. No hace falta un modelo bayesiano completo ni una suma de magnitudes; basta una señal cualitativa de cuán cerca está un hecho del siguiente nivel. [cite:180]

### 2) Tratar independencia, cadenas y rivales como problemas distintos

F3.D4 mejora mucho si distingue: (a) independencia de aportaciones, (b) mínimo por ruta y convergencia entre rutas, y (c) rival seria frente a rival residual. Ese triple ajuste evita tanto el sobrecómputo de pluralidad como el bloqueo excesivo del verde. [cite:94][cite:179][cite:56]

### 3) Encerrar la excepción del indicio único en una jaula estrecha

La subida a 🟢 por un solo indicio debe existir, pero como excepción controlada: checklist, motivación expresa, alta fiabilidad y rival debilitada. Si no, acabará siendo un atajo recurrente que vacía de sentido la exigencia de pluralidad o de enlace preciso y directo. [cite:56][cite:178]

## Cierre operativo

La mejor forma de mejorar F3.D4 no es convertirlo en un modelo numérico total, sino volver más inteligente su estructura: independencia con grados, rutas separadas, rival seria en vez de rival abstracta, y una disciplina específica para hechos negativos y para el indicio único fuerte. Con eso se conserva la sobriedad del semáforo sin aceptar sus rigideces más peligrosas. [cite:94][cite:95][cite:56]
