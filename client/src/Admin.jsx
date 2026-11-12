import React, { useEffect, useState } from "react";
import { Mark } from "./App.jsx";
import { postJSON } from "./api.js";
import AiCosts from "./AiCosts.jsx";
import { ORIGINS, count, listedPay } from "./format.js";

const DATASETS = { churches: "BizDev churches", nonprofits: "BizDev nonprofits" };

function Login({ onSignedIn }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    postJSON("/api/admin/login", { email, password })
      .then((r) => onSignedIn(r.email))
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <main className="login">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand"><Mark />Ministry Jobs Analyser</div>
        <h1>Admin sign in</h1>
        {/* TEMPORARY: reference login for testing. Delete this block before go-live. */}
        <div className="notice demo-login" role="note">
          <strong>Reference login</strong>
          <span>Email: <code>admin@example.com</code></span>
          <span>Password: <code>admin@123</code></span>
        </div>
        <label className="field">
          <span>Email</span>
          <input className="control" type="email" autoComplete="username" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span>Password</span>
          <input className="control" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <a className="muted small" href="/">Back to the dashboard</a>
      </form>
    </main>
  );
}

function JobDetails({ job }) {
  const pay = listedPay(job);
  const rows = [
    ["Job title", job.job_title],
    ["Organization", job.org_name],
    ["Website", job.org_website],
    ["Location", [job.city, job.state, job.country].filter(Boolean).join(", ")],
    ["Pay", pay && `${pay.amount} ${pay.unit}`],
    ["Job type", job.hours],
    ["Remote", job.remote == null ? null : job.remote ? "Yes" : "No"],
    ["Denomination", job.denomination],
    ["Church size", job.church_size != null && `${count(job.church_size)} weekly attendance`],
    ["Date posted", job.date_posted],
  ];
  return (
    <dl className="details">
      {rows.map(([label, value]) => (
        <React.Fragment key={label}>
          <dt>{label}</dt>
          <dd className={value ? "" : "muted"}>{value || "Not stated"}</dd>
        </React.Fragment>
      ))}
    </dl>
  );
}

function AddJob() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [dataset, setDataset] = useState("churches");
  const [saved, setSaved] = useState(null);

  const extract = (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    setSaved(null);
    postJSON("/api/admin/extract", { url: url.trim() })
      .then((r) => {
        setResult(r);
        setDataset(r.job.category === "church" ? "churches" : "nonprofits");
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  const save = () => {
    setBusy(true);
    setError(null);
    postJSON("/api/admin/jobs", { url: result.url, dataset, method: result.method, job: result.job, church_size_source: result.church_size_source })
      .then(() => setSaved(dataset))
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  const job = result?.job;
  return (
    <>
      <section className="card">
        <div className="card-head"><h2>Add a job from a URL</h2></div>
        <form className="url-form" onSubmit={extract}>
          <label className="sr-only" htmlFor="job-url">Job posting URL</label>
          <input id="job-url" className="control" type="url" required placeholder="https://… link to a single job posting"
            value={url} onChange={(e) => setUrl(e.target.value)} disabled={busy} />
          <button type="submit" className="btn btn-primary" disabled={busy || !url.trim()}>
            {busy && !result ? "Reading page…" : "Fetch job"}
          </button>
        </form>
        <p className="card-note">
          The page is read and an AI model extracts the job’s details. Blocked or JavaScript-only pages are read through web search,
          which can take up to a minute. Nothing is saved until you review it.
        </p>
        {error && <p className="form-error" role="alert">{error}</p>}
      </section>

      {job && job.page_type !== "job_posting" && (
        <section className="card notice" role="status">
          <strong>{job.page_type === "unreadable" ? "This page couldn’t be read as a job posting." : "This is not a job posting."}</strong>
          <span>{job.reason}</span>
        </section>
      )}

      {job && job.page_type === "job_posting" && (
        <section className="card">
          <div className="card-head">
            <h2>Review the extracted job</h2>
            <span className="meta">Will be saved as “{ORIGINS[`admin_${result.method}`]}”</span>
          </div>
          <p className="finding">{job.reason}</p>
          {result.warnings.length > 0 && (
            <ul className="card notice warnings" aria-label="Check before saving">
              {result.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          )}
          <JobDetails job={job} />
          <div className="save-row">
            <label className="field inline">
              <span>Add to</span>
              <select className="control" value={dataset} onChange={(e) => { setDataset(e.target.value); setSaved(null); }} disabled={busy}>
                {Object.entries(DATASETS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
            </label>
            <button type="button" className="btn btn-primary" onClick={save} disabled={busy || saved === dataset}>
              {saved === dataset ? "Saved" : busy ? "Saving…" : "Save job"}
            </button>
            {saved && (
              <a href={`/?source=${saved}&search=${encodeURIComponent(job.job_title || "")}`}>View it on the dashboard</a>
            )}
          </div>
          {job.category === "other" && <p className="card-note">The AI thinks this employer is a for-profit company. Check it belongs here before saving.</p>}
        </section>
      )}
    </>
  );
}

export default function Admin() {
  const [email, setEmail] = useState(undefined); // undefined = checking, null = signed out
  const [tab, setTab] = useState(window.location.hash === "#costs" ? "costs" : "add");
  const showTab = (next) => { setTab(next); window.history.replaceState(null, "", next === "costs" ? "#costs" : window.location.pathname); };

  useEffect(() => {
    fetch("/api/admin/me").then((r) => (r.ok ? r.json() : null)).then((r) => setEmail(r?.email ?? null)).catch(() => setEmail(null));
  }, []);

  if (email === undefined) return null;
  if (!email) return <Login onSignedIn={setEmail} />;

  const signOut = () => postJSON("/api/admin/logout", {}).finally(() => setEmail(null));
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand"><Mark />Ministry Jobs Analyser <span className="muted">· Admin</span></div>
          <div className="topbar-actions">
            <a href="/">Analyser</a>
            <span className="muted">{email}</span>
            <button type="button" className="link-btn" onClick={signOut}>Sign out</button>
          </div>
        </div>
      </header>
      <main className="canvas admin">
        <nav className="admin-tabs" aria-label="Admin sections">
          {[["add", "Add a job"], ["costs", "AI costs"]].map(([key, label]) => (
            <button key={key} type="button" className="admin-tab" aria-current={tab === key ? "page" : undefined} onClick={() => showTab(key)}>{label}</button>
          ))}
        </nav>
        {tab === "add" ? <AddJob /> : <AiCosts />}
      </main>
    </>
  );
}
