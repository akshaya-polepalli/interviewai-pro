import { apiClient } from "@/services/api";
import type { Page, Profile, SessionInfo, AdminStats, RoleInfo } from "@/types/users";

export async function fetchProfile(): Promise<Profile> {
  const { data } = await apiClient.get<Profile>("/users/me");
  return data;
}

export async function updateProfile(payload: Partial<Profile>): Promise<Profile> {
  const { data } = await apiClient.patch<Profile>("/users/me", payload);
  return data;
}

export async function changePassword(current_password: string, new_password: string): Promise<void> {
  await apiClient.post("/users/me/change-password", { current_password, new_password });
}

export async function deleteAccount(password: string): Promise<void> {
  await apiClient.delete("/users/me", { data: { password } });
}

export async function listSessions(): Promise<SessionInfo[]> {
  const { data } = await apiClient.get<SessionInfo[]>("/users/me/sessions");
  return data;
}

export async function revokeSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/users/me/sessions/${sessionId}`);
}

export async function fetchAdminStats(): Promise<AdminStats> {
  const { data } = await apiClient.get<AdminStats>("/admin/stats");
  return data;
}

export async function fetchAdminUsers(params: {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  role?: string;
}): Promise<Page<Profile>> {
  const { data } = await apiClient.get<Page<Profile>>("/admin/users", { params });
  return data;
}

export async function updateAdminUser(
  userId: string,
  payload: { status?: string; roles?: string[]; full_name?: string },
): Promise<Profile> {
  const { data } = await apiClient.patch<Profile>(`/admin/users/${userId}`, payload);
  return data;
}

export async function deleteAdminUser(userId: string): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}`);
}

export async function fetchRoles(): Promise<RoleInfo[]> {
  const { data } = await apiClient.get<RoleInfo[]>("/admin/roles");
  return data;
}
