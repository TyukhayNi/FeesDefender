# Manifiesto y registro en el intake

Doble registro de los outputs (decisión del despacho), ejecutado por `scripts/registrar_outputs.py`.

## 1. Manifiesto `05_Procedimiento/_index.md`

Tabla append, idempotente por nombre de fichero. Es el índice del work-product del letrado en el
expediente (la carpeta `05_Procedimiento` estaba inerte; esta skill es su primer escritor).

```markdown
# 05_Procedimiento — Índice de work-product

| Fichero | Tipo | Perspectiva | Fecha | Fuentes | Estado |
|---|---|---|---|---|---|
| `MINUTA_AP_W-EJEMPLO01.docx` | minuta_ap | actora | 2026-06-11 | demanda; contestación; entrevista; chat | borrador |
| `SOLICITUD_PRUEBA_W-EJEMPLO01.docx` | solicitud_prueba | actora | 2026-06-11 | demanda; contestación | borrador |
```

Campos: `fichero` · `tipo` (`minuta_ap` | `solicitud_prueba`) · `perspectiva` (`actora` | `defensiva`)
· `fecha` · `fuentes` (documental de la que bebe) · `estado` (`borrador` | `revisado` | `presentado`).

> **Helper canónico.** `scripts/registrar_outputs.py` es una copia byte-idéntica del
> helper compartido `.claude/skills/_shared/registrar_outputs.py` (sincronizado por
> `scripts/sync_skill_helpers.py`). Exige el campo **`destino`** en cada output
> (la subcarpeta del expediente). Para la AP, ambos documentos van a `05_Procedimiento`.

## 2. Sección `## Navegación` de `00_Input/_caso.md`

Se añaden wikilinks idempotentes (no se duplica si ya están), respetando el frontmatter YAML:

```markdown
## Navegación

- [[minuta_ap]]
- [[solicitud_prueba]]
```

## Formato del `outputs.json` que consume el script

```json
[
  {"fichero": "MINUTA_AP_W-EJEMPLO01.docx", "tipo": "minuta_ap", "perspectiva": "actora",
   "destino": "05_Procedimiento",
   "fuentes": ["demanda", "contestación", "entrevista", "chat"], "wikilink": "minuta_ap",
   "estado": "borrador"},
  {"fichero": "SOLICITUD_PRUEBA_W-EJEMPLO01.docx", "tipo": "solicitud_prueba", "perspectiva": "actora",
   "destino": "05_Procedimiento",
   "fuentes": ["demanda", "contestación"], "wikilink": "solicitud_prueba", "estado": "borrador"}
]
```

## ⚠️ Aviso a FeesDefender (convención nueva)

`05_Procedimiento` era hasta ahora **funcionalmente inerte**: lo crea el scaffolding de
`core/case_manager.py` (en `CASO_SUBDIRS`) y lo barre `core/linker.py`, pero **ningún módulo del core
escribe ni lee en él**. Esta skill introduce dos convenciones nuevas que el core debería reconocer:

1. **`05_Procedimiento/_index.md`** como manifiesto del work-product del letrado.
2. **Wikilinks `[[minuta_ap]]` / `[[solicitud_prueba]]`** en la sección Navegación de `00_Input/_caso.md`.

**Acción recomendada (vía Claude Code, no desde Cowork):** añadir una entrada en
`docs/MEJORAS_FUTURAS.md` para que el core (a) reconozca/lea `_index.md` al listar el expediente y
(b) resuelva los nuevos wikilinks de Navegación. Texto propuesto para el backlog:

> **[skill preparacion-audiencia-previa] Manifiesto `05_Procedimiento/_index.md` + wikilinks de AP.**
> La skill de preparación de audiencia previa escribe el primer work-product en `05_Procedimiento`
> (minuta y solicitud de prueba) y lo registra en un manifiesto `_index.md` y en la Navegación de
> `_caso.md` (`[[minuta_ap]]`, `[[solicitud_prueba]]`). Disparador: primer caso con AP preparada por la
> skill. Pendiente: que `case_manager`/indexador reconozcan el manifiesto y resuelvan los wikilinks; y
> decidir si el manifiesto se normaliza a `_index.json` para consumo programático.

> Regla de promoción del repo: esto entra en `MEJORAS_FUTURAS.md` (backlog), y solo se promueve a
> `PLAN.md` cuando haya disparador concreto (un caso real que lo necesite), conforme a `CLAUDE.md`.
