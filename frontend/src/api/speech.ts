import { ApiError, getToken } from "./client";

export type SpeechLanguage = "zh" | "nan";

export interface SpeechTranscription {
  text: string;
  language: SpeechLanguage;
}

export async function transcribeSpeech(audio: Blob, language: SpeechLanguage) {
  const form = new FormData();
  form.append("audio", audio, `speech.${audio.type.includes("webm") ? "webm" : "wav"}`);
  form.append("language", language);

  const token = getToken();
  const res = await fetch("/api/speech/transcribe", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });

  if (!res.ok) {
    let code = "ASR_ERROR";
    let message = `HTTP ${res.status}`;
    let data: Record<string, unknown> = {};
    try {
      const body = await res.json();
      const err = body?.detail?.error ?? body?.error;
      if (err) {
        code = err.code ?? code;
        message = err.message ?? message;
        data = err;
      }
    } catch {
      /* response is not JSON */
    }
    throw new ApiError(code, message, undefined, data);
  }

  return res.json() as Promise<SpeechTranscription>;
}
