# scripts/_codicert_humo.py
"""Humo del transporte contra el SANDBOX. No es un test: toca la red y gasta saldo.

    python -m scripts._codicert_humo

Hace solo lecturas y una sonda de validación que NO puede salir —`pais` fuera de su
enum—, y comprueba el crédito antes y después para acreditar que no se gastó nada.
"""
from __future__ import annotations

from core import codicert


def main() -> int:
    usuario, clave = codicert.credenciales(None, "sandbox")
    ficha = codicert.acceso(usuario, clave, entorno="sandbox")
    print(f"acceso OK · ficha de {len(ficha.token)} caracteres · vence {ficha.vence}")

    antes = codicert.credito(ficha, entorno="sandbox")
    print(f"crédito antes ... {antes} €")

    total = sum(1 for _ in codicert.listar(ficha, entorno="sandbox"))
    print(f"envíos listados . {total}")

    try:
        codicert.enviar_burofax(
            ficha, destinatario={"nombre": "SONDA NO ENVIAR", "pais": "Francia"},
            adjuntos=[], asunto="", cuerpo="", id_personalizado="SONDA",
            entorno="sandbox")
        print("⛔ la sonda NO fue rechazada: revisa el pestillo antes de seguir")
        return 1
    except codicert.CodicertDatosInvalidosError as e:
        print(f"sonda rechazada como se esperaba · campos: {sorted(e.campos)}")

    despues = codicert.credito(ficha, entorno="sandbox")
    print(f"crédito después . {despues} €  (gastado: {antes - despues})")
    if antes != despues:
        print("⛔ la sonda GASTÓ crédito: algo salió de verdad")
        return 1
    print("humo OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
