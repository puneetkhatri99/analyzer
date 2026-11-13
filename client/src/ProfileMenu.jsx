import React, { useEffect, useRef, useState } from "react";

// The signed-in user's menu: who they are, their access, and the account actions.
export default function ProfileMenu({ email, roleText, onChangePassword, onSignOut }) {
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const button = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    box.current.querySelector("[role=menuitem]")?.focus();
    const outside = (e) => !box.current.contains(e.target) && setOpen(false);
    const key = (e) => {
      if (e.key === "Escape") { setOpen(false); button.current.focus(); }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const items = [...box.current.querySelectorAll("[role=menuitem]")];
        const i = items.indexOf(document.activeElement);
        items[(i + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length].focus();
      }
    };
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", outside); document.removeEventListener("keydown", key); };
  }, [open]);

  const pick = (action) => () => { setOpen(false); action(); };

  return (
    <div className="profile" ref={box}>
      <button ref={button} type="button" className="profile-button" aria-haspopup="menu" aria-expanded={open}
        aria-label={`Profile: ${email}`} onClick={() => setOpen(!open)}>
        <span className="avatar" aria-hidden="true">{email[0].toUpperCase()}</span>
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 3.5l3 3 3-3" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      {open && (
        <div className="profile-menu" role="menu" aria-label="Profile">
          <div className="profile-who">
            <span className="avatar large" aria-hidden="true">{email[0].toUpperCase()}</span>
            <span>
              <strong>{email}</strong>
              <span className="profile-role">{roleText}</span>
            </span>
          </div>
          <button type="button" role="menuitem" className="profile-item" onClick={pick(onChangePassword)}>Change password</button>
          <button type="button" role="menuitem" className="profile-item" onClick={pick(onSignOut)}>Sign out</button>
        </div>
      )}
    </div>
  );
}
