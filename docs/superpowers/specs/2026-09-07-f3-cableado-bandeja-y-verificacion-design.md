---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-09-07
revision: v2 (2026-09-09 — R1 de Codex adjudicada: NO-SHIP, 14/14 confirmados; alcance rehecho)
topic: F3 — cablear el archivado a la bandeja, y verificar por el lado del expediente
relacionado:
  - docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md (rev. 5 — el cliente REST y el contrato medido)
  - docs/superpowers/specs/2026-09-07-f3-cableado-bandeja-y-verificacion-r1-adversarial-review.md (acta de la R1; adjudicada en §15)
  - docs/superpowers/specs/2026-07-19-intake-miniapp-entrega-design.md (entrega; su §2 y §5 quedan afectadas, ver §10)
  - docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md (§6 bandeja, §15 F3, §18.9 la terna)
  - docs/MEJORAS_FUTURAS.md (#176, #177, #178, #179, #181, #182)
---

# Diseño — F3: cablear el archivado a la bandeja, y verificar por el lado del expediente

> Cierra `MEJORAS #176` y `#177`, y encadena la pieza que F3 dejó construida y sin llamador.
> **No** construye el paso del webmail (pieza (b) del `[SIGUIENTE]` de `PLAN.md`), ni F4
> (renombrado por contenido), ni el estado compartido entre apps.

## 0. Qué cambió de la v1 a la v2, y por qué el alcance es otro

La v1 fue a **R1 adversarial con Codex** y volvió **NO-SHIP: 14 hallazgos, 14 confirmados,
0 refutados** (§15, con acta hermana que archiva el informe literal). El diseño no era apto para
construirse. Tres de los catorce **no eran enmiendas de redacción**, sino cambios del tamaño de la
pieza:

| | Qué era | Dirección |
|---|---|---|
| **H-01** | el cableado presuponía un inventario de adjuntos que la ingesta no construye | la pieza **crece hacia arriba**: `gmail_source` entra en el alcance (§9.1) |
| **H-02** | `elegir_cuenta` prometía elegir una copia que el cliente no elige | la pieza **se encoge**: el §5 se **retira** |
| **H-06** | la traza no podía representar los tres hechos que prometía | la pieza **crece hacia dentro**: cambia la forma de `ArchivoResult` (§7.2) |

**Dos correcciones que conviene leer antes que nada, porque eran afirmaciones falsas mías:**

1. **«La relación que escribe el relate es global.»** No lo es: la elige el servidor (§5). Salió de
   una medición que **no podía discriminar**, y llegó a `INTEGRACION_SUDESPACHO §10.10` —el SSOT
   del contrato del CRM— y a la memoria del proyecto. Los tres sitios, corregidos el 2026-09-09.
2. **«D4 lo hace inalcanzable hoy»** (la carrera del censo). Falso: dos pestañas de la bandeja en la
   misma máquina bastan (§11.3).

Y una tercera, menor pero rancia en un día: el §1 de la v1 decía que `git grep procurador_relate`
«devuelve solo su propio test». Es falso desde el 2026-09-08 **por mis propios commits** — los tres
sondeos que promoví importan del módulo. Sigue sin haber **llamador de producción**, que es lo que
importa.

## 1. El problema, en dos frases

**`core/procurador_relate.py` existe, está validado en vivo, y ningún camino de producción lo
llama.** Sus únicos consumidores son su test y tres sondeos de solo lectura; la bandeja sigue
diciendo *«Dry-run: confirmar registra la decision (terna §18.9); NO escribe en el CRM (eso es
F3)»* (`streamlit_app.py:2699`). Y cuando se le llame, **verifica desde el lado equivocado**: relee
`findRelations(uid, account)`, que es una vista **por copia** del correo.

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

## 3. Decisiones de Nikolai

| # | Decisión |
|---|---|
| D1 | **Un clic**: «Confirmar» archiva. Con **interruptor global** por variable de entorno, y **ausente ⇒ dry-run** |
| D2 | Un correo no indexado **bloquea el botón**, y la tarjeta dice que falta el paso del webmail |
| D3 | El nombre final de cada adjunto lo **escribe la persona** en la tarjeta, prerellenado con el original (2026-09-08, con censo — §9.2) |
| D4 | **Escritura solo en la máquina de Ana** (más la de Nikolai para probar). Paola y Sergio, dry-run |
| D5 | Alcance **judicial-first** — honra la decisión del 2026-07-19 (entrega §9) |
| ~~D6~~ | ~~elegir la copia sobre la que se escribe~~ — **RETIRADA**: el cliente no la elige (§5) |
| D7 | **La visibilidad tiene DOS superficies** (§5.1, explicado por Nikolai el 2026-09-07). Ninguna rama del diseño cuelga de ella |
| D8 | **FD sigue leyendo `procesal@`**; leer el buzón del usuario es la arquitectura objetivo, con disparador — §5.2 |

**Lo que D4 sí hace y lo que no.** Sí: reduce a una las instalaciones que escriben, así que el
corpus no se llena de escrituras concurrentes de personas distintas. **No: no hace inalcanzable la
carrera** — dos pestañas de la bandeja en el ordenador de Ana leen el mismo censo y postean las
dos. La v1 afirmaba lo contrario y era falso. Mitigación en §11.3.

## 4. Arquitectura

La regla del repo decide la forma: **la lógica va al core, Streamlit solo orquesta.** El botón no
llama a `archivar()`.

```
core/procurador_archivo.py          (NUEVO — orquestación con política)

  archivar_confirmado(item, action, *, quien, escritura_viva, cliente=None)
      -> ResultadoArchivo

  1. destino = destino_efectivo(prop, action)        # (elemento, id) o None
  2. destino is None                    -> revisión, sin red
  3. elemento != expedientes_judiciales -> bloqueado (D5), sin red
  4. inventario de adjuntos incoherente -> revisión, sin red        # §9.1
  5. nombres finales repetidos          -> revisión, sin red        # §9.3
  6. not escritura_viva                 -> dry-run: registra y sale
  7. cerrojo local por email_id                                     # §11.3
  8. registrar INTENTO en la traza                                  # §7.1
  9. pedidos = inventario menos lo que la decisión anterior subió    # §9.5
 10. relate.archivar(..., adjuntos=[(original, nombre_del_campo), ...])
 11. VERIFICAR por el lado del expediente — siempre, y sea cual sea
     el camino que `archivar` haya tomado por dentro                 # §6.2
 12. registrar RESULTADO (o DESCONOCIDO si hubo excepción)           # §7.1
 13. transicionar(item, "confirmar" | "revisar")                     # §6.4
```

**Fichero nuevo, no dentro de `procurador_relate.py`.** Ese módulo es el cliente REST; esto es
orquestación con política —el interruptor, el cerrojo, la traza, la transición de cola—. Se prueban
distinto: el cliente con transporte falso, el orquestador con **cliente** falso.

**El interruptor** es `PROCURADOR_ESCRITURA_CRM`, leído en `core/config.py`. **Ausente, vacío, o
cualquier valor que no sea `1`/`true` ⇒ dry-run.** No es un control de la UI. La bandeja **muestra
el modo**, para que nadie crea que archivó cuando no.

**El paso 8 es nuevo:** la traza se escribe **dos veces**, antes y después. Sin eso, «no hay línea
en el log» no distingue «no escribí» de «escribí y morí antes de registrarlo».

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
  servidor decida — no en el de quien archiva. Ver §11, punto 6.

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

El bloque `mail` del expediente —`get_relaciones(elemento, id)`— usa **el mismo espacio de ids que
el `mail_id` que devuelve el relate**, así que `mail_id ∈ ids` es una comprobación exacta. Y es la
**única independiente de la copia**: el `mail_id` aparece en el expediente aunque solo una copia lo
vea desde `findRelations` (§5). Comprobado en el 636 y en el 683.

Ese bloque puede traer elementos que **no** son expedientes — visto `mailcarpetas` y `tracking`,
éste con varios ids por correo. Quien lo recorra filtra por el elemento pedido; no asume que todo
sea un expediente.

### 6.2 La verificación vive en el ORQUESTADOR, no dentro de `relacionar()`

**La v1 decía que el arreglo iba dentro de `relacionar()` y que así quedaba cerrado «para cualquier
llamador». Era falso:** `archivar` llama a `_post_relate` **directamente** cuando `ya_estaba`, para
recuperar el manifiesto, y ese POST no pasa por `relacionar`. Un arreglo ahí dentro deja ese camino
fuera.

Así que la verificación autoritativa es un **paso del orquestador** (§4, paso 11) que corre
**después de `archivar`, sea cual sea el camino que haya tomado por dentro**. Es la única forma de
cubrir los dos POST con una sola comprobación.

- **La comprobación PREVIA por `findRelations` se RETIRA como guarda.** No es imprecisa: es
  **incorrecta** — sobre una copia que no es la elegida responde «no relacionado» cuando sí lo está.
- **`relacionar()` conserva su relectura interna como señal advisory**, y **nada del veredicto final
  cuelga de ella**.

### 6.3 Los dos mensajes falsos se arreglan aquí (`MEJORAS #177`)

- `resolver_cuenta()` deja de decir *«¿no indexado todavía?»* cuando hay N copias: distingue
  `sin_registro` de `varias_cuentas`, y los nombra.
- El relate deja de sugerir *«¿existe el miembro?»* cuando el miembro existe.

### 6.4 El estado `revision` hay que CREARLO

`core.procurador_review.transicionar` admite hoy **`confirmar` · `descartar` · `recuperar`** sobre
`pendiente | confirmado | descartado`. **`"revisar"` no existe y lanza `TransicionInvalida`**: el
pseudocódigo de la v1 se habría estrellado en el primer archivado incompleto.

La rev. 2 lo especifica en vez de suponerlo:

- **Estado nuevo `revision`**, alcanzable desde `pendiente` con la acción `revisar`, y desde el que
  se puede `confirmar` (reintento) o `descartar`.
- **La bandeja carga `revision`** además de `pendiente` y `descartado`. Sin eso, el trabajo
  incompleto queda invisible, que es peor que el estado que falta.
- **Un `confirmado` de dry-run NO es un archivado real.** Se distingue en la traza
  (`archivado_en_crm`), y la bandeja debe poder pedir una confirmación viva de un ítem que solo pasó
  por dry-run. Eso **no** es permiso retroactivo: es no confundir «registré la intención» con
  «escribí».

## 7. La traza (plan §18.9, F3 §6)

### 7.1 Dos fases, porque una excepción no puede borrar la evidencia

`record_decision` se llama **dos veces**:

- **INTENTO**, antes de tocar la red: destino, adjuntos pedidos con su nombre final, actor, modo.
- **RESULTADO**, después. Y si el camino murió por excepción, el orquestador registra
  **`DESCONOCIDO`** con el error.

Sin esto, un `ReadTimeout` posterior a que el servidor acepte el relate deja **cero rastro** y la
cola en pendiente. Con esto, «hay INTENTO sin RESULTADO» es un estado legible y reconciliable, que
es lo que F6 necesita. Y un fallo al **escribir** el log se propaga: no se traga.

### 7.2 Los tres hechos, y por qué hay que cambiar `ArchivoResult`

**La v1 prometía distinguir «no escribí» / «escribí y no lo confirmé» / «escribí y lo confirmé», y
con la forma actual del resultado no se puede.** Hoy `archivar` termina así:

```python
return ArchivoResult(ok=res.ok, verificado=res.verificado, …)   # res = el del ADJUNTAR
```

Consecuencias, verificadas en el código: relación verificada + adjunto que falla ⇒
`verificado=False`, **y el positivo de la relación se borra**; relación verificada + problema de
emparejamiento ⇒ `verificado=True` **con cero documentos**. Y `ya_presentes` se descarta al
construir el resultado, aunque la v1 dijera que se registra.

**Cambio de contrato, y es alcance nuevo:** `ArchivoResult` pasa a llevar **dos sub-resultados
independientes** —`relacion` y `documentos`—, cada uno con su `ok`, su `verificado` y su `error`,
más `ya_presentes`. **El `verificado` plano desaparece**: no significaba nada estable.

**Esto toca `core/procurador_relate.py`, cuyo contrato de retorno la v1 dijo que no cambiaría, y
los 31 tests que lo afirman.** Se revisan uno a uno, y **ninguno se relaja para que pase**.

**Y la traza no lleva `cuenta_usada`** (§5): registrar la copia «elegida» sería inventar
procedencia.

## 8. Errores — la tabla, ahora con los caminos que faltaban

| Situación | Escribe | Estado | Qué ve Ana |
|---|---|---|---|
| destino sin elemento | no | revisión | el motivo, botón bloqueado |
| elemento no judicial (D5) | no | bloqueado | «judicial-first» |
| `sin_registro` | no | revisión | «falta relacionarlo desde el webmail» (D2) |
| `varias_cuentas` | **sí** | según resultado | se archiva; la copia la elige el servidor (§5) |
| **inventario de adjuntos incoherente** | **no** | revisión | «el correo trae adjuntos y no tengo sus nombres» |
| **dos nombres finales iguales** | **no** | revisión | «repites un nombre: el censo no podría distinguirlos» |
| interruptor apagado | no | confirmado (dry-run) | «registrado, sin escribir» + el modo |
| relate 200 y el expediente no lo ve | — | revisión | `relacion.verificado=False`, con el motivo real |
| relate ok · adjunto falla | **sí, la relación** | revisión | `relacion.ok=True` **y** `documentos.ok=False`, por separado |
| censo ilegible o **truncado** | indeterminado | revisión | «no se pudo comprobar; no reintentes sin mirar» |
| adjunto ya en el censo **con su carpeta** | no re-sube | confirmado | «ya estaba» |
| **excepción en cualquier punto** | desconocido | revisión | queda INTENTO sin RESULTADO (§7.1) |

Dos reglas gobiernan la tabla, y las dos vienen de mediciones:

- **Censo ilegible o truncado no es fallo, es indeterminado**, porque un fallo invita a reintentar y
  **reintentar duplica** (F3 §8.2, medido).
- **La escritura de la relación y la de los documentos son dos hechos** y no se colapsan (§7.2).

## 9. Los adjuntos: inventario, nombre y censo

### 9.1 El inventario NO existe, y sin él el diseño confirma sin archivar

La v1 daba por hecho que la tarjeta conocía los adjuntos del correo. **No los conoce**, y el
resultado es el peor posible:

```
core/gmail_source.py            descarta `filename` y `attachmentId` de cada parte
core/procurador_runner.py:103   attachments=[]                    <- a pelo
core/procurador_review.py:98    {a.original_filename: … for a in proposal.attachments}
core/procurador_relate.py:458   if not pedidos: return ok=True, verificado=True
```

La tarjeta renderiza **cero campos**, `archivar` recibe **cero pedidos** y devuelve **éxito
verificado**. El correo sale de pendientes, el dedup no lo vuelve a mirar, y **el documento se
queda sin archivar sin que nadie se entere.**

**Remedio, y es el alcance nuevo hacia la ingesta:**

1. **`gmail_source` conserva el inventario.** La respuesta `format=full` que ya se recibe trae
   `filename` y `attachmentId` por parte. **No hacen falta los bytes**: solo los nombres. (Bajar los
   bytes sigue siendo `MEJORAS #181` y **no** entra aquí.)
2. **`procurador_runner` deja de poner `[]`** y rellena `IntakeProposal.attachments` con
   `proposed_name = original_filename` — sin LLM, que es F4.
3. **Guarda dura, que es lo que mata el camino silencioso:** si el correo **trae adjuntos** y el
   inventario llega vacío, **no se confirma**: va a revisión con ese motivo. Nunca se interpreta
   «sin pedidos» como «nada que subir».
4. **Los ítems ya persistidos en la cola no tienen inventario.** Caen en la guarda anterior y van a
   revisión, a propósito. No se les inventa uno.

### 9.2 El nombre lo escribe la persona (D3), con la convención censada

Un `text_input` por adjunto, prerellenado con el original. El nombre final viaja en el mapa
`att_id → nombre` de `relate/attachments`, así que **no hace falta bajar el adjunto**, ni OCR, ni
LLM, ni F4.

**Por qué, con el censo delante** (4.000 documentos de `gdocu`, 2026-09-08): solo el **1 %** (34)
conserva un nombre de máquina como final; **541** se renombraron **desde** un nombre de máquina; el
62 % no se renombra porque ya llegó con nombre descriptivo. El renombrado ocurre **justo cuando el
original es de máquina**, que es el caso de LexNET. La v1 —subir con el nombre original— habría
metido a FeesDefender sistemáticamente en ese 1 %.

**La convención, censada y no inventada:** `DIOR` 305 · `JUSTIF PROCU` 100 · `JUST PROCU` 87 ·
`D XX` 85 · `PROCU` 65 · `ESCR PROCU` 63 · `ESCR CRIO` 55 · `DECR` 52 · `AUTO` 51 · `FRA PROCU` 50
· `PROV` 25 · `D 01`–`D 07` y `DOC 02`–`DOC 11`. **Es inconsistente** (`JUSTIF`/`JUST`;
`D NN`/`DOC NN`), así que no hay taxonomía limpia que aprender: F4 tendrá que **proponer y dejar
corregir**. Y la convención que debe aprender es **ésta**, no la `AAAA-MM-DD_descripcion` del repo.
El campo `categoria` de `gdocu` viene **vacío**: el tipo vive en el nombre.

### 9.3 Nombres repetidos: se rechazan ANTES de escribir

Con nombres escritos a mano, dos adjuntos pueden recibir el **mismo** nombre final. El censo no
podría distinguirlos, y `subidos` los contaría a los dos a partir de una sola entrada nueva —
confirmando un documento que no subió.

**Se valida en la tarjeta y en el orquestador:** dos nombres finales iguales en el mismo correo ⇒
**revisión**, sin escribir. No se desambigua por nuestra cuenta.

### 9.4 El censo: por `(nombre, carpeta)`, y completo o indeterminado

Dos defectos del cliente actual, los dos verificados en el código:

- **`_censo_gestor_documental` pide `id_carpeta` y devuelve solo `nombrefinal`.** Así que la
  comprobación es por nombre a secas: un homónimo **en otra carpeta** bloquea la subida y devuelve
  éxito. **La frase de la v1 «se verifica nombre y carpeta» era falsa.** El censo pasa a devolver
  **pares `(nombre, carpeta)`** y la comparación usa el par.
- **`itemsPerPage=100`, sin paginar — y pidiendo `return_totals=true`.** El dato para detectar el
  truncamiento **viene en la respuesta y se tira**. El censo pasa a **leer el total y paginar**; si
  el total no se puede establecer, el resultado es **indeterminado** (§8), nunca «no está».

### 9.5 Reanudar: se LEE la decisión anterior

La v1 presentaba como mitigación «el nombre usado queda en la traza». **Escribir en un log que
nadie lee no es una mitigación.** El orquestador **consulta** `read_decisions` para ese `email_id`
antes de escribir (§4, paso 9) y excluye de los pedidos lo que una pasada anterior registró como
subido. Si no hay decisión previa, o quedó `DESCONOCIDO`, se cae en el censo; y si el censo no
discrimina, en **indeterminado**.

## 10. Lo que este diseño obliga a corregir en el spec de entrega

Su **§2** promete *«cuenta de archivado = la del propio usuario»*. **No es alcanzable**, y ahora por
dos razones: por el §2.1 —F3 solo escribe sobre copias que ya existen— y por el §5 —**la copia la
elige el servidor**—. Lo que ese documento debe recoger:

- Quien clique, se escribe sobre la copia que decida el **servidor**, no sobre la del usuario.
- **Qué visibilidad hereda el correo**: por el expediente lo ve el equipo (§5.1); en Roundcube lo ve
  el titular del buzón de **la copia que eligió el servidor**, que no controlamos. Ese documento no
  debe prometer ninguna de las dos como elección nuestra.
- Es la **cuarta** cosa pendiente en él; su §5 ya está marcado como afectado.

## 11. Lo que NO está probado, dicho por delante

1. **Qué `id_creador` deja una escritura de F3 en el CRM.** F3 escribe con `x-api-key` y existen
   usuarios `api.key.1..4`. Si el CRM le atribuye la escritura a uno de ellos, **deja de saber qué
   persona archivó**, y eso le importa a F6. Y —aviso de la R1— **leer `id_creador` de la fila
   `mail` no sirve**: esa fila ya existía antes (§2.1). Hay que identificar el objeto cuya autoría
   se mide: el vínculo o el documento nuevo.
2. **El contenido binario del adjunto subido**: se verifica nombre y carpeta, no los bytes.
3. **La ventana del censo** entre leer y postear: mitigada dentro de una máquina (§11.3), **no
   cerrada** entre máquinas.
4. **Que las N copias sean el mismo correo con los mismos adjuntos.** La medición del 2026-09-08
   —`hasAttachments` coincide en 10 de 10— es **consistente con** eso y **no lo establece**: es un
   booleano, no puede distinguir dos manifiestos ni contar adjuntos. Bajado de «sostiene el diseño»
   a lo que de verdad dice.
5. **La visibilidad, como cuestión de procedencia**: el §5.1 descansa en la explicación del
   administrador del CRM y con `x-api-key` —identidad de servicio— **no es medible**.
6. **La regla por la que el servidor elige la copia.** Dos observaciones, las dos la 15; **no es una
   regla**. Y su consecuencia —en qué webmail aparece el correo— **no la controla FD**.
7. **La autoría del clic**, más allá de lo que arregla §11.4: el actor sale de un selector, y nadie
   comprueba que quien lo eligió sea quien lo pulsa.

### 11.3 La carrera del censo: mitigada en una máquina, declarada entre varias

La v1 decía que D4 la hacía **inalcanzable**. Es falso: dos pestañas de la bandeja en el ordenador
de Ana leen el censo sin el documento y postean las dos.

- **Dentro de una máquina se cierra con un cerrojo local por `email_id`** (`filelock`, ya en las
  dependencias, mismo patrón que el mutex de `MEJORAS #126`). Serializa las dos pestañas.
- **Entre máquinas NO se cierra**, y se declara. D4 lo hace improbable —una sola instalación
  escribe— pero no imposible, y **no excluye a quien archive desde su Roundcube**, que no pasa por
  nuestro cerrojo.

### 11.4 La autoría: el selector, arreglado en lo que se puede

`st.radio("Yo soy", ["Nikolai", "Paola", "Ana"])` tiene dos defectos: **el primer valor es Nikolai**,
así que el descuido de Ana te atribuye su decisión, y **Sergio no está**, aunque D4 y D6 lo
contemplen como refuerzo.

- La lista incluye **a los cuatro**, y su valor inicial es un centinela **«— elige —»** que
  **bloquea el botón** hasta que alguien escoge.
- El actor viaja **como argumento de la operación**, no leído de un singleton global dentro del
  orquestador.
- **Lo que esto NO arregla**, y queda declarado: nada impide elegir el nombre de otro. Es un log de
  buena fe, no una autenticación, y así hay que leerlo.

### 11.5 La tarjeta: lo que muestra es lo que confirma

`st.success(f"Expediente #{exp_id}…")` muestra el **propuesto** mientras el botón usa el
**reasignado** de `st.session_state`. Si alguien reasigna y luego lee el encabezado, cree haber
vuelto al expediente que ve. **El encabezado y el destino salen de la misma fuente**
—`destino_efectivo`—, y la tarjeta muestra el destino **efectivo**. Es un defecto preexistente que
pasar de dry-run a escritura real vuelve material.

## 12. Pruebas

Orquestador con **cliente falso**; el cliente REST sigue con su transporte falso. Ningún test sale a
la red, y la guarda que lo impide levanta algo que el `except` del código **no atrapa**.

Casos exigidos, agrupados por el hallazgo que los obliga:

- **§9.1:** correo con adjuntos e inventario vacío ⇒ **revisión sin POST** · inventario presente ⇒
  un campo por adjunto · ítem viejo sin inventario ⇒ revisión.
- **§9.3/§9.4:** homónimo **en otra carpeta** ⇒ **no** cuenta como presente · dos nombres finales
  iguales ⇒ revisión sin POST · censo con `totalItems` mayor que la página ⇒ **pagina** · total
  ilegible ⇒ indeterminado.
- **§7.2:** relate ok + adjunto fallido ⇒ `relacion.ok=True` **y** `documentos.ok=False` · fallo de
  emparejamiento ⇒ `documentos.ok=False` con cero subidos · `ya_presentes` **se conserva**.
- **§6.2:** el camino `ya_estaba` también pasa por la verificación del expediente.
- **§7.1:** excepción tras el POST ⇒ queda **INTENTO sin RESULTADO** · fallo al escribir el log ⇒ se
  propaga.
- **§11.3:** dos ejecuciones concurrentes sobre el mismo `email_id` ⇒ el cerrojo serializa y solo una
  postea.
- **§9.5:** segunda pasada con nombre distinto ⇒ **no** repostea el `att_id` ya subido.
- **§6.4:** `revisar` es una transición válida · la bandeja carga `revision`.
- **§11.4:** actor sin elegir ⇒ botón bloqueado · el actor viaja **por operación**.
- **§11.5:** el encabezado y el destino efectivo salen de **la misma** fuente.
- **D1/D2:** interruptor ausente o basura ⇒ dry-run · **dry-run no toca la red**, así que en dry-run
  el bloqueo de D2 se resuelve con lo que la cola ya sepa, **sin** consultar el CRM, y la tarjeta lo
  dice.

**Arnés de mutación**, y cada mutante tiene que poner rojo un test:

| Mutante | Qué prueba |
|---|---|
| el interruptor devuelve siempre «vivo» | que el dry-run está probado y no es decorado |
| `if not pedidos: ok=True` sin la guarda de §9.1 | que el camino silencioso está cerrado |
| el censo compara solo por nombre | que el par `(nombre, carpeta)` se usa de verdad |
| el censo ignora `totalItems` | que la paginación no es decorado |
| `documentos.verificado` se copia a `relacion.verificado` | que los dos hechos siguen separados |
| se salta el registro del INTENTO | que la traza de dos fases existe |
| el cerrojo se vuelve un no-op | que la serialización se prueba con dos ejecuciones reales |
| el actor se lee del singleton | que viaja por operación |
| el encabezado vuelve a `exp_id` | que §11.5 lo sujeta un test |

Un guard recién escrito **siempre pasa**: hasta que se le ha visto rojo, no es una defensa.

## 13. Revisión adversarial

**Radio de daño: escribe relaciones y documentos en expedientes de clientes ⇒ 2 rondas.** La **R1
sobre el diseño está consumida** (§15: NO-SHIP, 14/14 confirmados). Queda la **R2 sobre el diff**.

Al revisor de la R2, cuatro cosas señaladas a propósito:

1. **§9.1 — la guarda que cierra el camino silencioso.** Es el remedio del único hallazgo que podía
   perder documentos sin avisar; conviene atacar si es **inerte**.
2. **§7.2 — la nueva forma de `ArchivoResult`** y los 31 tests revisitados: que ninguno se haya
   relajado para pasar.
3. **§11.3 — el cerrojo local**: que sirva para dos pestañas y que **no** se presente como solución
   entre máquinas.
4. **§5 y §11 punto 6 — lo que no controlamos**: que el diseño no vuelva a afirmar elección donde solo hay
   observación.

Y la nota de método que la R1 dejó: **varias cifras de este documento corrigen conclusiones previas
mías**, y tres afirmaciones falsas mías llegaron a documentos vigentes. Si una cifra de aquí no
cuadra con la fuente, **gana la fuente**; los sondeos que reproducen las lecturas son
`scripts/sondeo_copias_mail.py` y `scripts/sondeo_join_gmail_crm.py`, los dos con control positivo.

## 14. Higiene

Sin datos de cliente. Los expedientes citados son los de prueba del despacho (**636**
extrajudicial, **683** judicial) y sus residuos **se quedan** por decisión de Nikolai del
2026-09-07: habrá más escrituras y los borrará él al terminar. El `mail_id` 439232 corresponde a un
correo de marketing ajeno a cualquier caso, elegido a propósito, y es el sujeto del experimento del
§5.

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
| H-04 · el censo por nombre pierde carpeta y multiplicidad | CRÍTICO | **confirmado** | rev. 2 §9.4; el «se verifica nombre y carpeta» de la v1 era **falso** |
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

