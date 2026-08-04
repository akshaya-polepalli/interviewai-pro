import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <p className="text-ink-muted">Loading session…</p>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <p className="text-ink-muted">Loading session…</p>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (!user.roles.includes("admin")) {
    return (
      <div className="glass-panel mx-auto max-w-lg p-8 text-center">
        <h1 className="font-display text-2xl font-semibold">Admin access required</h1>
        <p className="mt-2 text-ink-muted">Your account does not have the admin role.</p>
      </div>
    );
  }
  return <>{children}</>;
}
