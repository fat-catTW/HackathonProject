import type { WeatherInfo } from "../types/weather";
import { api } from "./client";

export function getWeather(city?: string): Promise<WeatherInfo> {
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  return api<WeatherInfo>(`/api/weather${query}`);
}
