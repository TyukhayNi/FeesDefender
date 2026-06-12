# Formato de la minuta de audiencia previa

La minuta es el **guion del letrado para el acto**. Estructura canónica = las ocho finalidades de la
audiencia previa, en orden procesal (arts. 415→429 LEC). Los bloques 1–3 se redactan en **lenguaje
llano y visual** (se leen en voz alta en sala); la fijación de hechos (bloque 6) va en **tablas**.

## Plantilla visual (confirmada por el despacho)

- Fuente **Arial 12**; interlineado **1,25**; espaciado posterior 4 pt.
- Márgenes A4 **2,5 / 2,5 / 3,5 / 2 cm** (sup/inf/izq/der). El izquierdo amplio deja sitio para
  anotar a mano en sala.
- **Cabecera de bloque** sombreada (gris `D9D9D9`) con borde inferior; texto en negrita 12 pt y el
  artículo entre paréntesis en cursiva 10 pt.
- Bajo los bloques que se leen: `[ PARA LEER EN SALA ]` en 9 pt cursiva gris.
- Subpuntos **numerados jerárquicos** (`1.1.`, `3.1.1.`), con viñeta `➤` en los puntos de lectura y
  `▸` para los subtítulos temáticos. Sangría por nivel (0,5 / 1,0 / 1,5 cm).
- Tablas de hechos: cabecera gris 25 % (`BFBFBF`), filas alternas gris 5 % (`F2F2F2`).
- Número de página centrado, Arial 12, en el pie.

El script `scripts/gen_minuta.py` aplica todo esto. Markup inline en los textos: `**negrita**`,
`_cursiva_`.

## Los ocho bloques

1. **Conciliación (art. 415).** ¿Hay propuesta? Postura del despacho; umbral de acuerdo lo fija el
   letrado. Mención de la vía extrajudicial previa.
2. **Cuestiones procesales (art. 416).** Las propias (normalmente ninguna) y las observaciones a la
   contestación (p. ej. falta de precisión de la nulidad como indefensión, no como defecto de la
   demanda).
3. **Alegaciones complementarias y aclaratorias (art. 426).** El corazón: **causa de pedir**,
   transparencia/conocimiento, mala fe, base de cálculo. En lenguaje llano.
4. **Hechos nuevos o de nueva noticia (art. 426.4).**
5. **Impugnación y aportación de documentos (art. 427).** Impugnaciones de autenticidad/pertinencia y
   aportación/subsanación de documentos designados y no incorporados (arts. 231, 426.5, 265.3 LEC).
6. **Fijación de los hechos (art. 428).** TABLA I (no controvertidos) + TABLA II (controvertidos, con
   posición de cada parte y prueba). Nota final separando lo jurídico de lo fáctico.
7. **Proposición de prueba (art. 429).** Resumen (el escrito formal es la solicitud de prueba).
8. **Señalamiento del juicio (art. 429.2).**

> Adapta los bloques a la **perspectiva** (actora/defensiva): ver `actora_defensiva.md`.

## Esquema del JSON que consume `gen_minuta.py`

```json
{
  "cabecera": {
    "lineas": [
      "Procedimiento Ordinario 100/2025 — Juzgado de 1ª Inst. nº 1 de Ejemplo",
      "EV MMC SPAIN, S.L.U. (actora) c. D. … y Dña. …",
      "Audiencia previa: 11/06/2026, 09:30 — Cuantía: 43.076 €"
    ]
  },
  "bloques": [
    {
      "num": "1", "titulo": "CONCILIACIÓN", "articulo": "art. 415 LEC", "leer": true,
      "items": [
        {"texto": "**1.1.** ➤ No hay propuesta de la otra parte.", "nivel": 0}
      ]
    },
    {
      "num": "6", "titulo": "FIJACIÓN DE LOS HECHOS", "articulo": "art. 428 LEC",
      "tablas": [
        {
          "titulo": "TABLA I — HECHOS NO CONTROVERTIDOS",
          "cabecera": ["Nº", "Hecho", "Soporte"],
          "anchos_cm": [1.0, 10.5, 4.0], "size": 11,
          "filas": [["1", "…", "Doc. 2 demanda"]]
        },
        {
          "titulo": "TABLA II — HECHOS CONTROVERTIDOS",
          "cabecera": ["Nº", "Hecho controvertido", "Posición de EV", "Posición del demandado", "Prueba EV"],
          "anchos_cm": [0.8, 3.2, 4.6, 3.4, 3.5], "size": 10,
          "filas": [["1", "…", "…", "…", "…"]]
        }
      ],
      "nota": "_Cuestión jurídica, no fáctica:_ la causalidad … se resuelve por interpretación literal (art. 1281 CC)."
    }
  ]
}
```

Campos: `items[].nivel` (0/1/2 → sangría), `items[].sub:true` añade espacio antes (subtítulos `▸`).
Las tablas solo se usan en el bloque 6, pero el esquema las admite en cualquier bloque.

## Regla de fijación de hechos

- **No controvertidos:** solo lo que ambas partes admiten o no niegan. No incluyas como pacífico lo
  que es el núcleo del litigio (p. ej. la *eficacia causal* en una vuelta). Ancla cada hecho a su
  documento.
- **Controvertidos:** un hecho por fila, con la tesis de cada parte y la prueba con que EV lo sostiene.
- **Cuestión jurídica ≠ hecho:** validez de cláusula, devengo objetivo, base de cálculo de derecho →
  nota final, no fila de prueba.
