import { api } from "./client";

export interface CalendarDay {
  date: string;
  items: { request_id: string; service_name: string; status: string; status_label: string }[];
}

export function getCalendar() {
  return api<{ days: CalendarDay[] }>("/api/calendar");
}
