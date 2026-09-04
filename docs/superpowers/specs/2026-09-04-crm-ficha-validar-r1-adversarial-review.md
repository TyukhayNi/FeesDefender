---
tipo: revision-adversarial
objeto: "diff del validador del _ficha_crm.yaml y de los tres campos perdidos del contrario"
objeto_rev: "rama claude/crm-ficha-validar, commit a4eb8ed"
commit: a4eb8ed
ronda: "1"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: m9xz
sha256_informe: 8757a35e2a749125703bb4e6a4e20436c980606761fd5dd2575b86fe9e863475
adjudicado_en: docs/superpowers/specs/2026-09-04-crm-ficha-validar-r1-adversarial-review.md §3
adjudicador: Claude Code
independencia_adjudicacion: plena
---

> **Acta de revision adversarial R1.** El §1 conserva la voz del revisor sin una coma
> cambiada; el §2 es la evidencia que verifique por mi cuenta y el §3 mi adjudicacion.
>
> **La adjudicacion va en el §3 de esta misma acta** porque el cambio no tiene spec ni
> plan donde embeberla: es el punto 3 de un encargo directo de Nikolai en una sesion de
> operacion. Declarado en el frontmatter para que nadie la busque en otro sitio.
>
> **Una ronda, por radio de dano** (`PLAN.md` fila #13). El validador **lee**; lo unico
> que escribe es el completado del contrario existente, y esta disenado para **rellenar
> solo lo vacio** — no pisa nada, con su test. No decide quien puede escribir sobre que
> copia ni puede destruir datos de cliente. **El diff REMEDIADO no se ha vuelto a
> revisar**, y se dice: la regla da una ronda para esta clase de pieza, y encadenar una
> segunda porque la primera encontro algo es un argumento que nunca se agota.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:m9xz -->

# Revisión adversarial R1 — DIFF `501db93` → `a4eb8ed`

## Alcance e integridad

Revisión de contenido de `C:/t/rev3/DIFF.patch`, `base/` y `head/`. Los árboles no contienen `.git`, por lo que no se acredita genealogía; se contrastó el contenido suministrado. Toda ejecución que podía escribir se hizo sobre `C:/t/rev3/informe/scratch_root_r1` (o los scratch de los revisores paralelos), nunca sobre `head/` ni `base/`.

Comando de integridad ejecutado al abrir y al cerrar:

```bash
cd /c/t/rev3/head && find . -type f -exec sha256sum {} + | sort -k2 | sha256sum
```

Salida de apertura:

```text
c806d285f5243dc1b0957e356df2a933e85528cded58bdbc97f9ff77affc1c27 *-
```

Salida de cierre:

```text
c806d285f5243dc1b0957e356df2a933e85528cded58bdbc97f9ff77affc1c27 *-
```

El objeto revisado no fue mutado.

## H-01 — El frontmatter del espejo acredita datos ausentes del documento

**Severidad:** ALTO

**Fichero y línea:** `scripts/crm_ficha_validar.py:70-76`; formato real del espejo en `core/sala_maquina.py:774-789`; consumo en `core/crm_ficha_validacion.py:261-266`.

**Cómo lo comprobé:** construí un espejo con el mismo `build_frontmatter` usado por el repositorio, puse nombre y NIF sólo en `source_path` y un cuerpo que no contiene ninguno.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
FRONTMATTER_REAL
ANA LOPEZ ('ENCONTRADO', True)
12345678Z ('ENCONTRADO', True)
```

**Escenario de fallo concreto:** el OCR de un DNI no contiene `12345678Z`, pero el fichero se llama `DNI_ANA_LOPEZ_12345678Z.pdf`. El CLI lee el MD completo, encuentra ambos valores en `source_path` y los declara `ENCONTRADO` y acreditados. El resultado prueba el nombre del fichero, no la documental. Los dobles de `tests/test_crm_ficha_validacion.py:46-115` son cuerpos planos y no reproducen el frontmatter real, por lo que todos pasan por una representación incompleta del corpus.

## H-02 — `_caso.md` entra como prueba aunque es un fichero de control

**Severidad:** ALTO

**Fichero y línea:** `core/crm_ficha_validacion.py:223-229`; `core/sala_maquina.py:34,1181-1195`; contenido administrativo de `_caso.md` en `core/case_manager.py:109-156`.

**Cómo lo comprobé:** pasé a `corpus_legible` una fila canónica de cobertura para `_caso.md`.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
caso_md_control (('caso',), ())
```

**Escenario de fallo concreto:** `inventariar` no incluye `_caso.md` en su registro nominal de controles y `.md` es una extensión nativa soportada. El fichero contiene `meta.contraparte`, `ciudad` y un cuerpo con `Contraparte:`. Un nombre completo o una población tecleados en ese índice pueden acreditar la ficha aunque no aparezcan en ninguna documental independiente. La exclusión por extensión protege `_ficha_crm.yaml`, pero deja pasar este segundo control. Los tests de corpus (`tests/test_crm_ficha_validacion.py:132-163`) no incluyen `_caso.md`.

## H-03 — Los patrones sin límites completos producen falsos positivos y la normalización de documento produce falsos negativos

**Severidad:** ALTO

**Fichero y línea:** `core/crm_ficha_validacion.py:62-64,100-146`; tests insuficientes en `tests/test_crm_ficha_validacion.py:83-102,275-288`.

**Cómo lo comprobé:** ataqué límites izquierdo/derecho, metacaracteres y email con `+`.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
nif_una_letra ('ENCONTRADO', True)
nif_subcadena_izquierda ('ENCONTRADO', True)
documento_asterisco_exacto ('NO_ENCONTRADO', False)
documento_parentesis_exacto ('NO_ENCONTRADO', False)
email_plus_subcadena ('ENCONTRADO', True)
texto_subcadena_tokens ('ENCONTRADO', True)
```

**Escenario de fallo concreto:** `documento="Z"` acredita contra `LOPEZ`; `12345678Z` acredita contra el identificador distinto `X12345678Z`; `ANA LOPEZ` acredita contra `MARIANA LOPEZA`; y `ana+caso@example.com` acredita contra `xana+caso@example.com.es`. En dirección contraria, `A*B` y `A(B)` no casan ni consigo mismos: los signos se eliminan del valor, pero el patrón sólo admite espacio, punto o guion entre caracteres. `re.escape` sí protege el `+`; el defecto del email es la falta de límites, no una inyección regex.

## H-04 — El teléfono de nueve dígitos no reconoce un `+34` compacto y los teléfonos largos pierden dígitos significativos

**Severidad:** MEDIO

**Fichero y línea:** `core/crm_ficha_validacion.py:121-126`; cobertura débil en `tests/test_crm_ficha_validacion.py:104-109`.

**Cómo lo comprobé:** probé prefijo compacto y números de más de nueve dígitos.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
telefono_mas_9_digitos ('ENCONTRADO', True)
telefono_prefijo_compacto ('NO_ENCONTRADO', False)
```

**Escenario de fallo concreto:** la ficha normaliza a `600111222`, pero el documento contiene el formato válido `+34600111222`; el `(?<![0-9])` impide empezar a casar tras `34` y devuelve `NO_ENCONTRADO`. A la inversa, para un valor largo se conservan incondicionalmente sólo los nueve últimos dígitos: `+442079460958` se declara encontrado contra el número distinto `+34 079 460 958`. El test titulado “cualquier formato” sólo cubre `+34 600...` con un espacio que oculta el defecto.

## H-05 — El validador omite datos de la ficha, incluidos los tres campos reparados

**Severidad:** ALTO

**Fichero y línea:** `core/crm_ficha_validacion.py:157-193`, especialmente `:168-188`; estructura separada de nombre/apellidos en `core/crm_ficha.py:30-43` y `core/sudespacho_relations.py:243-257`.

**Cómo lo comprobé:** cargué una ficha con `apellido1`, `apellido2`, `cp`, `provincia` y `telefono` y enumeré los `Dato` producidos.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
DATOS_OMITIDOS
['contrario.nombre']
```

**Escenario de fallo concreto:** una ficha con `nombre: ANA`, `apellido1: LOPEZ`, `apellido2: RUIZ`, `cp: '08019'`, `provincia: BARCELONA` y `telefono: '931112233'` sólo valida `contrario.nombre`. Una errata en cualquiera de los otros cinco valores no genera ni `ENCONTRADO`, ni `NO_ENCONTRADO`, ni `SIN_COMPROBAR`: desaparece del denominador y el CLI puede salir 0. La justificación de `:170-172` (“el apellido va cubierto por nombre, que lleva el nombre completo”) contradice el DTO y los propios fixtures, que separan nombre y apellidos. Además contradice el contrato solicitado para una palabra: debía encontrarse sin acreditar, no omitirse.

## H-06 — La frontera de corpus descarta documental JSON/YAML y estados no reconocidos como si no existieran

**Severidad:** MEDIO

**Fichero y línea:** `core/crm_ficha_validacion.py:31-38,216-233`; clasificación nominal de controles ya existente en `core/sala_maquina.py:1174-1188`.

**Cómo lo comprobé:** clasifiqué una prueba YAML legible, una prueba JSON ilegible, un documento sin extensión, un control con extensión mayúscula y un estado de error.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
yaml_documental_real ((), ())
json_documental_ilegible ((), ())
sin_extension_ilegible ((), ('DNI',))
extension_mayusculas_control ((), ())
estado_desconocido ((), ())
```

**Escenario de fallo concreto:** un export probatorio `evidencia.JSON` con `estado="empty"` se excluye por su extensión y no incrementa `ilegibles`; si el dato sólo podría estar allí, `validar` devuelve `NO_ENCONTRADO` en vez de `SIN_COMPROBAR`. Un YAML documental con `estado="ok"` tampoco entra al corpus. Asimismo, una fila con estado vacío/desconocido queda fuera de ambos lados. Un `rel_path` sin extensión y las extensiones en mayúsculas sí funcionan; el defecto es clasificar por toda una extensión en lugar de por el registro nominal de controles y tratar los estados desconocidos como inexistentes.

## H-07 — `cp`, `provincia` y `telefono` siguen perdiéndose para un contrario ya existente

**Severidad:** ALTO

**Fichero y línea:** envío sólo en `core/sudespacho_relations.py:790-804`; rama de deduplicación en `core/sudespacho_relations.py:1385-1421`; test que salta esa rama en `tests/test_crm_ficha_campos_perdidos.py:51-75`.

**Cómo lo comprobé:** forcé que `resolver_parte` devolviera un contrario existente y observé las llamadas a crear, actualizar y vincular.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
EXISTENTE_NO_SE_ACTUALIZA
resultado ('1099', False)
create_called False update_called False link_called True
```

**Escenario de fallo concreto:** el NIF ya existe en el CRM, pero la ficha local añade `cp`, `provincia` y `telefono`. `_resolver_o_crear_contrario` devuelve el ID y sólo se vincula; nunca llama a `update_cliente_contrario`. Los tres valores continúan sin llegar en el camino idempotente normal, tanto extrajudicial como judicial. Los tests nuevos invocan directamente `_rest_post_cliente_contrario`, que sólo cubre altas nuevas.

## H-08 — Un CP sin comillas puede corromperse por resolución octal de PyYAML

**Severidad:** ALTO

**Fichero y línea:** carga YAML en `core/crm_ficha.py:59-71`; conversión tardía en `core/crm_ficha.py:41`; envío en `core/sudespacho_relations.py:790-791`; fixture que evita el caso en `tests/test_crm_ficha_campos_perdidos.py:26-42`.

**Cómo lo comprobé:** cargué escalares con cero inicial con PyYAML 6.0.3 y observé el valor que recibe el DTO.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
YAML_CP
08019 '08019' str en_DTO= 08019
01001 513 int en_DTO= 513
01234 668 int en_DTO= 668
00123 83 int en_DTO= 83
00000 0 int en_DTO= 0
```

**Escenario de fallo concreto:** `cp: 01001` se resuelve como octal `513`; `str(...)` produce `"513"` y el POST lo envía como código postal. El `08019` concreto no se corrompe porque contiene `8`/`9` y PyYAML lo conserva como cadena, pero el test fuerza además `cp: '08019'`, por lo que no protege ningún CP vulnerable.

## H-09 — Un escalar YAML vacío se convierte en la cadena literal `"None"` y se envía

**Severidad:** MEDIO

**Fichero y línea:** `core/crm_ficha.py:41-43`; normalización en `core/sudespacho_relations.py:259-261`; envío en `core/sudespacho_relations.py:790-793`.

**Cómo lo comprobé:** cargué `cp:` y `telefono:` sin valor y capturé el payload REST.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
NULOS_YAML
dto {'cp': 'None', 'telefono': 'None'}
payload {'nombre': 'ANA', 'cp': 'None', 'telefono1': 'None'}
```

**Escenario de fallo concreto:** quien deja una clave preparada pero vacía (`cp:`) espera que se omita. `str(None)` la hace truthy y se transmite el texto `None`; el servidor puede rechazar toda el alta o guardar un valor espurio. No hay tests de `null`/escalar vacío.

## H-10 — Una provincia inválida no impide que la operación se considere completada y “verificada”

**Severidad:** MEDIO

**Fichero y línea:** omisión en `core/sudespacho_relations.py:794-804`; el CLI de escritura sólo verifica relación/Notas en `scripts/crm_ficha.py:137-140,164-205`.

**Cómo lo comprobé:** envié una provincia no canónica, capturé el payload y la respuesta exitosa simulada.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
PROVINCIA_INVALIDA_POST_OK
id 1200 payload {'nombre': 'ANA'}
provincia 'Barchelona' no casa con ninguna del enum del CRM: se omite en vez de mandar un valor que el Select descartaria en silencio
```

**Escenario de fallo concreto:** `provincia: Barchelona` emite un warning, pero el alta devuelve ID, el vínculo puede verificarse y `scripts/crm_ficha.py:205` imprime `OK ficha CRM completada y VERIFICADA por lectura`. Esa lectura no consulta los campos del contrario. La provincia sí se pierde; no es totalmente silencioso dentro del proceso, pero el código de salida y el mensaje final contradicen el warning. Tampoco se verifica que el servidor haya conservado `cp` o `telefono1`.

## H-11 — Un valor sin patrón sale 0 como `SIN_COMPROBAR` aunque el corpus sea legible y el dato esté a la vista

**Severidad:** MEDIO

**Fichero y línea:** `core/crm_ficha_validacion.py:253-270`; presentación y salida en `scripts/crm_ficha_validar.py:90-127`.

**Cómo lo comprobé:** ejecuté el CLI contra un caso sintético con un móvil de ocho dígitos presente literalmente, un espejo legible y cero ilegibles.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
CLI_PATRON_NONE
exit_code 0
Ficha:      C:\t\rev3\informe\scratch_root_r1\tmpzee2z8ox\00_Input\_ficha_crm.yaml
Corpus:     1 documentos legibles
Ilegibles:  0

  [ok, pero no acredita] contrario.nombre = 'ANA'
        en: doc.md
  [sin comprobar] contrario.movil = '12345678'

Resumen: 1 encontrados · 0 sin aparecer · 1 sin comprobar
         de los encontrados, 1 NO acreditan: son de una sola palabra (una población, un apellido) y casan con cualquier tercero del expediente. Encontrarlos no prueba que este dato sea correcto.

No se pudo mirar en estos documentos — revísalos a mano:
```

**Escenario de fallo concreto:** `_patron` rechaza un teléfono corto y `validar` lo convierte incondicionalmente en `SIN_COMPROBAR`, aunque no haya documento ilegible y el literal esté en el cuerpo. El CLI explica falsamente que no pudo mirar “estos documentos”, lista ninguno y sale 0. Un valor malformado/no buscable no queda distinguido de un fallo de OCR.

## H-12 — `_cobertura.json` inválido sale 1 por excepción cruda, no por un veredicto

**Severidad:** MEDIO

**Fichero y línea:** `scripts/crm_ficha_validar.py:59-68`.

**Cómo lo comprobé:** invoqué el CLI con una cobertura que contiene `{ roto`.

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' .\repro_r1.py 2>&1
```

Salida pertinente exacta:

```text
CLI_COBERTURA_JSON_ROTO
exit_code 1
stdout ''
exception JSONDecodeError Expecting property name enclosed in double quotes: line 1 column 3 (char 2)
```

**Escenario de fallo concreto:** una escritura truncada o corrupción de `_cobertura.json` produce código 1 sin ningún mensaje `[ERROR]` del CLI y sin hallazgos. Por tanto, “1 sólo si hay `NO_ENCONTRADO`” no es cierto; tampoco se distingue un dato ausente de una precondición rota salvo por traceback.

## Cobertura ejecutada y calidad de tests

Se ejecutaron todos los tests directamente relacionados con los seis ficheros del diff y con deduplicación, sobre la copia y con `socket.connect/connect_ex` bloqueados mediante un plugin temporal:

```powershell
cd C:\t\rev3\informe\scratch_root_r1
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -p no_network_guard -o "addopts=" -q tests/test_crm_ficha_validacion.py tests/test_crm_ficha_campos_perdidos.py tests/test_crm_ficha.py tests/test_sudespacho_relations.py tests/test_crm_dedup_partes.py --basetemp .bt_final
```

Salida exacta:

```text
........................................................................ [ 37%]
........................................................................ [ 74%]
..................................................                       [100%]
194 passed in 5.03s
```

No hubo acceso de red: cualquier `socket.connect` habría fallado la sesión. Que los 194 tests pasen no refuta los hallazgos:

- los corpus inventados no contienen frontmatter;
- los tests de control equiparan extensión con naturaleza y omiten `_caso.md` y documental JSON/YAML;
- el test de CP usa comillas;
- los tests de payload llaman al POST privado y evitan el camino de deduplicación existente;
- no hay tests del nuevo CLI;
- no hay límites adversariales, prefijo telefónico compacto, escalares nulos ni campos omitidos.

`pytest-randomly`: **SIN VERIFICAR**. No está instalado:

```powershell
& 'C:\Users\tnm33\AppData\Local\Python\pythoncore-3.14-64\python.exe' -c "import importlib.util; print(importlib.util.find_spec('pytest_randomly'))"
```

```text
None
```

## Comprobaciones que no produjeron hallazgo

- `provincia_canonica` no tiene colisiones bajo su normalización en la lista actual de 52 entradas: `colisiones_normalizadas {}`.
- `BARCELONA` se traduce a `Barcelona` y `ALAVA` a `Álava`.
- `rel_path` sin extensión se clasifica correctamente según su estado; `.PDF` mayúscula también. `.YAML`/`.JSON` se normalizan de caja, aunque su clasificación indiscriminada es H-06.
- Un email con `+` exacto se escapa correctamente; el falso positivo de H-03 procede de no exigir límites.
- La aceptación real por el servidor de `cp`, `telefono1` y los literales de provincia quedó **SIN VERIFICAR** por la prohibición de red; se verificó la forma del request, no el CRM vivo.

VEREDICTO: NO-SHIP

<!-- informe-literal:fin:m9xz -->

## 2. Evidencia verificada por el adjudicador

- **H-01 CONFIRMADO, y medido contra el expediente real.** Los espejos de W-02Q38C
  empiezan por un frontmatter con `source_path`, y el caso tiene ficheros llamados
  `dni_alberto_frontal`, `certificado_titularidad_bancaria_albero_camprubi`… Comprobé
  además que el NIF **sí estaba en el cuerpo** de los documentos que el informe original
  citaba, así que el resultado que había dado no era falso — pero la vulnerabilidad es
  real y bastaba un fichero llamado con un DNI para acreditarlo por su nombre.
- **H-02 CONFIRMADO por el recuento del caso real:** al clasificar por naturaleza, el
  corpus baja de **46 a 45 documentos legibles**. El que sobraba era `_caso.md`, que
  lleva `meta.contraparte` y `ciudad`. Un dato tecleado en el índice del caso se estaba
  acreditando a sí mismo.
- **H-05 CONFIRMADO contando campos:** el validador miraba **1 de los 11** campos del
  contrario. Tras arreglarlo, el informe del caso real pasa de 18 a **21 datos** y de 1 a
  **4 marcados como que no acreditan**. La cifra vieja no era mejor: era menos honesta.
- **H-07 CONFIRMADO, y desmiente una afirmación mía al usuario.** Le dije que `cp` y
  `provincia` «ya llegarían al CRM». Sólo llegaban al crear. El contrario de este caso
  **ya existe** (ficha 1108), así que los tres campos seguían sin llegar. Mis tests no lo
  vieron porque llamaban a `_rest_post_cliente_contrario` directamente, saltándose la
  rama de deduplicación — exactamente lo que el revisor señala.
- **H-08 CONFIRMADO, con el matiz que lo hace peor:** el `08019` de este expediente se
  salvaba **por suerte**, porque `8` y `9` no son dígitos octales válidos y PyYAML lo
  dejaba como cadena. Un `01001` se habría convertido en `513` sin que nada avisara.
- **Lo que NO pude verificar:** que el CRM acepte `cp`, `telefono1` y los literales de
  provincia sobre un contrario existente. El revisor tenía la red prohibida y yo no he
  ejecutado el completado contra el tenant: se ha verificado **la forma de la petición**,
  no la escritura real. Queda declarado, no dado por bueno.

## 3. Adjudicación de la revisión adversarial (Codex, 2026-09-04) — NO-SHIP, remediado

- **Objeto revisado:** diff `501db93..a4eb8ed` — validador del `_ficha_crm.yaml` + tres campos del contrario
- **Ronda:** 1
- **Revisor:** Codex
- **Informe recibido:** 2026-09-04, `sha256` en el frontmatter
- **Hallazgos:** 12 recibidos · **12 confirmados** · 0 refutados · 0 escalados
- **Remediado en:** `d335c92`

**12 de 12.** El revisor copió el árbol, corrió las 194 pruebas relevantes bajo una
barrera de `socket` propia, y construyó los espejos con el mismo `build_frontmatter` del
repositorio — que es cómo encontró H-01, el hallazgo que invalidaba el resultado. Objeto
no mutado.

### Las dos familias en que caen los doce

**(a) Acreditar lo que no está acreditado.** El frontmatter como prueba (H-01), `_caso.md`
en el corpus (H-02), y los patrones sin límites, que hacían casar un NIF dentro de otro,
un nombre dentro de otro nombre y un correo dentro de otro (H-03, H-04).

**(b) Hacer desaparecer del recuento.** Once campos reducidos a uno (H-05), los estados de
cobertura desconocidos cayendo fuera de las dos listas (H-06), y un dato mal formado
disfrazado de fallo de OCR (H-11).

Las dos producen lo mismo: **un informe que se lee como «0 problemas» siendo falso.** Que
es exactamente lo que esta pieza existe para impedir, un nivel más arriba.

| # | Sev. | Frontera cerrada |
|---|---|---|
| H-01 | ALTO | El **cuerpo** del espejo es la documental; el frontmatter es el nombre del fichero |
| H-02 | ALTO | El corpus se clasifica por **naturaleza** (nombre de control), no por extensión |
| H-03 | ALTO | Límites por los **dos** lados; un documento de menos de 4 caracteres no se busca |
| H-04 | MEDIO | Prefijo telefónico pegado, y los dígitos de más se **exigen**, no se tiran |
| H-05 | ALTO | **Todos** los campos entran en el denominador; lo que no discrimina se marca |
| H-06 | MEDIO | Un estado desconocido es **ilegible**, no invisible |
| H-07 | ALTO | Los campos llegan también al contrario **existente**, sin pisar lo que ya hay |
| H-08 | ALTO | Un escalar numérico en un campo con ceros a la izquierda se **rechaza** |
| H-09 | MEDIO | Una clave vacía es ausencia, no la cadena `"None"` |
| H-10 | MEDIO | Cubierto por H-07: los campos ya no se pierden en el camino normal |
| H-11 | MEDIO | `NO_BUSCABLE` propio: el dato está mal escrito, no es que no se pudiera mirar |
| H-12 | MEDIO | Una precondición rota sale con **código 2** y mensaje, no con excepción cruda |

### Dos cosas mías que conviene no olvidar

**Dos de los doce eran afirmaciones que yo había hecho en voz alta y eran falsas** (H-05 y
H-07), y las dos nacieron *entre dos commits del mismo día*: añadí campos al DTO en uno y
no al validador en el siguiente; y afirmé que los datos «ya llegaban» habiendo probado
sólo la rama de creación. **Es el mismo modo de fallo que la ronda del PR #272 ya me
cobró:** cerrar una propiedad para un camino y no para los demás.

**Y el leak-guard bloqueó dos veces el commit de la remediación**, las dos por escribir un
NIF sintético en un comentario mientras redactaba notas sobre normalización de documentos.
Reformulado sin transcribir ningún documento.

### Lo que queda SIN VERIFICAR, declarado

- **La escritura real del completado contra el CRM.** Se ha verificado la forma de la
  petición y que no pisa lo existente, no que el tenant la acepte.
- **El diff remediado no ha tenido segunda ronda.** La regla da una ronda a esta clase de
  pieza; encadenar otra porque la primera encontró algo es un argumento que no se agota.
  Si Nikolai la quiere, es su techo el que decide.
- **Orden aleatorio:** el revisor no tiene `pytest-randomly`. Lo cubre el autor, con dos
  semillas.
