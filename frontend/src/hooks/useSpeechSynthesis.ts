import { useCallback, useEffect, useRef, useState } from "react";

/** 瀏覽器內建語音朗讀（zh-TW），按了才念，不自動播放。不支援時 supported=false。 */
export function useSpeechSynthesis() {
  const [speaking, setSpeaking] = useState(false);
  const [supported, setSupported] = useState(true);
  const currentUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    setSupported(typeof window !== "undefined" && !!window.speechSynthesis);
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  const speak = useCallback((text: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "zh-TW";
    currentUtteranceRef.current = utterance;
    const clearIfCurrent = () => {
      if (currentUtteranceRef.current === utterance) setSpeaking(false);
    };
    utterance.onend = clearIfCurrent;
    utterance.onerror = clearIfCurrent;
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }, []);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  }, []);

  return { speaking, supported, speak, stop };
}
