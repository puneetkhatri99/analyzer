import React, { useState } from "react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useMediaQuery } from "@/hooks/useMediaQuery.js";
import { activeSummary, resetFilters } from "../../lib/filters.js";
import CheckGroup from "./CheckGroup.jsx";
import ChipPicker from "./ChipPicker.jsx";
import JobTypeGroup from "./JobTypeGroup.jsx";

const SHOWN_DENOMINATIONS = 3;

// On wide screens the filters sit open beside the report; on narrow ones they fold away above it,
// so the answer is on the first screen instead of below a long panel.
export default function RefinePanel({ f, opts, setF }) {
  const wide = useMediaQuery("(min-width: 960px)");
  const [open, setOpen] = useState(false);
  const [allDenoms, setAllDenoms] = useState(false);
  const set = (key) => (value) => setF({ ...f, [key]: value });
  const denoms = opts.denominations;
  const shown = allDenoms ? denoms : [...new Set([...denoms.slice(0, SHOWN_DENOMINATIONS), ...f.denomination])];

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
          <button type="button" className="mh-link mh-reset" onClick={() => setF(resetFilters(f))}>Reset filters</button>
          <ChipPicker label="Role" values={f.role} options={opts.roles} onChange={set("role")} />
          <ChipPicker label="State" values={f.state} options={opts.states} onChange={set("state")} />
          <CheckGroup label="Weekly attendance" options={opts.sizes} values={f.size} onChange={set("size")} />
          <CheckGroup label="Denomination" options={shown} values={f.denomination} onChange={set("denomination")} allLabel="All denominations" />
          {denoms.length > SHOWN_DENOMINATIONS && (
            <button type="button" className="mh-link mh-show-all" onClick={() => setAllDenoms(!allDenoms)}>
              {allDenoms ? "Show fewer" : "Show all"}
            </button>
          )}
          <JobTypeGroup types={opts.job_types} value={f.type} onChange={set("type")} />
        </CollapsibleContent>
      </aside>
    </Collapsible>
  );
}
