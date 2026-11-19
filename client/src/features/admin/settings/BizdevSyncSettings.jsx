import React, { useEffect, useRef, useState } from "react";
import { Play } from "lucide-react";
import { fetchBizdevSync, runBizdevSync, saveBizdevLink } from "@/api/admin.js";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { when } from "@/lib/format.js";
import { usd } from "../costs/costFormat.js";
import SettingRow from "./SettingRow.jsx";

const KINDS = [["churches", "Churches sheet"], ["nonprofits", "Nonprofits sheet"]];
const n = (k, one, many = `${one}s`) => `${k} ${k === 1 ? one : many}`;

// Admin only: the links the server downloads the two BizDev Excel sheets from each week (server/app/ingestion/bizdev_sync.py).
export default function BizdevSyncSettings({ onChanged }) {
  const [sync, setSync] = useState(null); // { links, status, enrich, running } from the server
  const [links, setLinks] = useState({ churches: "", nonprofits: "" });
  const [status, setStatus] = useState(null); // { kind: "error" | "ok", text }
  const [busy, setBusy] = useState(false);

  const failures = useRef(0);
  const wasRunning = useRef(false);
  const load = () => fetchBizdevSync().then((s) => {
    failures.current = 0;
    setSync(s);
    if (wasRunning.current && !s.running) onChanged(); // a run just finished: the summary should show its result
    wasRunning.current = s.running;
  }).catch((e) => {
    if (++failures.current >= 3) setSync((s) => s && { ...s, running: false });
    setStatus({ kind: "error", text: `Couldn’t load this (${e.message})` });
  });
  useEffect(() => { load(); }, []);
  useEffect(() => { // while a check is going, look back until it's done
    if (!sync?.running) { setStatus((s) => (s?.started ? null : s)); return undefined; }
    const timer = setInterval(load, 2000);
    return () => clearInterval(timer);
  }, [sync?.running]);

  if (!sync) return status ? <p className="form-error" role="alert">{status.text}</p> : <Card aria-busy="true" className="p-5"><Skeleton className="h-5 w-60" /></Card>;

  const run = (action, done) => {
    setBusy(true);
    setStatus(null);
    action().then(done).catch((e) => setStatus({ kind: "error", text: e.message })).finally(() => setBusy(false));
  };
  const save = (kind) => (e) => {
    e.preventDefault();
    const removing = !links[kind].trim();
    run(() => saveBizdevLink(kind, links[kind].trim()), (s) => {
      setSync(s);
      setLinks((l) => ({ ...l, [kind]: "" }));
      onChanged();
      setStatus({ kind: "ok", text: removing ? "The link was removed." : "The link is saved." });
    });
  };
  const runNow = () => run(runBizdevSync, (s) => { wasRunning.current = true; setSync(s); setStatus({ kind: "ok", text: "Started. This can take a few minutes.", started: true }); });

  const last = sync.status;
  const ai = sync.enrich;
  const hasLink = KINDS.some(([kind]) => sync.links[kind]);

  return (
    <SettingRow
      title="Excel sheets"
      description={(
        <>
          <p>You keep two Excel sheets of churches and nonprofits that are hiring. Give the server a link to each, and it will check them for you.</p>
          <p>Once a week it downloads both and adds the jobs it doesn’t have yet. Jobs already saved are never overwritten.</p>
          <p>Once a day the AI then fills in what the sheets leave empty: each church’s size and group, and the pay of jobs it can’t read directly.</p>
        </>
      )}
    >
      {(last || ai) && (
        <dl className="grid gap-x-6 gap-y-3 text-[15px] sm:grid-cols-[150px_minmax(0,1fr)]">
          {last && (
            <>
              <dt className="text-muted-foreground">Last check</dt>
              <dd>
                {when(last.at)}
                {KINDS.filter(([kind]) => last.kinds?.[kind]).map(([kind, label]) => {
                  const r = last.kinds[kind];
                  return (
                    <span key={kind} className="block">
                      {label}: {r.ok ? `${n(r.new, "new job")} added, ${r.updated} already saved` : <b className="font-medium text-destructive">{r.message}</b>}
                    </span>
                  );
                })}
              </dd>
            </>
          )}
          {ai && (
            <>
              <dt className="text-muted-foreground">AI fill-in</dt>
              <dd>
                {when(ai.at)}.{" "}
                {ai.ok === false ? ai.message
                  : ai.skipped ? `Paused: ${ai.skipped}.`
                  : `Looked up ${n(ai.employers, "church", "churches")} and searched for pay on ${n(ai.pay_searched, "job")}, finding it for ${ai.pay_found}. Cost about ${usd(ai.cost_usd ?? 0)}.`}
              </dd>
            </>
          )}
        </dl>
      )}
      {KINDS.map(([kind, label]) => (
        <form key={kind} className="grid gap-1.5" onSubmit={save(kind)}>
          <Label htmlFor={`bizdev-${kind}`}>{label}</Label>
          <p className="break-all text-sm text-muted-foreground">{sync.links[kind] ? `Link saved: ${sync.links[kind]}` : "No link saved yet."}</p>
          <div className="flex flex-wrap gap-2">
            <Input id={`bizdev-${kind}`} type="url" placeholder="Paste the sheet’s link here" className="min-w-0 flex-1"
              value={links[kind]} onChange={(e) => setLinks({ ...links, [kind]: e.target.value })} autoComplete="off" />
            <Button type="submit" variant={!links[kind].trim() && sync.links[kind] ? "outline" : "default"} disabled={busy || (!links[kind].trim() && !sync.links[kind])}>
              {links[kind].trim() || !sync.links[kind] ? "Save link" : "Remove link"}
            </Button>
          </div>
        </form>
      ))}
      <details className="text-sm">
        <summary className="cursor-pointer font-medium">How do I get a link from Google Sheets?</summary>
        <ol className="mt-2 grid list-decimal gap-1 pl-5 text-muted-foreground">
          <li>Open the sheet and press <b className="font-medium text-foreground">Share</b>.</li>
          <li>Under “General access”, choose <b className="font-medium text-foreground">Anyone with the link</b> and <b className="font-medium text-foreground">Viewer</b>.</li>
          <li>Press <b className="font-medium text-foreground">Copy link</b> and paste it above.</li>
        </ol>
        <p className="mt-2 text-muted-foreground">A direct link to an .xlsx file also works.</p>
      </details>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="outline" onClick={runNow} disabled={busy || sync.running || !hasLink}>
          <Play aria-hidden="true" />{sync.running ? "Working…" : "Check the sheets now"}
        </Button>
        <span className="text-sm text-muted-foreground">{hasLink ? "It also runs by itself once a week. To remove a link, empty its box and press Remove link." : "Add a link first to turn this on."}</span>
      </div>
      {status && <p className={status.kind === "error" ? "form-error" : "text-sm"} role={status.kind === "error" ? "alert" : "status"}>{status.text}</p>}
    </SettingRow>
  );
}
