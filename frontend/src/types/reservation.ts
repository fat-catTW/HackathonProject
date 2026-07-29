export interface RestaurantInfo {
  id: string;
  name: string;
  brand: string;
  address: string;
  phone: string;
  cuisine: string;
  supports_booking_api: boolean;
}

export type TimeSlot = "LUNCH" | "DINNER";

export interface ReservationPayload {
  restaurant_id: string;
  reserved_date: string; // YYYY-MM-DD
  time_slot: TimeSlot;
  specific_time?: string | null; // HH:MM
  people: number;
  contact_name: string;
  phone: string;
  is_premium: boolean;
  preference_note?: string | null;
}

export interface ReservationSubmitResult {
  success: boolean;
  request_id: string;
  status: string;
  order_status: string;
  booking_url: string | null;
}

export interface ReservationOrder {
  request_id: string;
  status: string;
  order_status: string;
  order_items: {
    restaurant_id: string;
    restaurant_name: string;
    restaurant_phone: string;
    restaurant_address: string;
    people: number;
    is_premium: boolean;
    reserved_date: string;
    time_slot: TimeSlot;
    specific_time: string | null;
    contact_name: string;
    phone: string;
    preference_note: string | null;
  };
  vendor_data: { booking_id?: string; share_reservation_url?: string; confirmed_at?: string };
}
