import React, { useState } from "react";
import { Link2, Mail, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { shareLinks } from "../lib/share.js";

// Share: copy the report's link (whoever opens it signs up first) or email it from the visitor's own mail app.
// Downloading is the separate "Download report" button.
export default function ShareMenu({ r }) {
  const [copied, setCopied] = useState(false);
  if (!r) return <Button type="button" className="mh-btn mh-btn-outline" disabled><Share2 className="size-4" aria-hidden="true" />Share</Button>;

  const { url, mailto } = shareLinks(window.location.href, `${r.title.role} pay in ${r.title.area}`);
  const copy = () => {
    navigator.clipboard.writeText(url)
      .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); })
      .catch(() => window.prompt("Copy this link", url)); // clipboard blocked (no permission or not https)
  };

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button type="button" className="mh-btn mh-btn-outline">
          <Share2 className="size-4" strokeWidth={2.2} aria-hidden="true" />
          <span aria-live="polite">{copied ? "Link copied" : "Share"}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={copy} data-track="Copy share link"><Link2 />Copy link</DropdownMenuItem>
        <DropdownMenuItem asChild><a href={mailto} data-track="Email the report link"><Mail />Email</a></DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
