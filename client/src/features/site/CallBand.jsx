import React from "react";
import { Button } from "@/components/ui/button";
import { BOOK_URL } from "./links.js";

// The book-a-call band that closes the landing page and the report.
export default function CallBand({ title, children, secondary }) {
  return (
    <section className="mh-band" data-reveal>
      <div>
        <h2>{title}</h2>
        <p>{children}</p>
      </div>
      <div className="mh-band-actions">
        <Button asChild className="mh-btn mh-btn-yellow"><a href={BOOK_URL} data-track>Book a search strategy call</a></Button>
        {secondary}
      </div>
    </section>
  );
}
