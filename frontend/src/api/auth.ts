import { api } from "./client";

export interface DemoAccount {
  token: string;
  name: string;
}

export interface AuthResult {
  token: string;
  sub: string;
  name: string;
}

export function registerAccount(email: string, password: string, name: string) {
  return api<AuthResult>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export function loginWithEmail(email: string, password: string) {
  return api<AuthResult>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function fetchDemoAccounts() {
  return api<{ accounts: DemoAccount[] }>("/api/auth/demo-accounts");
}

export function fetchMe() {
  return api<{ sub: string; name: string }>("/api/auth/me");
}
