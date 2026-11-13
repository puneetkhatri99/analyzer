import React from "react";
import { Button } from "@/components/ui/button";
import { BOOK_URL, HOW_URL, SERVICES_URL } from "./links.js";

export default function SiteHeader() {
  return (
    <header className="mh-header">
      <div className="mh-wrap mh-header-inner">
        <a href="/" className="mh-logo-link"><img className="mh-logo" src="/ministryhub-logo.png" alt="MinistryHub" /></a>
        <nav className="mh-nav" aria-label="MinistryHub">
          <a href={SERVICES_URL}>Search Services</a>
          <a href={HOW_URL}>How a Search Works</a>
          <Button asChild className="mh-btn mh-btn-teal"><a href={BOOK_URL}>Book a Call</a></Button>
        </nav>
      </div>
    </header>
  );
}
