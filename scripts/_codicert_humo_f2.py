"""Humo de F2 contra PRODUCCIÓN. No es un test: toca la red.

    python -m scripts._codicert_humo_f2 "W-04AKM2 - OVC"

Solo lecturas: `listar`, `estados` y `certificado` son GET. Comprueba el crédito
antes y después para acreditar que no gastó, y **no escribe nada** — ni en el
expediente ni en el CRM. Para eso está `codicert cosechar`.

El sandbox no sirve para esto: su `POST /usuarios/acceso` devuelve
`400 "Error interno, contacte con el administrador"` desde el 2026-09-21, que no es
«credenciales inválidas». Y de las siete plazas solo Madrid tiene credencial cargada.

NO imprime datos de terceros: solo identificadores de envío, códigos de estado y el
emisor, que es nuestro propio cliente.
"""
from __future__ import annotations

import sys

from core import certificado_lectura as cert
from core import codicert

PLAZA = "Madrid"
VENTANA = ("2026-09-01", "2026-09-30")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print('uso: python -m scripts._codicert_humo_f2 "<id_personalizado>"')
        return 2
    objetivo = argv[0]

    usuario, clave = codicert.credenciales(PLAZA, "produccion")
    ficha = codicert.acceso(usuario, clave, entorno="produccion")
    antes = codicert.credito(ficha, entorno="produccion")
    print(f"acceso OK · {usuario} · crédito {antes} €")

    envios = [e for e in codicert.listar(ficha, entorno="produccion",
                                         fecha_inicio=VENTANA[0], fecha_fin=VENTANA[1])
              if e.get("id_personalizado") == objetivo]
    print(f"envíos de {objetivo!r}: {len(envios)}")
    fallos = 0
    for e in envios:
        id_envio = str(e["id"])
        historico = codicert.estados(ficha, id_envio, entorno="produccion")
        codigos = [h.get("codigo") for h in historico]
        print(f"  {id_envio} · {e.get('tipo_titulo')} · estados {codigos}")

        pdf = codicert.certificado(ficha, id_envio, entorno="produccion")
        emisor = cert.leer_emisor(pdf)
        ok = cert.es_emisor_esperado(emisor, razon_social=cert.EMISOR_ESPERADO,
                                     usuario=usuario)
        # Control NEGATIVO en vivo: el mismo instrumento tiene que poder decir que no.
        # Sin él, un "OK" no distingue "verificado" de "el control no mira nada".
        otro = cert.es_emisor_esperado(emisor, razon_social="NO SOMOS NOSOTROS, S.L.")
        print(f"      emisor: {emisor.razon_social} / {emisor.usuario} → "
              f"{'OK' if ok else '⛔ NO COINCIDE'}   (control negativo: "
              f"{'bien' if not otro else '⛔ ACEPTA CUALQUIERA'})")
        acta = cert.paginas_de_acta(pdf)
        print(f"      acta: páginas {acta} de {_paginas(pdf)} "
              f"({len(pdf)} bytes)")
        if not ok or otro:
            fallos += 1

    despues = codicert.credito(ficha, entorno="produccion")
    print(f"crédito después {despues} € (gastado: {antes - despues})")
    if antes != despues:
        print("⛔ el humo GASTÓ crédito: algo salió de verdad")
        return 1
    if fallos:
        print(f"⛔ {fallos} envío(s) no verifican su emisor")
        return 1
    print("humo OK")
    return 0


def _paginas(pdf: bytes) -> int:
    from io import BytesIO

    from pypdf import PdfReader

    return len(PdfReader(BytesIO(pdf)).pages)


if __name__ == "__main__":
    raise SystemExit(main())
