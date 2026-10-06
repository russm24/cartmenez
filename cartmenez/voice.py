"""Text -> speech, in a bratty cartoon-kid register.

Backends:
  pyttsx3    offline system TTS, pitched up with pydub. Free and instant, sounds
             like a cartoon kid rather than any specific person.
  elevenlabs any ElevenLabs voice you have rights to (e.g. one you designed in
             their Voice Design tool from a text description).
  print      no audio, just prints (for testing).
"""

import io
import os
import tempfile

import requests
from pydub import AudioSegment
from pydub.playback import play

from .config import Config


def pitch_shift(seg: AudioSegment, semitones: float) -> AudioSegment:
    """Resample-style shift: raises pitch and tempo together (cartoon effect)."""
    if not semitones:
        return seg
    new_rate = int(seg.frame_rate * (2.0 ** (semitones / 12.0)))
    shifted = seg._spawn(seg.raw_data, overrides={"frame_rate": new_rate})
    return shifted.set_frame_rate(seg.frame_rate)


class Voice:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.backend = cfg.tts_backend
        if self.backend == "pyttsx3":
            import pyttsx3

            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", cfg.tts_rate)
        elif self.backend == "elevenlabs":
            if not (cfg.elevenlabs_api_key and cfg.elevenlabs_voice_id):
                raise ValueError("TTS_BACKEND=elevenlabs needs ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID")

    def say(self, text: str) -> None:
        print(f"cartman> {text}")
        if not text or self.backend == "print":
            return
        if self.backend == "elevenlabs":
            play(self._elevenlabs(text))
        else:
            play(pitch_shift(self._pyttsx3(text), self.cfg.tts_pitch_semitones))

    def _pyttsx3(self, text: str) -> AudioSegment:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            self.engine.save_to_file(text, path)
            self.engine.runAndWait()
            return AudioSegment.from_file(path)
        finally:
            os.remove(path)

    def _elevenlabs(self, text: str) -> AudioSegment:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{self.cfg.elevenlabs_voice_id}",
            headers={"xi-api-key": self.cfg.elevenlabs_api_key, "accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": self.cfg.elevenlabs_model,
                "voice_settings": {"stability": 0.35, "similarity_boost": 0.8, "style": 0.6},
            },
            timeout=30,
        )
        r.raise_for_status()
        return AudioSegment.from_file(io.BytesIO(r.content), format="mp3")
