import React from "react";

export const BOOK_URL = "https://bookme.ministryhub.org/search-strategy-consultation";
export const SITE_URL = "https://ministryhub.org";
// shortcut: the client hasn't sent these page addresses yet (NEW_PLAN.md Q12), so they open the main site
export const SERVICES_URL = SITE_URL;
export const HOW_URL = SITE_URL;
export const PRIVACY_URL = SITE_URL;

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

export const longDay = (value) => {
  if (!value) return "…";
  const d = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return isNaN(d) ? "…" : d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
};

export function Header() {
  return (
    <header className="mh-header">
      <div className="mh-wrap mh-header-inner">
        <a href="/" className="mh-logo-link"><img className="mh-logo" src="/ministryhub-logo.png" alt="MinistryHub" /></a>
        <nav className="mh-nav" aria-label="MinistryHub">
          <a href={SERVICES_URL}>Search Services</a>
          <a href={HOW_URL}>How a Search Works</a>
          <a className="mh-btn mh-btn-teal" href={BOOK_URL}>Book a Call</a>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mh-footer">
      <div className="mh-wrap mh-footer-inner">
        <div className="mh-footer-brand">
          <img className="mh-logo" src="/ministryhub-logo-white.png" alt="MinistryHub" />
          <strong>Power Your Mission With The Right Team.</strong>
        </div>
        <span>© {new Date().getFullYear()} MinistryHub · <a href={SITE_URL}>ministryhub.org</a> · <a href={PRIVACY_URL}>Privacy</a></span>
      </div>
    </footer>
  );
}

export function CallBand({ title, children, secondary }) {
  return (
    <section className="mh-band" data-reveal>
      <div>
        <h2>{title}</h2>
        <p>{children}</p>
      </div>
      <div className="mh-band-actions">
        <a className="mh-btn mh-btn-yellow" href={BOOK_URL}>Book a search strategy call</a>
        {secondary}
      </div>
    </section>
  );
}
