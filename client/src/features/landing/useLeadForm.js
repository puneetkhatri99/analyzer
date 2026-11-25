import { useState } from "react";
import { postLead, reportQuery } from "@/api/report.js";
import { filtersFromUrl } from "@/lib/filters.js";
import { nextReport } from "@/lib/share.js";
import { forgetLead, saveLead, savedLead } from "@/lib/lead.js";

export const NATIONWIDE = "nationwide";
export const ANY_SIZE = "any"; // Radix Select can't hold "", so "Any size" has a value of its own

// The landing form: what the visitor is hiring for, who they are, and the jump to their report.
// From a shared link ("/?next=/report?…") the report is already chosen, so only who they are is asked.
export function useLeadForm() {
  const [lead, setLead] = useState(savedLead);
  const [next] = useState(nextReport);
  const [form, setForm] = useState({
    role: "", location: "", attendance: ANY_SIZE,
    name: lead?.name || "", email: lead?.email || "", organization: lead?.organization || "",
    emailReport: false,
    newsletter: false, // unticked until the visitor asks: only they can add themselves to the newsletter
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [missing, setMissing] = useState([]);

  // works for select values, input change events and the email switch (a checkbox)
  const set = (key) => (value) => setForm((f) => ({
    ...f, [key]: value?.target ? (value.target.type === "checkbox" ? value.target.checked : value.target.value) : value,
  }));
  // "Not you?": also empty the fields, so the next person on a shared computer doesn't see (or send as) this one
  const forget = () => { forgetLead(); setLead(null); setForm((f) => ({ ...f, name: "", email: "", organization: "" })); };

  // the report's query string: the shared one, or the visitor's choices
  const reportSearch = () => {
    if (next) return new URL(next, window.location.origin).search.slice(1);
    const state = form.location !== NATIONWIDE ? [form.location] : [];
    const size = form.attendance !== ANY_SIZE ? [form.attendance] : [];
    return reportQuery({ role: [form.role], state, size });
  };
  const openReport = () => { window.location.href = next || `/report?${reportSearch()}`; };

  // Radix selects aren't native inputs, so the browser can't check them; this does. It runs on the submit button's
  // click, before the browser checks the name and email, so the form is checked top to bottom.
  const checkChoices = (e) => {
    const empty = next ? [] : ["role", "location"].filter((k) => !form[k]);
    setMissing(empty);
    if (!empty.length) return true;
    e?.preventDefault();
    setError("Choose a role and a location to see your report.");
    document.getElementById(`lead-${empty[0]}`)?.focus();
    return false;
  };

  const submit = (e) => {
    e.preventDefault();
    if (!checkChoices()) return;
    setBusy(true);
    setError(null);
    const who = { name: form.name.trim(), email: form.email.trim(), organization: form.organization.trim() };
    const attendance = form.attendance === ANY_SIZE ? null : form.attendance;
    // a shared report's own search is what gets recorded for this lead
    const shared = next && filtersFromUrl(new URL(next, window.location.origin).search);
    const list = (values, max) => values.join(", ").slice(0, max) || null; // the API's length limits
    const search = shared
      ? { role: list(shared.role, 200), location: list(shared.state, 200) || NATIONWIDE, attendance: list(shared.size, 100) }
      : { role: form.role, location: form.location, attendance };
    postLead({ ...who, ...search, shared: Boolean(next), email_report: form.emailReport, newsletter: form.newsletter, report: reportSearch() })
      .then(() => { saveLead(who); openReport(); })
      .catch((err) => { setError(err.message); setBusy(false); });
  };

  return { lead, next, form, set, forget, submit, checkChoices, busy, error, missing };
}
