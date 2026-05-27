---
description: Diagnóstico completo del entorno — venv, dependencias, modelos NLP, conectividad CRM/Drive
allowed-tools: Bash
---

Ejecuta el health check completo del proyecto:

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m scripts.health_check
```

El script verifica:

- Venv activo y dependencias instaladas (`requirements.txt`).
- Modelos spaCy cargables (`es_lg`, `ca_sm`, `en_lg`).
- Conectividad sudespacho.net (REST + legacy).
- Conectividad Drive E&V (rclone + Drive API).
- Existencia de `.env` con todas las variables requeridas.
- Permisos sobre `data/CASOS/` y `data/_plantillas/`.

Devuelve un resumen con el estado de cada bloque (OK / ⚠️ / ❌) y, si hay problemas, sugiere el comando exacto para resolver cada uno.

Si todos los bloques verdes, devuelve solo "Entorno OK" sin más detalle.
