// Sharing a report: its URL already holds every filter. Someone who opens it without signing up is sent to the
// sign-up form first (ReportPage) and then lands back on this exact report (useLeadForm).
export function shareLinks(href, title) {
  const url = new URL(href).toString();
  const subject = `${title} | MinistryHub Market Analysis`;
  const body = `Here's the ministry pay report I put together with MinistryHub:\n\n${title}\n${url}`;
  return { url, mailto: `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}` };
}

// The report to open after sign-up, from "/?next=…". Only report pages, so the link can't redirect elsewhere.
export function nextReport(search = window.location.search) {
  const next = new URLSearchParams(search).get("next") || "";
  return next.startsWith("/report?") || next === "/report" ? next : null;
}
