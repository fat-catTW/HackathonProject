import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WeatherGreetingCard } from "./WeatherGreetingCard";
import * as weatherApi from "../api/weather";

vi.mock("../api/weather");

const speakMock = vi.fn();
vi.mock("../hooks/useSpeechSynthesis", () => ({
  useSpeechSynthesis: () => ({ speaking: false, supported: true, speak: speakMock, stop: vi.fn() }),
}));

beforeEach(() => {
  speakMock.mockClear();
  vi.mocked(weatherApi.getWeather).mockResolvedValue({
    city: "台中市",
    temperature: 27,
    high: 30,
    low: 22,
    condition: "晴時多雲",
    is_large_temp_swing: true,
    fallback_used: false,
  });
});

describe("WeatherGreetingCard", () => {
  it("shows the city, temperature, and condition once loaded", async () => {
    render(<WeatherGreetingCard userName="添財" />);
    expect(await screen.findByText(/台中市/)).toBeInTheDocument();
    expect(screen.getByText(/晴時多雲/)).toBeInTheDocument();
  });

  it("speaks a greeting including the user's name when the button is tapped", async () => {
    const user = userEvent.setup();
    render(<WeatherGreetingCard userName="添財" />);
    const button = await screen.findByRole("button", { name: /播放語音/ });
    await user.click(button);
    await waitFor(() => expect(speakMock).toHaveBeenCalledTimes(1));
    expect(speakMock.mock.calls[0][0]).toContain("添財");
  });
});
