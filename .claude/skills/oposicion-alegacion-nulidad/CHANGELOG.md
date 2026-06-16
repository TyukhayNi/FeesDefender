# CHANGELOG — `oposicion-alegacion-nulidad`

> Registro de cambios de la skill, en orden cronológico inverso (lo más reciente arriba).
> Formato ligero: fecha (AAAA-MM-DD) + qué cambió, una línea por cambio.

## 2026-06-16 — Telemetría canónica + drift de vías (v1.5.2)

- **Telemetría unificada**: retirado el logger bespoke `scripts/log_uso.py`; la skill pasa a usar el helper canónico `scripts/registrar_uso.py` (store central `data/_skill_logs/`, esquema con métricas dentro de `metricas`). Skill añadida al tuple `_TARGETS` de `scripts/sync_skill_helpers.py` → recibe los 4 helpers canónicos. *Evidencia*: handoff de homogeneización de skills (PLAN.md, Ola 1).
- **Corregido el drift de vías** (3 → 4) en el logger, `EVOLUCION.md` (Fase 1) y `logs/README.md`: A nulidad absoluta · B vicio del consentimiento · C incorporación · D contenido/abusividad, alineado con el cuerpo del `SKILL.md`.

## 2026-06-16 — PDF oficiales completos (v1.5.1)

- Incorporados a `sentencias_oficiales/` los **11 PDF del CGPJ** que faltaban (localizados en Descargas): 1001/2001, 1296/2006, 224/1999, 172/2018, 339/2016, 769/2014, 558/2019, SAP Oviedo 189/2018, SAP Cantabria 242/2019, SAP Granada 68/2018, SAP Madrid 281/2018. Nombre normalizado, sin duplicados, `_TEMP` retirado de la 558/2019.
- `archivo_oficial` actualizado en las 11 entradas del índice → **las 24 resoluciones CENDOJ ya tienen PDF oficial** (las 13 TJUE siguen por ECLI+enlace). README regenerado; integridad verificada con el consolidador.

## 2026-06-16 — Cosecha compartida en Drive (v1.5)

- **Estructura en el Shared Drive *DESPACHO - PRODUCCION*** → `Biblioteca_Skills/oposicion-alegacion-nulidad/` con `cosecha/`, `candidatas_verbatim/` y `_LEEME.md`.
- **Push por conector Google Drive** (Fase 6, paso 7): cada sesión sube **un fichero `.json` propio** a `cosecha/` (sin colisiones; Drive no permite *append* atómico) y las verbatim sugeridas a `candidatas_verbatim/`. IDs en `scripts/drive_config.json`.
- **Recogida bajo demanda por el mantenedor**: el agente descarga las carpetas vía conector y corre `scripts/consolidar_biblioteca.py --cosecha-dir` (adaptado para leer una carpeta de ficheros de sesión; nuevo `--candidatas-dir` con dedup). Verificación y promoción siguen siendo manuales y versionadas.

## 2026-06-16 — Biblioteca de jurisprudencia + control de artefactos (v1.4)

- **Reestructura de `references/jurisprudencia/`** en `sentencias_oficiales/` (13 PDF del CGPJ, para aportar) y `sentencias_md/` (37 .md de trabajo: verbatim + fichas), mismo basename para los pares PDF/md.
- **`indice_jurisprudencia.json`** — control de artefactos y **fuente única de verdad** (id, ECLI, ROJ/CELEX, `aplica` si/no/parcial, `tipo_md` verbatim/ficha, rutas, `usado_en`, `verificacion`). 37 entradas; STS 843/2006 y 123/2020 = `no`, SAP Madrid 50/2014 = `parcial`.
- **README.md generado** desde el índice (`scripts/generar_readme_jurisprudencia.py`); puntero de uso en `SKILL.md` (operativa→`sentencias_md`; aportación→PDF/enlace).
- **Mecanismo de cosecha distribuido**: `logs/cosecha.jsonl` (append-only, en producción en el Drive compartido); paso 7 de cierre en Fase 6; `scripts/consolidar_biblioteca.py` (consolidación supervisada por el mantenedor: integridad, ECLI nuevas a verificar, avisos aplica=no/parcial, huérfanas). Descarga/verificación/promoción y mejora de la skill: manuales y versionadas.

## 2026-06-16 — Clasificación en 4 vías + cruce de 3 handoffs (v1.3)

Integrado el diff B1–B6 tras valorar tres revisiones externas y **verificar toda la jurisprudencia** (CENDOJ + EUR-Lex):

- **B1 — Cuatro vías** (SKILL.md Fase 2 + Regla 2): añadida la **Vía A nulidad absoluta** (1261, 1276 simulación, 1271-1275, 6.3 CC con matiz *ultima ratio* y STS 558/2019; inexistencia subsumida; forma *ad solemnitatem*). Tabla de la Regla 2 ampliada a 4 vías con ejes **cauce** y **de oficio** separados.
- **B2 — Anulabilidad**: añadida **confirmación/sanación** (arts. 1309-1313 CC; insanable la nulidad radical, 1310); cauce matizado (pronunciamiento constitutivo exige acción/reconvención). Error obstativo como frontera porosa.
- **B3 — Incorporación**: separado el **ámbito subjetivo** (LCGC todo adherente / 80.1 TRLGDCU solo consumidor); efecto "no incorporada", no "nula".
- **B4 — Contenido**: corregida la cita de la **no integración** → autoridad **C-618/10 y C-488/11**; **Kásler C-26/13 reposicionada como excepción** (SEXTO + módulo).
- **B5 — Regla 1 bis**: añadida la cadena y los **límites del control de oficio** (Océano, Pannon, Aziz, Banif Plus, Cofidis, Banco Primus, Lintner), con ECLI.
- **B6 — Deslindes**: nueva sección (rescisión, resolución 1124 / *exceptio non adimpleti*; nulidad parcial como regla de cierre en SEXTO).
- **Verificación CENDOJ/EUR-Lex**: incorporadas ECLI verificadas (241/2013 ES:TS:2013:1916; 840/2013 ES:TS:2014:354; 367/2017 ES:TS:2017:2244; 266/2008, 503/2014, 560/2014; SAP Valencia 248/2005 ES:APV:2005:2680). **Retirada la STS 123/2020** (no es de representación). **Reencuadrada la SAP Madrid 50/2014** (mediación/mandato verbal, parcial). 13 asuntos TJUE archivados (3 verbatim + 10 fichas).
- Descartes razonados: estructura de 8 categorías (sobre-clasifica), fuentes terciarias (blogs/TFG) y citas sin ECLI verificable.

## 2026-06-16 — ECLIs del módulo de honorarios (v1.2.1)

- **4 SAP de honorarios de mediación con ECLI cotejado** e incorporadas al módulo y al índice: SAP Oviedo 189/2018 (ES:APO:2018:1147), SAP Cantabria 242/2019 (ES:APS:2019:267), SAP Granada 68/2018 (ES:APGR:2018:329), SAP Madrid 281/2018 (ES:APM:2018:8959). Textos verificados archivados.
- **ECLIs completadas por deriv