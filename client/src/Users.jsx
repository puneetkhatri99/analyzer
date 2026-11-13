import React, { useEffect, useState } from "react";
import { postJSON } from "./api.js";
import { longDate } from "./format.js";
import Confirm from "./components/Confirm.jsx";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const ROLE_TEXT = { admin: "Admin", editor: "Read and write", viewer: "Read only" };
const ROLE_HELP = "Read only: sees the dashboard. Read and write: also adds and deletes jobs. Only admins manage users.";

// A one-time password the admin hands over; the user must replace it at first sign-in.
function newPassword() {
  const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789";
  const bytes = crypto.getRandomValues(new Uint8Array(12));
  return Array.from(bytes, (b) => chars[b % chars.length]).join("");
}

function AccessSelect({ id, value, onChange, label }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} aria-label={label} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="viewer">{ROLE_TEXT.viewer}</SelectItem>
        <SelectItem value="editor">{ROLE_TEXT.editor}</SelectItem>
      </SelectContent>
    </Select>
  );
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
    <Card>
      <CardHeader><CardTitle>Add a user</CardTitle></CardHeader>
      <form className="user-form" onSubmit={submit}>
        <div className="grid gap-1.5">
          <Label htmlFor="new-email">Email</Label>
          <Input id="new-email" type="email" required value={form.email} onChange={set("email")} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="new-role">Access</Label>
          <AccessSelect id="new-role" value={form.role} onChange={(role) => setForm((f) => ({ ...f, role }))} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="new-password">One-time password</Label>
          <span className="flex gap-2">
            <Input id="new-password" className="font-mono" required minLength={8} value={form.password} onChange={set("password")} />
            <Button type="button" variant="outline" onClick={() => setForm((f) => ({ ...f, password: newPassword() }))}>New</Button>
          </span>
        </div>
        <Button type="submit" disabled={busy}>{busy ? "Adding…" : "Add user"}</Button>
      </form>
      <p className="card-note">{ROLE_HELP} The user signs in with the one-time password and must then choose their own.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
    </Card>
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
  const userUrl = (u) => `/api/admin/users/${encodeURIComponent(u.email)}`;
  const changeRole = (u, role) => act(postJSON(userUrl(u), { role }, "PATCH"));
  const resetPassword = (u) => {
    const password = newPassword();
    act(postJSON(userUrl(u), { password }, "PATCH").then(() => setHandover({ email: u.email, password })));
  };
  const remove = (u) => act(postJSON(userUrl(u), undefined, "DELETE"));

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <CreateUser onCreated={(u) => { setHandover(u); load(); }} />
      {handover && (
        <Alert variant="notice" role="status">
          <AlertTitle className="line-clamp-none">Give {handover.email} this one-time password: <code className="font-mono text-sm font-semibold">{handover.password}</code></AlertTitle>
          <AlertDescription className="text-inherit">
            It's shown only now. They'll be asked to change it when they sign in.
            <Button variant="link" className="h-auto p-0 text-inherit" onClick={() => setHandover(null)}>Done</Button>
          </AlertDescription>
        </Alert>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
      <Card>
        <CardHeader><CardTitle>Users</CardTitle></CardHeader>
        {!users ? <Skeleton className="h-5 w-60" /> : (
          <Table>
            <TableHeader>
              <TableRow><TableHead>Email</TableHead><TableHead>Access</TableHead><TableHead>Status</TableHead><TableHead>Added</TableHead><TableHead className="text-right">Actions</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.email}>
                  <TableCell>{u.email}{u.email === me ? <span className="muted"> (you)</span> : null}</TableCell>
                  <TableCell className="min-w-40">
                    {u.role === "admin" ? <Badge>{ROLE_TEXT.admin}</Badge> : (
                      <AccessSelect value={u.role} label={`Access for ${u.email}`} onChange={(role) => changeRole(u, role)} />
                    )}
                  </TableCell>
                  <TableCell>
                    {u.must_change_password ? <Badge variant="outline">Waiting for first sign-in</Badge> : <Badge variant="secondary">Active</Badge>}
                  </TableCell>
                  <TableCell className="muted">{longDate(u.created_at)}{u.created_by ? ` by ${u.created_by}` : ""}</TableCell>
                  <TableCell className="text-right">
                    {u.role !== "admin" && (
                      <span className="inline-flex gap-1">
                        <Confirm title={`Reset the password for ${u.email}?`} action="Reset password" danger={false} onConfirm={() => resetPassword(u)}
                          description="Their current password stops working and they're signed out. You'll get a new one-time password to give them.">
                          <Button variant="ghost" size="sm">Reset password</Button>
                        </Confirm>
                        <Confirm title={`Remove ${u.email}?`} action="Remove" onConfirm={() => remove(u)}
                          description="They will be signed out and can't sign in again.">
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">Remove</Button>
                        </Confirm>
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
