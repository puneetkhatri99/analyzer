import React, { useEffect, useRef, useState } from "react";
import { Play } from "lucide-react";
import { fetchFeed, runFeedNow, saveFeedLink } from "@/api/admin.js";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { longDate, when } from "@/lib/format.js";
import SettingRow from "./SettingRow.jsx";

const n = (k, one, many = `${one}s`) => `${k} ${k === 1 ? one : many}`;
const WARN_DAYS = 7; // server/app/ingestion/daily_feed.py WARN_DAYS

// Admin only: the link the server downloads the church jobs feed from each day (server/app/ingestion/daily_feed.py).
// The link expires; paste the new one here.
export default function FeedSettings({ onChanged }) {
  const [feed, setFeed] = useState(null); // { url, expires_at, days_left, expired, status, running } from the server
  const [link, setLink] = useState("");
  const [status, setStatus] = useState(null); // { kind: "error" | "ok", text }
  const [busy, setBusy] = useState(false);

  const failures = useRef(0); // refreshes failed in a row while a run is going
  const wasRunning = useRef(false);
  const load = () => fetchFeed().then((f) => {
    failures.current = 0;
    setFeed(f);
    if (wasRunning.current && !f.running) onChanged(); // a run just finished: the summary should show its result
    wasRunning.current = f.running;
  }).catch((e) => {
    // one network blip mustn't end the progress view; three in a row (server gone, session over) stop the checking
    if (++failures.current >= 3) setFeed((f) => f && { ...f, running: false });
    setStatus({ kind: "error", text: `Couldn’t load this (${e.message})` });
  });
  useEffect(() => { load(); }, []);
  useEffect(() => { // while a run is going, check back until it's done
    if (!feed?.running) { setStatus((s) => (s?.started ? null : s)); return undefined; }
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, [feed?.running]);

  if (!feed) return status ? <p className="form-error" role="alert">{status.text}</p> : <Card aria-busy="true" className="p-5"><Skeleton className="h-5 w-60" /></Card>;

  const run = (action, done) => {
    setBusy(true);
    setStatus(null);
    action().then(done).catch((e) => setStatus({ kind: "error", text: e.message })).finally(() => setBusy(false));
  };
  const save = (e) => {
    e.preventDefault();
    run(() => saveFeedLink(link.trim()), (s) => { setFeed(s); setLink(""); onChanged(); setStatus({ kind: "ok", text: "The new link is saved." }); });
  };
  const runNow = () => run(runFeedNow, (s) => { wasRunning.current = true; setFeed(s); setStatus({ kind: "ok", text: "Started. This can take a few minutes.", started: true }); });

  const { days_left: left, expired, status: last } = feed;
  const soon = !expired && left !== null && left <= WARN_DAYS;
  const live = feed.live;

  return (
    <SettingRow
      title="Church jobs feed"
      description={(
        <>
          <p>Once a day, the server downloads a list of church jobs from a special link. It adds the jobs it doesn’t have yet.</p>
          <p>Then the AI fills in what the list leaves out: the pay, each church’s group (such as Baptist) and how big it is.</p>
          <p>The link stops working on a set date. When that day comes you need to paste in a new one.</p>
        </>
      )}
    >
      {expired && (
        <Alert variant="destructive">
          <AlertTitle>The link has expired</AlertTitle>
          <AlertDescription>No new jobs are coming in. Ask whoever supplies the feed for a new link, then paste it in below.</AlertDescription>
        </Alert>
      )}
      <dl className="grid gap-x-6 gap-y-3 text-[15px] sm:grid-cols-[150px_minmax(0,1fr)]">
        <dt className="text-muted-foreground">Link saved</dt>
        <dd className="break-all">{feed.url || "No link yet"}</dd>
        {feed.expires_at && (
          <>
            <dt className="text-muted-foreground">Works until</dt>
            <dd className="flex flex-wrap items-center gap-2">
              {longDate(feed.expires_at)}
              <Badge variant={expired || soon ? "destructive" : "secondary"}>{expired ? "Expired" : `${left} day${left === 1 ? "" : "s"} left`}</Badge>
            </dd>
          </>
        )}
        {last && (
          <>
            <dt className="text-muted-foreground">Last check</dt>
            <dd>
              {when(last.at)}.{" "}
              {last.ok === false ? last.message : (
                <>
                  {n(last.new ?? 0, "new job")} added. The AI checked {last.reviewed ?? 0}, found pay for {last.pay ?? 0}
                  {" "}and looked up {n(last.church ?? 0, "church", "churches")}.
                  {last.cost_usd !== undefined && ` It cost about $${last.cost_usd.toFixed(2)}.`}
                </>
              )}
            </dd>
          </>
        )}
      </dl>
      {feed.running && (
        <div className="grid gap-2 rounded-md bg-muted p-4" role="status">
          {/* only the step is announced: the log is replaced every 2 s and would be read out again and again */}
          <p className="text-[15px] font-semibold" aria-live="polite">Working now: {live?.step || "starting"}…</p>
          <p className="text-sm">
            {live?.new ?? 0} new jobs saved · pay found for {live?.pay ?? 0} · {live?.church ?? 0} churches looked up
            {live?.run_id && ` · the AI has cost about $${(live.cost ?? 0).toFixed(2)} so far`}
          </p>
          <details className="text-sm text-muted-foreground">
            <summary className="cursor-pointer">Show the detailed log</summary>
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs">{(live?.lines || []).join("\n")}</pre>
          </details>
        </div>
      )}
      <form className="grid gap-1.5" onSubmit={save}>
        <Label htmlFor="feed-link">Paste a new link</Label>
        <div className="flex flex-wrap gap-2">
          <Input id="feed-link" type="url" placeholder="Paste the whole link here" className="min-w-0 flex-1"
            value={link} onChange={(e) => setLink(e.target.value)} autoComplete="off" />
          <Button type="submit" disabled={busy || !link.trim()}>Save link</Button>
        </div>
        <p className="text-sm text-muted-foreground">Copy the whole link, including everything after the question mark.</p>
      </form>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="outline" onClick={runNow} disabled={busy || feed.running || !feed.url || expired}>
          <Play aria-hidden="true" />{feed.running ? "Working…" : "Check for new jobs now"}
        </Button>
        <span className="text-sm text-muted-foreground">{!feed.url ? "Add a link first to turn this on." : expired ? "Add a new link first: the old one has expired." : "It also runs by itself once a day."}</span>
      </div>
      {status && <p className={status.kind === "error" ? "form-error" : "text-sm"} role={status.kind === "error" ? "alert" : "status"}>{status.text}</p>}
    </SettingRow>
  );
}
