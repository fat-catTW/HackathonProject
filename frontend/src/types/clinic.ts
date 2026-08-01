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

/** AI 管家在聊天室裡回的診所推薦卡片資料（症狀觸發，含地區與症狀原文，
 * 讓使用者選一張卡片後可以直接帶到掛號頁繼續填看診時間／聯絡人）。 */
export interface ClinicChatRecommendation extends SymptomTriageResult {
  city: string;
  district: string;
  symptom_note: string;
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
