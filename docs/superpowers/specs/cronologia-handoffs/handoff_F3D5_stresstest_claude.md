# Handoff: stress test adversarial de F3.D5 (contradicción inter-fuente) + mini pseudocódigo

Este handoff recoge la última respuesta sobre el stress test adversarial de F3.D5, centrado en cómo entra la contradicción inter-fuente en el cómputo del soporte sin que el sistema resuelva el conflicto automáticamente. Añade al final un mini pseudocódigo operativo para que Claude pueda convertir la crítica en una regla de implementación más precisa. [file:191]

## Tesis central

La decisión de que el sistema no "resuelva" la contradicción es correcta como postura de prudencia y de buena gobernanza probatoria, pero se queda corta si fuerza toda contradicción al molde binario X vs ¬X, si no distingue bien entre contenido, credibilidad y autenticidad, y si no ofrece al usuario una indicación clara de qué versión está mejor soportada. El modelo mejora mucho si admite rivales no binarias, múltiples roles por acto y un punto controvertido que compare soportes sin penalizar dos veces el mismo conflicto. [file:191]

## Stress test por puntos

## 1) Contradicción de contenido como hecho rival ¬X

**Fallo principal.** Tratar toda contradicción como un hecho rival `¬X` con su propio soporte funciona para binarios limpios, pero falla en contradicciones parciales, graduales o paramétricas, donde no hay una negación simple del hecho sino varias versiones rivales del mismo atributo (importe, fecha, modalidad, alcance). [file:191]

**Dónde se rompe.** En casos como “21,3M” frente a “19M”, el problema no es X frente a no‑X sino X1 frente a X2. Forzar el caso a `¬X` hace perder estructura y puede sobrerreducir el conflicto. [file:191]

**Corrección mínima.** Mantener la idea de rival con soporte propio, pero permitir rivales no booleanas: `precio=21,3M`, `precio=19M`, `precio=20M`, etc., todas agrupadas bajo el mismo punto controvertido. Para contradicción parcial, el tope debe afectar sólo el componente discutido y no necesariamente todo el hecho compuesto. [file:191]

## 2) Tres dianas: contenido, credibilidad y autenticidad

**Fallo principal.** La taxonomía está bien orientada, pero varios casos pisan dos dianas a la vez. Una auto-contradicción de la misma fuente afecta a contenido y credibilidad; una impugnación de autenticidad sin base puede terminar diciendo más sobre la credibilidad de quien impugna que sobre la genuinidad del documento. [file:191]

**Dónde se rompe.** Si el sistema obliga a asignar cada acto contradictorio a una sola diana, se pierde información relevante sobre cómo debe propagarse el conflicto. [file:191]

**Corrección mínima.** Permitir proyección múltiple: un mismo acto puede generar un enlace de contradicción de contenido y, además, alimentar una señal de incoherencia o de impugnación táctica en el eje de credibilidad. La diana principal sigue existiendo, pero no excluye efectos secundarios explícitos. [file:191]

## 3) Peso simétrico: soporte propio × diagnosticidad

**Fallo principal.** La regla general es sensata —una negación desnuda no debería derribar una estructura fuerte—, pero infravalora contradicciones cualitativamente demoledoras aunque sean breves o formalmente ligeras. [file:191]

**Dónde se rompe.** Una frase puede ser floja como contradicción de X y, al mismo tiempo, potentísima como indicio de Y. Si el sistema la trata solo por su debilidad como socava de X, pierde su importancia estructural en el caso. [file:191]

**Corrección mínima.** Mantener el peso simétrico como regla por defecto, pero añadir un flag `impacto_cualitativo_alto` y permitir multi-rol del acto: débil para socavar X, fuerte para apoyar Y. Así se evita que la simetría se convierta en ceguera analítica. [file:191]

## 4) Rebatibilidad solo por evento o enlace nuevo

**Fallo principal.** La no mutación es buena práctica de procedencia y auditoría, pero puede producir cadenas de “contradicción de la contradicción” difíciles de leer y explicar. [file:191]

**Dónde se rompe.** Sin una buena vista temporal o de conflicto, el rebatimiento circular genera sensación de inestabilidad o de recursión infinita, aunque conceptualmente el modelo siga siendo finito. [file:191]

**Corrección mínima.** Mantener la invariante de no mutación, pero materializar una vista de historial de conflicto dentro del punto controvertido, mostrando secuencia temporal de versiones, contradicciones y rebatimientos. A nivel de cómputo, el sistema debe mirar sólo el soporte actual de cada versión, no la profundidad de la recursión. [file:191]

## 5) No-resolución del sistema

**Fallo principal.** La prudencia de no fijar “ganador” es correcta para no judicializar el motor, pero puede resultar demasiado tímida para una herramienta de parte si el usuario no ve cuál versión está mejor soportada. [file:191]

**Dónde se rompe.** Un punto controvertido que solo diga “hay conflicto” es poco útil si no compara `estatus_soporte(X)` y `estatus_soporte(¬X)` o de las variantes X1/X2/X3. [file:191]

**Corrección mínima.** Mantener que el sistema no decide verdad, pero añadir una etiqueta analítica `version_mejor_soportada` y una comparación visible de estatus entre versiones rivales. Esa preferencia es analítica, no judicial. [file:191]

## 6) Punto controvertido como nodo frente a simple enlace

**Fallo principal.** El nodo de punto controvertido es valioso porque hace visible que hay versiones rivales agrupadas, pero si además el enlace `contradice` degrada por su cuenta y luego el nodo vuelve a topar, aparece doble contabilidad. [file:191]

**Dónde se rompe.** El mismo conflicto puede penalizar dos veces: una por rival seriamente sostenida y otra por la mera presencia del enlace contradictorio. [file:191]

**Corrección mínima.** Repartir funciones con claridad: el enlace `contradice` expresa rivalidad entre versiones; el nodo `punto_controvertido` es donde se comparan soportes y se decide si existe rival seria con efecto de tope. La degradación debe computarse una sola vez. [file:191]

## 7) Casos límite críticos

### Negación desnuda autoservida frente a registro contemporáneo

Debe tratarse como socava de bajo peso frente a soporte robusto; no debería bajar por sí sola un hecho fuerte, aunque sí debe marcar controversia. [file:191]

### La misma frase contradice X y apoya Y

El modelo debe permitir múltiples enlaces desde el mismo acto: `contradice(X)` e `indiciaria(Y)`. Si obliga a un único rol, pierde riqueza analítica. [file:191]

### Contradicción parcial o de grado

No debe forzarse a X vs ¬X; requiere rivales parametrizadas bajo un mismo punto controvertido. [file:191]

### Contradicción en cadena

Si se socava un hecho intermedio, la degradación debe propagarse por las rutas de F3.D4 hacia el hecho final. [file:191]

### Auto-contradicción de la misma fuente

Debe leerse como rivalidad de contenido y como problema de credibilidad del mismo actor. [file:191]

### Impugnación táctica de autenticidad

Una impugnación sin soporte no debe sacar por sí sola un documento de la capa canónica; como mucho, genera controversia y puede perjudicar credibilidad del impugnante. [file:191]

### Contradicción aparente por ruido de identidad

La resolución de identidad debe correr antes de consolidar contradicciones; si no, se fabrican controversias que desaparecen al resolver actores o artefactos. [file:191]

## Mini pseudocódigo operativo para F3.D5

Este pseudocódigo traduce la crítica en una lógica mínima de implementación. No pretende cerrar todos los matices, sino dar una base para que Claude redacte la decisión formal. [file:191]

```text
function procesar_contradiccion(acto_origen, hecho_objetivo, matiz):

  if identidad_no_resuelta(acto_origen, hecho_objetivo):
      devolver "posponer_contradiccion_hasta_resolver_identidad"

  if matiz == "de_contenido":
      version_rival = construir_version_rival(hecho_objetivo, acto_origen)
      punto = obtener_o_crear_punto_controvertido(hecho_objetivo, version_rival)
      enlazar(version_rival, punto, tipo="version_rival")
      enlazar(hecho_objetivo, punto, tipo="version_rival")
      enlazar(acto_origen, version_rival, tipo="apoyo")
      enlazar(version_rival, hecho_objetivo, tipo="contradice")

      estatus_obj = calcular_estatus_F3D4(hecho_objetivo)
      estatus_rival = calcular_estatus_F3D4(version_rival)

      if rival_seria(estatus_rival):
          aplicar_tope_una_sola_vez(hecho_objetivo, maximo="🟡")

      marcar(punto, "controvertido")
      comparar_versiones(punto, hecho_objetivo, version_rival)

  if matiz == "de_credibilidad":
      actos_apoyo = actos_que_sostienen(hecho_objetivo)
      for acto in actos_apoyo:
          if acto_afectado_por_contradiccion(acto_origen, acto):
              registrar_socava_credibilidad(acto_origen, acto)
      recalcular_eje_credibilidad(actos_apoyo)
      recalcular_estatus_F3D4(hecho_objetivo)

  if matiz == "de_autenticidad":
      registrar_evento_procesal_impugnacion(acto_origen, hecho_objetivo)
      if impugnacion_tiene_soporte_minimo(acto_origen):
          afectar_anclaje_o_alcance(hecho_objetivo)
      else:
          registrar_impugnacion_tactica(acto_origen)
      recalcular_estatus_F3D4(hecho_objetivo)

  if mismo_acto_socava_X_y_apoya_Y(acto_origen):
      permitir_multiples_enlaces(acto_origen)

  return resumen_conflicto(hecho_objetivo)
```

## Recomendaciones mínimas para Claude

### 1) No encerrar toda contradicción en X vs ¬X

La mejor mejora es aceptar rivales no binarias y contradicciones parciales o paramétricas. El molde booleano debe ser una subclase, no la forma universal. [file:191]

### 2) Evitar doble contabilidad del conflicto

El nodo de punto controvertido debe ser el único lugar donde se materializa la rival seria y su efecto de tope. El enlace `contradice` no debería penalizar por separado. [file:191]

### 3) Dar preferencia analítica sin adjudicar verdad

La herramienta puede y debe indicar qué versión está mejor soportada, siempre que quede claro que no está resolviendo judicialmente el conflicto. [file:191]

## Cierre operativo

F3.D5 está bien orientada si se entiende como una disciplina de representación y encauzamiento del conflicto, no como un módulo de resolución. Pero necesita más elasticidad tipológica, una separación más clara entre rivalidad y penalización, y una salida comparativa que ayude al usuario a trabajar con versiones rivales sin que el sistema finja neutralidad ciega. [file:191]
