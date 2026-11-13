import React, { useEffect, useState } from "react";
import { fetchReportOptions, postLead, reportQuery } from "./api.js";
import { CallBand, Footer, Header, PRIVACY_URL, forgetLead, longDay, saveLead, savedLead } from "./Brand.jsx";
import { money, moneyShort } from "./format.js";

const NATIONWIDE = "nationwide";

function Check() {
  return <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true"><circle cx="13" cy="13" r="13" fill="var(--mh-teal)" /><path d="M8 13.5l3.2 3.2L18 10" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

const FEATURES = [
  ["chart", "The pay range for your role", "Typical pay and the range most churches offer, for your role in your area."],
  ["filter", "How you compare", "Adjust by state, church size and denomination. Check an offer you're planning against the market."],
  ["doc", "A report you can share", "Download a prepared report for your board, elders or personnel committee."],
];
const ICONS = {
  chart: <path d="M7 17V11M11 17V7M15 17v-4M19 17V9" />,
  filter: <path d="M5 8h14M8 12h8M10.5 16h3" />,
  doc: <><path d="M8 4h6l4 4v12H8z" /><path d="M11 12h4M11 15h4" /></>,
};

export default function Landing() {
  const [opts, setOpts] = useState(null);
  const [lead, setLead] = useState(savedLead);
  const [form, setForm] = useState({ role: "", location: "", attendance: "", name: lead?.name || "", email: lead?.email || "", organization: lead?.organization || "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { fetchReportOptions().then(setOpts).catch(() => setError("We couldn't load the tool. Please refresh the page.")); }, []);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const openReport = () => {
    const state = form.location && form.location !== NATIONWIDE ? [form.location] : [];
    window.location.href = `/report?${reportQuery({ role: [form.role], state, size: form.attendance ? [form.attendance] : [] })}`;
  };

  const submit = (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const who = { name: form.name.trim(), email: form.email.trim(), organization: form.organization.trim() };
    postLead({ ...who, role: form.role, location: form.location, attendance: form.attendance || null })
      .then(() => { saveLead(who); openReport(); })
      .catch((err) => { setError(err.message); setBusy(false); });
  };

  const l = opts?.landing;
  return (
    <div className="mh">
      <Header />
      <main>
        <section className="mh-wrap mh-hero">
          <div className="mh-hero-copy">
            <p className="mh-eyebrow">MinistryHub Market Analysis Tool · Free</p>
            <h1>What are churches paying for this role <span className="mh-underline">right now?</span></h1>
            <p className="mh-lede">
              Live pay benchmarks drawn from {l?.openings_label || "thousands of"} active ministry job openings across the United States.
              Pick a role and a location and get your report in under a minute.
            </p>
            <ul className="mh-checks">
              <li><Check />Current openings, not last year's survey</li>
              <li><Check />Compare by state, church size and denomination</li>
              <li><Check />A ready-made report to share with your board or elders</li>
            </ul>
            <p className="mh-small">Built by the MinistryHub search team. Data as of {longDay(l?.as_of)}.</p>
          </div>

          <div className="mh-form-frame">
            <form className="mh-form" onSubmit={submit}>
              <h2>Get your free report</h2>
              <p className="mh-step"><span>1</span>What are you hiring for?</p>
              <div className="mh-row">
                <label className="mh-field">
                  <span>Role</span>
                  <select required value={form.role} onChange={set("role")}>
                    <option value="" disabled>Choose a role</option>
                    {opts?.roles.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </label>
                <label className="mh-field">
                  <span>Location</span>
                  <select required value={form.location} onChange={set("location")}>
                    <option value="" disabled>Choose a state</option>
                    <option value={NATIONWIDE}>Anywhere in the US</option>
                    {opts?.states.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </label>
              </div>
              <label className="mh-field">
                <span>Weekly attendance (optional)</span>
                <select value={form.attendance} onChange={set("attendance")}>
                  <option value="">Any size</option>
                  {opts?.sizes.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </label>

              {lead ? (
                <p className="mh-returning">
                  Welcome back, {lead.name}. <button type="button" className="mh-link" onClick={() => { forgetLead(); setLead(null); }}>Not you?</button>
                </p>
              ) : (
                <>
                  <p className="mh-step"><span>2</span>Where should we send it?</p>
                  <label className="mh-field"><span>Name</span><input required maxLength={200} autoComplete="name" placeholder="John Smith" value={form.name} onChange={set("name")} /></label>
                  <label className="mh-field"><span>Email</span><input required type="email" maxLength={320} autoComplete="email" placeholder="john@yourchurch.org" value={form.email} onChange={set("email")} /></label>
                  <label className="mh-field"><span>Church or organization</span><input required maxLength={300} autoComplete="organization" placeholder="Your church or organization" value={form.organization} onChange={set("organization")} /></label>
                </>
              )}

              {error && <p className="mh-error" role="alert">{error}</p>}
              <button type="submit" className="mh-btn mh-btn-yellow mh-btn-block" disabled={busy || !opts}>
                {busy ? "Preparing your report…" : <>See my report <span aria-hidden="true">→</span></>}
              </button>
              <p className="mh-fine">
                We'll email you a copy and occasional hiring insights. Unsubscribe anytime. See our <a href={PRIVACY_URL}>Privacy Policy</a>.
              </p>
            </form>
          </div>
        </section>

        <section className="mh-glance">
          <div className="mh-wrap">
            <p className="mh-eyebrow">The ministry job market at a glance</p>
            <div className="mh-glance-grid">
              <div><strong>{l?.typical ? money(l.typical) : "…"}</strong><span>Median pay across all ministry roles nationwide</span></div>
              <div><strong>{l?.low ? `${moneyShort(l.low)}–${moneyShort(l.high)}` : "…"}</strong><span>What the middle half of ministry roles pay</span></div>
              <div><strong>{l?.avg_attendance ?? "[XXX]"}</strong><span>Average weekly attendance of churches hiring</span></div>
              <div><strong>{l?.days_open != null ? `${l.days_open} days` : "[XX] days"}</strong><span>Typical time a ministry role stays open</span></div>
            </div>
          </div>
        </section>

        <section className="mh-wrap mh-section">
          <h2 className="mh-h2">What's in your report</h2>
          <p className="mh-sub">A clear answer first, then the detail if you want it.</p>
          <div className="mh-features">
            {FEATURES.map(([icon, title, text]) => (
              <div className="mh-feature" key={title}>
                <span className="mh-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{ICONS[icon]}</svg></span>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="mh-wrap mh-section-tight">
          <CallBand title="Hiring soon? Let's talk through your search.">
            MinistryHub equips churches and faith-based nonprofits to build world-changing staff teams. Grab a spot on
            Jordan's calendar for a search strategy consultation.
          </CallBand>
        </div>
      </main>
      <Footer />
    </div>
  );
}
