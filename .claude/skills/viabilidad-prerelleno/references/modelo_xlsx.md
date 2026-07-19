# Modelo del fichero .xlsx (4 hojas) — mapa para el pre-relleno

> El fichero es **uno solo por expediente** y funciona como **BITÁCORA append-only**. La Skill A escribe en `INFORMACION` (cabecera, equipo, importes, hitos, actividades), en `PREGUNTAS` (columnas del LLM) y en `AVISOS LLM`. **No escribe** VIABILIDAD, ni el recuadro ejecutivo `B48`, ni la hoja `BITACORA` (eso es Skill B / el abogado).
>
> Forma de trabajar: **partir de `assets/plantilla_informe_viabilidad.xlsx`** (ya trae formato, fórmulas, semáforo condicional, validaciones y protección) y **rellenar valores con `scripts/render_informe.py`**. No reconstruir el formato desde cero (rompería el semáforo y la protección).

## Hoja `INFORMACION` (la lee el CFO) — mapa de celdas
- `E4` FECHA · `E5` REF con patrón `<equipo> - <dirección> (<id_go>) - <etiqueta tipo>`.
- `E6` DIRECTOR CAPTADOR · `E7` ASESOR CAPTADOR · `E8` DIRECTOR BUSCADOR · `E9` ASESOR BUSCADOR. Formato **`Apellido, Nombre`**.
- `E11` OBSERVACIONES = etiqueta corta del tipo de caso (p. ej. `VUELTA`).
- `H12` MOTIVOS DE IMPAGO = frase telegráfica EN MAYÚSCULAS (postura del deudor). **Regla de relleno: vacío por defecto; se rellena solo si hay postura del deudor documentada y anclada a fuente** (aplica también a VUELTA — reconcilia handoff + caso [inmueble]). Solo tiene sentido en `BAD_DEBT` y `NEGATIVA_*`; en defensivos, vacío.
- Importes (mantener fórmulas): `H13` PRECIO · `E14` % · `H14` (fórmula) · `H15` pagos · `H16` (fórmula) · `H17` propuesta · `H18` (fórmula).
- **VIABILIDAD**: `E21` JURÍDICO (desplegable semáforo `verde/amarillo/rojo` + formato condicional) y `E22` FINANZAS. **En el pre-relleno SIEMPRE se dejan en blanco.**
- **DATOS OPERACIÓN**: 14 hitos `B25:B38`, score en `F` (merge `F:G`), fecha en `H`. `F39` TOTAL = `=SUM(F25:G38)` (no tocar). Ver `hitos_derivacion.md`.
- **ACTIVIDADES**: `F42:F45` numéricos.
- **Recuadro ejecutivo** `B48` (merge grande, borde grueso): **lo escribe la Skill B**, no la A. Dejar vacío.

## Hoja `PREGUNTAS` (hoja de trabajo/evidencia — el CFO NO la lee)
Columnas (fila 3 cabecera, fila 4 descriptor en cursiva — no tocar):
`B SECCIÓN · C ID · D PREGUNTA · E NOTAS LETRADO · F OBJETIVO PROBATORIO · G TIPO · H FUENTE PROBABLE · I RESPUESTA · J CITA/FUENTE · K CONFIANZA · L HITO · M ¿PENDIENTE ENTREVISTA?`

Reparto:
- **Fijo de plantilla (NO TOCAR)**: B, C, D, F, G, H, L.
- **El ABOGADO** (en la entrevista): E (NOTAS LETRADO). La Skill A la deja vacía.
- **Prerrellena la Skill A**: I (RESPUESTA, desde documento), J (CITA/FUENTE, rastro `[doc: fichero] "cita"`), K (CONFIANZA: `alta/media/baja`, desplegable), M (¿PENDIENTE?: `sí/no`, desplegable).
- Hoja **protegida**: editables solo E, I, K, M (y J por el render). El resto bloqueado. `autoFilter` activo en `B3:M88`.
- Las filas con `M=sí` hacen de **guion de entrevista** (Opción 1: hoja única, sin pestaña de huecos aparte).

## Hoja `AVISOS LLM` (capa de trabajo — el CFO NO la ve)
Columnas: `B Nº · C TIPO · D AVISO · E IMPACTO (hito/decisión) · F FUENTE/RASTRO · G SEVERIDAD (alta/media/baja) · H ACCIÓN SUGERIDA · I ¿SUBE AL RECUADRO CFO? (sí/no) · J ESTADO (abierto/resuelto)`. La Skill A vuelca aquí cuantía a conciliar, riesgos (despatrimonialización), pruebas débiles, documentos faltantes y el recuento de preguntas pendientes de entrevista. **No borra** observaciones: el abogado decide en `I` qué sube al recuadro. Estado inicial = `abierto`; `¿SUBE?` lo deja la Skill A en `no` por defecto (lo decide el abogado), salvo banderas de severidad alta de cuantía/riesgo, que puede sugerir `sí`.

## Hoja `BITACORA` (la lee el CFO — registro append-only)
Columnas: `FECHA · FASE · ACTOR (de→a) · QUÉ SE PIDE/DECIDE · IMPORTE · RESULTADO/ESTADO`. La Skill A **solo añade la primera entrada** del ciclo: `Pre-relleno documental · Administración/LLM → expediente · "Carga inicial de hitos desde 00_Input. Viabilidad en PENDIENTE." · — · Pendiente entrevista`. El resto de entradas las añade Skill B / el abogado.

## Reglas técnicas del .xlsx (no romper)
- **Semáforo**: color en `bgColor` con alfa `FF`, forma `<patternFill><bgColor rgb="FFxxxxxx"/></patternFill>`. Por eso se parte de la plantilla y no se regenera el formato condicional.
- **Celdas combinadas**: escribir siempre en la celda ancla (top-left). Cuidado con filas con dos merges.
- **Eliminar/añadir hitos**: reajustar a mano la fórmula del TOTAL (openpyxl no la corrige).
- **Protección**: `Protection(locked=False)` en editables + `ws.protection.sheet=True`, dejando `autoFilter/sort` permitidos.
