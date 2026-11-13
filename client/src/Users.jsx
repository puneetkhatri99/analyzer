import React, { useEffect, useState } from "react";
import { postJSON } from "./api.js";
import { longDate } from "./format.js";

const ROLE_TEXT = { admin: "Admin", editor: "Read and write", viewer: "Read only" };
const ROLE_HELP = "Read only: sees the dashboard. Read and write: also adds and deletes jobs. Only admins manage users.";

// A one-time password the admin hands over; the user must replace it at first sign-in.
function newPassword() {
  const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789";
  const bytes = crypto.getRandomValues(new Uint8Array(12));
  return Array.from(bytes, (b) => chars[b % chars.length]).join("");
}

function CreateUser({ onCreated }) {
  const [form, setForm] = useState({ email: "", role: "viewer", password: newPassword() });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    postJSON("/api/admin/users", form)
      .then((u) => { onCreated({ ...u, password: form.password }); setForm({ email: "", role: "viewer", password: newPassword() }); })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <section className="card">
      <div className="card-head"><h2>Add a user</h2></div>
      <form className="user-form" onSubmit={submit}>
        <label className="field"><span>Email</span>
          <input className="control" type="email" required value={form.email} onChange={set("email")} />
        </label>
        <label className="field"><span>Access</span>
          <select className="control" value={form.role} onChange={set("role")}>
            <option value="viewer">Read only</option>
            <option value="editor">Read and write</option>
          </select>
        </label>
        <label className="field"><span>One-time password</span>
          <span className="user-password">
            <input className="control" required minLength={8} value={form.password} onChange={set("password")} />
            <button type="button" className="btn" onClick={() => setForm((f) => ({ ...f, password: newPassword() }))}>New</button>
          </span>
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Adding…" : "Add user"}</button>
      </form>
      <p className="muted small">{ROLE_HELP} The user signs in with the one-time password and must then choose their own.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  );
}

export default function Users({ me }) {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [handover, setHandover] = useState(null); // {email, password} to give to the user, shown once

  const load = () => fetch("/api/admin/users")
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Couldn’t load users (${r.status})`))))
    .then(setUsers)
    .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const act = (promise) => promise.then(load).catch((e) => setError(e.message));
  const changeRole = (u, role) => act(postJSON(`/api/admin/users/${encodeURIComponent(u.email)}`, { role }, "PATCH"));
  const resetPassword = (u) => {
    const password = newPassword();
    act(postJSON(`/api/admin/users/${encodeURIComponent(u.email)}`, { password }, "PATCH").then(() => setHandover({ email: u.email, password })));
  };
  const remove = (u) => window.confirm(`Remove ${u.email}? They will be signed out and can't sign in again.`)
    && act(postJSON(`/api/admin/users/${encodeURIComponent(u.email)}`, undefined, "DELETE"));

  return (
    <div className="stack">
      <CreateUser onCreated={(u) => { setHandover(u); load(); }} />
      {handover && (
        <div className="notice" role="status">
          <strong>Give {handover.email} this one-time password: <code>{handover.password}</code></strong>
          <span>It's shown only now. They'll be asked to change it when they sign in.</span>
          <button type="button" className="link-btn user-done" onClick={() => setHandover(null)}>Done</button>
        </div>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
      <section className="card">
        <div className="card-head"><h2>Users</h2></div>
        {!users ? <span className="skeleton" style={{ width: 240 }}>Loading</span> : (
          <table className="plain-table">
            <thead><tr><th>Email</th><th>Access</th><th>Status</th><th>Added</th><th className="r">Actions</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.email}>
                  <td>{u.email}{u.email === me ? <span className="muted"> (you)</span> : null}</td>
                  <td>
                    {u.role === "admin" ? ROLE_TEXT.admin : (
                      <select className="control" aria-label={`Access for ${u.email}`} value={u.role} onChange={(e) => changeRole(u, e.target.value)}>
                        <option value="viewer">Read only</option>
                        <option value="editor">Read and write</option>
                      </select>
                    )}
                  </td>
                  <td>{u.must_change_password ? "Waiting for first sign-in" : "Active"}</td>
                  <td className="muted">{longDate(u.created_at)}{u.created_by ? ` by ${u.created_by}` : ""}</td>
                  <td className="r">
                    {u.role !== "admin" && (
                      <span className="user-actions">
                        <button type="button" className="link-btn" onClick={() => resetPassword(u)}>Reset password</button>
                        <button type="button" className="link-btn danger" onClick={() => remove(u)}>Remove</button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
