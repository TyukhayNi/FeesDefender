// gen_interrogatorio.js
// Genera el .docx de interrogatorio en MODO SOPORTE LETRADO.
// Doble salida segun rol del testigo:
//   - <Apellido>_letrado.docx: version completa (preguntas + RE + RD + Nota + caja anticipacion)
//   - <Apellido>_testigo.docx: solo preguntas + disclaimer (cuando aplica)
//
// Regla por defecto: version testigo se genera para roles "directo" y "neutro"; no para "cruzado" y "problematico".
// Flag opcional en el JSON: generar_version_testigo (boolean) sobrescribe la regla por defecto.
//
// Uso: node gen_interrogatorio.js <interrogatorio.json> <salida_base.docx>
// El generador produce <salida_base>_letrado.docx y, si aplica, <salida_base>_testigo.docx.

const fs = require("fs");
const path = require("path");
const { Document, Packer, AlignmentType } = require("docx");
const F = require("./format_constants");
const logUso = require("./log_uso");

const TITULO_POR_ROL = {
  directo: "INTERROGATORIO DIRECTO",
  cruzado: "INTERROGATORIO CRUZADO",
  neutro: "INTERROGATORIO",
  problematico: "INTERROGATORIO",
};

const DEFAULT_TESTIGO_BY_ROL = {
  directo: true,
  neutro: true,
  cruzado: false,
  problematico: false,
};

const DISCLAIMER = "Las preguntas que figuran a continuacion son orientativas y se le facilitan unicamente para que pueda prepararse con tranquilidad al acto del juicio. No tiene obligacion de contestarlas en los terminos en que aqui se anticipan: usted declarara libre y exclusivamente conforme a su conocimiento personal de los hechos, con la obligacion de decir verdad que le impone el articulo 365 LEC. Si alguna pregunta no la entiende, no recuerda la respuesta exacta o no le consta, asi lo manifestara al tribunal. El presente documento es confidencial. Se le ruega no difundirlo ni compartirlo con terceros.";

function buildLetrado(data) {
  const children = [];
  const titulo = TITULO_POR_ROL[data.testigo.rol] || "INTERROGATORIO";
  const nombre = (data.testigo.tratamiento ? data.testigo.tratamiento + " " : "") + data.testigo.nombre;
  children.push(F.PTitle(titulo + " — " + nombre));

  if (data.intro) {
    children.push(F.P(data.intro, { italic: true, before: 0, after: 120 }));
  }

  (data.bloques || []).forEach(b => {
    children.push(F.PH1(b.titulo));
    (b.preguntas || []).forEach(q => {
      children.push(F.Q(q.n, q.texto, q.exhibir));
      if (q.RE)   children.push(F.RE(q.RE));
      if (q.RD)   children.push(F.RD(q.RD));
      if (q.Nota) children.push(F.Nota(q.Nota));
    });
  });

  if (data.anticipacion && data.anticipacion.length > 0) {
    children.push(F.PH1("Anticipacion a repreguntas del adversario"));
    const antiParas = [];
    antiParas.push(F.P("ANTICIPACION A REPREGUNTAS — solo si el adversario abre el frente.", { bold: true, before: 60, after: 40 }));
    data.anticipacion.forEach(item => {
      if (item.label === "RE")        antiParas.push(F.RE(item.texto));
      else if (item.label === "RD")   antiParas.push(F.RD(item.texto));
      else                            antiParas.push(F.Nota(item.texto));
    });
    children.push.apply(children, F.BoxParagraphs(antiParas));
  }
  return children;
}

function buildTestigo(data) {
  const children = [];
  const nombre = (data.testigo.tratamiento ? data.testigo.tratamiento + " " : "") + data.testigo.nombre;
  children.push(F.PTitle("Preguntas orientativas — " + nombre));
  children.push(F.PCite(DISCLAIMER));

  (data.bloques || []).forEach(b => {
    children.push(F.PH1(b.titulo));
    (b.preguntas || []).forEach(q => {
      children.push(F.QSimple(q.n, q.texto, q.exhibir));
    });
  });
  return children;
}

function makeDoc(caso, children) {
  const headerTxt = caso.encabezado_pagina || "";
  const footerExtra = caso.fecha_juicio ? ("Juicio " + caso.fecha_juicio) : null;
  return new Document({
    creator: caso.autor || "Despacho",
    title: "Interrogatorio - " + (caso.ref || ""),
    styles: { default: { document: { run: { font: F.FONT, size: F.FS_BODY } } } },
    sections: [{
      properties: { page: F.PAGE },
      headers: { default: F.buildHeader(headerTxt) },
      footers: { default: F.buildFooter(footerExtra) },
      children: children,
    }],
  });
}

function main() {
  const dataPath = process.argv[2];
  const outBase = process.argv[3] || "PREGUNTAS.docx";
  if (!dataPath) {
    console.error("Uso: node gen_interrogatorio.js <interrogatorio.json> <salida_base.docx>");
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));

  // Determinar version testigo
  const rol = data.testigo && data.testigo.rol || "directo";
  const flagExplicit = (data.generar_version_testigo !== undefined);
  const genTestigo = flagExplicit ? !!data.generar_version_testigo : !!DEFAULT_TESTIGO_BY_ROL[rol];

  // Salida letrado
  const baseDir = path.dirname(outBase);
  const baseName = path.basename(outBase, path.extname(outBase));
  const outLetrado = path.join(baseDir, baseName + "_letrado.docx");
  const outTestigo = path.join(baseDir, baseName + "_testigo.docx");

  const tareas = [];

  const docLetrado = makeDoc(data, buildLetrado(data));
  tareas.push(Packer.toBuffer(docLetrado).then(buf => {
    fs.writeFileSync(outLetrado, buf);
    console.log("OK letrado:", outLetrado);
    return path.basename(outLetrado);
  }));

  if (genTestigo) {
    const docTestigo = makeDoc(data, buildTestigo(data));
    tareas.push(Packer.toBuffer(docTestigo).then(buf => {
      fs.writeFileSync(outTestigo, buf);
      console.log("OK testigo:", outTestigo);
      return path.basename(outTestigo);
    }));
  } else {
    console.log("(version testigo omitida para rol " + rol + ")");
  }

  // Telemetría: un único registro tras materializarse todos los .docx del testigo.
  Promise.all(tareas).then(archivos => {
    const nPreguntas = (data.bloques || []).reduce((acc, b) => acc + (b.preguntas || []).length, 0);
    logUso.log({
      ref: data.ref || null,
      accion: "gen_interrogatorio",
      archivos: archivos,
      testigo: (data.testigo && data.testigo.nombre) || null,
      rol: rol,
      version_testigo: genTestigo,
      bloques: (data.bloques || []).length,
      preguntas: nPreguntas,
      anticipacion: (data.anticipacion || []).length,
    });
  });
}

main();
