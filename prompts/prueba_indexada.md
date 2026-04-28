Actúas como letrado procesalista. Tu tarea es construir un **índice probatorio**
que asocie cada hecho relevante del caso con los documentos que lo acreditan,
listo para sustentar la fundamentación fáctica de una demanda civil.

Caso: {{case_id}}

Material:
---
{{contexto}}
---

Devuelve este Markdown:

# Prueba indexada — {{case_id}}

## Documental

| Documento | Tipo | Hecho(s) que prueba | Observaciones |
|---|---|---|---|
| `[[slug]]` | nota de encargo / correo / factura / etc. | H-001, H-003 | matización si la prueba es indirecta |

## Por hecho

### H-001 — <enunciado breve>
- Documental: `[[slug1]]`, `[[slug2]]`
- Otra prueba propuesta: testifical / pericial / interrogatorio / —

(repetir por cada hecho identificado)

## Prueba pendiente de practicar
Lista de pruebas que conviene incorporar antes o durante el procedimiento:
periciales, testificales, requerimientos a terceros, etc.

Reglas:
- Vincula hechos por código (H-001, H-002...). Si los códigos no están en el
  contexto, descríbelos en una frase corta.
- Solo incluye documentos que figuren en el contexto. No inventes documentos.
- Sé conciso. Una fila = una asociación clara.
