import React, { useState } from "react";
import { ExternalLink } from "lucide-react";
import { ORIGINS, count, listedPay, longDate, money } from "../format.js";
import Confirm from "./Confirm.jsx";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const yesNo = (v) => (v == null || v === "" ? null : String(v) === "true" ? "Yes" : "No");

function statusText(d) {
  if (d.status === "expired") return `Expired · found closed ${longDate(d.expired_at)}${d.last_live_at ? `, last seen open ${longDate(d.last_live_at)}` : ""}`;
  if (d.status === "open") return `Open · checked ${longDate(d.last_live_at)}`;
  return "Not verified · the job page couldn’t be checked";
}

// onDelete is given only to users who may delete (editors and admins); it returns a promise.
// returnFocus puts focus back on the job's row once the dialog has closed.
export default function JobDetail({ job, onClose, onDelete, returnFocus }) {
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
          {count(job.church_size)}+ weekly attendance
          {job.church_size_source && (
            <> · <a href={job.church_size_source} target="_blank" rel="noopener noreferrer">found online</a></>
          )}
        </>
      ) : null],
    ]],
    ["Record", [
      ["Date posted", job.first_indexed && longDate(job.first_indexed)],
      ["Status", statusText(job)],
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

        <DialogFooter className="flex-row flex-wrap justify-start sm:justify-start">
          {job.post_url && (
            <Button asChild>
              <a href={job.post_url} target="_blank" rel="noopener noreferrer">Open original posting <ExternalLink aria-hidden="true" /></a>
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>Close</Button>
          {onDelete && (
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
