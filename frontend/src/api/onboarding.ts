import { api } from "./client";

export interface OnboardingStatus {
  completed: boolean;
  version: number;
}

export function fetchOnboardingStatus() {
  return api<OnboardingStatus>("/api/onboarding/status");
}

export function completeOnboarding(version: number) {
  return api<{ success: boolean; completed: boolean; version: number }>(
    "/api/onboarding/complete",
    {
      method: "POST",
      body: JSON.stringify({ version }),
    },
  );
}
