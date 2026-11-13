import React from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// Radix Select can't hold "" as a value, so "All …" uses this and is turned back into "" here.
const ALL = "__all";

// options: [[value, label], …]; `all` is the label of the "no filter" choice.
export default function FilterSelect({ id, label, value, onChange, all, options }) {
  const v = value === "" || value === 0 || value == null ? ALL : String(value);
  return (
    <Select value={v} onValueChange={(x) => onChange(x === ALL ? "" : x)}>
      <SelectTrigger id={id} aria-label={label} className={`filter-select${v !== ALL ? " border-foreground" : ""}`}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>{all}</SelectItem>
        {options.map(([value, text]) => <SelectItem key={value} value={String(value)}>{text}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}
