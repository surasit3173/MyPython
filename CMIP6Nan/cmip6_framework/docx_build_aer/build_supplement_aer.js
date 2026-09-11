// Render the supplementary material in the same style as the manuscript.
//
// The manuscript builder and this one share every formatting decision: Times
// New Roman 10 pt, A4 with 1-inch margins, one column, double-spaced prose,
// continuous line numbering, and tables with horizontal rules only and a
// caption above. A supplement produced by a different toolchain looks like a
// different paper, which is what the earlier pandoc output did.
const fs = require("fs");
const path = require("path");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, ShadingType, BorderStyle, convertInchesToTwip,
} = d;

const FONT = "Times New Roman";
// matches the AER manuscript: 12-point body, 10-point tables, Letter page
const SZ = 24, SZ_TITLE = 28, SZ_SMALL = 20, SZ_CELL = 18, LINE = 480;
const USABLE = 9360;   // 6.5 inches of text on a Letter page

const S = JSON.parse(fs.readFileSync(path.join(__dirname, "supplement.json"), "utf8"));

const run = (t, o = {}) => new TextRun({
  text: t, font: FONT, size: o.size || SZ, bold: !!o.bold,
  italics: !!o.italics, superScript: !!o.sup, subScript: !!o.sub,
});

// same inline markup the manuscript builder understands
function rich(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|~[^~]+~|\^[^^]+\^)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(run(text.slice(last, m.index), base));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(run(tok.slice(2, -2), { ...base, bold: true }));
    else if (tok.startsWith("*")) out.push(run(tok.slice(1, -1), { ...base, italics: true }));
    else if (tok.startsWith("~")) out.push(run(tok.slice(1, -1), { ...base, sub: true }));
    else out.push(run(tok.slice(1, -1), { ...base, sup: true }));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(run(text.slice(last), base));
  return out.length ? out : [run("")];
}

const P = (t, o = {}) => new Paragraph({
  children: rich(t, o),
  alignment: o.align || AlignmentType.JUSTIFIED,
  spacing: { line: o.line || LINE, after: o.after || 0, before: o.before || 0 },
});

const CAP = (t, o = {}) => new Paragraph({
  children: rich(t, { size: SZ_SMALL }),
  alignment: AlignmentType.LEFT,
  spacing: { line: 240, before: o.before === undefined ? 160 : o.before,
             after: o.after === undefined ? 60 : o.after },
  keepNext: true, keepLines: true,
});

const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const RULE = { style: BorderStyle.SINGLE, size: 6, color: "000000" };

function cellP(text, o = {}) {
  return new Paragraph({
    children: rich(String(text), { bold: o.bold, size: SZ_CELL }),
    alignment: o.align || AlignmentType.LEFT,
    spacing: { line: 200, before: 10, after: 10 },
  });
}

// Numeric columns are right-aligned, everything else left, decided from the
// data rather than declared per table.
function alignments(cols, rows) {
  return cols.map((_, j) => {
    const vals = rows.map((r) => r[j]).filter((v) => v !== "");
    const numeric = vals.length &&
      vals.every((v) => /^[+-]?\d+(\.\d+)?$/.test(String(v).trim()));
    return numeric ? AlignmentType.RIGHT : AlignmentType.LEFT;
  });
}

// Column widths follow the longest entry, so a long text column does not get
// the same share as a two-digit count.
function weights(cols, rows) {
  return cols.map((c, j) => {
    const len = Math.max(String(c).length,
      ...rows.map((r) => String(r[j] || "").length));
    return Math.max(3.0, Math.min(len + 2, 42));
  });
}

function makeTable(cols, rows) {
  const w = weights(cols, rows);
  const al = alignments(cols, rows);
  const total = w.reduce((a, b) => a + b, 0);
  const widths = w.map((x) => Math.round((x / total) * USABLE));
  const head = new TableRow({
    tableHeader: true,
    children: cols.map((c, j) => new TableCell({
      width: { size: widths[j], type: WidthType.DXA },
      borders: { top: RULE, bottom: RULE, left: NONE, right: NONE },
      shading: { type: ShadingType.CLEAR, fill: "FFFFFF" },
      children: [cellP(c, { bold: true, align: al[j] })],
    })),
  });
  const body = rows.map((r, i) => new TableRow({
    children: r.map((v, j) => new TableCell({
      width: { size: widths[j], type: WidthType.DXA },
      borders: { top: NONE, bottom: i === rows.length - 1 ? RULE : NONE,
                 left: NONE, right: NONE },
      children: [cellP(v, { align: al[j] })],
    })),
  }));
  return new Table({ columnWidths: widths,
                     width: { size: USABLE, type: WidthType.DXA },
                     margins: { top: 10, bottom: 10, left: 40, right: 40 },
                     rows: [head, ...body] });
}

// ---------------------------------------------------------------- content
const body = [];
body.push(new Paragraph({
  children: rich("Supplementary material", { bold: true, size: SZ_TITLE }),
  spacing: { line: LINE, after: 120 },
}));
body.push(P(`**${S.title}**`));
body.push(P(""));
body.push(P(S.author));
body.push(P(S.affiliation, { size: SZ_SMALL }));
body.push(P(""));
body.push(P("Supplementary tables are numbered as they are cited in the "
  + "manuscript. Where a listing runs to thousands of rows it is supplied as a "
  + "machine-readable file with this submission rather than as a printed table; "
  + "those files are listed at the end."));
body.push(P(""));

for (const t of S.tables) {
  body.push(CAP(`**Supplementary ${t.number.startsWith("Data") ? t.number : "Table " + t.number}.** ${t.title}.`
    + (t.note ? ` ${t.note}` : "")));
  body.push(makeTable(t.columns, t.rows));
  body.push(P("", { line: 200 }));
}

body.push(new Paragraph({
  children: rich("Supplementary Data files", { bold: true }),
  spacing: { line: LINE, before: 200, after: 60 },
}));
body.push(P("The complete listings behind the aggregated tables above are "
  + "provided as comma-separated files in this submission."));
body.push(P("", { line: 200 }));
body.push(makeTable(["File", "Rows", "Columns"],
  S.data_files.map((f) => [f.file, String(f.rows), String(f.columns)])));

const doc = new Document({
  creator: S.author,
  title: "Supplementary Material",
  styles: { default: { document: { run: { font: FONT, size: SZ } } } },
  sections: [{
    properties: {
      lineNumbers: { countBy: 1, start: 1,
                     restart: d.LineNumberRestartFormat.CONTINUOUS },
      page: {
        size: { width: convertInchesToTwip(8.5),
                height: convertInchesToTwip(11) },
        margin: {
          top: convertInchesToTwip(1), bottom: convertInchesToTwip(1),
          left: convertInchesToTwip(1), right: convertInchesToTwip(1),
        },
      },
    },
    footers: {
      default: new d.Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          // without this the footer paragraph takes a line number of its own,
          // which prints a stray numeral in the margin of every page
          suppressLineNumbers: true,
          children: [new TextRun({
            children: [d.PageNumber.CURRENT], font: FONT, size: SZ_SMALL })],
        })],
      }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(S.out, buf);
  console.log(`supplementary Word document: ${S.out} `
    + `(${S.tables.length} tables, ${S.data_files.length} data files, `
    + `${(buf.length / 1024).toFixed(0)} KB)`);
});
