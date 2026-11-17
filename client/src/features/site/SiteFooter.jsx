import React from "react";
import { PRIVACY_URL, SITE_URL, TERMS_URL } from "./links.js";

export default function SiteFooter() {
  return (
    <footer className="mh-footer">
      <div className="mh-wrap mh-footer-inner">
        <div className="mh-footer-brand">
          <img className="mh-logo" src="/ministryhub-logo-white.png" alt="MinistryHub" />
          <strong>Power Your Mission With The Right Team.</strong>
        </div>
        <span>© {new Date().getFullYear()} MinistryHub · <a href={SITE_URL} data-track>ministryhub.org</a> · <a href={PRIVACY_URL}>Privacy Policy</a> · <a href={TERMS_URL}>Terms</a></span>
      </div>
    </footer>
  );
}
