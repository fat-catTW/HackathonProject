// 最小 Web Speech API 型別（避免額外安裝 @types/dom-speech-recognition）
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}
interface SpeechRecognition extends EventTarget {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((ev: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((ev: Event) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
declare const SpeechRecognition: { new (): SpeechRecognition };
