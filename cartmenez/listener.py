"""Microphone -> text."""

import speech_recognition as sr


class Listener:
    def __init__(self, backend: str = "google", whisper_model: str = "base.en"):
        self.backend = backend
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.mic = sr.Microphone()
        self._whisper = None
        if backend == "whisper":
            from faster_whisper import WhisperModel

            self._whisper = WhisperModel(whisper_model, compute_type="int8")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)

    def listen(self, timeout: float, phrase_limit: float) -> str | None:
        """Return what was said, or None on silence / unintelligible audio."""
        try:
            with self.mic as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return None

        try:
            if self._whisper is not None:
                return self._transcribe_whisper(audio)
            return self.recognizer.recognize_google(audio) or None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[stt] request failed: {e}")
            return None

    def _transcribe_whisper(self, audio: "sr.AudioData") -> str | None:
        import io

        segments, _ = self._whisper.transcribe(io.BytesIO(audio.get_wav_data()), language="en")
        text = " ".join(s.text for s in segments).strip()
        return text or None


class TypedListener:
    """Keyboard stand-in for the mic (--text mode)."""

    def listen(self, timeout: float, phrase_limit: float) -> str | None:
        text = input("you> ").strip()
        return text or None
