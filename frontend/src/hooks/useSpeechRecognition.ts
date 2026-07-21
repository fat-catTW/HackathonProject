import { useCallback, useEffect, useRef, useState } from "react";

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "麥克風權限被拒，請於瀏覽器設定允許存取後再試一次。",
  "service-not-allowed": "麥克風權限被拒，請於瀏覽器設定允許存取後再試一次。",
  "no-speech": "沒有偵測到語音，請再說一次。",
  "audio-capture": "偵測不到麥克風，請確認裝置已連接。",
  network: "語音服務連線失敗，請檢查網路後再試一次。",
  aborted: "語音輸入已取消。",
};

/** Web Speech API 語音轉文字（zh-TW），不支援時回報 supported=false 供文字輸入備援。 */
export function useSpeechRecognition(onResult: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  useEffect(() => {
    const Ctor: typeof SpeechRecognition | undefined =
      (window as unknown as { SpeechRecognition?: typeof SpeechRecognition })
        .SpeechRecognition ??
      (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition })
        .webkitSpeechRecognition;
    if (!Ctor) {
      setSupported(false);
      return;
    }
    const rec = new Ctor();
    rec.lang = "zh-TW";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const text = e.results[0]?.[0]?.transcript?.trim();
      if (text) onResultRef.current(text);
    };
    rec.onend = () => setListening(false);
    rec.onerror = (e) => {
      setListening(false);
      setError(ERROR_MESSAGES[e.error] ?? "語音辨識發生錯誤，請再試一次或改用文字輸入。");
    };
    recognitionRef.current = rec;
    return () => rec.abort();
  }, []);

  const start = useCallback(() => {
    if (!recognitionRef.current || listening) return;
    setError(null);
    try {
      recognitionRef.current.start();
      setListening(true);
    } catch {
      setListening(false);
      setError("無法啟動語音輸入，請再試一次或改用文字輸入。");
    }
  }, [listening]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return { listening, supported, error, start, stop };
}
