import React, { useEffect, useRef } from "react";
import { ORIGINS, count, listedPay, longDate, money } from "../format.js";

const yesNo = (v) => (v == null || v === "" ? null : String(v) === "true" ? "Yes" : "No");

function statusText(d) {
  if (d.status === "expired") return `Expired · found closed ${longDate(d.expired_at)}${d.last_live_at ? `, last seen open ${longDate(d.last_live_at)}` : ""}`;
  if (d.status === "open") return `Open · checked ${longDate(d.last_live_at)}`;
  return "Not verified · the job page couldn’t be checked";
}

export default function JobDetail({ job, onClose }) {
  const dialog = useRef(null);
  useEffect(() => {
    dialog.current?.showModal(); // native modal: traps focus, Esc closes
  }, []);

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
    <dialog ref={dialog} className="job-dialog" aria-labelledby="job-dialog-title" onClose={onClose}
      onClick={(e) => e.target === dialog.current && dialog.current.close()}>
      <div className="job-dialog-body">
        <header className="job-dialog-head">
          <div>
            <h2 id="job-dialog-title">{job.job_name || "Untitled role"}</h2>
            <p className="muted">{[job.company_name, location].filter(Boolean).join(" · ") || "Employer not stated"}</p>
          </div>
          <button type="button" className="btn icon-btn" aria-label="Close" onClick={() => dialog.current.close()}>
            <svg width="14" height="14" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
          </button>
        </header>

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

        <footer className="job-dialog-foot">
          {job.post_url && (
            <a className="btn btn-primary" href={job.post_url} target="_blank" rel="noopener noreferrer">Open original posting ↗</a>
          )}
          <button type="button" className="btn" onClick={() => dialog.current.close()}>Close</button>
        </footer>
      </div>
    </dialog>
  );
}
