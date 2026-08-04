import { apiClient } from "@/services/api";
import {
  clearTokens,
  getStoredRefreshToken,
  storeTokens,
} from "@/services/tokenStorage";
import type { MessageResponse, TokenResponse, UserPublic } from "@/types/auth";

export {
  clearTokens,
  getStoredRefreshToken,
  storeTokens,
} from "@/services/tokenStorage";

export async function registerAccount(input: {
  email: string;
  full_name: string;
  password: string;
}): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>("/auth/register", input);
  return data;
}

export async function login(input: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", input);
  storeTokens(data.access_token, data.refresh_token);
  return data;
}

export async function refreshSession(): Promise<TokenResponse | null> {
  const refresh = getStoredRefreshToken();
  if (!refresh) return null;
  const { data } = await apiClient.post<TokenResponse>("/auth/refresh", {
    refresh_token: refresh,
  });
  storeTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout(everywhere = false): Promise<void> {
  const refresh = getStoredRefreshToken();
  try {
    await apiClient.post("/auth/logout", {
      refresh_token: refresh,
      everywhere,
    });
  } finally {
    clearTokens();
  }
}

export async function fetchMe(): Promise<UserPublic> {
  const { data } = await apiClient.get<UserPublic>("/auth/me");
  return data;
}

export async function verifyEmail(token: string): Promise<UserPublic> {
  const { data } = await apiClient.post<UserPublic>("/auth/verify-email", { token });
  return data;
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(token: string, new_password: string): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>("/auth/reset-password", {
    token,
    new_password,
  });
  return data;
}
