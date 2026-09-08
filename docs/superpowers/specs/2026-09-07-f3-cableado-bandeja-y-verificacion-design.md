---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-07
revision: v1
topic: F3 — cablear el archivado a la bandeja, y verificar por el lado del expediente
relacionado:
  - docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md (rev. 5 — el cliente REST y el contrato medido)
  - docs/superpowers/specs/2026-07-19-intake-miniapp-entrega-design.md (entrega; su §2 y §5 quedan afectadas, ver §10)
  - docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md (§6 bandeja, §15 F3, §18.9 la terna)
  - docs/MEJORAS_FUTURAS.md (#176, #177, #178, #179)
---

# Diseño — F3: cablear el archivado a la bandeja, y verificar por el lado del expediente

> Cierra `MEJORAS #176` y `#177`, y encadena la pieza que F3 dejó construida y sin llamador.
> **No** construye el paso del webmail (pieza (b) del `[SIGUIENTE]` de `PLAN.md`), ni F4
> (renombrado por contenido), ni el estado compartido entre apps.

## 1. El problema, en dos frases

**`core/procurador_relate.py` existe, está validado en vivo, y nadie lo llama.** `git grep
procurador_relate` devuelve solo su propio test; la bandeja sigue diciendo *«Dry-run: confirmar
registra la decision (terna §18.9); NO escribe en el CRM (eso es F3)»*
(`streamlit_app.py:2699`). Y cuando se le llame, **verifica desde el lado equivocado**: relee
`findRelations(uid, account)`, que es una vista **por copia**, mientras la relación que escribe es
**global** — medido el 2026-09-07, produce `ok=False` sobre una escritura correcta (F3 rev. 5 §4.1).

Esta pieza hace dos cosas, en este orden: **arregla la verificación** y **encadena el archivado**.

## 2. El modelo real del correo, corregido por Nikolai el 2026-09-07

Esto no es contexto: gobierna el diseño, y yo lo tenía mal.

- **`procesal@` NO está configurado en Roundcube.** Es una lista que **reenvía** a cuatro buzones
  personales —Ana, Sergio, Nikolai, Paola—, y **son esos cuatro los configurados en el CRM**.
- **Cada persona relaciona desde SU Roundcube, y al hacerlo crea SU fila `mail`.** De ahí que un
  mismo Message-ID tenga N filas: **N no es un misterio del enrutado, es cuánta gente archivó ese
  correo.** *(Esto retira el §8.8 de F3 rev. 5, que lo declaraba «causa no medida».)*
- **La cuenta es el buzón de quien relaciona**, y se confirma con datos de este repo: las 23 filas
  de `cuenta 20` las creó `id_creador=23` (Ana); las de `cuenta 15`, `id_creador=2` (Nikolai).
  **Cuenta 20 = el buzón de Ana.**
- **Medido el 2026-09-07 sobre 3.710 Message-ID** (4.000 filas ordenadas por `uid`, bordes de la
  muestra descartados): **6,3 % tiene más de una copia** — 203 con dos, 17 con tres, 15 con cuatro.
  Los pares observados son `['15','20']` y `['20','3']`. **Re-ejecutable:**
  `python -m scripts.sondeo_copias_mail --paginas 8`, que lo reprodujo el 2026-09-08 (234/3.712).
  ⚠️ **Con muestra corta el mismo sondeo devuelve 0 %** (2 páginas), y por eso imprime un control
  que lo declara: ese cero no es evidencia.

### 2.1 El límite que de aquí se deriva, y es el importante

> **F3 no puede crear la copia de quien lo usa. Solo su Roundcube puede.**

F3 escribe sobre una fila que **ya existe** y `resolver_cuenta` la lee. Si Paola usa la miniapp,
F3 escribiría sobre la copia que haya —hoy la de Ana—, no sobre la de Paola, que no existe hasta
que Paola la cree desde su webmail. **No es un detalle de implementación: es cómo entra un correo
en la tabla `mail`.**

## 3. Decisiones de Nikolai (2026-09-07)

| # | Decisión |
|---|---|
| D1 | **Un clic**: «Confirmar» archiva. Con **interruptor global** por variable de entorno, y **ausente ⇒ dry-run** |
| D2 | Un correo no indexado **bloquea el botón**, y la tarjeta dice que falta el paso del webmail |
| D3 | Los adjuntos se suben con su **nombre ORIGINAL**. Renombrar es de F4 |
| D4 | **Escritura solo en la máquina de Ana** (más la de Nikolai para probar). Paola y Sergio, dry-run |
| D5 | Alcance **judicial-first** — honra la decisión del 2026-07-19 (entrega §9) |
| D6 | Si el usuario no es dueño de una copia, **se escribe sobre la copia que haya**; nuestro log registra quién clicó |
| D7 | **La visibilidad tiene DOS superficies** y las dos afirmaciones del expediente documental eran ciertas (§5.1, explicado por Nikolai el 2026-09-07). Ninguna rama del diseño cuelga de ella |

**D4 gana una razón mejor que la concurrencia con el §2.1 delante:** la copia que existe es la de
Ana, así que la app que escribe debe ser la de Ana. Hoy es la única configuración coherente, no una
mitigación provisional. Se levanta poniendo la variable a quien la cubra.

## 4. Arquitectura

La regla del repo decide la forma: **la lógica va al core, Streamlit solo orquesta.** El botón no
llama a `archivar()`.

```
core/procurador_archivo.py          (NUEVO — orquestación con política)

  archivar_confirmado(item, action, *, quien, escritura_viva, cuenta_propia, cliente=None)
      -> ResultadoArchivo

  1. destino = destino_efectivo(prop, action)            # (elemento, id) o None
  2. destino is None                       -> revisión, sin red
  3. elemento != expedientes_judiciales    -> bloqueado (D5), sin red
  4. not escritura_viva                    -> dry-run: registra y sale
  5. cuenta = elegir_cuenta(message_id, cuenta_propia)   # §5
  6. relate.archivar(..., adjuntos=[(n, n) for n in originales], account=cuenta)   # D3
  7. verificación por el lado del EXPEDIENTE             # §6
  8. record_decision(prop, action, quien=quien, resultado=...)   # traza §7
  9. transicionar(item, "confirmar" | "revisar") -> upsert_queue_item
```

**Fichero nuevo, no dentro de `procurador_relate.py`.** Ese módulo es el cliente REST (505 líneas);
esto es orquestación con política —el interruptor, la elección de copia, la traza, la cola—. Se
prueban distinto: el cliente con transporte falso, el orquestador con **cliente** falso.

**El interruptor** es `PROCURADOR_ESCRITURA_CRM`, leído en `core/config.py` como el resto.
**Ausente, vacío, o cualquier valor que no sea `1`/`true` ⇒ dry-run.** No es un control de la UI: un
fallo de dedo no puede activarlo y Paola y Sergio no lo ven. La bandeja **muestra el modo**, para
que nadie crea que archivó cuando no.

## 5. Qué copia se escribe (§2 + D6)

`PROCURADOR_CUENTA_CRM` declara la cuenta del buzón de quien corre la app (20 en la de Ana). Es
**configuración, no inferencia**: el endpoint que mapearía cuenta↔persona (`/api/accounts/{id}`)
devuelve **credenciales IMAP en texto plano** (`INTEGRACION §10.9`) y no se llama.

```
elegir_cuenta(message_id, cuenta_propia):
    copias = cuentas con fila `mail` para este Message-ID
    0 copias                     -> sin_registro      (falta el webmail; D2)
    cuenta_propia ∈ copias       -> cuenta_propia     (por la TRAZA, no por visibilidad)
    si no                        -> la copia de menor cuenta, anotada en la traza
```

**No se falla cerrado en ninguna rama con copia**, y descansa solo en hechos medidos: la relación
es **global** y re-relacionar **no duplica**, así que escribir en cualquier copia consigue el
objetivo. La preferencia por la copia propia es para que la traza sea limpia, no una precaución de
permisos.

### 5.1 La visibilidad tiene dos superficies, y relacionar es el puente

**Explicado por Nikolai el 2026-09-07** (procedencia: el administrador del CRM, no una medición de
este repo — con `x-api-key`, que es una identidad de servicio, no se puede observar lo que ve una
persona):

| Superficie | Quién ve el correo |
|---|---|
| **Roundcube** | **solo el titular del buzón.** Un correo que llegó a la cuenta de Ana no lo ven Sergio, Nikolai ni Paola: nadie entra al Roundcube de otro |
| **A través del expediente** | **todo el equipo con acceso a ese expediente**, una vez el correo está relacionado con él |

Las dos afirmaciones que este repo tenía escritas y parecían contradecirse **eran ciertas a la
vez**, de superficies distintas. La del §8 de F3 —*«el correo hereda la visibilidad del buzón»*— lo
es **de Roundcube**; que el equipo lo vea al relacionarlo lo es **del expediente**. La frase de F3
solo fallaba en no decir de cuál hablaba.

**Y de aquí sale algo que no estaba escrito en ninguna parte, y es la mitad del valor de esta
pieza:** *relacionar no es solo archivar — es el acto que hace el correo visible al equipo.* Antes
de relacionarlo vive en un solo buzón; después, lo lee cualquiera con acceso al expediente.

**Consecuencia para el diseño: ninguna rama cuelga de esto.** Cualquier copia sirve, porque la
visibilidad de equipo la da la relación con el expediente y la relación es global. Por eso el §5 no
corta a revisión el 6,3 % multicopia: una versión anterior lo hacía «para no decidir a ciegas la
visibilidad», y esa precaución no protegía nada.

## 6. La verificación (`MEJORAS #176`)

### 6.1 Lo medido que gobierna

```
get_relaciones('expedientes_judiciales','683')['mail']  ->  [{'id':'439232'}, {'id':'464006'}]
```

1. **El bloque `mail` del expediente usa el MISMO espacio de ids que el `mail_id` del relate**
   (439232 es el correo archivado esa tarde) ⇒ `mail_id ∈ ids` es una comprobación exacta.
2. **Ese bloque solo trae `id`**, sin `uid`; y antes del relate no se conoce el `mail_id`.

### 6.2 De ahí la forma, y el arreglo va DENTRO de `relacionar()`

- **La comprobación POSTERIOR es la autoritativa**, por `get_relaciones(elemento, miembro)['mail']`.
  Es la que fija `verificado`.
- **La PREVIA se degrada de guarda a atajo.** Sigue leyendo `findRelations` por copia, pero un
  negativo significa «no consta en esta copia», no «no está», y se procede. Es admisible **porque
  está medido** que re-relacionar no duplica. `ya_estaba` pasa a ser una pista, y **nada cuelga de
  él** salvo el atajo.
- **El arreglo vive en `relacionar()`, no en el orquestador.** La verificación equivocada está ahí;
  parchearla solo en el llamador deja el defecto para el siguiente que la use. Es el patrón «la
  guarda está en el envoltorio y el otro llamador la rodea», que en este repo ya ha costado tres
  veces.

### 6.3 Los dos mensajes falsos se arreglan aquí (`MEJORAS #177`)

- `resolver_cuenta()` deja de decir *«¿no indexado todavía?»* cuando hay N copias: distingue
  `sin_registro` de `varias_cuentas`, y los nombra.
- El relate deja de sugerir *«¿existe el miembro?»* cuando el miembro existe y la relación está
  escrita.

Los dos fallan **cerrado** hoy: esto no corrige corrupción, corrige un diagnóstico que manda a la
persona a buscar donde no está.

## 7. La traza (plan §18.9, F3 §6)

`record_decision` se extiende con `{ok, verificado, mail_id, elemento, miembro, cuenta_usada,
cuenta_propia, folder_id, adjuntos_subidos, ya_presentes, motivo, error}` y el estado
`archivado_en_crm`.

**`ok`, `verificado` y «la relación quedó escrita» son TRES hechos distintos, y se guardan por
separado.** Colapsarlos en un booleano es lo que produjo el falso negativo del 2026-09-07. F6 tiene
que poder distinguir «no escribí», «escribí y no lo confirmé» y «escribí y lo confirmé». Y
`cuenta_usada` frente a `cuenta_propia` deja por escrito cuándo se escribió sobre copia ajena (D6).

## 8. Errores — la tabla completa

| Situación | Escribe | Estado | Qué ve Ana |
|---|---|---|---|
| destino sin elemento | no | revisión | el motivo, botón bloqueado |
| elemento no judicial (D5) | no | bloqueado | «judicial-first» |
| `sin_registro` | no | revisión | «falta relacionarlo desde el webmail» (D2) |
| copia ajena, una o varias (§5) | **sí** | confirmado | archivado, con la copia usada anotada |
| interruptor apagado | no | confirmado (dry-run) | «registrado, sin escribir» + el modo, visible |
| relate 200 y el expediente no lo ve | — | revisión | `verificado=False`, con el motivo real |
| relate ok · adjunto falla | **sí, la relación** | revisión | `ok=False` **y** la relación registrada |
| censo del gestor ilegible | indeterminado | revisión | «no se pudo comprobar; no reintentes sin mirar» |
| adjunto ya en el censo | no re-sube | confirmado | «ya estaba» |

El penúltimo importa: **censo ilegible no es fallo**, porque un fallo invita a reintentar y
reintentar **duplica** (F3 §8.2, medido).

## 9. Los adjuntos (D3)

Se suben con el nombre original: `[(nombre, nombre)]`. Tres razones, y la segunda no es estética:

1. F4 —quien compone el nombre— **no está construido**, y `propose_attachment_name` (existe en
   `core/procurador_intake.py:533`, también sin llamador) necesita el **contenido extraído** del
   adjunto, que es justo la parte que falta.
2. **La guarda anti-duplicado del adjuntar filtra por NOMBRE**, y `relate/attachments` **duplica**
   (medido: censo 3→4→5). Un nombre estable la hace fiable; un nombre propuesto la esquiva. Elegir
   nombres bonitos hoy agravaría a propósito `MEJORAS #178`.
3. Los nombres reales son feos y se acepta: `Todos-1531714.pdf`, `LXN202609041126090071.PDF`.

## 10. Lo que este diseño obliga a corregir en el spec de entrega

Su **§2** promete *«cuenta de archivado = la del propio usuario»*. **No es alcanzable con F3**, y no
por implementación: por el §2.1 — F3 solo escribe sobre copias que ya existen, y la copia de una
persona la crea su Roundcube. Lo que ese documento debe recoger:

- Quien clique, se escribe sobre la copia disponible. **Qué visibilidad hereda el correo queda
  abierto** (§5.1, D7): Nikolai sostiene que va por el expediente, el §8 de F3 dice que va por el
  buzón, y con `x-api-key` no es medible. El documento de entrega no debe prometer ninguna de las
  dos hasta que una persona lo compruebe con su sesión.
- Es la **cuarta** cosa pendiente en ese documento; su §5 ya está marcado como afectado.

## 11. Lo que NO está probado, dicho por delante

1. **Qué `id_creador` deja una escritura de F3 en el CRM.** Hoy las filas dicen la persona porque
   las hizo desde el webmail. F3 escribe con `x-api-key`, y existen usuarios `api.key.1..4`
   (24, 25, 32, 33). Si el CRM le atribuye la escritura a uno de ellos, **deja de saber qué persona
   archivó**, y eso le importa a F6. **La prueba de Nikolai previa al despliegue lo contesta
   gratis**: archiva él uno y se lee el `id_creador` resultante.
2. **El contenido binario del adjunto subido**: se verifica nombre y carpeta, no los bytes (F3 §8.7).
3. **La ventana del censo**: entre leer el censo y postear el adjunto hay un hueco sin cerrojo. D4
   lo hace inalcanzable hoy; **no lo cierra**.
4. ~~**El contenido de la copia elegida**~~ — **MEDIDO el 2026-09-08, y sostiene el diseño.**
   `hasAttachments` —que es propiedad del **mensaje**— **coincide entre copias en 10 de 10** de los
   casos divergentes sondeados. Las copias son el mismo correo, así que `elegir_cuenta` (§5) puede
   tomar cualquiera sin perder adjuntos.
   ⚠️ **Y de camino, una trampa que casi tumbó este párrafo en falso: el campo `adjuntos` del
   elemento `mail` NO es el número de adjuntos.** Es estado **por copia** y no sigue a
   `hasAttachments`: hay ocho casos con `hasAttachments=False` y una copia con `adjuntos=1`. Leído
   como «trae N adjuntos» da que **31,2 %** de los multicopia «difieren en adjuntos» — conclusión
   que se publicó y se retiró el mismo día al discriminar con `hasAttachments`. Qué significa
   `adjuntos` sigue **sin saberse**, y F3 no lo usa: el manifiesto lo da el relate.
   *(Lo que sigue sin medirse es el cotejo de `att_id` entre copias: obtenerlos exige POSTear el
   relate, que escribe, y no se hace sobre correos reales de cliente.)*
5. **La visibilidad, no como incógnita sino como procedencia.** El §5.1 descansa en la
   explicación del administrador del CRM, no en una medición de este repo, y **con `x-api-key` no
   es medible** —es una identidad de servicio, ve lo que ve la clave—. No bloquea nada porque
   ninguna rama cuelga de ella; se anota para que nadie la cite luego como «medido».

## 12. Pruebas

Orquestador con **cliente falso**; el cliente REST sigue con su transporte falso. Ningún test sale
a la red, y la guarda que lo impide tiene que levantar algo que el `except` del código no atrape.

Casos exigidos: dry-run no toca la red · interruptor ausente ⇒ dry-run · interruptor con valor
basura ⇒ dry-run · `sin_registro` ⇒ revisión sin POST · copia propia presente ⇒ se usa la propia ·
copia ajena (una o varias) ⇒ se usa la de menor cuenta y se anota (D6) ·
extrajudicial ⇒ bloqueado sin POST · **verificación desde el expediente con el `mail_id` presente y
ausente** · relate ok + adjunto fallido ⇒ `ok=False` con la relación registrada · censo ilegible ⇒
indeterminado · adjunto ya en el censo ⇒ no re-sube · la traza guarda los tres hechos por separado.

**Arnés de mutación**, y cada mutante tiene que poner rojo un test:

| Mutante | Qué prueba |
|---|---|
| el interruptor devuelve siempre «vivo» | que el dry-run está probado y no es decorado |
| `ok = verificado` (colapsarlos) | que la traza distingue los tres hechos |
| la verificación vuelve a `findRelations` por copia | que `#176` está realmente cerrado |
| `varias_cuentas` se trata como `sin_registro` | que los dos estados se distinguen (`#177`) |
| `elegir_cuenta` toma siempre la primera copia | que la preferencia por la propia está sujeta (§5) |
| el nombre final deja de ser el original | que D3 lo sujeta un test y no un comentario |

Un guard recién escrito **siempre pasa**: hasta que se le ha visto rojo, no es una defensa.

## 13. Revisión adversarial

**Radio de daño: escribe relaciones y documentos en expedientes de clientes ⇒ 2 rondas** — una
sobre este diseño antes de construir, otra sobre el diff. Contrato en `CLAUDE.md`.

Al revisor, cuatro cosas señaladas a propósito:

1. **§5.1 / §11.5 — la visibilidad viene de una explicación, no de una medición.** Ninguna rama
   cuelga de ella, pero conviene comprobar que el §5.1 no se apoye en ella sin darse cuenta. Una
   versión anterior cortaba a revisión el 6,3 % multicopia «para proteger la visibilidad», y esa
   precaución no protegía nada.
2. **§6.2 — la comprobación previa degradada a atajo**, apoyada en que re-relacionar no duplica.
   Es una medición de un día sobre tres correos.
3. **§11.1 — el `id_creador` de una escritura de F3**: incógnita con consecuencia para F6.
4. **§11.4 — que las N copias sean el mismo correo con los mismos adjuntos**: asumido, no cotejado.

## 14. Higiene

Sin datos de cliente. Los expedientes citados son los de prueba del despacho (**636**
extrajudicial, **683** judicial) y sus residuos **se quedan** por decisión de Nikolai del
2026-09-07: habrá más escrituras y los borrará él al terminar. El `mail_id` 439232 corresponde a un
correo de marketing ajeno a cualquier caso, elegido a propósito.
