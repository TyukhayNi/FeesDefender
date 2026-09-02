---
tipo: plan
objeto: "MEJORAS #136 — el registro de workspaces no admite el canon como copia local"
estado_remediacion: remediado
creado: 2026-09-02
---

# `MEJORAS #136` — el canon no es una copia de trabajo, y ahora el registro lo sabe

> **Qué es esto.** El defecto no tenía plan propio: apareció como hallazgo **H21-01** mientras se
> revisaba el diseño de `MEJORAS #124`, y resultó ser un **defecto vivo en `main`**, no del diseño.
> Este documento existe porque las adjudicaciones tienen que vivir en el documento que la decisión
> modificó, y el corpus de los guards **G7/G8** es `docs/superpowers/` — una adjudicación en
> `MEJORAS_FUTURAS.md` quedaría sin comprobar.
>
> **Rondas: R22 (diff) y R23 (diff remediado, autorizada expresamente por Nikolai).** El radio de
> daño es «decide quién puede escribir sobre qué copia», que en `CLAUDE.md` compra dos; la tercera
> la autorizó él, que es lo que el techo duro exige.
>
> **Cobertura de revisión de la remediación de R23: AUSENTE.** Nadie ha atacado el árbol tal como
> queda. Se declara en vez de darlo por bueno: un revisor que no corre no refuta.

---

## 1. El defecto, medido

`repository_cli adoptar` apuntado a **la ruta del canon** era **ACEPTADO**. Desde ese momento
`es_copia_prestada` devolvía `True` y todo el intake escribía sobre el expediente **sin desviar,
mientras estaba prestado**. Sonda del 2026-09-02:

```
verificar_adopcion.ok  : True | checkout propio con manifest y nombre coherente
adoptar(CANON)         : ACEPTADO
es_copia_prestada      : True
dir_intake             : <CANON>\00_Input\03_Email      ← SIN desviar
resolver .working_root : <CANON>   (mode = local_checkout)
```

**La causa, en una frase:** la invariante «el registro no contiene rutas del catálogo» la aplicaba
**un solo lector** (`resolver_por_ruta`) y **ninguno** de los escritores. Y era alcanzable porque el
canon **también** recibe `MANIFEST_CHECKOUT.json` mientras está prestado — el mismo hecho con el que
se había descartado el manifiesto como discriminante, sin cruzarlo nunca con la adopción.

**Por qué es un error natural y no exótico:** `adoptar` toma la ruta como posicional y deduce el
W-code **del nombre de la carpeta**, que es idéntico en las dos copias. Apuntar al Drive en vez de al
Desktop es el error propio de quien usa un comando que existe para «tengo un checkout y el registro
no lo sabe».

---

## 2. El diseño, tal como quedó

| Puerta | Dónde | Qué regla |
|---|---|---|
| **G-A** | `WorkspaceRegistry._escribir` | la **invariante**: ninguna entrada `DENTRO` llega a disco |
| **G-B** | `alta` / `revalidar` (`_exigir_clasificable`) | la **política**: no se introduce lo que no se pueda demostrar `FUERA` |
| **G-C** | `verificar_adopcion` | el motivo **legible** antes de la firma humana |
| **G-D** | `_visibles` en `cargar`/`buscar` | oculta lo canónico heredado, **nunca** lo indeterminado |
| **G-E** | `clasificar_bajo` | componentes de ruta **+** `os.path.realpath` |
| **G-F** | `CaseWorkspaceResolver._sin_canonicos` | **autoriza**: exige `FUERA`, no «distinto de dentro» |

### 2.1. Tres estados, no un booleano

`DENTRO` / `FUERA` / `INDETERMINADO`. Colapsarlos obliga a elegir una polaridad, y **los consumidores
tienen polaridades opuestas**: quien autoriza lee «no lo sé» como «no»; quien conserva no puede, o
borra. La primera versión usaba el booleano y **perdía datos** (§4, H22-04).

### 2.2. La invariante y la política no son la misma regla

`_escribir` rechaza solo lo demostradamente `DENTRO`; `alta` y `revalidar` rechazan además lo
indeterminado. Si `_escribir` rechazara ambos, una entrada ya presente que se volviera inclasificable
dejaría el registro **bloqueado para escritura** — no podrías ni darla de baja. Dos reglas con
sujetos distintos en sitios distintos no son una guarda duplicada.

### 2.3. La resolución física es del sistema operativo, no mía

`os.path.realpath` sobre las dos rutas y comparación de componentes. Sustituye a un ascenso por
ancestros con `samestat` que yo había inventado y en el que R23 encontró tres defectos. Menos
superficie propia.

**Límite declarado:** la equivalencia **UNC ↔ letra de unidad** no se cubre. `realpath` no traduce
`\\host\C$\x` a `C:\x`. Queda **SIN VERIFICAR**, no refutado.

---

## 3. Lo que este documento NO arregla

- **H23-05** — `revalidar` reemplaza `local_path` en **todas** las entradas que casan con el
  `CaseRef`, y el registro contrata que un checkout y un scratch del mismo W-code coexisten.
- **H23-06** — la unicidad de carpeta de `alta` compara `normcase(str(path))`, así que la misma
  carpeta escrita relativa y absoluta atraviesa la guarda.

**Los dos son preexistentes en `e24b9c6`** —lo dice el propio revisor— y sin llamador productivo.
Van a `MEJORAS` con su medición. Un PR que arregla todo lo que encuentra por el camino deja de ser
revisable, y ésa es la única razón: no son menos ciertos por quedarse fuera.

---

## 4. Adjudicación de la revisión adversarial (Codex, 2026-09-02) — NO-SHIP, remediado

- **Objeto revisado:** el diff de la primera versión, commit `55dcb06`
- **Ronda:** R22 (diff)
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-02-mejoras-136-r22-adversarial-review.md`
- **Hallazgos:** 9 — 4 CRÍTICOS, 4 ALTOS, 1 BAJO; **9 confirmados, 0 refutados**
- **Remediado en:** commits `b464578`, `479e71c`, `c2a9b86`

**Los cuatro graves, reproducidos por mí antes de tocar nada:**

```
H22-01  extendida \\?\...\CASOS\Caso  : False   (normal: True, samefile: True)
H22-06  CASOS_ROOT=C:\ , hijo C:\tmp  : False   (deberia ser True)
H22-02  revalidar escribe el canon    : True    (segundo escritor sin guarda)
H22-04  'Uno' sigue en el JSON crudo  : False   ← PERDIDA DE DATOS
```

**H22-02 y H22-04 son defectos míos, y de distinta clase.** El primero es el censo incompleto: puse
el rechazo en los dos sitios donde vi el ejemplo y me dejé la frontera. El segundo lo **introduje al
arreglar**: filtrar al leer con el booleano que falla cerrado ocultaba lo indeterminado, y `alta`
reescribía desde la vista filtrada.

**Y H22-08 va en la dirección contraria a la habitual:** el revisor demostró que
`test_un_registro_ilegible_NO_desactiva_el_guard` **sí** discrimina su polaridad. Yo había escrito en
su docstring que no podía. No inflé lo que el test probaba: lo **rebajé** — y una nota de humildad
falsa habría retirado de la vista la única prueba de esa polaridad.

**Nota de método, porque cuesta una ronda:** la primera corrida de R22 murió en el filtro de
contenido del revisor, y **lo que se cortó fue mi encargo** —pedía «rodear las cuatro puertas»—, no
el objeto. Segunda vez que piso esa trampa teniéndola anotada. Mientras estuvo cortada el estado
correcto era **sin verificar**, no «refutado». Se relanzó reformulada como problema de
**clasificación** y esa corrida es la archivada.

---

## 5. Adjudicación de la revisión adversarial (Codex, 2026-09-02) — NO-SHIP, remediado

- **Objeto revisado:** el diff remediado, commit `c2a9b86`
- **Ronda:** R23 (diff remediado, autorizada expresamente por Nikolai)
- **Revisor:** Codex
- **Informe recibido:** `docs/superpowers/specs/2026-09-02-mejoras-136-r23-adversarial-review.md`
- **Hallazgos:** 7 — 1 CRÍTICO, 2 ALTOS, 3 MEDIOS, 1 BAJO; **7 confirmados, 0 refutados**
- **Remediado en:** commit `7e54c99` (H23-05 y H23-06 **no**, §3)

**El CRÍTICO es la misma frontera mal cerrada por CUARTA vez en esta sesión.** Una *junction* que
apunta a un **descendiente** del catálogo se clasificaba `fuera` sobre la misma carpeta: el ascenso
por ancestros seguía el árbol **léxico** y nunca visitaba el padre físico canónico. Yo había
contratado el caso «*junction* → raíz» y di por generalizada la propiedad, que es *«cualquier alias
cuyo destino físico caiga dentro del catálogo»*.

Reproducido y cerrado con **la misma sonda**:

```
antes   junction -> RAIZ : dentro    junction -> CASO : fuera   (samefile: True)
despues junction -> RAIZ : dentro    junction -> CASO : dentro
```

**H23-03 nombra una distinción que el diseño no tenía:** el resolver filtraba con `!= DENTRO`, o sea
con la polaridad de **conservar**. El registro guarda lo indeterminado a propósito —para no
borrarlo—, pero entregárselo al resolver convertía esa entrada conservada en un `LOCAL_CHECKOUT`
cuya raíz podía ser físicamente el canon. **Conservar no es autorizar**, y las dos fronteras hacen la
misma pregunta con polaridades opuestas.

**H23-07 se cerró construyendo lo que pedía.** Tenía razón: «catorce mutantes mueren cada uno por su
frontera» en un mensaje de commit **no es verificable**. El manifiesto ejecutable vive en
`tests/_mutantes_mejoras_136.py`. **Y ejecutarlo destapó cuatro problemas más que ninguna ronda
vio:** dos expectativas mías demasiado estrechas y dos mutantes rotos —uno retiraba una *llamada*
que otro test parchea, otro dejaba un nombre sin importar y moría por `NameError`, no por contrato—.

**Lo que las tres rondas enseñan juntas, y no es sobre este código:** R21 encontró el defecto, R22
encontró que mi arreglo estaba incompleto **y que introducía otro**, R23 encontró que mi segundo
arreglo cerraba un caso de la frontera y no la frontera. Ninguna volvió limpia. El criterio implícito
«hasta que una ronda vuelva sin críticos» **no converge**; lo que sí ahorró rondas fue, cada vez,
preguntar de qué frontera era ejemplo el hallazgo — y la vez que no lo pregunté, la ronda siguiente
lo cobró.

---

## 6. Estado

**Suite 3.727+ / 0 fallos / 0 errores** con las semillas 777 y 31337, `XPASS 0`. **14 mutantes, 14
muertos, cada uno por su frontera**, reproducible con `python -m tests._mutantes_mejoras_136`.

**Cobertura de revisión de lo remediado tras R23: ausente.**
