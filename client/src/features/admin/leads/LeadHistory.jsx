import React, { useEffect, useState } from "react";
import { fetchLeadHistory } from "@/api/admin.js";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { longDate } from "@/lib/format.js";
import { when } from "../costs/costFormat.js";
import { describe } from "./leadEvents.js";
import HotBadge from "./HotBadge.jsx";

// One lead's full history, newest first: sign-ups, reports viewed, offers checked, shares, downloads, clicks.
export default function LeadHistory({ email, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    setData(null);
    setError(null);
    if (email) fetchLeadHistory(email).then(setData).catch((e) => setError(`Couldn’t load the history (${e.message})`));
  }, [email]);

  const lead = data?.lead;
  return (
    <Dialog open={Boolean(email)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{lead ? <>{lead.name}, {lead.organization}{lead.hot && <HotBadge />}</> : email}</DialogTitle>
          <DialogDescription>
            {lead ? <><a href={`mailto:${lead.email}`}>{lead.email}</a> · signed up {longDate(lead.created_at)} · {lead.reports} report{lead.reports === 1 ? "" : "s"} viewed{lead.hot_at && <> · hot since {longDate(lead.hot_at)}</>}</> : "Loading…"}
          </DialogDescription>
        </DialogHeader>
        {error && <p className="form-error" role="alert">{error}</p>}
        {!data && !error && <Skeleton className="h-24 w-full" />}
        {data && (data.events.length ? (
          <ol className="grid gap-3 border-l pl-4">
            {data.events.map((e, i) => {
              const [what, detail] = describe(e);
              return (
                <li key={i} className="grid gap-0.5">
                  <span className="text-xs text-muted-foreground">{when(e.created_at)}</span>
                  <span className="font-medium">{what}</span>
                  {detail && <span className="text-sm text-muted-foreground break-words">{detail}</span>}
                </li>
              );
            })}
          </ol>
        ) : <p className="empty-line">No activity recorded yet. History starts from 17 November 2026.</p>)}
      </DialogContent>
    </Dialog>
  );
}
