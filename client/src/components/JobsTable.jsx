import React, { useEffect, useRef } from "react";
import { TabulatorFull as Tabulator } from "tabulator-tables";
import "tabulator-tables/dist/css/tabulator.min.css";
import { ORIGINS, isoDate, listedPay } from "../format.js";

function esc(s) {
  return (s == null ? "" : String(s)).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

const DASH = '<span class="dash">—</span>';
const location = (d) => [d.city, d.region].filter(Boolean).join(", ") || d.country || "";
const payText = (d) => {
  const p = listedPay(d);
  return p ? `${p.amount} ${p.unit}` : "";
};

const COLUMNS = [
  {
    title: "Job", field: "job_name", minWidth: 200, widthGrow: 3, responsive: 0,
    formatter: (cell) => {
      const d = cell.getData();
      const title = esc(d.job_name || "Untitled role");
      // A button so keyboard users can open the details too; the click bubbles to the row handler.
      return `<button type="button" class="job-title">${title}</button><div class="job-sub">${esc(d.company_name || "Employer not stated")}</div>`;
    },
  },
  { title: "Role", field: "role", minWidth: 150, widthGrow: 1, responsive: 2 },
  { title: "Denomination", field: "denomination", minWidth: 140, widthGrow: 1, responsive: 4, formatter: (c) => esc(c.getValue()) || DASH },
  { title: "Location", field: "region", minWidth: 150, widthGrow: 1, responsive: 1, formatter: (c) => esc(location(c.getData())) || DASH, accessorDownload: (_v, d) => location(d) },
  {
    title: "Pay", field: "salary_annual_mid", minWidth: 130, responsive: 0, hozAlign: "right", headerHozAlign: "right",
    sorter: "number", sorterParams: { alignEmptyValues: "bottom" },
    formatter: (c) => {
      const p = listedPay(c.getData());
      return p ? `<span class="num">${p.amount}</span><span class="pay-unit">${p.unit}</span>` : DASH;
    },
    accessorDownload: (_v, d) => payText(d),
  },
  {
    title: "Status", field: "status", minWidth: 160, responsive: 3,
    formatter: (c) => {
      const d = c.getData();
      if (d.status === "expired") return `<span class="status expired" title="${d.last_live_at ? `Last seen open ${isoDate(d.last_live_at)}` : "Never seen open"}">Expired <span class="num">${isoDate(d.expired_at)}</span></span>`;
      if (d.status === "open") return `<span class="status open" title="Checked open on ${isoDate(d.last_live_at)}">Open</span>`;
      return `<span class="status" title="The job page couldn't be read, so it isn't known whether it's still open">Not verified</span>`;
    },
    accessorDownload: (_v, d) => (d.status === "expired" ? `Expired ${isoDate(d.expired_at)}` : d.status === "open" ? "Open" : "Not verified"),
  },
  {
    title: "Added via", field: "origin", minWidth: 140, responsive: 2,
    formatter: (c) => `<span class="origin" title="Added ${isoDate(c.getData().added_at)}">${esc(ORIGINS[c.getValue()] || c.getValue())}</span>`,
    accessorDownload: (v) => ORIGINS[v] || v,
  },
  { title: "Type", field: "hours", minWidth: 100, responsive: 3, formatter: (c) => esc(c.getValue()) || DASH },
  {
    title: "Posted", field: "first_indexed", minWidth: 110, responsive: 2, hozAlign: "right", headerHozAlign: "right",
    formatter: (c) => `<span class="num">${isoDate(c.getValue())}</span>`, accessorDownload: (v) => isoDate(v),
  },
  { title: "Employer", field: "company_name", visible: false, download: true },
  { title: "Link", field: "post_url", visible: false, download: true },
];

export default function JobsTable({ rows, onReady, onOpen }) {
  const el = useRef(null);
  const table = useRef(null);
  const built = useRef(false);
  const latest = useRef(rows);
  latest.current = rows;

  useEffect(() => {
    const t = new Tabulator(el.current, {
      data: latest.current,
      columns: COLUMNS,
      index: "post_uuid",
      layout: "fitColumns",
      responsiveLayout: "hide",
      pagination: true,
      paginationSize: 25,
      paginationSizeSelector: [25, 50, 100],
      paginationCounter: (size, current, page, total, pages) =>
        total ? `${(page - 1) * size + 1}–${Math.min(page * size, total)} of ${total.toLocaleString("en-US")}` : "",
      placeholder: "No postings match these filters.",
      initialSort: [{ column: "first_indexed", dir: "desc" }],
      columnDefaults: { headerSortTristate: false, resizable: false },
    });
    t.on("rowClick", (_e, row) => onOpen?.(row.getData()));
    t.on("tableBuilt", () => {
      built.current = true;
      t.setData(latest.current);
      onReady?.(t);
    });
    table.current = t;
    return () => {
      built.current = false;
      t.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (built.current) table.current.setData(rows);
  }, [rows]);

  return <div ref={el} />;
}
