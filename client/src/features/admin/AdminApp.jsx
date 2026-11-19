import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MENU_SECTIONS, TABS, can } from "./access.js";
import AddJobPage from "./add-job/AddJobPage.jsx";
import ChangePasswordForm from "./auth/ChangePasswordForm.jsx";
import LoginPage from "./auth/LoginPage.jsx";
import { useSession } from "./auth/useSession.js";
import CostsPage from "./costs/CostsPage.jsx";
import JobsPage from "./jobs/JobsPage.jsx";
import LeadsPage from "./leads/LeadsPage.jsx";
import RejectedPage from "./rejected/RejectedPage.jsx";
import SettingsPage from "./settings/SettingsPage.jsx";
import AdminHeader from "./layout/AdminHeader.jsx";
import UsersPage from "./users/UsersPage.jsx";

const PASSWORD = "password"; // opened from the profile menu, so it has no tab of its own
const PANEL = "flex min-w-0 flex-col gap-3";

// The hash keeps the open section across reloads: /admin#users
function useSection() {
  const [section, setSection] = useState(window.location.hash.slice(1) || "jobs");
  const show = (next) => {
    setSection(next);
    window.history.replaceState(null, "", next === "jobs" ? window.location.pathname + window.location.search : `#${next}`);
  };
  return [section, show];
}

export default function AdminApp() {
  const { user, setUser, refresh, signOut } = useSession();
  const [section, showSection] = useSection();

  if (user === undefined) return null;
  if (!user) return <LoginPage onSignedIn={setUser} />;

  const tabs = TABS.filter(([, , role]) => can(user, role));
  const menu = MENU_SECTIONS.filter(([, , role]) => can(user, role));
  const opens = (k) => k === section;
  const current = section === PASSWORD || tabs.some(([k]) => opens(k)) || menu.some(([k]) => opens(k)) ? section : "jobs";
  return (
    <>
      <AdminHeader user={user} sections={menu} onOpen={showSection} onChangePassword={() => showSection(PASSWORD)} onSignOut={signOut} />
      {user.must_change_password ? (
        <main className="login"><ChangePasswordForm forced onDone={refresh} /></main>
      ) : (
        <main className="canvas admin">
          <Tabs value={current} onValueChange={showSection} className="gap-3">
            <TabsList variant="line" aria-label="Admin sections" className="admin-tabs max-w-full justify-start overflow-x-auto">
              {tabs.map(([key, label]) => <TabsTrigger key={key} value={key} className="flex-none px-3">{label}</TabsTrigger>)}
            </TabsList>
            <TabsContent value="jobs" className={PANEL}><JobsPage canEdit={can(user, "editor")} /></TabsContent>
            <TabsContent value="rejected" className={PANEL}><RejectedPage canEdit={can(user, "editor")} /></TabsContent>
            <TabsContent value="add" className={PANEL}><AddJobPage /></TabsContent>
            <TabsContent value="leads" className={PANEL}><LeadsPage /></TabsContent>
            <TabsContent value="users" className={PANEL}><UsersPage me={user.email} /></TabsContent>
            <TabsContent value="costs" className={PANEL}><CostsPage /></TabsContent>
            <TabsContent value="settings" className={PANEL}><SettingsPage onOpenCosts={() => showSection("costs")} /></TabsContent>
            {current === PASSWORD && <div className="password-page"><ChangePasswordForm /></div>}
          </Tabs>
        </main>
      )}
    </>
  );
}
