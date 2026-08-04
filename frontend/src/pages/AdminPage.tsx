import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as usersApi from "@/services/users";

export function AdminPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [role, setRole] = useState("");
  const [page, setPage] = useState(1);

  const statsQuery = useQuery({
    queryKey: ["admin-stats"],
    queryFn: usersApi.fetchAdminStats,
  });

  const usersQuery = useQuery({
    queryKey: ["admin-users", page, search, status, role],
    queryFn: () =>
      usersApi.fetchAdminUsers({
        page,
        page_size: 10,
        search: search || undefined,
        status: status || undefined,
        role: role || undefined,
      }),
  });

  const rolesQuery = useQuery({
    queryKey: ["admin-roles"],
    queryFn: usersApi.fetchRoles,
  });

  const updateMutation = useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: string;
      payload: { status?: string; roles?: string[] };
    }) => usersApi.updateAdminUser(userId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => usersApi.deleteAdminUser(userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
    },
  });

  const stats = statsQuery.data;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold">Admin dashboard</h1>
        <p className="mt-2 text-ink-muted">Platform stats, roles, and user management.</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total users" value={stats?.total_users} />
        <StatCard label="Active" value={stats?.active_users} />
        <StatCard label="Pending verify" value={stats?.pending_verification} />
        <StatCard label="New (7d)" value={stats?.recent_registrations_7d} />
        <StatCard label="Interviews" value={stats?.total_interviews} />
        <StatCard label="Submissions" value={stats?.total_submissions} />
        <StatCard label="Resumes" value={stats?.total_resumes} />
        <StatCard label="Suspended" value={stats?.suspended_users} />
      </section>

      {stats && (
        <section className="glass-panel p-6">
          <h2 className="font-display text-lg font-semibold">Users by role</h2>
          <div className="mt-3 flex flex-wrap gap-3">
            {Object.entries(stats.users_by_role).map(([name, count]) => (
              <span
                key={name}
                className="rounded-xl border border-white/10 px-3 py-1.5 text-sm text-ink-muted"
              >
                {name}: <span className="text-ink">{count}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      <section className="glass-panel p-6">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-display text-lg font-semibold">Users</h2>
          <div className="flex flex-wrap gap-2">
            <input
              className="field"
              placeholder="Search email or name"
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
            />
            <select
              className="field"
              value={status}
              onChange={(e) => {
                setPage(1);
                setStatus(e.target.value);
              }}
            >
              <option value="">All statuses</option>
              <option value="active">active</option>
              <option value="pending_verification">pending_verification</option>
              <option value="suspended">suspended</option>
              <option value="inactive">inactive</option>
            </select>
            <select
              className="field"
              value={role}
              onChange={(e) => {
                setPage(1);
                setRole(e.target.value);
              }}
            >
              <option value="">All roles</option>
              {(rolesQuery.data ?? []).map((r) => (
                <option key={r.id} value={r.name}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-ink-muted">
              <tr>
                <th className="pb-3 font-medium">User</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Roles</th>
                <th className="pb-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(usersQuery.data?.items ?? []).map((u) => (
                <tr key={u.id} className="border-t border-white/10">
                  <td className="py-3">
                    <p className="text-ink">{u.full_name}</p>
                    <p className="text-xs text-ink-muted">{u.email}</p>
                  </td>
                  <td className="py-3 text-ink-muted">{u.status}</td>
                  <td className="py-3 text-ink-muted">{u.roles.join(", ")}</td>
                  <td className="py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="btn-ghost px-3 py-1.5 text-xs"
                        onClick={() =>
                          updateMutation.mutate({
                            userId: u.id,
                            payload: {
                              status: u.status === "suspended" ? "active" : "suspended",
                            },
                          })
                        }
                      >
                        {u.status === "suspended" ? "Unsuspend" : "Suspend"}
                      </button>
                      {!u.roles.includes("admin") && (
                        <button
                          type="button"
                          className="btn-ghost px-3 py-1.5 text-xs"
                          onClick={() =>
                            updateMutation.mutate({
                              userId: u.id,
                              payload: { roles: [...new Set([...u.roles, "admin"])] },
                            })
                          }
                        >
                          Make admin
                        </button>
                      )}
                      <button
                        type="button"
                        className="rounded-xl border border-danger/40 px-3 py-1.5 text-xs text-danger"
                        onClick={() => {
                          if (window.confirm(`Delete ${u.email}?`)) {
                            deleteMutation.mutate(u.id);
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-ink-muted">
          <span>
            Page {usersQuery.data?.page ?? page} / {usersQuery.data?.pages ?? 1} ·{" "}
            {usersQuery.data?.total ?? 0} users
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              className="btn-ghost px-3 py-1.5 text-xs"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Prev
            </button>
            <button
              type="button"
              className="btn-ghost px-3 py-1.5 text-xs"
              disabled={page >= (usersQuery.data?.pages ?? 1)}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value?: number }) {
  return (
    <article className="glass-panel p-4">
      <p className="text-xs uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="mt-2 font-display text-2xl font-semibold text-ink">
        {value == null ? "—" : value}
      </p>
    </article>
  );
}
