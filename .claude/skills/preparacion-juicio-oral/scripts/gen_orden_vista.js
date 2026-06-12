// gen_orden_vista.js - guion de vista (opcional)
const fs = require("fs");
const path = require("path");
const { Document, Packer, AlignmentType, WidthType, Table, TableRow } = require("docx");
const F = require("./format_constants");
const logUso = require("./log_uso");

const COLW = [500, 2800, 1500, 1500, 2487];

function rowT(t) {
  return new TableRow({
    children: [
      F.C(String(t.n || ""), { align: AlignmentType.CENTER, w: COLW[0] }),
      F.C(t.testigo || "", { w: COLW[1] }),
      F.C(t.rol || "", { align: AlignmentType.CENTER, w: COLW[2] }),
      F.C(t.tiempo || "", { align: AlignmentType.CENTER, w: COLW[3] }),
      F.C(t.notas || "", { w: COLW[4] }),
    ],
  });
}

function build(data) {
  const children = [];
  children.push(F.PTitle("ORDEN DE VISTA — " + (data.ref || "")));
  children.push(F.P("Procedimiento: " + (data.procedimiento || "") + ". " + (data.organo || "") + ".", { bold: true, before: 0 }));
  children.push(F.P("Fecha: " + (data.fecha_juicio || "por confirmar") + "."));
  children.push(F.P("Sala: " + (data.sala || "por confirmar") + ".", { after: 120 }));

  if ((data.documentos_mano || []).length > 0) {
    children.push(F.PH1("1. Documentos a tener a mano"));
    data.documentos_mano.forEach((d, i) => children.push(F.PN(i + 1, d)));
  }

  if ((data.orden_testigos || []).length > 0) {
    children.push(F.PH1("2. Orden de testigos previsto"));
    const header = new TableRow({
      tableHeader: true,
      children: [
        F.C("Orden", { header: true, align: AlignmentType.CENTER, w: COLW[0] }),
        F.C("Testigo", { header: true, align: AlignmentType.CENTER, w: COLW[1] }),
        F.C("Rol", { header: true, align: AlignmentType.CENTER, w: COLW[2] }),
        F.C("Tiempo", { header: true, align: AlignmentType.CENTER, w: COLW[3] }),
        F.C("Notas", { header: true, align: AlignmentType.CENTER, w: COLW[4] }),
      ],
    });
    children.push(new Table({
      width: { size: COLW.reduce((a,b)=>a+b,0), type: WidthType.DXA },
      columnWidths: COLW,
      rows: [header, ...data.orden_testigos.map(rowT)],
    }));
    if (data.razon_orden) children.push(F.P("Razon del orden: " + data.razon_orden, { italic: true }));
  }

  if ((data.protestas_previsibles || []).length > 0) {
    children.push(F.PH1("3. Protestas previsibles"));
    data.protestas_previsibles.forEach((p, i) => children.push(F.PN(i + 1, p)));
  }

  if ((data.riesgos || []).length > 0) {
    children.push(F.PH1("4. Riesgos identificados"));
    data.riesgos.forEach((r, i) => children.push(F.PN(i + 1, r)));
  }

  if ((data.conclusiones_orales_bullets || []).length > 0) {
    children.push(F.PH1("5. Conclusiones orales — bullets"));
    data.conclusiones_orales_bullets.forEach((b, i) => children.push(F.PN(i + 1, b)));
  }

  if ((data.recordatorios || []).length > 0) {
    children.push(F.PH1("6. Recordatorios procesales"));
    data.recordatorios.forEach((r, i) => children.push(F.PN(i + 1, r)));
  }
  return children;
}

function main() {
  const dataPath = process.argv[2];
  const outPath = process.argv[3] || "ORDEN_VISTA.docx";
  const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
  const doc = new Document({
    creator: data.autor || "Despacho",
    title: "Orden de vista - " + (data.ref || ""),
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
    logUso.log({
      ref: data.ref || null,
      accion: "gen_orden_vista",
      archivos: [path.basename(outPath)],
      testigos: (data.orden_testigos || []).length,
      documentos_mano: (data.documentos_mano || []).length,
      protestas: (data.protestas_previsibles || []).length,
      riesgos: (data.riesgos || []).length,
      recordatorios: (data.recordatorios || []).length,
    });
  });
}
main();
