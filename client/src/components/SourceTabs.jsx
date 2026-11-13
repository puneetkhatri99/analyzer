import React from "react";
import { count } from "../format.js";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const NOTES = {
  json: "Job feed with stated pay",
  churches: "Excel leads · pay read from each job page",
  nonprofits: "Excel leads · pay read from each job page",
};

export default function SourceTabs({ sources, value, onChange }) {
  return (
    <Tabs value={value} onValueChange={onChange}>
      <TabsList aria-label="Data source" className="sources w-full bg-transparent p-0 group-data-[orientation=horizontal]/tabs:h-auto">
        {(sources || [{ key: value, label: "…" }]).map((s) => (
          <TabsTrigger key={s.key} value={s.key} className="source h-auto whitespace-normal data-[state=active]:shadow-none">
            <span className="source-label">{s.label}</span>
            {s.postings != null && (
              <span className="source-meta num">
                {count(s.postings)} postings · {count(s.paid)} with pay
                {s.key !== "json" && s.fetched < s.postings && <> · {count(s.fetched)} pages read</>}
                {s.expired > 0 && <> · {count(s.expired)} expired</>}
              </span>
            )}
            <span className="source-note">{NOTES[s.key]}</span>
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
