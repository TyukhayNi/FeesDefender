# Checklist post — engel-volkers (Fase 1)

Formulario brevísimo que el asistente ofrece **al cerrar el trabajo de un asunto** en el que se usó el contexto de cliente E&V. Una sola pregunta; si el letrado declina, no se insiste ni se escribe nada.

## Pregunta al letrado

> **¿El contexto de cliente de E&V fue correcto y completo, y se activó cuando debía?**
> Si algo falló, dime qué (sociedad equivocada, tipología, Market Center que faltó, o que la skill se activó cuando no tocaba / no se activó cuando sí).

## Cómo se registra

Con la respuesta, el asistente escribe **una línea** en `logs/<ref>_post.jsonl` (esquema en `logs/README.md`). En PowerShell:

```powershell
$dir = "C:\Users\tnm33\despacho-skills\engel-volkers"   # ajusta si está en otra ruta
$ref = "W-XXXXXX"
$rec = @{ ts=[DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"); skill="engel-volkers";
          ref=$ref; fase="post"; contexto_correcto=$true; "faltó"=""; "activó_cuando_debía"=$true;
          nota="" } | ConvertTo-Json -Compress
Add-Content "$dir\logs\$($ref)_post.jsonl" -Value $rec -Encoding UTF8
```

Rellena `contexto_correcto`, `activó_cuando_debía` (true/false), `faltó` y `nota` según la respuesta del letrado.
