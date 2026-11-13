import React from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ORIGINS } from "@/lib/format.js";
import JobFields from "./JobFields.jsx";

const DATASETS = { churches: "BizDev churches", nonprofits: "BizDev nonprofits" };

// The review step: the extracted job, any warnings, and where to save it.
export default function ExtractedJobCard({ result, dataset, onDatasetChange, onSave, busy, saved }) {
  const job = result.job;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Review the extracted job</CardTitle>
        <CardDescription>Will be saved as “{ORIGINS[`admin_${result.method}`]}”</CardDescription>
      </CardHeader>
      <p className="finding">{job.reason}</p>
      {result.warnings.length > 0 && (
        <Alert variant="notice" role="status" className="mt-3" aria-label="Check before saving">
          <ul className="m-0 list-disc pl-4">{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </Alert>
      )}
      <JobFields job={job} />
      <div className="save-row">
        <div className="flex items-center gap-2.5">
          <Label htmlFor="save-dataset">Add to</Label>
          <Select value={dataset} onValueChange={onDatasetChange} disabled={busy}>
            <SelectTrigger id="save-dataset"><SelectValue /></SelectTrigger>
            <SelectContent>
              {Object.entries(DATASETS).map(([k, label]) => <SelectItem key={k} value={k}>{label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button type="button" onClick={onSave} disabled={busy || saved === dataset}>
          {saved === dataset ? "Saved" : busy ? "Saving…" : "Save job"}
        </Button>
        {saved && <a href={`/admin?source=${saved}&search=${encodeURIComponent(job.job_title || "")}`}>View it in Jobs</a>}
      </div>
      {job.category === "other" && <p className="card-note">The AI thinks this employer is a for-profit company. Check it belongs here before saving.</p>}
    </Card>
  );
}
