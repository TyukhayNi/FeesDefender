---
tipo: handoff
estado: consumido
creado: 2026-07-03
origen: sesión Cowork (decisiones de formato 02–03/07/2026)
destino: Claude Code — .claude/skills/escritos-judiciales/
consumido_por: "skill escritos-judiciales v1.1 (.claude/skills/escritos-judiciales/)"
migrado: "2026-07-19 (regla MEJORAS #77 / GOBERNANZA §5)"
---

# HANDOFF → Claude Code: escritos-judiciales v1.0 → v1.1

**Origen:** sesión Cowork 2026-07-03 (decisiones de formato confirmadas por Nikolai el 02 y 03/07).
**Destino:** `.claude/skills/escritos-judiciales/` en FeesDefender (y regenerar `dist/skills/escritos-judiciales.skill`).
**Fuente de los cambios:** los ficheros ya editados están dentro de `escritos-judiciales-v1.1b.skill` (outputs de la sesión Cowork; Nikolai puede pasarlo). Si no está disponible, aplicar los 4 cambios siguientes sobre v1.0:

## 1. Numeración de párrafos: número volado alineado por el punto
Sustituir en `hechos-cont` (sección «Subapartados — lista decimal continua», helper `sub()`, `pDoc()` y la extensión OOXML/python-docx) la francesa fija `left=0/hanging=425` (número a la izquierda) por:
- `lvlJc=right` (número alineado por el punto) + `suff=tab` + `ind left="0" hanging="113"` (0,2 cm)
- Aplicado en el nivel de `numbering.xml` **y** en el `pPr` de cada párrafo
- Motivo: con francesa fija el hueco número→texto varía con el nº de cifras y se rompe con 3 cifras; validado con 111 párrafos (W-02VND1 v24, 2026-07-02)
- Checklist: + ítem de verificación visual renderizando ordinales de 1/2/3 cifras

## 2. Índice documental (`idx-docs`): mismo esquema volado
Migrar de francesa 425/425 al esquema del punto 1. Separador tras `DOCUMENTO Nº XX`: dos puntos (`: `).

## 3. Regla nueva universal: prohibido el guion largo (em dash «—»)
Nueva subsección en «Reglas tipográficas obligatorias»: nunca «—» ni «--» en ninguna parte del escrito (cuerpo, índice, notas al pie, otrosíes). Sustituir por dos puntos, coma, paréntesis o punto y frase nueva. Capa dura al generar; `pase-de-estilo` solo como segunda red. + ítem en checklist.

## 4. Eliminada la tabla de cabecera
Suprimir la sección «Tabla de cabecera del escrito» (Mi ref. / Juzgado). El escrito arranca directamente con «AL JUZGADO DE PRIMERA INSTANCIA…». Instrucción expresa de no reintroducirla desde modelos antiguos.

## Meta
- Frontmatter: `version: "1.1"`
- CHANGELOG.md: entradas del 2026-07-03 (redactadas ya en el .skill)
- Tras commit: regenerar `dist/skills/escritos-judiciales.skill` y avisar a Nikolai para reinstalar en Cowork
