import { beacon } from "@/api/http.js";

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

// One step in the signed-up visitor's history (admin → Leads). Nothing is sent for a visitor who hasn't signed up.
// type: report | offer | download | cta | click (server/app/leads/router.py EventType)
export function track(type, details = {}) {
  const lead = savedLead();
  if (lead?.email) beacon("/api/leads/events", { email: lead.email, type, details });
}
