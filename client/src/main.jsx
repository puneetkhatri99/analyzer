import React from "react";
import ReactDOM from "react-dom/client";
import Landing from "./Landing.jsx";
import Report from "./Report.jsx";
import "./styles.css";
import "./public.css";

// The admin bundle (tables, charts) loads only on /admin, so the public pages stay light.
const Admin = React.lazy(() => import("./Admin.jsx"));
const PAGES = { "/admin": Admin, "/report": Report };
const Page = PAGES[window.location.pathname.replace(/\/$/, "")] || Landing;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <React.Suspense fallback={null}><Page /></React.Suspense>
  </React.StrictMode>
);
