---
description: Ejecuta la suite de pytest completa o un subconjunto
argument-hint: [ruta opcional al fichero/carpeta de tests]
allowed-tools: Bash
---

Ejecuta los tests del proyecto.

Si recibes argumento, ejecuta solo esa ruta **en serie** (sin `-n`): sobre un fichero
suelto arrancar 12 workers cuesta más de lo que ahorra —17,0 s contra 11,9 s, medido el
2026-09-06— y además en serie los tracebacks se leen sin interleave.

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m pytest -q --tb=short $ARGUMENTS
```

Si no hay argumento, ejecuta la suite completa **en paralelo** (371 s → 94 s):

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m pytest -q --tb=no -n auto
```

Tras ejecutar:

- Si hay fallos, muestra el traceback resumido y propón el siguiente paso (qué fichero tocar).
- Si todo verde, devuelve solo "N/N verdes" y nada más.
