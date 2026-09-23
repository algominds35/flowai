"use client";
import { auth, business, setToken, setBusinessId, clearToken, getToken } from "./api";

export async function login(email: string, password: string) {
  const { access_token } = await auth.login(email, password);
  setToken(access_token);
  await loadBusiness();
}

export async function register(email: string, password: string, full_name: string) {
  const { access_token } = await auth.register(email, password, full_name);
  setToken(access_token);
}

export async function loadBusiness() {
  const businesses = await business.list();
  if (businesses.length > 0) {
    setBusinessId(businesses[0].id);
    return businesses[0];
  }
  return null;
}

export async function logout() {
  clearToken();
  window.location.href = "/login";
}

export function isAuthenticated(): boolean {
  return !!getToken();
}
