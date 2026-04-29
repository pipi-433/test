import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type SpeakOptions = {
  maxChars?: number;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (message: string) => void;
};

function speechSupported() {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

function normalizeSpeechText(value: string, maxChars: number) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > maxChars ? `${normalized.slice(0, maxChars)}。后面的内容我先显示在页面里，方便你继续查看。` : normalized;
}

export function useSpeechSynthesis() {
  const [supported, setSupported] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [error, setError] = useState("");
  const suppressCancelErrorRef = useRef(false);

  useEffect(() => {
    if (!speechSupported()) {
      setSupported(false);
      return undefined;
    }
    setSupported(true);
    const loadVoices = () => setVoices(window.speechSynthesis.getVoices());
    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);
    return () => {
      suppressCancelErrorRef.current = true;
      window.speechSynthesis.cancel();
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
    };
  }, []);

  const preferredVoice = useMemo(() => {
    return (
      voices.find((voice) => voice.lang.toLowerCase() === "zh-cn") ||
      voices.find((voice) => voice.lang.toLowerCase().startsWith("zh")) ||
      voices[0] ||
      null
    );
  }, [voices]);

  const stop = useCallback(() => {
    if (!speechSupported()) {
      return;
    }
    suppressCancelErrorRef.current = true;
    window.speechSynthesis.cancel();
    setSpeaking(false);
    window.setTimeout(() => {
      suppressCancelErrorRef.current = false;
    }, 0);
  }, []);

  const speak = useCallback(
    (text: string, options: SpeakOptions = {}) => {
      const maxChars = options.maxChars ?? 420;
      if (!speechSupported()) {
        const message = "当前浏览器不支持语音播报，请继续使用文本讲解。";
        setError(message);
        setSpeaking(false);
        options.onError?.(message);
        return false;
      }
      const speechText = normalizeSpeechText(text, maxChars);
      if (!speechText) {
        return false;
      }
      suppressCancelErrorRef.current = true;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(speechText);
      utterance.lang = preferredVoice?.lang || "zh-CN";
      utterance.voice = preferredVoice;
      utterance.rate = 0.95;
      utterance.pitch = 1;
      utterance.onstart = () => {
        suppressCancelErrorRef.current = false;
        setError("");
        setSpeaking(true);
        options.onStart?.();
      };
      utterance.onend = () => {
        setSpeaking(false);
        options.onEnd?.();
      };
      utterance.onerror = (event) => {
        const expectedCancel = event.error === "canceled" || event.error === "interrupted";
        if (suppressCancelErrorRef.current || expectedCancel) {
          suppressCancelErrorRef.current = false;
          setSpeaking(false);
          return;
        }
        const message = "语音播报被浏览器中断，文本内容仍可继续查看。";
        setError(message);
        setSpeaking(false);
        options.onError?.(message);
      };
      window.speechSynthesis.speak(utterance);
      return true;
    },
    [preferredVoice],
  );

  return {
    error,
    preferredVoice,
    speak,
    speaking,
    stop,
    supported,
  };
}
