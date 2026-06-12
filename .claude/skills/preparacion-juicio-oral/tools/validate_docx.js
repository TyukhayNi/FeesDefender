// validate_docx.js — validador OPC/OOXML ligero para los .docx generados.
// No forma parte de la skill empaquetada: es utilería de QA/regresión.
// Uso: node validate_docx.js <archivo1.docx> [archivo2.docx ...]
// Verifica: (1) es un ZIP/OPC legible; (2) contiene las partes obligatorias
// ([Content_Types].xml y word/document.xml); (3) cada parte XML es well-formed.
// Salida: línea "OK" o "FAIL" por archivo y código de salida !=0 si alguno falla.

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

// Descompresión mínima de ZIP sin dependencias: usamos el propio Node para
// inflar. docx empaqueta con DEFLATE; zlib.inflateRawSync sirve por entrada.
const zlib = require("zlib");

function readZipEntries(buf) {
  // Localiza el End Of Central Directory (EOCD).
  const entries = {};
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("EOCD no encontrado (no es un ZIP válido)");
  const cdCount = buf.readUInt16LE(eocd + 10);
  let off = buf.readUInt32LE(eocd + 16);
  for (let n = 0; n < cdCount; n++) {
    if (buf.readUInt32LE(off) !== 0x02014b50) throw new Error("cabecera de central dir corrupta");
    const method = buf.readUInt16LE(off + 10);
    const compSize = buf.readUInt32LE(off + 20);
    const nameLen = buf.readUInt16LE(off + 28);
    const extraLen = buf.readUInt16LE(off + 30);
    const commentLen = buf.readUInt16LE(off + 32);
    const lho = buf.readUInt32LE(off + 42);
    const name = buf.toString("utf8", off + 46, off + 46 + nameLen);
    // Cabecera local para saltar a los datos
    const lhNameLen = buf.readUInt16LE(lho + 26);
    const lhExtraLen = buf.readUInt16LE(lho + 28);
    const dataStart = lho + 30 + lhNameLen + lhExtraLen;
    const comp = buf.slice(dataStart, dataStart + compSize);
    let data;
    if (method === 0) data = comp;
    else if (method === 8) data = zlib.inflateRawSync(comp);
    else throw new Error("método de compresión no soportado: " + method);
    entries[name] = data;
    off += 46 + nameLen + extraLen + commentLen;
  }
  return entries;
}

function isWellFormedXml(str) {
  // Validador XML ligero: balanceo de etiquetas. Suficiente para detectar
  // XML roto generado por el .docx (etiquetas sin cerrar, etc.).
  const tagRe = /<\/?([a-zA-Z_][\w:.-]*)([^>]*?)(\/?)>/g;
  const stack = [];
  let m;
  let body = str.replace(/<\?[\s\S]*?\?>/g, "").replace(/<!--[\s\S]*?-->/g, "");
  while ((m = tagRe.exec(body)) !== null) {
    const full = m[0];
    const name = m[1];
    const selfClose = m[3] === "/" || /\/\s*>$/.test(full);
    if (full.startsWith("</")) {
      if (stack.pop() !== name) return false;
    } else if (!selfClose) {
      stack.push(name);
    }
  }
  return stack.length === 0;
}

const REQUIRED = ["[Content_Types].xml", "word/document.xml"];

function validate(file) {
  const buf = fs.readFileSync(file);
  const entries = readZipEntries(buf);
  for (const req of REQUIRED) {
    if (!entries[req]) return { ok: false, msg: "falta parte obligatoria: " + req };
  }
  for (const name of Object.keys(entries)) {
    if (name.endsWith(".xml") || name.endsWith(".rels")) {
      const txt = entries[name].toString("utf8");
      if (!isWellFormedXml(txt)) return { ok: false, msg: "XML mal formado: " + name };
    }
  }
  const nParts = Object.keys(entries).length;
  return { ok: true, msg: nParts + " partes, document.xml " + entries["word/document.xml"].length + " bytes" };
}

function main() {
  const files = process.argv.slice(2);
  if (files.length === 0) { console.error("Uso: node validate_docx.js <archivo.docx> ..."); process.exit(2); }
  let allOk = true;
  for (const f of files) {
    try {
      const r = validate(f);
      console.log((r.ok ? "OK  " : "FAIL") + "  " + path.basename(f) + "  — " + r.msg);
      if (!r.ok) allOk = false;
    } catch (e) {
      console.log("FAIL  " + path.basename(f) + "  — " + e.message);
      allOk = false;
    }
  }
  process.exit(allOk ? 0 : 1);
}

main();
