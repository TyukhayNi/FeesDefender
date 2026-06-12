"""Smoke test: matcher F1 contra 2 correos reales de procuradores."""
import json
import re
from dataclasses import asdict

from core.procurador_intake import (
    extract_signals,
    is_procurador_email,
    match_expediente,
)

# --- Correo 1: ProcuradoraF (Su ref 21/25) ---
EMAIL_1 = {
    "from": "Pilar Ibañez <proc-f@colegio-proc.example>",
    "subject": "Mi referencia: 2026/7494 - Referencia: 21/25 - EV MMC SPAIN SL- ENGEL & VÖLKER - Sueca 2 Procedimiento ordinario  Autos: 202/26",
    "body": (
        "Cliente: EV MMC SPAIN SL- ENGEL & VÖLKER  Ref.: 21/25\n"
        "Contrario: MICHAEL SEAN HAYES\n"
        "Organo: Sueca 2\n"
        "Procedimiento: Procedimiento ordinario  N.º 202/26\n"
        "M/Ref.: 2026/7494\n"
        "Letrado: Nikolai\n\n"
        "Último trámite:\n"
        "Resguardo de presentación de escrito de alegaciones\n\n"
        "Sin otro particular, reciba un cordial saludo."
    ),
}

# --- Correo 2: Castañeda (Su ref 33/2024) ---
EMAIL_2 = {
    "from": "Castañeda Procuradores <marta@procuradores-b.example>",
    "subject": "Ref : 5979   PROCEDIMIENTO ORDINARIO    572/2024    SECCIÓN DE LO MERCANTIL DEL TI    14  MADRID    Su ref :     33/2024   NEXOLUB, S.L.    Pablo María De Castro García",
    "body": (
        "Adjunto remito última actuación del expediente referenciado:\n\n"
        "CLIENTE.................................. NEXOLUB, S.L.\n"
        "CONTRARIO.............................Pablo María De Castro García\n"
        "ABOGADO..............................Francisco Javier Guirao Cartagena\n"
        "PROCEDIMIENTO.................... PROCEDIMIENTO ORDINARIO 572/2024\n"
        "JUZGADO............................... SECCIÓN DE LO MERCANTIL DEL TI 14 MADRID\n\n"
        "15.06.2026  LEXNET   Dior. Se acuerda suspensión y nuevo señalamiento.\n"
        "Se tiene por constituido el litisconsorcio y por formulada demanda contra LIFE FOR TIRES SL.\n"
        "Se acuerda su emplazamiento a través nuestra\n\n"
        "Señalamientos\n24.09.2026  12:30     Vista"
    ),
}


def run_email(label: str, email: dict):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    # 1. Filtro remitente
    is_proc = is_procurador_email(email["from"])
    print(f"Procurador: {is_proc}")

    # 2. Extraer señales (LLM)
    print("Extrayendo señales (Mistral)...")
    signals = extract_signals(email["subject"], email["body"])
    print(f"  Su ref:       {signals.su_ref}")
    print(f"  Num/Serie:    {signals.num_expediente}/{signals.serie_expediente}")
    print(f"  Contrario:    {signals.contrario}")
    print(f"  Cliente:      {signals.cliente}")
    print(f"  Juzgado:      {signals.juzgado}")
    print(f"  Autos:        {signals.num_asunto}")
    print(f"  Tipo proc:    {signals.tipo_procedimiento}")
    print(f"  Tipo actuac:  {signals.tipo_actuacion}")
    print(f"  Fecha:        {signals.fecha_actuacion}")
    print(f"  Es ruido:     {signals.es_ruido}")

    # 3. Match expediente (API Sudespacho)
    if signals.num_expediente and signals.serie_expediente:
        print("Buscando expediente en Sudespacho...")
        result = match_expediente(signals)
        print(f"  Confianza:    {result.confianza}")
        print(f"  Expediente:   {result.expediente_id}")
        print(f"  Señales:      {result.senales_usadas}")
        if result.datos_expediente:
            print(f"  Datos CRM:    {json.dumps(result.datos_expediente, ensure_ascii=False, indent=4)}")
    else:
        print("Sin Su ref — no se busca en Sudespacho")


if __name__ == "__main__":
    run_email("ProcuradoraF — Su ref 21/25", EMAIL_1)
    run_email("Castañeda — Su ref 33/2024", EMAIL_2)
