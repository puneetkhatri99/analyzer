import React from "react";
import { ROLE_TEXT } from "../access.js";
import ProfileMenu from "./ProfileMenu.jsx";

export default function AdminHeader({ user, sections, onOpen, onChangePassword, onSignOut }) {
  return (
    <header className="topbar admin-topbar">
      <div className="topbar-inner">
        <div className="brand">
          <img className="brand-logo" src="/ministryhub-logo.png" alt="MinistryHub" />
          <span className="brand-name">Market Analysis Tool</span>
        </div>
        <div className="topbar-actions">
          <a href="/">Public tool</a>
          <ProfileMenu email={user.email} roleText={ROLE_TEXT[user.role]} sections={sections} onOpen={onOpen}
            onChangePassword={onChangePassword} onSignOut={onSignOut} />
        </div>
      </div>
    </header>
  );
}
