import React from "react";
import SiteFooter from "./SiteFooter.jsx";
import SiteHeader from "./SiteHeader.jsx";

// The MinistryHub page frame. `after` sits outside the screen frame (the printed report).
export default function PublicLayout({ children, after }) {
  return (
    <div className="mh">
      <div className="mh-screen">
        <SiteHeader />
        <main>{children}</main>
        <SiteFooter />
      </div>
      {after}
    </div>
  );
}
