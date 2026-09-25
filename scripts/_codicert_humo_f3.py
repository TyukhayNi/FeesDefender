"""Humo de F3 contra PRODUCCIÓN. No es un test: toca la red.

    python -m scripts._codicert_humo_f3 W-04AKM2 OVC <carpeta_de_trabajo>

Solo lecturas en Codicert —`listar`, `estados`, `certificado`, `descargar_adjunto` y
`credito` son GET— y **nada en el expediente ni en el CRM**: los íntegros se bajan a
`<carpeta_de_trabajo>` —fuera del repo— y los aportables se escriben ahí. Crédito
antes y después para acreditar que no gastó, sabiendo que la cuenta se mueve sola
(M-10 del plan de F3): acredita esta ventana, no el día.

Es la prueba que ningún doble da: el transporte real, los certificados reales y los
adjuntos reales, de extremo a extremo.

NO imprime datos de terceros: identificadores de envío, estados, páginas y avisos.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

from core import expedicion_certificada as exp

PLAZA = "Madrid"


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 3:
        print("uso: python -m scripts._codicert_humo_f3 <W-code> <REQ|OVC> <carpeta>")
        return 2
    w_code, tipo, carpeta = argv[0], argv[1], Path(argv[2])
    carpeta.mkdir(parents=True, exist_ok=True)

    # El transporte REAL —el que ningún doble sustituye aquí—, con el expediente
    # cambiado por la carpeta de trabajo y sin leer el CRM.
    real = exp.entorno_real(plaza=PLAZA, entorno="produccion")
    entorno = dataclasses.replace(real, raiz=carpeta, partes_de=lambda w: [],
                                  carpeta_certificados=lambda w: carpeta)
    antes = entorno.codicert.credito()
    print(f"acceso OK · {entorno.usuario} · crédito {antes} €")

    expedicion = exp.refrescar(w_code, tipo, entorno_exp=entorno)
    for envio in expedicion.cosechables:
        destino = carpeta / exp.nombre_canonico(envio.asunto, w_code, envio.id_envio)
        destino.write_bytes(entorno.codicert.certificado(envio.id_envio))
    resultados = exp.preparar_aportables(w_code, tipo, entorno_exp=entorno)
    fallos = 0
    for r in resultados:
        print(f"  {r.id_envio} · {r.canal} · {r.estado} · retiradas {list(r.retiradas)}")
        if r.motivo:
            print(f"      motivo: {r.motivo}")
        for a in r.avisos:
            print(f"      ⚠ {a}")
        fallos += r.estado == exp.PARADO

    despues = entorno.codicert.credito()
    print(f"crédito después {despues} € (gastado en esta ventana: {antes - despues})")
    if antes != despues:
        print("⛔ el crédito cambió en la ventana del humo: compruébalo en el portal "
              "(la plaza envía por su cuenta, M-10) antes de dar el humo por bueno")
        return 1
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
