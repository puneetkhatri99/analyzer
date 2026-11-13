import React, { useState } from "react";
import { extractJob, saveJob } from "@/api/admin.js";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import ExtractedJobCard from "./ExtractedJobCard.jsx";

// Paste a job page's URL, let the AI read it, review, then save it to a BizDev dataset.
export default function AddJobPage() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [dataset, setDataset] = useState("churches");
  const [saved, setSaved] = useState(null);

  const run = (promise) => {
    setBusy(true);
    setError(null);
    return promise.catch((err) => setError(err.message)).finally(() => setBusy(false));
  };

  const extract = (e) => {
    e.preventDefault();
    setResult(null);
    setSaved(null);
    run(extractJob(url.trim()).then((r) => {
      setResult(r);
      setDataset(r.job.category === "church" ? "churches" : "nonprofits");
    }));
  };

  const save = () => run(saveJob({ url: result.url, dataset, method: result.method, job: result.job, church_size_source: result.church_size_source })
    .then(() => setSaved(dataset)));

  const job = result?.job;
  return (
    <>
      <Card>
        <CardHeader><CardTitle>Add a job from a URL</CardTitle></CardHeader>
        <form className="url-form" onSubmit={extract}>
          <Label className="sr-only" htmlFor="job-url">Job posting URL</Label>
          <Input id="job-url" type="url" required placeholder="https://… link to a single job posting"
            value={url} onChange={(e) => setUrl(e.target.value)} disabled={busy} />
          <Button type="submit" disabled={busy || !url.trim()}>{busy && !result ? "Reading page…" : "Fetch job"}</Button>
        </form>
        <p className="card-note">
          The page is read and an AI model extracts the job’s details. Blocked or JavaScript-only pages are read through web search,
          which can take up to a minute. Nothing is saved until you review it.
        </p>
        {error && <p className="form-error" role="alert">{error}</p>}
      </Card>

      {job && job.page_type !== "job_posting" && (
        <Alert variant="notice" role="status">
          <AlertTitle className="line-clamp-none">
            {job.page_type === "unreadable" ? "This page couldn’t be read as a job posting." : "This is not a job posting."}
          </AlertTitle>
          <AlertDescription className="text-inherit">{job.reason}</AlertDescription>
        </Alert>
      )}

      {job && job.page_type === "job_posting" && (
        <ExtractedJobCard result={result} dataset={dataset} busy={busy} saved={saved} onSave={save}
          onDatasetChange={(v) => { setDataset(v); setSaved(null); }} />
      )}
    </>
  );
}
