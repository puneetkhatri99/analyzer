import React from "react";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// A labelled brand select. options: [[value, label], …]. `placeholder` shows while nothing is chosen.
export default function FormSelect({ id, label, value, onChange, options, placeholder, required, invalid }) {
  return (
    <div className="mh-field">
      <Label htmlFor={id}>{label}</Label>
      {/* no native `required`: Radix's hidden select would block the submit without showing why; the form checks instead */}
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id={id} aria-required={required || undefined} aria-invalid={invalid || undefined}><SelectValue placeholder={placeholder} /></SelectTrigger>
        <SelectContent>
          {options.map(([v, text]) => <SelectItem key={v} value={v}>{text}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  );
}
