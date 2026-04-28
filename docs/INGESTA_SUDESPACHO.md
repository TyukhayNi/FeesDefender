# Cómo descargar documentos desde sudespacho.net

Tres rutas, ordenadas por la facilidad con la que se ponen en marcha. La
**recomendada para uso continuo es la ruta API** (Ruta C).

---

## Ruta A — Manual (rápida, puntual)

Para casos sueltos o auditoría:

1. Abre el expediente en sudespacho.net.
2. Descarga el ZIP de documentos (o cada documento por separado).
3. Crea el caso local y arrastra los archivos:

```bash
python -m scripts.init_caso EV-2026-001 --titulo "Reclamación E&V — calle X"
# Copia los .pdf/.docx/.eml dentro de:
#   data/CASOS/EV-2026-001/00_INPUT/

python -m scripts.run_pipeline EV-2026-001 --no-sync
```

Coste: 0 minutos de configuración. Inviable a escala.

---

## Ruta B — Vía Drive con rclone

Si sudespacho.net ya te sincroniza la carpeta del expediente al Drive
corporativo (configurable desde **sudespacho → Ajustes → Integraciones →
Google Drive**), basta con apuntar `rclone` al Drive.

```bash
# Una sola vez:
rclone config        # crear remoto "gdrive" (OAuth con tu cuenta)

# Por cada caso:
python -m scripts.init_caso EV-2026-001 \
    --drive "gdrive:Ruta/Donde/Sudespacho/Sincroniza/EV-2026-001"

python -m scripts.run_pipeline EV-2026-001 --sync
```

Coste: configuración inicial de rclone (5 min) + activación del sync de
sudespacho a Drive. Ventaja: no consumes API. Inconveniente: dependes del
intervalo de sync del CRM.

---

## Ruta C — sudespacho.net (recomendada)

El sistema descarga los documentos del Gestor Documental del expediente
directamente al `00_INPUT/` del caso, combinando **dos clientes**:

`core/sync_sudespacho.py` — cliente de la **API REST nueva**
(`api-crm-commons-pro.sudespacho.biz`), autenticada con `x-api-key`. Se
usa para `healthcheck` y, en el futuro, lectura de metadatos del
expediente como elemento.

`core/sync_sudespacho_legacy.py` — cliente del **frontal heredado** del
tenant (`tnm.sudespacho.net` o el subdominio que corresponda),
autenticado con cookie de sesión PHP (`PHPSESSID`). Se usa para el
listado y descarga de documentos: la API REST no expone esa operación.

### 1. Obtén la API key

En **sudespacho.net → Ajustes → API**. Genera una clave personal.

### 2. Obtén la cookie de sesión PHP

Inicia sesión normal en `https://<tu_subdominio>.sudespacho.net`. Abre
DevTools (`Ctrl+Shift+I`) → pestaña **Application** (o **Almacenamiento**)
→ **Cookies** → `https://<tu_subdominio>.sudespacho.net`. Localiza la
cookie `PHPSESSID` y copia su **Value**.

### 3. Configura `.env`

```env
# API REST nueva
SUDESPACHO_BASE_URL=https://api-crm-commons-pro.sudespacho.biz
SUDESPACHO_API_KEY=tu_api_key_aqui
SUDESPACHO_AUTH_HEADER=x-api-key
SUDESPACHO_AUTH_SCHEME=
SUDESPACHO_ELEMENT=expedientes_judiciales
SUDESPACHO_TIMEOUT_S=120

# Frontal heredado (para listado/descarga del Gestor Documental)
SUDESPACHO_LEGACY_HOST=tnm.sudespacho.net
SUDESPACHO_LEGACY_PHPSESSID=el_valor_que_copiaste
SUDESPACHO_LEGACY_TIMEOUT_S=120
```

> La API REST usa `x-api-key`. El frontal heredado usa cookie de sesión.
> Ambos son necesarios — el primero para validación, el segundo para la
> descarga real (la API REST nueva no expone el listado de documentos
> de un expediente).

### 4. Verifica ambas conexiones

```bash
python -m scripts.sync_sudespacho check          # API REST
python -m scripts.sync_sudespacho check_legacy   # Cookie de sesión
```

Si `check_legacy` falla con "Sesión expirada" o "401", la cookie ha
caducado: vuelve al paso 2, refresca el valor en `.env`.

### 5. Localiza el expediente

El ID está en la URL de la vista del expediente:
`https://tnm.sudespacho.net/.../expedientes_judiciales/miembro/<ID>`.
El segmento final tras `miembro/` es el ID que pasarás a `--expediente`.

### 6. Descarga y procesa

```bash
# Solo descarga
python -m scripts.sync_sudespacho pull \
    --case EV-2026-001 \
    --expediente 649 \
    --titulo "Reclamación honorarios E&V — calle X"

# Descarga + pipeline completo (scoring, viabilidad, demanda)
python -m scripts.sync_sudespacho pull \
    --case EV-2026-001 \
    --expediente 649 \
    --run-pipeline

# Expedientes extrajudiciales
python -m scripts.sync_sudespacho pull \
    --case MED-2026-014 \
    --expediente 67890 \
    --element expedientes_extrajudiciales
```

Es idempotente: re-ejecutar no re-descarga. Para forzar re-descarga, usa
`--force` o borra `00_INPUT/.sudespacho_pulled` y los archivos.

---

## Modelo de la API real (decodificado contra el tenant commons-pro)

**Limitación clave:** la API REST nueva no expone "listar documentos de
un expediente". Las propiedades filtrables de `/api/documents` no
incluyen `relatedRegisters` (que sí está en el schema de salida pero no
es indexable). Tampoco `/api/folders/gdocu/0?related_element=…` devuelve
las carpetas del expediente. El sistema de "elementos"
(`/api/element_register/expedientes_judiciales/{id}`) está actualmente
bug-eado en el backend (responde 500 *Array to string conversion* para
cualquier combinación de `properties[]`).

Por eso el listado y la descarga van por el frontal heredado.

### Flujo legacy (decodificado del JS de la página del CRM)

**Listado de documentos del expediente:**

```
POST tnm.sudespacho.net/gdocu/list/elemento/gdocu/
     elemento_relacionado/{element}/miembro_relacionado/{id}/
     direccion_relacionado/der
```

Devuelve HTML; el cliente extrae los IDs por regex de
`id="fila_gdocu_<doc_id>"`.

**Resolución de URL de descarga:**

```
POST tnm.sudespacho.net/gestordocumental/predownloadfile/
     elemento_relacionado/{element}/miembro_relacionado/{id}/
     direccion_relacionado/der
body: csrf_token=…&id={doc_id}
→ {resultado, metodo: 's3'|'cloud'|'s3old'}

POST tnm.sudespacho.net/gestordocumental/descargaficheros3/
     id_docu/{doc_id}/elemento_relacionado/{element}/
     miembro_relacionado/{id}/direccion_relacionado/der
body: csrf_token=…
→ {resultado, url: '<URL S3 prefirmada (5 min)>'}
```

**Descarga binaria:** GET de la URL S3 (sin auth, presigned). El nombre
original del archivo viene en `Content-Disposition`.

**Auth legacy:** cookie `PHPSESSID` + token CSRF (32 hex chars) extraído
del HTML de cualquier página (`var csrf_token = '…';`).

### API REST nueva (uso actual)

```
GET /api/online/current   — healthcheck (404 con API key, 204 con sesión)
GET /api/documents?itemsPerPage=1   — healthcheck efectivo con API key
```

Si en el futuro se arregla el bug del backend en `element_register`, el
cliente leerá metadatos del expediente vía la API nueva sin necesidad
del frontal heredado.

---

## Si la API no responde como espera el cliente

`core/sync_sudespacho.py` centraliza paths y nombres de campo en dos
diccionarios al principio del archivo (`ENDPOINTS` y `DOC_FIELDS`). Si el
tenant usa nombres distintos:

1. Abre `core/sync_sudespacho.py`.
2. Ajusta `ENDPOINTS` y `DOC_FIELDS`.
3. Vuelve a ejecutar `python -m scripts.sync_sudespacho check`.

Es la única zona del código que cambia entre revisiones de la API.

---

## Modelo de datos resultante

Cada fuente de ingestión escribe en su propia subcarpeta dentro de
`00_INPUT/`. Esto preserva trazabilidad de origen, permite idempotencia
por fuente, y deja añadir nuevas fuentes (email, WhatsApp, etc.) sin
mezclarse con las existentes.

```
data/CASOS/EV-2026-001/
├── 00_INPUT/
│   ├── _caso.md                      ← creado por case_manager
│   ├── _inventory.json               ← inventory.scan, con `source` por archivo
│   ├── sudespacho/                   ← pull desde el CRM
│   │   ├── .pulled                   marcador idempotencia
│   │   ├── 01_actuacion_procesal_01.pdf
│   │   ├── 02_demanda_01.pdf
│   │   └── ...
│   ├── drive/                        ← rclone (si está configurado)
│   │   └── .synced
│   └── manual/                       ← drag-and-drop del abogado
│       └── nota_anadida.pdf
├── 01_PROCESADO/                     ← rellenado por el pipeline
└── ...
```

El `_inventory.json` registra el campo `source` por cada archivo
(`sudespacho`, `drive`, `email`, `whatsapp`, `manual`, …) para que las
fases posteriores del pipeline puedan filtrar o priorizar por origen sin
parsear paths.

Si tenías una versión anterior con archivos volcados directamente en
`00_INPUT/` y un marcador `.sudespacho_pulled` en la raíz, la migración
es manual una sola vez: mueve los archivos a `00_INPUT/sudespacho/`,
renombra el marcador a `.pulled` y vuélvelo a guardar dentro de
`sudespacho/`. O más simple: borra el caso y re-pull con `--force`.
