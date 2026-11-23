import React from "react";
import { Button } from "@/components/ui/button";
import { PRIVACY_URL, TERMS_URL } from "@/features/site/links.js";
import FormSelect from "./FormSelect.jsx";
import TextField from "./TextField.jsx";
import { ANY_SIZE, NATIONWIDE, useLeadForm } from "./useLeadForm.js";

const pairs = (list) => (list || []).map((v) => [v, v]);

export default function LeadForm({ options }) {
  const { lead, next, form, set, forget, submit, checkChoices, busy, error, missing } = useLeadForm();
  return (
    <div className="mh-form-frame" data-reveal>
      <form className="mh-form" onSubmit={submit}>
        {next ? (
          <>
            <h2>A report was shared with you</h2>
            <p>Tell us who you are to open it. It's free.</p>
          </>
        ) : (
          <>
            <h2>Get your free report</h2>
            <p className="mh-step"><span>1</span>What are you hiring for?</p>
            <div className="mh-row">
              <FormSelect id="lead-role" label="Role" placeholder="Choose a role" value={form.role} onChange={set("role")}
                options={pairs(options?.roles)} required invalid={missing.includes("role")} />
              <FormSelect id="lead-location" label="Location" placeholder="Choose a state" value={form.location} onChange={set("location")}
                options={[[NATIONWIDE, "Anywhere in the US"], ...pairs(options?.states)]} required invalid={missing.includes("location")} />
            </div>
            <FormSelect id="lead-attendance" label="Church size (optional)" value={form.attendance} onChange={set("attendance")}
              options={[[ANY_SIZE, "Any size"], ...pairs(options?.sizes)]} />
          </>
        )}

        {lead ? (
          <p className="mh-returning">
            Welcome back, {lead.name}. <button type="button" className="mh-link" onClick={forget}>Not you?</button>
          </p>
        ) : (
          <>
            {!next && <p className="mh-step"><span>2</span>About you</p>}
            <TextField id="lead-name" label="Name" maxLength={200} autoComplete="name" placeholder="John Smith"
              value={form.name} onChange={set("name")} />
            <TextField id="lead-email" label="Email" type="email" maxLength={320} autoComplete="email" placeholder="john@yourchurch.org"
              value={form.email} onChange={set("email")} />
            <TextField id="lead-org" label="Church or organization" maxLength={300} autoComplete="organization"
              placeholder="Your church or organization" value={form.organization} onChange={set("organization")} />
          </>
        )}

        <label className="mh-switch">
          <input type="checkbox" role="switch" checked={form.emailReport} onChange={set("emailReport")} />
          <span>Email me this report{lead ? ` (to ${lead.email})` : ""}</span>
        </label>
        <label className="mh-switch">
          <input type="checkbox" checked={form.newsletter} onChange={set("newsletter")} />
          <span>Send me the MinistryHub newsletter</span>
        </label>

        {error && <p className="mh-error" role="alert">{error}</p>}
        <Button type="submit" className="mh-btn mh-btn-yellow mh-btn-block" disabled={busy || !options} onClick={checkChoices}>
          {busy ? "Preparing your report…" : <>See my report <span aria-hidden="true">→</span></>}
        </Button>
        <p className="mh-fine">
          By continuing you agree to our <a href={TERMS_URL} target="_blank" rel="noreferrer">Terms</a> and{" "}
          <a href={PRIVACY_URL} target="_blank" rel="noreferrer">Privacy Policy</a>.
        </p>
      </form>
    </div>
  );
}
