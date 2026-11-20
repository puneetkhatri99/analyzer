// Who sees what. The server enforces the same roles; hiding tabs is only for clarity.
export const ROLES = ["viewer", "editor", "admin"];
export const ROLE_TEXT = { admin: "Admin", editor: "Read and write", viewer: "Read only" };

export const can = (user, role) => ROLES.indexOf(user.role) >= ROLES.indexOf(role);

// [key, label, lowest role that sees it]
export const TABS = [
  ["jobs", "Jobs", "viewer"],
  ["add", "Add a job", "editor"],
  ["leads", "Leads", "admin"],
  ["users", "Users", "admin"],
];

// Opened from the profile menu (the round button top right), not from the tabs: the same shape as TABS.
export const MENU_SECTIONS = [
  ["rejected", "Rejected jobs", "viewer"],
  ["settings", "Settings", "admin"],
  ["costs", "AI costs", "admin"],
];
