export interface ClinicInfo {
  id: string;
  name: string;
  specialties: string[];
  address: string;
  phone: string;
  is_open_now: boolean;
}

export interface SymptomTriageResult {
  specialty: string;
  advisory: string;
  clinics: ClinicInfo[];
  recommended_clinic_id: string | null;
  recommend_reason: string | null;
}

export interface ClinicAppointmentPayload {
  clinic_id: string;
  appointment_date: string; // YYYY-MM-DD
  appointment_time: string; // HH:MM
  symptom_note: string;
  contact_name: string;
  phone: string;
}

export interface ClinicAppointmentResult {
  success: boolean;
  request_id: string;
  status: string;
}

export interface ClinicAppointmentOrder {
  request_id: string;
  status: string;
  order_items: {
    clinic_id: string;
    clinic_name: string;
    clinic_address: string;
    clinic_phone: string;
    appointment_date: string;
    appointment_time: string;
  };
}
