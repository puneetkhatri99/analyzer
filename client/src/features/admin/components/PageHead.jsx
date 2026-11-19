import React from "react";

// The title of an admin page that has no tab of its own (Settings, AI costs): its name, one plain sentence about it,
// and optional actions on the right.
export default function PageHead({ title, children, actions }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 pb-1">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {children && <p className="mb-0 mt-1 max-w-[62ch] text-[15px] leading-6 text-muted-foreground">{children}</p>}
      </div>
      {actions}
    </div>
  );
}
