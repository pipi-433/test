import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

type SpeechRecognitionResultLike = {
  readonly isFinal: boolean;
  readonly [index: number]: { readonly transcript: string };
};

type SpeechRecognitionEventLike = Event & {
  readonly resultIndex: number;
  readonly results: {
    readonly length: number;
    readonly [index: number]: SpeechRecognitionResultLike;
  };
};

type SpeechRecognitionErrorEventLike = Event & {
  readonly error?: string;
  readonly message?: string;
};

type SpeechRecognitionInstance = EventTarget & {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onstart: (() => void) | null;
  abort: () => void;
  start: () => void;
  stop: () => void;
};

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

type RecognitionOptions = {
  onResult?: (text: string) => void;
  onError?: (message: string) => void;
  onStart?: () => void;
  onEnd?: () => void;
};

function recognitionConstructor() {
  if (typeof window === "undefined") {
    return undefined;
  }
  return window.SpeechRecognition || window.webkitSpeechRecognition;
}

export function useSpeechRecognition() {
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");
  const [transcript, setTranscript] = useState("");

  useEffect(() => {
    setSupported(Boolean(recognitionConstructor()));
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  const startListening = useCallback((options: RecognitionOptions = {}) => {
    const Recognition = recognitionConstructor();
    if (!Recognition) {
      const message = "当前浏览器不支持语音输入，请使用文本提问。";
      setError(message);
      setListening(false);
      options.onError?.(message);
      return false;
    }
    recognitionRef.current?.abort();
    const recognition = new Recognition();
    let failed = false;
    recognitionRef.current = recognition;
    recognition.lang = "zh-CN";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      setError("");
      setTranscript("");
      setListening(true);
      options.onStart?.();
    };
    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result[0]?.transcript || "";
        if (result.isFinal) {
          finalText += text;
        } else {
          interimText += text;
        }
      }
      const nextText = (finalText || interimText).trim();
      if (nextText) {
        setTranscript(nextText);
        if (finalText) {
          options.onResult?.(finalText.trim());
        }
      }
    };
    recognition.onerror = (event) => {
      failed = true;
      const message = event.error === "not-allowed" ? "浏览器没有麦克风权限，请改用文本提问。" : "语音识别暂不可用，请使用文本提问。";
      setError(message);
      setListening(false);
      options.onError?.(message);
    };
    recognition.onend = () => {
      setListening(false);
      if (!failed) {
        options.onEnd?.();
      }
    };
    try {
      recognition.start();
      return true;
    } catch {
      const message = "语音识别启动失败，请使用文本提问。";
      setError(message);
      setListening(false);
      options.onError?.(message);
      return false;
    }
  }, []);

  return {
    error,
    listening,
    startListening,
    stopListening,
    supported,
    transcript,
  };
}
