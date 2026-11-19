import React, { useEffect, useState } from "react";
import { fetchBizdevSync, fetchCosts, fetchFeed, fetchSettings } from "@/api/admin.js";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { longDate, when } from "@/lib/format.js";
import { usd } from "../costs/costFormat.js";
import StatusMark from "./StatusMark.jsx";

const n = (k, one, many = `${one}s`) => `${k} ${k === 1 ? one : many}`;

// Each automatic job as one sentence a non-technical person can act on: state (ok / attention / off), what is
// happening, a hint, and where to change it ("go" is a Settings tab, or "costs", the AI costs page).
function describe({ feed, sync, costs, email }) {
  const rows = [];

  rows.push({ key: "feed", title: "New jobs from the church jobs feed", go: "jobs", ...(() => {
    if (!feed) return { state: "attention", text: "Couldn’t check this just now.", act: "Open" };
    if (!feed.url) return { state: "off", text: "No link has been added yet, so no new jobs are coming in.", act: "Add the link" };
    if (feed.expired) return { state: "attention", text: "The link has expired, so no new jobs are coming in.", act: "Add a new link" };
    const last = feed.status;
    if (feed.days_left !== null && feed.days_left <= 7) {
      return { state: "attention", text: `The link stops working in ${n(feed.days_left, "day")}. Get a new one and paste it in.`, act: "Add a new link" };
    }
    if (last && last.ok === false) return { state: "attention", text: last.message, act: "See details" };
    return {
      state: "ok",
      text: feed.running ? "Downloading new jobs right now…"
        : last ? `Last checked ${when(last.at)}: ${n(last.new ?? 0, "new job")} found.` : "Link saved. The first download happens by itself today.",
      hint: feed.expires_at ? `The link works until ${longDate(feed.expires_at)}.` : null,
      act: "Open",
    };
  })() });

  rows.push({ key: "sheets", title: "Jobs from your Excel sheets", go: "jobs", ...(() => {
    if (!sync) return { state: "attention", text: "Couldn’t check this just now.", act: "Open" };
    if (!Object.values(sync.links).some(Boolean)) return { state: "off", text: "No sheet links have been added yet.", act: "Add the links" };
    const last = sync.status;
    const failed = last && Object.values(last.kinds || {}).find((k) => !k.ok);
    if (failed) return { state: "attention", text: `A sheet couldn’t be downloaded: ${failed.message}`, act: "See details" };
    const added = last ? Object.values(last.kinds || {}).reduce((sum, k) => sum + (k.new || 0), 0) : 0;
    const ai = sync.enrich && !sync.enrich.skipped && sync.enrich.ok !== false ? sync.enrich : null;
    return {
      state: "ok",
      text: sync.running ? "Checking the sheets right now…"
        : last ? `Last checked ${when(last.at)}: ${n(added, "new job")} added.` : "Links saved. The sheets are checked by themselves once a week.",
      hint: ai ? `Then the AI filled in ${n(ai.employers, "church", "churches")} and ${n(ai.pay_found, "pay figure")}.` : null,
      act: "Open",
    };
  })() });

  rows.push({ key: "ai", title: "The AI helper", go: "costs", ...(() => {
    const b = costs?.budget;
    if (!b) return { state: "attention", text: "Couldn’t check this just now.", act: "Open" };
    if (b.reached) return { state: "attention", text: `The AI is paused: this month’s limit of ${usd(b.limit_usd)} is used up.`, act: "Change the limit" };
    if (b.limit_usd && b.spent / b.limit_usd >= 0.8) {
      return { state: "attention", text: `${usd(b.spent)} of the ${usd(b.limit_usd)} monthly limit is used. It pauses at the limit.`, act: "See AI costs" };
    }
    if (b.limit_usd) return { state: "ok", text: `${usd(b.spent)} of the ${usd(b.limit_usd)} monthly limit is used.`, act: "See AI costs" };
    return { state: "off", label: "No limit", text: `The AI has cost ${usd(b.spent)} this month. There is no spending limit.`, act: "Set a limit" };
  })() });

  rows.push({ key: "email", title: "The daily email about new leads", go: "email", ...(() => {
    if (!email) return { state: "attention", text: "Couldn’t check this just now.", act: "Open" };
    if (!email.email_ready) return { state: "attention", text: "The email can’t go out because email isn’t set up on the server yet.", act: "See details" };
    const k = email.hot_lead_emails.length;
    if (!k) return { state: "off", text: "Nobody is on the list yet, so nobody gets the email.", act: "Add an address" };
    return { state: "ok", text: `Sent every morning at 8 AM New York time to ${n(k, "address", "addresses")}.`, act: "Open" };
  })() });

  return rows;
}

const settled = (r) => (r.status === "fulfilled" ? r.value : null);

export default function Overview({ stamp, go, onOpenCosts }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    let current = true;
    Promise.allSettled([fetchFeed(), fetchBizdevSync(), fetchCosts(), fetchSettings()]).then(([feed, sync, costs, email]) => {
      if (current) setData({ feed: settled(feed), sync: settled(sync), costs: settled(costs), email: settled(email) });
    });
    return () => { current = false; };
  }, [stamp]);

  if (!data) return <Card aria-busy="true" className="p-5"><Skeleton className="h-5 w-60" /></Card>;

  const rows = describe(data);
  const waiting = rows.filter((r) => r.state === "attention").length;
  return (
    <div className="grid gap-4">
      <div className="grid gap-1 [&_p]:m-0">
        <h2 className="text-base font-semibold">What is happening right now</h2>
        <p className={`text-[15px] ${waiting ? "font-medium text-destructive" : "text-muted-foreground"}`}>
          {waiting ? `${n(waiting, "thing")} ${waiting === 1 ? "needs" : "need"} you. Everything else is running by itself.` : "Everything is running by itself. Nothing needs you."}
        </p>
      </div>
      <div className="rounded-lg border border-border bg-card">
        <ul className="divide-y divide-border px-5">
          {rows.map((r) => (
            <li key={r.key} className="grid items-center gap-x-6 gap-y-3 py-4 sm:grid-cols-[minmax(0,1fr)_auto]">
              <div className="grid min-w-0 gap-0.5 [&_p]:m-0">
                <h3 className="text-[15px] font-semibold">{r.title}</h3>
                <p className="text-[15px] leading-6">{r.text}</p>
                {r.hint && <p className="text-sm text-muted-foreground">{r.hint}</p>}
              </div>
              <div className="flex flex-wrap items-center gap-4 sm:justify-end">
                <StatusMark state={r.state} label={r.label} />
                <Button variant="outline" size="sm" onClick={() => (r.go === "costs" ? onOpenCosts() : go(r.go))}>{r.act}</Button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
