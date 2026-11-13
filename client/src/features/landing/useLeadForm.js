import { useState } from "react";
import { postLead, reportQuery } from "@/api/report.js";
import { forgetLead, saveLead, savedLead } from "@/features/site/lead.js";

export const NATIONWIDE = "nationwide";
export const ANY_SIZE = "any"; // Radix Select can't hold "", so "Any size" has a value of its own

// The landing form: what the visitor is hiring for, who they are, and the jump to their report.
export function useLeadForm() {
  const [lead, setLead] = useState(savedLead);
  const [form, setForm] = useState({
    role: "", location: "", attendance: ANY_SIZE,
    name: lead?.name || "", email: lead?.email || "", organization: lead?.organization || "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [missing, setMissing] = useState([]);

  // works for both select values and input change events
  const set = (key) => (value) => setForm((f) => ({ ...f, [key]: value?.target ? value.target.value : value }));
  const forget = () => { forgetLead(); setLead(null); };

  const openReport = () => {
    const state = form.location !== NATIONWIDE ? [form.location] : [];
    const size = form.attendance !== ANY_SIZE ? [form.attendance] : [];
    window.location.href = `/report?${reportQuery({ role: [form.role], state, size })}`;
  };

  const submit = (e) => {
    e.preventDefault();
    // Radix selects aren't native inputs, so the browser can't check them; this does.
    const empty = ["role", "location"].filter((k) => !form[k]);
    setMissing(empty);
    if (empty.length) {
      setError("Choose a role and a location to see your report.");
      document.getElementById(`lead-${empty[0]}`)?.focus();
      return;
    }
    setBusy(true);
    setError(null);
    const who = { name: form.name.trim(), email: form.email.trim(), organization: form.organization.trim() };
    const attendance = form.attendance === ANY_SIZE ? null : form.attendance;
    postLead({ ...who, role: form.role, location: form.location, attendance })
      .then(() => { saveLead(who); openReport(); })
      .catch((err) => { setError(err.message); setBusy(false); });
  };

  return { lead, form, set, forget, submit, busy, error, missing };
}
