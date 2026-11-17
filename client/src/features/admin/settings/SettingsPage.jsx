import React, { useEffect, useState } from "react";
import { Mail, X } from "lucide-react";
import { fetchSettings, saveSettings, sendTestReport } from "@/api/admin.js";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

const MAX = 10; // server/app/leads/router.py MAX_RECIPIENTS

// Admin only: who gets the daily lead report (sent by a cron job, see DAILY_REPORT_CRON.md).
export default function SettingsPage() {
  const [saved, setSaved] = useState(null); // { hot_lead_emails, email_ready, test_sender } from the server
  const [emails, setEmails] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState(null); // { kind: "error" | "ok", text }
  const [busy, setBusy] = useState(false);

  const load = (s) => { setSaved(s); setEmails(s.hot_lead_emails); };
  useEffect(() => { fetchSettings().then(load).catch((e) => setStatus({ kind: "error", text: `Couldn’t load settings (${e.message})` })); }, []);

  if (!saved) return status ? <p className="form-error" role="alert">{status.text}</p> : <Card aria-busy="true"><Skeleton className="h-5 w-60" /></Card>;

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
  const save = () => run(() => saveSettings({ hot_lead_emails: emails }), (s) => { load(s); setStatus({ kind: "ok", text: "Saved." }); });
  const test = () => run(sendTestReport, (r) => setStatus({ kind: "ok", text: `Test report sent to ${r.sent_to} address${r.sent_to === 1 ? "" : "es"}.` }));
  const unsaved = emails.join() !== saved.hot_lead_emails.join();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Daily lead report</CardTitle>
        <CardDescription>
          Every morning at 8:00 AM US Eastern, these addresses get an email with yesterday’s new hot leads
          (3 or more reports viewed) and the day’s numbers. It’s sent even on days with none.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {!saved.email_ready && (
          <Alert variant="notice">
            <AlertTitle>Email sending isn’t set up yet</AlertTitle>
            <AlertDescription>Set RESEND_API_KEY and ALERT_FROM_EMAIL on the server. See DAILY_REPORT_CRON.md.</AlertDescription>
          </Alert>
        )}
        {saved.email_ready && saved.test_sender && (
          <Alert variant="notice">
            <AlertTitle>Using Resend’s test sender</AlertTitle>
            <AlertDescription>
              Until a sending domain is verified in Resend, the report only reaches the address the Resend account was
              created with. Any other address here makes Resend refuse the whole email. See DAILY_REPORT_CRON.md, step 1.
            </AlertDescription>
          </Alert>
        )}
        <div className="flex flex-wrap gap-2" aria-label="Addresses that get the report">
          {emails.length ? emails.map((email) => (
            <Badge key={email} variant="secondary" className="gap-1 py-1 text-sm">
              {email}
              <button type="button" aria-label={`Remove ${email}`} onClick={() => setEmails(emails.filter((x) => x !== email))}>
                <X className="size-3.5" aria-hidden="true" />
              </button>
            </Badge>
          )) : <p className="empty-line">No addresses yet: nobody gets the report.</p>}
        </div>
        <form className="flex flex-wrap items-end gap-2" onSubmit={add}>
          <div className="grid gap-1.5">
            <Label htmlFor="report-email">Add an address</Label>
            <Input id="report-email" type="email" placeholder="jordan@ministryhub.org" className="w-72" value={input}
              onChange={(e) => setInput(e.target.value)} disabled={emails.length >= MAX} />
          </div>
          <Button type="submit" variant="outline" disabled={!input.trim() || emails.length >= MAX}>Add</Button>
        </form>
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={save} disabled={busy || !unsaved}>Save</Button>
          <Button variant="outline" onClick={test} disabled={busy || unsaved || !saved.hot_lead_emails.length || !saved.email_ready}>
            <Mail aria-hidden="true" />Send test report
          </Button>
          {unsaved && <span className="text-sm text-muted-foreground">Save before sending a test.</span>}
        </div>
        {status && <p className={status.kind === "error" ? "form-error" : "text-sm"} role={status.kind === "error" ? "alert" : "status"}>{status.text}</p>}
      </CardContent>
    </Card>
  );
}
