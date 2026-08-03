---
tipo: handoff
estado: activo
creado: 2026-08-03
origen: sesión Claude Code autora de la pieza A (PR #193) — encargo escrito el 2026-08-03 para lanzarlo el 2026-08-08
destino: Codex — revisión adversarial de ronda 2, solo lectura, sobre el CÓDIGO ya mergeado
titulo: Encargo de revisión adversarial ronda 2 — identidad del segmento de bundle, pieza A (código mergeado)
revisor: Codex
objeto_commit: 88339aa
ronda: "2"
ruta_informe: C:\Users\tnm33\Dev\_revisiones\2026-08-08-identidad-pieza-a-r2-codex.md
ronda_anterior: docs/superpowers/specs/2026-08-02-identidad-segmento-bundle-pieza-a-r1-claude-adversarial-review.md
---

> **Andamio efímero** (gobernanza §5). Este fichero **es el mandato literal**: al archivar la revisión
> se copia entero al **§0 del acta** de la ronda 2.
>
> **Escrito el 2026-08-03, para lanzarse el 2026-08-08**, cuando Codex recupere cupo. Se escribe con
> antelación a propósito —el contexto de la construcción está fresco— y por eso el §0 avisa de lo que
> eso puede costar.

---

# MANDATO — revisión adversarial, ronda 2 (código)

## 0. Qué eres aquí, y una advertencia sobre quién escribió este mandato

Eres el **revisor adversarial** del código que implementa la pieza A de la identidad del segmento de
bundle. La ronda 1 fue sobre el **plan**; esta es sobre el **código mergeado**.

**Tú no adjudicas.** Un hallazgo tuyo puede ser correcto y su remedio pasarse de rosca; distinguirlo
lo hace quien tiene la intención del encargo en la mano.

**Dos advertencias, y las dos importan para calibrar cuánto desconfiar:**

1. **Este mandato lo escribió el autor del código, cinco días antes de que lo leas.** Está redactado
   para dirigirte a lo que él cree que es frágil. **Eso es exactamente lo que no debes dar por
   bueno.** El §3 son puntos de partida, no el perímetro: si el ataque más rentable está fuera de esa
   lista, esa es la respuesta correcta y el §5 tiene sitio para decirlo.
2. **La ronda 1 la hizo un revisor sustituto del MISMO MODELO que el autor** —sesión limpia de Claude
   Code, porque tú estabas sin cupo— y **refutó 0 de 24 hallazgos**. Encontró cosas reales, incluido
   un `B0` de diseño, pero **no discrepó del autor ni una vez**. Trata por tanto lo «ya adjudicado»
   como **no verificado por nadie independiente**, no como cerrado. Acta con su informe literal y
   digest: `docs/superpowers/specs/2026-08-02-identidad-segmento-bundle-pieza-a-r1-claude-adversarial-review.md`;
   adjudicación en el §14 del spec.

## 1. Objeto

```text
repo:    https://github.com/TyukhayNi/FeesDefender  (rama main)
cambio:  88339aa  — squash del PR #193, «identidad persistente del segmento de bundle»
```

Trabaja sobre `origin/main` al día de la revisión, y usa `git show 88339aa` para ver el conjunto del
cambio. Ficheros del cambio: `core/split_documental.py`, `core/sala_maquina.py`,
`scripts/sala_maquina.py`, `tests/test_split_doc_id.py`, `tests/test_split_reconciliacion.py`,
`tests/test_sala_maquina_generacion.py`, `tests/test_split_reproceso_e2e.py`,
`tests/test_docs_gobernanza.py`, más `tests/test_sala_maquina.py`, `tests/test_split_documental.py` y
`tests/test_split_sala_maquina_e2e.py` tocados.

**Contrato de diseño vigente:** `docs/superpowers/specs/2026-08-01-identidad-segmento-bundle-design.md`
**rev. 4** (§0 y §3–§9). La **pieza B** (§10–§12) está bloqueada y **fuera de alcance**.

## 2. Solo lectura, y qué significa

El repo, los ficheros ignorados por git, `data/CASOS/`, la unidad `G:` y los sistemas externos (CRM,
Drive) son **entradas de solo lectura durante toda la revisión**.

**Sí** puedes ejecutar código y tests cuando **todas** sus escrituras van fuera del repo:
`PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `--basetemp` fuera del árbol.
`git status --porcelain --untracked-files=all` antes y después es evidencia adicional, **no**
sustituto de la prohibición.

Dos trampas del arnés, medidas, que te ahorrarán un falso hallazgo:

- **`--basetemp` CORTO** (p. ej. `C:/tmp/x`): con ruta larga,
  `test_migrar_nombres_informe::test_resumen_cuenta_por_estado` falla por presupuesto de `MAX_PATH`
  y **no es un fallo del repo**.
- **`--runslow`**: `tests/test_split_sala_maquina_e2e.py` está marcado `slow` y `conftest.py` lo salta
  por defecto. Sin la bandera, el verde no cubre el e2e del split.

Base medida por el autor el 2026-08-02 con `--runslow`: **2785 tests, 0 failures, 2771 passed,
7 skips, 7 xfailed, 0 XPASS**. Los 7 `xfail` son defectos vivos de OTRA línea de trabajo
(arquitectura dual del expediente): **no son tuyos**.

## 3. Puntos de partida, ordenados por daño

Contéstalos punto por punto, numera tus hallazgos `H-NN` con severidad `B0`/`A`/`M`. Y si el ataque
más rentable está fuera de esta lista, dilo.

1. **La fusión autoritativa (`fusionar_cobertura`, spec §6.1) es lo más nuevo y lo menos revisado.**
   Descarta las filas previas de todo `rel_path` que la corrida reprocesa. El conjunto lo pone el
   llamador desde el **plan**, no desde las filas. ¿Hay algún camino en el que eso **borre registro
   de custodia que nadie reescribe**? Mira en particular `reforzar` (que llama sin el conjunto), el
   camino `--solo`, y un documento que falla a mitad: sus filas nuevas no existen, ¿se han descartado
   ya las viejas?
2. **El passthrough que archiva (`archivar_bundle_entero`, spec §7.1).** Retira la carpeta entera de
   un bundle que ha dejado de detectarse como tal, **manifiesto incluido**. ¿Puede disparar cuando no
   debe —un `detectar` que falla por una causa transitoria (fichero bloqueado, memoria) en vez de por
   el contenido— y retirar una generación buena? ¿Y el `shutil.rmtree(..., ignore_errors=True)` deja
   estados a medias que nadie audita?
3. **El guard bidireccional (`verificar_integridad_bundles`) y su alcance.** Corre **después** de
   persistir y sale 3. ¿Hay un camino en el que el alcance salga vacío y el guard no mire? ¿Y uno en
   el que aborte por daño que la corrida no causó (hay 7 huérfanos medidos en 2 casos reales, ver
   `MEJORAS #117`)?
4. **Los mutantes que el autor NO construyó.** Declara 22 mutantes lanzados y 22 muertos. Es el punto
   donde un revisor del mismo modelo aporta menos y tú más: **construye los que él no pensó**. La
   ronda 1 encontró dos vivos justo así (tombstones que no acumulaban; el test de custodia que solo
   asertaba los `.md`).
5. **La publicación por generación bajo fallo parcial.** `publicar_segmentos` archiva y luego mueve;
   el archivado **no es transaccional** y está declarado como tal. ¿La ventana es la que dice el spec,
   o hay estados peores no declarados? ¿Puede una fila de cobertura acabar declarando un `sha` que no
   corresponde a los bytes publicados?
6. **El ledger (`next_doc_id`, `retirados`) y la validación de `doc_id`.** `re.fullmatch(r"d[0-9]{2,}")`
   tras un hallazgo de la ronda 1 sobre `re.match` con `$`. ¿Queda alguna forma que entre en una ruta?
   ¿Puede el ledger decrecer o reutilizar un tombstone por algún camino (manifiesto editado a mano,
   `--force` sobre un mixto, JSON con tipos raros)?
7. **El preflight y sus promesas acotadas.** Valida identidad y no rangos, y su «cero bytes escritos»
   se rebajó a «cero artefactos de Sala de máquina» porque `apply` atomiza el correo antes. ¿Las
   acotaciones del spec §4 describen de verdad lo que hace el código?
8. **`MEJORAS #117`, los cinco límites declarados.** ¿Alguno es en realidad un defecto que se está
   normalizando por escrito?

## 4. Lo que NO tienes que hacer

- **No adjudicas** (§0).
- **No revises la pieza B** (§10–§12 del spec): bloqueada por un lock roto que arregla otra línea.
- **No escribas en `G:`** ni ejecutes nada contra un caso real. Si necesitas un caso para medir,
  cópialo antes a un temporal fuera del repo.
- **No repitas el censo de daño** de `MEJORAS #117` (7 huérfanos en 2 casos, medido read-only el
  2026-08-02) salvo que tengas una sospecha nueva; si la tienes, dila como hallazgo.

## 5. Cómo se entrega el informe

- **Ruta fijada, fuera del repo** (créala si no existe; **no sobrescribas informes anteriores**: sus
  digests son la cadena de custodia):

  ```text
  C:\Users\tnm33\Dev\_revisiones\2026-08-08-identidad-pieza-a-r2-codex.md
  ```

- **Devuelve `ruta` y `sha256` canónico** —UTF-8, `LF`, un único salto final— **antes de que se
  adjudique**, por un canal separado del fichero.
- **Veredicto** del vocabulario cerrado, en la primera línea: `SHIP` · `LISTA-CON-CAMBIOS` ·
  `REQUIERE-REVISION` · `NO-SHIP` · `NO-EJECUTABLE` · `SIN-VEREDICTO`.
- **Secciones obligatorias**, además de la respuesta al §3 y la tabla de hallazgos: `## Verificado
  ejecutando` (con la salida literal), `## Verificado leyendo`, `## Lo que intenté refutar y NO pude`
  y `## NO VERIFICADO`. **Un revisor que no corre no refuta: deja sin verificar**, y eso se declara.
- **Y una sección que este encargo te pide expresamente:** `## Lo que la ronda 1 dio por bueno y no
  lo está`. Si no encuentras nada, dilo — pero búscalo, porque la ronda 1 no refutó nada y eso es
  improbable, no tranquilizador.

## 6. Cómo se registrará

Tu informe se archiva **literal**, con su digest, en un acta hermana —nombre canónico del §4 del
contrato: `…-pieza-a-r2-codex-adversarial-review.md`, fechada el día de la revisión— y la adjudicación
va embebida en el spec, como **§15**. El acta llevará `revisor: Codex` e `independencia: independiente`
— por primera vez en esta pieza, con verdad.
