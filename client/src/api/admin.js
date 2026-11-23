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
// who to contact about a BizDev job (editors and admins only; the job lists never carry it)
export const fetchJobContact = (source, id) => getJSON(`/api/admin/jobs/contact?${toQuery({ source, id })}`);
// rejected feed postings: out of every view and figure, and skipped when the feed sends them again
export const rejectJob = (id, reason) => postJSON("/api/admin/jobs/reject", { id, reason });
export const setEmployerFacts = (source, id, facts) => patchJSON("/api/admin/employer", { source, id, ...facts });
export const fetchRejected = () => getJSON("/api/admin/rejected");
export const restoreRejected = (id) => postJSON("/api/admin/rejected/restore", { id });

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
// the monthly spending limit in dollars (null removes it): at the limit, nothing calls OpenAI
export const saveCostLimit = (limit_usd) => patchJSON("/api/admin/costs/limit", { limit_usd });
// the calls list (filtered, paged) and deleting rows; every total is summed from the same rows
export const fetchCostCalls = (filters, page) => getJSON(`/api/admin/costs/calls?${toQuery({ ...filters, page })}`);
export const deleteCostCalls = (ids) => postJSON("/api/admin/costs/calls/delete", { ids });
export const deleteMatchingCostCalls = (filters) => postJSON("/api/admin/costs/calls/delete-matching", filters);

// leads (visitors who signed up for a report)
export const fetchLeads = () => getJSON("/api/admin/leads");
export const fetchLeadHistory = (email) => getJSON(`/api/admin/leads/${encodeURIComponent(email)}`);
export const deleteLead = (email) => del(`/api/admin/leads/${encodeURIComponent(email)}`);

// settings (who gets the daily lead report)
export const fetchSettings = () => getJSON("/api/admin/settings");
export const saveSettings = (settings) => patchJSON("/api/admin/settings", settings);
export const sendTestReport = () => postJSON("/api/admin/settings/test-email");

// daily jobs feed (the signed link the server downloads every day)
export const fetchFeed = () => getJSON("/api/admin/feed");
export const saveFeedLink = (url) => postJSON("/api/admin/feed", { url });
export const runFeedNow = () => postJSON("/api/admin/feed/run");

// weekly BizDev sheets (the two workbook links the server downloads every week)
export const fetchBizdevSync = () => getJSON("/api/admin/bizdev-sync");
export const saveBizdevLink = (kind, url) => postJSON("/api/admin/bizdev-sync", { kind, url });
export const runBizdevSync = () => postJSON("/api/admin/bizdev-sync/run");
