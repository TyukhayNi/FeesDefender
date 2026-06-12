# PREPARACIÓN {{TIPO_ESCRITO}} — {{REFERENCIA}}

> Documento maestro estratégico. Punto único de verdad del asunto.
> Toda decisión cerrada se consigna aquí. Cualquier modificación posterior debe reflejarse en este documento ANTES de tocar borradores.

---

## 1. Identificación del asunto

- **Referencia interna:** {{REFERENCIA}}
- **Tipo de escrito:** {{TIPO_ESCRITO}}
- **Procedimiento:** {{PROCEDIMIENTO}}
- **Cuantía:** {{CUANTIA}}
- **Juzgado:** {{JUZGADO}}
- **Parte representada:** DON/DOÑA **{{PARTE_REPRESENTADA}}**
- **Posición procesal:** {{POSICION}}
- **Contraparte:** DON/DOÑA **{{CONTRAPARTE}}**
- **Fecha de apertura:** {{FECHA_APERTURA}}

---

## 2. Decisiones estratégicas cerradas

> Cada punto cerrado se marca con `[CERRADO]`. Lo abierto, con `[PENDIENTE]`.
> Las decisiones de los bloques 2.6, 2.7 y 2.8 son convenciones permanentes del despacho — no se renegocian.

### 2.1. Arquitectura del escrito

- [PENDIENTE] Estructura: {{ARQUITECTURA}}

### 2.2. Pretensión

- [PENDIENTE] Petitum principal: {{PETITUM_PRINCIPAL}}
- [PENDIENTE] Petitum subsidiario: {{PETITUM_SUBSIDIARIO}}

### 2.3. Intereses

- [PENDIENTE] Tipo: {{TIPO_INTERES}}
- [PENDIENTE] Fecha de origen: {{FECHA_INTERES}} — fundamento: {{FUNDAMENTO_INTERES}}

### 2.4. Costas

- [PENDIENTE] Solicitud expresa con fundamento en art. 394 LEC.

### 2.5. Prueba

- [PENDIENTE] Documental: incluida con el escrito.
- [PENDIENTE] Pericial: {{PERICIAL}}
- [PENDIENTE] Perito propuesto: DON/DOÑA **{{PERITO}}**
- [PENDIENTE] Testifical: {{TESTIFICAL}}
- [PENDIENTE] Interrogatorio de parte: {{INTERROGATORIO}}

### 2.6. Estilo y formato (cerrado por convención del despacho)

- [CERRADO] Criterios formales TS Sala 1.ª (Times 12, márgenes 2,5 cm, interlineado 1,5, citas 10 pt cursiva sangría 1 cm).
- [CERRADO] DON/DOÑA + nombre en MAYÚSCULAS NEGRITA en toda mención.
- [CERRADO] Listas de 2.º nivel en formato a), b), c).
- [CERRADO] Listas jerárquicas 1., 1.1., 1.1.1.
- [CERRADO] Párrafos numerados correlativamente.
- [CERRADO] Nomen iuris con paréntesis único: `(en adelante, «el X»)`.
- [CERRADO] Sin trimembraciones gratuitas.
- [CERRADO] En civil siempre «desestimar», no «absolver».

### 2.7. Deontología (cerrado por convención del despacho)

- [CERRADO] Sin aportar correspondencia entre letrados (art. 21 EGAE, art. 5 CDCGAE). Revisión obligatoria del índice documental antes del cierre.

### 2.8. Anclaje a fuente y verificación (cerrado por convención del despacho)

- [CERRADO] Anclaje a fuente obligatorio en la fijación de Hechos (convivencia con `verificacion-anclada-fuente`). Cada Hecho con estado 🟢/🟡/🔴; sin inferencias no marcadas.
- [CERRADO] Hechos 🟡 (pendientes de soporte) admisibles, con medio de prueba previsto y registrados en el mapa de prueba (sección 7).
- [CERRADO] Jurisprudencia a citar verificada en CENDOJ antes del cierre; referencias de bases privadas contrastadas contra el CGPJ (encadenar `cendoj-descarga`).

### 2.9. Decisiones específicas del asunto

- [PENDIENTE] {{DECISION_ESPECIFICA_1}}

---

## 3. Arquitectura del escrito (esquema)

```
ENCABEZAMIENTO
PREVIO (opcional)
HECHOS
  PRIMERO — {{TITULO_HECHO_1}}
  SEGUNDO — {{TITULO_HECHO_2}}
  ...
FUNDAMENTOS DE DERECHO
  I. JURISDICCIÓN Y COMPETENCIA
  II. PROCEDIMIENTO
  III. LEGITIMACIÓN
  IV. POSTULACIÓN
  V. CUANTÍA
  VI. FONDO
  VII. INTERESES
  VIII. COSTAS
SUPLICO
OTROSÍES
```

---

## 4. Cronología de hechos

| Fecha | Hecho | Documento de respaldo |
|-------|-------|------------------------|
| | | DOC_NN |

> Las filas sin `DOC_NN` corresponden a hechos pendientes de soporte: indicar el medio de prueba previsto y reflejarlas en el mapa de prueba (sección 7).

---

## 5. Personas clave

| Nombre | Rol | Datos relevantes |
|--------|-----|------------------|
| DON/DOÑA **{{PARTE_REPRESENTADA}}** | {{POSICION}} | |
| DON/DOÑA **{{CONTRAPARTE}}** | Contraparte | |

---

## 6. Índice documental

| DOC | Descripción | Origen | Fecha |
|-----|-------------|--------|-------|
| DOC_01 | | | |
| DOC_02 | | | |

> [PENDIENTE] Revisión deontológica del índice: verificar ausencia de correspondencia entre letrados antes del cierre.

---

## 7. Mapa de prueba (hechos pendientes de soporte)

> Hechos alegados aún sin documento cerrado (estado 🟡 en `HECHOS_X.md`). Convivencia con `verificacion-anclada-fuente`. Cada fila debe tener un medio de prueba previsto antes de pasar a redacción. Ningún hecho en estado 🔴 (inferencia no soportada) puede figurar como Hecho.

| Hecho | Enunciado breve | Medio de prueba previsto | Estado |
|-------|-----------------|--------------------------|--------|
|       |                 |                          | por recabar / propuesto / admitido |

---

## 8. Pendientes operativos

- [ ] {{PENDIENTE_1}}

---

## 9. Histórico de decisiones reabiertas

> Solo se rellena si se reabre una decisión previamente cerrada. Anotar fecha, motivo y nueva redacción.

| Fecha | Decisión reabierta | Motivo | Nueva redacción |
|-------|---------------------|--------|------------------|
| | | | |
