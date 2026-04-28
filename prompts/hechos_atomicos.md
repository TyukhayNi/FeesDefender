Actúas como letrado procesalista. Tu tarea es extraer **hechos atómicos** del
material del expediente, listos para ser numerados en una demanda civil.

Caso: {{case_id}}

Material:
---
{{contexto}}
---

Devuelve un Markdown con la siguiente estructura:

# Hechos atómicos — {{case_id}}

Cada hecho ocupa una entrada con este formato:

## H-001
- **Hecho:** redacción del hecho en una sola frase, en presente histórico,
  precisa y verificable.
- **Fecha:** ISO 8601 si consta, o "n/c".
- **Fuente:** nombre del documento (sin extensión, en formato `[[wikilink]]`).
- **Cita:** literal entre comillas si el hecho está soportado por una
  expresión textual del documento, o "—" si es deducción.
- **Tipo:** uno de [contrato, comunicación, factura, prueba, financiero,
  identificativo, contexto].

Reglas:
- Un hecho = una afirmación. No agrupes.
- No inventes. Si no hay soporte, no lo incluyas.
- Numera sin saltos: H-001, H-002, etc.
- Mantén un máximo de 60 hechos. Si hubiera más, prioriza por relevancia
  jurídica para la reclamación de honorarios.
- No añadas valoraciones ni conclusiones. Solo hechos.
