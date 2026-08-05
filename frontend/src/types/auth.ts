export type UserPublic = {
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
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserPublic;
};

export type MessageResponse = {
  message: string;
  detail?: string | null;
  debug_token?: string | null;
};

export type ApiErrorBody = {
  message?: string;
  detail?: string;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};
