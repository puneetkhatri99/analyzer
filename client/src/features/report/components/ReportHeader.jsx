import React from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import ShareMenu from "./ShareMenu.jsx";

// Title plus "Share" and "Download report" (prints the branded export; the browser saves it as a PDF).
export default function ReportHeader({ r }) {
  return (
    <div className="mh-report-head" data-reveal>
      <div>
        <p className="mh-eyebrow">Market Analysis Report</p>{/* taste-skill-ignore: label in the client's approved design */}
        <h1>{r ? <>{r.covers.role} pay in <span className="mh-underline">{r.covers.area}</span></> : "Loading your report…"}</h1>
      </div>
      <div className="mh-report-actions">
        <ShareMenu r={r} />
        <Button type="button" className="mh-btn mh-btn-yellow" onClick={() => window.print()} disabled={!r}>
          <Download className="size-4" strokeWidth={2.2} aria-hidden="true" />
          <span className="mh-wide-only">Download report</span><span className="mh-narrow-only">Download</span>
        </Button>
      </div>
    </div>
  );
}
