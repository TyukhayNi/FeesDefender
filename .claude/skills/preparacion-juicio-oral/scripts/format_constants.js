// format_constants.js
// Constantes y helpers para los generadores .docx (modo SOPORTE LETRADO)
const {
  Paragraph, TextRun, AlignmentType, BorderStyle, WidthType, ShadingType,
  VerticalAlign, TableCell, Header, Footer, PageNumber,
} = require("docx");

const FONT = "Arial";
const FS_BODY = 24;
const FS_H1 = 32;
const FS_H2 = 28;
const FS_SMALL = 20;
const FS_CITE = 18;
const LINE_125 = 300;

const PAGE = {
  size: { width: 11906, height: 16838 },
  margin: { top: 1417, right: 1134, bottom: 1417, left: 1985 },
};
const PAGE_SYM = {
  size: { width: 11906, height: 16838 },
  margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
};

const INDENT_QUOTE = 567;
const INDENT_BODY_BULLET = 340;
const INDENT_CITE = 200;

const GRAY_DARK = "595959";
const GRAY_BLOCK = "E7E6E6";
const GRAY_HEADER = "BFBFBF";
const GRAY_ALT = "F2F2F2";
const ORANGE_CTRV = "FCE4D6";
const BOX_BG = "F8F8F8";
const BOX_BORDER = "808080";

const CELL_BORDER = { style: BorderStyle.SINGLE, size: 4, color: "808080" };
const CELL_BORDERS = { top: CELL_BORDER, bottom: CELL_BORDER, left: CELL_BORDER, right: CELL_BORDER };

// Modo formal Sala 1ª TS (subset)
const TNR = "Times New Roman";
const LINE_15 = 360;
const PAGE_TS = {
  size: { width: 11906, height: 16838 },
  margin: { top: 1417, right: 1417, bottom: 1417, left: 1417 },
};

function T(text, o) {
  o = o || {};
  return new TextRun({
    text: text,
    font: o.font || FONT,
    size: o.size || FS_BODY,
    bold: !!o.bold,
    italics: !!o.italic,
    color: o.color,
  });
}

function PTitle(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { line: LINE_125, before: 0, after: 240 },
    children: [T(text, { size: FS_H1, bold: true })],
  });
}

function PH1(text) {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { line: LINE_125, before: 320, after: 120 },
    shading: { fill: GRAY_BLOCK, type: ShadingType.CLEAR },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "808080", space: 1 } },
    children: [T(text, { size: FS_H2, bold: true })],
  });
}

function PHead(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 200, after: 60 },
    children: [T(text, { bold: true })],
  });
}

function PBody(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 60, after: 60 },
    indent: { left: INDENT_BODY_BULLET },
    children: [T(text)],
  });
}

function PN(num, text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 60, after: 0 },
    children: [T(num + ". ", { bold: true }), T(text)],
  });
}

function P(text, opts) {
  opts = opts || {};
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: opts.before == null ? 80 : opts.before, after: opts.after == null ? 80 : opts.after },
    indent: opts.indent,
    children: [T(text, opts)],
  });
}

function PCite(text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 80, after: 80 },
    indent: { left: INDENT_QUOTE },
    children: [T(text, { size: FS_SMALL, italic: true, color: GRAY_DARK })],
  });
}

function Q(n, text, exhibir) {
  const runs = [
    T("☐  ", { size: FS_H2, bold: true }),
    T(n + ". ", { size: FS_H2, bold: true }),
    T(text),
  ];
  if (exhibir) {
    runs.push(T("  [Exhibir: " + exhibir + "]", { italic: true, color: GRAY_DARK }));
  }
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 160, after: 40 },
    children: runs,
  });
}

function QSimple(n, text, exhibir) {
  const runs = [T(n + ". ", { bold: true }), T(text)];
  if (exhibir) {
    runs.push(T("  [Documento: " + exhibir + "]", { italic: true, color: GRAY_DARK }));
  }
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 160, after: 60 },
    children: runs,
  });
}

function labeled(label, text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 30, after: 30 },
    indent: { left: INDENT_QUOTE },
    children: [
      T(label + " — ", { size: FS_SMALL, italic: true, bold: true, color: GRAY_DARK }),
      T(text, { size: FS_SMALL, italic: true, color: GRAY_DARK }),
    ],
  });
}
const RE = (t) => labeled("RE", t);
const RD = (t) => labeled("RD", t);
const Nota = (t) => labeled("Nota", t);

function CitaAp(c) {
  const cab = "[" + c.timestamp + ", " + c.atribucion + "] ";
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE_125, before: 40, after: 40 },
    indent: { left: INDENT_CITE },
    children: [
      T(cab, { size: FS_CITE, italic: true, bold: true, color: GRAY_DARK }),
      T("«" + c.texto + "»", { size: FS_CITE, italic: true, color: GRAY_DARK }),
    ],
  });
}

function BoxParagraphs(paragraphs) {
  const boxBorder = {
    top:    { style: BorderStyle.SINGLE, size: 6, color: BOX_BORDER, space: 4 },
    bottom: { style: BorderStyle.SINGLE, size: 6, color: BOX_BORDER, space: 4 },
    left:   { style: BorderStyle.SINGLE, size: 6, color: BOX_BORDER, space: 4 },
    right:  { style: BorderStyle.SINGLE, size: 6, color: BOX_BORDER, space: 4 },
  };
  return paragraphs.map(p => {
    return new Paragraph({
      alignment: p.alignment || AlignmentType.JUSTIFIED,
      spacing: p.spacing || { line: LINE_125, before: 40, after: 40 },
      indent: p.indent,
      shading: { fill: BOX_BG, type: ShadingType.CLEAR },
      border: boxBorder,
      children: p._children || p.children,
    });
  });
}

function C(text, opts) {
  opts = opts || {};
  const isHeader = !!opts.header;
  const fill = opts.fill || (isHeader ? GRAY_HEADER : undefined);
  const align = opts.align || AlignmentType.LEFT;
  const lines = Array.isArray(text) ? text : [text];
  const ps = lines.map(t =>
    new Paragraph({
      alignment: align,
      spacing: { line: LINE_125, before: 30, after: 30 },
      children: [T(t, { size: opts.size || FS_BODY, bold: isHeader || opts.bold })],
    })
  );
  return new TableCell({
    borders: CELL_BORDERS,
    width: { size: opts.w, type: WidthType.DXA },
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    verticalAlign: VerticalAlign.TOP,
    shading: fill ? { fill: fill, type: ShadingType.CLEAR } : undefined,
    children: ps,
  });
}

function CMulti(paragraphs, opts) {
  opts = opts || {};
  return new TableCell({
    borders: CELL_BORDERS,
    width: { size: opts.w, type: WidthType.DXA },
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    verticalAlign: VerticalAlign.TOP,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: paragraphs,
  });
}

function buildHeader(text) {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.RIGHT,
      spacing: { line: 240, before: 0, after: 40 },
      children: [T(text, { size: FS_SMALL, color: GRAY_DARK })],
    })],
  });
}

function buildFooter(extraText) {
  const children = [
    T("Pag. ", { size: FS_SMALL, color: GRAY_DARK }),
    new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: FS_SMALL, color: GRAY_DARK }),
  ];
  if (extraText) {
    children.push(T(" — " + extraText, { size: FS_SMALL, color: GRAY_DARK }));
  }
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { line: 240 },
      children: children,
    })],
  });
}

module.exports = {
  FONT, FS_BODY, FS_H1, FS_H2, FS_SMALL, FS_CITE, LINE_125,
  PAGE, PAGE_SYM, INDENT_QUOTE, INDENT_BODY_BULLET, INDENT_CITE,
  GRAY_DARK, GRAY_BLOCK, GRAY_HEADER, GRAY_ALT, ORANGE_CTRV, BOX_BG, BOX_BORDER,
  CELL_BORDERS,
  TNR, LINE_15, PAGE_TS,
  T, PTitle, PH1, PHead, PBody, PN, P, PCite,
  Q, QSimple, RE, RD, Nota, labeled, CitaAp, BoxParagraphs,
  C, CMulti, buildHeader, buildFooter,
};
