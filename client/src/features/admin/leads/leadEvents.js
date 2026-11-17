import { pay } from "../../report/lib/pay.js"; // relative so node --test can run it

const join = (...parts) => parts.flat().filter(Boolean).join(" · ");
const REPORT_TITLE = { open: "Opened a report", update: "Updated the report", reset: "Reset the filters" };

// One history row in words: [what happened, the details]. Event types: server/app/leads/router.py
export function describe({ type, details: d = {} }) {
  switch (type) {
    case "signup":
      return [d.shared ? "Signed up to open a shared report" : "Signed up", join(d.role, d.location, d.attendance, d.organization)];
    case "report":
      return [
        REPORT_TITLE[d.trigger] || "Viewed a report",
        join(d.shown, d.size, d.denomination, d.type === "part-time" && "part-time", d.widened_to && `widened to ${d.widened_to}`),
      ];
    case "offer":
      return [`Checked an offer of ${pay(d.amount, d.unit)}${d.unit === "hour" ? " an hour" : " a year"}`, join(d.verdict, d.report)];
    case "share_link":
      return ["Copied a share link", d.report];
    case "share_email":
      return ["Emailed the report link", d.report];
    case "download":
      return ["Downloaded the report (PDF)", d.report];
    case "cta":
      return [`Went to MinistryHub: “${d.label || "a link"}”`, d.url];
    case "click":
      return [`Clicked “${d.label}”`, d.page === "/report" ? "on the report" : d.page === "/" ? "on the landing page" : d.page];
    default:
      return [type, ""];
  }
}
