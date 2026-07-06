# HANDOFF — Skill `engel-volkers` (continuación)

Fecha: 2026-05-20.

## Estado

**Fase A (investigación) — completada.** Borrador `engel-volkers-investigacion.md` (v2) entregado y revisado parcialmente contigo.

**Fase B (cristalización en `SKILL.md`) — pendiente.** No arranca hasta cerrar las decisiones del §A de este handoff.

## Archivos vivos

- `_skills_drafts/engel-volkers/engel-volkers-investigacion.md` — borrador v2 (este handoff lo acompaña).
- `_skills_drafts/engel-volkers/HANDOFF.md` — este documento.
- Fuentes consultadas:
  - 78 sesiones locales (lista completa en histórico de la sesión 2026-05-20).
  - `core/config.py` y `core/sudespacho_create.py` — fuente canónica de tipologías y notas.
  - `data/_plantillas/cuestionario_viabilidad.yaml` — cuestionario aplicable a 7 tipologías.
  - Organigrama E&V Iberia Julio 2025 (pptx aportado por el usuario).

## A. Decisiones que quedaron cerradas en la sesión 2026-05-20

1. Dos skills separadas: `engel-volkers` (cliente) y `mediacion-inmobiliaria` (materia, segunda fase).
2. Alcance temporal: todos los hilos.
3. Datos personales: regla general «solo cargos y funciones, no nombres» — con excepción a decidir en §B para puestos directivos estables.
4. Triggers: solo nombre exacto E&V y variantes ortográficas (no «agencia inmobiliaria» ni «mediación inmobiliaria»).
5. Ámbito territorial efectivo del despacho: España y Andorra. **Se descartan** EV MMC Portugal y EV Finance Spain.
6. Sociedades dentro del alcance: EV MMC SPAIN, S.L.U. (ID CRM 2, cliente propio por defecto) y ENGEL & VÖLKERS SPAIN, S.L. (ID 27, alternativo).
7. Tipologías oficiales confirmadas:
   - Actoras (7): BAD_DEBT, NEGATIVA_OFERTA, NEGATIVA_ARRAS, NEGATIVA_ESCRITURA, NEGATIVA_CONTRATO_ARRENDAMIENTO, VUELTA, INCUMPLIMIENTO_EXCLUSIVA.
   - Defensivas (4): RESPONSABILIDAD_PROFESIONAL, DEVOLUCION_RESERVA, LAU_20, DEVOLUCION_HONORARIOS.
   - Otros (1): OTROS.
   - Sub-categorías especiales como tags (no tipologías): FRANQUICIA, CONSULTORES.
8. Vía habitual en actoras: requerimiento extrajudicial → verbal (≤ 15.000 €) u ordinario (> 15.000 €). **Sin monitorio** como vía habitual. En VUELTA se prefiere ordinario aunque cuantía menor, por complejidad probatoria.
9. **«Ejes jurídicos» fuera de la skill cliente**: la fundamentación por tipología sale de `engel-volkers` y va íntegra a `mediacion-inmobiliaria` (materia). En la skill cliente, cada tipología queda con cinco campos: clave · tag CRM · supuesto fáctico (nota oficial) · cuestionario sí/no · vía habitual.

## B. Decisiones pendientes de confirmar contigo antes de cristalizar el SKILL.md

Las preguntas del §7 del borrador siguen abiertas, más una decimera nueva sobre nombres tras revisar el organigrama:

1. Política de E&V sobre proveedor cloud y residencia EEE para letrados externos.
2. Encaje del cliente propio CRM: ¿cuándo conviene salir del default EV MMC SPAIN al alternativo ENGEL & VÖLKERS SPAIN? (parece que cambio de razón social en encargo, franquicias, asuntos transversales del grupo).
3. LAU_20 post-Ley 12/2023: criterio del despacho ante arrendadores particulares no profesionales y régimen transitorio.
4. FRANQUICIA y CONSULTORES — ¿promover a tipología formal en `TIPOS_CASO_*` o mantener solo como tag CRM?
5. ¿Existe hoja de encargo marco de servicios jurídicos entre el despacho y E&V Iberia / Spain? Si existe, referenciarla.
6. Política de costas en defensivas: ¿el cliente asume costas si se pierde? ¿hay póliza de defensa jurídica que cubre?
7. Umbrales económicos para escalar/transigir en NEGATIVA_*.
8. Alcance del despacho sobre las 10 franquicias E&V en España: ¿se llevan asuntos donde la parte es franquiciada y no MMC?
9. Regla de nombres personales en la skill cliente (tras revisión del organigrama Iberia):
   - (a) Estricta: solo cargos.
   - (b) Excepción para puestos directivos estables (CEO Iberia, COO/Head of Operations & Franchises, Head of Legal Iberia, Legal Assistant Iberia Barcelona).
   - (c) Volcar el organigrama entero como anexo de la skill.
   - Recomendación dada: (b).

## C. Cambios pendientes de aplicar al MD cuando se reabra

Ajustes que quedaron acordados en chat pero no se vertieron todavía al MD (decisión del usuario: «no modifiques por el momento el MD»):

a) Reescritura del §1 «Identidad del cliente» con:
   - Tabla de sociedades del grupo y alcance del despacho.
   - Ámbito territorial efectivo (España + Andorra).
   - Mapa de Market Centers con HC y zonas comerciales (Sx, Rx, CC, PD).

b) Reescritura del §2 «Relación con el despacho» con interlocución por nivel:
   - a) Encargo y supervisión jurídica (Legal Iberia).
   - b) Comercial implicado en cada expediente (MC, Sales Director, Director de Zona, Team Assistant).
   - c) Operativa y franquicias (COO).
   - d) Recursos humanos y consultores (P&C, Recruiting).

c) Recorte del §3.1 quitando el bullet «Ejes jurídicos» de cada tipología (decisión cerrada §A.9). Los cinco campos a conservar por tipología: clave · tag CRM · supuesto fáctico · cuestionario · vía habitual.

d) Actualizar §5 (jurisprudencia) y §6.4 (ejes argumentales) marcándolos como **material destinado a la skill `mediacion-inmobiliaria`** y no a la skill cliente.

e) Actualizar el §8 «Separación cliente/materia» reflejando que los ejes jurídicos se trasladan por completo.

## D. Próximos pasos para la siguiente sesión

1. Repasar este HANDOFF.
2. Responder al §B (las nueve decisiones pendientes).
3. Aplicar al MD los cambios del §C.
4. Pasar a Fase B: redactar `SKILL.md` definitivo de `engel-volkers` siguiendo el formato de skills personales del despacho.
5. Decidir si se arranca también la skill `mediacion-inmobiliaria` en la misma tanda o se difiere.

## E. Cómo retomar en un hilo nuevo

Mensaje sugerido para arrancar el siguiente hilo:

> «Sigo trabajando en la skill `engel-volkers`. Lee `_skills_drafts/engel-volkers/HANDOFF.md` y el borrador en la misma carpeta. Vamos por la Fase B.»
