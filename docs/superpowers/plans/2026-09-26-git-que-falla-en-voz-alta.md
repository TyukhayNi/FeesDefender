---
tipo: plan
estado: vigente
creado: 2026-09-26
objeto: que ningún guard ni verja lea un fallo de git como «no hay nada»
spec: docs/superpowers/specs/2026-08-01-gobernanza-revisiones-adversariales-design.md
---

# Git que falla en voz alta

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** que un guard, la verja de cierre o el escaneo de CI que enumeran con `git` **paren o lo declaren** cuando `git` falla, en vez de leer la salida vacía como «no hay nada que objetar» y dar verde sin haber mirado.

**Architecture:** tres sitios con tres remedios del mismo principio —«no pude medir» no es «medí y salió cero»—. En los tests, un helper único (`tests/_git.py`) que ejecuta `git` y hace `pytest.fail` con su stderr si el código de salida no es uno de los que el comando usa como respuesta. En `session_close`, una **sonda** previa: si `git` no responde en el árbol, se dice, los avisos que dependen de él salen como «no comprobado» y la verja corre los tests lentos por si acaso. En CI, `pipefail` en el paso de `leak-scan`.

**Tech Stack:** Python 3.14, `pytest`, GitHub Actions (bash). Sin dependencias nuevas.

## Global Constraints

- Nunca se borra ni se debilita un test para poner verde; los guards migrados conservan sus aserciones.
- Un negativo contra un literal se vacía: los «no contiene» se escriben contra constantes del módulo.
- Aceptar el cambio son dos semillas (777 y 31337), con la suite entera.
- Tocar un guard **no se exime nunca** de revisión (`CLAUDE.md`).

---

## 1. El hallazgo y su frontera

**Lo vio la R1 de Codex de los estados medidos** (2026-09-26, sección SIN VERIFICAR de su informe): `_md_trackeados()` de `tests/test_docs_gobernanza.py` hace `git ls-files` sin mirar el código de salida. En la copia `git archive` sin `.git` sobre la que trabajan los revisores, `git` falla, la lista sale vacía y los guards que la recorren **pasan en verde sin haber mirado nada**. Confirmado en la fuente.

**La frontera no es ese helper: es «un fallo de git se lee como un resultado vacío».** Recorridas las 26 llamadas a `git` del repo (`tests/`, `scripts/`, `core/`), estas son las que la cruzan:

| Sitio | Qué hace hoy si `git` falla |
|---|---|
| `tests/test_docs_gobernanza.py::_md_trackeados` (`git ls-files *.md`) | los guards G2, G7, G8… pasan sin mirar nada |
| `tests/test_docs_gobernanza.py::test_sin_refs_a_docs_plan_legacy` (`git grep`) | pasa: lee el fallo como «sin coincidencias» |
| `tests/test_guard_no_basetemp_versionado.py::_trackeados` (`git ls-files`) | pasa sin mirar nada |
| `tests/test_gitignore_no_inerte.py::_regla` (`check-ignore -v`) | lee «sin regla» |
| **`.github/workflows/leak-scan.yml`** (`git ls-files -z \| xargs -0 -r …`, sin `pipefail`) | **el escaneo de PII de CI sale verde sin escanear**: el código de la tubería es el de `xargs` |
| `scripts/session_close.py::_git_lines` → `_anon_tocado` y los avisos | la verja **se salta los tests lentos** y los avisos dicen «nada que avisar» |
| `tests/_mutantes_*.py` (cinco arneses, `git status --porcelain`) | el arnés cree que el árbol quedó limpio |

**Lo que ya estaba bien, comprobado:** `scripts/precommit_leak_guard.py::_git` (declara el principal «no determinado»), `core/codicert.py`, `core/email_atomize/entregas.py` («desconocido»), `_ls_files` y el lote de `check-ignore` de `test_gitignore_no_inerte.py`, el `_git` de `test_precommit_leak_guard.py` (exige 0) y `test_plugin_desplegado.py` (sus llamadores exigen `is not None` y lista no vacía). **Fuera, declarado:** `scripts/check_skills.py`, en modo aviso y, dentro de `session_close`, cubierto por la sonda.

**Dos trampas de diseño, medidas antes de escribir:**
- **Algunos comandos usan el código de salida como respuesta.** `git grep` devuelve 1 sin coincidencias y `git check-ignore`, 1 si no está ignorado: «falla si no es 0» a ciegas rompería esos guards. El helper recibe los códigos válidos de cada comando.
- **En `session_close`, un fallo por rama es legítimo.** `_git_count` cuenta cero cuando el remoto de una rama ya no existe (`rev-list` da 128): si cada llamada lanzara, una sola rama así tumbaría el aviso de todas. Por eso allí el remedio es la sonda de «¿responde git aquí?», no hacer lanzar a cada llamada.

## 2. Tasks

### Task 1: `tests/_git.py` y los guards que lo usan
- [ ] Tests primero (`tests/test_guard_git_falla_en_voz_alta.py`): el helper para con el stderr si el código no es válido, admite los códigos que se le dan, para si `git` no existe; `_md_trackeados`, las referencias heredadas, `_trackeados` y `_regla` paran con un `git` que falla, y devuelven algo con el `git` real (control positivo).
- [ ] Implementar el helper y migrar `test_docs_gobernanza.py` (dos sitios) y `test_guard_no_basetemp_versionado.py`; `_regla` valida su código como ya hacen sus hermanas del mismo fichero.

### Task 2: `session_close`, la sonda
- [ ] Tests primero: con la sonda en fallo, el modo de la verja es COMPLETO y dice por qué; los avisos que dependen de `git` salen como «no comprobado»; con `git` sano, nada cambia.
- [ ] Implementar `_git_responde()`, el modo de la verja y el envoltorio de los avisos.

### Task 3: CI, `pipefail`
- [ ] Test primero: el paso de `leak-scan` corre con `set -o pipefail` antes de la tubería.
- [ ] Implementarlo.

### Task 4: los arneses
- [ ] `check=True` en el `git status --porcelain` de los cinco arneses (herramientas, no tests: sin test propio).

### Task 5: verificación y revisión
- [ ] Suite con las dos semillas; mutantes de cada remedio.
- [ ] R1 de Codex sobre el diff: una ronda; **`gpt-6-astra` · `medium`**, fila «gobernanza que pueda hacer que la cobertura parezca presente estando ausente: un guard». Adjudicación embebida aquí; acta hermana `…-git-que-falla-en-voz-alta-r1-adversarial-review.md`.
