import React from "react";
import { CalendarCheck, Flame, Mail, MailX } from "lucide-react";
import { Badge } from "@/components/ui/badge";

// Hot = viewed 3 or more reports (server/app/leads/__init__.py HOT_AT_REPORTS), marked once in leads.hot_at.
export default function HotBadge() {
  return <Badge className="ml-2 gap-1 bg-orange-700 text-white"><Flame className="size-3" aria-hidden="true" />Hot</Badge>;
}

// The latest "Email me this report": sent, or failed / not sent (the lead's history says why).
export function EmailBadge({ status }) {
  if (!status) return null;
  return status === "sent"
    ? <Badge variant="outline" className="ml-2 gap-1 border-slate-400 text-slate-700"><Mail className="size-3" aria-hidden="true" />Report emailed</Badge>
    : <Badge variant="outline" className="ml-2 gap-1 border-red-700 text-red-800"><MailX className="size-3" aria-hidden="true" />Email not sent</Badge>;
}

// Clicked through to the booking page: the strongest buying signal recorded.
export function BookedBadge() {
  return <Badge variant="outline" className="ml-2 gap-1 border-teal-700 text-teal-800"><CalendarCheck className="size-3" aria-hidden="true" />Booked a call</Badge>;
}
