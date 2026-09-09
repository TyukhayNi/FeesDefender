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
| D3 | ~~nombre ORIGINAL~~ → **CAMBIADA el 2026-09-08 con medición**: la tarjeta lleva **un campo de nombre por adjunto**, prerellenado con el original, y lo escribe la persona. Ver §9 |
| D4 | **Escritura solo en la máquina de Ana** (más la de Nikolai para probar). Paola y Sergio, dry-run |
| D5 | Alcance **judicial-first** — honra la decisión del 2026-07-19 (entrega §9) |
| D6 | Si el usuario no es dueño de una copia, **se escribe sobre la copia que haya**; nuestro log registra quién clicó |
| D7 | **La visibilidad tiene DOS superficies** y las dos afirmaciones del expediente documental eran ciertas (§5.1, explicado por Nikolai el 2026-09-07). Ninguna rama del diseño cuelga de ella |
| D8 | **FD sigue leyendo `procesal@`** (2026-09-08). Leer el buzón del propio usuario es la **arquitectura objetivo**, con disparador escrito — §5.2 |

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

## 5. Qué copia se escribe — RETIRADO: no lo decide el cliente

> **La versión v1 de este §5 especificaba un `elegir_cuenta` con preferencia por la copia propia,
> más D6 y la variable `PROCURADOR_CUENTA_CRM`. Se retira entero.** No por ser ceremonia: porque
> **engaña**. Le diría al operador —y a la traza— que eligió un destino que no puede elegir.

**Medido el 2026-09-09** (a raíz de R1/H-02, que lo señaló leyendo el cuerpo del POST):

1. **`account` NO viaja en el POST del relate.** El cuerpo es `{messageIds, relatedMembers,
   relatedElement, cookies, dataHash}` (`core/procurador_relate.py`, `_post_relate`). El servidor
   **no puede saber** qué copia eligió el cliente.
2. **La relación se pega a UNA copia, no a todas.** Experimento: correo con copias en las cuentas
   2 y 15, relate hacia `extrajudiciales:636` **pasando `account=2`**. Después, la copia de la
   **15** ve la relación nueva y la de la **2** sigue viendo `[]`.
3. **La elige el servidor**, y escogió la 15 en las dos observaciones. **La regla no está medida**;
   dos datos no la establecen.
4. **Control positivo hecho**, para no repetir el error de método: `findRelations(account=2)`
   **sí** devuelve relaciones para otros correos de esa cuenta (5 de 5 con `estarelacionado=1`).
   Su `[]` es una respuesta, no un instrumento mudo.

**Consecuencias, y son de diseño:**

- **Se borran `elegir_cuenta`, D6 y `PROCURADOR_CUENTA_CRM`.** El orquestador (§4) pasa el
  `account` que resuelva la lectura y **no afirma nada sobre el destino**.
- **`cuenta_usada` desaparece de la traza (§7).** Registrarlo sería inventar procedencia: un dato
  con forma autoritativa sobre algo que el cliente no controla.
- **Qué copia lleva la relación es una propiedad del sistema, no una decisión nuestra**, y así se
  declara. Si la visibilidad en Roundcube va por buzón, el correo aparece en el webmail de quien el
  servidor decida — no en el de quien archiva. Ver §11.6.

**Y una corrección de la v1 que hay que dejar dicha:** su §5 justificaba «cualquier copia sirve»
con que **la relación es global**. Eso era falso, y salió de una medición que no podía
discriminar: se mandó el relate con dos `account` distintos, se obtuvo el mismo `mail_id`, y como
`account` no viaja, el mismo resultado era **inevitable**. La afirmación llegó a
`INTEGRACION_SUDESPACHO §10.10` —el SSOT del contrato— y a la memoria del proyecto; las tres
quedaron corregidas el 2026-09-09.

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

**Consecuencia para el diseño: ninguna rama cuelga de esto** — pero el argumento de la v1 era
falso y se sustituye. La v1 decía «cualquier copia sirve **porque la relación es global**». **No es
global** (§5). Lo que sostiene la conclusión es una medición distinta y mejor: **el expediente ve
el correo sea cual sea la copia que lleve la relación** — el `mail_id` aparece en el bloque `mail`
del 636 y del 683 aunque solo una copia lo vea desde `findRelations`. Así que la visibilidad de
equipo por el expediente se sostiene; lo que **no** se sostiene es que el cliente elija la copia.

### 5.2 Por qué se sigue leyendo `procesal@`, y qué la sustituirá

Se planteó leer **el buzón de Gmail del usuario que corre la app** en vez de `procesal@`. Decidido
el 2026-09-08: **se mantiene `procesal@`**, y lo otro queda como objetivo con disparador.

**Tres opciones, y solo dos son distintas.** (A) API de Gmail sobre `procesal@` —hoy—; (B) API de
Gmail sobre el buzón del propio usuario; (C) IMAP contra ese mismo buzón, que es «lo que lee
Roundcube». **B y C leen el mismo almacén** —Roundcube es un cliente, no un almacén, y detrás está
Gmail—; solo cambia el protocolo, y C exige credenciales IMAP, que es justo lo que `DEAD_ENDS`
manda no reproducir. Si algún día se cambia, se cambia a **B**.

**Lo que B arregla de verdad.** El grano: Roundcube es por persona, la fila `mail` es por persona,
el acto de relacionar es por persona, y **la lectura de FD es lo único compartido**. Con B
desaparecen `elegir_cuenta` (§5), D6 y `PROCURADOR_CUENTA_CRM`: la cuenta de la app **es** la
cuenta. Y da la **certeza** —no la casi-certeza— de que el correo está en el buzón sobre el que
actuará el webview.

⚠️ **Un argumento que se usó a favor de B y es FALSO, anotado para que nadie lo resucite:** que B
«le da a la app el uid IMAP» que necesita el composite del plugin. **No.** La API de Gmail no expone
uids de IMAP; el uid se saca del `rcmail.env` del webmail en los dos casos, y como el Message-ID
sobrevive al reenvío —medido, 23 de 32— la búsqueda funciona igual leyendo la lista.

**Por qué se queda A:**

1. **Con D4 —solo escribe la máquina de Ana— A y B dan hoy el mismo resultado.** El desajuste de
   grano solo muerde cuando escribe una segunda persona, y D4 aplaza ese caso.
2. **La lista es la puerta canónica.** Los buzones personales están detrás del reenvío, que **pierde
   cosas**: filtros, reglas, spam. Medido: 1 de 32 correos de la muestra estaba en SPAM.
3. **A cuesta cero.** B cuesta cuatro tokens OAuth —sobre una app con problema conocido de
   caducidad— y debilita el visor compartido del §3 de la entrega, que hoy sale gratis porque las
   cuatro apps leen la misma lista.

**Disparador para pasar a B:** el día que escriba en el CRM alguien que no sea Ana. **Y de ahí se
sigue algo que el revisor debe saber:** `elegir_cuenta`, D6 y `PROCURADOR_CUENTA_CRM` son
**andamio con fecha de caducidad**, no diseño definitivo. Se construyen porque hoy hacen falta y se
retiran con B.

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

## 9. Los adjuntos y su nombre (D3, **cambiada el 2026-09-08**)

**La tarjeta lleva un campo de texto por adjunto, prerellenado con el nombre original, y el nombre
final lo escribe la persona.** Un `text_input` por adjunto y nada más: el nombre final viaja al CRM
en el mapa `att_id → nombre` de `relate/attachments`, así que **no hace falta bajar el adjunto**, ni
OCR, ni LLM, ni `MEJORAS #181`, ni F4.

### 9.1 Por qué cambió, con el censo delante

La versión anterior subía el nombre original, razonando que renombrar era trabajo de F4. **Medido
el 2026-09-08 sobre 4.000 documentos del gestor documental**, eso era un retroceso:

| | |
|---|---|
| documentos cuyo nombre final **sigue siendo de máquina** | **34 de 4.000 — el 1 %** |
| renombrados **desde** un nombre de máquina (`LXN…`, `Env_…`) | **541** |
| no renombrados (`nombrefinal == nombreoriginal`) | 2.482 (62 %) — llegaron ya con nombre descriptivo |

Los dos últimos no se contradicen: **el renombrado ocurre justo cuando el original es de máquina**,
que es exactamente el caso de los adjuntos de LexNET. Con la D3 anterior, FeesDefender habría
entrado **sistemáticamente en ese 1 %** — inyectando `LXN202609071009040422.PDF` en un corpus donde
891 documentos de 16 expedientes judiciales siguen una convención humana, sin una sola excepción.

**Y el error de razonamiento fue anterior al diseño:** al ofrecer las opciones se descartó «que lo
escriba la persona en la tarjeta» por *«más teclear que ahora»*. Falso: hoy la persona **ya compone
un nombre con convención**, y los 4.000 documentos lo prueban. La opción descartada por costosa no
añade trabajo — lo **mueve** del webmail a la app.

### 9.2 La convención de la casa, censada (no inventada)

Prefijo de tipo procesal, descripción en mayúsculas, a veces importe o fecha. Los más frecuentes:

`DIOR` (305, diligencia de ordenación) · `JUSTIF PROCU` (100) · `JUST PROCU` (87) · `D XX` (85) ·
`PROCU` (65) · `ESCR PROCU` (63) · `ESCR CRIO` (55) · `DECR` (52) · `AUTO` (51) · `FRA PROCU` (50) ·
`PROV` (25) · `D 01`–`D 07` y `DOC 02`–`DOC 11` (~22 cada uno, el probatorio).

**Es inconsistente a propósito de nadie:** `JUSTIF` y `JUST` designan lo mismo, y el probatorio se
escribe `D NN` y `DOC NN`. **No hay taxonomía limpia que aprender**, así que F4 tendrá que
**proponer y dejar corregir**, nunca imponer. Y la convención que debe aprender es **ésta**, no la
`AAAA-MM-DD_descripcion` del repo — que es un hallazgo con el que se habría construido lo
equivocado. El campo `categoria` de `gdocu` viene **vacío**: el tipo vive en el nombre.

### 9.3 Lo que la guarda anti-duplicado exige de este cambio

`relate/attachments` **duplica** (medido: censo 3→4→5) y la guarda de `adjuntar` filtra **por
nombre**. Con nombres escritos a mano eso deja un hueco real: **dos nombres distintos para el mismo
adjunto la esquivan y el documento entra dos veces** (`MEJORAS #178`). Mitigación de esta pieza: el
campo se prerellena y **el nombre efectivamente usado se guarda en la traza** (§7), así que una
segunda pasada compara contra lo que se subió y no contra lo que se propuso.

### 9.4 F4 deja de ser prerequisito y pasa a ser mejora

Cuando exista, **prerellena** el campo con su propuesta y la persona corrige en vez de teclear. Y
tiene su set de evaluación esperándole: los **541 pares `nombreoriginal → nombrefinal`** del censo
son trabajo etiquetado a mano — ver `MEJORAS #182`.

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
indeterminado · adjunto ya en el censo ⇒ no re-sube · la traza guarda los tres hechos por separado ·
**el nombre que viaja al CRM es el del campo, no el original** (D3) · **campo dejado en blanco ⇒ se
usa el original, nunca una cadena vacía** · **el nombre USADO queda en la traza** (§9.3).

**Arnés de mutación**, y cada mutante tiene que poner rojo un test:

| Mutante | Qué prueba |
|---|---|
| el interruptor devuelve siempre «vivo» | que el dry-run está probado y no es decorado |
| `ok = verificado` (colapsarlos) | que la traza distingue los tres hechos |
| la verificación vuelve a `findRelations` por copia | que `#176` está realmente cerrado |
| `varias_cuentas` se trata como `sin_registro` | que los dos estados se distinguen (`#177`) |
| `elegir_cuenta` toma siempre la primera copia | que la preferencia por la propia está sujeta (§5) |
| el nombre del campo se ignora y se manda el original | que D3 la sujeta un test y no un comentario |
| un campo en blanco manda `""` al CRM | que el vacío no se convierte en un documento sin nombre |
| la traza guarda el nombre propuesto en vez del usado | que §9.3 —la mitigación del hueco de `#178`— no es decorado |

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
4. **§5.2 — `elegir_cuenta`, D6 y `PROCURADOR_CUENTA_CRM` son ANDAMIO**, con disparador de retirada
   escrito. Atacar su elegancia como si fueran diseño definitivo es gastar ronda; lo que sí merece
   ataque es si **fallan** mientras existan.

Y una nota sobre las mediciones que este diseño cita: **todas se hicieron el 2026-09-07/08 y varias
corrigen conclusiones previas mías del mismo día.** El §0 del spec de F3 rev. 5 lleva el catálogo.
Si una cifra de aquí no cuadra con la fuente, la fuente gana — y el sondeo que la reproduce está en
`scripts/sondeo_copias_mail.py` y `scripts/sondeo_join_gmail_crm.py`, los dos con control positivo.

## 14. Higiene

Sin datos de cliente. Los expedientes citados son los de prueba del despacho (**636**
extrajudicial, **683** judicial) y sus residuos **se quedan** por decisión de Nikolai del
2026-09-07: habrá más escrituras y los borrará él al terminar. El `mail_id` 439232 corresponde a un
correo de marketing ajeno a cualquier caso, elegido a propósito.

## 15. Adjudicación de la revisión adversarial R1 (Codex, 2026-09-08) — NO-SHIP, parcial

- **Objeto revisado:** `docs/superpowers/specs/2026-09-07-f3-cableado-bandeja-y-verificacion-design.md` rev. v1, commit `221b4d4`
- **Ronda:** 1
- **Revisor:** Codex CLI 0.153.4, solo lectura sobre copia congelada de 1.249 ficheros
- **Informe recibido:** `2026-09-07-f3-cableado-bandeja-y-verificacion-r1-adversarial-review.md`
- **Hallazgos:** 14 confirmados · 0 rebajados · 0 refutados · 0 escalados · 0 sin verificar
- **Remediado en:** rev. 2 de este documento — H-02 ya remediado (§5 retirado); los trece restantes en curso

Ronda sobre el **diseño**, antes de construir. El revisor corrió sin red sobre el commit congelado
y **ejecutó** 104 pruebas del repo más 12 reproducciones adversariales. El `sha256` del objeto
coincide al abrir y al cerrar. Adjudicado contra la fuente: **siete hallazgos se comprobaron línea
a línea en el código** y los siete se sostienen.

**Cero refutados, y no por no buscarlo.** Es el resultado honesto: el diseño **no era apto para
construirse**.

| Hallazgo | Sev. | Veredicto | Dónde se remedia |
|---|---|---|---|
| H-01 · el cableado no tiene inventario de adjuntos y puede confirmar sin subir ninguno | CRÍTICO | **confirmado** | rev. 2: la ingesta debe transportar los nombres (`gmail_source` los tira hoy) |
| H-04 · el censo por nombre pierde carpeta y multiplicidad | CRÍTICO | **confirmado** | rev. 2; el §11.2 de la v1 era **falso** |
| H-02 · `cuenta_usada` no identifica la copia escrita | ALTO | **confirmado y AGRAVADO** | **§5 retirado**; medición propia del 2026-09-09 |
| H-03 · el arreglo dentro de `relacionar()` deja un POST fuera | ALTO | **confirmado** | rev. 2 |
| H-05 · el censo solo mira los primeros 100 documentos | ALTO | **confirmado y AGRAVADO** | rev. 2 |
| H-06 · la traza no tiene el tercer hecho y destruye evidencia parcial | ALTO | **confirmado** | rev. 2: cambia la forma de `ArchivoResult` |
| H-07 · una excepción se lleva la escritura sin traza | ALTO | **confirmado** | rev. 2 |
| H-08 · D4 no hace inalcanzable la carrera del censo | ALTO | **confirmado** | rev. 2; la frase del §11.3 era **falsa** |
| H-09 · guardar el nombre en el log no es una mitigación | ALTO | **confirmado** | rev. 2 |
| H-11 · la autoría local puede atribuir el clic a otra persona | ALTO | **confirmado y AGRAVADO** | rev. 2 |
| H-12 · la tarjeta muestra un expediente y confirma otro | ALTO | **confirmado** | rev. 2; defecto preexistente que este cableado vuelve material |
| H-10 · el protocolo invoca una transición inexistente | MEDIO | **confirmado** | rev. 2: `"revisar"` **lanza** `TransicionInvalida` |
| H-13 · `hasAttachments` no verifica igualdad de contenido | MEDIO | **confirmado** | rev. 2: el §11.4 baja de «sostiene» a «consistente con, no establecido» |
| H-14 · mandatos incompatibles entre secciones | MEDIO | **confirmado** | rev. 2 |

### 15.1 Los tres que agravé al verificarlos

- **H-02.** El revisor leyó que `account` no viaja en el POST y dejó SIN VERIFICAR qué fila elige el
  servidor. Se midió: **la relación NO es global, la elige el servidor, y no es la copia que se le
  pasa.** Eso retira el §5 entero y obligó a corregir la afirmación «la relación es global» en
  **tres** documentos donde la escribí el 2026-09-07 — incluido `INTEGRACION_SUDESPACHO §10.10`,
  que es el SSOT del contrato del CRM. Detalle en §5.
- **H-05.** El censo no solo trunca a 100: **pide `return_totals=true` y tira el total**. El dato
  para detectar su propio truncamiento viene en la respuesta.
- **H-11.** El selector de autoría no solo tiene a Nikolai por defecto: **Sergio no está en la
  lista**, aunque D4 y D6 lo contemplen como refuerzo.

### 15.2 Lo que esta ronda dice de mi método, y es la parte que no conviene suavizar

**H-01 debí cazarlo yo.** El 2026-09-08 encontré **dos** rutas declaradas de punta a punta que
llegaban vacías —`attachment_texts` y `propose_attachment_name`—, las escribí en `MEJORAS #181`…
y no miré la tercera, `IntakeProposal.attachments`, que era la que sostenía la D3 que acababa de
cambiar. Encontré el patrón dos veces y falló justo donde tenía consecuencia.

**H-02 y H-13 son el mismo defecto de método por tercera y cuarta vez en dos días:** publicar una
conclusión sacada de un instrumento que no podía dar el otro valor. En H-02 fueron dos peticiones
idénticas leídas como prueba de globalidad; en H-13, un booleano leído como prueba de igualdad de
contenido. La regla que ya tengo escrita —*si una medición propia refuta o establece algo, exigir
un control positivo antes de publicarla*— no se aplicó ninguna de las dos veces.

**Divergencia declarada:** ninguna. Se acepta el veredicto y las catorce severidades. Lo único que
se añade es alcance: **H-01, H-02 y H-06 no son enmiendas de redacción**, son cambios del tamaño de
la pieza — hacia la ingesta, hacia menos, y hacia el contrato de `procurador_relate`
respectivamente. La rev. 2 se escribe con el alcance rehecho, no como parche de catorce puntos.

