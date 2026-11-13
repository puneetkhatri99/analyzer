import React from "react";
import { count, listedPay } from "@/lib/format.js";

// What the AI read from the page, field by field, so the admin can check it before saving.
export default function JobFields({ job }) {
  const pay = listedPay(job);
  const rows = [
    ["Job title", job.job_title],
    ["Organization", job.org_name],
    ["Website", job.org_website],
    ["Location", [job.city, job.state, job.country].filter(Boolean).join(", ")],
    ["Pay", pay && `${pay.amount} ${pay.unit}`],
    ["Job type", job.hours],
    ["Remote", job.remote == null ? null : job.remote ? "Yes" : "No"],
    ["Denomination", job.denomination],
    ["Church size", job.church_size != null && `${count(job.church_size)} weekly attendance`],
    ["Date posted", job.date_posted],
  ];
  return (
    <dl className="details">
      {rows.map(([label, value]) => (
        <React.Fragment key={label}>
          <dt>{label}</dt>
          <dd className={value ? "" : "muted"}>{value || "Not stated"}</dd>
        </React.Fragment>
      ))}
    </dl>
  );
}
