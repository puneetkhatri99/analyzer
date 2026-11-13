import React, { useState } from "react";
import { postJSON } from "./api.js";

// forced: first sign-in with a password an admin gave, so nothing else is reachable until it's changed.
export default function ChangePassword({ forced, onDone }) {
  const [form, setForm] = useState({ current: "", next: "", again: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = (e) => {
    e.preventDefault();
    if (form.next !== form.again) return setError("The new passwords don't match.");
    setBusy(true);
    setError(null);
    postJSON("/api/admin/password", { current_password: form.current, new_password: form.next })
      .then(() => { setDone(true); setForm({ current: "", next: "", again: "" }); onDone?.(); })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <form className="card login-card" onSubmit={submit}>
      <h1>{forced ? "Choose your own password" : "Change your password"}</h1>
      {forced && <p className="muted">You signed in with a one-time password from an admin. Choose a new one to continue.</p>}
      <label className="field"><span>{forced ? "One-time password" : "Current password"}</span>
        <input className="control" type="password" autoComplete="current-password" required value={form.current} onChange={set("current")} />
      </label>
      <label className="field"><span>New password (at least 8 characters)</span>
        <input className="control" type="password" autoComplete="new-password" required minLength={8} value={form.next} onChange={set("next")} />
      </label>
      <label className="field"><span>New password again</span>
        <input className="control" type="password" autoComplete="new-password" required minLength={8} value={form.again} onChange={set("again")} />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      {done && !forced && <p className="muted" role="status">Password changed. Your other sessions were signed out.</p>}
      <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save password"}</button>
    </form>
  );
}
