#!/usr/bin/env python3
"""
Scaffolding de expedientes de litigio civil.

Crea el árbol de carpetas estándar del despacho y los documentos maestros
inicializados (PREPARACION_X.md y HECHOS_X.md), pre-cargados con la cabecera
del asunto y con las decisiones cerradas permanentes del despacho.

Uso:

    python scaffold_expediente.py \\
        --base-dir "/ruta/destino" \\
        --tipo-escrito demanda \\
        --referencia "REF-2026-001" \\
        --parte-representada "JUAN PÉREZ GARCÍA" \\
        --posicion actor \\
        --contraparte "PEDRO GÓMEZ LÓPEZ" \\
        [--fase-previa monitorio] \\
        [--procedimiento ordinario] \\
        [--juzgado "Juzgado de 1ª Instancia nº 3 de Madrid"] \\
        [--cuantia "12.345,67 €"] \\
        [--objeto "Resolución contractual"] \\
        [--cliente "Cliente AB"]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path


TIPOS_ESCRITO_VALIDOS = {
    "demanda",
    "contestacion",
    "recurso",
    "requerimiento",
    "tramite",
}

POSICIONES_VALIDAS = {
    "actor",
    "demandado",
    "recurrente",
    "recurrido",
    "remitente",
}

# Mapeo de fase previa a etiqueta de carpeta 01_ y 02_.
# Si no se pasa --fase-previa, se usan etiquetas genéricas.
FASE_PREVIA_MAP = {
    "monitorio": ("01_MONITORIO", "02_OPOSICION"),
    "demanda": ("01_DEMANDA", "02_REQUERIMIENTOS_PREVIOS"),
    "primera_instancia": ("01_PRIMERA_INSTANCIA", "02_SENTENCIA"),
    "requerimiento": ("01_REQUERIMIENTO_EXTRAJUDICIAL", "02_RESPUESTA_CONTRARIA"),
    "extrajudicial": ("01_ANTECEDENTES", "02_INTERCAMBIO_PREVIO"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea el árbol de carpetas y los documentos maestros de un expediente civil.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base-dir", required=True, help="Ruta donde se creará el expediente.")
    parser.add_argument(
        "--tipo-escrito",
        required=True,
        choices=sorted(TIPOS_ESCRITO_VALIDOS),
        help="Tipo de escrito procesal.",
    )
    parser.add_argument("--referencia", required=True, help="Referencia interna del despacho.")
    parser.add_argument(
        "--parte-representada",
        required=True,
        help="Nombre completo de la parte representada (sin DON/DOÑA).",
    )
    parser.add_argument(
        "--posicion",
        required=True,
        choices=sorted(POSICIONES_VALIDAS),
        help="Posición procesal de la parte representada.",
    )
    parser.add_argument(
        "--contraparte",
        default="",
        help="Nombre completo de la contraparte (sin DON/DOÑA).",
    )
    parser.add_argument(
        "--fase-previa",
        choices=sorted(FASE_PREVIA_MAP),
        default=None,
        help="Identifica la fase procesal previa para renombrar carpetas 01_ y 02_.",
    )
    parser.add_argument("--procedimiento", default="", help="Procedimiento (ordinario, verbal, monitorio, etc.).")
    parser.add_argument("--juzgado", default="", help="Juzgado, si se conoce.")
    parser.add_argument("--cuantia", default="", help="Cuantía del procedimiento.")
    parser.add_argument("--objeto", default="", help="Descripción breve del objeto del asunto.")
    parser.add_argument("--cliente", default="", help="Nombre del cliente (puede coincidir con parte representada).")
    return parser.parse_args()


def crear_arbol(base: Path, fase_previa: str | None) -> dict[str, Path]:
    """Crea el árbol de carpetas y devuelve un dict con las rutas relevantes."""
    if fase_previa:
        carpeta_01, carpeta_02 = FASE_PREVIA_MAP[fase_previa]
    else:
        carpeta_01, carpeta_02 = "01_ANTECEDENTES", "02_ACTUACION_CONTRARIA"

    subcarpetas = [
        "00_PREPARACION",
        carpeta_01,
        carpeta_02,
        "03_PRUEBA",
        "04_INTERNO",
        "05_BORRADORES",
    ]

    rutas: dict[str, Path] = {}
    for nombre in subcarpetas:
        ruta = base / nombre
        ruta.mkdir(parents=True, exist_ok=True)
        rutas[nombre] = ruta
    return rutas


def construir_preparacion(args: argparse.Namespace) -> str:
    hoy = _dt.date.today().isoformat()
    tipo_upper = args.tipo_escrito.upper()
    contraparte_linea = (
        f"- **Contraparte:** DON/DOÑA **{args.contraparte}**"
        if args.contraparte
        else "- **Contraparte:** _por completar_"
    )

    return f"""# PREPARACIÓN {tipo_upper} — {args.referencia}

> Documento maestro estratégico. Punto único de verdad del asunto.
> Toda decisión cerrada se consigna aquí. Cualquier modificación posterior debe reflejarse en este documento ANTES de tocar borradores.

---

## 1. Identificación del asunto

- **Referencia interna:** {args.referencia}
- **Tipo de escrito:** {args.tipo_escrito}
- **Procedimiento:** {args.procedimiento or "_por completar_"}
- **Cuantía:** {args.cuantia or "_por completar_"}
- **Juzgado:** {args.juzgado or "_por completar_"}
- **Parte representada:** DON/DOÑA **{args.parte_representada}**
- **Posición procesal:** {args.posicion}
{contraparte_linea}
- **Fecha de apertura:** {hoy}

---

## 2. Decisiones estratégicas cerradas

> Cada punto cerrado se marca con `[CERRADO]`. Lo abierto, con `[PENDIENTE]`.
> Las decisiones de los bloques 2.6 y 2.7 son convenciones permanentes del despacho — no se renegocian.

### 2.1. Arquitectura del escrito

- [PENDIENTE] Estructura: _por decidir_

### 2.2. Pretensión

- [PENDIENTE] Petitum principal: _por decidir_
- [PENDIENTE] Petitum subsidiario: _por decidir / no procede_

### 2.3. Intereses

- [PENDIENTE] Tipo: _por decidir_
- [PENDIENTE] Fecha de origen: _por decidir_ — fundamento: _por decidir_

### 2.4. Costas

- [PENDIENTE] Solicitud expresa con fundamento en art. 394 LEC.

### 2.5. Prueba

- [PENDIENTE] Documental: incluida con el escrito.
- [PENDIENTE] Pericial: _por decidir (si procede, cláusula doble vía 337.1 + 339 LEC)_
- [PENDIENTE] Perito propuesto: DON/DOÑA **_por designar_**
- [PENDIENTE] Testifical: _por decidir_
- [PENDIENTE] Interrogatorio de parte: _por decidir_

### 2.6. Estilo y formato (cerrado por convención del despacho)

- [CERRADO] Criterios formales TS Sala 1.ª (Times 12, márgenes 2,5 cm, interlineado 1,5, citas 10 pt cursiva sangría 1 cm).
- [CERRADO] DON/DOÑA + nombre en MAYÚSCULAS NEGRITA en toda mención.
- [CERRADO] Listas de 2.º nivel en formato a), b), c).
- [CERRADO] Listas jerárquicas 1., 1.1., 1.1.1.
- [CERRADO] Párrafos numerados correlativamente.
- [CERRADO] Nomen iuris con paréntesis único: `(en adelante, «el X»)`.
- [CERRADO] Sin trimembraciones gratuitas.
- [CERRADO] En civil siempre «desestimar», no «absolver».

### 2.7. Deontología (cerrado por convención del despacho)

- [CERRADO] Sin aportar correspondencia entre letrados (art. 21 EGAE, art. 5 CDCGAE). Revisión obligatoria del índice documental antes del cierre.

### 2.8. Decisiones específicas del asunto

- [PENDIENTE] _añadir según necesidad_

---

## 3. Arquitectura del escrito (esquema)

```
ENCABEZAMIENTO
PREVIO (opcional)
HECHOS
  PRIMERO — _por completar_
  SEGUNDO — _por completar_
FUNDAMENTOS DE DERECHO
  I. JURISDICCIÓN Y COMPETENCIA
  II. PROCEDIMIENTO
  III. LEGITIMACIÓN
  IV. POSTULACIÓN
  V. CUANTÍA
  VI. FONDO
  VII. INTERESES
  VIII. COSTAS
SUPLICO
OTROSÍES
```

---

## 4. Cronología de hechos

| Fecha | Hecho | Documento de respaldo |
|-------|-------|------------------------|
|       |       | DOC_NN                 |

---

## 5. Personas clave

| Nombre | Rol | Datos relevantes |
|--------|-----|------------------|
| DON/DOÑA **{args.parte_representada}** | {args.posicion} | |
| DON/DOÑA **{args.contraparte or "_contraparte_"}** | Contraparte | |

---

## 6. Índice documental

| DOC | Descripción | Origen | Fecha |
|-----|-------------|--------|-------|
| DOC_01 |  |  |  |
| DOC_02 |  |  |  |

> [PENDIENTE] Revisión deontológica del índice: verificar ausencia de correspondencia entre letrados antes del cierre.

---

## 7. Pendientes operativos

- [ ] _por añadir_

---

## 8. Histórico de decisiones reabiertas

| Fecha | Decisión reabierta | Motivo | Nueva redacción |
|-------|---------------------|--------|------------------|
|       |                     |        |                  |
"""


def construir_hechos(args: argparse.Namespace) -> str:
    tipo_upper = args.tipo_escrito.upper()
    return f"""# HECHOS {tipo_upper} — {args.referencia}

> Redacción literal aprobada por Hecho. Fuente de verdad textual para el escrito final.
> Cada Hecho es un módulo cerrado: título + texto. Se traspasa literal al .docx.

---

## HECHO PRIMERO. — _por completar_

**Estado:** [BORRADOR]

_texto pendiente_

---

## HECHO SEGUNDO. — _por completar_

**Estado:** [BORRADOR]

_texto pendiente_

---

<!-- Añadir tantos hechos como sea necesario, conservando la numeración ordinal en mayúsculas (TERCERO, CUARTO, etc.). -->

---

## Notas internas

> Espacio para observaciones del letrado que NO se trasladan al escrito final.

- _vacío_
"""


def main() -> int:
    args = parse_args()

    base = Path(args.base_dir).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)

    rutas = crear_arbol(base, args.fase_previa)

    preparacion = rutas["00_PREPARACION"] / f"PREPARACION_{args.tipo_escrito.upper()}.md"
    hechos = rutas["00_PREPARACION"] / f"HECHOS_{args.tipo_escrito.upper()}.md"

    preparacion.write_text(construir_preparacion(args), encoding="utf-8")
    hechos.write_text(construir_hechos(args), encoding="utf-8")

    print(f"[OK] Expediente creado en: {base}")
    print(f"[OK] Maestro estratégico: {preparacion.relative_to(base)}")
    print(f"[OK] Maestro de Hechos:   {hechos.relative_to(base)}")
    print("[OK] Subcarpetas:")
    for nombre, ruta in rutas.items():
        print(f"        - {ruta.relative_to(base)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
