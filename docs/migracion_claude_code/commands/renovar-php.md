---
description: Renueva PHPSESSID + @token + @refreshToken de sudespacho.net en .env
allowed-tools: Bash, Edit, Read
---

Renovación de las 3 cookies de sudespacho.net necesarias desde 2026-05-04.

Pasos:

1. Verifica primero si las cookies actuales aún funcionan:

```powershell
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
python -m scripts.sync_sudespacho check-legacy
```

2. Si están vivas, no hacer nada — informa al usuario.

3. Si están caducadas, instruye al usuario:

> Abre Chrome → https://tnm.sudespacho.net → login si hace falta → DevTools (F12) → Application → Cookies → tnm.sudespacho.net → copia los valores de:
>   - PHPSESSID
>   - @token
>   - @refreshToken
>
> Pégamelos aquí en el chat (uno por línea, formato `NOMBRE=valor` o solo el valor) y los meto en `.env`.

4. Tras recibir los valores, edita `.env`:
   - Sustituye las 3 líneas correspondientes.
   - **Nunca** mostrar los valores completos en la respuesta — solo confirmar "actualizado" y los últimos 4 caracteres para verificación.

5. Re-ejecuta `check-legacy` para confirmar que funcionan.

Si el usuario ya pega valores en el primer mensaje, salta los pasos 1-3.

Nota crítica de seguridad: no dejes los valores en logs, en commit messages, ni en docs/. Si por error los pegas en un fichero rastreado, ejecuta `git restore <fichero>` antes de cualquier commit.
