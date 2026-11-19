import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import PageHead from "../components/PageHead.jsx";
import BizdevSyncSettings from "./BizdevSyncSettings.jsx";
import EmailSettings from "./EmailSettings.jsx";
import FeedSettings from "./FeedSettings.jsx";
import Overview from "./Overview.jsx";

// Admin only. Opens on a plain-words summary of what runs by itself; each area then has its own view.
// "stamp" is bumped whenever something is saved or a run finishes, so the summary re-reads the facts.
export default function SettingsPage({ onOpenCosts }) {
  const [tab, setTab] = useState("overview");
  const [stamp, setStamp] = useState(0);
  const changed = () => setStamp((s) => s + 1);
  return (
    <>
      <PageHead title="Settings">Most of this app runs by itself. Start with what is happening; change things in the other two sections.</PageHead>
      <Tabs value={tab} onValueChange={setTab} className="gap-5">
        <TabsList variant="line" aria-label="Settings sections" className="admin-tabs max-w-full justify-start overflow-x-auto">
          <TabsTrigger value="overview" className="flex-none px-2.5 sm:px-3">What’s happening</TabsTrigger>
          <TabsTrigger value="email" className="flex-none px-2.5 sm:px-3">Email</TabsTrigger>
          <TabsTrigger value="jobs" className="flex-none px-2.5 sm:px-3">Job downloads</TabsTrigger>
        </TabsList>
        <TabsContent value="overview"><Overview stamp={stamp} go={setTab} onOpenCosts={onOpenCosts} /></TabsContent>
        <TabsContent value="email"><EmailSettings onChanged={changed} /></TabsContent>
        <TabsContent value="jobs"><FeedSettings onChanged={changed} /><BizdevSyncSettings onChanged={changed} /></TabsContent>
      </Tabs>
    </>
  );
}
