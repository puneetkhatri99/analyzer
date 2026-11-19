import React, { useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { ORIGIN_FILTERS, count, money } from "@/lib/format.js";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import ActiveFilters from "./ActiveFilters.jsx";
import { isSet } from "../lib/filters.js";
import FilterSelect from "./FilterSelect.jsx";

const CHURCH_SIZES = [
  [250, "250+ attendance"],
  [1000, "1,000+ attendance"],
  [5000, "5,000+ attendance"],
];
const MIN_PAY = [30000, 40000, 50000, 60000, 80000, 100000];
const MORE_KEYS = ["origin", "country", "remote", "min_salary", "has_pay"];
const counted = (pairs) => pairs.map(([name, n]) => [name, `${name} (${count(n)})`]);

export default function FilterBar({ filters, setFilter, clearFilter, resetFilters, options: opts, showChurchSize = true }) {
  const moreActive = MORE_KEYS.filter((k) => filters[k]).length;
  const [moreOpen, setMoreOpen] = useState(moreActive > 0);
  const [panelOpen, setPanelOpen] = useState(false);
  const o = opts || { roles: [], denominations: [], regions: [], countries: [], hours: [] };
  const active = Object.entries(filters).filter(([, v]) => isSet(v));
  const number = (key) => (v) => setFilter(key, Number(v) || 0);

  return (
    <section className="filters" aria-label="Filters">
      <Button variant="outline" className="filters-toggle" aria-expanded={panelOpen} onClick={() => setPanelOpen((v) => !v)}>
        {panelOpen ? "Hide filters" : `Filters${active.length ? ` (${active.length})` : ""}`}
      </Button>

      <Collapsible open={moreOpen} onOpenChange={setMoreOpen} className={`filter-panel${panelOpen ? " is-open" : ""}`}>
        <div className="filter-row">
          <div className="search">
            <Label htmlFor="f-search" className="sr-only">Search job title or employer</Label>
            <Search className="size-3.5" aria-hidden="true" />
            <Input id="f-search" type="search" placeholder="Search title or employer" value={filters.search} onChange={(e) => setFilter("search", e.target.value)} />
          </div>
          <FilterSelect id="f-role" label="Role" value={filters.role} onChange={(v) => setFilter("role", v)} all="All roles" options={counted(o.roles)} />
          <FilterSelect id="f-region" label="State" value={filters.region} onChange={(v) => setFilter("region", v)} all="All states" options={counted(o.regions)} />
          <FilterSelect id="f-denom" label="Denomination" value={filters.denomination} onChange={(v) => setFilter("denomination", v)} all="All denominations" options={counted(o.denominations)} />
          {showChurchSize && (
            <FilterSelect id="f-size" label="Church size" value={filters.min_church_size} onChange={number("min_church_size")} all="Any church size" options={CHURCH_SIZES} />
          )}
          <FilterSelect id="f-hours" label="Employment type" value={filters.hours} onChange={(v) => setFilter("hours", v)} all="Any job type" options={counted(o.hours)} />
          <CollapsibleTrigger asChild>
            <Button variant="outline">
              More filters{moreActive ? ` (${moreActive})` : ""}
              <ChevronDown className={`size-3 transition-transform ${moreOpen ? "rotate-180" : ""}`} aria-hidden="true" />
            </Button>
          </CollapsibleTrigger>
        </div>

        <CollapsibleContent className="more-row">
          <FilterSelect id="f-origin" label="Added via" value={filters.origin} onChange={(v) => setFilter("origin", v)} all="Any origin" options={Object.entries(ORIGIN_FILTERS)} />
          <FilterSelect id="f-country" label="Country" value={filters.country} onChange={(v) => setFilter("country", v)} all="All countries" options={counted(o.countries)} />
          <FilterSelect id="f-remote" label="Remote" value={filters.remote} onChange={(v) => setFilter("remote", v)} all="Remote or on-site"
            options={[["true", "Remote only"], ["false", "On-site only"]]} />
          <FilterSelect id="f-pay" label="Minimum pay" value={filters.min_salary} onChange={number("min_salary")} all="Any pay"
            options={MIN_PAY.map((v) => [v, `${money(v)}+ a year`])} />
          <div className="flex h-9 items-center gap-2 px-1">
            <Checkbox id="f-has-pay" checked={filters.has_pay} onCheckedChange={(v) => setFilter("has_pay", v === true)} />
            <Label htmlFor="f-has-pay" className="font-normal">Listed pay only</Label>
          </div>
        </CollapsibleContent>
      </Collapsible>

      <ActiveFilters active={active} clearFilter={clearFilter} resetFilters={resetFilters} />
    </section>
  );
}
