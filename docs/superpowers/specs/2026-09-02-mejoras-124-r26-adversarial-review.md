---
tipo: revision-adversarial
objeto: "remediación de R25 sobre la costura y su primer cliente (MEJORAS #124, alcance recortado)"
objeto_rev: "rama claude/mejoras-124-rev2, commit 43471be"
commit: 43471be
ronda: "26"
revisor: Codex
veredicto: NO-SHIP
marcador_nonce: q7vt
sha256_informe: 241a724d8de80ae23c9caa2ab56d0e51ce0346c6348972aa12b152e33298d055
adjudicado_en: docs/superpowers/plans/2026-09-02-mejoras-124-copia-de-trabajo.md §12
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R26.** El §1 conserva la voz del revisor sin una coma
> cambiada; la **adjudicación** vive en el **§12 del plan**. Es la ronda del **DIFF**.
>
> Veredicto `NO-SHIP`: **6 hallazgos — 1 CRÍTICO, 2 ALTOS, 2 MEDIOS, 1 BAJO**. Adjudicados: **todos confirmados, 0
> refutados**; los graves **reproducidos con sondas propias** antes de remediar.
>
> **Lo que esta ronda compró, y es lo más incómodo de la sesión.** Los tres hallazgos graves son
> míos y de la misma familia: cerré el **ejemplo** que R25 midió y dejé la **frontera** abierta por
> dos sitios nuevos —un workspace local del caso A apuntando al canon de B, y un descendiente del
> canon—, y usé la petición como prueba de identidad tres líneas debajo de un docstring que dice lo
> contrario.
>
> **Y demostró que mi evidencia de test era falsa** (H26-04): `ensure_case` escribe `id_go: null`,
> mi fixture comprobaba `if "id_go" not in txt` —la cadena sí estaba— y el valor real nunca entraba.
> Los 26 tests pasaban por el **nombre de la carpeta**, no por el metadato que sus docstrings dicen
> probar. Arreglar la fixture **no bastó**: hizo falta un caso con nombre neutro para que el mutante
> del metadato muriera.
>
> **El bloque literal archiva DOS textos**, por lo mismo que en R21-R24: el guard G9 exige la
> palabra del veredicto dentro del bloque y el informe no la contiene.

## 1. Informe recibido de Codex, sin modificar

<!-- informe-literal:inicio:q7vt -->
# Revisión adversarial R26 — remediación de R25

Objeto revisado: `DIFF_remediacion.patch` (`base -> head`). `DIFF_completo.patch` se usó solo como contexto. Claude Code adjudica cada hallazgo contra la fuente; este informe no adjudica.

## sha256 agregado al abrir

`02dbf898d7a1e162846ecfe19654e3bf110bd446a29f17380282787450bc3809` (1.131 ficheros).

Método: SHA-256 de los bytes de cada fichero; líneas `<sha256-en-minúsculas>  <ruta-relativa-con-/>`, orden ordinal sensible a mayúsculas por ruta, unidas con `\n`, codificadas en UTF-8 sin BOM y sin salto final; después SHA-256 del bloque resultante.

El parche aplica limpiamente sobre los cuatro ficheros afectados de `base` y reproduce byte por byte los cuatro de `head`. `git apply` solo advirtió una línea en blanco añadida al EOF.

## H26-01 — La invariante permite escribir sin guard en otro canon

**Severidad: CRÍTICO**

**Evidencia.** `core/casos/escritura.py:204-217` solo exige desigualdad textual entre una raíz local y el canon resuelto **del caso pedido**. No exige que la raíz local esté fuera del catálogo. Después, `core/casos/escritura.py:387-388` decide no consultar `guard_escritura` exclusivamente por el modo local.

Comando sobre copia de `head`:

```text
python -m pytest -p no:randomly \
  tests/test_r26_adversarial.py::test_junction_local_al_canon_salta_invariante_y_guard \
  tests/test_r26_adversarial.py::test_local_del_caso_a_apunta_al_canon_b_y_escribe_sin_guard \
  -vv -s --basetemp=../pytest_tmp_r26_invariante_real
```

Salida observada:

```text
junction: (dep.desviada, ruta_resuelta_en_canon, existe) = (False, <canon>/.../junction.txt, True)
otro caso: (dep.desviada, existe, cae_en_canon_b) = (False, True, True)
2 failed
```

El segundo caso no necesita enlaces: un `CaseWorkspace` público de A, modo `LOCAL_CHECKOUT`, con `working_root` igual al canon B, recibe identidad/mutex de A y escribe físicamente en B sin el guard de B. También pasaron como “locales” un descendiente del canon, la raíz del catálogo, una junction al propio canon y la forma extendida `\\?\`; el arnés volvió a ejecutarse con el Python indicado y produjo `impacto_otro_canon result='WROTE'` e `impacto_junction result='WROTE'` en `agent_modo_sala/probe_output_r3.txt`. La misma comparación rechaza como `DRIVE_ACTIVE` una junction o forma extendida para la que `os.path.samefile` es verdadera.

**Qué habría que hacer.** Para modos locales, demostrar que `working_root` está físicamente fuera del catálogo completo, con el clasificador físico existente y la misma raíz autoritativa que usa el catálogo; fallar cerrado ante `INDETERMINADO`. Para `DRIVE_ACTIVE`, comprobar identidad física con el canon resuelto. No volver a introducir una segunda raíz tomada de `settings.casos_root`: la API del catálogo debe exponer la clasificación contra su propia fuente. Añadir regresiones para otro canon, descendiente, raíz del catálogo, junction y `\\?\` en ambas polaridades.

## H26-02 — La petición vuelve a convertirse en prueba cuando el canon no declara W-code

**Severidad: ALTO**

**Evidencia.** `_identidad()` solo toma el canon de `meta.id_go` o del nombre (`core/casos/escritura.py:148-151`). La nueva función añade la petición como fallback (`core/casos/escritura.py:300`). Con un canon localizado por `case_id` cuyo metadato y nombre no contienen W-code, una petición arbitraria pasa a nombrar el mutex en la vía workspace, aunque la histórica declara identidad no utilizable.

Comando:

```text
python -m pytest -p no:randomly \
  tests/test_r26_adversarial.py::test_con_canon_sin_w_la_peticion_sola_se_vuelve_prueba \
  -vv -s --basetemp=../pytest_tmp_r26_request_only
```

Salida:

```text
_identidad(ref)              -> (None, <motivo>)
_identidad_de_workspace(...) -> ('W-PEDR26', None)
FAILED
```

La vía nueva es, por tanto, más permisiva que la vieja. En `modo="v1"`, sostener el mutex de ese W-code pedido permite avanzar donde la vía histórica abortaría por `IdentidadNoUtilizable`. En el camino sin canon ocurre una elevación adicional: con `CaseRef(case_id="desconocido")`, el nombre fabricado `Scratch inventado - (W-FABR26)` produjo exactamente `('W-FABR26', raiz, None)`.

**Qué habría que hacer.** Si existe canon, derivar `canon` solo de las mismas fuentes probatorias que `_identidad()`; la petición participa en la comparación, nunca en el fallback. Para un scratch sin canon, no elevar el basename por sí solo a identidad: exigir una identidad validada procedente del registro/resolver y concordante con la petición y la presentación, o devolver `None` y motivo de garantía débil.

## H26-03 — Se fusionan los `case_id` por preferencia y se descarta el W-code al localizar

**Severidad: ALTO**

**Evidencia.** `core/casos/escritura.py:263-270` compara los W-codes de `ref` y `workspace.case_ref`, pero `:271` elige `workspace.case_ref.case_id` con `or` y nunca contrasta los dos `case_id`. En `:275` construye después `CaseRef(case_id=case_id)`, descartando todo W-code aunque estuviera presente.

Dos reproducciones del barrido final (`6 failed, 2 passed` en `tests/test_r26_adversarial.py`):

```text
ref.case_id=B, workspace.case_ref.case_id=A, ambos sin W-code
-> DID NOT RAISE IdentidadDiscordante; resolvió A.

ref/workspace=(case_id inexistente, w_code='W-REAL26'), canon localizable por
meta.id_go='W-REAL26' pero con nombre W-OTRO26
-> _identidad(ref) rechazó; _identidad_de_workspace(ref, ws) no rechazó.
```

El segundo resultado ocurre porque la histórica localiza primero por W-code, mientras la nueva lo borra, declara “sin canon” y acepta el nombre W-REAL26 de la copia. Es otra divergencia de permisividad respecto de la regla que se afirma unificada.

**Qué habría que hacer.** Tratar `ref` y `workspace.case_ref` como dos peticiones completas: rechazar `case_id` distintos cuando ambos estén presentes (o demostrar mediante el catálogo que resuelven al mismo directorio) y no perder el W-code al localizar. Añadir una matriz explícita `case_id/case_id`, `case_id/w_code` y referencias con ambos campos, incluyendo identificadores obsoletos.

## H26-04 — Los tests clave no ejercitan `meta.id_go` ni la rama de gramática inválida

**Severidad: MEDIO**

**Evidencia.** Las fixtures de `tests/test_escritura_sobre_workspace.py:68-82` y `tests/test_sala_maquina_por_la_costura.py:28-42` hacen:

```python
if "id_go" not in txt:
    ...
```

pero `ensure_case` ya escribe `id_go: null`. Tras ejecutar los 26 tests de los dos ficheros, la inspección de todos sus temporales mostró `meta.id_go: null`, incluidos `test_pedir_solo_por_case_id_NO...` y `test_un_workspace_sin_W_code...`. Sus resultados salen del W-code del nombre, no del metadato que los docstrings dicen probar.

Mutación dirigida:

```text
id_go = None  # ignorar por completo read_case_meta(canon_dir)
pytest ... test_escritura_sobre_workspace.py test_sala_maquina_por_la_costura.py
-> 26 passed
```

La prueba `test_un_W_code_con_gramatica_invalida_no_da_namespace` tampoco construye una identidad inválida efectiva: `_ws(...)` lleva siempre `W-DEPO01` y su `case_id` gana en `:271`. El mutante `w = canon` en vez de `_w_code_valido(canon)` dejó también `26 passed`; cobertura de rama dejó sin ejecutar `core/casos/escritura.py:306-308`.

Como control, con fixture corregida, nombre neutro y `meta.id_go` real, los canarios propios de H25-01 (W-code falso) y H25-02 (`case_id` solo conserva W-code) sí pasaron: `2 passed`.

**Qué habría que hacer.** Editar el YAML semánticamente o sustituir `id_go: null`, usar nombres locales neutros para que no puedan suplir al metadato, y construir un scratch realmente desconocido con W-code de gramática inválida. Exigir valor, motivo y excepción concretos, no solo que la llamada no lance.

## H26-05 — El espía protege `apply`, pero no las demás piezas de la remediación

**Severidad: MEDIO**

**Evidencia.** El mutante solicitado sobre los dos cables de `apply` (`dep=_dep_sala -> dep=None`) muere correctamente en `tests/test_sala_maquina_por_la_costura.py:248-251`; el espía observa una lista vacía. El canario de vía directa también dispara en `scripts/sala_maquina.py:147`, por la razón esperada.

No ocurre lo mismo con estas piezas:

- mutar solo los dos cables de `reforzar` en `scripts/sala_maquina.py:976,981` a `dep=None` dejó verdes los 187 tests `test_sala_maquina*.py`;
- reintroducir la captura de identidad y el `return None` en `_deposito_sala` dejó verdes los 26 tests cambiados;
- reintroducir en `plan` la llamada muerta `_deposito_sala(ws)` dejó verdes los 187 tests de sala.

El código actual se comportó correctamente en el arnés ejecutado: `--case-dir`, offline, legacy sin W-code y `reforzar` escribieron estado/cobertura atravesando la capacidad; `IdentidadDiscordante` se propagó. El defecto aquí es que esas tres remediaciones pueden regresar sin que sus tests fallen.

**Qué habría que hacer.** Añadir un E2E de `reforzar` con depósito espía y asertos sobre `_COBERTURA` y `_STATE`; un canario que exija propagación exacta de `IdentidadDiscordante` desde `_deposito_sala`; y un canario en `plan` que haga fallar cualquier construcción de la capacidad. Cubrir también `--case-dir` y offline en tests de comando, no solo en arnés.

## H26-06 — Quedan asertos cuya condición no puede ser falsa

**Severidad: BAJO**

**Evidencia.** `tests/test_escritura_sobre_workspace.py:264,266` hace `assert escritura.deposito(...)`; `Deposito` no define `__bool__`, por lo que el resultado siempre es verdadero si la llamada retorna. La evaluación aún detecta excepciones, pero el `assert` no añade condición. `tests/test_sala_maquina_por_la_costura.py:108,124` conserva `assert d is not None`; tras retirar el fallback, `_deposito_sala` devuelve `Deposito` o lanza, y además ambos tests acceden inmediatamente a atributos de `d`.

**Qué habría que hacer.** Sustituirlos por propiedades observables (`_base` no debe exponerse; usar destino escrito, `desviada`, clase, identidad/motivo) o dejar la llamada desnuda cuando el único contrato sea “no lanza”.

## Controles que sí pasaron

- Los 26 tests cambiados pasan sobre `head`.
- El mutante de los cables de `apply` muere; el canario directo se dispara en la rama directa.
- H25-01 y H25-02 pasan con un canon cuyo W-code existe solo en `meta.id_go` y con copia de nombre neutro.
- `DRIVE_ACTIVE` directo sobre el canon y local directo fuera del catálogo pasan; `DRIVE_ACTIVE` sin canon y con raíz distinta se rechaza.
- La retirada del fallback no rompió en el arnés `--case-dir`, offline, legacy sin W-code ni `reforzar`.
- La normalización LF quedó observada por bytes (`b"\r\n" not in crudo`).
- Pytest recolectó 3.763 tests oficiales. Una verificación compuesta dejó verdes 3.762: 3.751 en la pasada principal y 10 sondas que, por restricciones de escritura del cwd, se ejecutaron desde el directorio padre.

## Lo que NO pude verificar

- **SIN VERIFICAR:** el resultado literal “3.763 tests, 0 fallos” en una única invocación. Un nodo de `tests/test_mcp_wrappers.py` para `expedientes_xl` falla igual en `base` y `head` porque vacía `PATH` y el wrapper intenta usar `ping`; no se imputa a esta remediación, pero impide declarar cero absoluto. Ocho sondas que escriben dentro del árbol requirieron una segunda invocación desde el padre por `PermissionError` al ejecutarlas con la copia como cwd.
- **SIN VERIFICAR:** los 77 tests omitidos por lentitud, fixture PII ausente, Ollama ausente, blocklist ausente y E2E declarados lentos. Se observaron los 10 `xfail`; no hubo señal de `xpass` en las pasadas usadas.
- **SIN VERIFICAR:** una corrida contra Drive/registro reales. Los caminos de `sala_maquina` se ejecutaron sobre filesystem temporal y dobles deterministas de dependencias externas.
- **SIN VERIFICAR:** aliases 8.3 y Volume GUID. Sí se ejecutaron junction y forma extendida `\\?\`.
- **SIN VERIFICAR:** mutación exhaustiva de todo el repositorio. Se mutaron las ramas nuevas de identidad/invariante y los cables de la remediación; no se usó un motor exhaustivo sobre cada operador posible.
- **SIN VERIFICAR:** los identificadores de commit `5e75553` y `43471be` mediante `git rev-parse`, porque las copias entregadas no contienen `.git`. Sí se verificó que el parche aplica a `base` y reproduce exactamente los cuatro ficheros cambiados de `head`.

## sha256 agregado al cerrar

`02dbf898d7a1e162846ecfe19654e3bf110bd446a29f17380282787450bc3809` (1.131 ficheros), calculado con el mismo método. Coincide con el hash de apertura.

----- VEREDICTO.md (fichero aparte, pedido asi en el mandato) -----

NO-SHIP
La invariante permite a un workspace local escribir sin guard en el canon de otro caso y la nueva identidad sigue siendo más permisiva que la histórica.
<!-- informe-literal:fin:q7vt -->

## 2. Evidencia verificada por el adjudicador

Las sondas y su resultado —antes y después de remediar— están en la adjudicación
(§12 del plan). No se repiten aquí para que el acta siga siendo lo que debe ser: el
archivo de la voz del revisor, no un segundo hogar de la decisión.
