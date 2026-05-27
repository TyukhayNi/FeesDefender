---
description: Sincroniza un expediente concreto desde sudespacho.net al árbol local 05_CRM/
argument-hint: <case_id> [--dry-run]
allowed-tools: Bash, Read
---

Ejecuta el pull v2 de un expediente del CRM hacia su árbol local `00_Input/05_CRM/`.

Recibes como argumento: `$ARGUMENTS` — el case_id (`BaRR3 - Roser 39, 2º (W-030LFT) - Art 20 LAU`).

Pasos:

1. Verifica que el case_id existe localmente y tiene `meta.expediente_id` o `meta.expediente_judicial_id` en `_caso.md`.

2. Si no, sugiere al usuario vincular el expediente vía la UI antes de continuar.

3. Lanza el pull:

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m scripts.sync_sudespacho pull "$ARGUMENTS"
```

Si el usuario pasa `--dry-run`:

```powershell
cd "C:\Users\tnm33\Dev\FeesDefender"
python -m scripts.sync_sudespacho pull "$ARGUMENTS" --dry-run
```

4. Tras la ejecución:

- Si returncode = 0, lee `_caso.md` y resume:
  - `documents_total_crm` actualizado.
  - `linked_at` / `last_sync`.
  - Distribución por carpeta (`by_carpeta`).
- Si hay errores en `errors[]`, lístalos.
- Si returncode != 0, propón qué revisar (probable: PHPSESSID caducada → `/renovar-php`).

Pre-vuelo automático: comprueba antes de lanzar el pull si la sesión CRM está viva. Si está caducada, pide al usuario que ejecute `/renovar-php` y aborta.
