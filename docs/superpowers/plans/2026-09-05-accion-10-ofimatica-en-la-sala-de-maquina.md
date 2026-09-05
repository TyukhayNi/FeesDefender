---
titulo: "Los `.doc` dejan de ser ilegibles: ruta `ofimatica` en la sala de máquina"
fecha: 2026-09-05
estado: implementado
rev: "1"
relacionado: "MEJORAS #61 · PLAN fila #21 acción 10 · [SIGUIENTE-DOC-LIBREOFFICE]"
---

# Los `.doc` dejan de ser ilegibles: ruta `ofimatica` en la sala de máquina

> Plan corto de una pieza pequeña con un daño concreto: en W-02MA0R la demanda del juicio
> ordinario existía solo como `ordinario_vuelta_comprador.doc` y la sala de máquina la
> dejaba en `sin_soporte`, sin PDF, sin MD y sin decir por qué. Radio de daño: no decide
> quién escribe ni destruye datos → **una ronda**, sobre el diff (§4).

## 1. Qué se cambia y qué no

**Se cambia.** `core/sala_maquina.clasificar_ruta` gana una ruta, `ofimatica`, para lo que
LibreOffice abre como Writer/Impress y hoy no tenía camino: `.doc`, `.dot`, `.odt`, `.ott`,
`.ppt`, `.pps`, `.pptx`, `.odp`. El documento se convierte a PDF con `soffice --headless`
(`core/ofimatica_a_pdf.py`) y **sigue por el camino PDF de siempre**: si el PDF trae capa de
texto suficiente se persiste en `01_OCR/` como buscable (custodia, igual que el producto de
la escalera) y pasa por `_split_o_md` con método `ofimatica`; si no la trae —un `.doc` que
envuelve un escaneo— baja a la escalera de OCR sobre el intermedio.

**No se cambia.** `.docx` y `.rtf` siguen en `nativo` (extractor determinista propio): moverlos
cambiaría el MD de los casos ya hechos sin ganar nada. Tampoco se toca la escalera, el split
ni la cobertura: la ruta nueva produce las mismas filas que las demás.

## 2. Las tres decisiones que no son detalle

1. **Verificar por resultado, nunca por código de salida.** `soffice` devuelve 0 en más de un
   caso en que no ha escrito nada (perfil bloqueado por una instancia abierta, filtro
   ausente). `convertir` exige que `<outdir>/<stem>.pdf` exista con bytes; si no,
   `ConversionFallida` con `rc` y el `stderr` recortado.
2. **Perfil de usuario efímero** (`-env:UserInstallation=file:///…`). Sin él, con LibreOffice
   abierto en pantalla la orden headless se pega a esa instancia y termina sin convertir.
   Medido en seco antes de escribir (`C:\t\soffice_prueba`): `.docx→.doc` 6,3 s en frío,
   `.doc→pdf` 1,5 s, texto recuperable con pypdf.
3. **La ausencia del conversor se DICE, no se disfraza.** Sin `soffice` la fila es
   `sin_soporte` con la causa en la nota («sin convertir: LibreOffice (soffice) no
   encontrado…»), nunca «sin soporte para esta extensión»; y `plan`/`apply` avisan en alto
   antes de la corrida (`_avisar_ofimatica_sin_conversor`). No aborta: el aislamiento por
   documento ya cubre el lote, pero el aviso evita el footgun de `MAX_INTENTOS` (tres
   corridas sin conversor agotarían los intentos y el documento se saltaría «en verde»).

**Y una cuarta, que la impuso el trinquete.** La primera versión creaba `01_OCR/` desde
`sala_maquina` (`mkdir` + `shutil.move` del intermedio) y `tests/test_escritura_censo.py` subió
a 89/88. La forma correcta era la de `ocr_pdf`: el conversor escribe **directamente** en
`01_OCR/<slug>.pdf` y crea la carpeta él (`core/ofimatica_a_pdf.py` está fuera de la lista de
productores por la misma razón que `core/anon/ocr.py` e `imagen_a_pdf.py`: escribe donde le
dicen). Si el PDF no trae texto, se aparta a un temporal y la escalera vuelve a ocupar el
destino. El censo de `sala_maquina` queda en 13, como estaba.

Localización del binario, en orden: `FEESDEFENDER_SOFFICE` (si apunta a un fichero), `soffice`
en el PATH, las dos rutas de instalación habituales de Windows. `None` es respuesta válida.

## 3. Pruebas

`tests/test_sala_maquina_ofimatica.py` — O1 enrutado (9 extensiones + las que no cambian +
`plan()` real sobre un `.doc`); O2 `localizar_soffice` (variable, ausencia); O3 `convertir`
con un `soffice` falso que sale 0 sin escribir, o escribe un PDF vacío; O4 conversión
correcta con perfil efímero y `--headless` en la línea; O5 `ejecutar` persiste PDF+MD con
método `ofimatica`; O6 sin LibreOffice la fila dice «soffice» y no se escribe nada; O7 el
fallo de uno no tumba al siguiente; O8 el PDF sin texto baja a la escalera; O9 el CLI cuenta
la ruta y avisa; O10 (`slow`) LibreOffice **real** sobre `tests/_fixtures/ofimatica/
encargo_prueba.doc` (generado con python-docx → soffice, texto neutro), se salta si no está.

Docs tocados: `SKILL.md` de `organizar-sala-maquina` (rutas y aviso), CHANGELOG 1.5,
`RUNBOOK_APERTURA_EXPEDIENTE.md` `[APER-21]`, `MEJORAS_FUTURAS.md` #61 (`[RESUELTO]` el punto
`.doc`; los otros dos siguen en backlog), `PLAN.md` fila 21 acción 10.

**Fuera, con nombre:** Excel/Calc siguen en `nativo` vía pandas; `.pages`/`.wpd` no entran
(sin disparador); el texto que pypdf saca de un PDF de LibreOffice puede partir los
diacríticos («cancio n») —es del extractor, no de la conversión— y la calidad lo marca como
cualquier otro PDF.
