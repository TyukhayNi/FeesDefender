---
tipo: spec
estado: vigente
creado: 2026-09-25
objeto: core/crm_ficha.py, scripts/crm_ficha.py
rev: "1"
---

# `crm_ficha`: el YAML se lee entero, y lo que se verifica es el conjunto

Remedio de `MEJORAS #283` y `#288`, las dos medidas en aperturas de este mes. **Pieza de dos
rondas** por el radio de daño: escribe datos de cliente en el CRM, decide qué partes quedan
vinculadas a un expediente, y un vínculo de más **da acceso** al expediente a quien no debe
tenerlo. Este documento es el objeto de la **primera** (diseño); la segunda irá sobre el diff.

## 0. Lo medido, que es lo que decide el diseño

- **`#283` (W-030A13, 2026-09-16; medido por GET el 2026-09-23).** El `_ficha_crm.yaml`
  escribió el primer apellido como `apellido:`. `core/crm_ficha.py::_contrario_de` lee
  `apellido1`/`apellido2` con `d.get(...)` y no mira las claves que sobran: la corrida terminó
  sin error y las fichas `clientes_contrarios` 1128 y 1129 quedaron con `1apellido` **vacío**.
  **El daño no se queda en el CRM:** Codicert compone el nombre del requerido desde esos campos
  del CRM (`core/expedicion_certificada.py`, `_CAMPOS_NOMBRE_COMPLETO`), así que el burofax de
  ese expediente habría salido **sin el primer apellido del deudor**.
- **Censo de claves, 2026-09-25**, sobre los **14** `_ficha_crm.yaml` reales del Drive del
  despacho (solo nombres de clave, nunca valores): en raíz, solo las cinco que el loader conoce;
  en colaborador, solo las cinco que conoce; en contrario, **una** clave desconocida —`apellido`—,
  dos veces y **las dos en W-030A13**. Rechazar las claves desconocidas no rompe ninguna ficha
  legítima del corpus.
- **`#288` (W-030A13, expediente 653, 2026-09-16).** `scripts/crm_ficha.py::_auditar` recorre lo
  que la corrida escribió y comprueba que está (con su cardinalidad), pero **nunca mira lo que
  sobra**: cerró «VERIFICADA por lectura» con cuatro colaboradores cuando el expediente tenía
  **seis** —dos *team leaders* de otro Market Center—. Lo vio Nikolai en la pantalla del CRM.

## 1. La frontera, y por qué son dos defectos de una sola

**Lo que el YAML declara y lo que queda en el CRM tienen que ser verificablemente lo mismo, en
los dos extremos.** En la **entrada**, toda clave del YAML se consume o se rechaza: nada se
descarta sin decirlo. En la **salida**, lo que se lee del CRM se contrasta con lo declarado como
**igualdad**, no como inclusión. `#283` es el agujero del primer extremo y `#288`, el del segundo.

La misma frontera aparece dos veces más en el cargador, sin incidente conocido todavía:
`colaboradores` filtra con `if isinstance(c, dict)`, así que un elemento roto desaparece sin
aviso —el contrario ya lo rechaza con su índice (R1/H-08 de P6)—, y un `colaboradores` que no es
lista (un mapping) se itera por sus claves y da **cero colaboradores**. Y una clave de **raíz**
mal escrita —`contrarios:` en plural— dejaría el expediente **sin contrario**, que es un estado
legítimo (`[APER-63]`) e indistinguible del error.

## 2. Decisiones

1. **El YAML es la lista COMPLETA de partes del expediente** (decisión de Nikolai del
   2026-09-25, sobre la alternativa «el YAML es lo que se añade»). Consecuencia: una parte en el
   CRM que el YAML no declara es un **fallo** de la verificación, no un aviso.
2. **Una clave desconocida se rechaza, no se avisa ni se adivina.** Ni alias (`apellido` →
   `apellido1`): adivinar qué quiso decir el humano es otra manera de perder el dato. Rechazar
   cuesta relanzar; ignorar costó un apellido en un burofax.
3. **`crm_ficha` nunca desvincula.** Lo que sobra lo decide un humano: puede ser legítimo (y se
   añade al YAML) o no (y se desvincula a mano, como se hizo en el 653).
4. **La comparación vive en el core**, como función pura (`CLAUDE.md`: la lógica en `core/`, el
   script solo orquesta). Hoy `_auditar` es un cierre dentro del CLI.

## 3. Parte A — el YAML se lee entero o no se escribe nada (`#283`)

**Una sola fuente de las claves.** Tres tuplas de módulo en `core/crm_ficha.py`:
`CLAVES_RAIZ` (`contrario`, `colaboradores`, `notas_html`, `cliente_propio`, `firmante`),
`CLAVES_CONTRARIO` (las once que hoy lee `_contrario_de`) y `CLAVES_COLABORADOR` (las cinco de
`_colaborador_de`). Los constructores leen **de esas tuplas**, de modo que añadir un campo al
loader sin declararlo, o al revés, no pueda pasar sin que un test lo diga (§6).

**Validación ANTES de construir nada**, en `cargar_ficha_yaml`, sobre el YAML entero:

- clave de raíz fuera de `CLAVES_RAIZ` → error;
- clave de un contrario fuera de `CLAVES_CONTRARIO` → error con su ruta, `contrario.<clave>` si
  es un mapping o `contrario[<i>].<clave>` si es lista;
- clave de un colaborador fuera de `CLAVES_COLABORADOR` → error, `colaboradores[<i>].<clave>`;
- `colaboradores` que no sea lista, `null` o ausente → error; elemento que no sea mapping → error
  con su índice (lo mismo que ya hace `contrario`).

**Todos los problemas en un solo `ValueError`**, no el primero: quien corrige el YAML a mano tiene
que ver la lista entera. Cada clave desconocida lleva una sugerencia si hay una clave válida
cercana (`difflib.get_close_matches`, sin inventar si no la hay): `contrario[0].apellido: clave
desconocida; ¿querías 'apellido1'?`.

**Efecto en los tres llamadores**, todos ya en voz alta ante un `ValueError`: `scripts/crm_ficha.py`
sale con código 1 **antes de cualquier escritura** (hoy ya carga el YAML antes del plan);
`scripts/crm_ficha_validar.py` sale con código 2; y `scripts/abrir_caso.py::_firmante_de` lo
convierte en `FichaIlegible`, que la etapa `actuacion` de V2 ya trata como bloqueo. Ninguno lo
degrada a «no hay ficha».

**Lo que NO cambia:** la validación de valores de `_escalar` (enteros, nulos) y la semántica de
`contrario` (mapping, lista, ausente) del R1/H-08 de P6.

## 4. Parte B — la verificación compara el conjunto (`#288`)

**Función pura en `core/crm_ficha.py`:**

```python
@dataclass(frozen=True)
class AuditoriaRelaciones:
    ok: list[str]          # «colaboradores id=256», «... (x2)» si se pidió dos veces
    faltan: list[str]      # lo escrito que la lectura no ve (o ve menos veces)
    sobran: list[str]      # lo que la lectura ve y el YAML no declara (o ve más veces)

def auditar_relaciones(esperado: Mapping[str, Sequence[str]],
                       leido: Mapping[str, Sequence[Mapping]]) -> AuditoriaRelaciones: ...
```

- `esperado` es lo que hoy construye el CLI: `clientes_propios` = el id del cliente propio;
  `clientes_contrarios` y `colaboradores` = los ids que devolvieron `ensure_*_vinculado`, en el
  orden de la corrida. Son **los tres bloques que `crm_ficha` gestiona**, y solo esos se
  comparan: actuaciones, documentos y demás relaciones del expediente no son de su incumbencia.
- **Por multiplicidad, no por pertenencia**, en los dos sentidos: un id pedido dos veces y leído
  una es `falta`; un id pedido una vez y leído dos es `sobra` (vínculo duplicado).
- **Un bloque que el CRM no devuelve** se lee como vacío solo si la respuesta es un mapping
  válido; `None` («no se pudo leer») no llega a esta función: el CLI ya lo trata como SIN
  VERIFICAR, que no es lo mismo que mal.

**El CLI** (`scripts/crm_ficha.py`) imprime `[ok]`, `[FALTA]` y una línea nueva por cada sobrante:

```
  [SOBRA] colaboradores id=624 — está vinculado y el _ficha_crm.yaml no lo declara
```

y el veredicto final:

- **`faltan` no vacío** → como hoy: la lectura desmiente la escritura, código 1;
- **`sobran` no vacío** → código 1 y el mensaje dice qué hacer, sin hacerlo: «si la parte es
  legítima, añádela al `_ficha_crm.yaml` y relanza; si no, desvincúlala a mano en el CRM.
  `crm_ficha` no desvincula». **Nunca** «VERIFICADA»;
- los dos vacíos y todo leído → «VERIFICADA por lectura», como hoy.

**La auditoría parcial** (la que corre tras una escritura fallida) **solo informa de `faltan`**:
las partes que la corrida no llegó a resolver no tienen id todavía, así que cualquier vínculo
suyo de una corrida anterior saldría como «sobrante» sin serlo. Se dice en la salida:
«sobrantes: sin comprobar, la corrida no llegó a resolver todas las partes».

## 5. Lo que queda fuera, dicho

- **Reparar las fichas 1128 y 1129** de W-030A13: es trabajo del caso y escritura en el CRM.
- **C6 de `verificar_apertura`** tiene la misma frontera —cuenta que haya partes, no cuáles—,
  pero compararlas con el YAML exige saber qué id del CRM corresponde a cada parte, y eso hoy
  solo lo sabe la corrida de `crm_ficha`. Haría falta un recibo de ids; es otra pieza.
- **Qué vinculó a los dos colaboradores ajenos del 653**: sin log de auditoría del CRM no se
  puede distinguir un automatismo de una acción en la UI (`#288`).
- **`--dry-run` no lee el CRM**: seguiría sin red. Leer las relaciones antes de escribir para
  enseñar los sobrantes en el plan sería útil, pero cambia el contrato del modo.

## 6. Cómo se prueba (para el plan)

Todo contra dobles, como los tests actuales del CLI (`tests/test_crm_ficha_cli.py`):

- **A, rojo:** una clave desconocida en cada nivel (raíz, contrario mapping, contrario lista,
  colaborador) → `ValueError` con la ruta y, si procede, la sugerencia; y en el CLI, **cero
  llamadas** a `link_ev_mmc`/`ensure_*`/`update_expediente`. Varias claves malas → todas en el
  mensaje. `colaboradores` mapping y elemento no mapping → error con índice.
- **A, control positivo:** un YAML con **todas** las claves de las tres tuplas carga sin error;
  y un test que exige que cada campo de `NuevoClienteContrario`/`NuevoColaborador` que el
  loader rellena tenga su clave en la tupla (así no se puede añadir un campo por un solo lado).
- **B, rojo:** el 653 reproducido —cuatro escritos, seis leídos— → dos `[SOBRA]`, código 1, sin
  «VERIFICADA»; vínculo duplicado → `sobra`; y la auditoría parcial no inventa sobrantes.
- **B, control positivo:** el conjunto exacto → «VERIFICADA»; las regresiones de hoy (`[FALTA]`
  por cardinalidad, `SIN VERIFICAR` si no se lee) siguen iguales.
- **Mutantes** mínimos, cada uno por su test: quitar la comprobación de sobrantes; comparar por
  pertenencia en vez de multiplicidad; validar solo la raíz; que la auditoría parcial compute
  sobrantes.

## 7. Rondas

Dos, por el radio de daño (`CLAUDE.md` §«Cuántas rondas»): esta, sobre el diseño, con
`gpt-6-astra` · `medium` (fila «diseño de … escritura sobre datos de cliente»); y la segunda
sobre el diff, en la sesión que lo implemente, con la misma fila.
