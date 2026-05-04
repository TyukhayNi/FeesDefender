"""Diagnóstico: comprueba qué devuelven las rutas candidatas de CSRF."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

cookies = {
    "PHPSESSID":     os.getenv("SUDESPACHO_LEGACY_PHPSESSID", ""),
    "@token":        os.getenv("SUDESPACHO_LEGACY_JWT", ""),
    "@refreshToken": os.getenv("SUDESPACHO_LEGACY_REFRESH_TOKEN", ""),
}
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

paths = [
    "/tnm/gestion/extrajudiciales",
    "/tnm/gestion/colaboradores",
    "/tnm/gestion/expedientes_judiciales",
]

print(f"PHPSESSID: {cookies['PHPSESSID'][:8]}...")
print()

for path in paths:
    r = httpx.get(
        "https://tnm.sudespacho.net" + path,
        cookies=cookies,
        headers=headers,
        follow_redirects=True,
        timeout=15,
    )
    has_csrf  = "csrf_token" in r.text
    is_eplan  = "E-plan" in r.text[:500]
    title_s   = r.text.find("<title>")
    title_e   = r.text.find("</title>")
    title     = r.text[title_s+7:title_e].strip()[:60] if title_s >= 0 else "sin título"
    snippet   = r.text[:300].replace("\n", " ")

    print(f"PATH: {path}")
    print(f"  HTTP {r.status_code} | csrf_token={has_csrf} | E-plan={is_eplan}")
    print(f"  Título: {title}")
    print(f"  HTML inicio: {snippet}")
    print()
