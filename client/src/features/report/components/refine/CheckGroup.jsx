import React, { useId } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

function CheckRow({ id, checked, onChange, children }) {
  return (
    <div className="mh-check">
      <Checkbox id={id} checked={checked} onCheckedChange={onChange} className="size-[18px]" />
      <Label htmlFor={id} className="font-normal">{children}</Label>
    </div>
  );
}

// A set of checkboxes. `allLabel` adds an "all" box that is ticked when nothing is picked.
export default function CheckGroup({ label, options, values, onChange, allLabel }) {
  const base = useId();
  const toggle = (o) => onChange(values.includes(o) ? values.filter((x) => x !== o) : [...values, o]);
  return (
    <fieldset className="mh-filter">
      <legend>{label}</legend>
      {allLabel && <CheckRow id={`${base}-all`} checked={!values.length} onChange={() => onChange([])}>{allLabel}</CheckRow>}
      {options.map((o, i) => (
        <CheckRow key={o} id={`${base}-${i}`} checked={values.includes(o)} onChange={() => toggle(o)}>{o}</CheckRow>
      ))}
    </fieldset>
  );
}
