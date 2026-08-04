/** In-memory access token + localStorage refresh token helpers. */

const REFRESH_KEY = "iap_refresh_token";

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function storeTokens(access: string, refresh: string): void {
  setAccessToken(access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  setAccessToken(null);
  localStorage.removeItem(REFRESH_KEY);
}
