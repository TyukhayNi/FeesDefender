"""Motor de atomización fina de WhatsApp a nivel de chat numerado.

Ver docs/superpowers/specs/2026-06-25-whatsapp-atomize-design.md.
Lee 00_Input/02_Whatsapp/<rol>/<chat>/_chat.txt (+ media) y produce, en
01_Procesado/Whatsapp/, un .md numerado por chat (citable), atoms .md de las
unidades enterradas promovidas, adjuntos deduplicados por sha256 con ficha,
corpus.jsonl y _registro.json (IDs congelados). Nunca toca 00_Input; idempotente.
"""
