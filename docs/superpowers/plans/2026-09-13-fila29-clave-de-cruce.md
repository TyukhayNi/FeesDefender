---
tipo: plan
estado: vigente
creado: 2026-09-13
rev: 1
---

# Fila #29 — el rescate de las 838 líneas, y por qué salió por otro sitio (`MEJORAS #251`, `#252`)

## 1. El encargo era subir un módulo; lo que había que arreglar era otra cosa

La fila #29 decía: rebasar sobre `main` las **838 líneas** de `core/intake_drive_hash.py`
—la vía (a) de `MEJORAS #225`, escritas el 2026-09-10 y nunca commiteadas— resolver su
colisión con el PR #358 y abrir PR.

Al leerlas resultó que **hacen lo mismo** que `verificar_apertura` C1 y C2 (censo remoto +
`sha256` contra Drive), construidas un día después por otra vía: rclone en un caso, la API
de Drive en el otro. Subir el módulo habría dejado **dos verificadores del mismo hecho**
que pueden discrepar entre sí, y habría metido red en el camino del pull — justo lo que el
§3.4 del handoff de la fila #27 decidió no hacer.

**Pero traían una medición que C1/C2 no tenía.** Y al comprobarla contra la fuente, C1/C2
salieron rotos.

## 2. Lo que se midió

Sonda del 2026-09-13: el mismo documento, declarado por Drive con la `Á` **descompuesta**
(NFD) y guardado en `G:` **precompuesta** (NFC).

| | Antes | Debería |
|---|---|---|
| **C1** | `fallo`: «1 fichero del remoto que no está en local y 1 en local que no está en el remoto» — **con las dos rutas imprimiéndose idénticas** | `ok` |
| **C2** | `pendiente`: «ninguno de los 1 ficheros locales tiene hash en Drive con el que contrastar» | contrastar 1 de 1 |

**Lo de C2 es lo caro.** No decía «no cuadra»: decía **no puedo**, con un motivo que suena
a limitación del remoto. El hash estaba ahí. El fichero **dejó de verificarse en silencio**,
sobre la pieza cuyo único trabajo es acreditar custodia.

El hallazgo original es del módulo huérfano, sobre **W-02V48N**, donde el falso hallazgo
**tapaba una discrepancia real de +326 bytes**.

**Y la instrucción ya estaba escrita.** `RUNBOOK_APERTURA_EXPEDIENTE.md` `[APER-65]`, del
2026-09-10, manda al operador que hace el censo a mano: «normaliza a **NFC** antes de
comparar, o un topónimo acentuado da falsos positivos». C1 se construyó **al día siguiente**
para automatizar ese mismo censo, y no la aplicó.

## 3. Qué se construyó

- **`clave_de_cruce`**: NFC, **y nada más**. La normalización Unicode es segura —NFC y NFD
  son dos escrituras del mismo texto, así que unificarlas no puede fundir dos ficheros
  distintos—. El encoding de rclone **no lo es**, y por eso no se deshace: ver §5.
- **`tiene_marcas_de_encoding`**: reconoce, no traduce. Un descuadre entre nombres que
  pasaron por el `--local-encoding` sale **explicado**, para que el operador no persiga un
  fantasma ni borre un «sobrante» que es el mismo documento.
- **Colisiones de clave**, en C1 **y** en C2: dos ficheros del remoto que colapsan a la
  misma clave no se funden en silencio.
- **`_es_el_relleno_de_225`**: C2 pasa de sospechar a **probar**. El módulo huérfano solo
  podía decir «compatible con el relleno» (tamaño múltiplo de 512) porque la otra mitad de
  la firma «exige abrir el fichero»; C2 ya lo abre, así que rehashea sin la cola de ceros y,
  si cuadra con el `sha256` de Drive, está demostrado.
- **`MEJORAS #252`**: V1 corre la verificación al terminar. Fuera del mutex, sin tocar el
  código de salida, y si revienta lo dice y sigue.

## 4. Qué NO se rescató, y por qué

- **La función pura `comparar`** del módulo huérfano: no tiene consumidor una vez decidido
  que no hay un segundo verificador. Sería una pieza que nadie encadena.
- **Verificar dentro del pull**: duplicaría C1/C2 y metería dos `rclone lsjson` en cada
  ronda de V1 —uno de ellos hashea todo el destino, que en `G:` puede forzar la hidratación
  del árbol entero—.
- **Las 838 líneas se conservan** en el tag `wip/via-a-225-2026-09-10` (`776d531`), sin
  mergear: es el original auditable, y permite contrastar que lo entregado sale de ahí.

## 5. Adjudicación de la revisión adversarial (Codex, 2026-09-13) — NO-SHIP, remediado

- **Objeto revisado:** `docs/superpowers/plans/2026-09-13-fila29-clave-de-cruce.md` rev. 1, commit `78afc7a`
- **Ronda:** 1
- **Revisor:** Codex (solo lectura)
- **Informe recibido:** `2026-09-13-fila29-r1-adversarial-review.md`
- **Hallazgos:** 8 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** PR #360 (`78afc7a` + la remediación)

**Una ronda que cambió el diseño, no solo el código.** Los dos `ALTO` dicen que el primer
remedio era **inseguro**: una tabla plana que deshacía el `--local-encoding` con
`str.translate`. Dos razones independientes, y las dos se verificaron ejecutando:

1. **Las reglas de rclone son posicionales y `translate` no** (H-01). `LeftSpace` y
   `RightSpace` codifican el espacio **al principio o al final** del segmento. Un remoto
   `a b.txt` y un local `a␠b.txt` —que rclone nunca habría escrito— se cruzaban como el
   mismo fichero y C1/C2 daban `ok`: **aceptar como presente un objeto de identidad
   distinta**.
2. **La clase no se cierra con una tabla** (H-02). El `--local-encoding` real activa también
   `SquareBracket`, `Ctl` e `InvalidUtf8`, y rclone tiene un **escape** (`‛`). Yo afirmé
   «cerrar la clase» habiéndola cerrado **por ejemplos**.

**El intercambio que hice era el prohibido:** cambiar falsos descuadres —que gritan— por
falsos cruces —que callan—. Esta red **falla cerrado**. La tabla se retiró entera; lo que
queda es NFC (seguro) más una **declaración** de las marcas.

Los otros seis, con su remedio, en la tabla del §2 del acta. **Tres son reincidencias de
fronteras cerradas horas antes en la pieza A de la fila #27**, y esa es la lección de la
ronda: H-04 («remediar el ejemplo, no la frontera» — detecté las colisiones en C1 y no en
C2), H-05 (la carrera de `MEJORAS #214`, dentro del remedio que la persigue) y H-07/U1
(`A19`: el test prueba el helper, no su cableado).

**Dos mutaciones del revisor sobrevivían** a los 11 mutantes del autor; hoy son `M17` y
`M18` del arnés. Tras remediar: **18 mutantes, 18 muertos**, más un **superviviente
declarado** al que **no se le atribuye garantía** —`len(cola) != tam - seguro`, cuya caso
discriminante no supe construir— y una guarda **retirada por inerte**, el
`p.stat().st_size != tam` final que el arnés mostró incapaz de morder.

## 6. Lo que queda SIN VERIFICAR

- **Deshacer de verdad el encoding de rclone.** Haría falta reimplementar su decodificador
  posicional con escape; un descuadre por `SquareBracket`, `Ctl` o `／` **sigue saliendo
  como descuadre**, ahora explicado. No se intenta a medias: hacerlo a medias es H-01.
- **Que la verificación encadenada corra de verdad en una apertura real.** El guard AST
  acredita que el cableado existe, no que se ejecute.
