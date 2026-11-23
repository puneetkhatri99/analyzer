import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useMediaQuery } from "@/hooks/useMediaQuery.js";
import { activeSummary } from "../../lib/filters.js";
import CheckGroup from "./CheckGroup.jsx";
import DenominationSuggest from "./DenominationSuggest.jsx";
import ChipPicker from "./ChipPicker.jsx";
import JobTypeGroup from "./JobTypeGroup.jsx";

// On wide screens the filters sit open beside the report; on narrow ones they fold away above it,
// so the answer is on the first screen instead of below a long panel.
// `f` is a draft: changes show in the report only after "Search" (apply), placed after the last filter.
export default function RefinePanel({ f, opts, setF, apply, pending, reset, changed }) {
  const wide = useMediaQuery("(min-width: 960px)");
  const [open, setOpen] = useState(false);
  const set = (key) => (value) => setF({ ...f, [key]: value });

  return (
    <Collapsible asChild open={wide || open} onOpenChange={setOpen}>
      <aside className="mh-refine" aria-label="Refine your report">
        <div className="mh-refine-head">
          <h2>Refine your report</h2>
          {!wide && (
            <>
              <CollapsibleTrigger className="mh-link mh-refine-toggle">{open ? "Close" : "Change"}</CollapsibleTrigger>
              <span className="mh-refine-summary">{activeSummary(f, opts.job_types)}</span>
            </>
          )}
        </div>
        <CollapsibleContent className="mh-refine-body">
          <ChipPicker label="Role" values={f.role} options={opts.roles} onChange={set("role")} />
          <ChipPicker label="State" values={f.state} options={opts.states} onChange={set("state")} />
          <CheckGroup label="Church size" options={opts.sizes} values={f.size} onChange={set("size")} />
          <CheckGroup label="Denomination" options={opts.denominations} values={f.denomination} onChange={set("denomination")} allLabel="All denominations" />
          <DenominationSuggest />
          <JobTypeGroup types={opts.job_types} value={f.type} onChange={set("type")} />
          {pending && <p className="mh-muted mh-pending" role="status">Click Search to see these changes.</p>}
          <div className="mh-refine-actions">
            <Button type="button" className="mh-btn mh-btn-teal" disabled={!pending} onClick={() => { apply(); setOpen(false); }}>
              Search
            </Button>
            {changed && <button type="button" className="mh-link mh-reset" onClick={reset}>Reset filters</button>}
          </div>
        </CollapsibleContent>
      </aside>
    </Collapsible>
  );
}
