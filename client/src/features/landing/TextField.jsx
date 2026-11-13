import React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function TextField({ id, label, ...input }) {
  return (
    <div className="mh-field">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} required {...input} />
    </div>
  );
}
