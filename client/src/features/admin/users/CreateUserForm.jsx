import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import AccessSelect from "./AccessSelect.jsx";
import { newPassword } from "./password.js";

const ROLE_HELP = "Read only: sees the dashboard. Read and write: also adds and deletes jobs. Only admins manage users.";
const blank = () => ({ email: "", role: "viewer", password: newPassword() });

export default function CreateUserForm({ onCreate }) {
  const [form, setForm] = useState(blank);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (value) => setForm((f) => ({ ...f, [key]: value }));

  const submit = (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    onCreate(form)
      .then(() => setForm(blank()))
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <Card>
      <CardHeader><CardTitle>Add a user</CardTitle></CardHeader>
      <form className="user-form" onSubmit={submit}>
        <div className="grid gap-1.5">
          <Label htmlFor="new-email">Email</Label>
          <Input id="new-email" type="email" required value={form.email} onChange={(e) => set("email")(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="new-role">Access</Label>
          <AccessSelect id="new-role" value={form.role} onChange={set("role")} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="new-password">One-time password</Label>
          <span className="flex gap-2">
            <Input id="new-password" className="font-mono" required minLength={8} value={form.password} onChange={(e) => set("password")(e.target.value)} />
            <Button type="button" variant="outline" onClick={() => set("password")(newPassword())}>New</Button>
          </span>
        </div>
        <Button type="submit" disabled={busy}>{busy ? "Adding…" : "Add user"}</Button>
      </form>
      <p className="card-note">{ROLE_HELP} The user signs in with the one-time password and must then choose their own.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
    </Card>
  );
}
