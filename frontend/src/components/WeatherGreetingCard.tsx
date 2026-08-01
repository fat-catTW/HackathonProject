import { useEffect, useState } from "react";
import { getWeather } from "../api/weather";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";
import type { WeatherInfo } from "../types/weather";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  userName: string;
}

export function WeatherGreetingCard({ userName }: Props) {
  const [weather, setWeather] = useState<WeatherInfo | null>(null);
  const { speaking, supported, speak, stop } = useSpeechSynthesis();

  useEffect(() => {
    getWeather()
      .then(setWeather)
      .catch(() => setWeather(null));
  }, []);

  if (!weather) return null;

  const greeting = `${userName}早安，今天${weather.city}${weather.condition}，氣溫約${Math.round(
    weather.temperature,
  )}度。${weather.is_large_temp_swing ? "早晚溫差大，要記得多穿一件外套喔！" : "祝你今天有個好心情！"}`;

  return (
    <section className="mt-6 rounded-[22px] bg-[var(--color-surface)] p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-info-soft)] text-[var(--color-info)]">
            <ServiceIcon type="sun" size={22} />
          </span>
          <div>
            <p className="text-sm font-extrabold text-[var(--color-foreground)]">
              {weather.city} · {weather.condition}
            </p>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              {Math.round(weather.temperature)}°（{Math.round(weather.low)}°–{Math.round(weather.high)}°）
            </p>
          </div>
        </div>
        {supported && (
          <button
            type="button"
            onClick={() => (speaking ? stop() : speak(greeting))}
            className="flex min-h-[44px] items-center gap-1.5 rounded-full bg-brand px-4 text-sm font-bold text-[var(--color-on-primary)]"
          >
            <ServiceIcon type="chat" size={16} />
            {speaking ? "停止" : "播放語音"}
          </button>
        )}
      </div>
    </section>
  );
}
