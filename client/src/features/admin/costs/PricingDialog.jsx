import React, { useState } from "react";
import { Calculator } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { count } from "@/lib/format.js";
import { usd } from "./costFormat.js";

// The three jobs the AI does, in the order of the volume boxes. `key` is the purpose in ai_usage (server PROFILES).
const JOBS = [
  { key: "posting_review", volume: "review", label: "Posting review", plural: "Posting reviews", help: "judges one new JSON job, and reads its pay" },
  { key: "church_lookup", volume: "church", label: "Church lookup", plural: "Church lookups", help: "searches the web for one church’s size and denomination" },
  { key: "bizdev_pay", volume: "pay", label: "Pay search", plural: "Pay searches", help: "searches the web for one job whose page can’t be read" },
];

// Volumes per month. Steady: new JSON jobs arrive at about 21 a day; the two sheets add roughly 475 jobs a month, about
// 70% of them on pages that can’t be read; about 200 of the employers are new. Backlog: the first month, while the daily
// limit works through the 397 church employers and about 1,700 unread jobs already there.
const PRESETS = {
  steady: { label: "A normal month", volumes: { review: 630, church: 200, pay: 330 } },
  backlog: { label: "First month (clearing the backlog)", volumes: { review: 630, church: 450, pay: 1900 } },
};

// One call's cost on a model: tokens at that model's prices, plus the web searches (1¢ each, whatever the model).
const callCost = (m, p, searchPrice) =>
  ((p.input - p.cached) * m.input + p.cached * m.cached + p.output * m.output) / 1e6 + p.searches * searchPrice;

export default function PricingDialog({ pricing }) {
  const [open, setOpen] = useState(false);
  const [volumes, setVolumes] = useState(PRESETS.steady.volumes);
  const models = Object.entries(pricing.models);
  const rows = models.map(([name, m]) => {
    const calls = JOBS.map((j) => callCost(m, pricing.profiles[j.key], pricing.web_search));
    const month = JOBS.reduce((sum, j, i) => sum + calls[i] * (Number(volumes[j.volume]) || 0), 0);
    return { name, m, calls, month };
  });

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}><Calculator aria-hidden="true" />Monthly cost estimate</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[calc(100vh-48px)] gap-5 overflow-y-auto sm:max-w-[860px]">
          <DialogHeader className="text-left">
            <DialogTitle className="text-xl">What the AI would cost per month</DialogTitle>
            <DialogDescription>
              The same work priced on each OpenAI model. Change the numbers to match the month you are planning.
            </DialogDescription>
          </DialogHeader>

          <section className="grid gap-3">
            <div className="flex flex-wrap gap-2">
              {Object.values(PRESETS).map((p) => (
                <Button key={p.label} type="button" variant="outline" size="sm" onClick={() => setVolumes(p.volumes)}>{p.label}</Button>
              ))}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {JOBS.map((j) => (
                <div key={j.key} className="grid gap-1.5">
                  <Label htmlFor={`vol-${j.volume}`}>{j.plural} a month</Label>
                  <Input id={`vol-${j.volume}`} type="number" min="0" step="10" inputMode="numeric" value={volumes[j.volume]}
                    onChange={(e) => setVolumes({ ...volumes, [j.volume]: e.target.value })} />
                  <p className="text-xs text-muted-foreground">One {j.label.toLowerCase()} {j.help}.</p>
                </div>
              ))}
            </div>
          </section>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Model</TableHead>
                <TableHead className="text-right">Price per million tokens<br />in / out</TableHead>
                {JOBS.map((j) => <TableHead key={j.key} className="text-right">One {j.label.toLowerCase()}</TableHead>)}
                <TableHead className="text-right">Per month</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.name}>
                  <TableCell className="font-medium">
                    {r.name}
                    {r.name === pricing.model && <Badge variant="secondary" className="ml-2">In use</Badge>}
                  </TableCell>
                  <TableCell className="text-right">${r.m.input.toFixed(2)} / ${r.m.output.toFixed(2)}</TableCell>
                  {r.calls.map((c, i) => <TableCell key={JOBS[i].key} className="text-right">{usd(c)}</TableCell>)}
                  <TableCell className="text-right font-semibold">{usd(r.month)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="grid gap-2 text-sm text-muted-foreground">
            <p>
              <b className="font-medium text-foreground">How it’s worked out.</b> Each call has two costs. Tokens are the text the AI
              reads and writes (about ¾ of a word each); a bigger model charges more per token. Every web search costs
              {" "}{usd(pricing.web_search)} on any model. The tokens and searches per call are the averages
              of your own calls ({count(JOBS.filter((j) => pricing.profiles[j.key].measured).length)} of 3 kinds measured; the
              posting review is an estimate until it has run five times).
            </p>
            <p>
              <b className="font-medium text-foreground">Why a cheaper model saves less than you’d expect.</b> The searches are a
              fixed cost: a church lookup makes about {pricing.profiles.church_lookup.searches.toFixed(1)} of them, which is
              {" "}{usd(pricing.profiles.church_lookup.searches * pricing.web_search)} before any tokens. A smaller model can only
              shrink the token part. It may also be less accurate, which this table can’t tell you.
            </p>
            <p>
              List prices from OpenAI’s model pages (GPT-5.4 and 5.5 from price trackers) in November 2026, and only an estimate:
              your OpenAI billing page is the exact figure. To change the model, set OPENAI_MODEL on the server.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
