import React from "react";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ORIGIN_FILTERS, count, money } from "@/lib/format.js";

function describe(key, value) {
  switch (key) {
    case "search": return ["Search", `“${value}”`];
    case "role": return ["Role", value];
    case "region": return ["State", value];
    case "denomination": return ["Denomination", value];
    case "min_church_size": return ["Church size", `${count(value)}+`];
    case "hours": return ["Type", value];
    case "origin": return ["Added via", ORIGIN_FILTERS[value]];
    case "country": return ["Country", value];
    case "remote": return [value === "true" ? "Remote only" : "On-site only", null];
    case "min_salary": return ["Pay", `${money(value)}+`];
    case "has_pay": return ["Listed pay only", null];
    default: return [key, value];
  }
}

// The filters in use as removable chips, plus "Clear all".
export default function ActiveFilters({ active, clearFilter, resetFilters }) {
  if (!active.length) return null;
  return (
    <div className="chips" aria-label="Active filters">
      {active.map(([key, value]) => {
        const [name, detail] = describe(key, value);
        return (
          <Badge asChild variant="secondary" key={key} className="h-[26px] cursor-pointer gap-1.5 pr-1.5 pl-2.5 text-[13px] font-normal hover:bg-accent">
            <button type="button" onClick={() => clearFilter(key)} aria-label={`Remove filter ${name}${detail ? ` ${detail}` : ""}`}>
              <span>{name}{detail && <>: <b className="font-medium">{detail}</b></>}</span>
              <X className="text-muted-foreground" aria-hidden="true" />
            </button>
          </Badge>
        );
      })}
      <Button variant="link" size="sm" className="h-auto px-1.5 text-[13px] text-foreground" onClick={resetFilters}>Clear all</Button>
    </div>
  );
}
