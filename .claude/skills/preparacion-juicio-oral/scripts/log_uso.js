// log_uso.js — auto-instrumentación de la skill (EVOLUCION.md, Fase 1).
//
// Módulo helper que cada generador invoca al finalizar para dejar una línea
// estructurada de telemetría en logs/uso.jsonl. También sirve a los formularios
// pre/post-juicio para escribir en logs/<ref>_pre.jsonl y logs/<ref>_post.jsonl.
//
// Diseño:
//   - log(entry)            -> añade una línea a logs/uso.jsonl
//   - logTo(file, entry)    -> añade una línea al archivo .jsonl indicado
//   - El timestamp `ts` (ISO 8601 UTC) se inyecta automáticamente si el caller
//     no lo aporta; `skill` se rellena por defecto si falta.
//   - El directorio logs/ se crea si no existe.
//   - Es best-effort: si el log falla, avisa por stderr pero NUNCA lanza, para
//     no romper la generación del .docx (la telemetría no debe degradar el output).
//
// El esquema de cada archivo está documentado en logs/README.md.

const fs = require("fs");
const path = require("path");

const SKILL = "preparacion-juicio-oral";

// Resolución del directorio de logs (espejo de _shared/registrar_uso.py):
//   1. FEESDEFENDER_SKILL_LOGS -> <base>/<skill>
//   2. repo detectado (pyproject.toml subiendo) -> <repo>/data/_skill_logs/<skill>
//   3. fallback portable -> ../logs de la propia skill
function resolveLogsDir() {
  const env = process.env.FEESDEFENDER_SKILL_LOGS;
  if (env) return path.join(env, SKILL);
  let dir = __dirname;
  for (let i = 0; i < 8; i++) {
    if (fs.existsSync(path.join(dir, "pyproject.toml"))) {
      return path.join(dir, "data", "_skill_logs", SKILL);
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return path.join(__dirname, "..", "logs");
}

const LOGS_DIR = resolveLogsDir();

// Lee `version:` del frontmatter de ../SKILL.md (def. "0.0").
function readVersion() {
  try {
    const txt = fs.readFileSync(path.join(__dirname, "..", "SKILL.md"), "utf8");
    let inFm = false;
    for (const line of txt.split(/\r?\n/)) {
      if (line.trim() === "---") { if (inFm) break; inFm = true; continue; }
      if (inFm && /^version:/i.test(line)) {
        return line.split(":")[1].trim().replace(/^["']|["']$/g, "") || "0.0";
      }
    }
  } catch (e) { /* best-effort */ }
  return "0.0";
}

const VERSION = readVersion();

function ensureLogsDir() {
  if (!fs.existsSync(LOGS_DIR)) {
    fs.mkdirSync(LOGS_DIR, { recursive: true });
  }
}

// Añade una línea JSON al archivo .jsonl indicado dentro de logs/.
// Devuelve true si escribió, false si hubo error (best-effort).
function logTo(file, entry) {
  try {
    ensureLogsDir();
    const record = Object.assign(
      { ts: new Date().toISOString(), skill: SKILL, version: VERSION },
      entry || {}
    );
    fs.appendFileSync(path.join(LOGS_DIR, file), JSON.stringify(record) + "\n", "utf8");
    return true;
  } catch (e) {
    process.stderr.write("[log_uso] aviso: no se pudo registrar telemetría (" + e.message + ")\n");
    return false;
  }
}

// Atajo para el log de uso general (uso.jsonl).
function log(entry) {
  return logTo("uso.jsonl", entry);
}

module.exports = { log, logTo, LOGS_DIR, SKILL };
