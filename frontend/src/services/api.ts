import type { ApiResponse } from "../types";

const TOKEN_KEY = "sdlc_nexus_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "demo-token";
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...(init.headers || {}),
    },
  });
  const payload = (await response.json()) as ApiResponse<T>;
  if (!payload.success) {
    throw new Error(payload.error?.message || "Request failed");
  }
  return payload.data;
}
