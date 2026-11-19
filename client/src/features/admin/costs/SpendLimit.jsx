import React, { useState } from "react";
import { saveCostLimit } from "@/api/admin.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import SettingRow from "../settings/SettingRow.jsx";
import { usd } from "./costFormat.js";

// Admin only: the most the AI may cost in a month (server/app/ai_usage/service.py ensure_budget). When this month's
// estimated spend reaches it, the daily jobs run, the Excel AI fill-in and "Add a job" stop calling OpenAI.
export default function SpendLimit({ budget, onSaved }) {
  const { limit_usd: limit, spent, reached } = budget;
  const [value, setValue] = useState("");
  const [status, setStatus] = useState(null); // { kind: "error" | "ok", text }
  const [busy, setBusy] = useState(false);

  const share = limit ? Math.min(100, (spent / limit) * 100) : 0;
  const near = !reached && share >= 80;
  const barColor = reached ? "bg-destructive" : near ? "bg-[#c58b00]" : "bg-primary";

  const save = (next, text) => {
    setBusy(true);
    setStatus(null);
    saveCostLimit(next)
      .then(() => { setValue(""); setStatus({ kind: "ok", text }); onSaved(); })
      .catch((e) => setStatus({ kind: "error", text: e.message }))
      .finally(() => setBusy(false));
  };
  const submit = (e) => {
    e.preventDefault();
    const n = Number(value);
    if (!(n > 0)) return setStatus({ kind: "error", text: "Enter an amount above $0." });
    return save(n, `The limit is now ${usd(n)} a month.`);
  };

  return (
    <SettingRow
      title="Monthly spending limit"
      description={(
        <>
          <p>Choose the most the AI may cost in one month. When the month’s spending reaches it, the AI stops by itself until next month, or until you raise the limit.</p>
          <p>While it is paused, no new jobs are checked, no churches are looked up and “Add a job” doesn’t work. The people on the daily email list are told. Amounts are estimates and can go a few cents over.</p>
        </>
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        {reached && <Badge variant="destructive">The limit is reached: the AI is paused</Badge>}
        {near && <Badge variant="secondary">More than 80% used</Badge>}
        {limit ? (
          <p className="text-[15px]"><b className="font-semibold">{usd(spent)}</b> of {usd(limit)} used this month ({Math.round(share)}%)</p>
        ) : (
          <p className="text-[15px]">There is no limit, so the AI is never paused. This month so far: <b className="font-semibold">{usd(spent)}</b>.</p>
        )}
      </div>
      {limit > 0 && (
        <div role="progressbar" aria-label="Share of the monthly limit used" aria-valuemin={0} aria-valuemax={100}
          aria-valuenow={Math.round(share)} className="h-2.5 overflow-hidden rounded-full bg-muted">
          <div className={`h-full rounded-full ${barColor}`} style={{ width: `${share}%` }} />
        </div>
      )}
      <form className="flex flex-wrap items-end gap-2" onSubmit={submit}>
        <div className="grid gap-1.5">
          <Label htmlFor="ai-limit">{limit ? "Change the limit" : "Set a limit"} (US dollars a month)</Label>
          <Input id="ai-limit" type="number" min="0.01" step="0.01" inputMode="decimal" placeholder={limit ? String(limit) : "For example, 50"}
            className="w-52" value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <Button type="submit" disabled={busy || !value}>Save limit</Button>
        {limit && (
          <Button type="button" variant="outline" disabled={busy} onClick={() => save(null, "The limit was removed.")}>Remove the limit</Button>
        )}
      </form>
      {status && <p className={status.kind === "error" ? "form-error" : "text-sm"} role={status.kind === "error" ? "alert" : "status"}>{status.text}</p>}
    </SettingRow>
  );
}
