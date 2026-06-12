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
const LOGS_DIR = path.join(__dirname, "..", "logs");

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
      { ts: new Date().toISOString(), skill: SKILL },
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
