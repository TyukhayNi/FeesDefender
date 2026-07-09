#!/usr/bin/env python3
"""Gestión de cuentas de google-despacho desde la terminal.

El flujo OAuth necesita navegador → el alta se hace aquí, nunca desde el server.

    python plugins/google_despacho_mcp/google_cli.py add            # autentica una cuenta (abre navegador)
    python plugins/google_despacho_mcp/google_cli.py list           # lista cuentas conectadas
    python plugins/google_despacho_mcp/google_cli.py remove EMAIL    # elimina el token local
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import google_auth  # noqa: E402


def cmd_add() -> None:
    print("Se abrirá el navegador para autenticar la cuenta (SOLO LECTURA de Drive)...")
    email = google_auth.add_account()
    print(f"OK · cuenta conectada: {email}")
    print(f"Token guardado en: {google_auth.tokens_dir() / (email + '.json')}")


def cmd_list() -> None:
    accounts = google_auth.list_account_emails()
    if not accounts:
        print("(sin cuentas conectadas)")
        return
    print("Cuentas conectadas:")
    for a in accounts:
        print(f"  - {a}")


def cmd_remove(email: str) -> None:
    if google_auth.remove_account(email):
        print(f"Token eliminado: {email}")
        print("Revoca también en https://myaccount.google.com/permissions "
              "si quieres invalidarlo en Google.")
    else:
        print(f"No existe token para: {email}")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    cmd = args[0]
    if cmd == "add":
        cmd_add()
    elif cmd == "list":
        cmd_list()
    elif cmd == "remove":
        if len(args) < 2:
            print("Uso: python google_cli.py remove EMAIL")
            sys.exit(1)
        cmd_remove(args[1])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
