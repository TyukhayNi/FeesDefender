// gen_conclusiones.js
// Genera el documento único de conclusiones en modo SOPORTE LETRADO.
// Uso: node gen_conclusiones.js <caso.json> <salida.docx>

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Table, TableRow, AlignmentType, WidthType, Paragraph,
} = require("docx");
const F = require("./format_constants");
const logUso = require("./log_uso");

// Anchos de columna (área útil A4 con márgenes 2/3,5 cm = 8787 DXA)
const COLW_NC = [500, 3500, 2200, 1100, 1487];
const COLW_C  = [500, 2400, 1900, 1900, 2087];

function rowHechoNC(f, alt) {
  const fill = alt ? F.GRAY_ALT : undefined;
  const hechoParas = [
    new Paragraph({
      alignment: AlignmentType.JUSTIFIED,
      spacing: { line: F.LINE_125, before: 30, after: 30 },
      children: [F.T(f.hecho, { size: F.FS_BODY })],
    }),
    ...(f.cita_ap || []).map(F.CitaAp),
  ];
  return new TableRow({
    children: [
      F.C(String(f.n), { align: AlignmentType.CENTER, w: COLW_NC[0], fill }),
      F.CMulti(hechoParas, { w: COLW_NC[1], fill }),
      F.C(f.posicion_demandado || "", { w: COLW_NC[2], fill }),
      F.C(f.prueba || "", { align: AlignmentType.CENTER, w: COLW_NC[3], fill }),
      F.C(f.estado || "No controvertido", { align: AlignmentType.CENTER, w: COLW_NC[4], bold: true, fill }),
    ],
  });
}

function rowHechoC(f) {
  const hechoParas = [
    new Paragraph({
      alignment: AlignmentType.JUSTIFIED,
      spacing: { line: F.LINE_125, before: 30, after: 30 },
      children: [F.T(f.hecho, { size: F.FS_BODY, bold: true })],
    }),
    ...(f.cita_ap || []).map(F.CitaAp),
  ];
  return new TableRow({
    children: [
      F.C(String(f.n), { align: AlignmentType.CENTER, w: COLW_C[0], fill: F.ORANGE_CTRV }),
      F.CMulti(hechoParas, { w: COLW_C[1], fill: F.ORANGE_CTRV }),
      F.C(f.tesis_actora || "", { w: COLW_C[2] }),
      F.C(f.tesis_demandada || "", { w: COLW_C[3] }),
      F.C(f.fuente_probatoria || "", { w: COLW_C[4] }),
    ],
  });
}

function tablaNC(filas) {
  const header = new TableRow({
    tableHeader: true,
    children: [
      F.C("Nº", { header: true, align: AlignmentType.CENTER, w: COLW_NC[0] }),
      F.C("Hecho", { header: true, align: AlignmentType.CENTER, w: COLW_NC[1] }),
      F.C("Posición del demandado", { header: true, align: AlignmentType.CENTER, w: COLW_NC[2] }),
      F.C("Prueba", { header: true, align: AlignmentType.CENTER, w: COLW_NC[3] }),
      F.C("Estado", { header: true, align: AlignmentType.CENTER, w: COLW_NC[4] }),
    ],
  });
  return new Table({
    width: { size: COLW_NC.reduce((a,b)=>a+b,0), type: WidthType.DXA },
    columnWidths: COLW_NC,
    rows: [header, ...filas.map((f, i) => rowHechoNC(f, i % 2 === 1))],
  });
}

function tablaC(filas) {
  const header = new TableRow({
    tableHeader: true,
    children: [
      F.C("Nº", { header: true, align: AlignmentType.CENTER, w: COLW_C[0] }),
      F.C("Hecho controvertido", { header: true, align: AlignmentType.CENTER, w: COLW_C[1] }),
      F.C("Tesis actora", { header: true, align: AlignmentType.CENTER, w: COLW_C[2] }),
      F.C("Tesis demandada", { header: true, align: AlignmentType.CENTER, w: COLW_C[3] }),
      F.C("Fuente probatoria", { header: true, align: AlignmentType.CENTER, w: COLW_C[4] }),
    ],
  });
  return new Table({
    width: { size: COLW_C.reduce((a,b)=>a+b,0), type: WidthType.DXA },
    columnWidths: COLW_C,
    rows: [header, ...filas.map(rowHechoC)],
  });
}

function build(caso) {
  const children = [];
  children.push(F.PTitle("ESQUEMA DE CONCLUSIONES"));

  children.push(F.PH1("I. HECHOS NO CONTROVERTIDOS"));
  if (caso.ap && caso.ap.fecha) {
    children.push(F.P(
      "Hechos fijados o admitidos en la audiencia previa de " + caso.ap.fecha + " (transcripcion oficial; minutaje entre corchetes).",
      { italic: true, size: F.FS_SMALL, color: F.GRAY_DARK }
    ));
  }
  children.push(tablaNC(caso.hechos_no_controvertidos || []));

  children.push(F.PH1("II. HECHOS CONTROVERTIDOS"));
  const hc = caso.hechos_controvertidos || {};
  if (hc.intro) {
    children.push(F.P(hc.intro, { italic: true, size: F.FS_SMALL, color: F.GRAY_DARK }));
  }
  children.push(tablaC(hc.filas || []));

  children.push(F.PH1("III. CONCLUSIONES"));
  (caso.conclusiones || []).forEach(c => {
    children.push(F.P(c.head, { bold: true, before: 200, after: 60 }));
    (c.body || []).forEach(b => children.push(F.PBody(b)));
  });

  children.push(F.PH1("IV. PETITUM"));
  (caso.petitum || []).forEach(line => children.push(F.P(line)));

  return children;
}

function main() {
  const casoPath = process.argv[2];
  const outPath  = process.argv[3] || "CONCLUSIONES.docx";
  if (!casoPath) {
    console.error("Uso: node gen_conclusiones.js <caso.json> <salida.docx>");
    process.exit(1);
  }
  const caso = JSON.parse(fs.readFileSync(casoPath, "utf8"));

  const footerExtra = caso.fecha_juicio ? ("Juicio " + caso.fecha_juicio) : null;
  const headerTxt = caso.encabezado_pagina || ((caso.procedimiento || "") + " - " + (caso.organo || "") + " - " + (caso.ref || ""));

  const doc = new Document({
    creator: caso.autor || "Despacho",
    title: "Esquema de conclusiones - " + (caso.ref || ""),
    styles: { default: { document: { run: { font: F.FONT, size: F.FS_BODY } } } },
    sections: [{
      properties: { page: F.PAGE },
      headers: { default: F.buildHeader(headerTxt) },
      footers: { default: F.buildFooter(footerExtra) },
      children: build(caso),
    }],
  });

  Packer.toBuffer(doc).then(buf => {
    fs.writeFileSync(outPath, buf);
    console.log("OK:", outPath);
    logUso.log({
      ref: caso.ref || null,
      accion: "gen_conclusiones",
      archivos: [path.basename(outPath)],
      hechos_no_ctrv: (caso.hechos_no_controvertidos || []).length,
      hechos_ctrv: ((caso.hechos_controvertidos || {}).filas || []).length,
      conclusiones: (caso.conclusiones || []).length,
      petitum: (caso.petitum || []).length,
    });
  });
}

main();
