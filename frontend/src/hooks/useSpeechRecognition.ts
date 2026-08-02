import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeSpeech, type SpeechLanguage } from "../api/speech";

type RecognitionConstructor = {
  new (): SpeechRecognition;
};

type AudioContextConstructor = typeof AudioContext;

function getSpeechRecognitionConstructor(): RecognitionConstructor | undefined {
  return (
    (window as unknown as { SpeechRecognition?: RecognitionConstructor }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: RecognitionConstructor }).webkitSpeechRecognition
  );
}

function getAudioContextConstructor(): AudioContextConstructor | undefined {
  return (
    window.AudioContext ??
    (window as unknown as { webkitAudioContext?: AudioContextConstructor }).webkitAudioContext
  );
}

function resampleAudio(samples: Float32Array, fromSampleRate: number, toSampleRate: number) {
  if (fromSampleRate === toSampleRate) return samples;
  const ratio = fromSampleRate / toSampleRate;
  const length = Math.round(samples.length / ratio);
  const result = new Float32Array(length);
  for (let i = 0; i < length; i += 1) {
    const sourceIndex = i * ratio;
    const before = Math.floor(sourceIndex);
    const after = Math.min(before + 1, samples.length - 1);
    const weight = sourceIndex - before;
    result[i] = samples[before] * (1 - weight) + samples[after] * weight;
  }
  return result;
}

function encodeWav(chunks: Float32Array[], sampleRate: number) {
  const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const rawSamples = new Float32Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    rawSamples.set(chunk, offset);
    offset += chunk.length;
  }

  const outputSampleRate = 16000;
  const samples = resampleAudio(rawSamples, sampleRate, outputSampleRate);
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (at: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) view.setUint8(at + i, value.charCodeAt(i));
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, outputSampleRate, true);
  view.setUint32(28, outputSampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let dataOffset = 44;
  for (const sample of samples) {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(dataOffset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    dataOffset += 2;
  }
  return new Blob([view], { type: "audio/wav" });
}

export function useSpeechRecognition(
  onResult: (text: string) => void,
  language: SpeechLanguage = "zh",
) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);
  const onResultRef = useRef(onResult);
  const languageRef = useRef(language);

  onResultRef.current = onResult;
  languageRef.current = language;

  const cleanupAudio = useCallback(() => {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    void audioContextRef.current?.close();
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    audioContextRef.current = null;
  }, []);

  useEffect(() => {
    const supportsWebSpeech = Boolean(getSpeechRecognitionConstructor());
    const supportsRecording =
      typeof navigator.mediaDevices?.getUserMedia === "function" && Boolean(getAudioContextConstructor());
    setSupported(language === "zh" ? supportsWebSpeech : supportsRecording);
  }, [language]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      cleanupAudio();
    };
  }, [cleanupAudio]);

  const startWebSpeech = useCallback(() => {
    const Ctor = getSpeechRecognitionConstructor();
    if (!Ctor || listening) return;

    setError(null);
    const recognition = new Ctor();
    recognition.lang = "zh-TW";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const text = event.results[0]?.[0]?.transcript?.trim();
      if (text) onResultRef.current(text);
    };
    recognition.onerror = () => {
      setListening(false);
      setError("中文語音辨識失敗，請再試一次。");
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [listening]);

  const startTaiwaneseAsr = useCallback(async () => {
    const AudioContextCtor = getAudioContextConstructor();
    if (!AudioContextCtor || listening || transcribing || !supported) return;

    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContextCtor();
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      chunksRef.current = [];

      processor.onaudioprocess = (event) => {
        chunksRef.current.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };
      source.connect(processor);
      processor.connect(audioContext.destination);

      streamRef.current = stream;
      audioContextRef.current = audioContext;
      sourceRef.current = source;
      processorRef.current = processor;
      setListening(true);
    } catch (err) {
      cleanupAudio();
      setListening(false);
      setError(err instanceof Error ? err.message : "無法啟動麥克風。");
    }
  }, [cleanupAudio, listening, supported, transcribing]);

  const start = useCallback(() => {
    if (languageRef.current === "zh") {
      startWebSpeech();
      return;
    }
    void startTaiwaneseAsr();
  }, [startTaiwaneseAsr, startWebSpeech]);

  const stop = useCallback(() => {
    if (languageRef.current === "zh") {
      recognitionRef.current?.stop();
      return;
    }

    const audioContext = audioContextRef.current;
    const chunks = chunksRef.current;
    cleanupAudio();
    setListening(false);
    if (!audioContext || chunks.length === 0) return;

    const audio = encodeWav(chunks, audioContext.sampleRate);
    setTranscribing(true);
    transcribeSpeech(audio, "nan")
      .then((result) => {
        const text = result.text.trim();
        if (text) onResultRef.current(text);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "台語語音辨識失敗，請再試一次。");
      })
      .finally(() => setTranscribing(false));
  }, [cleanupAudio]);

  return { listening, supported, transcribing, error, start, stop };
}
