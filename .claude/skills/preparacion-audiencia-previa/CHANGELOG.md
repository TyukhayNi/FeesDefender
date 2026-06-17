# CHANGELOG — `preparacion-audiencia-previa`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-06-17 — Estilo de la casa (enganche)

- Puntero al contrato `data/_estilo/contrato_estilo.md` (capa 1) en los campos de texto libre del JSON (minuta + solicitud de prueba) + `pase-de-estilo` (capa 2) sobre la solicitud de prueba (escrito procesal) antes de darla por lista. *Evidencia*: `[ESTILO-DE-LA-CASA]` (PLAN.md / STATUS.md), commit `f65f371`.

## 2026-06-16 — Telemetría canónica (v1.0.1)

- Retirado el *shim* `scripts/log_uso.py`: ya no había código que lo invocara (los generadores no auto-registraban). La telemetría usa directamente el helper canónico `scripts/registrar_uso.py`. Referencias en prosa actualizadas (`SKILL.md`, `references/flujo.md`). *Evidencia*: handoff de homogeneización de skills (PLAN.md, Ola 1).
