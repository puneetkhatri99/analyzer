import React, { useState } from "react";
import { signIn } from "@/api/admin.js";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage({ onSignedIn }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    signIn(email, password)
      .then(onSignedIn)
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  };

  return (
    <main className="login">
      <Card className="w-full max-w-[380px] p-7">
        <form className="flex flex-col gap-4" onSubmit={submit}>
          <div className="brand"><img className="brand-logo" src="/ministryhub-logo.png" alt="MinistryHub" />Market Analysis Tool</div>
          <h1 className="m-0 mt-1 text-xl font-semibold">Admin sign in</h1>
          <div className="grid gap-1.5">
            <Label htmlFor="login-email">Email</Label>
            <Input id="login-email" type="email" autoComplete="username" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="login-password">Password</Label>
            <Input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
          <a className="muted small" href="/">Back to the public tool</a>
        </form>
      </Card>
    </main>
  );
}
