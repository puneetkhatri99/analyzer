import React from "react";
import SiteFooter from "./SiteFooter.jsx";
import SiteHeader from "./SiteHeader.jsx";
import { track } from "./lead.js";

// Clicks that matter for sales go into a signed-up visitor's history (admin → Leads): only elements marked
// `data-track`, so a new button isn't recorded by accident. Links to MinistryHub's site are "cta", the rest "click".
// Filter changes, downloads and offers are recorded by their own events, with their details.
// React passes clicks up from portals too, so items in dropdown menus are caught here as well.
function label(el) {
  return (el.dataset.track || el.textContent).replace(/\s+/g, " ").trim().slice(0, 120); // data-track="…" names it
}

function trackClick(e) {
  const el = e.target.closest?.("[data-track]");
  if (!el) return;
  if (el.matches("a[href^='http']")) track("cta", { label: label(el), url: el.href });
  else track("click", { label: label(el), page: window.location.pathname });
}

// The MinistryHub page frame. `after` sits outside the screen frame (the printed report).
export default function PublicLayout({ children, after }) {
  return (
    <div className="mh" onClick={trackClick}>
      <div className="mh-screen">
        <SiteHeader />
        <main>{children}</main>
        <SiteFooter />
      </div>
      {after}
    </div>
  );
}
