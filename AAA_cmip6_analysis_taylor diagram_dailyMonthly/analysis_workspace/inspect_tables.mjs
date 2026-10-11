import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const base = path.resolve("analysis_workspace", "future_zip", "output", "future_q1_uttaradit", "tables");
const names = process.argv.slice(2);
if (!names.length) {
  throw new Error("Pass one or more workbook file names");
}

for (const name of names) {
  const candidate = path.resolve(name);
  const filePath = path.isAbsolute(name) || name.includes("/") || name.includes("\\")
    ? candidate
    : path.join(base, name);
  const input = await FileBlob.load(filePath);
  const workbook = await SpreadsheetFile.importXlsx(input);
  const result = await workbook.inspect({
    kind: "workbook,sheet,table",
    maxChars: 60000,
    tableMaxRows: 200,
    tableMaxCols: 30,
    tableMaxCellChars: 120,
  });
  console.log(`===== ${name} =====`);
  console.log(result.ndjson);
}
