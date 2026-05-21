---
description: Ejecuta la suite de pytest completa o un subconjunto
argument-hint: [ruta opcional al fichero/carpeta de tests]
allowed-tools: Bash
---

Ejecuta los tests del proyecto.

Si recibes argumento, ejecuta solo esa ruta:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m pytest -q --tb=short $ARGUMENTS
```

Si no hay argumento, ejecuta la suite completa:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m pytest -q --tb=no
```

Tras ejecutar:

- Si hay fallos, muestra el traceback resumido y propón el siguiente paso (qué fichero tocar).
- Si todo verde, devuelve solo "N/N verdes" y nada más.
