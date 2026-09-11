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

**Este documento es el objeto de la R1.** La R2 irá sobre el diff. Presupuesto de 2 rondas fijado
por el radio de daño —la pieza escribe en el índice del expediente y puede destruir una nota del
letrado—, no por el tamaño del fichero.

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

### 2.1 El teorema, que es lo que hay que atacar en la R1

Sea `C` el cuerpo del fichero, `M` la `meta` reconstruida desde el frontmatter y `M'` la misma con
los campos nuevos aplicados.

- **Si `C ≠ _cuerpo_del_indice(M)`** → el cuerpo no se toca. Cero escritura, cero pérdida.
- **Si `C = _cuerpo_del_indice(M)`** → se escribe `_cuerpo_del_indice(M')`. Como `M'` difiere de `M`
  **solo** en los campos de la lista blanca (§3.1), la diferencia entre `C` y el cuerpo nuevo es
  exactamente lo que esos campos renderizan. **Todo lo demás del cuerpo es idéntico byte a byte,
  porque lo produce el mismo generador con los mismos datos.**

De ahí: **lo único que esta pieza puede perder es texto que ella misma acaba de reproducir.** No
hay un tercer caso, y no lo hay porque la comparación es sobre la cadena entera, no sobre un
fragmento. Un falso positivo —"parece canónico y no lo es"— exigiría que el letrado hubiera escrito
a mano, carácter a carácter, el cuerpo que la plantilla genera; y aun entonces la reescritura
devuelve ese mismo texto.

El modo de fallo que **sí** queda vivo es el falso negativo: un cuerpo canónico que la comparación
declara distinto, y entonces la cuantía no llega al cuerpo. Eso es el §4.

### 2.2 Lo que esto NO arregla, dicho por delante

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

Esto cierra **H-03 de la R1** ("campos con otro hogar aceptados sin avisar") *por construcción* y
no por una comprobación: un campo nuevo no entra por descuido, entra editando esta constante y
justificando por qué no tiene otro hogar.

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
    "cuerpo": "reescrito",             # "reescrito" | "conservado"
    "motivo": None,                    # si "conservado": por qué, en una frase
}
```

`motivo` no es decorativo: es la única forma de que el letrado sepa que el cuerpo de su `_caso.md`
dice `_(pendiente)_` y el frontmatter no. Sin eso la pieza miente por omisión.

### 3.3 El frontmatter se escribe SIEMPRE, y por la vía que ya conserva lo ajeno

La fusión del frontmatter (`{**fm, **propias}` conservando `bucket_override` y demás claves ajenas,
`deepcopy` de la lista de expedientes para no emitir anclas YAML) ya está resuelta en
`_actualizar_indice`. **Se factoriza, no se reescribe**: `_fusionar_frontmatter(fm, meta)` sale de
ahí y lo usan los dos caminos. `_actualizar_indice` conserva su cuerpo por `_actualizar_cuerpo`;
`update_meta` usa el suyo por comparación. La diferencia entre los dos queda en una línea visible.

La escritura va por `_escribir_indice_atomico` — temporal en el mismo directorio y `os.replace`,
igual que los registradores.

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

No hay ningún otro lector: el resto de apariciones de `cuantia` en `core/` y `scripts/` son del
payload del CRM (`sudespacho_create`) o de la firma de `ensure_case`, ninguna lee `_caso.md`.

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

## 8. Tests, con su control positivo

Fichero: `tests/test_caso_md_update_meta.py` (nuevo). Ninguno escribe en el árbol de producción:
todos sobre `tmp_casos_root`.

1. **Reescribe cuando es canónico.** `ensure_case` sin cuantía → `update_meta(cuantia=73140.5)` →
   el cuerpo trae `- Cuantía: 73140.5` y el frontmatter también. Informe `cuerpo="reescrito"`.
2. **Conserva cuando hay una nota.** Se inserta `## Notas del letrado` a mano → `update_meta` →
   **la nota sigue ahí byte a byte**, el cuerpo sigue diciendo `_(pendiente)_`, el frontmatter trae
   la cuantía, e informe `cuerpo="conservado"` con `motivo` no vacío.
3. **Conserva ante un solo espacio de más.** El control fino: la comparación es exacta.
4. **Rechaza un campo fuera de la lista blanca.** `update_meta(case_id, direccion="X")` levanta
   `ValueError` nombrando `direccion` **y su hogar** (`ensure_case`), y **no escribe nada**: se
   comprueba el sha256 del fichero antes y después, no solo el tipo de la excepción (R2/H2-08: un
   test de «no se crea nada» que mira la excepción y no el árbol no acredita nada).
5. **Una clave con `None` se escribe; una clave ausente no se toca.** Las dos mitades de H2-06.
6. **Idempotencia:** dos `update_meta` iguales dejan el fichero byte a byte idéntico (cerrando la
   duplicación de línea que el diseño anterior tenía).
7. **Conserva las claves ajenas del frontmatter** (`bucket_override`) y la sección de expedientes.
8. **La CLI no pisa con cero:** `abrir_caso` dos veces, la segunda sin `--cuantia`, y la cuantía
   sigue siendo la primera. Es el test de H2-06, reconstruido.
9. **Los tres mensajes del alta CRM son distinguibles** (§6.2): alta falla / alta bien + registro
   falla / todo bien.

**Control positivo, acreditado con mutantes dirigidos** y no con la afirmación de que existe:

| Test | Mutante que tiene que matarlo |
|---|---|
| 2 y 3 | sustituir la comparación por `True` (reescribir siempre) |
| 1 | sustituir la comparación por `False` (no reescribir nunca) |
| 4 | vaciar `CAMPOS_ACTUALIZABLES` de su comprobación |
| 5 | filtrar los `None` de `campos` |
| 6 | añadir `actualizado_en` al cuerpo |
| 8 | devolver el default de `--cuantia` a `0.0` |
| 9 | volver a un solo `except` alrededor de las dos llamadas |

Cada mutante se aplica, se corre el test, se comprueba que **se pone rojo**, y se revierte. Lo que
no mate su mutante no acredita lo que dice acreditar.

Suite completa con las **dos semillas** (777 y 31337) antes de mergear, conteo por `--junit-xml`.
Línea base de esta sesión, medida sobre `b59bb49`: **5.313 recogidos, 0 fallos, 94 skipped**.

## 9. Lo que esta pieza NO hace

- No toca `_actualizar_cuerpo` ni el contrato de `MEJORAS #146`.
- No exige el mutex (§7).
- No repara `_caso.md` legacy cuyo cuerpo ya no sea canónico (§4).
- No cierra `MEJORAS #184` ni `#192`.
- No toca `core/anon/`.
