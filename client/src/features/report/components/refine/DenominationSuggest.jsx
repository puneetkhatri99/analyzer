import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { track } from "@/features/site/lead.js";

// "Don't see your denomination?" (brief D5): what the visitor types goes to their activity in Admin → Leads and to
// the daily lead email, so the list can grow over time.
export default function DenominationSuggest() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sent, setSent] = useState(false);

  if (sent) return <p className="mh-muted mh-suggest" role="status">Thanks. We'll look at adding it.</p>;
  if (!open) {
    return (
      <button type="button" className="mh-link mh-suggest" onClick={() => setOpen(true)}>
        Don't see your denomination?
      </button>
    );
  }
  const send = (e) => {
    e.preventDefault();
    const denomination = text.trim();
    if (!denomination) return;
    track("suggest", { denomination });
    setSent(true);
  };
  return (
    <form className="mh-field mh-suggest" onSubmit={send}>
      <Label htmlFor="suggest-denomination">Your denomination</Label>
      <div className="mh-suggest-row">
        <Input id="suggest-denomination" value={text} maxLength={100} autoFocus onChange={(e) => setText(e.target.value)} />
        <button type="submit" className="mh-link">Send</button>
      </div>
    </form>
  );
}
