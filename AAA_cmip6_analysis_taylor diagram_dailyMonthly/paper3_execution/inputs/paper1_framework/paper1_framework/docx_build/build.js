const fs = require("fs");
const path = require("path");
const d = require("docx");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, ShadingType, BorderStyle, ImageRun,
  convertInchesToTwip,
} = d;

const FONT = "Times New Roman";
const SZ = 20, SZ_TITLE = 24, SZ_SMALL = 18, LINE = 480;
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
    children: rich(String(text), { bold: o.bold, size: SZ_SMALL }),
    alignment: o.align || AlignmentType.LEFT,
    spacing: { line: 240, before: 20, after: 20 },
  });
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
  children: rich("Near-Future Changes in Daily Precipitation and Selected Rainfall Extremes over Uttaradit, Thailand Using Bias-Corrected Global Climate Models", { bold: true, size: SZ_TITLE }),
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
body.push(P("**Keywords:** Daily rainfall, Hydroclimatic projection, Model evaluation, Northern Thailand, Quantile adjustment, Rainfall variability"));
body.push(BLANK());

// Body with tables and figures anchored after the subsection they support
const AFTER_SH = {
  "2.1 Study area and rain-gauge data": () => [
    figure("Paper1_Figure_01_study_area.png", 4.3),
    CAP("**Figure 1** Location of Uttaradit Province in Thailand (inset) and the 13 rain gauges used in this study, over terrain elevation. The provincial boundary is shown in black."),
  ],
  "2.3 CMIP6 data and model configuration": () => [
    CAP("**Table 1** Configuration of the seven CMIP6 models. \"Distinct series\" is the number of different daily series the 13 analysed gauges receive from that model, that is the number of native grid cells effectively serving the province.", { keepNext: true, after: 60 }),
    makeTable(["Model", "Institution", "Variant", "Grid", "Calendar", "Days", "Distinct series"],
      J("T2models.json").map((r) => [r.Model, r.Institution, r.Variant, r.Grid,
        r.Calendar, String(r["Days (1981\u20132014)"]), String(r["Distinct series"])]),
      [2.2, 3.0, 1.5, 0.9, 1.3, 1.2, 1.5], [L, L, L, C, L, R, C]),
  ],
  "3.1 Calibration-period performance": () => [
    CAP("**Table 2** Calibration-period (1981–2002) mean absolute bias, defined by Equation (2), of raw and QDM-corrected CMIP6 daily precipitation against gauge observations, averaged over 13 gauges and 7 models. Marginal-distribution performance only; this table does not imply correction of temporal sequencing or multi-day persistence. Signed biases and the full metric set are given in Supplementary Table S2.", { keepNext: true, after: 60 }),
    biasTable(J("T2.json")),
    figure("Paper1_Figure_02_calibration.png", 4.6),
    CAP("**Figure 2** Mean absolute bias of raw and QDM-corrected CMIP6 daily precipitation against gauge observations over the calibration period 1981\u20132002, averaged across 13 gauges and 7 models. The dotted divider separates statistics primarily controlled by the marginal daily distribution from sequence-dependent and multi-day statistics that are not explicitly reconstructed by quantile mapping."),
  ],
  "3.2 Independent validation": () => [
    CAP("**Table 3** Independent validation (2003\u20132014) of QDM-corrected CMIP6 precipitation against observations, using parameters fitted on 1981\u20132002 and frozen. Mean absolute bias as defined by Equation (2), averaged over 13 gauges and 7 models. Signed biases are given in Supplementary Table S3 and the homogeneity sensitivity in Supplementary Table S4.", { keepNext: true, after: 60 }),
    biasTable(J("T3.json")),
    figure("Paper1_Figure_03_validation.png", 4.6),
    CAP("**Figure 3** As Figure 2, for the independent validation period 2003\u20132014 using parameters fitted on 1981\u20132002 and frozen. Axes are identical to Figure 2 to allow direct comparison. CDD is the only index for which the corrected bias exceeds the raw bias."),
  ],
  "3.3 Near-future precipitation changes, 2021\u20132050": () => [
    CAP("**Table 4** Projected change for 2021\u20132050 relative to each model's own bias-corrected baseline (1995\u20132014), from Equation (3). For each scenario the ensemble median, the inter-model interquartile range in square brackets and the agreement fraction in parentheses are given; bold denotes agreement of at least 0.80. Indices marked \"diagnostic\" depend on the ordering of wet and dry days, which quantile mapping does not correct (Section 3.2).", { keepNext: true, after: 60 }),
    changeTable(J("T4.json")),
    figure("Paper1_Figure_04_near_future_precipitation.png", 5.1),
    CAP("**Figure 4** Projected change in precipitation characteristics for 2021\u20132050 relative to each model's own bias-corrected baseline (1995\u20132014). Bars are ensemble medians and whiskers denote the inter-model interquartile range, which represents inter-model spread and not a confidence interval. The number beneath each bar is the inter-model agreement fraction; bold marks agreement of at least 0.80, and those bars are filled solid."),
  ],
  "3.4 Near-future rainfall extremes": () => [
    figure("Paper1_Figure_05_near_future_extremes.png", 5.0),
    CAP("**Figure 5** As Figure 4, for the extreme-rainfall indices: (a) intensity and threshold indices and (b) tail and persistence indices. CDD, CWD and Rx5day depend on the ordering of wet and dry days, which quantile mapping does not correct; they are drawn as open hatched bars and are reported as diagnostics rather than as corrected projections."),
  ],
  "3.5 Gauge-level spatial pattern and model agreement": () => [
    figure("Paper1_Figure_06_near_future_map.png", 5.3),
    CAP("**Figure 6** Ensemble median change in annual precipitation for 2021\u20132050 relative to each model's own bias-corrected baseline. The shaded surface is an inverse-distance-weighted interpolation between the 13 gauges, for visualisation only, clipped to the verified provincial boundary; the gauges themselves are drawn on top, sized by the inter-model agreement fraction, with filled symbols for agreement of at least 0.80 and open symbols below it."),
  ],
};

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
    // equation body indented, number set off by a tab so it sits clear of the
    // expression whatever the renderer does with positional tabs
    const parts = s.v.split(/\s{2,}(\(\d\))$/);
    const kids = rich(parts[0].trim());
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
        spacing: { line: 240, after: 60 },
        indent: { left: convertInchesToTwip(0.3),
                  hanging: convertInchesToTwip(0.3) },
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
        size: { width: convertInchesToTwip(8.27), height: convertInchesToTwip(11.69) },
        margin: {
          top: convertInchesToTwip(1), bottom: convertInchesToTwip(1),
          left: convertInchesToTwip(1), right: convertInchesToTwip(1),
        },
      },
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = PATHS.out;
  fs.writeFileSync(out, buf);
  console.log("written:", out, (buf.length / 1024).toFixed(0) + " KB");
});
