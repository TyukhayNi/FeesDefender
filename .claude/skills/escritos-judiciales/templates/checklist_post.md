# Checklist posterior — escrito procesal

Se rellena tras la presentación/resolución y se vuelca a `<ref>_post.jsonl` (vía
`registrar_uso.py --fase post`). Lo dispara la revisión programada
(`programar_revision.py`, escrito = presentación + 15 días, o al detectar la
versión `_FIRMADO`). Campos:

- **resultado**: admitido | inadmitido | estimado | desestimado | pendiente.
- **resolucion**: providencia/auto/sentencia y lo que fija.
- **correcciones_letrado**: qué reescribió el letrado frente al borrador (el
  detalle literal lo captura `capturar_delta.py` en `<ref>_delta.md`).
- **alegacion_no_prevista**: argumento/objeción que faltó o sobró.
- **valoracion**: 1-5 + nota breve.

Ejemplo de registro:

```bash
python scripts/registrar_uso.py escritos-judiciales "<ref>" checklist_post --fase post \
  --metricas '{"resultado": "estimado", "resolucion": "...", "alegacion_no_prevista": "...", "valoracion": 4}'
```
