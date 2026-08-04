import { useEffect, useState, type FormEvent } from "react";
import { AxiosError } from "axios";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/contexts/AuthContext";
import * as usersApi from "@/services/users";
import { clearTokens } from "@/services/tokenStorage";
import type { ApiErrorBody } from "@/types/auth";

const TARGET_ROLES = [
  "software_engineer",
  "backend_engineer",
  "frontend_engineer",
  "full_stack_engineer",
  "data_analyst",
  "ml_engineer",
  "devops_engineer",
  "student",
  "other",
];

const TARGET_COMPANIES = [
  "google",
  "amazon",
  "microsoft",
  "meta",
  "apple",
  "netflix",
  "stripe",
  "openai",
  "general",
];

export function SettingsPage() {
  const { user, setUser, logout } = useAuth();
  const queryClient = useQueryClient();
  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: usersApi.fetchProfile,
  });
  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: usersApi.listSessions,
  });

  const [fullName, setFullName] = useState("");
  const [bio, setBio] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [targetCompany, setTargetCompany] = useState("");
  const [years, setYears] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [deletePassword, setDeletePassword] = useState("");

  useEffect(() => {
    if (profileQuery.data) {
      setFullName(profileQuery.data.full_name);
      setBio(profileQuery.data.bio ?? "");
      setTargetRole(profileQuery.data.target_role ?? "");
      setTargetCompany(profileQuery.data.target_company ?? "");
      setYears(
        profileQuery.data.years_of_experience != null
          ? String(profileQuery.data.years_of_experience)
          : "",
      );
    }
  }, [profileQuery.data]);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const updated = await usersApi.updateProfile({
        full_name: fullName,
        bio: bio || null,
        target_role: targetRole || null,
        target_company: targetCompany || null,
        years_of_experience: years === "" ? null : Number(years),
      } as never);
      setUser({
        ...user!,
        full_name: updated.full_name,
        target_role: updated.target_role,
        target_company: updated.target_company,
      });
      setMessage("Profile saved");
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function onChangePassword(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await usersApi.changePassword(currentPassword, newPassword);
      clearTokens();
      setMessage("Password changed. Please sign in again.");
      await logout();
    } catch (err) {
      setError(extractError(err));
    }
  }

  async function onDeleteAccount(event: FormEvent) {
    event.preventDefault();
    if (!window.confirm("Soft-delete your account? This cannot be undone from the UI.")) return;
    setError(null);
    try {
      await usersApi.deleteAccount(deletePassword);
      clearTokens();
      await logout();
    } catch (err) {
      setError(extractError(err));
    }
  }

  if (profileQuery.isLoading) {
    return <p className="text-ink-muted">Loading profile…</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold">Settings</h1>
        <p className="mt-2 text-ink-muted">Manage profile, password, sessions, and account.</p>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}
      {message && <p className="text-sm text-accent">{message}</p>}

      <section className="glass-panel p-6">
        <h2 className="font-display text-xl font-semibold">Profile</h2>
        <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={saveProfile}>
          <label className="block space-y-1 sm:col-span-2">
            <span className="text-sm text-ink-muted">Full name</span>
            <input
              className="field"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-1 sm:col-span-2">
            <span className="text-sm text-ink-muted">Bio</span>
            <textarea
              className="field min-h-24"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm text-ink-muted">Target role</span>
            <select className="field" value={targetRole} onChange={(e) => setTargetRole(e.target.value)}>
              <option value="">Select…</option>
              {TARGET_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-sm text-ink-muted">Target company</span>
            <select
              className="field"
              value={targetCompany}
              onChange={(e) => setTargetCompany(e.target.value)}
            >
              <option value="">Select…</option>
              {TARGET_COMPANIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-sm text-ink-muted">Years of experience</span>
            <input
              className="field"
              type="number"
              min={0}
              max={60}
              value={years}
              onChange={(e) => setYears(e.target.value)}
            />
          </label>
          <div className="sm:col-span-2">
            <button type="submit" className="btn-primary">
              Save profile
            </button>
          </div>
        </form>
        {profileQuery.data && (
          <p className="mt-4 text-xs text-ink-subtle">
            Permissions: {(profileQuery.data.permissions ?? []).join(", ") || "none"}
          </p>
        )}
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-xl font-semibold">Change password</h2>
        <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={onChangePassword}>
          <label className="block space-y-1">
            <span className="text-sm text-ink-muted">Current password</span>
            <input
              className="field"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-1">
            <span className="text-sm text-ink-muted">New password</span>
            <input
              className="field"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </label>
          <div className="sm:col-span-2">
            <button type="submit" className="btn-ghost">
              Update password
            </button>
          </div>
        </form>
      </section>

      <section className="glass-panel p-6">
        <h2 className="font-display text-xl font-semibold">Sessions</h2>
        <div className="mt-4 space-y-3">
          {(sessionsQuery.data ?? []).map((session) => (
            <div
              key={session.id}
              className="flex flex-col gap-2 rounded-xl border border-white/10 p-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="text-sm text-ink-muted">
                <p className="text-ink">{session.ip_address ?? "Unknown IP"}</p>
                <p className="truncate font-mono text-xs">{session.user_agent ?? "—"}</p>
                <p className="text-xs">
                  {session.revoked_at ? "Revoked" : "Active"} · created{" "}
                  {new Date(session.created_at).toLocaleString()}
                </p>
              </div>
              {!session.revoked_at && (
                <button
                  type="button"
                  className="btn-ghost text-sm"
                  onClick={() =>
                    void usersApi.revokeSession(session.id).then(() =>
                      queryClient.invalidateQueries({ queryKey: ["sessions"] }),
                    )
                  }
                >
                  Revoke
                </button>
              )}
            </div>
          ))}
          {!sessionsQuery.data?.length && (
            <p className="text-sm text-ink-muted">No sessions found.</p>
          )}
        </div>
      </section>

      <section className="glass-panel border-danger/30 p-6">
        <h2 className="font-display text-xl font-semibold text-danger">Danger zone</h2>
        <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={onDeleteAccount}>
          <input
            className="field"
            type="password"
            placeholder="Confirm with password"
            value={deletePassword}
            onChange={(e) => setDeletePassword(e.target.value)}
            required
          />
          <button type="submit" className="rounded-xl bg-danger/90 px-5 py-2.5 font-medium text-canvas">
            Delete account
          </button>
        </form>
      </section>
    </div>
  );
}

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as ApiErrorBody | undefined;
    return data?.error?.message ?? err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
