// The visitor's sign-up, kept in this browser so a returning visitor skips the form. Storage can be blocked.
const LEAD_KEY = "mh_lead";

export function savedLead() {
  try { return JSON.parse(localStorage.getItem(LEAD_KEY)) || null; } catch { return null; }
}
export function saveLead(lead) {
  try { localStorage.setItem(LEAD_KEY, JSON.stringify(lead)); } catch { /* the report still opens this time */ }
}
export function forgetLead() {
  try { localStorage.removeItem(LEAD_KEY); } catch { /* nothing stored */ }
}
