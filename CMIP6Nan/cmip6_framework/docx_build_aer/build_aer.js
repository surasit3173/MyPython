const fs = require("fs");
const path = require("path");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, ShadingType, BorderStyle, ImageRun,
  convertInchesToTwip,
} = d;

const FONT = "Times New Roman";
// AER: 12-point body, double spacing, Letter page, 129 mm figures
const SZ = 24, SZ_TITLE = 28, SZ_SMALL = 20, SZ_CELL = 20, LINE = 480;
const FIG_IN = 5.08;   // 129 mm, one of the four widths AER accepts
const PATHS = JSON.parse(fs.readFileSync(path.join(__dirname, "paths.json"), "utf8"));
const SRC = PATHS.src;
const FIGDIR = PATHS.figdir;
const USABLE = 9020;          // A4 minus 1-inch margins, in DXA

const run = (t, o = {}) => new TextRun({
  text: t, font: FONT, size: o.size || SZ, bold: !!o.bold, italics: !!o.italics,
  superScript: !!o.sup, subScript: !!o.sub,
});

function nested(text, base) {
  // emphasis can appear inside a subscript or superscript, e.g. "*i*=1"
  const out = [];
  const re = /\*([^*]+)\*/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(run(text.slice(last, m.index), base));
    out.push(run(m[1], { ...base, italics: true }));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(run(text.slice(last), base));
  return out.length ? out : [run(text, base)];
}

function rich(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|~[^~]+~|\^[^^]+\^)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(run(text.slice(last, m.index), base));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(run(tok.slice(2, -2), { ...base, bold: true }));
    else if (tok.startsWith("*")) out.push(run(tok.slice(1, -1), { ...base, italics: true }));
    else if (tok.startsWith("~")) out.push(...nested(tok.slice(1, -1), { ...base, sub: true }));
    else out.push(...nested(tok.slice(1, -1), { ...base, sup: true }));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(run(text.slice(last), base));
  return out.length ? out : [run("")];
}

const P = (t, o = {}) => new Paragraph({
  children: typeof t === "string" ? rich(t, o) : t,
  alignment: o.align || AlignmentType.JUSTIFIED,
  spacing: { line: o.line || LINE, after: o.after || 0, before: o.before || 0 },
  indent: o.indent ? { firstLine: convertInchesToTwip(0.25) } : undefined,
});

const H = (t) => new Paragraph({
  children: rich(t, { bold: true }), alignment: AlignmentType.LEFT,
  spacing: { line: LINE, before: 120, after: 40 }, keepNext: true,
});

const SH = (t) => new Paragraph({
  children: rich(t, { italics: true }), alignment: AlignmentType.LEFT,
  spacing: { line: LINE, before: 100, after: 20 }, keepNext: true,
});

const BLANK = () => new Paragraph({ children: [run("")], spacing: { line: LINE } });

const CAP = (t, o = {}) => new Paragraph({
  children: rich(t, { size: SZ_SMALL }), alignment: AlignmentType.LEFT,
  spacing: { line: 240, before: o.before === undefined ? 40 : o.before, after: o.after === undefined ? 80 : o.after },
  keepNext: !!o.keepNext, keepLines: true,
});

// ---------------------------------------------------------------- tables
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const RULE = { style: BorderStyle.SINGLE, size: 6, color: "000000" };

function cellP(text, o = {}) {
  return new Paragraph({
    children: rich(String(text), { bold: o.bold, size: SZ_CELL }),
    alignment: o.align || AlignmentType.LEFT,
    spacing: { line: 240, before: 20, after: 20 },
  });
}

function mabTable(recs) {
  return makeTable(["Index", "Type", "Raw CMIP6", "QM/EQM", "DetQM", "QDM"],
    recs.map((r) => [r.Index, r.Type, r["Raw CMIP6"].toFixed(2),
      r["QM/EQM"].toFixed(2), r.DetQM.toFixed(2), r.QDM.toFixed(2)]),
    [1.7, 1.5, 1.5, 1.3, 1.3, 1.3], [L, L, R, R, R, R]);
}

function peTable(recs) {
  // Index and Type repeat only on the first row of each block, so the eye
  // reads down the scenario pairs without visual noise.
  const head = ["Index", "Type", "Scenario", "QM/EQM", "DetQM", "QDM", "n"];
  let lastIdx = "";
  const rows = recs.map((r) => {
    const first = r.Index !== lastIdx;
    lastIdx = r.Index;
    return [first ? r.Index : "", first ? r.Type : "", r.Scenario,
            r["QM/EQM"], r.DetQM, r.QDM, first ? String(r.GCMs) : ""];
  });
  return makeTable(head, rows,
    [1.55, 1.45, 1.35, 2.45, 2.45, 2.45, 0.45],
    [L, L, L, C, C, C, C]);
}

function twoColumnTable(recs) {
  // 13 gauges laid out as two side-by-side blocks so the table occupies half
  // the vertical space of a single-column listing.
  const half = Math.ceil(recs.length / 2);
  const fmt = (r) => r
    ? [String(r.Station), r["Longitude (°E)"].toFixed(2), r["Latitude (°N)"].toFixed(2),
       String(Math.round(r["Mean annual rainfall (mm)"]))]
    : ["", "", "", ""];
  const rows = [];
  for (let i = 0; i < half; i++) {
    rows.push(fmt(recs[i]).concat(fmt(recs[i + half])));
  }
  const h = ["Station", "Lon (°E)", "Lat (°N)", "Rainfall (mm)"];
  return makeTable(h.concat(h), rows,
    [1.2, 1.2, 1.2, 1.6, 1.2, 1.2, 1.2, 1.6],
    [L, R, R, R, L, R, R, R]);
}

function makeTable(headers, rows, weights, aligns) {
  const total = weights.reduce((a, b) => a + b, 0);
  const cols = weights.map((w) => Math.round((w / total) * USABLE));
  const head = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => new TableCell({
      width: { size: cols[i], type: WidthType.DXA },
      borders: { top: RULE, bottom: RULE, left: NONE, right: NONE },
      shading: { type: ShadingType.CLEAR, fill: "FFFFFF" },
      children: [cellP(h, { bold: true, align: aligns[i] })],
    })),
  });
  const body = rows.map((r, ri) => new TableRow({
    children: r.map((c, i) => new TableCell({
      width: { size: cols[i], type: WidthType.DXA },
      borders: { top: NONE, bottom: ri === rows.length - 1 ? RULE : NONE, left: NONE, right: NONE },
      children: [cellP(c, { align: aligns[i] })],
    })),
  }));
  return new Table({ columnWidths: cols, width: { size: USABLE, type: WidthType.DXA },
                     rows: [head, ...body] });
}

// ---------------------------------------------------------------- figures
function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }

function figure(file, widthIn) {
  const p = path.join(FIGDIR, file);
  if (!fs.existsSync(p)) {
    console.warn("  [skip] figure not found:", file);
    return new Paragraph({ children: [run("")], spacing: { after: 0 } });
  }
  const buf = fs.readFileSync(p);
  const dim = pngSize(buf);
  const w = Math.round(widthIn * 96);
  return new Paragraph({
    children: [new ImageRun({ data: buf, type: "png",
      transformation: { width: w, height: Math.round((dim.h / dim.w) * w) } })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 60, after: 20, lineRule: d.LineRuleType.AUTO },
    keepNext: true,
  });
}

const J = (f) => JSON.parse(fs.readFileSync(path.join(__dirname, f), "utf8"));
const { EQUATIONS } = require("./equations.js");
// Captions come from the manuscript, so the builder cannot hold a stale copy.
const CAPTIONS = J("captions.json");
const cap = (key, o = {}) => {
  const text = CAPTIONS[key];
  if (!text) throw new Error("no caption in the manuscript for " + key);
  return CAP(text, o);
};
// Table 6 in the main text carries the indices the Results actually discuss;
// the full sixteen-index listing is supplementary.
const T6KEEP = new Set(["PRCPTOT", "SDII", "q50", "R20mm", "R50mm", "R95p"]);
const L = AlignmentType.LEFT, C = AlignmentType.CENTER, R = AlignmentType.RIGHT;

// ---------------------------------------------------------------- content
const PRETTY = { wet_day_pct: "Wet days", PRCPTOT: "PRCPTOT", SDII: "SDII",
  q95: "q95", Rx1day: "Rx1day", Rx5day: "Rx5day", CDD: "CDD", CWD: "CWD",
  R20mm: "R20mm", R50mm: "R50mm", R95p: "R95p", R99p: "R99p" };
const HORDER = { Near: 0, Mid: 1, Late: 2 };

function biasTable(rows) {
  return makeTable(
    ["Index", "Raw CMIP6", "QDM-corrected"],
    rows.map((r) => [PRETTY[r.Index] || r.Index,
                     r["Raw CMIP6"].toFixed(2), r["QDM-corrected"].toFixed(2)]),
    [3, 2, 2], [L, R, R]);
}

function changeTable(recs) {
  // Rows are indices, columns are scenarios: "median [IQR] (agreement)".
  // Robust entries are bold; diagnostic indices are marked in their own column.
  const scen = [...new Set(recs.map((r) => r.Scenario))].sort();
  const idx = [...new Set(recs.map((r) => r.Index))];
  const by = {};
  for (const r of recs) by[r.Index + "|" + r.Scenario] = r;
  const rows = idx.map((k) => {
    const first = recs.find((r) => r.Index === k);
    const cells = [PRETTY[k] || k, first && first.Type === "diagnostic" ? "diagnostic" : "projection"];
    for (const sc of scen) {
      const r = by[k + "|" + sc];
      if (!r) { cells.push("\u2014"); continue; }
      const txt = `${Number(r["Median (%)"]).toFixed(1)} [${String(r["IQR (%)"]).replace(" to ", ", ")}] (${Number(r.Agreement).toFixed(2)})`;
      cells.push(r.Robust === "yes" ? `**${txt}**` : txt);
    }
    return cells;
  });
  const w = [1.9, 1.3].concat(scen.map(() => 3.0));
  const a = [L, L].concat(scen.map(() => C));
  return makeTable(["Index", "Type"].concat(scen), rows, w, a);
}

const body = [];

// Title block
body.push(new Paragraph({
  children: rich(PATHS.title, { bold: true, size: SZ_TITLE }),
  alignment: AlignmentType.LEFT, spacing: { line: LINE, after: 160 },
}));
body.push(new Paragraph({ children: [run("Surasit Punyawansiri"), run("1,*", { sup: true })],
  spacing: { line: LINE } }));
body.push(new Paragraph({ children: [run("1", { sup: true }),
  run("Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand")],
  spacing: { line: LINE } }));
body.push(new Paragraph({ children: [run("*", { sup: true }), run("Corresponding author: Surasit.ku@ku.th")],
  spacing: { line: LINE } }));
body.push(new Paragraph({ children: [run("Received … ; Revised … ; Accepted …", { size: SZ_SMALL })],
  alignment: R, spacing: { line: 240, before: 80, after: 160 } }));

// Abstract
body.push(H("Abstract"));
body.push(P(fs.readFileSync(path.join(__dirname, "abstract.txt"), "utf8").trim()));
body.push(BLANK());
body.push(P(PATHS.keywords));
body.push(BLANK());

// Body with tables and figures anchored after the subsection they support
const AFTER_SH = {
  "2.1 Study area and data": () => [
    figure("Paper2_Figure_01_study_area.png", FIG_IN),
    cap("Figure 1"),
  ],
  "3.1 Historical bias reduction": () => [
    
  ],
  "3.2 Independent validation": () => [
    
    figure("Paper2_Figure_03_validation_methods.png", FIG_IN),
    cap("Figure 2"),
  ],
  "3.3 Preservation of bulk and distributional climate signals": () => [
    cap("Table 1", { keepNext: true, after: 60 }),
    peTable(J("T4bulk.json")),
    figure("Paper2_Figure_04_signal_bulk_quantile.png", FIG_IN),
    cap("Figure 3"),
  ],
  "3.4 Preservation of extreme-rainfall signals": () => [
    cap("Table 2", { keepNext: true, after: 60 }),
    peTable(J("T5ext.json")),
    figure("Paper2_Figure_05_signal_extremes.png", FIG_IN),
    cap("Figure 4"),
  ],
  "3.6 Relative roles of climate model and method effects": () => [
    cap("Table 3", { keepNext: true, after: 60 }),
    makeTable(["Scenario", "Index", "N", "n", "GCM main effect (%)", "BC-method main effect (%)", "Residual (%)"],
      J("T6decomp.json").filter((r) => T6KEEP.has(r.Index))
        .map((r) => [r.Scenario.replace("-", "\u2011"), r.Index,
                     String(r["N cells"]), String(r.GCMs), r.GCM.toFixed(1),
                     r.Method.toFixed(1), r.Residual.toFixed(1)]),
      [1.5, 1.5, 0.7, 0.8, 2.1, 2.3, 1.9], [L, L, R, R, R, R, R]),
    figure("Paper2_Figure_06_synthesis.png", FIG_IN),
    cap("Figure 5"),
  ],
};

// A block keyed to a heading that no longer exists would place nothing and say
// nothing, which is how Table 3 went missing once. Check the keys up front.
{
  const headings = new Set(J("sections.json")
    .filter((x) => x.t === "sh" || x.t === "h").map((x) => x.v));
  const orphan = Object.keys(AFTER_SH).filter((k) => !headings.has(k));
  if (orphan.length) {
    throw new Error("these display blocks are keyed to headings that are not in "
      + "the manuscript: " + orphan.join("; "));
  }
}

const secs = J("sections.json");
let pendingSH = null;
let refMode = false;
for (let i = 0; i < secs.length; i++) {
  const s = secs[i];
  const nextIsBreak = (j) => {
    const n = secs[j + 1];
    return !n || n.t === "h" || n.t === "sh";
  };
  if (s.t === "h") {
    if (pendingSH && AFTER_SH[pendingSH]) { body.push(...AFTER_SH[pendingSH]()); pendingSH = null; }
    refMode = s.v.startsWith("11.");
    body.push(H(s.v));
  } else if (s.t === "sh") {
    if (pendingSH && AFTER_SH[pendingSH]) { body.push(...AFTER_SH[pendingSH]()); }
    pendingSH = s.v;
    body.push(SH(s.v));
  } else if (s.t === "eq") {
    // Real Word equation objects: the manuscript token selects the OMML built
    // in equations.js, and the trailing number is set off with tabs. Falling
    // back to styled text would defeat the point, so a missing key is fatal.
    const parts = s.v.split(/\s{2,}(\(\d\))$/);
    const key = Object.keys(EQUATIONS).find((k) => s.v.startsWith(k));
    if (!key) throw new Error("no OMML defined for equation: " + s.v.slice(0, 40));
    const kids = [EQUATIONS[key]];
    if (parts[1]) {
      kids.push(new TextRun({ children: [new d.Tab(), new d.Tab()] }));
      kids.push(run(parts[1]));
    }
    body.push(new Paragraph({ children: kids, alignment: AlignmentType.LEFT,
      spacing: { line: LINE, before: 60, after: 60 },
      indent: { left: convertInchesToTwip(0.5) } }));
  } else {
    if (refMode) {
      body.push(new Paragraph({
        children: rich(s.v),
        alignment: AlignmentType.JUSTIFIED,
        spacing: { line: 240, after: 20 },
        indent: { left: convertInchesToTwip(0.25),
                  hanging: convertInchesToTwip(0.25) },
      }));
    } else {
      body.push(P(s.v, { indent: !s.v.startsWith("**Keywords") }));
    }
    if (nextIsBreak(i) && pendingSH && AFTER_SH[pendingSH]) {
      body.push(...AFTER_SH[pendingSH]()); pendingSH = null;
    }
  }
}
if (pendingSH && AFTER_SH[pendingSH]) body.push(...AFTER_SH[pendingSH]());

const doc = new Document({
  creator: "Surasit Punyawansiri",
  title: "Bias-corrected CMIP6 projections of precipitation and rainfall extremes over Uttaradit Province, Thailand",
  styles: { default: { document: { run: { font: FONT, size: SZ } } } },
  sections: [{
    properties: {
      // APST: "Every line should have numeric identification."
      lineNumbers: { countBy: 1, start: 1, restart: d.LineNumberRestartFormat.CONTINUOUS },
      page: {
        size: { width: convertInchesToTwip(8.5), height: convertInchesToTwip(11) },
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
  const out = PATHS.out;
  fs.writeFileSync(out, buf);
  console.log("written:", out, (buf.length / 1024).toFixed(0) + " KB");
});
