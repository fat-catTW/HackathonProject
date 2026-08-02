import { api } from "./client";

/** 卡片上的一則提醒；kind 決定它用什麼顏色與圖示呈現。 */
export interface GreetingItem {
  id: string;
  kind: "today" | "upcoming" | "action_needed" | "in_progress" | "followup";
  service_id: string;
  title: string;
  detail: string;
  action_label: string;
  action_path: string;
}

/** 一句可以直接丟給管家的開場白。 */
export interface GreetingSuggestion {
  service_id: string;
  label: string;
  prompt: string;
}

export interface DailyGreeting {
  date: string;
  weekday: string;
  date_label: string;
  /** 卡片對外宣稱的推播時間（目前固定 07:00）。 */
  push_time: string;
  period: "morning" | "afternoon" | "evening" | "night";
  greeting: string;
  headline: string;
  message: string;
  items: GreetingItem[];
  suggestions: GreetingSuggestion[];
}

/** 取得今天的問候卡。日期以使用者裝置為準，裝置時區不同時「今天的行程」才不會錯。 */
export function fetchDailyGreeting(clientDate: string) {
  return api<DailyGreeting>(`/api/daily-greeting?client_date=${encodeURIComponent(clientDate)}`);
}
