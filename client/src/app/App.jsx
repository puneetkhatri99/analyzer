import React, { Suspense, lazy } from "react";
import { BrowserRouter } from "react-router-dom";

// Each page loads as its own bundle, so a visitor downloads only the page they open
// (the admin table and charts never reach the public pages).
const LandingPage = lazy(() => import("@/features/landing/LandingPage.jsx"));
const ReportPage = lazy(() => import("@/features/report/ReportPage.jsx"));
const AdminApp = lazy(() => import("@/features/admin/AdminApp.jsx"));

const ROUTES = { "/admin": AdminApp, "/report": ReportPage };

export function pageFor(pathname) {
  return ROUTES["/" + pathname.split("/")[1]] || LandingPage;
}

export default function App({ Page }) {
  return <BrowserRouter><Suspense fallback={null}><Page /></Suspense></BrowserRouter>;
}
