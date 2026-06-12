# Checklist previo — escrito procesal

Se rellena al iniciar la redacción y se vuelca a `<ref>_pre.jsonl` (vía
`registrar_uso.py --fase pre`). Campos:

- **objetivo**: qué pretende el escrito (petitum principal en una frase).
- **tipo**: demanda | contestacion | reconvencion | recurso | requerimiento | escrito_tramite.
- **frentes**: argumentos/motivos principales que se van a sostener.
- **riesgos**: flancos previsibles (admisiones propias, prescripción, legitimación…).
- **prueba_clave**: documental/pericial/testifical de la que depende el éxito.

Ejemplo de registro:

```bash
python scripts/registrar_uso.py escritos-judiciales "<ref>" checklist_pre --fase pre \
  --metricas '{"objetivo": "...", "tipo": "demanda", "frentes": ["..."], "riesgos": ["..."], "prueba_clave": ["..."]}'
```
