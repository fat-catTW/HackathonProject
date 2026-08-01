import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSpeechSynthesis } from "./useSpeechSynthesis";

const originalSpeechSynthesis = window.speechSynthesis;
const originalUtterance = window.SpeechSynthesisUtterance;

describe("useSpeechSynthesis", () => {
  let speakMock: ReturnType<typeof vi.fn>;
  let cancelMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    speakMock = vi.fn();
    cancelMock = vi.fn();
    Object.defineProperty(window, "speechSynthesis", {
      value: { speak: speakMock, cancel: cancelMock, speaking: false },
      writable: true,
      configurable: true,
    });
    const MockUtterance = class {
      text: string;
      lang: string = "";
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(text: string) {
        this.text = text;
      }
    };
    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      value: MockUtterance,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "speechSynthesis", { value: originalSpeechSynthesis, configurable: true });
    Object.defineProperty(window, "SpeechSynthesisUtterance", { value: originalUtterance, configurable: true });
  });

  it("reports supported=true when window.speechSynthesis exists", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    expect(result.current.supported).toBe(true);
  });

  it("calls speechSynthesis.speak with a zh-TW utterance when speak() is called", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => result.current.speak("阿伯早安"));
    expect(speakMock).toHaveBeenCalledTimes(1);
    const utterance = speakMock.mock.calls[0][0];
    expect(utterance.text).toBe("阿伯早安");
    expect(utterance.lang).toBe("zh-TW");
  });

  it("calls speechSynthesis.cancel when stop() is called", () => {
    const { result } = renderHook(() => useSpeechSynthesis());
    act(() => result.current.stop());
    expect(cancelMock).toHaveBeenCalledTimes(1);
  });

  it("reports supported=false when window.speechSynthesis is undefined", () => {
    Object.defineProperty(window, "speechSynthesis", { value: undefined, configurable: true });
    const { result } = renderHook(() => useSpeechSynthesis());
    expect(result.current.supported).toBe(false);
  });
});
