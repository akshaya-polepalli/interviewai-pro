export type Profile = {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  is_email_verified: boolean;
  status: string;
  target_role: string | null;
  target_company: string | null;
  roles: string[];
  created_at: string;
  bio?: string | null;
  years_of_experience?: number | null;
  permissions?: string[];
  last_login_at?: string | null;
  is_deleted?: boolean;
};

export type SessionInfo = {
  id: string;
  user_agent: string | null;
  ip_address: string | null;
  device_label: string | null;
  expires_at: string;
  revoked_at: string | null;
  last_seen_at: string | null;
  created_at: string;
};

export type AdminStats = {
  total_users: number;
  active_users: number;
  pending_verification: number;
  suspended_users: number;
  deleted_users: number;
  verified_users: number;
  total_interviews: number;
  total_submissions: number;
  total_resumes: number;
  users_by_role: Record<string, number>;
  recent_registrations_7d: number;
};

export type RoleInfo = {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: string[];
};

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};
