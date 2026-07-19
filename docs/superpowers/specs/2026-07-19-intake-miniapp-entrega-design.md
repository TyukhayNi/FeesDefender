---
estado: vigente
dueño: Nikolai Tyukhay
fecha: 2026-07-19
topic: Intake procuradores — entrega: miniapp de escritorio, bajo demanda, por persona
relacionado:
  - docs/superpowers/specs/2026-07-19-f3-relate-crm-plugin-roundcube-design.md (el archivado en sí)
  - docs/superpowers/plans/PLAN_INTAKE_PROCURADORES_EMAIL.md (§6 bandeja, §15 fases, §18 QA)
---

# Diseño — Entrega del intake: miniapp de escritorio, bajo demanda, por persona

> **Eje distinto de F3.** F3 es *cómo se pega el correo al expediente en el CRM*. Esto es
> *cómo se empaqueta y se entrega el intake al despacho para uso diario*, sin depender de
> ningún ordenador encendido a todas horas ni de un servidor. Decidido con Nikolai el
> 2026-07-19.

## 1. Objetivo

Que Ana (y, como refuerzo, Paola o Sergio) procese el intake de correos de procuradores
desde una **app propia, instalada en su ordenador**, que reutiliza el motor ya construido
(F1 matcher + F2 bandeja) y el archivado (F3), **sin servidor central ni PC 24/7**, y sin
tener que usar la app Streamlit completa del despacho.

## 2. Modelo de ejecución (decidido)

- **Miniapp instalable por persona.** Se instala en el PC de Ana (titular) y en los de Paola
  y Sergio (refuerzo cuando Ana no está). Cada instalación corre en el contexto de su dueño.
- **Bajo demanda, no en bucle.** No hay proceso 24/7. **Al abrir la app**, ésta busca los
  correos de procuradores nuevos, los empareja (F1) y los presenta en la bandeja (F2); la
  persona confirma; se archiva (F3). Para el volumen del despacho (~7 correos/día), abrirla
  1-2 veces al día basta. Nadie deja el ordenador encendido esperando.
- **Solo la bandeja.** La miniapp expone **únicamente** la vista de intake (la pestaña
  «Bandeja de correos»), no el resto de la app del despacho (anonimizador, viabilidad, etc.).
- **Fuente de lectura = `procesal@`.** La app lee de `procesal@tyukhay.legal` (puerta única
  donde caen todos los correos de procuradores), igual que el robot actual (`BUZONES_DESPACHO`).
- **Cuenta de archivado = la del propio usuario.** El archivado (relate + adjuntar, F3) se
  ejecuta desde la cuenta del webmail **de quien usa la app** (Ana con la de Ana, etc.); todas
  reciben el correo por el reenvío, así que todas pueden. Esto **cierra la «decisión abierta 1»
  de F3** (no hay «cuenta fija»).

## 3. La bandeja es un visor compartido, no una cola que se vacía

Requisito de Nikolai (2026-07-19): **un correo archivado por Ana debe seguir apareciendo** en
las apps de Paola, Sergio y Nikolai, para que puedan **leerlo** — aunque ya conste relacionado.

- La app muestra **todos** los correos de procuradores, cada uno con su **estado a la vista**:
  - 🟠 **Pendiente** — nadie lo ha archivado; reclama acción.
  - ✅ **Archivado (→ expediente X)** — ya relacionado; **no desaparece**; cualquiera lo abre y
    lo lee.
- Cuando alguien archiva un correo, en las demás apps pasa de 🟠 a ✅ (sigue listado, legible).
- **La visibilidad no se recorta nunca**; lo que cambia es solo el estado.

## 4. Estado compartido sin servidor

- **«¿Archivado?»** es del **CRM**: si el correo ya está relacionado con un expediente, está
  archivado. Es la fuente de verdad y las tres apps la ven igual.
- Para no preguntar al CRM por cada correo constantemente, al archivar se marca además una
  **etiqueta en Gmail** sobre el correo en `procesal@` (que las tres apps leen) → estado
  compartido barato.
- **Anti-duplicado por comprobación, no por ocultación:** antes de archivar, la app comprueba
  en el CRM si el correo ya está relacionado. Si lo está, **no re-archiva** (lo muestra ✅).
  Así, aunque dos personas miren a la vez, solo se archiva una vez. *(Encaja con el
  anti-duplicado de F3 §5/§6 y del plan §4.)*

## 5. Auth (relación con el Track 1 de F3)

El modelo **facilita** el punto más delicado de F3 (obtener sesión del webmail): la app corre
en el contexto de la persona y **con su cuenta**, así que iniciar sesión en el webmail como
ella es mucho más natural que para un robot headless anónimo en un servidor. El detalle
técnico (login programático a Roundcube / reuso de sesión) se resuelve en el **spike del
Track 1**, ahora en modo «app de la persona». Fallback C (la persona da el último clic en el
webmail) sigue disponible si el login programático no sale.

## 6. Qué reutiliza (no se reconstruye)

- **F1** (`core/procurador_intake.py`, `core/llm_cloud.py`): leer + entender + emparejar.
- **F2** (`core/procurador_review.py`, `core/procurador_runner.py`, `core/procurador_search.py`):
  cola, tarjetas 🟢🟡🔴, combobox, terna de decisión. La miniapp **envuelve** la vista de
  bandeja existente; no la reescribe.
- **F3** (`core/procurador_relate.py`, a construir): el archivado al confirmar.

## 7. Coste

- **Económico: cero.** Usa Gmail, el CRM y (en el futuro, F6) el Drive que el despacho ya
  tiene. Sin servidor, sin infraestructura nueva, sin API de pago (más allá del LLM de
  céntimos/mes ya previsto en F1).
- **De construcción:** el grueso ya existe (F1/F2). Lo nuevo de este eje es (a) el disparo
  «al abrir», (b) exponer solo la bandeja, (c) el estado ✅/🟠 leído de CRM+Gmail, y (d) el
  **empaquetado** como app instalable. (a)-(c) son pequeños; (d) es el trabajo principal.

## 8. Aplazado (no se construye ahora)

- **Registro de autoría (quién archivó / cuándo).** El estado ✅/🟠 + expediente sale gratis de
  CRM+Gmail. El «por quién y cuándo» necesitaría un pequeño **registro compartido** (un fichero
  por persona en el Drive del despacho — append sin candados, todas leen los N ficheros). Es
  barato pero **no hace falta para el requisito de lectura**, y es justo lo que consume el
  **control de calidad (F6)**. → Se construye **con F6**, no antes.
- **Empaquetado definitivo** (formato del instalador Windows): al plan de implementación.

## 9. Decisiones abiertas

- **Formato de la miniapp:** empaquetar la vista Streamlit como app de escritorio (ejecutable
  con navegador embebido / Electron / equivalente). A decidir en el plan; no cambia el diseño.
- **Alcance de elementos (heredado de F3):** recomendación **judicial-first** (los procuradores
  actúan en pleitos); extrajudicial como interruptor, clientes fuera. Pendiente de tu OK.
- **Retención/orden de la lista:** cuántos archivados se muestran y con qué filtros (solo UI).

## 10. Higiene

Sin datos reales en este documento. Los correos y adjuntos siguen las reglas del despacho
(nada de PII en repo; el correo vive en Gmail/CRM, no en el árbol del proyecto).
