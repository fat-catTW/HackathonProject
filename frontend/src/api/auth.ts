import { api } from "./client";

export interface DemoAccount {
  token: string;
  name: string;
}

export function fetchDemoAccounts() {
  return api<{ accounts: DemoAccount[] }>("/api/auth/demo-accounts");
}

export function fetchMe() {
  return api<{ sub: string; name: string }>("/api/auth/me");
}
