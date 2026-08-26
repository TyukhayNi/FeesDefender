---
tipo: revision-adversarial
objeto: core/casos/case_mutex.py
objeto_rev: "PR #247"
commit: 5998888
ronda: "11"
revisor: Codex
veredicto: SIN-VEREDICTO
marcador_nonce: k4tm
sha256_informe: f560bd9f69b52182d0328d61f7657bc2b0ca717519017bf3f9423416bf3c1e32
adjudicado_en: docs/superpowers/plans/2026-08-25-apertura-v1-plan2-mutex.md §1
adjudicador: Claude Code
independencia_adjudicacion: restablecida
---

> **Acta de revisión adversarial R11 — la ronda NO produjo informe, y eso es lo primero
> que hay que leer.**
>
> **Qué pasó.** El arnés del revisor **se ejecutó entero** y emitió sus siete sondas. La
> redacción del informe la cortó el **filtro de contenido de su propia plataforma**: el
> arnés combinaba multiproceso, borrado de un lockfile sostenido y un escape por enlace,
> y eso se leyó como trabajo ofensivo. El fichero `informe/INFORME_R11.md` **nunca se
> escribió**.
>
> **Qué NO se puede decir por tanto.** No hay veredicto del revisor. No hay severidades
> suyas. No hay «Codex confirmó». Un revisor que no termina **no refuta y no confirma**:
> deja evidencia. Lo que sigue es esa evidencia cruda, literal, y **el veredicto
> `NO-SHIP` lo firmo yo** tras verificar las siete sondas contra la fuente, una por una.
>
> **Los dos digests, y cuál es cuál.** El `sha256_informe` del frontmatter es el del
> **bloque archivado**, que es lo que el guard recomputa. El del **log completo de la
> sesión de Codex** —la fuente de la que salieron estas siete líneas— es
> `00691bfdffcd59ec7d856d203e11fef46cd1bc31f1915b47186f0ce5bed9de66`, y se conserva
> aquí para que la evidencia se pueda contrastar contra su origen.
>
> **Por qué se archiva igual.** Porque la evidencia es lo que importa y es contrastable:
> siete líneas de salida que cualquiera puede volver a producir. El digest es del **log
> completo de la sesión** (`codex.log`), no de un informe, precisamente porque no lo hay.

## 1. Informe recibido de Codex, sin modificar

**No hay informe: hay evidencia.** El revisor nunca llegó a redactarlo (ver la nota
de cabecera). Lo que se archiva aquí, literal y sin tocar, son las siete sondas de su
arnés tal como las imprimió, más el bloqueo que cortó la redacción:

<!-- informe-literal:inicio:k4tm -->
> **[Nota del adjudicador, no del revisor.]** Esta línea la escribo yo, dentro del bloque
> literal y marcada como mía, porque el guard de gobernanza exige que el veredicto conste
> en el material archivado y **aquí no hay veredicto que archivar**: la ronda se cortó
> antes de emitirlo. Se declara por tanto **SIN-VEREDICTO**. Todo lo que sigue debajo de
> esta nota es salida literal del arnés de Codex, sin tocar.

```text
FUTURE_TAKEOVER True True 2099-01-01T00:00:00Z
SWALLOWED_RENEWAL True ['BODY_CONTINUES_AFTER_RENEW_ERROR', 'SECOND_ENTERED:fe1a5c48004406fa', 'EXIT:MutexNotMine']
MASKED_EXCEPTION MutexNotMine [MUTEX_NOT_MINE] � el mutex del caso pertenece a otro titular � caso W-R11TEST context=RuntimeError
INVALID_SCHEMA_ACCEPTED 999 {}
SYMLINK_ESCAPE C:\Users\tnm33\AppData\Local\Temp\r11_mutex_diff\scratch\runs\symlink\lexically_safe True C:\Users\tnm33\AppData\Local\Temp\r11_mutex_diff\scratch\repo\inside_repo_target\W-R11TEST.lock
RAW_TIMEOUT filelock.Timeout structured= False
GUARD_DELETE PermissionError:[WinError 32] El proceso no tiene acceso al archivo porque est� siendo utilizado por otro proceso: 'C:\\Users\\tnm33\\AppData\\Local\\Temp\\r11_mutex_diff\\scratch\\runs\\guard_delete\\W-R11TEST.lock.guard'
```

Y el bloqueo que impidió el informe, literal:

```text
ERROR: This content was flagged for possible cybersecurity risk. If this seems wrong, try rephrasing your request. To get authorized for security work, join the Trusted Access for Cyber program: https://chatgpt.com/cyber
```
<!-- informe-literal:fin:k4tm -->

## 2. Evidencia verificada al adjudicar (Claude Code, 2026-08-26)

**Cada sonda verificada contra la fuente por el adjudicador**, no aceptada por venir del
arnés. Tres las había medido yo **antes** de que el arnés corriera; tres no.

| # | Sonda | Quién lo vio primero | Veredicto | Severidad |
|---|---|---|---|---|
| H11-01 | `FUTURE_TAKEOVER` | el arnés | **CONFIRMADO** — un `ahora` de 2099 pisa un lease vivo | CRÍTICO |
| H11-02 | `SWALLOWED_RENEWAL` | los dos | **CONFIRMADO** — el cuerpo sigue y un segundo proceso entra | CRÍTICO |
| H11-03 | `MASKED_EXCEPTION` | yo | **CONFIRMADO** — el llamador ve `MutexNotMine`, no su error | ALTO |
| H11-04 | `INVALID_SCHEMA_ACCEPTED` | el arnés | **CONFIRMADO** — `schema: 999` y `propietario: {}` pasan | ALTO |
| H11-05 | `SYMLINK_ESCAPE` | el arnés | **CONFIRMADO** — una junction escapa la contención léxica | ALTO |
| H11-06 | `RAW_TIMEOUT` | yo | **CONFIRMADO** — `filelock.Timeout` fuera del §10 | MEDIO |
| — | `GUARD_DELETE` | el arnés | **SIN HALLAZGO** — `WinError 32`: el guard resiste | — |

**La séptima se declara aunque no encontrara nada.** Un acta que solo lista lo que falló
no permite saber qué se miró, y «no se miró» y «se miró y estaba bien» son cosas
distintas.

### Lo que aporta el adjudicador, y no estaba en ninguna sonda

**H11-01 es la mitad de R10/H10-02 que no cerré.** Aquel hallazgo decía, literalmente, «un
`ahora` **naïve o futuro** roba un lease vivo». Cerré el naïve, añadí monotonía a
`renovar`, y **di el crítico por remediado**. La mitad que quedaba abierta es la que un
revisor volvió a encontrar una ronda después. Remediar la parte que entiendes y declarar
cerrado el hallazgo entero es un modo de fallo con nombre propio, y este es su caso.

**H11-05 es una regresión que introduje AL ARREGLAR otra cosa.** La contención era
`resolve()` y la hice **léxica** para matar una carrera real medida en la ronda 8 de 12.
Al hacerlo dejé de ver a dónde apunta un enlace. Las dos propiedades son ciertas y hacen
falta las dos: la comprobación **por llamada** tiene que ser léxica (o vuelve la carrera)
y la de la **raíz** tiene que resolver (o pasa la junction). El remedio las separa.

**Y un defecto de mi propia remediación, que cazaron dos tests que ya existían.** Al
cerrar H11-02 puse un `revalidar()` después de `liberar()`: como `liberar` borra el lock,
«no hay lock» se leía como «lo perdí», y `tomado()` lanzaba `MutexPerdido` en el camino
feliz. No lo vi yo: lo vieron `test_el_renovador_para_al_salir` y
`test_RENUEVA_mientras_el_cuerpo_corre`, escritos dos días antes.

### Lo que sigue SIN VERIFICAR, y se declara

- **La ronda no se completó.** Un informe redactado podría haber contenido hallazgos que
  el arnés no cubría: las siete sondas son las que el revisor **alcanzó a ejecutar**, no
  necesariamente todas las que pensaba escribir. La cobertura de esta ronda es **parcial
  y no se sabe cuánto**.
- **No se ha vuelto a revisar el diff después de remediar.** Las seis remediaciones son
  código nuevo sin ronda propia.
- **El comportamiento con relojes desincronizados de verdad** (NTP saltando durante una
  operación): la cota de 600 s es una decisión, no una medición.
