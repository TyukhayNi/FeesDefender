# Protocolo DevTools — Captura POST creación expediente extrajudicial

> Objetivo: capturar el payload exacto que envía sudespacho.net al crear un  
> expediente extrajudicial nuevo, para poder replicarlo desde FeesDefender.

---

## Qué necesitamos obtener

Al final de este protocolo debes tener:

1. **URL completa** del endpoint POST (path + host)
2. **Headers de la request** (especialmente `Content-Type` y cualquier token)
3. **Body de la request** (JSON o form-data)
4. **Respuesta** del servidor (especialmente el `id` del expediente creado)

---

## Pasos

### Paso 1 — Abre DevTools y prepara la captura

1. Abre Chrome y navega a `https://tnm.sudespacho.net`
2. Inicia sesión si no lo estás
3. Pulsa `F12` (o `Ctrl+Shift+I`) para abrir DevTools
4. Ve a la pestaña **Network** (Red)
5. Asegúrate de que está grabando (el círculo rojo debe estar activo)
6. Marca la casilla **Preserve log** (Conservar registro) — así no perderás nada al navegar
7. En el filtro de tipo, selecciona **Fetch/XHR** para ver solo peticiones API

### Paso 2 — Crea un expediente extrajudicial de prueba

1. Navega a la sección de expedientes extrajudiciales en sudespacho
2. Pulsa "Nuevo expediente extrajudicial" (o equivalente en la UI)
3. Rellena los campos mínimos obligatorios con datos de prueba:
   - Asunto: `TEST-CAPTURA-FEESDEFENDER` (así lo identificas en la lista)
   - Referencia: cualquier valor
   - Resto de campos: mínimo necesario para que el formulario se acepte
4. Pulsa **Guardar** / **Crear**

### Paso 3 — Localiza la request correcta en DevTools

Después de guardar, en el panel Network verás varias peticiones. Busca:

- **Método:** POST
- **Status:** 200 o 201
- **URL:** probablemente algo como:
  - `https://tnm.sudespacho.net/extrajudicial/add/...`
  - `https://api-crm-commons-pro.sudespacho.biz/api/extrajudicial`
  - `https://tnm.sudespacho.net/api/expedientes_extrajudiciales`
  - o similar

Si hay varias peticiones POST, la correcta es la que devuelve un `id` numérico del expediente recién creado.

### Paso 4 — Extrae los datos necesarios

Haz clic en la request correcta y anota:

#### Tab "Headers"

```
Request URL: [copiar URL completa]
Request Method: POST

Request Headers:
  Content-Type: [¿application/json? ¿application/x-www-form-urlencoded? ¿multipart/form-data?]
  x-api-key o Authorization: [si aparece]
  Cookie: [copiar PHPSESSID y cualquier otra cookie relevante]
  X-CSRF-TOKEN o similar: [si aparece]
```

#### Tab "Payload" (o "Request")

Copiar el body completo tal como aparece. Puede ser:

- **JSON** (si `Content-Type: application/json`):
```json
{
  "asunto": "TEST-CAPTURA-FEESDEFENDER",
  "referencia": "...",
  ...
}
```

- **Form data** (si `Content-Type: application/x-www-form-urlencoded`):
```
asunto=TEST-CAPTURA-FEESDEFENDER&referencia=...&csrf_token=...
```

#### Tab "Response"

Copiar la respuesta completa. Lo más importante:
```json
{
  "id": 652,       ← este es el ID del expediente creado
  ...
}
```

### Paso 5 — Exportar como cURL (método rápido)

Para capturarlo todo de una vez:

1. Clic derecho sobre la request correcta en el panel Network
2. **Copy → Copy as cURL**
3. Pegar el resultado aquí

El formato cURL contiene: URL, headers y body. Ejemplo de lo que verás:

```bash
curl 'https://tnm.sudespacho.net/ruta/al/endpoint' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Cookie: PHPSESSID=abc123...' \
  -H 'X-CSRF-Token: def456...' \
  --data-raw '{"asunto":"TEST","referencia":"W-000000",...}'
```

---

## Después de capturar

Comparte aquí el cURL completo (o los datos de los tabs si prefieres). Con eso:

1. Implementamos `core/sudespacho_create.py` con el endpoint real
2. Añadimos el botón "Crear en sudespacho" en la UI de Streamlit
3. Eliminamos este expediente de prueba desde la UI de sudespacho

---

## Limpieza tras la captura

Una vez capturado el endpoint, borra el expediente de prueba desde sudespacho:

- Expediente asunto: `TEST-CAPTURA-FEESDEFENDER`
- Borrarlo desde la propia UI del CRM (si permite eliminación) o marcarlo como cerrado/archivado

---

## Atajo: inventariar campos sin capturar un guardado (`data-testid`)

> Verificado 2026-07-12 (descubrimiento de la referencia común sudespacho).

Para **inventariar los campos de un formulario y su mapeo campo→nombre de propiedad API** no siempre
hace falta capturar un POST de guardado. El DOM del front de sudespacho expone ese mapeo directamente:

- Cada campo del formulario está envuelto en un contenedor con
  `data-testid="form_field_<Label visible>"` (p. ej. `form_field_Fecha de expedición`).
- El `<input>`/`<select>`/`<textarea>` de dentro lleva el atributo **`name`** con el **nombre real de
  la propiedad API** (p. ej. `name="fecha_contabilizado"`).

Recorriendo el DOM con la consola de DevTools se obtiene la tabla Label→propiedad de golpe, sin pulsar
Guardar (útil cuando no se quiere crear un registro de prueba, o para descubrir nombres engañosos como
«Fecha de expedición» → `fecha_contabilizado`). Ejemplo de volcado read-only:

```javascript
[...document.querySelectorAll('[data-testid^="form_field_"]')].map(c => ({
  label: c.getAttribute('data-testid').replace(/^form_field_/, ''),
  prop:  c.querySelector('input,select,textarea')?.getAttribute('name') ?? null,
}))
```

Sigue haciendo falta la captura del POST/PUT para (a) el shape exacto del body, (b) los headers/auth y
(c) la respuesta con el `id`; el `data-testid` solo cubre el **inventario de campos**.

---

## Qué hacer si la request no aparece en Fetch/XHR

Si el formulario usa un submit HTML clásico (no AJAX), la petición aparecerá en **All** (todos) en lugar de **Fetch/XHR**. En ese caso:

1. Cambia el filtro a "All"
2. Busca el POST entre todas las peticiones
3. El método seguirá siendo POST y el status 200/201/302

Si la respuesta es un redirect (302), la request que nos interesa es la que precede al redirect.
