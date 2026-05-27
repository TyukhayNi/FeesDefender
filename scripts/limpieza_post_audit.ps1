# Shim minimo. Toda la logica vive en scripts/limpieza_post_audit.py
# (Python maneja UTF-8 nativo; PowerShell 5.1 sin BOM choca con no-ASCII.)
Set-Location -Path "C:\Users\tnm33\Dev\FeesDefender"
python -m scripts.limpieza_post_audit
exit $LASTEXITCODE
