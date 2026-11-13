import React from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

// Full-time (yearly pay) or part-time (hourly rate); the two are never mixed.
export default function JobTypeGroup({ types, value, onChange }) {
  return (
    <fieldset className="mh-filter">
      <legend>Job type</legend>
      <RadioGroup value={value} onValueChange={onChange} className="gap-2.5">
        {types.map((t) => (
          <div key={t.key} className="mh-check">
            <RadioGroupItem id={`type-${t.key}`} value={t.key} className="size-[18px]" />
            <Label htmlFor={`type-${t.key}`} className="font-normal">{t.label}</Label>
          </div>
        ))}
      </RadioGroup>
    </fieldset>
  );
}
