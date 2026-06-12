// gen_cuadro_hechos.js - cuadro tabular suelto (opcional)
const fs = require("fs");
const path = require("path");
const { Document, Packer, Table, TableRow, AlignmentType, WidthType, Paragraph } = require("docx");
const F = require("./format_constants");
const logUso = require("./log_uso");

const COLW = [500, 3500, 2200, 1100, 1487];

function rowFila(f, alt) {
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
      F.C(String(f.n), { align: AlignmentType.CENTER, w: COLW[0], fill }),
      F.CMulti(hechoParas, { w: COLW[1], fill }),
      F.C(f.posicion_demandado || "", { w: COLW[2], fill }),
      F.C(f.prueba || f.documento || "", { align: AlignmentType.CENTER, w: COLW[3], fill }),
      F.C(f.estado || "", { align: AlignmentType.CENTER, w: COLW[4], bold: true, fill }),
    ],
  });
}

function build(data) {
  const children = [];
  children.push(F.PTitle("CUADRO CONSOLIDADO DE HECHOS"));

  if (data.ap && data.ap.fecha) {
    children.push(F.P("Audiencia previa de " + data.ap.fecha + " (transcripcion oficial).", { italic: true, size: F.FS_SMALL, color: F.GRAY_DARK }));
  }

  const header = new TableRow({
    tableHeader: true,
    children: [
      F.C("Nº", { header: true, align: AlignmentType.CENTER, w: COLW[0] }),
      F.C("Hecho", { header: true, align: AlignmentType.CENTER, w: COLW[1] }),
      F.C("Posicion del demandado", { header: true, align: AlignmentType.CENTER, w: COLW[2] }),
      F.C("Prueba", { header: true, align: AlignmentType.CENTER, w: COLW[3] }),
      F.C("Estado", { header: true, align: AlignmentType.CENTER, w: COLW[4] }),
    ],
  });
  const filas = data.filas || [];
  children.push(new Table({
    width: { size: COLW.reduce((a,b)=>a+b,0), type: WidthType.DXA },
    columnWidths: COLW,
    rows: [header, ...filas.map((f, i) => rowFila(f, i % 2 === 1))],
  }));

  if (data.conclusion_operativa) {
    children.push(F.PH1("Conclusion operativa"));
    children.push(F.P(data.conclusion_operativa));
  }
  return children;
}

function main() {
  const dataPath = process.argv[2];
  const outPath = process.argv[3] || "CUADRO_HECHOS.docx";
  const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
  const doc = new Document({
    creator: data.autor || "Despacho",
    title: "Cuadro de hechos - " + (data.ref || ""),
    styles: { default: { document: { run: { font: F.FONT, size: F.FS_BODY } } } },
    sections: [{
      properties: { page: F.PAGE },
      headers: { default: F.buildHeader(data.encabezado_pagina || "") },
      footers: { default: F.buildFooter(data.fecha_juicio ? "Juicio " + data.fecha_juicio : null) },
      children: build(data),
    }],
  });
  Packer.toBuffer(doc).then(buf => {
    fs.writeFileSync(outPath, buf);
    console.log("OK:", outPath);
    const filas = data.filas || [];
    const norm = s => (s || "").trim().toLowerCase();
    logUso.log({
      ref: data.ref || null,
      accion: "gen_cuadro_hechos",
      archivos: [path.basename(outPath)],
      filas: filas.length,
      hechos_ctrv: filas.filter(f => norm(f.estado) === "controvertido").length,
      hechos_no_ctrv: filas.filter(f => norm(f.estado) === "no controvertido").length,
    });
  });
}
main();
