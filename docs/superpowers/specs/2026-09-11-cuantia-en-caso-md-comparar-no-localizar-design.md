---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-11
---

# La cuantía llega a `_caso.md` — comparar en vez de localizar (`MEJORAS #227`)

Segundo intento de `MEJORAS #227`, pieza **P7** de la fila #28 de `PLAN.md`. El primero
—`update_meta` con heurísticas de líneas— se retiró el 2026-09-11 por decisión de Nikolai tras
dos rondas adversariales: `docs/superpowers/plans/2026-09-11-identidad-sin-teclado.md` §5, con sus
actas `-r1-` y `-r2-`.

**Rev. 2 — 2026-09-11, tras la R1.** El documento fue objeto de la R1, que volvió
`REQUIERE-REVISION` con **9 hallazgos, 2 ALTOS, los 9 confirmados**. La adjudicación está en el
§10 y el diseño de abajo **ya está corregido**: lo que se lee aquí es la rev. 2, no la revisada.
La R2 irá sobre el diff. Presupuesto de 2 rondas fijado por el radio de daño —la pieza escribe en
el índice del expediente y puede destruir una nota del letrado—, no por el tamaño del fichero.

## 1. El defecto, y por qué el primer diseño no podía cerrarlo

La cuantía se conoce al leer el encargo, pero el alta en el CRM va **al final** de la apertura
(`feedback-crm-alta-al-final-no-durante-intake`). Cuando llega, `_caso.md` ya existe, así que
`--cuantia` acaba en el CRM y **no** en el índice local, que se queda en `- Cuantía: _(pendiente)_`.
`ensure_case` no puede reponerlo: su contrato es crear, y sobre un caso existente solo actualiza
`tipo_caso`, `direccion`, `id_go` y `ciudad`. `cuantia` y `referencia_crm` no tienen registrador.

El primer diseño añadía `update_meta`, que **buscaba** la línea a sustituir dentro del cuerpo
Markdown. Las dos rondas encontraron **seis formas** de romper esa misma propiedad: preámbulo que
se come una sección `###`; encabezados con la sangría que CommonMark permite; cercas de distinto
carácter o longitud; cercas sin cerrar; inserción fuera del ámbito recién validado; duplicación de
la línea al repetir. Cada ronda remedié *el caso del informe* y no *la propiedad de la que era
ejemplo* — [[feedback-remediar-la-frontera-no-el-ejemplo]].

**Localizar un fragmento de Markdown con heurísticas de líneas no es una función que se pueda
depurar hasta que esté bien.** Es una clase de defecto con una cola infinita, y su coste es una
nota del letrado destruida. Eso es lo que `MEJORAS #146` existe para impedir.

## 2. El diseño: no localizar, comparar

El cuerpo canónico de un `_caso.md` lo genera `_cuerpo_del_indice(meta)`
([`core/case_manager.py:183`](../../../core/case_manager.py)). La propuesta:

> Si el cuerpo del fichero **es exactamente** el que `_cuerpo_del_indice` produciría para la `meta`
> que trae el frontmatter, se reescribe entero con la `meta` nueva. Si difiere **en cualquier
> cosa**, no se toca el cuerpo: se escribe el frontmatter y se **declara**.

Un problema de *parsing* convertido en una **igualdad de cadenas**.

### 2.1 El teorema, y las DOS fronteras que la R1 encontró bajo él

Sea `C` el cuerpo del fichero, `M` la `meta` reconstruida desde el frontmatter y `M'` la misma con
los campos nuevos aplicados.

- **Si `C ≠ _cuerpo_del_indice(M)`** → el cuerpo **no se reescribe**, y además **sus bytes no se
  tocan**: la escritura sustituye *solo el bloque de frontmatter* (§2.3).
- **Si `C = _cuerpo_del_indice(M)`** → se escribe `_cuerpo_del_indice(M')`. Como `M'` difiere de `M`
  **solo** en los campos de la lista blanca (§3.1), la diferencia entre `C` y el cuerpo nuevo es
  exactamente lo que esos campos renderizan.

**La rev. 1 se quedaba aquí, y era falso por dos sitios.** La R1 ejecutó los dos:

1. **La garantía se enunció sobre cadenas y el fichero está hecho de bytes** (H-01). `write_md`
   hace `body.strip()` y escribe con la convención de saltos de la plataforma, así que «conservar
   el cuerpo» pasándolo otra vez por el escritor **le quita los espacios finales** de la nota del
   letrado y, en Windows, **le cambia los finales de línea a toda la nota**. Medido: una nota que
   acaba en `CONSERVAR` + dos espacios vuelve del escritor sin esos dos espacios. Ninguna
   comparación falla aquí: **el texto se pierde en la rama que prometía no tocar nada.** Es la
   misma clase de defecto que la vía (d) venía a matar, reaparecida **en la capa de E/S** en vez de
   en el parser.
2. **La comparación es sobre texto normalizado, no sobre bytes** (H-01, tercera mitad). `read_md`
   lee con traducción universal de saltos, y `_FM_RE` acaba en un `\s*` que se come las líneas en
   blanco que haya tras el `---` de cierre. Así que un fichero con una línea en blanco de más entre
   el frontmatter y el cuerpo **iguala** al canónico. Un falso positivo, entonces, **no** exige que
   el letrado haya escrito la plantilla entera a mano, como decía la rev. 1: basta un blanco.

### 2.2 Lo que la rev. 2 garantiza, dicho en bytes

- **Rama conservada:** los bytes del fichero desde el final del frontmatter hasta EOF quedan
  **idénticos**. Se sustituye únicamente el tramo que `_FM_RE` delimita.
- **Rama canónica:** el fichero se regenera por `write_md`, igual que hacen hoy los tres
  registradores. La garantía es entonces **de contenido, no de bytes**: el `strip()` y la
  convención de saltos de la plataforma se aplican como en cualquier otra escritura del índice. Lo
  único que cambia respecto del contenido anterior es lo que renderizan los campos de la lista
  blanca.
- **El falso positivo residual** —líneas en blanco entre el frontmatter y el cuerpo, que la rama
  canónica normaliza— **se declara**, no se niega: es cosmético, lo produce ya cualquier
  registrador, y no puede alcanzar a texto del letrado, porque cualquier carácter suyo en el cuerpo
  rompe la igualdad.

### 2.3 Cómo se sustituye el frontmatter sin tocar el cuerpo

La frontera **no es una heurística**: `_FM_RE` está anclada al principio del fichero y delimitada
por `---`. Su `m.end()` es el primer carácter del cuerpo.

```python
crudo = index.read_text(encoding="utf-8")            # traducción universal de saltos
m = _FM_RE.match(crudo)
if m is None:                                        # índice sin frontmatter: no se escribe
    return informe_sin_tocar(...)
nuevo = build_frontmatter(fm_nuevo) + "\n" + crudo[m.end():]
index.write_text(nuevo, encoding="utf-8", newline="")
```

`newline=""` es lo que impide que Python vuelva a traducir los saltos del cuerpo al escribir; sin
él, un cuerpo leído de un fichero LF sale en CRLF y el «no lo toco» es falso. El salto intercalado
replica lo que `write_md` pone entre el frontmatter y el cuerpo, de modo que un fichero canónico
escrito por `write_md` y reescrito por esta vía sale idéntico.

**La escritura sigue siendo atómica** (temporal en el mismo directorio + `os.replace`), como
`_escribir_indice_atomico`: el cambio es qué se escribe, no cómo se reemplaza.

**Si el fichero no tiene frontmatter parseable, no se escribe nada** y el informe lo dice (§3.4).
Un índice roto no se convierte en alta nueva por esta vía.

### 2.4 Lo que esto NO arregla, dicho por delante

No toca `_actualizar_cuerpo`, que es la vía por la que los registradores (`register_expediente`,
`register_drive_ev`, `cache_drive_folder_info`) actualizan sus tres fragmentos. Esa función tiene
sus propias heurísticas de líneas y sigue como está: es el remedio de `MEJORAS #146` y lleva dos
rondas encima. `MEJORAS #184` y `#192` siguen abiertas y nada de esto las cierra.

## 3. La API

### 3.1 Lista blanca de campos, no `**campos` abierto

```python
# `core/case_manager.py`
CAMPOS_ACTUALIZABLES = frozenset({"cuantia", "referencia_crm"})
```

Los **únicos** dos campos de `CaseMeta` que se conocen después de crear el caso y **no tienen
registrador propio**. Todo lo demás se rechaza con `ValueError`:

- `direccion`, `id_go`, `tipo_caso`, `ciudad` → los actualiza `ensure_case` sobre un caso existente.
- `drive_ev_*` → `register_drive_ev` y `cache_drive_folder_info`.
- `sudespacho_expedientes` → `register_expediente` / `update_pull_state`, con su fusión por entrada.
- `estado_repositorio` y los `checkout_*` → la biblioteca de casos, bajo su propio protocolo.

Esto cierra *por construcción* —no por una comprobación— que un campo entre por descuido: para
añadir uno hay que editar esta constante y justificar por qué no tiene otro hogar.

**Lo que la lista blanca NO hace, y la rev. 1 dijo que sí** (H-03 y H-02 de la R1): acotar **lo que
se escribe**. Acota lo que se *pide*. La escritura la gobierna el §3.3, y ahí está el arreglo real.

**Y la justificación de arriba era demasiado amplia** (H-03): no es cierto que `cuantia` y
`referencia_crm` sean los únicos campos que se conocen tarde y carecen de registrador. `cliente`,
`contraparte`, `organo`, `titulo`, `drive_link` y `drive_remote_path` **solo** se escriben al
crear: `ensure_case` no los repone sobre un caso existente. La lista blanca se queda en dos por
**alcance de `#227`**, no porque los demás estén cubiertos. Los huecos van al backlog, no a esta
pieza — ampliarla «ya que estamos» es exactamente lo que este documento existe para no hacer.

### 3.2 Firma y contrato

```python
def update_meta(case_id: str, **campos) -> dict:
    """Fija campos de `CaseMeta` en `_caso.md` sin poder destruir el cuerpo.

    Cada clave de `campos` SE ESCRIBE, incluido `None`: pasar una clave es la orden
    de escribirla. El que no quiera escribir un campo NO PASA LA CLAVE —un default
    no es una orden de escribir (R2/H2-06 del primer intento).

    Devuelve el informe; NO lanza cuando el cuerpo queda sin tocar, porque eso no
    es un error: es el caso normal de un expediente con notas.
    """
```

**Informe devuelto**, y el llamante está obligado a decirlo por pantalla:

```python
{
    "case_id": "…",
    "frontmatter": ["cuantia"],        # claves efectivamente escritas, ordenadas
    "cuerpo": "reescrito",             # "reescrito" | "conservado" | "sin tocar"
    "motivo": None,                    # si no es "reescrito": por qué, en una frase
}
```

Tres estados, no dos (H-08): `"conservado"` es «escribí el frontmatter y dejé tu cuerpo»;
`"sin tocar"` es **«no escribí nada»**, que es lo que pasa con un índice ilegible. Confundirlos
sería el «OK» que describe el paso y no el expediente.

`motivo` no es decorativo: es la única forma de que el letrado sepa que el cuerpo de su `_caso.md`
dice `_(pendiente)_` y el frontmatter no. Sin eso la pieza miente por omisión.

### 3.3 El frontmatter se escribe con las claves PROPIAS y nada más

**La rev. 1 proponía factorizar la fusión de `_actualizar_indice` y reutilizarla. Era un error, y
la R1 lo ejecutó** (H-02, ALTO). Esa fusión hace mucho más que conservar claves ajenas: reconcilia
la lista de expedientes con `_fusionar_expedientes` y regenera las diez claves superiores. Y la
reconciliación **revierte datos**:

```
tras register_expediente('10','expedientes_judiciales') + update_pull_state('10', element='extrajudiciales')
  lista TOP LEVEL : [{'id':'10', 'element':'extrajudiciales',        'last_sync':'2026-09-11'}]
  ESPEJO en meta  : [{'id':'10', 'element':'expedientes_judiciales'}]
  _fusionar(top, espejo) -> [{'id':'10', 'element':'expedientes_judiciales', 'last_sync':'…'}]
```

`update_pull_state` escribe en la lista **superior** y deja el espejo de `meta` como estaba;
`_fusionar_expedientes` aplica el espejo **encima** y el `element` vuelve atrás. Un `update_meta`
que reutilizara esa fusión para fijar la cuantía **revertiría un dato que no pidió tocar**, en
silencio. La frontera es: *una lista blanca de argumentos no acota lo que se escribe.*

**La rev. 2 no factoriza nada.** `update_meta` parte del `fm` leído del disco y escribe **solo sus
propias claves**, enumeradas:

```python
fm_nuevo = copy.deepcopy(fm)                    # todo lo demás, intacto
meta_nuevo = dict(fm_nuevo.get("meta") or {})
for clave, valor in campos.items():             # solo CAMPOS_ACTUALIZABLES
    meta_nuevo[clave] = valor
meta_nuevo["actualizado_en"] = now_iso()
fm_nuevo["meta"] = meta_nuevo
if "referencia_crm" in campos:                  # este campo tiene DOS hogares
    fm_nuevo["referencia_crm"] = campos["referencia_crm"]
```

`referencia_crm` vive además en el nivel superior del frontmatter
(`_frontmatter_del_indice`); `cuantia` **no**. Los dos hogares se enumeran aquí porque son dos, no
porque haya una regla: **cada campo de la lista blanca declara sus hogares, y hay un test que
recorre `_frontmatter_del_indice` y falla si aparece un hogar nuevo que nadie ha enumerado.**

Nada más se toca: ni `sudespacho_expedientes` (arriba o en el espejo), ni `estado`, ni `fecha`, ni
`bucket_override`, ni ninguna clave ajena. `_actualizar_indice` se queda **exactamente como está**.

La escritura es atómica —temporal en el mismo directorio y `os.replace`— y la hace la vía del
§2.3, no `write_md` en sitio.

### 3.4 Contrato de entrada: cuándo NO se escribe (H-08)

`update_meta` **no normaliza un índice que no puede preservar**. Se abstiene, sin escribir, y lo
dice en el informe, en estos casos:

| Entrada | Qué hace |
|---|---|
| el caso no existe o no hay `00_Input/_caso.md` | `FileNotFoundError` |
| una clave fuera de `CAMPOS_ACTUALIZABLES` | `ValueError` nombrando el campo **y su hogar** |
| `campos` vacío | `ValueError`: llamar sin nada que escribir es un error del llamante |
| el fichero no empieza por frontmatter parseable (`_FM_RE` no casa, BOM, YAML inválido) | **no escribe**; informe con `cuerpo="sin tocar"` y `motivo` |
| `fm["meta"]` no es un mapa | ídem |
| `fm["meta"]` no permite reconstruir `CaseMeta` | ídem: sin `meta_previa` no hay con qué comparar |

La reconstrucción de `CaseMeta` **filtra por los nombres del dataclass**: una clave ajena en
`meta` —hay `_caso.md` con ellas, y el modelo promete conservarlas— haría `TypeError` con
`CaseMeta(**m)`. El filtrado es contrato, no detalle de la sonda.

**Lo que ninguna de las dos ramas puede conservar, y se dice aquí en vez de prometerlo:** los
comentarios YAML del frontmatter y la primera de dos claves duplicadas. Los borra `yaml.safe_load`
al leer, antes de que esta pieza vea nada. La garantía de esta pieza es sobre **el cuerpo**; sobre
el frontmatter es «las claves que había siguen estando, con su valor».

## 4. La medición: ¿alguna vez se cumple la igualdad?

**La pregunta que decide si la pieza sirve para algo.** Si los registradores rompieran la
canonicidad, la vía (d) no reescribiría el cuerpo nunca y sería un no-op caro.

Sonda ejecutada el 2026-09-11 (`CASOS_ROOT` a un temporal, no escribe en el árbol de producción).
Reconstruye `CaseMeta` desde `fm["meta"]` filtrando por los nombres del dataclass, y compara
`_cuerpo_del_indice(meta)` con el cuerpo leído:

| Forma | ¿canónico? |
|---|---|
| caso mínimo (solo `case_id`), tras `ensure_case` | **sí** |
| caso completo (título, partes, órgano, cuantía, Drive, referencia CRM) | **sí** |
| `ensure_case` por segunda vez (idempotencia) | **sí** |
| tras `register_expediente` × 2 (sección `## Expedientes sudespacho` presente) | **sí** |
| tras `register_drive_ev` | **sí** |
| tras `cache_drive_folder_info` | **sí** |
| tras `update_pull_state` | **sí** |

**Y la sonda puede dar el otro valor** — [[feedback-guarda-inerte-comprobar-el-otro-valor]]. Dos
controles negativos, los dos rojos como se esperaba:

| Control negativo | ¿canónico? |
|---|---|
| una sección `## Notas del letrado` insertada a mano | **no** |
| **un solo espacio de más** tras `## Partes` | **no** |

Conclusión medida: **en el camino normal de la apertura la igualdad se cumple**, que es justo el
caso de `#227` (el alta CRM llega al final sobre un `_caso.md` que solo han tocado los
registradores). En cuanto hay una nota, no se cumple — y entonces la pieza no toca el cuerpo, que
es lo que se quiere.

**Lo que esta medición NO dice:** que se cumpla sobre los `_caso.md` **reales** del Drive, escritos
por versiones anteriores del código. No los he mirado. Sobre un índice legacy la igualdad fallará y
el cuerpo se conservará — degradación segura, pero degradación. Queda declarado, no resuelto.

## 5. El precio, medido antes de pagarlo

El §5 del plan anterior lo anotó así: «en un `_caso.md` con notas la cuantía solo llega al
frontmatter — y ese precio hay que medirlo antes de pagarlo, porque hoy el único lector de
`meta.cuantia` es la línea del cuerpo».

**Esa frase dejó de ser cierta el mismo día en que se escribió.** `git grep` sobre el consumo:

```
core/verificar_apertura.py:797   fm, err = _frontmatter(case_dir)
core/verificar_apertura.py:798   meta = fm.get("meta") if isinstance(fm.get("meta"), dict) else {}
core/verificar_apertura.py:799   local_crudo = meta.get("cuantia")
```

`c9_cuantia_coherente` —la comprobación que cruza la cuantía local con la del CRM, entrada con el
PR #344 a las 09:38 del 2026-09-11— lee **el frontmatter**, no la línea del cuerpo. Y
`_frontmatter_del_indice` vuelca `"meta": asdict(meta)` entero, así que el dato está ahí.

**Por tanto el precio es menor de lo que el diseño anterior temía:** en un `_caso.md` con notas, la
comprobación cruzada contra el CRM sigue funcionando; lo único que se degrada es lo que **lee un
humano** en el cuerpo. Y eso lo cubre el `motivo` del informe.

**Dicho con la precisión que la R1 exigió** (H-07): no hay ningún otro lector **determinista y en
Python** del valor. El resto de apariciones de `cuantia` en `core/` y `scripts/` son del payload
del CRM (`sudespacho_create`) o de la firma de `ensure_case`, y ninguna lee `_caso.md`. Pero el
fichero lo leen además dos consumidores que un `git grep` por `cuantia` no encuentra:

- **el visor de la UI** (`streamlit_app.py`), que renderiza el `_caso.md` entero y por tanto
  seguiría enseñando la línea `- Cuantía: _(pendiente)_`;
- **las skills del despacho**, que mandan leer la cuantía de `_caso.md` sin fijar precedencia entre
  sus dos representaciones, y que **no ven el informe de consola** de `update_meta`.

Los dos leen un fichero que se contradice consigo mismo. Qué valor escogería un modelo ante esa
contradicción **no se ha medido y queda SIN VERIFICAR**. Por eso el `motivo` del informe no basta
como único aviso, y el precio real de la vía (d) es **mayor que el que decía la rev. 1** — aunque
sigue siendo muy menor que el de la vía que destruye notas.

## 6. Dos cosas que volvieron del intento retirado, y una es un defecto vivo en `main`

Verificado por contenido sobre `origin/main` el 2026-09-11, no por la prosa del plan.

### 6.1 El default de `--cuantia` NO se conservó, y el plan dice que sí

El §4 del plan anterior afirma, de la remediación de H2-06: «**Se conserva aunque la pieza se
retire**, porque la frontera vale para cualquier flag que acabe escribiendo en el expediente».

```
$ git show origin/main:scripts/abrir_caso.py | grep 'cuantia.*typer.Option'
    cuantia: float = typer.Option(0.0, "--cuantia"),
```

Se fue entero con el PR #338 cerrado, sus cinco tests incluidos. **Hoy no es un defecto** —sin
`update_meta`, ese `0.0` solo alimenta `crm_payload`— pero es exactamente la mina que esta pieza
rearma: en cuanto `update_meta` escriba la cuantía, repetir el comando sin el flag la pisaría con
cero. Medido entonces de punta a punta: `before=73140.5`, `after=0.0`, `crm_amounts=[73140.5]`.

**Entra en esta pieza:** `--cuantia` pasa a `float | None = typer.Option(None, …)`, y la clave solo
se pasa a `update_meta` cuando el flag vino. Y **hay que corregir esa frase del plan anterior**, que
en `main` afirma algo falso.

**Con una cautela que la R1 encontró y la rev. 1 no** (H-04): ese mismo valor va también a
`crm_payload(ident, cuantia=cuantia)`, y de ahí al DTO del CRM, donde se hace aritmética
(`datos.cuantia + datos.costas + datos.intereses`). Un `None` propagado hasta ahí revienta el alta
en un caso que hoy funciona. **La ausencia del flag se traduce a `0.0` en la frontera del payload y
a «no escribir la clave» en la frontera local**; son dos políticas distintas del mismo hecho y se
escriben por separado. Tiene su propio test: alta sin `--cuantia`, alta con `--cuantia 0`, alta con
cuantía.

### 6.2 H-05 sigue vivo en `main`: «Alta CRM falló» con el alta hecha

```python
# scripts/abrir_caso.py:741-749, en origin/main
try:
    exp_id = sudespacho_create.create_expediente(payload)
    case_manager.register_expediente(ident.case_id, exp_id, _ELEMENT_EXTRAJUDICIAL)
    typer.echo(f"OK CRM id={exp_id}")
except Exception as exc:
    typer.echo(f"[AVISO] Alta CRM falló ({exc!r}): …")
```

El `except` cubre **las dos** llamadas. Si el alta funciona y el registro local falla, el mensaje
dice que falló el alta: el letrado reintenta, el CRM ya tiene el expediente y el reintento es
estéril o duplica. La R1 lo encontró, el plan lo dio por «retirado con la pieza», y **no lo estaba**:
es código de `main` que el `update_meta` retirado no tocaba.

**Entra en esta pieza** porque la escritura de `update_meta` va justo detrás y multiplicaría la
confusión: tres actos (alta, registro, índice) bajo un solo mensaje de fallo. Se separan en tres,
cada uno diciendo lo suyo.

**Y son cuatro desenlaces, no tres** (H-05): alta falla · alta bien + registro falla · alta y
registro bien + **índice falla** · todo bien. El cuarto es el que introduce esta pieza y el que la
rev. 1 olvidó enumerar.

**Lo que esta pieza NO intenta, y se dice para no prometerlo:** automatizar la reparación. Si el
alta funcionó y el índice no, el reintento entra por la guarda de idempotencia («CRM ya
registrado») y **retorna antes** de llegar a la escritura, así que repetir el comando no repone la
cuantía. Cablear la reparación en esa rama es un cambio del contrato de `_alta_crm` que no cabe
aquí: **va al backlog**, y mientras tanto el mensaje del cuarto desenlace dice qué hacer a mano.

## 7. El mutex, y por qué esta pieza no lo pide

`MEJORAS #126` fijó que **el mutex lo pide quien escribe**, en el entrypoint. Los registradores de
`_caso.md` (`register_expediente`, `register_drive_ev`, `cache_drive_folder_info`) **no** lo exigen;
`ensure_case` sí, pero solo en `modo="v1"`, porque es la puerta de alta.

`update_meta` se alinea con sus vecinos: **no exige el mutex**. Su llamante en `abrir_caso.py` corre
ya bajo el mutex del caso (comentario de `MEJORAS #142` en `scripts/abrir_caso.py:728`), así que el
camino real está cubierto.

**Esto es una decisión, no un descuido, y su riesgo residual se declara:** un llamante futuro fuera
del mutex podría pisar una escritura concurrente. Exigirlo aquí y no en los otros tres registradores
sería incoherente, y exigirlo en los cuatro es un cambio de contrato que no cabe en esta pieza.
**Es candidato a entrada de backlog**, no a ampliación silenciosa del alcance.

**Y eso acota el teorema del §2.1, que la rev. 1 enunciaba incondicional** (H-09). La igualdad
acredita **la versión leída**, no la que existe al reemplazar: entre el `read` y el `os.replace`
cabe la escritura de otro. La R1 lo ejecutó como intercalación dirigida —A lee canónico, B añade
una nota, A reemplaza con su lectura vieja, la nota desaparece— y el mismo hueco existe hoy para
los tres registradores y para `registrar_outputs`. Así que la garantía se enuncia **bajo exclusión
vigente durante lectura, comparación y reemplazo**, y esa exclusión la aporta el llamante. Sin
ella, la pieza puede destruir texto que el generador nunca escribió: no porque compare mal, sino
porque comparó otra cosa.

`«todos mis vecinos lo hacen»` no es un argumento de seguridad. Es una decisión de compatibilidad,
y lo que cambia respecto de la rev. 1 es que ahora está **en el teorema**, no en una nota al pie.

## 8. Tests, con su control positivo

Fichero: `tests/test_caso_md_update_meta.py` (nuevo). Ninguno escribe en el árbol de producción:
todos sobre `tmp_casos_root`.

**Conservación del cuerpo**

1. **Reescribe cuando es canónico.** `ensure_case` sin cuantía → `update_meta(cuantia=73140.5)` →
   el cuerpo trae `- Cuantía: 73140.5` y el frontmatter también. Informe `cuerpo="reescrito"`.
2. **Conserva cuando hay una nota, y lo conserva EN BYTES.** Se inserta `## Notas del letrado` con
   **espacios finales y una línea indentada** → `update_meta` → los bytes del fichero desde el
   final del frontmatter hasta EOF son **idénticos** a los de antes (comparación `bytes`, no
   `str`). El frontmatter trae la cuantía; el informe dice `cuerpo="conservado"` con `motivo`.
3. **Conserva los finales de línea.** Un `_caso.md` con el cuerpo en `CRLF` y una nota → tras
   `update_meta`, el cuerpo sigue en `CRLF`. Es la mitad de H-01 que un test sobre `str` no ve.
4. **Conserva ante un solo espacio de más.** El control fino de la comparación.
5. **Un índice sin frontmatter parseable no se escribe.** `sha256` del fichero **antes y después**,
   e informe `cuerpo="sin tocar"`. Se comprueba el árbol, no el tipo de la excepción.

**Frontmatter**

6. **Escribe solo sus claves.** Se parte de un `_caso.md` con `bucket_override`, una clave ajena
   dentro de `meta`, dos expedientes y un `pull_state` → `update_meta(cuantia=…)` → **todo el
   frontmatter es idéntico** salvo `meta.cuantia` y `meta.actualizado_en`. Comparación de dicts
   completa, no de las claves que se me ocurran.
7. **No revierte lo que `update_pull_state` escribió.** El escenario de H-02, ejecutado:
   `register_expediente('10','expedientes_judiciales')` → `update_pull_state('10',
   element='extrajudiciales')` → `update_meta(cuantia=…)` → el `element` sigue siendo
   `extrajudiciales` **arriba y en el espejo**. Es el test que mata el diseño de la rev. 1.
8. **`referencia_crm` llega a sus DOS hogares**, y ningún otro campo de la lista blanca aparece en
   un hogar que nadie haya enumerado: el test recorre las claves que `_frontmatter_del_indice`
   produce y falla si una de la lista blanca sale por una vía no declarada.
9. **Rechaza un campo fuera de la lista blanca.** `direccion="X"` levanta `ValueError` nombrando el
   campo **y su hogar**, y **no escribe nada**: `sha256` antes y después.
10. **Una clave con `None` se escribe; una clave ausente no se toca.** Las dos mitades de H2-06.
11. **`campos` vacío es un error del llamante**, no un no-op silencioso.

**Idempotencia y CLI**

12. **Idempotencia con el reloj fijo.** Dos `update_meta` iguales, con `now_iso` parcheado, dejan
    el fichero byte a byte idéntico. **Y además** —H-06— la **primera** salida se compara contra
    `_cuerpo_del_indice(meta')`: sin eso, un generador que metiera `actualizado_en` en el cuerpo
    pasaría el test de idempotencia con el texto indebido dentro. El reloj se fija porque
    `now_iso` tiene resolución de segundos y dos llamadas seguidas coinciden **por suerte**.
13. **La CLI no pisa con cero:** `abrir_caso` dos veces, la segunda sin `--cuantia`. Y el test
    **acredita que recorrió la frontera**: se comprueba que la segunda invocación llegó a la
    escritura local y no retornó antes por la guarda de idempotencia (H-06 dice, con razón, que
    ese retorno temprano dejaría el test verde sin probar nada).
14. **El payload del CRM sigue recibiendo un número** sin `--cuantia` (H-04): alta sin flag, con
    `--cuantia 0` y con cuantía; en los tres el DTO recibe un `float`.
15. **Los cuatro desenlaces del alta son distinguibles** (§6.2): alta falla · registro falla ·
    índice falla · todo bien, cada uno con su mensaje.

**Control positivo, acreditado con mutantes dirigidos** y no con la afirmación de que existe:

| Test | Mutante que tiene que matarlo |
|---|---|
| 1 | sustituir la comparación por `False` (no reescribir nunca) |
| 2, 4 | sustituir la comparación por `True` (reescribir siempre) |
| 2 | volver a escribir por `write_md` en la rama conservada (devuelve el `strip()`) |
| 3 | quitar `newline=""` del `write_text` |
| 5, 9 | escribir antes de validar |
| 6, 7 | reutilizar `_actualizar_indice` / `_fusionar_expedientes`, que es el diseño de la rev. 1 |
| 8 | escribir `referencia_crm` solo en `meta` |
| 10 | filtrar los `None` de `campos` |
| 11 | aceptar `campos` vacío |
| 12, 16 | que `update_meta` añada un sello al cuerpo al reescribir |
| 13 | devolver el default de `--cuantia` a `0.0` |
| 14 | pasar el `None` tal cual a `crm_payload` |
| 15 | volver a un solo `except` alrededor de las tres llamadas |

16. **Al reescribir, solo cambia lo que renderiza el campo.** El teorema del §2.1, con un oráculo
    que **no es el generador**: se compara el cuerpo contra el **anterior** y se exige que la única
    línea que cambie sea `- Cuantía:`.

Cada mutante se aplica, se corre el test, se comprueba que **se pone rojo**, y se revierte. Lo que
no mate su mutante no acredita lo que dice acreditar. **Y la tabla se comprueba entera**: la rev. 1
dejó un test (el 7 de entonces) sin mutante asignado y la R1 lo cazó.

**Resultado: 13 mutantes, 13 muertos** — y el 13º costó descubrir algo que el diseño no decía.

**El mutante de `actualizado_en` estaba MAL APUNTADO, y sobrevivía por eso.** Lo puse sobre
`_cuerpo_del_indice`, que usan **la creación y la actualización**: con él, la línea de más aparece
en las dos, el diff sale vacío y los 18 tests siguen verdes. Un mutante que no mata no siempre
acusa al test — a veces acusa a la puntería. El correcto lo mete `update_meta` en su rama canónica,
y entonces muere.

**Y destapó que el oráculo del test 12 era tautológico:** comparar el cuerpo escrito contra
`_cuerpo_del_indice` es preguntarle al generador si el generador tiene razón. De ahí el test 16,
que compara contra el cuerpo anterior. Es [[feedback-el-arnes-de-mutacion-tiene-sus-propios-defectos]]
otra vez, y en la forma que menos se ve: el arnés funcionaba, lo que estaba mal era dónde apuntaba.

Suite completa con las **dos semillas** (777 y 31337) antes de mergear, conteo por `--junit-xml`.
Línea base de esta sesión, medida sobre `b59bb49`: **5.313 recogidos, 0 fallos, 94 skipped**.

## 9. Lo que esta pieza NO hace

- No toca `_actualizar_cuerpo` ni el contrato de `MEJORAS #146`.
- No exige el mutex (§7).
- No repara `_caso.md` legacy cuyo cuerpo ya no sea canónico (§4).
- No cierra `MEJORAS #184` ni `#192`.
- No toca `core/anon/`.

## 10. Adjudicación de la revisión adversarial (Codex, 2026-09-11) — REQUIERE-REVISION, remediado

- **Objeto revisado:** diseño `c325723` — la rev. 1 de este mismo documento
- **Ronda:** R1 de 2 (la R2 va sobre el diff)
- **Revisor:** Codex (CLI 0.153.4), copia `git archive` sin `.git`, solo lectura
- **Informe recibido:** 2026-09-11, `C:/t/rev227-r1-1421/wd/INFORME.md`, 52614 bytes
- **Hallazgos:** 9 — 2 ALTOS, 6 MEDIOS, 1 BAJO; **9 confirmados, 0 refutados**
- **Remediado en:** este §10 y la rev. 2 del diseño (§2, §3, §5, §6 y §7)

Acta con el informe literal y su digest:
`docs/superpowers/specs/2026-09-11-cuantia-en-caso-md-comparar-no-localizar-r1-adversarial-review.md`.
El `sha256` del bloque canonicalizado coincide con el del `INFORME.md` original, así que la cadena
se verifica contra la salida del revisor y no solo contra sí misma.

**Los dos ALTOS son el mismo error mío en dos capas, y los reproduje antes de aceptarlos.**

### H-01, ALTO — la garantía se enunció sobre cadenas y el fichero está hecho de bytes

`write_md` hace `body.strip()` y escribe con la convención de saltos de la plataforma. Reproducido:
una nota que acaba en `CONSERVAR` + dos espacios vuelve del escritor **sin** esos dos espacios, y
un fichero cuyo cuerpo estaba en LF sale en CRLF. **La rama que prometía no tocar nada perdía
texto del letrado**, sin que ninguna comparación fallara. Y la comparación misma resultó ser sobre
texto normalizado: `_FM_RE` se come las líneas en blanco tras el `---`, así que el falso positivo
no exige lo que la rev. 1 decía que exigía.

**De qué frontera es esto un ejemplo, que es la pregunta que importa:** convertí un problema de
*parsing* en una igualdad de cadenas y **enuncié la garantía en ese mismo plano**, sin bajar a la
capa donde el fichero existe. La clase de defecto no estaba en el parser: estaba en creer que
«conservar una variable llamada `cuerpo`» es conservar el cuerpo. Remediado en el **§2.2 y §2.3**:
la rama conservada sustituye *solo* el tramo del frontmatter y escribe con `newline=""`.

### H-02, ALTO — una lista blanca de argumentos no acota lo que se escribe

Reproducido: `update_pull_state` escribe en la lista superior y deja el espejo de `meta` como
estaba; `_fusionar_expedientes(superior, espejo)` aplica el espejo encima y **el `element` vuelve
atrás**. Reutilizar esa fusión —que es lo que la rev. 1 proponía factorizar— habría revertido un
dato ajeno a la lista blanca, en silencio.

**La frontera:** dije «cierra H-03 por construcción» de una comprobación que actúa sobre los
**argumentos**, y el daño estaba en los **efectos**. Remediado en el **§3.3**: no se factoriza
nada, `_actualizar_indice` se queda como está, y `update_meta` escribe sus claves enumeradas sobre
un `deepcopy` del `fm` leído.

### Los otros siete

| # | Sev. | Adjudicación | Dónde acabó |
|---|---|---|---|
| H-03 | MEDIO | **CONFIRMADO** — la justificación de la lista blanca era demasiado amplia: `cliente`, `contraparte`, `organo` y otros tampoco tienen actualizador | §3.1, corregida; los huecos **al backlog**, no a esta pieza |
| H-04 | MEDIO | **CONFIRMADO** — el `None` de `--cuantia` llega a `crm_payload` y de ahí a una suma del DTO | §6.1: dos políticas distintas del mismo hecho, y su test (el 14) |
| H-05 | MEDIO | **CONFIRMADO** — faltaba el **cuarto** desenlace (índice falla) y la reparación no es automática | §6.2, con lo que NO se intenta dicho por delante |
| H-06 | MEDIO | **CONFIRMADO** — tres de mis controles positivos podían seguir verdes | §8: 15 tests y 13 mutantes, con oráculo sobre la **primera** salida y reloj fijo |
| H-07 | BAJO | **CONFIRMADO** — «único lector» era demasiado amplio: el visor y las skills leen el fichero entero | §5, acotado a «lector determinista en Python», con el precio real |
| H-08 | MEDIO | **CONFIRMADO** — faltaba el contrato de entrada del «SIEMPRE» | §3.4, con su tabla y el tercer estado `"sin tocar"` |
| H-09 | MEDIO | **CONFIRMADO** — la igualdad acredita la versión **leída**, no la del reemplazo | §7: el teorema pasa a enunciarse **bajo exclusión vigente** |

**Lo que el revisor NO hizo, y es lo que más dice de la ronda:** no propuso volver a localizar
líneas con heurísticas. Su cierre lo declara expresamente. El núcleo —comparar en vez de
localizar— sale de la R1 **confirmado**; lo que se cayó fue mi ejecución de él, en las dos
fronteras de arriba.

**Lo que la R1 declaró SIN VERIFICAR, y sigue sin verificarse:** la suite con las dos semillas (su
Python de sistema no trae `pytest-randomly`), la genealogía del commit (sin `.git`), el
comportamiento sobre los `_caso.md` reales del Drive, y la concurrencia real de procesos — su
escenario de H-09 es una intercalación dirigida dentro de un proceso, no una carrera medida.
