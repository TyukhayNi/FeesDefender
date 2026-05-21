# Instalación de la skill + agente CENDOJ

Tres archivos a instalar:

```
cendoj-descarga/
├── SKILL.md          ← manual operativo (skill)
└── cendoj-bot.md     ← definición del agente
```

## Paso 1 — Cerrar Claude Desktop

Cierra completamente la aplicación (icono de la bandeja del sistema → Salir, no solo cerrar ventana). Esto evita que el sincronizador interno sobrescriba lo que vas a copiar.

## Paso 2 — Instalar la skill

Pega esto en la barra de direcciones del Explorador de Windows:

```
%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\skills-plugin\6c9fdc80-48fa-4623-ab08-dae679510ce5\79faa18e-1db3-4cf2-bbba-9a595e4e4b28\skills
```

**Importante:** la ruta empieza por `%LOCALAPPDATA%` (que es `C:\Users\<usuario>\AppData\Local`), NO por `%APPDATA%`. Es porque Claude Desktop está instalado como aplicación MSIX (Microsoft Store) y guarda sus datos en `Local\Packages\...`, no en `Roaming\Claude\` como hace la versión clásica.

Es la misma carpeta donde tienes `escritos-judiciales/` y `preparacion-litigio-civil/`.

Mueve **toda la carpeta** `cendoj-descarga/` (con `SKILL.md` dentro) ahí desde tu Downloads.

## Paso 3 — Instalar el agente

Los agentes (subagentes) van en una carpeta paralela a `skills/`. Pega en el Explorador:

```
%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\skills-plugin\6c9fdc80-48fa-4623-ab08-dae679510ce5\79faa18e-1db3-4cf2-bbba-9a595e4e4b28\agents
```

Si la carpeta `agents/` no existe, créala manualmente (sube un nivel hasta `79faa18e-...\` y haz Nuevo → Carpeta → `agents`).

Mueve **solo el archivo** `cendoj-bot.md` ahí.

## Paso 4 — Reabrir Claude

Abre Claude Desktop. La próxima conversación que inicies tendrá:

- `cendoj-descarga` en la lista de `available_skills`.
- `cendoj-bot` en los tipos de subagente que puedo invocar.

## Cómo invocar al agente

En cualquier conversación, basta con frases como:

- *«Búscame estas sentencias en CENDOJ: …»* + lista de referencias.
- *«Descárgame los PDFs oficiales de estas referencias de Sepin»* + enlaces.
- *«Localiza la SAP Madrid Sec. 13 de 2-7-2018»*.

Yo detectaré que es un encargo para el agente CENDOJ y lo lanzaré. Tú verás:

1. Un breve resumen mío del encargo.
2. El agente trabajando en su contexto aislado (verás actividad en tu Chrome).
3. Su informe final con tabla + enlaces.

Tu chat principal queda limpio de los pasos intermedios.

## Si no aparece el agente en `available_skills` tras reabrir

Posibles causas:

1. **Carpeta `agents/` en el sitio equivocado.** Claude Desktop puede buscar agentes en `~/.claude/agents/` en lugar de la carpeta del skills-plugin. Prueba a copiarlo también a:
   ```
   %USERPROFILE%\.claude\agents\cendoj-bot.md
   ```

2. **Versión de Claude Desktop sin soporte de subagentes en Cowork mode.** Si la versión instalada no admite agentes personalizados en modo Cowork, todavía puedes usar la skill: invocaré el procedimiento yo mismo en la conversación principal (con la skill como guía). Es funcionalmente equivalente, solo que el chat se llena de los pasos intermedios.

3. **Sincronizador todavía no recargado.** A veces tarda 30-60 s tras reabrir. Inicia una conversación nueva tras un minuto.

## Mantenimiento

- **Actualizaciones del manual.** Cuando descubras una nueva estrategia útil (por ejemplo, una base privada nueva, un código ROJ de una provincia que no esté en la tabla, una palabra clave que funciona mejor para un tema), edita `SKILL.md` directamente. La próxima invocación lo verá.
- **Cambios en el comportamiento del agente.** Si quieres ajustar tono, exigencias o flujo de trabajo, edita `cendoj-bot.md`.
- **Versionado.** No es estrictamente necesario versionarlo en Git, pero si lo haces, ambos archivos son markdown puro y diffean bien.

## Estructura final esperada

```
%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\6c9fdc80-...\79faa18e-...\
├── skills\
│   ├── escritos-judiciales\
│   ├── preparacion-litigio-civil\
│   └── cendoj-descarga\
│       └── SKILL.md
└── agents\
    └── cendoj-bot.md
```
