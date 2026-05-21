# PLAN_DESPLIEGUE_EV — Hospedaje del Streamlit y apertura a Engel & Völkers

> Plan de despliegue del Streamlit de FeesDefender en VPS dedicado para dar acceso a
> Marta Reynares (E&V) y, en una segunda fase, a 1-2 Team Leaders E&V adicionales.
> Sustituye la operación actual (Streamlit local en el equipo de Nikolai, datos en
> Drive corporativo) por una arquitectura cliente-servidor con autenticación,
> roles y cumplimiento RGPD/RIA formalizado.
>
> **Estado**: borrador inicial (s24, 2026-05-21). Pendiente de ejecución por fases.
> **Tracking**: tareas Fase 0–5 en TODO list del proyecto.

---

## 1. Contexto

Hasta ahora el Streamlit corría en local en el equipo de Nikolai y era consumido
por Paola y Ana desde la red del despacho. Marta Reynares (E&V) accedía a los
datos solo mediante el Drive compartido de E&V, sin entrar a la UI.

A partir de esta planificación, Marta y futuros Team Leaders de E&V (1–3 en el
primer año según decisión cerrada en sesión s24) accederán al Streamlit con un
rol restringido: lectura de sus propios casos y alta de nuevos asuntos. Esto
obliga a hospedar el servicio fuera del equipo de Nikolai, con autenticación
real, segregación de permisos y un marco RGPD/RIA cerrado antes del go-live.

El planteamiento también resuelve un problema operativo paralelo: la lentitud
de Claude Code y de la suite de tests cuando el repo vive en Google Drive for
Desktop. La migración a servidor convierte al VPS en fuente de verdad del
filesystem, con Drive degradado a copia operativa.

## 2. Decisiones cerradas (sesión s24, 2026-05-21)

| Punto | Decisión |
|---|---|
| Nivel de acceso E&V | Lectura sobre sus propios casos + alta de nuevos asuntos vía formulario |
| Hosting | VPS Hetzner Cloud EU (CX22) + Cloudflare Tunnel + Cloudflare Access |
| Volumen primer año | 1–3 Team Leaders (Marta + 1-2) |
| Datos | Migración a `/srv/feesdefender/data/CASOS` (fuente de verdad) + backup dual a Drive (operativo) y Backblaze B2 (off-site cifrado) |

Justificación de la pila Hetzner + Cloudflare:

1. **Coste mínimo**: ~€5/mes el VPS, Cloudflare Access gratis hasta 50 usuarios,
   Backblaze B2 ~€0,06/mes para los volúmenes previstos.
2. **GDPR-clean**: Hetzner es proveedor europeo con DPA estándar UE. Cloudflare
   Access procesa solo metadatos de autenticación (no contenido). Backblaze B2
   con `rclone crypt` cifra en cliente antes de subir.
3. **Sin código de autenticación propio**: Cloudflare Access maneja login,
   MFA, allowlist por email y logs de auditoría. El Streamlit solo lee la
   cabecera `Cf-Access-Authenticated-User-Email` que Cloudflare inyecta.
4. **Sin puertos expuestos**: Cloudflare Tunnel hace que el VPS se conecte
   saliente a Cloudflare; el servidor no tiene 80/443 abiertos a Internet.

## 3. Arquitectura objetivo

```
   Marta / Team Leaders E&V          Paola, Ana, Nikolai
            │                              │
            └──────────────┬───────────────┘
                           ▼
              ┌──────────────────────────┐
              │     Cloudflare Access     │
              │   feesdefender.tnm.legal  │
              │   (auth + MFA + log)      │
              └─────────────┬─────────────┘
                            │ Cloudflare Tunnel
                            ▼
         ┌──────────────────────────────────────┐
         │   Hetzner Cloud CX22 (Falkenstein)   │
         │   ┌────────────────────────────────┐ │
         │   │ Streamlit (systemd)            │ │
         │   │  ├─ core/auth (resolve role)   │ │
         │   │  └─ vistas filtradas por rol   │ │
         │   └──────────────┬─────────────────┘ │
         │                  ▼                   │
         │   /srv/feesdefender/data/CASOS/      │  ← fuente de verdad
         │                  │                   │
         │   rclone sync diario ──► Drive       │  ← backup operativo
         │                       ──► Backblaze  │  ← backup off-site cifrado
         └──────────────────────────────────────┘
```

### 3.1 Componentes

- **VPS Hetzner CX22** (Falkenstein o Núremberg): 2 vCPU, 4 GB RAM, 40 GB NVMe,
  Ubuntu 24.04 LTS. ~€4,51/mes. Suficiente para 5 usuarios concurrentes y el
  pipeline LLM existente.
- **Cloudflare Tunnel**: servicio `cloudflared` saliente. El VPS no expone
  puertos a Internet. Termina TLS en el edge de Cloudflare.
- **Cloudflare Access**: política de aplicación que exige login (email + MFA)
  antes de llegar al VPS. Inyecta cabeceras firmadas con identidad del usuario.
- **Streamlit + systemd**: servicio persistente, autostart, logs en
  `journalctl`. Sin nginx delante: Cloudflare Tunnel ya hace el reverse proxy.
- **rclone (cron)**: sincroniza `data/CASOS` a Drive (operativo, sin cifrar)
  y a Backblaze B2 (off-site, cifrado en cliente con `rclone crypt`).

### 3.2 Lo que NO entra en esta arquitectura

- nginx (innecesario con Cloudflare Tunnel).
- Let's Encrypt (Cloudflare termina TLS).
- Sistema de contraseñas propio (Cloudflare Access).
- IdP propio (SSO con Google Workspace de E&V se evaluará en v2 si se llega a 10+ Team Leaders).
- Base de datos relacional (no necesaria en v1; el sistema sigue trabajando con filesystem).

## 4. Roles y permisos

### 4.1 Modelo

Tres roles, resueltos por email en `core/auth/roles.yaml`:

| Rol | Quién | Cómo se identifica |
|---|---|---|
| `admin` | Nikolai | `nikolai.tyukhay@tyukhay.legal` |
| `despacho` | Paola, Ana | dominio `@tyukhay.legal` (excluyendo admin) |
| `ev_team_leader` | Marta + Team Leaders | lista nominal en roles.yaml (no dominio entero) |

La identificación por dominio E&V (`@engelvoelkers.com`) **no** se usa para
asignar rol automáticamente: cada Team Leader debe figurar nominalmente en
`roles.yaml`, alineado con el anexo de tratamiento firmado.

### 4.2 Matriz de visibilidad

| Recurso | admin | despacho | ev_team_leader |
|---|:---:|:---:|:---:|
| Listado completo de casos | Sí | Sí | **No** (solo casos con `captador ∈ oficinas E&V`) |
| `00_Input/` del caso | Sí | Sí | **No** |
| `06_Anonimizado/` | Sí | Sí | **No** |
| Ficha de viabilidad (pública) | Sí | Sí | **Sí** (versión recortada, definida en Fase 0) |
| Estado del caso | Sí | Sí | **Sí** |
| Comunicaciones internas | Sí | Sí | **No** |
| Honorarios objetivo / estrategia | Sí | Sí | **No** |
| `90_NOTAS_PERSONALES/` | Sí | Sí | **No** |
| Alta de asunto E&V | Sí | Sí | **Sí** (queda `pending_review=true`) |
| Edición posterior al alta | Sí | Sí | **No** |
| Configuración del sistema | Sí | **No** | **No** |

### 4.3 Hermeticidad

El filtro por rol vive en el **core**, no en la UI. Toda función que devuelve
casos acepta un argumento `role` y filtra antes de devolver. La UI solo
orquesta. Esto se garantiza con tests dedicados en `tests/auth/`:

- `test_ev_team_leader_no_ve_casos_no_ev`: lista universos mixtos y verifica
  que ningún case_id no-E&V aparece en la respuesta.
- `test_ev_team_leader_no_accede_directamente_a_case_id_ajeno`: intenta
  acceder por URL a un case_id que no le pertenece y verifica 403.
- `test_ev_team_leader_no_ve_campos_internos`: render de la ficha y
  comprobación de que campos restringidos no aparecen ni en HTML ni en el JSON
  intermedio.

Sin estos tests verdes, **no se abre el acceso a Marta**.

## 5. Plan por fases

### Fase 0 — Pre-requisitos (1 día)

1. Subdominio `feesdefender.tnm.legal` en el DNS de tnm.legal apuntando a
   Cloudflare (Cloudflare como autoritativo).
2. Cuenta Hetzner Cloud (`https://console.hetzner.cloud`).
3. Cuenta Cloudflare con Zero Trust habilitado (plan Free).
4. Cuenta Backblaze B2 con bucket `feesdefender-backup-eu` región EU.
5. **Lista cerrada de campos visibles para `ev_team_leader`**: producto de
   trabajo a entregar en este plan, no en la implementación. Borrador en
   `docs/PERMISOS_EV_v1.md`.
6. **Listado de captadores/oficinas E&V** que disparan el filtro de casos.
   Fuente: `core/constants/clientes_propios_ev.py` ya existente + posible
   ampliación a oficinas concretas. Borrador en `docs/CAPTADORES_EV_v1.md`.

### Fase 1 — Infraestructura (1 día)

```bash
# Provisión VPS (desde consola Hetzner, no PowerShell)
# - Tipo: CX22 (Ubuntu 24.04)
# - Región: nbg1 (Núremberg) o fsn1 (Falkenstein)
# - SSH key: cargar clave pública de Nikolai
# - Firewall Hetzner: solo SSH puerto 22 desde IP fija del despacho
```

Hardening tras primer login:

```bash
# ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable

# fail2ban
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban

# Deshabilitar root SSH y password auth
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Usuario de servicio
sudo adduser --system --group --home /srv/feesdefender feesdefender
```

Cloudflare Tunnel:

```bash
# Instalar cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Autenticación y túnel
cloudflared tunnel login
cloudflared tunnel create feesdefender
# Configurar /etc/cloudflared/config.yml con ruta a /srv/feesdefender
sudo cloudflared service install
```

Política Cloudflare Access (desde dashboard Zero Trust):

- Aplicación: `feesdefender.tnm.legal`
- Tipo: Self-hosted
- Policy 1 (allow): emails en allowlist (Nikolai, Paola, Ana, Marta)
- Policy 2 (require): MFA obligatorio
- Session duration: 8 horas
- Identity provider: One-time PIN por email (suficiente para v1) o Google si los usuarios tienen Workspace

Resultado de Fase 1: `https://feesdefender.tnm.legal` exige login y devuelve un
"Hello World" desde el VPS.

### Fase 2 — Migración de datos (medio día)

```powershell
# Desde PowerShell en el equipo de Nikolai
cd "G:\Unidades compartidas\DESPACHO - PRODUCCION\Base datos expedientes"

# Subir data/CASOS al VPS (vía rclone sobre SFTP o vía scp/rsync)
rclone copy "data/CASOS" feesdefender-vps:/srv/feesdefender/data/CASOS `
  --drive-skip-shortcuts --progress
```

Configuración en el VPS:

```bash
sudo -u feesdefender mkdir -p /srv/feesdefender/data/CASOS
sudo chown -R feesdefender:feesdefender /srv/feesdefender

# Verificar tamaño y estructura
sudo -u feesdefender du -sh /srv/feesdefender/data/CASOS
sudo -u feesdefender ls /srv/feesdefender/data/CASOS | head
```

Repointado del .env:

```ini
# En el VPS, /srv/feesdefender/.env
CASOS_ROOT=/srv/feesdefender/data/CASOS
```

Backup dual (cron diario, 03:00 UTC):

```bash
# /etc/cron.d/feesdefender-backup
0 3 * * * feesdefender rclone sync /srv/feesdefender/data/CASOS gdrive-ev:Backup/CASOS \
  --drive-skip-shortcuts --log-file=/var/log/feesdefender/rclone-drive.log

30 3 * * * feesdefender rclone sync /srv/feesdefender/data/CASOS b2crypt:CASOS \
  --log-file=/var/log/feesdefender/rclone-b2.log
```

`b2crypt:` es un remote `rclone crypt` que cifra nombres y contenidos en
cliente antes de subir a Backblaze B2. La clave vive solo en el VPS y en un
sobre cerrado en la caja fuerte del despacho.

### Fase 3 — Auth + roles + vista E&V (2–3 días dev)

Estructura nueva en el repo:

```
core/auth/
├── __init__.py
├── middleware.py        # lee Cf-Access-Authenticated-User-Email
├── roles.py             # resolve_role(email) → Literal["admin","despacho","ev_team_leader"]
├── roles.yaml           # mapeo email → rol (gitignored, gestionado vía script)
├── decorators.py        # @require_role, @require_case_access
└── permissions.py       # matriz declarativa de la sección 4.2
tests/auth/
├── test_hermeticidad_ev.py
├── test_resolve_role.py
└── test_permissions_matrix.py
```

Cambios en UI Streamlit:

- `app.py`: al inicio, resolver rol vía `core/auth/middleware`. Si no hay
  cabecera (acceso directo al VPS), denegar.
- Nuevo `pages/ev_dashboard.py`: vista exclusiva del rol `ev_team_leader`,
  filtrada por captador.
- Nuevo `pages/ev_nuevo_asunto.py`: formulario reducido de alta, crea caso
  con `pending_review=true` y notifica por email a despacho.
- Decorador en cada página existente: `@require_role(["admin","despacho"])`.

Tag `pending_review`: campo nuevo en el manifiesto del caso. Casos con esta
flag aparecen destacados en el dashboard de despacho hasta que un admin o
despacho los marca como revisados.

Notificación de alta: email a `nikolai.tyukhay@tyukhay.legal` y a las
direcciones de `despacho` cada vez que un Team Leader da de alta un asunto.
Usar SMTP autenticado del despacho.

### Fase 4 — Cumplimiento RGPD/RIA (paralela a Fase 3, ~1 semana)

Cierre del plan ya esbozado en `docs/CUMPLIMIENTO.md` y memoria
`project_cumplimiento_ria_rgpd.md`, ahora con el delta E&V:

1. **DPAs firmados**:
   - Hetzner Cloud (DPA estándar EU, disponible en panel).
   - Cloudflare (DPA en `https://www.cloudflare.com/cloudflare-customer-dpa/`).
   - Backblaze B2 (DPA bajo demanda).

2. **Anexo de tratamiento despacho ↔ E&V**: documento bilateral que define:
   - **Qué datos exactos verán Marta y Team Leaders** (referencia a la lista
     cerrada de Fase 0).
   - **Base legal**: interés legítimo del despacho (gestión de la relación
     comercial con E&V como cliente recurrente del despacho) + información
     previa al cliente del despacho en la hoja de encargo.
   - **Roles**: el despacho es responsable del tratamiento; E&V es destinatario
     (no encargado). E&V no toma decisiones sobre los datos, solo los recibe
     en el marco de la relación comercial.
   - **Finalidad**: gestión del asunto vinculado a una operación inmobiliaria
     intermediada por E&V.
   - **Plazos**: el acceso de E&V a un caso se revoca al cierre del asunto.
     Los datos en backup se conservan según el plan general del despacho.
   - **Notificación de brechas**: el despacho notifica a E&V en 72h si una
     brecha afecta a datos visibles para Team Leaders.

3. **Actualización de la hoja de encargo** del despacho: cláusula que informa
   al cliente de que, si su asunto está vinculado a una operación intermediada
   por una agencia inmobiliaria, datos limitados de su expediente pueden ser
   accesibles para personal autorizado de dicha agencia, con finalidad de
   coordinación y dentro del marco del anexo de tratamiento.

4. **Actualización de la política de privacidad** del despacho con el mismo
   contenido informativo.

5. **Log de accesos por rol `ev_team_leader`**: integración con Cloudflare
   Access (logs nativos en Zero Trust dashboard) + log aplicativo en
   `/var/log/feesdefender/access-ev.log` con formato JSON línea (timestamp,
   email, action, case_id, result). Retención mínima 1 año.

6. **Banner UI de información a usuarios**: al login de un `ev_team_leader`,
   primera pantalla informativa con resumen del anexo y enlace al texto
   completo. Aceptación registrada.

7. **Evaluación de impacto (PIA)** ligera: el sistema no usa categorías
   especiales de datos ni decisión automatizada que afecte significativamente
   al cliente (el pre-relleno LLM es asistencia al abogado, no decisión).
   PIA simplificada documentando ausencia de riesgo alto. Archivada en
   `docs/cumplimiento/PIA_DESPLIEGUE_EV.md`.

### Fase 5 — Piloto con Marta (1–2 semanas)

1. **Onboarding (30 min)**: videollamada con Marta, alta nominal en
   `roles.yaml`, primer login, recorrido por el dashboard y el formulario de
   alta de asunto.
2. **Manual de una página** en castellano para Team Leader E&V, guardado en
   `docs/manuales/MANUAL_TEAM_LEADER_EV.md` y exportado a PDF para Marta.
3. **Feedback semanal** durante 2 semanas (15 min cada uno) con Marta.
   Cambios iterativos sobre vista y formulario.
4. **Criterio de éxito v1**: Marta da de alta 3 asuntos sin asistencia y
   consulta 10 expedientes sin incidencias funcionales ni de permisos.
5. **Apertura controlada**: una vez estabilizada con Marta y validado el
   criterio, alta nominal de 1-2 Team Leaders adicionales con el mismo
   protocolo de onboarding.

## 6. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|:---:|:---:|---|
| Bug en filtro hermético → ev_team_leader ve caso ajeno | Baja | Alto | Tests obligatorios en `tests/auth/hermeticidad`, code review, log de accesos para detección post-hoc |
| Fallo VPS Hetzner | Baja | Medio | Backup dual diario; restauración desde Backblaze o Drive en <2h; degradación temporal a streamlit local |
| Caducidad de credenciales Cloudflare Tunnel | Baja | Medio | Tunnel es persistente con token largo plazo; monitor de uptime externo (UptimeRobot free) |
| Rechazo de E&V al anexo de tratamiento | Media | Alto | Trabajar el anexo con E&V antes de Fase 3 para evitar desarrollar sobre supuestos no validados |
| Marta no adopta la herramienta | Media | Medio | Onboarding personal + feedback semanal + manual breve; alternativa de uso vía email mantiene la operativa actual |
| Lentitud LLM por VPS modesto | Baja | Bajo | Pre-relleno LLM ya externaliza a Anthropic API; el VPS solo orquesta |
| Coste imprevisto en B2 si los expedientes crecen | Baja | Bajo | B2 cobra ~€5/TB/mes; volumen actual <100 GB, holgura abundante |

## 7. Lo que queda fuera de v1 (backlog v2)

- SSO con Google Workspace de E&V (sustituye one-time PIN si se llega a 10+ Team Leaders).
- Roles más finos (ej. `ev_office_manager` vs `ev_agent`).
- Dashboard analítico para E&V (ratios de éxito, tiempos medios, etc.).
- API REST para que E&V integre desde su CRM.
- App móvil o PWA.
- Migración del repo de código a GitHub privado + servidor (decisión separada,
  ver conversación s24 sobre Drive vs local).

## 8. Calendario tentativo

| Semana | Trabajo |
|---|---|
| s25 (26-30 mayo) | Fase 0 + Fase 1 + iniciar Fase 4 (DPAs) |
| s26 (2-6 junio) | Fase 2 + arrancar Fase 3 |
| s27 (9-13 junio) | Fase 3 (vista E&V + alta) + tests hermeticidad |
| s28 (16-20 junio) | Cierre Fase 3, Fase 4 (anexo E&V firmado), QA interno |
| s29-s30 (23 junio-4 julio) | Fase 5 piloto Marta |
| s31-s32 (7-18 julio) | Apertura a 1-2 Team Leaders adicionales |

Margen ~6-8 semanas hasta producción estable con Marta. Las fechas se
recalibran al cerrar el anexo con E&V, que es el camino crítico no técnico.

## 9. Referencias

- `STATUS.md` — fuente de verdad operativa del proyecto.
- `docs/ARQUITECTURA.md` — arquitectura del core.
- `docs/CUMPLIMIENTO.md` — plan RGPD/RIA general.
- `core/constants/clientes_propios_ev.py` — identificación de operaciones E&V.
- Memoria: `project_cumplimiento_ria_rgpd.md`, `project_feesdefender_users.md`,
  `project_otros_y_clientes_propios.md`.

---

*Documento abierto. Actualizar a medida que se cierran fases o cambian decisiones.*
