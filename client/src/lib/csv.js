// CSV for the postings export. columns: [[header, row => value], …]
const cell = (v) => {
  let s = v == null ? "" : String(v);
  if (typeof v === "string" && /^[=+\-@\t\r]/.test(s)) s = `'${s}`; // Excel would run it as a formula
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export const toCsv = (rows, columns) =>
  [columns.map(([h]) => cell(h)), ...rows.map((r) => columns.map(([, get]) => cell(get(r))))].map((line) => line.join(",")).join("\r\n");

export function downloadCsv(text, filename) {
  // the BOM tells Excel the file is UTF-8, so curly quotes and accents show correctly
  const url = URL.createObjectURL(new Blob(["﻿", text], { type: "text/csv;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}
