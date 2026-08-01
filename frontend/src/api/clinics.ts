import type {
  ClinicAppointmentOrder,
  ClinicAppointmentPayload,
  ClinicAppointmentResult,
  ClinicInfo,
  SymptomTriageResult,
} from "../types/clinic";
import { api } from "./client";

export function listClinics(city: string, district: string, specialty?: string) {
  const params = new URLSearchParams({ city, district });
  if (specialty) params.set("specialty", specialty);
  return api<{ clinics: ClinicInfo[] }>(`/api/clinics?${params.toString()}`).then((r) => r.clinics);
}

export function triageSymptom(symptomText: string, city: string, district: string) {
  return api<SymptomTriageResult>("/api/symptom-triage", {
    method: "POST",
    body: JSON.stringify({ symptom_text: symptomText, city, district }),
  });
}

export function submitClinicAppointment(payload: ClinicAppointmentPayload) {
  return api<ClinicAppointmentResult>("/api/clinic-appointments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getClinicAppointment(requestId: string) {
  return api<ClinicAppointmentOrder>(`/api/clinic-appointments/${encodeURIComponent(requestId)}`);
}
