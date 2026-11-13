import React from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ROLE_TEXT } from "../access.js";

// Admins can hand out read only or read and write; admin accounts come only from the server command.
export default function AccessSelect({ id, value, onChange, label }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} aria-label={label} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="viewer">{ROLE_TEXT.viewer}</SelectItem>
        <SelectItem value="editor">{ROLE_TEXT.editor}</SelectItem>
      </SelectContent>
    </Select>
  );
}
