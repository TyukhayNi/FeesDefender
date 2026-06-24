"""Motor de atomización de correo a nivel de mensaje.

Ver ``docs/superpowers/specs/2026-06-24-email-atomize-design.md`` y el plan
``docs/superpowers/plans/2026-06-24-email-atomize-fase1.md``.

Lee ``00_Input/03_Email/*.eml`` (exportados por :mod:`core.email_export`) y produce, en
``01_Procesado/Emails/``, un ``.md`` por mensaje atómico (frontmatter + cuerpo limpio),
adjuntos deduplicados por sha256 con ficha, ``corpus.jsonl``, ``_registro.json`` (IDs
congelados), ``CORREOS_LECTURA.md`` e ``INDICE_ADJUNTOS.md``. Nunca toca ``00_Input``;
idempotente por IDs congelados.
"""
