import React, { useEffect, useState } from "react";
import { Mail, X } from "lucide-react";
import { fetchSettings, saveSettings, sendTestReport } from "@/api/admin.js";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import SettingRow from "./SettingRow.jsx";

const MAX = 10; // server/app/leads/router.py MAX_RECIPIENTS

// Admin only: who gets the daily lead email (sent by the server itself, see DAILY_REPORT_CRON.md).
export default function EmailSettings({ onChanged }) {
  const [saved, setSaved] = useState(null); // { hot_lead_emails, email_ready, test_sender } from the server
  const [emails, setEmails] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState(null); // { kind: "error" | "ok", text }
  const [busy, setBusy] = useState(false);

  const load = (s) => { setSaved(s); setEmails(s.hot_lead_emails); };
  useEffect(() => { fetchSettings().then(load).catch((e) => setStatus({ kind: "error", text: `Couldn’t load this (${e.message})` })); }, []);

  if (!saved) return status ? <p className="form-error" role="alert">{status.text}</p> : <Card aria-busy="true" className="p-5"><Skeleton className="h-5 w-60" /></Card>;

  const add = (e) => {
    e.preventDefault();
    const email = input.trim().toLowerCase();
    if (!email) return;
    if (!emails.includes(email)) setEmails([...emails, email]);
    setInput("");
  };
  const run = (action, done) => {
    setBusy(true);
    setStatus(null);
    action().then(done).catch((e) => setStatus({ kind: "error", text: e.message })).finally(() => setBusy(false));
  };
  const save = () => run(() => saveSettings({ hot_lead_emails: emails }), (s) => { load(s); onChanged(); setStatus({ kind: "ok", text: "Saved." }); });
  const test = () => run(sendTestReport, (r) => setStatus({ kind: "ok", text: `Test email sent to ${r.sent_to} ${r.sent_to === 1 ? "address" : "addresses"}.` }));
  const unsaved = emails.join() !== saved.hot_lead_emails.join();

  return (
    <SettingRow
      title="Who gets the daily email"
      description={(
        <>
          <p>Every morning at 8 AM New York time, these people get an email about yesterday: the new “hot” leads and the day’s numbers.</p>
          <p>A hot lead is someone who looked at 3 or more reports. The email is sent even on days with no new leads.</p>
        </>
      )}
    >
      {!saved.email_ready && (
        <Alert variant="notice">
          <AlertTitle>The email can’t be sent yet</AlertTitle>
          <AlertDescription>Email isn’t set up on the server. Whoever looks after the server needs to finish this (the steps are in DAILY_REPORT_CRON.md).</AlertDescription>
        </Alert>
      )}
      {saved.email_ready && saved.test_sender && (
        <Alert variant="notice">
          <AlertTitle>For now, the email only reaches one address</AlertTitle>
          <AlertDescription>
            Until your own sending domain is verified with the email service, it only delivers to the address it was set up with.
            Adding any other address makes it refuse the whole email. The steps are in DAILY_REPORT_CRON.md, step 1.
          </AlertDescription>
        </Alert>
      )}
      <div className="grid gap-2">
        <p className="text-sm font-medium">The list ({emails.length} of {MAX})</p>
        <div className="flex flex-wrap gap-2" aria-label="Addresses that get the email">
          {emails.length ? emails.map((email) => (
            <Badge key={email} variant="secondary" className="gap-1 py-1 text-sm">
              {email}
              <button type="button" aria-label={`Remove ${email}`} onClick={() => setEmails(emails.filter((x) => x !== email))}>
                <X className="size-3.5" aria-hidden="true" />
              </button>
            </Badge>
          )) : <p className="empty-line">Nobody yet. Add an address below.</p>}
        </div>
      </div>
      <form className="flex flex-wrap items-end gap-2" onSubmit={add}>
        <div className="grid gap-1.5">
          <Label htmlFor="report-email">Add an email address</Label>
          <Input id="report-email" type="email" placeholder="name@yourchurch.org" className="w-72 max-w-full" value={input}
            onChange={(e) => setInput(e.target.value)} disabled={emails.length >= MAX} />
        </div>
        <Button type="submit" variant="outline" disabled={!input.trim() || emails.length >= MAX}>Add to the list</Button>
      </form>
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={save} disabled={busy || !unsaved}>Save the list</Button>
        <Button variant="outline" onClick={test} disabled={busy || unsaved || !saved.hot_lead_emails.length || !saved.email_ready}>
          <Mail aria-hidden="true" />Send a test email now
        </Button>
        {unsaved && <span className="text-sm text-muted-foreground">You have changes that aren’t saved yet.</span>}
      </div>
      {status && <p className={status.kind === "error" ? "form-error" : "text-sm"} role={status.kind === "error" ? "alert" : "status"}>{status.text}</p>}
    </SettingRow>
  );
}
