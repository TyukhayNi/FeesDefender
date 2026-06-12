# Solicitud de prueba (escrito procesal)

Es un **escrito presentable y firmable**, no una nota interna. Se genera con el **generador bundleado
`scripts/gen_solicitud.py`**, que reproduce el formato exacto de la plantilla del despacho (Times New
Roman 12, márgenes 2,5 cm, tabla de referencia en cabecera, comparecencia con `DIGO`, lista numerada,
`SUPLICO`, firma letrado/procurador, número de página centrado). Sigue las convenciones de
`escritos-judiciales`; no improvises el escrito a mano. Rellena el JSON y ejecuta:

```
python scripts/gen_solicitud.py datos.json "05_Procedimiento/SOLICITUD_PRUEBA_<REF>.docx"
```

## Esquema del JSON

```json
{
  "ref": "10/2025", "ref_procurador": "000000",
  "juzgado": "JUZGADO DE PRIMERA INSTANCIA Nº 1 DE EJEMPLO",
  "procedimiento": "PROCEDIMIENTO ORDINARIO - 100/2025",
  "procurador": "DOÑA PROCURADORA EJEMPLO",
  "cliente": "EV MMC SPAIN, S.L.U.",
  "pruebas": [
    {"tipo": "documental", "texto": "a fin de que se tengan por reproducidos…"},
    {"tipo": "mas_documental", "etiqueta": "MÁS DOCUMENTAL 1", "texto": "consistente en…"},
    {"tipo": "testigo", "nombre": "DOÑA CONSULTORA PRIMERA", "dni": "00000001A",
     "descripcion": "consultora de mi representada, persona que…",
     "citacion": "C/ … (Barcelona)", "movil": "+34 …", "email": "…"},
    {"tipo": "interrogatorio", "texto": "del demandado D. … (art. 301 LEC)."},
    {"tipo": "oficio", "texto": "al Colegio de API sobre la costumbre de la plaza."}
  ],
  "fecha": "23-01-2026", "letrado": "LETRADO EJEMPLO", "procurador_firma": "DOÑA PROCURADORA EJEMPLO"
}
```

Tipos de `pruebas[]`: `documental`, `mas_documental` (con `etiqueta`), `testigo` (con `dni`,
`descripcion`, `citacion`, `movil`, `email`), `interrogatorio`, `oficio`. Ejemplo completo en
`assets/ejemplo_solicitud.json`.

## Estructura (modelo del despacho)

1. **Encabezamiento**: tabla con `Mi ref.` y `Ref. procurador`; órgano y número de procedimiento.
2. **AL JUZGADO** + comparecencia del procurador en nombre de EV MMC SPAIN, S.L.U. (`DIGO,`).
3. **Fórmula de proposición**: notificada la providencia que convoca a la AP (art. 414.1 en relación
   con el art. 429 LECiv), se formula **PROPOSICIÓN DE LAS PRUEBAS** pertinentes y útiles.
4. **Lista numerada de medios de prueba:**
   1. **DOCUMENTAL** — por reproducida la que acompaña a demanda y contestación.
   2. **MÁS DOCUMENTAL** — documentos que se aportan ahora, **vinculándolos a la alegación
      complementaria** que los justifica (p. ej. el chat de WhatsApp aportado a la vista del motivo de
      incumplimiento alegado de contrario). Aquí encaja el documento designado y no incorporado, vía
      subsanación (art. 231) / art. 426.5 en relación con 265.3 LEC.
   3. **DECLARACIÓN en calidad de TESTIGO** de cada testigo: nombre en **MAYÚSCULAS NEGRITA**, **DNI**,
      cargo/relación con el objeto del pleito, y **CITACIÓN JUDICIAL** con dirección, móvil y email.
   4. **INTERROGATORIO** de la parte contraria (art. 301 LEC) cuando proceda.
   5. **OFICIOS** (p. ej. al Colegio de API para la costumbre de la plaza) cuando proceda.
5. **SUPLICO** de admisión + copias.
6. **Cierre**: "Es justicia que respetuosamente pido, a [fecha]" + `LTDO. [NOMBRE]` y
   `PROC. [NOMBRE]`.

## Reglas

- Nombres de personas (testigos, partes) en **MAYÚSCULAS NEGRITA**; **DNI** en negrita.
- Cada testigo lleva su **petición de citación judicial** con domicilio, móvil y email (la
  Administración del despacho gestiona las citaciones).
- Vincula la "más documental" a la **alegación complementaria** que la hace pertinente; así se sostiene
  su admisión pese a la preclusión del art. 269.
- Terminología propietario/buscador en el texto redactado; cita literal entre comillas puede conservar
  el término original.
- Los datos de los testigos (DNI, domicilio, contacto) se toman de la documental / CRM del expediente,
  anclados a fuente. Si faltan, se marca `[pendiente: dato de citación]` y se avisa al letrado.

## Defensiva

Si EV es demandada, la solicitud propone la prueba de descargo (testifical de los consultores que
acrediten la diligencia, documental del CRM/actividades, pericial si se discute valoración) y, en su
caso, el interrogatorio del actor. Ver `actora_defensiva.md`.
