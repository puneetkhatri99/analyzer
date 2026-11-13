import React, { useEffect, useState } from "react";
import { postJSON } from "./api.js";
import AiCosts from "./AiCosts.jsx";
import AdminJobs from "./AdminJobs.jsx";
import ChangePassword from "./ChangePassword.jsx";
import Users from "./Users.jsx";
import ProfileMenu from "./ProfileMenu.jsx";
import { ORIGINS, count, listedPay } from "./format.js";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
      <Card>
        <CardHeader><CardTitle>Add a job from a URL</CardTitle></CardHeader>
        <form className="url-form" onSubmit={extract}>
          <Label className="sr-only" htmlFor="job-url">Job posting URL</Label>
          <Input id="job-url" type="url" required placeholder="https://… link to a single job posting"
            value={url} onChange={(e) => setUrl(e.target.value)} disabled={busy} />
          <Button type="submit" disabled={busy || !url.trim()}>
            {busy && !result ? "Reading page…" : "Fetch job"}
          </Button>
        </form>
        <p className="card-note">
          The page is read and an AI model extracts the job’s details. Blocked or JavaScript-only pages are read through web search,
          which can take up to a minute. Nothing is saved until you review it.
        </p>
        {error && <p className="form-error" role="alert">{error}</p>}
      </Card>

      {job && job.page_type !== "job_posting" && (
        <Alert variant="notice" role="status">
          <AlertTitle className="line-clamp-none">{job.page_type === "unreadable" ? "This page couldn’t be read as a job posting." : "This is not a job posting."}</AlertTitle>
          <AlertDescription className="text-inherit">{job.reason}</AlertDescription>
        </Alert>
      )}

      {job && job.page_type === "job_posting" && (
        <Card>
          <CardHeader>
            <CardTitle>Review the extracted job</CardTitle>
            <CardDescription>Will be saved as “{ORIGINS[`admin_${result.method}`]}”</CardDescription>
          </CardHeader>
          <p className="finding">{job.reason}</p>
          {result.warnings.length > 0 && (
            <Alert variant="notice" role="status" className="mt-3" aria-label="Check before saving">
              <ul className="m-0 list-disc pl-4">{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </Alert>
          )}
          <JobDetails job={job} />
          <div className="save-row">
            <div className="flex items-center gap-2.5">
              <Label htmlFor="save-dataset">Add to</Label>
              <Select value={dataset} onValueChange={(v) => { setDataset(v); setSaved(null); }} disabled={busy}>
                <SelectTrigger id="save-dataset"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(DATASETS).map(([k, label]) => <SelectItem key={k} value={k}>{label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" onClick={save} disabled={busy || saved === dataset}>
              {saved === dataset ? "Saved" : busy ? "Saving…" : "Save job"}
            </Button>
            {saved && (
              <a href={`/admin?source=${saved}&search=${encodeURIComponent(job.job_title || "")}`}>View it in Jobs</a>
            )}
          </div>
          {job.category === "other" && <p className="card-note">The AI thinks this employer is a for-profit company. Check it belongs here before saving.</p>}
        </Card>
      )}
    </>
  );
}

// [key, label, lowest role that sees it]. The server enforces the same roles; hiding tabs is only for clarity.
const TABS = [["jobs", "Jobs", "viewer"], ["add", "Add a job", "editor"], ["users", "Users", "admin"], ["costs", "AI costs", "admin"]];
const ROLES = ["viewer", "editor", "admin"];
const ROLE_TEXT = { admin: "Admin", editor: "Read and write", viewer: "Read only" };
const can = (user, role) => ROLES.indexOf(user.role) >= ROLES.indexOf(role);

export default function Admin() {
  const [user, setUser] = useState(undefined); // undefined = checking, null = signed out
  const [tab, setTab] = useState(window.location.hash.slice(1) || "jobs");
  const showTab = (next) => { setTab(next); window.history.replaceState(null, "", next === "jobs" ? window.location.pathname : `#${next}`); };
  const refresh = () => fetch("/api/admin/me").then((r) => (r.ok ? r.json() : null)).then(setUser).catch(() => setUser(null));

  useEffect(() => { refresh(); }, []);

  if (user === undefined) return null;
  if (!user) return <Login onSignedIn={setUser} />;

  const signOut = () => postJSON("/api/admin/logout", {}).finally(() => setUser(null));
  const tabs = TABS.filter(([, , role]) => can(user, role));
  // "password" is opened from the profile menu, not from a tab
  const current = tab === "password" || tabs.some(([k]) => k === tab) ? tab : "jobs";
  return (
    <>
      <header className="topbar admin-topbar">
        <div className="topbar-inner">
          <div className="brand"><img className="brand-logo" src="/ministryhub-logo.png" alt="MinistryHub" /><span className="brand-name">Market Analysis Tool</span></div>
          <div className="topbar-actions">
            <a href="/">Public tool</a>
            <ProfileMenu email={user.email} roleText={ROLE_TEXT[user.role]} onChangePassword={() => showTab("password")} onSignOut={signOut} />
          </div>
        </div>
      </header>
      {user.must_change_password ? (
        <main className="login"><ChangePassword forced onDone={refresh} /></main>
      ) : (
        <main className="canvas admin">
          <Tabs value={current} onValueChange={showTab} className="gap-3">
            <TabsList variant="line" aria-label="Admin sections" className="admin-tabs">
              {tabs.map(([key, label]) => <TabsTrigger key={key} value={key} className="flex-none px-3">{label}</TabsTrigger>)}
            </TabsList>
            <TabsContent value="jobs" className="flex min-w-0 flex-col gap-3"><AdminJobs canEdit={can(user, "editor")} /></TabsContent>
            <TabsContent value="add" className="flex min-w-0 flex-col gap-3"><AddJob /></TabsContent>
            <TabsContent value="users" className="min-w-0"><Users me={user.email} /></TabsContent>
            <TabsContent value="costs" className="flex min-w-0 flex-col gap-3"><AiCosts /></TabsContent>
            {/* opened from the profile menu, so it has no tab of its own */}
            {current === "password" && <div className="password-page"><ChangePassword /></div>}
          </Tabs>
        </main>
      )}
    </>
  );
}
