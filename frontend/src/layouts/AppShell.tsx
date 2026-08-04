import { Outlet } from "react-router-dom";

import { SiteHeader } from "@/components/SiteHeader";

export function AppShell() {
  return (
    <div className="min-h-screen bg-hero-grid">
      <SiteHeader />
      <main className="relative mx-auto w-full max-w-6xl px-4 pb-16 pt-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
