import { Link, NavLink } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "text-sm transition",
    isActive ? "text-accent" : "text-ink-muted hover:text-ink",
  ].join(" ");

export function SiteHeader() {
  const { user, logout, loading } = useAuth();
  const isAdmin = !!user?.roles.includes("admin");

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-canvas/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="font-display text-lg font-semibold tracking-tight text-ink">
          InterviewAI <span className="text-accent">Pro</span>
        </Link>
        <nav className="flex items-center gap-3 sm:gap-5">
          <NavLink to="/" end className={linkClass}>
            Home
          </NavLink>
          {user && (
            <>
              <NavLink to="/dashboard" className={linkClass}>
                Dashboard
              </NavLink>
              <NavLink to="/resumes" className={linkClass}>
                Resumes
              </NavLink>
              <NavLink to="/interviews" className={linkClass}>
                Interviews
              </NavLink>
              <NavLink to="/coding" className={linkClass}>
                Coding
              </NavLink>
              <NavLink to="/reports" className={linkClass}>
                Reports
              </NavLink>
              <NavLink to="/coach" className={linkClass}>
                Coach
              </NavLink>
              <NavLink to="/roadmaps" className={linkClass}>
                Roadmaps
              </NavLink>
              <NavLink to="/billing" className={linkClass}>
                Billing
              </NavLink>
              <NavLink to="/settings" className={linkClass}>
                Settings
              </NavLink>
            </>
          )}
          {isAdmin && (
            <NavLink to="/admin" className={linkClass}>
              Admin
            </NavLink>
          )}
          <NavLink to="/system/health" className={linkClass}>
            System
          </NavLink>
          {!loading && !user && (
            <>
              <NavLink to="/login" className={linkClass}>
                Sign in
              </NavLink>
              <Link to="/signup" className="btn-primary text-sm">
                Get started
              </Link>
            </>
          )}
          {!loading && user && (
            <button type="button" className="btn-ghost text-sm" onClick={() => void logout()}>
              Sign out
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
