// schedule_post_juicio.js — programa la revisión post-juicio (EVOLUCION.md, Fase 1).
//
// Calcula la fecha de disparo (fecha_juicio + 7 días) y construye el descriptor
// de tarea programada en el formato que espera la skill `schedule` / la herramienta
// scheduled-tasks de Claude Code:
//     { taskId, fireAt (ISO 8601 con offset), description, prompt }
//
// Un script Node no puede crear por sí mismo la tarea en el harness de Claude
// (eso vive a nivel de la app, no del proceso node). Por eso este helper:
//   1) Deja el descriptor en logs/<ref>_schedule.json (registro / cola).
//   2) Registra la intención en logs/uso.jsonl (telemetría).
//   3) Imprime por stdout la instrucción lista para que el letrado la pegue
//      en Claude Code / Cowork e invoque la skill `schedule` manualmente.
//
// Uso: node schedule_post_juicio.js <caso.json> [hora_local=09:00] [dias=7]

const fs = require("fs");
const path = require("path");
const logUso = require("./log_uso");

// Offset local de España peninsular (Europe/Madrid): CEST (+02:00) entre el último
// domingo de marzo y el último domingo de octubre; CET (+01:00) el resto del año.
function ultimoDomingo(year, month /* 0-index */) {
  const d = new Date(Date.UTC(year, month + 1, 0)); // último día del mes
  return d.getUTCDate() - d.getUTCDay();
}
function offsetMadrid(year, month /* 0-index */, day) {
  const inicioDST = ultimoDomingo(year, 2);   // marzo
  const finDST = ultimoDomingo(year, 9);      // octubre
  let dst;
  if (month < 2 || month > 9) dst = false;
  else if (month > 2 && month < 9) dst = true;
  else if (month === 2) dst = day >= inicioDST;
  else /* month === 9 */ dst = day < finDST;
  return dst ? "+02:00" : "+01:00";
}

function addDays(isoDate, days) {
  const [y, m, d] = isoDate.split("-").map(Number);
  const base = new Date(Date.UTC(y, m - 1, d));
  base.setUTCDate(base.getUTCDate() + days);
  return {
    y: base.getUTCFullYear(),
    m: base.getUTCMonth(), // 0-index
    d: base.getUTCDate(),
  };
}

function pad(n) { return String(n).padStart(2, "0"); }

function main() {
  const casoPath = process.argv[2];
  const horaLocal = process.argv[3] || "09:00";
  const dias = parseInt(process.argv[4] || "7", 10);
  if (!casoPath) {
    console.error("Uso: node schedule_post_juicio.js <caso.json> [hora_local=09:00] [dias=7]");
    process.exit(1);
  }
  const caso = JSON.parse(fs.readFileSync(casoPath, "utf8"));
  const ref = caso.ref || "SIN-REF";

  // fecha_juicio puede venir como "AAAA-MM-DD" o "AAAA-MM-DD HH:MM".
  const fechaJuicioRaw = caso.fecha_juicio;
  if (!fechaJuicioRaw) {
    console.error("El caso no tiene 'fecha_juicio'; no se puede programar la revisión.");
    process.exit(1);
  }
  const fechaJuicio = String(fechaJuicioRaw).split(" ")[0].split("T")[0];

  const t = addDays(fechaJuicio, dias);
  const [hh, mm] = horaLocal.split(":");
  const off = offsetMadrid(t.y, t.m, t.d);
  const fireAt = `${t.y}-${pad(t.m + 1)}-${pad(t.d)}T${pad(+hh)}:${pad(+mm)}:00${off}`;

  const taskId = ("post-juicio-" + ref).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

  const prompt = [
    `Revisión post-juicio del asunto ${ref} (skill preparacion-juicio-oral, Fase 1).`,
    `El juicio se celebró el ${fechaJuicio}. Han pasado ${dias} días.`,
    ``,
    `Abre el formulario templates/checklist_post_juicio.md y pídele al letrado que lo`,
    `responda campo a campo (5 campos: entregables usados en sala, pregunta no prevista,`,
    `respuesta de retirada que falló, bloque largo o corto, valoración del acto sin entrar`,
    `en sentencia).`,
    ``,
    `Guarda las respuestas como una línea JSON en logs/${ref}_post.jsonl usando`,
    `log_uso.logTo("${ref}_post.jsonl", { ... }) con el esquema documentado en logs/README.md`,
    `(fase: "post").`,
  ].join("\n");

  const descriptor = {
    taskId,
    fireAt,
    description: `Revisión post-juicio ${ref} (${dias} días tras el acto).`,
    prompt,
  };

  // 1) Descriptor en logs/<ref>_schedule.json
  if (!fs.existsSync(logUso.LOGS_DIR)) fs.mkdirSync(logUso.LOGS_DIR, { recursive: true });
  const descPath = path.join(logUso.LOGS_DIR, `${ref}_schedule.json`);
  fs.writeFileSync(descPath, JSON.stringify(descriptor, null, 2) + "\n", "utf8");

  // 2) Telemetría de la intención
  logUso.log({
    ref,
    accion: "schedule_post_juicio",
    fecha_juicio: fechaJuicio,
    fire_at: fireAt,
    task_id: taskId,
  });

  // 3) Instrucción para invocación manual
  console.log("Descriptor de tarea programada generado:");
  console.log("  archivo : " + descPath);
  console.log("  taskId  : " + taskId);
  console.log("  fireAt  : " + fireAt + "  (fecha_juicio " + fechaJuicio + " + " + dias + " días)");
  console.log("");
  console.log("Para activarla, en Claude Code / Cowork invoca la skill `schedule` (o la");
  console.log("herramienta scheduled-tasks) con estos campos. Instrucción lista para pegar:");
  console.log("");
  console.log("  /schedule  Programa una tarea de un solo disparo (fireAt=" + fireAt + ")");
  console.log("  con taskId \"" + taskId + "\" y el prompt almacenado en " + path.basename(descPath) + ".");
}

main();
