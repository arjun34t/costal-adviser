import { useState, useRef, useCallback } from "react";
import { transcribeAudio } from "../api.js";
import { LABELS } from "../constants.js";
import { useApp } from "../context/AppContext.jsx";

export function useVoice() {
  const { lang, sendMessage, addAgentMessage } = useApp();
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = useCallback(async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const mimeType =
        ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"].find((t) =>
          MediaRecorder.isTypeSupported(t)
        ) || "";

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      const recordedMime = recorder.mimeType || "audio/webm";
      const ext = recordedMime.includes("ogg") ? "ogg" : "webm";

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setIsRecording(false);

        const blob = new Blob(audioChunksRef.current, { type: recordedMime });

        if (blob.size < 100) {
          addAgentMessage("⚠️ No audio captured. Check microphone permissions.");
          return;
        }

        try {
          const json = await transcribeAudio(blob, ext, lang);
          if (json.transcript) {
            sendMessage(json.transcript);
          } else {
            addAgentMessage(LABELS[lang].transcriptionFailed);
          }
        } catch (err) {
          addAgentMessage(`⚠️ ${err.message}`);
        }
      };

      recorder.start(250);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (_) {
      addAgentMessage(LABELS[lang].micDenied);
    }
  }, [lang, sendMessage, addAgentMessage]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  return { isRecording, startRecording, stopRecording };
}
