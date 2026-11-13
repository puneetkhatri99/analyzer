import React, { useState } from "react";
import { changePassword } from "@/api/admin.js";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const FIELDS = [
  ["current", "current-password", 0],
  ["next", "new-password", 8],
  ["again", "new-password", 8],
];

// forced: first sign-in with a password an admin gave, so nothing else is reachable until it's changed.
export default function ChangePasswordForm({ forced, onDone }) {
  const [form, setForm] = useState({ current: "", next: "", again: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const labels = {
    current: forced ? "One-time password" : "Current password",
    next: "New password (at least 8 characters)",
    again: "New password again",
  };

  const submit = (e) => {
    e.preventDefault();
    if (form.next !== form.again) return setError("The new passwords don't match.");
    setBusy(true);
    setError(null);
    changePassword(form.current, form.next)
      .then(() => { setDone(true); setForm({ current: "", next: "", again: "" }); onDone?.(); })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <Card className="w-full max-w-[380px] p-7">
      <form className="flex flex-col gap-4" onSubmit={submit}>
        <h1 className="m-0 text-xl font-semibold">{forced ? "Choose your own password" : "Change your password"}</h1>
        {forced && <p className="muted m-0">You signed in with a one-time password from an admin. Choose a new one to continue.</p>}
        {FIELDS.map(([key, autoComplete, minLength]) => (
          <div className="grid gap-1.5" key={key}>
            <Label htmlFor={`pw-${key}`}>{labels[key]}</Label>
            <Input id={`pw-${key}`} type="password" autoComplete={autoComplete} required minLength={minLength || undefined}
              value={form[key]} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} />
          </div>
        ))}
        {error && <p className="form-error" role="alert">{error}</p>}
        {done && !forced && <p className="muted m-0" role="status">Password changed. Your other sessions were signed out.</p>}
        <Button type="submit" className="w-full" disabled={busy}>{busy ? "Saving…" : "Save password"}</Button>
      </form>
    </Card>
  );
}
