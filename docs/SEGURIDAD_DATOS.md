---
titulo: Seguridad de datos — prevención de fugas de PII y secretos
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-07
---

# Seguridad de datos — FeesDefender

> **Hogar canónico** de cómo el proyecto evita fugas de datos personales (PII) y
> secretos. Doctrina + controles + runbook de incidente. No redescribe la
> arquitectura ni la gobernanza: **enlaza**. Cableado en el mapa SSOT
> (`ARQUITECTURA_RELACIONES.md`), indexado en `docs/INDICE.md`, invariantes duros
> en `CLAUDE.md §Reglas que nunca se rompen`, implementación en `PLAN.md`.

## Principio rector

**Cuanto antes y más automática es la barrera, más barata.** El coste de parar una
fuga crece por órdenes de magnitud según dónde la pilles:

> `pre-commit` (segundos) ≪ CI en servidor (minutos) ≪ reescribir historial + recrear repo (una sesión entera)

La última la vivimos el 2026-07-06/07 (Fase 2 del saneado). Toda la estrategia es
empujar la detección **a la izquierda**: al momento del `commit`, no al del desastre.

---

## Los principios (por capas de defensa)

*Defense in depth: si una barrera falla, otra lo para.*

### A. Mantener el dato real FUERA del repo (prevención en origen)

1. **Separación dato/código.** El código va al repo; el dato real (expedientes, PII,
   credenciales) vive fuera: `data/CASOS/`, `.env`, Drive. El repo nunca es el sitio
   donde reposa información sensible. *(Es la frontera arquitectónica de
   `ARQUITECTURA_RELACIONES.md §1`: `UI → Core → data/CASOS/` gitignored — aquí leída
   como frontera de fugas.)*
2. **Las capturas de depuración son radiactivas por defecto.** HAR, volcados de red,
   dumps de auditoría, exports de CRM traen secretos y PII dentro. Fue la fuga de este
   proyecto (HAR de 22 MB en el commit inicial). Nunca se commitean.
3. **Los tests corren sobre datos SINTÉTICOS, nunca reales.** Nombres/emails reales en
   fixtures son una fuga que viaja en cada clon. Pasó (nombres reales en `tests/core`
   de los atomizadores).
4. **Mínimo privilegio y vida corta para los secretos.** Se inyectan por entorno, con
   el menor alcance y caducidad posibles. Si uno se filtra, se rota — no se debate.
   *(La vida corta salvó el incidente: los tokens del HAR ya estaban caducados.)*

### B. Barreras automáticas (la disciplina humana NO es un control)

5. **Lo que no impone la máquina, no es un control.** El incidente ocurrió por confiar
   en "acordarse de no commitear". Un control de verdad actúa aunque el humano se
   despiste → `pre-commit`.
6. **Doble barrera: local Y servidor.** Un `pre-commit` local se salta con
   `git commit --no-verify`. Hace falta una segunda comprobación en servidor que nadie
   pueda saltar → CI (GitHub Actions) que bloquee el push/merge.

### C. Higiene al escribir (para lo que sí es texto legítimo)

7. **Referenciar, no reproducir.** En docs, bitácora y mensajes de commit: personas y
   casos **por código interno** (`W-XXXXX`), jamás por nombre, email o dirección de
   tercero. *(Esta regla tenía su hogar en `GOBERNANZA §4`; ahora vive aquí y §4
   apunta.)*
8. **Si hay que nombrar, pseudónimo reversible con el mapa fuera del repo.** Cuando el
   trabajo exige identidades (p. ej. tests de atribución de correos), pseudónimos
   estables e inyectivos con mapa reversible gitignored. *(Patrón `data/_saneado/mapa_pii.json`.)*

### D. Mentalidad y respuesta (el coste es asimétrico)

9. **Un commit es, en la práctica, permanente y público.** Llega a clones, forks,
   `refs/pull/*` y cachés. Sacarlo cuesta lo que costó la Fase 2. El repo privado es una
   red de seguridad, no un permiso para relajar la higiene.
10. **Respuesta a incidentes ensayada (runbook).** Ver abajo. Documentarla la convierte
    en control.

---

## Doctrina → mecanismo → fichero (lo que la hace control, no norma)

| Principio | Mecanismo | Fichero / lugar | Estado |
|---|---|---|---|
| 1 dato/código | `.gitignore` (frontera dura) + frontera de capas | `.gitignore`, `ARQUITECTURA_RELACIONES.md §1` | vigente |
| 2 capturas radiactivas | gitignore de rutas de captura + límite de tamaño de blob | `.gitignore` (`*.har`, `docs/_descubrimiento/`, `data/_audit/`); `check-added-large-files` (maxkb=2048) | **vigente** |
| 3 fixtures sintéticas | fixtures inventadas (ya pseudonimizadas en Fase 1) + test-guard que falla ante PII en `tests/`+`core/` | `tests/test_no_pii_en_tests.py` (reutiliza `escanear`) | **vigente** |
| 4 secretos mínimos/efímeros | inyección por entorno + rotación documentada | `.env` (gitignored), este doc §Runbook | vigente |
| 5 barrera automática | `pre-commit` (gitleaks + `check-added-large-files` + `leak-guard`) en `pre-commit` y `pre-push` | `.pre-commit-config.yaml`, `scripts/precommit_leak_guard.py` (+ test) | **vigente** |
| 6 doble barrera | CI de escaneo de fugas + gate de merge en `main` | `.github/workflows/leak-scan.yml` + branch protection (check `leak-scan` obligatorio, PR requerido, `enforce_admins`) | **vigente** (prevención server-side activa desde 2026-07-07, Pro) |
| 7 referenciar por código | escaneo de nombres/emails de tercero en el contenido (blocklist gitignored) | `leak-guard` (`escanear`) en pre-commit + CI (con secret `PII_BLOCKLIST`) | **vigente** (CI exige el secret: el job `leak-scan` falla si no está definido) |
| 7-bis PII por forma (cualquier caso) | detección por PATRÓN, no por valor: DNI/NIE/IBAN bloquean, email de tercero avisa; reutiliza `core/anon` | `leak-guard` (`escanear_formas`) en pre-commit + CI | **vigente** (independiente de la blocklist) |
| 8 pseudónimo reversible | mapa inyectivo fuera del árbol | `data/_saneado/mapa_pii.json` (gitignored) | vigente (patrón) |

> **Blocklist (por valor) vs. shape-detection (por forma).** La blocklist es una
> *denylist*: solo caza PII ya enumerada (la que pasó por el anonimizador). No cubre
> un caso nuevo cuyos nombres/emails nadie ha listado. El *shape-detection*
> (`escanear_formas`) cierra ese hueco para los **identificadores estructurados**
> (DNI/NIE/IBAN) de cualquier expediente, sin depender de lista alguna. Para
> **nombres y direcciones** de casos nuevos no hay detector barato por forma; ahí la
> defensa sigue siendo el principio 1 (el dato de caso no entra al repo). El
> shape-detection se salta zonas curadas con ejemplos sintéticos (`tests/`, `docs/`,
> `.claude/`, `*.example`) y admite la anotación de línea `leak-guard:allow` para
> valores sintéticos legítimos; el NIF/CIF queda fuera por ser dato público de
> registro (p. ej. el CIF de la clienta en `core/config`).
>
> **Punto ciego conocido (binarios).** El escaneo de contenido (por valor y por forma)
> solo mira ficheros de texto: PDF/DOCX/XLSX/imágenes se omiten (tienen `\x00`). Un
> documento binario con PII en una ruta NO vetada no se inspecciona por contenido; su
> red es la ruta vetada + el límite de tamaño. Extraer texto de binarios en el hook
> queda como mejora futura (coste alto, valor incremental bajo).

> La **implementación de los pendientes** es un punto de `PLAN.md` (disparador
> concreto: el incidente de la Fase 2), por la regla de promoción backlog→cola.

---

## Runbook de incidente (cuando algo se filtra)

1. **Rotar** de inmediato cualquier secreto expuesto (no evaluar primero: rotar).
2. **Evaluar exposición**: ¿repo público o privado? ¿desde cuándo? ¿qué blobs/refs?
3. **Si hay PII/secretos persistentes en el historial**: reescribir con
   `git filter-repo` sobre un **clon `--mirror` aparte** (nunca la worktree; backup
   íntegro primero). Si el force-push de `main` no basta —porque `refs/pull/*` y otras
   ramas siguen anclando los objetos viejos—, **borrar y recrear el repo** y re-empujar
   solo las ramas limpias.
4. **Purgar el local**: `reset --hard` de las worktrees a los SHAs nuevos +
   `reflog expire --expire=now --all` + `gc --prune=now`.
5. **Avisar de re-clonado** a todo clon/Cowork (los SHAs cambian; `pull`/`fetch` no
   reconcilian sin ancestro común).

*Ejecutado el 2026-07-06/07 (Fase 2 del saneado de PII): purga del HAR + `data/_audit/`
del historial, sustitución de PII por pseudónimos, repo recreado. Detalle en
`PLAN.md [SANEADO-PII-FASE-2]` y memoria `project-saneado-pii-repo`.*

---

## Reconciliación con `GOBERNANZA §2` (dónde va el enforcement)

`GOBERNANZA_FUENTES_VERDAD.md §2` recomienda enganchar la automatización en
`scripts/session_close`, no en un linter/CI aparte. **Para el drift de gobernanza es
correcto; para las fugas, no.** `session_close` corre al *cerrar* la sesión, pero el
hook `post-commit` **ya ha auto-pusheado cada commit a GitHub**: cuando `session_close`
mira, el secreto ya es público. Por eso el control de fugas vive en `pre-commit` (antes
de que exista el blob) + CI en servidor (no saltable con `--no-verify`). No contradice
§2: es **otro modelo de amenaza** — el drift se recupera; una fuga no.
