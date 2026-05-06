r"""
test_apikey_write.py -- Prueba si x-api-key funciona para escritura (POST).

Hipotesis: POST /api/element_register/colaboradores acepta x-api-key
en lugar de Authorization: Bearer JWT, igual que los endpoints GET.

Ejecutar desde PowerShell:
    cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"
    python -m scripts.test_apikey_write

El script lee SUDESPACHO_API_KEY del .env. No imprime la clave.
Solo muestra el codigo HTTP y el cuerpo de respuesta (sanitizado).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Cargar .env ──────────────────────────────────────────────────────────────
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("SUDESPACHO_API_KEY", "").strip()
BASE_URL = os.getenv("SUDESPACHO_BASE_URL", "https://api-crm-commons-pro.sudespacho.biz").rstrip("/")

if not API_KEY:
    print("❌ SUDESPACHO_API_KEY está vacía en el .env.")
    print("   Ve a tnm.sudespacho.net → Ajustes → API, copia la clave y pégala en .env.")
    sys.exit(1)

print(f"✅ API key cargada desde .env ({len(API_KEY)} caracteres)")
print(f"   Base URL: {BASE_URL}")

# ── Request ───────────────────────────────────────────────────────────────────
ENDPOINT = f"{BASE_URL}/api/element_register/colaboradores"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}
PAYLOAD = {
    "nombre": "TEST FEESDEFENDER BORRAR",
}

print(f"\n📤 POST {ENDPOINT}")
print(f"   Headers: x-api-key=<redacted>, Content-Type=application/json")
print(f"   Body: {json.dumps(PAYLOAD)}")
print()

try:
    resp = requests.post(ENDPOINT, headers=HEADERS, json=PAYLOAD, timeout=30)
except requests.RequestException as exc:
    print(f"❌ Error de red: {exc}")
    sys.exit(1)

# ── Resultado ─────────────────────────────────────────────────────────────────
print(f"── Respuesta ──────────────────────────────────────────────────────────")
print(f"   HTTP {resp.status_code}")

# Intentar parsear JSON (no imprime la API key, que no debería estar en la respuesta)
try:
    body = resp.json()
    # Si la respuesta incluye un ID, lo mostramos (útil para borrarlo después)
    printed = json.dumps(body, ensure_ascii=False, indent=2)
    # Truncar si es muy largo
    if len(printed) > 800:
        printed = printed[:800] + "\n… (truncado)"
    print(f"   Body (JSON):\n{printed}")
except Exception:
    text = resp.text[:800]
    print(f"   Body (texto): {text}")

print()

# ── Interpretación ────────────────────────────────────────────────────────────
if resp.status_code in (200, 201):
    print("🟢 RESULTADO: x-api-key FUNCIONA para escritura (POST).")
    print("   → Opción A viable. Podemos migrar todos los _rest_post a x-api-key")
    print("     y eliminar la dependencia de JWT en create/link.")
    print()
    print("⚠️  ACCIÓN MANUAL REQUERIDA: borrar el registro de prueba del CRM.")
    print("   Busca 'TEST FEESDEFENDER BORRAR' en Colaboradores y elimínalo.")
elif resp.status_code in (401, 403):
    print("🔴 RESULTADO: x-api-key NO tiene permisos para escritura (POST).")
    print("   → Dead end confirmado. Documentar en docs/DEAD_ENDS.md.")
    print("   → Pasar a Opción B: robustecer refresh token JWT.")
else:
    print(f"🟡 RESULTADO INESPERADO: HTTP {resp.status_code}.")
    print("   Revisa el body de la respuesta para determinar la causa.")
