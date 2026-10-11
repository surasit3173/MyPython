import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const runDir = path.resolve(process.argv[2] ?? "");
if (!runDir) throw new Error("Usage: node build_results_workbook.mjs <run-directory>");
const tablesDir = path.join(runDir, "tables");
const previewDir = path.join(runDir, "validation", "workbook_previews");
await fs.mkdir(previewDir, { recursive: true });

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  const clean = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < clean.length; i += 1) {
    const ch = clean[i];
    if (quoted) {
      if (ch === '"' && clean[i + 1] === '"') { field += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += ch;
  }
  if (field.length || row.length) { row.push(field.replace(/\r$/, "")); rows.push(row); }
  const headers = rows[0];
  const textFields = new Set(["station_id", "key", "method", "period", "scope", "status", "family", "significant_lags", "metric", "unit"]);
  return rows.map((values, rowIndex) => values.map((value, columnIndex) => {
    if (rowIndex === 0 || textFields.has(headers[columnIndex])) return value;
    if (value === "") return null;
    if (value === "True" || value === "true") return true;
    if (value === "False" || value === "false") return false;
    if (/^-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(value)) return Number(value);
    return value;
  }));
}

async function loadCsv(file) {
  return parseCsv(await fs.readFile(path.join(tablesDir, file), "utf8"));
}

function colName(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) { value -= 1; result = String.fromCharCode(65 + (value % 26)) + result; value = Math.floor(value / 26); }
  return result;
}

const workbook = Workbook.create();
const fontName = "Arial";
const navy = "#17365D";
const blue = "#DCE6F1";
const lightBlue = "#F4F8FC";
const border = "#C7D1DB";

function styleDataSheet(sheet, matrix, tableName) {
  const rows = matrix.length;
  const cols = matrix[0].length;
  const used = sheet.getRangeByIndexes(0, 0, rows, cols);
  used.values = matrix;
  used.format.font = { name: fontName, size: 9 };
  used.format.verticalAlignment = "center";
  used.format.borders = { preset: "all", style: "thin", color: border };
  const header = sheet.getRangeByIndexes(0, 0, 1, cols);
  header.format.fill = navy;
  header.format.font = { name: fontName, size: 9, bold: true, color: "#FFFFFF" };
  header.format.wrapText = true;
  header.format.rowHeightPx = 34;
  for (let c = 0; c < cols; c += 1) {
    const headerName = String(matrix[0][c]);
    const width = Math.min(34, Math.max(11, headerName.length + 2, ...matrix.slice(1, 40).map(row => String(row[c] ?? "").length + 1)));
    sheet.getRangeByIndexes(0, c, rows, 1).format.columnWidth = width;
    const lower = headerName.toLowerCase();
    if (["year", "n", "reps", "seed", "stations", "station_count", "valid_days", "expected_days", "block_length", "invalid_replicates", "invalid_series"].includes(lower)) {
      sheet.getRangeByIndexes(1, c, Math.max(rows - 1, 1), 1).format.numberFormat = "0";
    } else if (lower.includes("p_value") || lower.includes("q_value") || lower.includes("fdr") || lower.includes("fwer") || lower.includes("mcse") || lower.includes("alpha") || lower.includes("phi") || lower.includes("tau") || lower.includes("correction") || lower.includes("completeness") || lower === "estimate" || lower.startsWith("ci_")) {
      sheet.getRangeByIndexes(1, c, Math.max(rows - 1, 1), 1).format.numberFormat = "0.0000";
    } else if (lower.includes("slope") || lower.includes("intercept") || lower.includes("rain") || lower.includes("total") || lower.includes("mean_mm") || lower === "s") {
      sheet.getRangeByIndexes(1, c, Math.max(rows - 1, 1), 1).format.numberFormat = "0.00";
    }
  }
  sheet.freezePanes.freezeRows(1);
  sheet.showGridLines = false;
  const rangeAddress = `A1:${colName(cols - 1)}${rows}`;
  const table = sheet.tables.add(rangeAddress, true, tableName);
  table.style = "TableStyleMedium2";
  table.showBandedRows = true;
  return { rows, cols, headers: matrix[0] };
}

const datasets = [
  ["Data Quality", "data_quality.csv", "DataQualityTable"],
  ["Network Results", "network_results.csv", "NetworkResultsTable"],
  ["Station Results", "station_results.csv", "StationResultsTable"],
  ["Bootstrap CI", "bootstrap_ci.csv", "BootstrapCITable"],
  ["Method Simulation", "method_simulation.csv", "MethodSimulationTable"],
  ["FDR Simulation", "fdr_simulation.csv", "FDRSimulationTable"],
];
const loaded = new Map();
for (const [name, file] of datasets) loaded.set(name, await loadCsv(file));

const summary = workbook.worksheets.add("Summary");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Prachuap Khiri Khan Rainfall Trend Analysis — Version 5"]];
summary.getRange("A1:H1").format = { fill: navy, font: { name: fontName, size: 16, bold: true, color: "#FFFFFF" }, verticalAlignment: "center" };
summary.getRange("A1:H1").format.rowHeightPx = 34;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["Complete-period, fail-closed analysis; values trace to the immutable run manifest and CSV tables."]];
summary.getRange("A2:H2").format = { fill: blue, font: { name: fontName, size: 10, italic: true, color: "#333333" }, wrapText: true };
summary.getRange("A4:A6").values = [["Stations"], ["Station-level BH discoveries"], ["Network-level BH discoveries"]];
summary.getRange("A4:A6").format.font = { name: fontName, bold: true, size: 10 };

for (const [name, , tableName] of datasets) {
  const sheet = workbook.worksheets.add(name);
  const info = styleDataSheet(sheet, loaded.get(name), tableName);
  sheet.tabColor = name.includes("Simulation") ? "#D97706" : "#1F4E78";
  if (name === "Station Results" || name === "Network Results") {
    const qIndex = info.headers.indexOf("q_value");
    if (qIndex >= 0) sheet.getRangeByIndexes(1, qIndex, info.rows - 1, 1).conditionalFormats.add("cellIs", { operator: "lessThanOrEqual", formula: 0.05, format: { fill: "#D9EAD3", font: { bold: true, color: "#274E13" } } });
  }
}

const dataQualityHeaders = loaded.get("Data Quality")[0];
const dqValueCol = colName(dataQualityHeaders.indexOf("value"));
summary.getRange("B4").formulas = [[`='Data Quality'!${dqValueCol}2`]];
const stationHeaders = loaded.get("Station Results")[0];
const stationRejectCol = colName(stationHeaders.indexOf("reject_bh"));
const stationRows = loaded.get("Station Results").length;
const stationDecisionCount = loaded.get("Station Results").slice(1).filter(row => row[stationHeaders.indexOf("reject_bh")] === true).length;
summary.getRange("B5").values = [[stationDecisionCount]];
const networkHeaders = loaded.get("Network Results")[0];
const networkRejectCol = colName(networkHeaders.indexOf("reject_bh"));
const networkRows = loaded.get("Network Results").length;
const networkDecisionCount = loaded.get("Network Results").slice(1).filter(row => row[networkHeaders.indexOf("reject_bh")] === true).length;
summary.getRange("B6").values = [[networkDecisionCount]];
summary.getRange("B4:B6").format = { fill: lightBlue, font: { name: fontName, size: 11, bold: true }, numberFormat: "0", borders: { preset: "all", style: "thin", color: border } };

const networkMatrix = loaded.get("Network Results");
const nh = networkMatrix[0];
const mkRows = networkMatrix.slice(1).filter(row => row[nh.indexOf("method")] === "MK");
summary.getRange("A8:H8").values = [["Period", "Method", "N", "Sen slope (mm/year)", "Raw p", "BH q", "BH reject", "Interpretation"]];
summary.getRange("A8:H8").format = { fill: navy, font: { name: fontName, bold: true, color: "#FFFFFF" }, wrapText: true, borders: { preset: "all", style: "thin", color: border } };
const mkSummary = mkRows.map(row => {
  const period = row[nh.indexOf("period")];
  const q = row[nh.indexOf("q_value")];
  return [period, "MK", row[nh.indexOf("n")], row[nh.indexOf("slope")], row[nh.indexOf("p_value")], q, row[nh.indexOf("reject_bh")], q <= 0.05 ? "Detected after BH" : "Not detected after BH"];
});
summary.getRangeByIndexes(8, 0, mkSummary.length, 8).values = mkSummary;
summary.getRange(`A9:H${8 + mkSummary.length}`).format = { font: { name: fontName, size: 9 }, borders: { preset: "all", style: "thin", color: border } };
summary.getRange(`D9:F${8 + mkSummary.length}`).format.numberFormat = "0.000";

summary.getRange("A14:H14").merge();
summary.getRange("A14").values = [["Interpretation guardrails"]];
summary.getRange("A14:H14").format = { fill: blue, font: { name: fontName, bold: true, color: navy } };
summary.getRange("A15:H18").merge(true);
summary.getRange("A15:A18").values = [["• Network results are equal-weight gauge means, not province-wide areal rainfall."], ["• HR-MMK-3 is a prespecified three-lag sensitivity variant; simulation does not show universal calibration."], ["• Station discoveries depend on method and BH family; raw p-values are not multiplicity-adjusted evidence."], ["• Dry labels denote the year in which the November–April season ends; partial 1981 and 2015 seasons are excluded."]];
summary.getRange("A15:H18").format = { fill: lightBlue, font: { name: fontName, size: 9 }, wrapText: true, borders: { preset: "all", style: "thin", color: border } };
summary.getRange("A15:H18").format.rowHeightPx = 29;
summary.getRange("A1:H18").format.columnWidth = 16;
summary.getRange("A1:A18").format.columnWidth = 23;
summary.getRange("H1:H18").format.columnWidth = 28;
summary.freezePanes.freezeRows(2);
summary.tabColor = navy;

const sources = workbook.worksheets.add("Sources");
const manifest = JSON.parse(await fs.readFile(path.join(runDir, "run_manifest.json"), "utf8"));
const sourceRows = [
  ["Category", "Source", "SHA-256 / DOI", "Purpose"],
  ["Input", manifest.inputs.rainfall.path, manifest.inputs.rainfall.sha256, "Daily observed rainfall"],
  ["Input", manifest.inputs.station_metadata.path, manifest.inputs.station_metadata.sha256, "Station coordinates and elevation metadata"],
  ["Configuration", manifest.inputs.config.path, manifest.inputs.config.sha256, "Analysis contract"],
  ["Method", "https://www.sciencedirect.com/science/article/pii/S002216949700125X", "10.1016/S0022-1694(97)00125-X", "Hamed–Rao variance correction"],
  ["Method", "https://rss.onlinelibrary.wiley.com/doi/pdf/10.1111/j.2517-6161.1995.tb02031.x", "10.1111/j.2517-6161.1995.tb02031.x", "Benjamini–Hochberg FDR"],
  ["Method", "https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2001WR000861", "10.1029/2001WR000861", "Prewhitening limitation"],
];
styleDataSheet(sources, sourceRows, "SourcesTable");
sources.getRange("B1:B7").format.columnWidth = 58;
sources.getRange("C1:C7").format.columnWidth = 66;
sources.getRange("D1:D7").format.columnWidth = 32;
sources.tabColor = "#6B7280";

const fdrSheet = workbook.worksheets.getItem("FDR Simulation");
const fdrHeaders = loaded.get("FDR Simulation")[0];
const methodCol = colName(fdrHeaders.indexOf("method"));
const fdrCol = colName(fdrHeaders.indexOf("fdr"));
const fdrRows = loaded.get("FDR Simulation").length;
const chart = fdrSheet.charts.add("bar", [fdrSheet.getRange(`${methodCol}1:${methodCol}${fdrRows}`), fdrSheet.getRange(`${fdrCol}1:${fdrCol}${fdrRows}`)]);
chart.title = "Complete-null FDR by method";
chart.titleTextStyle.typeface = fontName;
chart.hasLegend = false;
chart.xAxis = { axisType: "textAxis", textStyle: { typeface: fontName, fontSize: 9 } };
chart.yAxis = { numberFormatCode: "0.0%", numberFormatSourceLinked: false, textStyle: { typeface: fontName, fontSize: 9 } };
chart.setPosition("P2", "W18");

const summaryInspect = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 12000, tableMaxRows: 4, tableMaxCols: 8 });
await fs.mkdir(path.join(runDir, "validation"), { recursive: true });
await fs.writeFile(path.join(runDir, "validation", "workbook_inspection.txt"), summaryInspect.ndjson ?? String(summaryInspect), "utf8");

const formulaErrors = [];
for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange(true);
  if (!used) continue;
  const values = used.values;
  for (let r = 0; r < values.length; r += 1) for (let c = 0; c < values[r].length; c += 1) {
    if (typeof values[r][c] === "string" && /^#(?:REF!|DIV\/0!|VALUE!|NAME\?|N\/A|NUM!|NULL!)/.test(values[r][c])) formulaErrors.push(`${sheet.name}!${colName(c)}${r + 1}:${values[r][c]}`);
  }
}
await fs.writeFile(path.join(runDir, "validation", "workbook_formula_errors.json"), JSON.stringify(formulaErrors, null, 2), "utf8");
if (formulaErrors.length) throw new Error(`Formula errors found: ${formulaErrors.join(", ")}`);

for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" });
  const safeName = sheet.name.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  await fs.writeFile(path.join(previewDir, `${safeName}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(runDir, "Prachuap_Rainfall_Trend_Results.xlsx"));
console.log(path.join(runDir, "Prachuap_Rainfall_Trend_Results.xlsx"));
