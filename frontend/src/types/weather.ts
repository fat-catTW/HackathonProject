export interface WeatherInfo {
  city: string;
  temperature: number;
  high: number;
  low: number;
  condition: string;
  is_large_temp_swing: boolean;
  fallback_used: boolean;
}
