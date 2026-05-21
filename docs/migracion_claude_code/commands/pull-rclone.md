---
description: Lanza un pull rclone del Drive E&V para un caso concreto, con flags blindados
argument-hint: <case_id o folder URL>
allowed-tools: Bash, Read
---

Ejecuta un pull rclone sobre una carpeta del Drive E&V con los flags que el proyecto requiere obligatoriamente.

Recibes como argumento: `$ARGUMENTS` — o un case_id (`BaRS10 - ...`) o una URL de Drive.

Pasos:

1. Si el argumento es una URL, extrae el folder ID y resuelve el case_id desde `core/intake_drive.py` (o pide confirmación al usuario).

2. Verifica que el caso existe en `data/CASOS/<ciudad>/<case_id>/` antes de continuar.

3. Lanza rclone con los flags obligatorios:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
rclone copy gdrive_ev: "data\CASOS\<ciudad>\<case_id>\00_Input\01_Drive EV" `
  --drive-team-drive <team_id> `
  --drive-root-folder-id <folder_id> `
  --drive-skip-shortcuts `
  --ignore-size --ignore-checksum --inplace `
  --retries 3 --retries-sleep 5s `
  -vv
```

Flags obligatorios y por qué (NO omitir nunca):

- `--drive-skip-shortcuts` — evita `exit 1` por dangling shortcuts heredados de consultores rotados.
- `--ignore-size --ignore-checksum --inplace` — destino Drive for Desktop (`G:\Unidades compartidas\...`); sin estos flags rclone reporta falsamente "corrupted on transfer".
- `--retries 3 --retries-sleep 5s` — resiliencia frente a rate-limit de la Drive API (cuota compartida del OAuth client).
- `-vv` — logging detallado en caso de fallo.

4. Si rclone termina con returncode != 0, examina el stderr (debe estar UTF-8 íntegro) y propón qué revisar.

5. Si termina OK, lista los ficheros descargados:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
Get-ChildItem -Path "data\CASOS\<ciudad>\<case_id>\00_Input\01_Drive EV" -Recurse | Measure-Object Length -Sum
```

y devuelve un resumen: N ficheros, X MiB totales.

Si no tienes claro el team_id o folder_id, consúltalo con el helper:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python scripts\diag_drive_autofill.py "<URL o folder ID>"
```
