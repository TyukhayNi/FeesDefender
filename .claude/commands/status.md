---
description: Checklist de apertura de sesión — git log, tests, check-legacy, [SIGUIENTE] de STATUS.md
allowed-tools: Bash, Read
---

Ejecuta el checklist de apertura del proyecto y resume el estado.

Pasos:

1. Ejecuta los 3 comandos del checklist de apertura (cada uno en una llamada Bash separada para que la salida sea legible):

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
git log --oneline -5
```

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m pytest -q --tb=no
```

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m scripts.sync_sudespacho check-legacy
```

2. Lee `STATUS.md` (las primeras 80 líneas) y extrae la sección `[SIGUIENTE]`.

3. Devuelve un resumen breve con:
   - Último commit (1 línea).
   - Resultado de la suite (N/N verdes o fallos).
   - Estado de PHPSESSID (válida / caducada).
   - `[SIGUIENTE]` actual.

Sin formato pesado — un párrafo breve y los puntos en líneas separadas si hay anomalías.
