// Admin API. Every call rides on the session cookie; the server checks the role.
import { del, getJSON, patchJSON, postJSON, toQuery } from "./http.js";

// session
export const fetchMe = () => getJSON("/api/admin/me").catch((e) => (e.status === 401 ? null : Promise.reject(e)));
export const signIn = (email, password) => postJSON("/api/admin/login", { email, password });
export const signOut = () => postJSON("/api/admin/logout");
export const changePassword = (current, next) => postJSON("/api/admin/password", { current_password: current, new_password: next });

// jobs dashboard
export const fetchSources = () => getJSON("/api/sources");
export const fetchFilterOptions = (source) => getJSON(`/api/filter-options?${toQuery({ source })}`);
export const fetchSummary = (source, filters) => getJSON(`/api/summary?${toQuery({ source, ...filters })}`);
export const fetchJobs = (source, filters) => getJSON(`/api/jobs?${toQuery({ source, ...filters })}`);
export const deleteJob = (source, id) => del(`/api/admin/jobs?${toQuery({ source, id })}`);

// adding a job from a URL
export const extractJob = (url) => postJSON("/api/admin/extract", { url });
export const saveJob = (body) => postJSON("/api/admin/jobs", body);

// users
const userPath = (email) => `/api/admin/users/${encodeURIComponent(email)}`;
export const fetchUsers = () => getJSON("/api/admin/users");
export const createUser = (user) => postJSON("/api/admin/users", user);
export const updateUser = (email, change) => patchJSON(userPath(email), change);
export const removeUser = (email) => del(userPath(email));

// AI costs
export const fetchCosts = () => getJSON("/api/admin/costs");

// leads (visitors who signed up for a report)
export const fetchLeads = () => getJSON("/api/admin/leads");
export const fetchLeadHistory = (email) => getJSON(`/api/admin/leads/${encodeURIComponent(email)}`);

// settings (who gets the daily lead report)
export const fetchSettings = () => getJSON("/api/admin/settings");
export const saveSettings = (settings) => patchJSON("/api/admin/settings", settings);
export const sendTestReport = () => postJSON("/api/admin/settings/test-email");
