import React from "react";
import ReactDOM from "react-dom/client";
import App, { pageFor } from "@/app/App.jsx";
import "@/styles/index.css";
import "@/styles/admin.css";
import "@/styles/public.css";

const Page = pageFor(window.location.pathname);
// Picks the shadcn theme in styles/index.css. Pop-ups render outside the page, so it goes on <html>.
document.documentElement.dataset.site = window.location.pathname.startsWith("/admin") ? "admin" : "public";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App Page={Page} />
  </React.StrictMode>
);
