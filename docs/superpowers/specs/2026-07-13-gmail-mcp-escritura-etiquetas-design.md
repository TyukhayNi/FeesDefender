# Diseño — `gmail_mcp`: ampliación a escritura de etiquetas + migración al repo

- **Fecha:** 2026-07-13
- **Estado:** aprobado (brainstorming) → pendiente de plan de implementación
- **Rama:** `feat/gmail-mcp-escritura`
- **Origen:** necesidad operativa de organizar el correo de un caso (crear la etiqueta
  del expediente y aplicarla a los mensajes) desde el MCP propio del despacho, no solo
  desde el conector nativo de claude.ai (que es de una sola cuenta y depende de la sesión).

## 1. Contexto

Hoy conviven dos MCP de correo:

- **`Gmail_despacho__solo_lectura`** (`~/Dev/Gmail MCP Desktop/`, alias `gmail-ro`): MCP
  propio, **multicuenta** (contabilidad, mails.repositorio, engelvoelkers, tyukhay.legal,
  procesal), scope **`gmail.readonly`** y **sin tools de modificación** (restricción doble:
  scope + ausencia de tools). Alimenta la skill `exportar-correos-etiqueta` (que en realidad
  lee vía `core.gmail_source`, no vía este MCP).
- **Conector nativo de claude.ai** (`63085f9d…`): **una sola cuenta** (la conectada en
  claude.ai), ya con escritura (`create_label`, `label_thread/message`, `unlabel…`). Es lo
  que se usó para etiquetar/desetiquetar el caso W-02XOR7 el 2026-07-13.

Este diseño amplía **el MCP propio** para que cree y aplique etiquetas de forma multicuenta,
duradera y disponible en Cowork.

## 2. Decisiones cerradas (brainstorming 2026-07-13)

1. **Superficie de escritura:** crear etiqueta + aplicar/quitar etiqueta. "Mover a etiqueta"
   = **aplicar** la etiqueta; el correo **permanece en Inbox** (no se archiva).
2. **Arquitectura:** **ampliar en el mismo servidor** (gemelo de google-despacho F1→F2), no
   un servidor de escritura aparte.
3. **Scope y cuentas:** scope único **`gmail.modify`** (subsume `readonly`; **no** permite
   borrado permanente, que exige `mail.google.com`). Reautorizar **las 5 cuentas**.
4. **Hogar del código:** **migrar** `~/Dev/Gmail MCP Desktop/` → **`plugins/gmail_mcp/`**,
   hermano de `plugins/google_despacho_mcp/` (control de versiones, tests en la suite,
   cobertura leak-scan, flujo rama+PR).

## 3. Alcance / hogar del código

Migrar a `plugins/gmail_mcp/`:

```
plugins/gmail_mcp/
    __init__.py
    gmail_auth.py       # scope, tokens, OAuth (add/remove account)
    server.py           # FastMCP: tools de lectura (existentes) + escritura (nuevas)
    gmail_cli.py        # add/list/remove cuentas
    run_server.bat      # arranque robusto (poll-until-ready), patrón expedientes/google-despacho
    README.md
    dxt-build/          # manifest + .dxt (UNTRACKED el .dxt binario; manifest versionado)
tests/
    test_gmail_mcp_*.py # tools puras con service inyectado
```

- El **config-home sigue en `~/.gmail-mcp/`** (tokens y `credentials.json` NO se mueven; la
  ruta del código y la de los tokens son independientes).
- Actualizar `claude_desktop_config.json` al nuevo path del repo.

## 4. Auth / scope

- `gmail_auth.SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]`. Fijado en el
  fichero, no parametrizado (ampliarlo exige edición consciente), igual que hoy.
- `gmail.modify` **subsume** `gmail.readonly` → las tools de lectura siguen funcionando.
- `gmail.modify` **no** permite borrado permanente ni acceso IMAP/SMTP total → el borrado
  queda descartado a nivel de scope, no solo de tools.
- **Reautorización de las 5 cuentas** (`python -m plugins.gmail_mcp.gmail_cli add` o el CLI
  del plugin; flujo OAuth en navegador, lo ejecuta Nikolai). Consecuencia conocida y
  deliberada: si una cuenta queda con token `readonly` viejo, sus llamadas darán
  `invalid_scope` hasta reautorizar (mismo comportamiento observado en google-despacho).
- **Prerrequisito a verificar antes de reautorizar:** la app OAuth debe estar en
  **Producción**. Si sigue en *Testing*, el refresh token caduca a los 7 días. Ver
  `reference-gmail-mcp-token-expiry` (memoria) / `docs/` sobre el MCP de Gmail.

## 5. Tools nuevas (escritura)

Todas exigen **`account` explícito** (una dirección concreta). **Prohibido el fan-out en
escritura**: nunca modificar las 5 cuentas a la vez.

| Tool | Firma | Comportamiento |
|---|---|---|
| `create_label` | `(account, name) -> {id, name}` | Crea la etiqueta de usuario si no existe; **idempotente** (si ya existe, devuelve su id). |
| `apply_label` | `(account, label, target_id, target_type="message"\|"thread") -> {…}` | Resuelve `label` por **id o nombre** (si es un nombre inexistente → **error**; crear es explícito con `create_label`). Añade la etiqueta al mensaje o al hilo. El correo **permanece en Inbox**. |
| `remove_label` | `(account, label, target_id, target_type) -> {…}` | Quita la etiqueta del mensaje o del hilo. |

Cambio en tool existente:

- `list_labels`: **extender** para devolver `{id, name}` por etiqueta (hoy solo devuelve
  nombres; aplicar necesita el id). Mantener la clave por cuenta.

## 6. Guardarraíles (fail-closed, espíritu del `allow_external` de google-despacho)

- **Solo etiquetas de usuario.** Rechazar operar (crear/aplicar/quitar) sobre etiquetas de
  sistema: `INBOX, SENT, DRAFT, TRASH, SPAM, IMPORTANT, STARRED, UNREAD, CHAT` y `CATEGORY_*`.
  Fail-closed ante etiqueta desconocida/ambigua.
- **`account` obligatorio** en toda escritura (sin default, sin fan-out).
- **Sin borrado** (ni de mensajes ni de etiquetas), **sin envío/borradores**, **sin
  archivar**, **sin marcar leído/no leído**. No se registran esas tools.
- **Identidad del server:** renombrar `FastMCP("gmail-multiaccount-ro")` →
  `"gmail-multiaccount"`; el docstring del módulo deja de afirmar "solo lectura" y describe
  la superficie real (lectura + etiquetado, sin borrado/envío).

## 7. Refactor para tests

- Introducir **inyección de `service`** (`build_server(service_factory=…)`) como en
  `plugins/google_despacho_mcp/server.py`, para testear las tools con un service falso sin
  tocar Gmail. Hoy `server.py` llama a `gmail_auth.build_service` directo; se parametriza.
- **Tests mínimos:**
  - `create_label` crea cuando no existe y es idempotente cuando existe.
  - `apply_label` / `remove_label` sobre **mensaje** y sobre **hilo**.
  - Resolución `nombre → id`; nombre inexistente en `apply_label` → error.
  - Rechazo de etiqueta de **sistema** (fail-closed).
  - `account` obligatorio en escritura.
  - Las tools de lectura existentes siguen pasando (no regresión).

## 8. Rollout / Cowork

- Reempaquetar el **`.dxt`** con display "Gmail despacho — multicuenta (lectura + escritura)"
  y **reimportar** en Cowork (Ajustes → Extensiones).
- Actualizar `claude_desktop_config.json` al nuevo path del repo (`plugins/gmail_mcp/`),
  con **Claude Desktop cerrado** (reescribe el config al cerrar) — ver
  `reference-claude-desktop-config-clobber`.
- **Gotcha:** no dejar a la vez la entrada cruda del config y el `.dxt` con el mismo nombre
  (colisión del puente). Quedarse con una sola vía.

## 9. Fuera de alcance (YAGNI)

Archivar / mover-de-bandeja, borrar (mensajes o etiquetas), enviar / borradores, marcar
leído-no-leído, scope por-cuenta, filtros/reglas de Gmail, jerarquías de etiquetas.

## 10. Entrega

- Rama **`feat/gmail-mcp-escritura`** + **PR** contra `main` (protegida). No sobre la rama del
  intake W-02XOR7.
- **Suite verde** + **leak-scan** en verde antes de mergear.
- `pre-commit`/`pre-push` instalados en el worktree.
- Tras merge (pasos operativos, no de código): reautorizar las 5 cuentas, verificar app en
  Producción, reempaquetar+reimportar `.dxt`, recablear `claude_desktop_config.json`.

## 11. Riesgos

- **Escritura en 5 buzones reales** (incl. contabilidad, procesal): mitigado con
  etiquetas-solo + fail-closed + sin borrado + `account` obligatorio. Todo reversible
  (`remove_label`).
- **Reautorización olvidada** → `invalid_scope` en la cuenta no migrada (síntoma conocido).
- **App en Testing** → caducidad de 7 días del refresh token; verificar Producción.
- **Migración de path** rompe el cableado de Claude Desktop/Cowork hasta actualizar config
  y reimportar `.dxt`.
