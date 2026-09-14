# P6 — Ficha CRM y actuaciones: plan de implementación

> **Para quien lo ejecute:** SUB-SKILL REQUERIDA: `superpowers:subagent-driven-development`
> (recomendada) o `superpowers:executing-plans`, tarea por tarea. Los pasos usan casillas
> (`- [ ]`) para seguimiento.

**Objetivo:** que la apertura deje de fundir a dos personas que comparten correo, que la ficha
admita N contrarios, y que crear una actuación en el CRM deje de reescribirse a mano contra la
prosa.

**Arquitectura:** tres piezas sobre dos módulos existentes y uno nuevo. La pieza 2 reordena
`resolver_parte` para que el criterio fuerte (NIF) mande sobre el débil (email) y añade una tabla
de decisión sobre las fichas que comparten buzón. La pieza 3 amplía el lector del YAML de mapping
a lista con validación previa a cualquier escritura. La pieza 1 encapsula la receta de seis pasos
del §15.6 en un módulo nuevo con recibo reanudable.

**Stack:** Python 3.12, `httpx` (sustituido por inyección en los tests), `pytest`, `pyyaml`.

**Diseño (SSOT):**
[`2026-09-14-p6-ficha-crm-y-actuaciones-design.md`](../specs/2026-09-14-p6-ficha-crm-y-actuaciones-design.md)
rev. 2. Acta de la R1: [`…-r1-adversarial-review.md`](../specs/2026-09-14-p6-ficha-crm-y-actuaciones-r1-adversarial-review.md).

## Restricciones globales

- **Ningún test llama al CRM real.** `_buscar_registros` y `httpx` se sustituyen por inyección
  (`monkeypatch`), patrón del PR #282. Ninguna prueba lee `SUDESPACHO_API_KEY`.
- **Ningún test escribe en el árbol de producción.** Árboles sintéticos en `tmp_path`
  (`tests/test_guard_aislamiento_paralelo.py` lo vigila).
- **Encoding UTF-8 sin BOM**; `subprocess` con `encoding="utf-8", errors="replace"`.
- **Fallar cerrado ante incertidumbre de identidad** (decisión de Nikolai, 2026-09-04): si no se
  puede comprobar, no se crea ni se vincula.
- **`ResolucionParte()` vacía significa «no existe: créala».** No es un valor neutro:
  `_exigir_identidad_cierta` la deja pasar. Solo se devuelve con evidencia comparable.
- **La igualdad de documentos es canónica y simétrica**, vía `_canonizar_documento` en los **dos**
  lados, y solo está definida entre documentos *utilizables*.
- **Suite de referencia:** 5.531 recogidos / 0 fallos / 94 skipped (`origin/main`, `530d033`).
  Cualquier variación se explica en el cierre.
- **Dos rondas adversariales.** La R1 sobre el diseño ya está adjudicada; la **R2 va sobre el
  diff** de este plan, antes del merge.

---

## Estructura de ficheros

| Fichero | Responsabilidad | Tarea |
|---|---|---|
| `core/sudespacho_relations.py` (mod.) | `ResolucionParte` gana `motivo`; `resolver_parte` reordenada + tabla §2.2; `_exigir_identidad_cierta` dice la verdad | 1, 2, 3 |
| `tests/test_resolver_parte_aper71.py` (nuevo) | La pieza 2 entera, con doble de CRM en memoria | 1, 2, 3 |
| `core/crm_ficha.py` (mod.) | `contrario` mapping **o** lista, validada entera antes de escribir | 4 |
| `tests/test_crm_ficha_n_contrarios.py` (nuevo) | La semántica del §3 del diseño | 4 |
| `core/sudespacho_actuaciones.py` (nuevo) | La receta de seis pasos, con recibo | 5, 6, 7, 8 |
| `tests/test_sudespacho_actuaciones.py` (nuevo) | Las cuatro salidas del paso 1, destino, recibo, duración | 5, 6, 7, 8 |
| `tests/_mutantes_p6.py` (nuevo) | Arnés: cada mutante apunta a su test | 9 |
| `docs/RUNBOOK_APERTURA_EXPEDIENTE.md` (mod.) | `[APER-63]`, `[APER-71]`, `[APER-72]` pasan a resueltos | 10 |
| `PLAN.md` (mod.) | Fila #33 | 10 |

**Nota de decomposición:** la pieza 2 va en **tres** tareas (vocabulario → orden → tabla) porque
cada una es rechazable por separado y las tres tocan la misma función: mezclarlas haría
irrevisable el diff. La pieza 1 va en cuatro por la misma razón.

---

### Tarea 1: El vocabulario de la identidad (`motivo` y los tres estados)

**Ficheros:**
- Modificar: `core/sudespacho_relations.py` — `ResolucionParte` (~:1134), `_exigir_identidad_cierta` (~:1222)
- Test: `tests/test_resolver_parte_aper71.py`

**Interfaces:**
- Consume: `_canonizar_documento(str) -> str` (ya existe).
- Produce: `ResolucionParte.motivo: str = ""`; `sudespacho_relations._estado_documento(str) -> str`
  con valores `"ausente" | "utilizable" | "no_interpretable"`.

- [ ] **Paso 1: escribir los tests que fallan**

Los de `test_resolver_parte_aper71.py` que cubren el vocabulario:
`test_h01_un_nif_no_interpretable_no_cae_a_la_politica_de_email`,
`test_un_nif_ausente_de_verdad_si_usa_la_politica_de_email`,
`test_el_error_de_un_nif_no_interpretable_no_habla_de_varias_fichas`.

- [ ] **Paso 2: verificar que fallan por la razón correcta**

Run: `python -m pytest tests/test_resolver_parte_aper71.py -k "no_interpretable or ausente_de_verdad" -q --tb=short -p no:randomly`
Esperado: FAIL — `AttributeError: 'ResolucionParte' object has no attribute 'motivo'`, y el de
`no_interpretable` resolviendo a `"A"` por email.

- [ ] **Paso 3: implementar lo mínimo**

```python
def _estado_documento(valor: str) -> str:
    """`ausente` | `utilizable` | `no_interpretable`. Son TRES, y la R1 lo midió.

    `_canonizar_documento` elimina separadores, así que `" -- . "` se convierte en `""`:
    tratarlo como «no se aportó» activaba la política de email en silencio sobre un dato
    que SÍ se aportó (R1/H-01). La pérdida de información al normalizar no puede degradar
    un documento hasta cambiar de criterio.
    """
    if not (valor or "").strip():
        return "ausente"
    return "utilizable" if _canonizar_documento(valor) else "no_interpretable"
```

En `ResolucionParte`, tras `sin_comprobar`:

```python
    #: Por qué no está resuelta, cuando el motivo no es «varias fichas». Vacío si no aplica.
    motivo: str = ""
```

Y `resuelta` pasa a contar el motivo:

```python
    @property
    def resuelta(self) -> bool:
        return not (self.conflicto or self.ambiguo or self.sin_comprobar or self.motivo)
```

En `_exigir_identidad_cierta`, **antes** de la rama de `ambiguo`:

```python
    if r.motivo and not r.ambiguo:
        raise ConflictoDeIdentidad(
            f"En {elemento}, no se puede decidir la identidad de esta parte: {r.motivo}. "
            "No se crea ni se vincula nada."
        )
```

- [ ] **Paso 4: verificar que pasan**

Run: `python -m pytest tests/test_resolver_parte_aper71.py -k "no_interpretable or ausente_de_verdad" -q --tb=short -p no:randomly`
Esperado: PASS.

- [ ] **Paso 5: commit**

```bash
git add core/sudespacho_relations.py tests/test_resolver_parte_aper71.py
git commit -m "Un documento tiene TRES estados, no dos (R1/H-01)"
```

---

### Tarea 2: El NIF único manda sobre la multiplicidad del email

**Ficheros:**
- Modificar: `core/sudespacho_relations.py` — `resolver_parte` (~:1160-1218)
- Test: `tests/test_resolver_parte_aper71.py`

**Interfaces:**
- Consume: `_estado_documento` (tarea 1), `Consulta.ids`, `_PROP_NIF`.
- Produce: `resolver_parte` con el orden del §2.1 del diseño. Firma sin cambios.

- [ ] **Paso 1: escribir los tests que fallan**

`test_h03_el_nif_unico_manda_aunque_el_email_devuelva_varias`,
`test_h03_el_orden_de_los_resultados_no_cambia_la_decision`,
`test_el_nif_unico_fuera_del_conjunto_del_email_sigue_siendo_conflicto`,
`test_varias_fichas_por_nif_sigue_siendo_ambiguo`,
`test_una_consulta_fallida_manda_sobre_todo_lo_demas`,
`test_sin_nif_y_con_varias_fichas_en_el_buzon_es_ambiguo`.

- [ ] **Paso 2: verificar que falla el que importa**

Run: `python -m pytest tests/test_resolver_parte_aper71.py -k h03 -q --tb=short -p no:randomly`
Esperado: FAIL — `test_h03_el_nif_unico_manda…` devuelve `ambiguo=("A","B")` en vez de `id="B"`.

- [ ] **Paso 3: reordenar la función**

Sustituir el bloque desde `ids_nif = set(c_nif.ids)` hasta el `return ResolucionParte()` final:

```python
    ids_nif = set(c_nif.ids)
    ids_mail = set(c_mail.ids)

    # 1. «No pude mirar» manda sobre todo: conserva su precedencia (R1 lo intentó refutar).
    if sin:
        return ResolucionParte(sin_comprobar=tuple(sin))

    # 2. Un documento aportado que no se puede comparar NO cae al email (R1/H-01).
    if estado_nif == "no_interpretable":
        return ResolucionParte(
            motivo=f"el NIF {nif!r} no es interpretable como documento")

    # 3. **El NIF manda, y su unicidad no la tapa la multiplicidad del email** (R1/H-03).
    #    Esta es la frontera de la ronda: la guarda de ambigüedad del email se evaluaba
    #    ANTES del cruce, así que `ids_nif={B}` con `ids_mail={A,B}` salía ambiguo teniendo
    #    la respuesta unívoca delante — y ese es justo el estado que crea el paso 5.
    if len(ids_nif) == 1:
        unico = next(iter(ids_nif))
        if ids_mail and unico not in ids_mail:
            return ResolucionParte(conflicto=(unico, sorted(ids_mail)[0]))
        return ResolucionParte(id=unico, por="nif")

    # 4. Varias fichas para el criterio fuerte: nada desempata.
    if len(ids_nif) > 1:
        return ResolucionParte(ambiguo=tuple(sorted(ids_nif)))

    # 5. Sin match de NIF y con NIF utilizable: decide la tabla del §2.2 (tarea 3).
    if estado_nif == "utilizable" and ids_mail:
        return _resolver_por_buzon_compartido(nif, c_mail, prop_nif)

    # 6. Sin NIF que contrastar, el email es lo único posible.
    if len(ids_mail) > 1:
        return ResolucionParte(ambiguo=tuple(sorted(ids_mail)))
    if ids_mail:
        return ResolucionParte(id=next(iter(ids_mail)), por="email")
    return ResolucionParte()
```

Y arriba, tras `nif_canon = _canonizar_documento(nif)`, añadir:

```python
    estado_nif = _estado_documento(nif)
```

En la tarea 3 se define `_resolver_por_buzon_compartido`; hasta entonces, para que el módulo
importe, añadir el stub **con su test ya escrito** (paso siguiente).

- [ ] **Paso 4: stub mínimo para que el módulo cargue**

```python
def _resolver_por_buzon_compartido(nif, c_mail, prop_nif) -> "ResolucionParte":
    return ResolucionParte(motivo="pendiente: tabla del buzón compartido")
```

- [ ] **Paso 5: verificar que pasan los de esta tarea**

Run: `python -m pytest tests/test_resolver_parte_aper71.py -k "h03 or conflicto or varias_fichas_por_nif or consulta_fallida or sin_nif_y_con_varias" -q --tb=short -p no:randomly`
Esperado: PASS.

- [ ] **Paso 6: commit**

```bash
git add core/sudespacho_relations.py tests/test_resolver_parte_aper71.py
git commit -m "El NIF único manda sobre la multiplicidad del email (R1/H-03)"
```

---

### Tarea 3: La tabla del buzón compartido

**Ficheros:**
- Modificar: `core/sudespacho_relations.py` — `_resolver_por_buzon_compartido`, y la llamada a
  `_buscar_registros` por email para que pida el NIF
- Test: `tests/test_resolver_parte_aper71.py`

**Interfaces:**
- Consume: `_estado_documento`, `_canonizar_documento`, `_values_dict`, `Consulta.registros`.
- Produce: `_resolver_por_buzon_compartido(nif: str, c_mail: Consulta, prop_nif: str) -> ResolucionParte`.

- [ ] **Paso 1: escribir los tests que fallan**

`test_aper71_el_buzon_compartido_con_nif_distinto_crea_ficha_nueva`,
`test_la_ficha_del_buzon_sin_nif_para_en_vez_de_crear`,
`test_h02_un_nif_igual_escrito_de_otra_forma_para_en_vez_de_duplicar`,
`test_para_si_alguna_ficha_del_buzon_no_queda_descartada`,
`test_la_consulta_por_email_pide_tambien_el_nif`,
`test_la_segunda_corrida_sobre_el_mismo_yaml_converge`,
`test_un_tercer_firmante_del_mismo_buzon_tambien_resuelve`.

- [ ] **Paso 2: verificar que fallan**

Run: `python -m pytest tests/test_resolver_parte_aper71.py -q --tb=short -p no:randomly`
Esperado: FAIL en los siete, con `motivo="pendiente: tabla del buzón compartido"`.

- [ ] **Paso 3: la consulta por email pide el NIF**

En `resolver_parte`, sustituir la construcción de `c_mail`:

```python
    c_mail = (_buscar_registros(elemento, "email", (email or "").strip(),
                                properties=(prop_nif,))
              if (email or "").strip() else Consulta())
```

- [ ] **Paso 4: implementar la tabla**

```python
def _resolver_por_buzon_compartido(
    nif: str, c_mail: "Consulta", prop_nif: str,
) -> "ResolucionParte":
    """El NIF aportado es utilizable y no casó ninguna ficha; el buzón sí casó alguna.

    Un email identifica un BUZÓN, no a una persona: el correo doméstico de un matrimonio
    —la norma entre propietarios— es uno solo. Así que cada ficha del buzón se contrasta
    por su documento, y **crear exige que TODAS queden descartadas**.

    Los tres resultados por ficha, y ninguno se puede colapsar (R1/H-01, H-02):

    - documento **utilizable y distinto** → es otra persona: se descarta como candidata;
    - documento **utilizable e igual** → la consulta por NIF debió encontrarla y no lo hizo:
      algo no cuadra y no se adivina;
    - documento **ausente o no interpretable** → no se puede distinguir «la misma sin NIF
      registrado» de «otra».

    Devolver `ResolucionParte()` vacía es autorizar una CREACIÓN, así que solo se devuelve
    cuando la evidencia es comparable en todas.
    """
    mio = _canonizar_documento(nif)
    for reg in c_mail.registros:
        fid = str(reg.get("id") or "").strip()
        suyo = str(_values_dict(reg).get(prop_nif) or "")
        estado = _estado_documento(suyo)
        if estado == "utilizable" and _canonizar_documento(suyo) != mio:
            continue                      # otra persona en el mismo buzón
        if estado == "utilizable":
            return ResolucionParte(motivo=(
                f"la ficha {fid} comparte el email y tiene el MISMO documento, pero la "
                "consulta por NIF no la encontró: revisa cómo está escrito en el CRM"))
        return ResolucionParte(motivo=(
            f"la ficha {fid} comparte el email y no tiene un documento comparable: no se "
            "puede saber si es la misma parte"))
    return ResolucionParte()
```

- [ ] **Paso 5: verificar que pasa el fichero entero**

Run: `python -m pytest tests/test_resolver_parte_aper71.py -q --tb=short -p no:randomly`
Esperado: PASS, 16 tests.

- [ ] **Paso 6: no romper lo que ya había**

Run: `python -m pytest tests/test_sudespacho_relations.py tests/test_crm_dedup_incertidumbre.py -q --tb=short -p no:randomly`
Esperado: PASS. Si algo falla, **leerlo antes de tocarlo**: puede ser un test que congelaba el
comportamiento viejo (legítimo de corregir, con su justificación) o una regresión real.

- [ ] **Paso 7: commit**

```bash
git add core/sudespacho_relations.py tests/test_resolver_parte_aper71.py
git commit -m "El email identifica un buzón, no a una persona ([APER-71])"
```

---

### Tarea 4: La ficha admite N contrarios

**Ficheros:**
- Modificar: `core/crm_ficha.py:109-115` (lectura de `contrario`) y el DTO (~:21)
- Test: `tests/test_crm_ficha_n_contrarios.py` (nuevo)

**Interfaces:**
- Consume: `_contrario_de(dict) -> NuevoClienteContrario` (ya existe).
- Produce: `FichaCRMInput.contrarios: list[NuevoClienteContrario]` (lista, **nunca `None`**).
  `FichaCRMInput.contrario` se conserva como propiedad de compatibilidad que devuelve el
  primero o `None`.

- [ ] **Paso 1: escribir el test que falla**

```python
def test_una_lista_de_dos_contrarios_produce_dos(tmp_path):
    ficha = _escribir(tmp_path, {"contrario": [
        {"nombre": "A", "nif": "11111111H"},
        {"nombre": "B", "nif": "22222222J"},
    ]})
    d = crm_ficha.cargar(ficha)
    assert [c.nombre for c in d.contrarios] == ["A", "B"]


def test_un_mapping_suelto_sigue_valiendo(tmp_path):
    d = crm_ficha.cargar(_escribir(tmp_path, {"contrario": {"nombre": "A"}}))
    assert [c.nombre for c in d.contrarios] == ["A"]
    assert d.contrario.nombre == "A"          # compatibilidad


@pytest.mark.parametrize("valor", [None, []])
def test_ausente_null_y_lista_vacia_son_lo_mismo(tmp_path, valor):
    d = crm_ficha.cargar(_escribir(tmp_path, {"contrario": valor}))
    assert d.contrarios == [] and d.contrario is None


def test_un_elemento_invalido_aborta_con_su_indice_y_no_escribe_nada(tmp_path):
    with pytest.raises(ValueError) as exc:
        crm_ficha.cargar(_escribir(tmp_path, {"contrario": [
            {"nombre": "A"}, "esto-no-es-un-mapping",
        ]}))
    assert "1" in str(exc.value), str(exc.value)
```

- [ ] **Paso 2: verificar que fallan**

Run: `python -m pytest tests/test_crm_ficha_n_contrarios.py -q --tb=short -p no:randomly`
Esperado: FAIL — `AttributeError: 'FichaCRMInput' object has no attribute 'contrarios'`.

- [ ] **Paso 3: implementar**

```python
def _contrarios_de(raw) -> list[NuevoClienteContrario]:
    """`contrario:` como mapping, como lista, o ausente. **Valida TODO antes de devolver.**

    Filtrar los elementos que no sean mapping —el patrón de `colaboradores`— convertiría
    una lista de un elemento inválido en «cero contrarios» en silencio, y validar mientras
    se itera escribiría el primero antes de descubrir que el segundo está roto (R1/H-08).
    **Un elemento inválido no es una parte ausente.**
    """
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [_contrario_de(raw)]
    if not isinstance(raw, list):
        raise ValueError(
            f"'contrario' tiene que ser un mapping o una lista, y es {type(raw).__name__}")
    fuera = [str(i) for i, e in enumerate(raw) if not isinstance(e, dict)]
    if fuera:
        raise ValueError(
            f"'contrario' tiene elementos que no son mappings en las posiciones "
            f"{', '.join(fuera)}: corrígelos; no se escribe nada")
    return [_contrario_de(e) for e in raw]
```

En el DTO, `contrario` pasa a propiedad:

```python
    contrarios: list[NuevoClienteContrario] = field(default_factory=list)

    @property
    def contrario(self) -> NuevoClienteContrario | None:
        """El primero, o `None`. Compatibilidad con los llamadores de un solo contrario."""
        return self.contrarios[0] if self.contrarios else None
```

Y en `cargar`, sustituir las dos líneas de `contrario_raw` por
`contrarios=_contrarios_de(data.get("contrario"))`.

- [ ] **Paso 4: verificar**

Run: `python -m pytest tests/test_crm_ficha_n_contrarios.py tests/test_crm_ficha*.py -q --tb=short -p no:randomly`
Esperado: PASS.

- [ ] **Paso 5: commit**

```bash
git add core/crm_ficha.py tests/test_crm_ficha_n_contrarios.py
git commit -m "La ficha admite N contrarios, validados enteros antes de escribir ([APER-63])"
```

---

### Tarea 5: `sudespacho_actuaciones` — el paso 1 y sus CUATRO salidas

**Ficheros:**
- Crear: `core/sudespacho_actuaciones.py`
- Test: `tests/test_sudespacho_actuaciones.py` (nuevo)

**Interfaces:**
- Consume: `httpx`, `os.getenv("SUDESPACHO_API_KEY")`, `_REST_BASE` (copiar la constante, no
  importar de `relations`: son módulos hermanos).
- Produce: `IdPredefinido` (dataclass con `valor: int | None`, `estado: str`,
  `motivo: str = ""`), estados `"aprendido" | "no_aplica" | "sin_filas" | "sin_comprobar"`;
  `aprender_id_predefinido(asunto: str, *, client=None) -> IdPredefinido`.

- [ ] **Paso 1: escribir los tests que fallan**

```python
def test_aprende_el_id_de_una_instancia_real():
    r = act.aprender_id_predefinido("TA - CONTROL DICTADO SENTENCIA",
                                    client=_cliente([{"id": "1", "values": [
                                        {"property": {"name": "id_predefinido"}, "value": 84}]}]))
    assert (r.estado, r.valor) == ("aprendido", 84)


def test_filas_con_el_campo_vacio_significan_que_NO_nace_de_plantilla():
    """[APER-72] lo midió sobre 20 actuaciones reales: el campo viene vacío en todas.
    Buscarlo y no encontrarlo es el resultado CORRECTO, no un fallo de la consulta."""
    r = act.aprender_id_predefinido("SENIOR - EXTRAJUDICIAL - REVISION VIABILIDAD",
                                    client=_cliente([{"id": "1", "values": []}] * 3))
    assert r.estado == "no_aplica" and r.valor is None


def test_cero_filas_no_es_lo_mismo_que_filas_sin_campo():
    r = act.aprender_id_predefinido("ASUNTO QUE NO EXISTE", client=_cliente([]))
    assert r.estado == "sin_filas" and r.valor is None


def test_una_consulta_fallida_no_es_ausencia():
    r = act.aprender_id_predefinido("X", client=_cliente_que_falla())
    assert r.estado == "sin_comprobar" and r.valor is None
```

- [ ] **Paso 2: verificar que fallan**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py -q --tb=short -p no:randomly`
Esperado: FAIL — `ModuleNotFoundError: core.sudespacho_actuaciones`.

- [ ] **Paso 3: implementar el módulo y la función**

Cabecera del módulo con la receta citada (§15.6) y:

```python
@dataclass(frozen=True)
class IdPredefinido:
    """Qué se sabe del `id_predefinido` de un asunto. **Cuatro estados, no dos.**

    `[APER-72]` midió sobre 20 actuaciones reales que el campo viene VACÍO: esas actuaciones
    no nacen de plantilla y el campo se OMITE en el POST. Confundir «no aplica» con «no pude
    mirar» o con «no hay filas» lleva a inventar un entero, y el paso 1 de la receta existe
    justamente para no inventarlo.
    """
    estado: str
    valor: int | None = None
    motivo: str = ""
```

`aprender_id_predefinido` consulta `element_registries/actuaciones` con
`properties[0]=Subject`, `properties[1]=id_predefinido`, `operator=like` sobre el asunto, y
clasifica: excepción o HTTP != 200 → `sin_comprobar`; sin filas → `sin_filas`; filas con todos
los `id_predefinido` vacíos → `no_aplica`; un entero → `aprendido`.

- [ ] **Paso 4: verificar**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py -q --tb=short -p no:randomly`
Esperado: PASS, 4 tests.

- [ ] **Paso 5: commit**

```bash
git add core/sudespacho_actuaciones.py tests/test_sudespacho_actuaciones.py
git commit -m "El paso 1 de la receta tiene CUATRO salidas ([APER-72], MEJORAS #209)"
```

---

### Tarea 6: El paso 3 — resolver el destino y contrastarlo

**Ficheros:**
- Modificar: `core/sudespacho_actuaciones.py`
- Test: `tests/test_sudespacho_actuaciones.py`

**Interfaces:**
- Produce: `Destino` (dataclass: `elemento: str`, `exp_id: str`, `evidencia: str`);
  `resolver_destino(elemento: str, exp_id: str, referencia_esperada: str, *, client=None) -> Destino`.
  Lanza `DestinoNoAcreditado` si la referencia no casa.

- [ ] **Paso 1: escribir los tests que fallan**

```python
def test_un_expediente_de_OTRO_caso_con_el_mismo_numero_no_se_acredita():
    """Cada elemento numera aparte: en W-02VEKE, 464 es de extrajudiciales y 540 del judicial,
    y `GET expedientes_judiciales/464` devuelve un expediente de OTRO caso, con 200 y todo."""
    with pytest.raises(act.DestinoNoAcreditado):
        act.resolver_destino("expedientes_judiciales", "464", "BaRS10 - … (W-02VEKE) - …",
                             client=_cliente_expediente("OTRA COSA (W-0XXXXX)"))


def test_el_destino_correcto_se_acredita_con_su_evidencia():
    d = act.resolver_destino("extrajudiciales", "464", "BaRS10 - … (W-02VEKE) - …",
                             client=_cliente_expediente("BaRS10 - … (W-02VEKE) - …"))
    assert d.exp_id == "464" and "W-02VEKE" in d.evidencia


def test_no_acreditar_el_destino_no_escribe_nada(monkeypatch):
    escrituras = []
    monkeypatch.setattr(act, "crear_actuacion", lambda *a, **k: escrituras.append(1))
    with pytest.raises(act.DestinoNoAcreditado):
        act.resolver_destino("extrajudiciales", "464", "ESPERADA",
                             client=_cliente_expediente("OTRA"))
    assert escrituras == []
```

- [ ] **Paso 2: verificar que fallan**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py -k destino -q --tb=short -p no:randomly`
Esperado: FAIL — `AttributeError: module has no attribute 'resolver_destino'`.

- [ ] **Paso 3: implementar**

`resolver_destino` hace `GET element_registries/{elemento}` filtrando por id, pide la property
de referencia (`Referencia_Cliente` para `extrajudiciales`, `referencia_cliente` para
`expedientes_judiciales` — **no se unifican**, pedirle la mayúscula al judicial da HTTP 500) y
compara por W-code con `wcode_match` del módulo hermano. Sin coincidencia → `DestinoNoAcreditado`
con los dos valores en el mensaje.

- [ ] **Paso 4: verificar**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py -q --tb=short -p no:randomly`
Esperado: PASS.

- [ ] **Paso 5: commit**

```bash
git add core/sudespacho_actuaciones.py tests/test_sudespacho_actuaciones.py
git commit -m "Verificar la llegada no verifica la intención: el paso 3 (R1/H-06)"
```

---

### Tarea 7: El recibo reanudable (pasos 4-6)

**Ficheros:**
- Modificar: `core/sudespacho_actuaciones.py`
- Test: `tests/test_sudespacho_actuaciones.py`

**Interfaces:**
- Produce: `Recibo` (dataclass: `estado: str`, `act_id: str | None`, `paso: int`, `motivo: str`),
  estados `"verificada" | "incompleta" | "incierta"`;
  `crear_actuacion(...) -> str`, `vincular_actuacion(...) -> None`,
  `verificar_actuacion_vinculada(...) -> bool`,
  `alta_actuacion(..., desde: Recibo | None = None) -> Recibo`.

- [ ] **Paso 1: escribir los tests que fallan**

```python
def test_si_el_vinculo_falla_el_recibo_conserva_el_id_creado():
    """Una verificación negativa NO es ausencia de escritura (R1/H-04). Sin el id, el
    reintento crea otra actuación y la primera queda huérfana."""
    r = act.alta_actuacion(..., client=_cliente_que_crea_y_falla_al_vincular("N"))
    assert r.estado == "incompleta" and r.act_id == "N" and r.paso == 4


def test_reanudar_desde_el_recibo_no_crea_otra_actuacion():
    creadas = []
    r1 = act.alta_actuacion(..., client=_cliente_que_crea_y_falla_al_vincular("N", creadas))
    r2 = act.alta_actuacion(..., desde=r1, client=_cliente_que_vincula_ok(creadas))
    assert creadas == ["N"], f"creó otra actuación al reanudar: {creadas}"
    assert r2.estado == "verificada"


def test_un_post_sin_recibo_deja_el_estado_INCIERTO_y_no_se_reintenta():
    r = act.alta_actuacion(..., client=_cliente_que_hace_timeout_al_crear())
    assert r.estado == "incierta" and r.act_id is None


def test_alta_actuacion_no_declara_exito_sin_la_verificacion_del_paso_6():
    r = act.alta_actuacion(..., client=_cliente_que_crea_y_vincula_pero_no_aparece("N"))
    assert r.estado != "verificada"
```

- [ ] **Paso 2: verificar que fallan**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py -k "recibo or reanudar or incierto or paso_6" -q --tb=short -p no:randomly`
Esperado: FAIL.

- [ ] **Paso 3: implementar**

`alta_actuacion` encadena 1→6; con `desde` salta al paso indicado reutilizando `act_id`. Un fallo
tras el POST devuelve `incompleta` con el id; un fallo **durante** el POST sin respuesta,
`incierta`. Docstring: **reintentar el alta completa en estado `incompleta` está prohibido**.

- [ ] **Paso 4: verificar**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py -q --tb=short -p no:randomly`
Esperado: PASS.

- [ ] **Paso 5: commit**

```bash
git add core/sudespacho_actuaciones.py tests/test_sudespacho_actuaciones.py
git commit -m "El recibo reanudable: una verificación negativa no es ausencia de escritura (R1/H-04)"
```

---

### Tarea 8: El asunto canónico y la duración

**Ficheros:**
- Modificar: `core/sudespacho_actuaciones.py`, `core/crm_ficha.py` (campo `firmante`)
- Test: `tests/test_sudespacho_actuaciones.py`, `tests/test_crm_ficha_n_contrarios.py`

**Interfaces:**
- Produce: `asunto_canonico(base: str, *, firmante: str) -> str` (lanza `ValueError` sin
  firmante); `duracion_desde_ronda(case_dir: Path) -> int | None`;
  `FichaCRMInput.firmante: str = ""`.

- [ ] **Paso 1: escribir los tests que fallan**

```python
def test_el_asunto_exige_el_firmante_porque_el_prefijo_ES_la_tarifa():
    """SENIOR factura a 103,00 €/h y ABOGADO a 77,00 ([APER-72], 20 actuaciones reales).
    Elegir el prefijo por defecto factura al cliente la tarifa de otro."""
    with pytest.raises(ValueError):
        act.asunto_canonico("EXTRAJUDICIAL - REVISION VIABILIDAD", firmante="")


def test_el_firmante_no_es_quien_opera():
    """Ana puede tramitar una revisión que firma Nikolai (R1/H-05)."""
    a = act.asunto_canonico("EXTRAJUDICIAL - REVISION VIABILIDAD", firmante="Nikolai_Tyukhay")
    assert a.startswith("SENIOR - ")


def test_la_duracion_sale_de_la_ronda_v1_y_dice_None_si_no_cerro(tmp_path):
    """El fichero es `_apertura_v1.json`, no `estado.json`, y el evento de cierre NO lleva
    las fechas (R1/H-07)."""
    assert act.duracion_desde_ronda(_ronda(tmp_path, "2026-09-14T10:00:00Z",
                                           "2026-09-14T10:01:30Z")) == 90
    assert act.duracion_desde_ronda(_ronda(tmp_path, "2026-09-14T10:00:00Z", None)) is None


def test_extremos_invertidos_se_rechazan(tmp_path):
    with pytest.raises(ValueError):
        act.duracion_desde_ronda(_ronda(tmp_path, "2026-09-14T10:01:30Z",
                                        "2026-09-14T10:00:00Z"))
```

- [ ] **Paso 2: verificar que fallan**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py -k "asunto or firmante or duracion or invertidos" -q --tb=short -p no:randomly`
Esperado: FAIL.

- [ ] **Paso 3: implementar**

`asunto_canonico` mapea username → prefijo con una tabla explícita y **sin defecto**; el mapeo
vive en el módulo con su fuente (`docs/MANUAL_DESPACHO.md`) citada. `duracion_desde_ronda` usa
`core.apertura_v1_estado.leer`, acepta `Z`, devuelve `None` con `terminada` ausente y lanza con
extremos invertidos. Docstring: **mide la ronda V1 (Drive → CRM → sala de máquina), no la
actividad facturable**.

`FichaCRMInput` gana `firmante: str = ""`, leído de `data.get("firmante")`.

- [ ] **Paso 4: verificar**

Run: `python -m pytest tests/test_sudespacho_actuaciones.py tests/test_crm_ficha_n_contrarios.py -q --tb=short -p no:randomly`
Esperado: PASS.

- [ ] **Paso 5: commit**

```bash
git add core/sudespacho_actuaciones.py core/crm_ficha.py tests/
git commit -m "El prefijo ES la tarifa, y la duración mide la ronda que mide ([APER-72], R1/H-05, H-07)"
```

---

### Tarea 9: El arnés de mutación

**Ficheros:**
- Crear: `tests/_mutantes_p6.py`

- [ ] **Paso 1: escribir el arnés** con el contrato de la casa (copiar la estructura de
  `tests/_mutantes_p4.py`: `_escribir` con reintentos, `_corre` devolviendo `(rc, salida)`,
  `_PYTEST_USAGE_ERROR` distinguido de un rojo, restauración armada **antes** de mutar).

  Mutantes mínimos, uno por decisión: el orden del NIF sobre el email; `_estado_documento`
  colapsando `no_interpretable` en `ausente`; la comparación textual en vez de canónica; el
  `continue` de la tabla convertido en `return vacía`; la consulta por email sin `properties`;
  el filtrado silencioso de elementos no-mapping; las cuatro salidas del paso 1 reducidas a
  dos; `resolver_destino` sin contraste; el recibo perdiendo el `act_id`; `asunto_canonico`
  con defecto.

- [ ] **Paso 2: correr con el árbol limpio**

Run: `python -m tests._mutantes_p6`
Esperado: todos muertos, o los supervivientes **declarados con su razón**.

- [ ] **Paso 3: commit**

```bash
git add tests/_mutantes_p6.py
git commit -m "El arnés de P6: cada mutante apunta a su test"
```

---

### Tarea 10: Documentación y cierre

**Ficheros:**
- Modificar: `docs/RUNBOOK_APERTURA_EXPEDIENTE.md`, `PLAN.md`, `docs/MEJORAS_FUTURAS.md`

- [ ] **Paso 1:** `[APER-71]`, `[APER-63]` y `[APER-72]` ganan su bloque «resuelto el
  2026-09-14», **con lo que sigue sin resolverse dicho**: la parte de un nombre opaco no se
  infiere, y la tarifa efectiva sigue sin acreditarse por un `Subject`.
- [ ] **Paso 2:** `MEJORAS #209` cerrada con su PR.
- [ ] **Paso 3:** fila #33 en `PLAN.md` con las dos rondas y sus actas.
- [ ] **Paso 4: la verja.** Run: `python -m scripts.session_close`
  Esperado: dos semillas (777, 31337) verdes. Explicar la variación del conteo.
- [ ] **Paso 5: R2 adversarial sobre el diff**, adjudicar, acta hermana `…-r2-…`.
- [ ] **Paso 6:** PR. **No mergear**: lo decide Nikolai.

---

## Auto-revisión del plan

**Cobertura del spec:** §1 (vocabulario) → tarea 1. §2.1 (orden) → tarea 2. §2.2 (tabla) →
tarea 3. §2.3 (reejecución) → tests de la tarea 3. §3 (YAML) → tarea 4. §4 tabla de funciones →
tareas 5-8. §4.1 (paso 3) → tarea 6. §4.2 (recibo) → tarea 7. §4.3 (rol) y §4.4 (duración) →
tarea 8. §5 (pruebas) → repartido. **Sin huecos.**

**Sin placeholders:** cada paso de código lleva su código o el nombre exacto de los tests ya
escritos en `tests/test_resolver_parte_aper71.py`.

**Consistencia de tipos:** `IdPredefinido.estado` y `Recibo.estado` son `str` con conjuntos
cerrados documentados; `ResolucionParte.motivo` es `str` y se consulta en `resuelta`;
`FichaCRMInput.contrarios` es `list` y `contrario` propiedad derivada — los llamadores actuales
de `.contrario` siguen funcionando.
