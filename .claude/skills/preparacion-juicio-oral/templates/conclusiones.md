# Plantilla — Documento de conclusiones (modo soporte letrado)

Documento único integrado: I. Hechos no controvertidos (tabla); II. Hechos controvertidos (tabla); III. Conclusiones (bullets); IV. Petitum.

## Formato

- Arial 12 pt, interlineado 1,25, márgenes asimétricos (2,5/2/2,5/3,5 cm) — modo soporte letrado.
- Encabezados de bloque con fondo gris tenue (10 %) y línea inferior fina.
- Tabla I (no controvertidos): cabecera gris 25 %, filas alternas gris 5 %, columnas: Nº / Hecho / Posición del demandado / Prueba / Estado.
- Tabla II (controvertidos): primeras dos columnas (Nº + Hecho controvertido) con sombreado naranja tenue; columnas: Nº / Hecho controvertido / Tesis actora / Tesis demandada / Fuente probatoria.
- Citas literales de AP debajo del hecho en su celda: cursiva 9 pt color gris oscuro, formato `[mm:ss, Atribución] «texto»`.
- Atribuciones tipificadas: `Magistrado` | `Letrado actora` | `Letrado demandada`. Sin nombres personales.

## Estructura del JSON

Ver `caso_ejemplo.json`. Campos clave:

- `hechos_no_controvertidos[]` con objetos `{n, hecho, posicion_demandado, prueba, estado, cita_ap[]}`.
- `hechos_controvertidos.filas[]` con objetos `{n, hecho, tesis_actora, tesis_demandada, fuente_probatoria, cita_ap[]}`.
- `cita_ap[]` = array de `{timestamp, atribucion, texto}`. Si se omite, la celda solo muestra el hecho.
- `conclusiones[]` con `{head, body[]}`.
- `petitum[]` con líneas cortas.

## Notas

- El cuadro tabular es solo de soporte letrado: nadie más lo ve. No es escrito procesal Sala 1ª TS.
- Si la AP fue activa y fijó hechos en sala, se incluyen las citas literales como prueba de la fijación. Si no hubo fijación expresa, `cita_ap` se omite.
- Los hechos no controvertidos también pueden tener cita (admisión expresa del adversario) o no (admisión implícita por la contestación).
