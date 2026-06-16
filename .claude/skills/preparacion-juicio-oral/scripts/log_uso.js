// log_uso.js — shim de telemetría: delega en el helper canónico registrar_uso.py.
//
// Antes esta skill tenía su propio logger JS (esquema + versión + escritura
// duplicados respecto a _shared/registrar_uso.py). Ahora la telemetría se unifica
// en registrar_uso.py (bundleado en este scripts/), fuente única del esquema y del
// store central data/_skill_logs/<skill>/. Este módulo conserva la API previa
// (log / logTo) para no tocar los generadores ni schedule_post_juicio.js, pero
// reenvía cada evento al helper Python vía child_process.
//
// Sigue exportando LOGS_DIR — schedule_post_juicio.js lo usa para escribir el
// descriptor <ref>_schedule.json, que no es telemetría y registrar_uso.py no
// emite — y SKILL. Es best-effort: si el registro falla, avisa por stderr pero
// NUNCA lanza (la telemetría no debe degradar la generación del .docx).
//
// Esquema de cada archivo: ver logs/README.md (las métricas específicas de cada
// evento viajan dentro de `metricas`).

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const SKILL = "preparacion-juicio-oral";
const REGISTRAR = path.join(__dirname, "registrar_uso.py");

// Resolución del store central (espejo de registrar_uso.log_dir, necesaria aquí
// porque schedule_post_juicio.js escribe <ref>_schedule.json en este directorio):
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

// Lanza `python registrar_uso.py <skill> <ref> <accion> [--archivos ...]
// [--metricas JSON] --fase <fase>`. Prueba intérpretes hasta dar con uno
// disponible (python3 en el servidor, python en Windows). Best-effort.
function delegar(ref, accion, archivos, metricas, fase) {
  const args = [REGISTRAR, SKILL, ref == null ? "" : String(ref), accion || "uso"];
  if (Array.isArray(archivos) && archivos.length) {
    args.push("--archivos", ...archivos.map(String));
  }
  if (metricas && Object.keys(metricas).length) {
    args.push("--metricas", JSON.stringify(metricas));
  }
  args.push("--fase", fase);
  for (const py of ["python3", "python"]) {
    const r = spawnSync(py, args, { encoding: "utf8" });
    if (r.error && r.error.code === "ENOENT") continue; // intérprete ausente: prueba el siguiente
    if (r.status !== 0) {
      process.stderr.write("[log_uso] aviso: registrar_uso.py salió con código " + r.status + "\n");
    }
    return r.status === 0;
  }
  process.stderr.write("[log_uso] aviso: no se encontró intérprete de Python para la telemetría\n");
  return false;
}

// Separa el evento {ref, accion, archivos, ...resto} en los argumentos del CLI;
// `resto` se convierte en el objeto `metricas` del esquema canónico.
function partir(entry) {
  const { ref = null, accion = null, archivos = null, ...metricas } = entry || {};
  return { ref, accion, archivos, metricas };
}

// API previa: log(entry) -> evento de uso (uso.jsonl).
function log(entry) {
  try {
    const { ref, accion, archivos, metricas } = partir(entry);
    return delegar(ref, accion, archivos, metricas, "uso");
  } catch (e) {
    process.stderr.write("[log_uso] aviso: no se pudo registrar telemetría (" + e.message + ")\n");
    return false;
  }
}

// API previa: logTo("<ref>_pre.jsonl" | "<ref>_post.jsonl", entry) -> checklist
// pre/post. La fase y, si falta, la ref se derivan del nombre de archivo.
function logTo(file, entry) {
  try {
    const { ref, accion, archivos, metricas } = partir(entry);
    const base = path.basename(file || "");
    let fase = "uso";
    let refDeArchivo = base.replace(/\.jsonl$/i, "");
    if (/_post\.jsonl$/i.test(base)) { fase = "post"; refDeArchivo = base.replace(/_post\.jsonl$/i, ""); }
    else if (/_pre\.jsonl$/i.test(base)) { fase = "pre"; refDeArchivo = base.replace(/_pre\.jsonl$/i, ""); }
    return delegar(ref || refDeArchivo, accion || "checklist", archivos, metricas, fase);
  } catch (e) {
    process.stderr.write("[log_uso] aviso: no se pudo registrar telemetría (" + e.message + ")\n");
    return false;
  }
}

module.exports = { log, logTo, LOGS_DIR, SKILL };
