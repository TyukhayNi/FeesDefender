# Changelog — contestacion-honorarios-art20-lau

## 1.1.0 — 2026-07-03

- Biblioteca local `references/jurisprudencia/`: PDF anonimizados de la SJPI
  nº 29 de Valencia 157/2025 (íntegra) y de la SJPI nº 46 de Madrid 559/2025
  (retirada la primera página LexNet con referencias internas), más `INDICE.md`
  con perímetros de uso y pasajes clave verificados contra los PDF. Barcelona
  69/2025 pendiente de incorporar.
- `assets/FORMULARIO_CONTESTACION.docx`: formulario tipo en Word (texto
  idéntico a la plantilla maestra) para trabajo manual sin asistencia.

## 1.0.0 — 2026-07-03

Versión inicial. Cristaliza el playbook del asunto W-02THLJ (contestación
íntegra aprobada) y la variante corta del asunto EV Santander (PO 318/2026):

- Arquitectura de ocho motivos como Hechos (arts. 399/405 LEC) con condiciones
  de inclusión y reglas de renumeración.
- Uso quirúrgico de las resoluciones de apoyo (SJPI Valencia 157/2025, SJPI
  Madrid 559/2025, SJPI Barcelona 69/2025) con sus perímetros.
- Plantilla maestra placeholderizada (variante Cataluña), plantilla del motivo
  de temporada y suplico en cascada.
- Estrategia maestra de desacople, punto flaco (temporalidad no documentada) y
  línea roja (hilo interno consultora-legal).
- Checklists previo y de entrega; telemetría con el helper canónico
  `registrar_uso.py`.
