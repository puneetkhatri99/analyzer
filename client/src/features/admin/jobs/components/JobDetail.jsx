import React, { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { ORIGINS, count, listedPay, longDate, money } from "@/lib/format.js";
import Confirm from "@/components/Confirm.jsx";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const yesNo = (v) => (v == null || v === "" ? null : String(v) === "true" ? "Yes" : "No");

// Rejecting a feed posting moves it to the Rejected jobs tab: out of every view and figure, and skipped when the feed
// sends it again. It can be included again from that tab.
function RejectForm({ onReject }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState(null);
  return (
    <section>
      <h3>Not a church, school or ministry job?</h3>
      <form className="mt-2 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); onReject(reason.trim()).catch((err) => setError(err.message)); }}>
        <Input aria-label="Why reject this job" placeholder="Why, e.g. public school, not a church" className="min-w-0 flex-1"
          value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} />
        <Button type="submit" variant="outline" size="sm">Reject job</Button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  );
}

// An editor fills in what the AI couldn't find (brief: "manually work through ones without church size"). It applies to
// every job of this employer; an empty box leaves that value as it is.
function EmployerFactsForm({ job, onSave }) {
  const [size, setSize] = useState("");
  const [denomination, setDenomination] = useState("");
  const [error, setError] = useState(null);
  const save = (e) => {
    e.preventDefault();
    const facts = {};
    if (size.trim()) facts.church_size = Number(size);
    if (denomination.trim()) facts.denomination = denomination.trim();
    if (!Object.keys(facts).length) return setError("Enter a church size, a denomination, or both.");
    onSave(facts).catch((err) => setError(err.message));
  };
  return (
    <section>
      <h3>Fill in the employer</h3>
      <p className="muted small">Saved for every job of {job.company_name || "this employer"}. Leave a box empty to keep its value.</p>
      <form className="mt-2 flex flex-wrap gap-2" onSubmit={save}>
        <Input aria-label="Church size" placeholder="Church size, e.g. 450" type="number" min={1} max={100000}
          className="w-44" value={size} onChange={(e) => setSize(e.target.value)} />
        <Input aria-label="Denomination" placeholder="Denomination" className="min-w-0 flex-1" maxLength={80}
          value={denomination} onChange={(e) => setDenomination(e.target.value)} />
        <Button type="submit" variant="outline" size="sm">Save</Button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  );
}

// The person to contact about a BizDev job, from the sheet. Only editors and admins get onContact; the job lists never carry it.
function Contact({ onContact }) {
  const [contact, setContact] = useState(undefined); // undefined = loading
  const [error, setError] = useState(null);
  useEffect(() => { onContact().then(setContact).catch((e) => { setError(e.message); setContact(null); }); }, []);
  const name = contact && [contact.first_name, contact.last_name].filter(Boolean).join(" ");
  return (
    <section>
      <h3>Person to contact</h3>
      {contact === undefined && <p className="muted small" aria-busy="true">Loading…</p>}
      {error && <p className="form-error" role="alert">Couldn’t load the contact ({error})</p>}
      {contact && (
        <dl className="details">
          <dt>Name</dt><dd className={name ? "" : "muted"}>{name || "Not stated"}</dd>
          <dt>Title</dt><dd className={contact.title ? "" : "muted"}>{contact.title || "Not stated"}</dd>
          <dt>Email</dt>
          <dd className={contact.email ? "" : "muted"}>{contact.email ? <a href={`mailto:${contact.email}`}>{contact.email}</a> : "Not stated"}</dd>
        </dl>
      )}
    </section>
  );
}

// onDelete and onReject are given only to users who may change jobs (editors and admins); they return promises.
// onContact (editors and admins, BizDev jobs only) loads the person to contact. returnFocus puts focus back on the
// job's row once the dialog has closed.
export default function JobDetail({ job, onClose, onDelete, onReject, onContact, onSetFacts, returnFocus }) {
  const [deleteError, setDeleteError] = useState(null);

  const pay = listedPay(job);
  const location = [job.city, job.region, job.country].filter(Boolean).join(", ");
  const sections = [
    ["The job", [
      ["Role", job.role],
      ["Job type", job.hours],
      ["Remote", yesNo(job.remote)],
      ["Seniority", job.seniority],
      ["Department", job.department],
      ["Location", location],
    ]],
    ["The employer", [
      ["Organization", job.company_name],
      ["Denomination", job.denomination],
      ["Church size", job.church_size != null ? (
        <>
          {count(job.church_size)}+
          {/^https?:\/\//i.test(job.church_size_source || "") && (
            <> · <a href={job.church_size_source} target="_blank" rel="noopener noreferrer">found online</a></>
          )}
          {/^entered by /.test(job.church_size_source || "") && <> · {job.church_size_source}</>}
        </>
      ) : null],
    ]],
    ["Record", [
      ["Date posted", job.first_indexed && longDate(job.first_indexed)],
      ["Added via", `${ORIGINS[job.origin] || job.origin}${job.added_at ? ` · ${longDate(job.added_at)}` : ""}`],
      ["Job site", job.board_source],
    ]],
  ];

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="job-dialog max-h-[calc(100vh-48px)] gap-5 overflow-y-auto sm:max-w-[640px]"
        onCloseAutoFocus={(e) => { e.preventDefault(); returnFocus?.(); }}>
        <DialogHeader className="text-left">
          <DialogTitle className="pr-8 text-xl">{job.job_name || "Untitled role"}</DialogTitle>
          <DialogDescription>{[job.company_name, location].filter(Boolean).join(" · ") || "Employer not stated"}</DialogDescription>
        </DialogHeader>

        <div>
          {pay
            ? <p className="job-dialog-pay"><span className="num">{pay.amount}</span><span className="pay-unit">{pay.unit}</span></p>
            : <p className="job-dialog-pay muted">No pay listed</p>}
          {job.salary_period === "hour" && job.salary_annual_mid && (
            <p className="muted small">About {money(job.salary_annual_mid)} a year at 2,080 hours</p>
          )}
        </div>

        {sections.map(([title, rows]) => (
          <section key={title}>
            <h3>{title}</h3>
            <dl className="details">
              {rows.map(([label, value]) => (
                <React.Fragment key={label}>
                  <dt>{label}</dt>
                  <dd className={value ? "" : "muted"}>{value || "Not stated"}</dd>
                </React.Fragment>
              ))}
            </dl>
          </section>
        ))}
        {onSetFacts && <EmployerFactsForm job={job} onSave={onSetFacts} />}
        {onContact && <Contact onContact={onContact} />}
        {job.source === "json" && onReject && <RejectForm onReject={onReject} />}

        <DialogFooter className="flex-row flex-wrap justify-start sm:justify-start">
          {job.post_url && (
            <Button asChild>
              <a href={job.post_url} target="_blank" rel="noopener noreferrer">Open original posting <ExternalLink aria-hidden="true" /></a>
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>Close</Button>
          {onDelete && job.source !== "json" && ( // feed jobs are rejected instead, so the feed skips them later
            <Confirm title={`Delete “${job.job_name || "this job"}”?`} action="Delete job"
              description="It is removed for good from every view and report."
              onConfirm={() => onDelete().catch((e) => setDeleteError(e.message))}>
              <Button variant="outline" className="ml-auto border-[#f0c4c6] text-destructive hover:border-destructive hover:bg-[#fdf2f2] hover:text-destructive">Delete job</Button>
            </Confirm>
          )}
        </DialogFooter>
        {deleteError && <p className="form-error" role="alert">{deleteError}</p>}
      </DialogContent>
    </Dialog>
  );
}
