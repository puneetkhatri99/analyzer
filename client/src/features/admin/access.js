// Who sees what. The server enforces the same roles; hiding tabs is only for clarity.
export const ROLES = ["viewer", "editor", "admin"];
export const ROLE_TEXT = { admin: "Admin", editor: "Read and write", viewer: "Read only" };

export const can = (user, role) => ROLES.indexOf(user.role) >= ROLES.indexOf(role);

// [key, label, lowest role that sees it]
export const TABS = [
  ["jobs", "Jobs", "viewer"],
  ["add", "Add a job", "editor"],
  ["users", "Users", "admin"],
  ["costs", "AI costs", "admin"],
];
