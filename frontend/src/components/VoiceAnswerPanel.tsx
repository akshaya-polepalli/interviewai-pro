import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Volume2 } from "lucide-react";

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

declare global {
  interface Window {
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    SpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

export function VoiceAnswerPanel({
  questionText,
  initialTranscript,
  disabled,
  busy,
  onSubmit,
}: {
  questionText: string;
  initialTranscript: string;
  disabled: boolean;
  busy: boolean;
  onSubmit: (payload: { transcript: string; audio: Blob | null }) => void;
}) {
  const [transcript, setTranscript] = useState(initialTranscript);
  const [recording, setRecording] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [supported, setSupported] = useState({ mic: false, tts: false, stt: false });
  const [hint, setHint] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    setTranscript(initialTranscript);
    setAudioBlob(null);
  }, [initialTranscript]);

  useEffect(() => {
    setSupported({
      mic: typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia,
      tts: typeof window !== "undefined" && "speechSynthesis" in window,
      stt:
        typeof window !== "undefined" &&
        !!(window.SpeechRecognition || window.webkitSpeechRecognition),
    });
    return () => {
      window.speechSynthesis?.cancel();
      recognitionRef.current?.stop();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const speakQuestion = useCallback(() => {
    if (!supported.tts) {
      setHint("Text-to-speech is not available in this browser.");
      return;
    }
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(questionText);
    utter.rate = 1;
    utter.onstart = () => setSpeaking(true);
    utter.onend = () => setSpeaking(false);
    utter.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utter);
  }, [questionText, supported.tts]);

  function stopRecording(): Promise<Blob | null> {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    const recorder = mediaRecorderRef.current;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setRecording(false);

    if (!recorder || recorder.state === "inactive") {
      return Promise.resolve(audioBlob);
    }

    return new Promise((resolve) => {
      recorder.onstop = () => {
        const type = recorder.mimeType || "audio/webm";
        const blob = chunksRef.current.length
          ? new Blob(chunksRef.current, { type })
          : null;
        setAudioBlob(blob);
        resolve(blob);
      };
      recorder.stop();
    });
  }

  async function startRecording() {
    setHint(null);
    setAudioBlob(null);
    if (!supported.mic) {
      setHint("Microphone access is not available. Type your spoken answer below.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mime = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
          ? "audio/mp4"
          : "";
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start(250);
      setRecording(true);

      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SR) {
        const recognition = new SR();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";
        recognition.onresult = (event) => {
          let text = "";
          for (let i = 0; i < event.results.length; i += 1) {
            text += event.results[i][0]?.transcript ?? "";
          }
          if (text.trim()) setTranscript(text.trim());
        };
        recognition.onerror = () => {
          /* keep recording; user can edit transcript */
        };
        recognitionRef.current = recognition;
        try {
          recognition.start();
        } catch {
          /* already started */
        }
      } else {
        setHint("Live captioning unavailable — record audio and/or type the transcript.");
      }
    } catch {
      setHint("Could not access microphone. Allow mic permission or type your answer.");
    }
  }

  async function handleSubmit() {
    const blob = recording ? await stopRecording() : audioBlob;
    onSubmit({ transcript: transcript.trim(), audio: blob });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="btn-ghost"
          disabled={disabled || speaking}
          onClick={speakQuestion}
        >
          <Volume2 className="h-4 w-4" />
          {speaking ? "Speaking…" : "Speak question"}
        </button>
        {!recording ? (
          <button
            type="button"
            className="btn-primary"
            disabled={disabled || busy}
            onClick={() => void startRecording()}
          >
            <Mic className="h-4 w-4" />
            Start answering
          </button>
        ) : (
          <button type="button" className="btn-ghost" onClick={() => void stopRecording()}>
            <MicOff className="h-4 w-4" />
            Stop recording
          </button>
        )}
      </div>
      {recording && (
        <p className="text-sm text-accent">
          Recording… speak clearly. Live transcript appears below.
        </p>
      )}
      {audioBlob && !recording && (
        <p className="text-sm text-ink-muted">
          Audio captured ({Math.max(1, Math.round(audioBlob.size / 1024))} KB). Edit transcript if
          needed, then save.
        </p>
      )}
      {hint && <p className="text-sm text-ink-muted">{hint}</p>}
      <textarea
        className="field min-h-[180px] resize-y"
        value={transcript}
        onChange={(e) => setTranscript(e.target.value)}
        disabled={disabled}
        placeholder="Your spoken answer transcript (auto-filled when speech recognition is available). Edit before saving."
      />
      {!disabled && (
        <button
          type="button"
          className="btn-primary"
          disabled={busy || (!transcript.trim() && !audioBlob && !recording)}
          onClick={() => void handleSubmit()}
        >
          {busy ? "Saving…" : "Save voice answer"}
        </button>
      )}
    </div>
  );
}
