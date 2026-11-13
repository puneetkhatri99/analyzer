import React, { useState } from "react";
import { Plus, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

// Picks several values from a long list: chosen ones as chips, "+ Add" opens a searchable list.
export default function ChipPicker({ label, values, options, onChange }) {
  const [open, setOpen] = useState(false);
  const noun = label.toLowerCase();
  const left = options.filter((o) => !values.includes(o));
  const add = (v) => { onChange([...values, v]); setOpen(false); };

  return (
    <div className="mh-filter">
      <h3>{label}</h3>
      <div className="mh-chips">
        {values.map((v) => (
          <Badge key={v} className="mh-chip">
            {v}
            <button type="button" aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}>
              <X className="size-3.5" aria-hidden="true" />
            </button>
          </Badge>
        ))}
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button type="button" className="mh-chip-add" disabled={!left.length}>
              <Plus className="size-3.5" aria-hidden="true" />Add {noun}
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-64 p-0">
            <Command>
              <CommandInput placeholder={`Search ${noun}s…`} />
              <CommandList>
                <CommandEmpty>No match.</CommandEmpty>
                {left.map((o) => <CommandItem key={o} value={o} onSelect={() => add(o)}>{o}</CommandItem>)}
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}
