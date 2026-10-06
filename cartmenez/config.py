import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Config:
    model: str = field(default_factory=lambda: _env("CLAUDE_MODEL", "claude-opus-5-5"))
    effort: str = field(default_factory=lambda: _env("CLAUDE_EFFORT", "low"))

    camera_index: int = field(default_factory=lambda: int(_env("CAMERA_INDEX", "0")))
    arrive_frames: int = field(default_factory=lambda: int(_env("ARRIVE_FRAMES", "5")))
    leave_seconds: float = field(default_factory=lambda: float(_env("LEAVE_SECONDS", "4")))
    cooldown_seconds: float = field(default_factory=lambda: float(_env("COOLDOWN_SECONDS", "8")))

    stt_backend: str = field(default_factory=lambda: _env("STT_BACKEND", "google"))
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL", "base.en"))
    listen_timeout: float = field(default_factory=lambda: float(_env("LISTEN_TIMEOUT", "6")))
    phrase_limit: float = field(default_factory=lambda: float(_env("PHRASE_LIMIT", "12")))

    tts_backend: str = field(default_factory=lambda: _env("TTS_BACKEND", "pyttsx3"))
    tts_pitch_semitones: float = field(default_factory=lambda: float(_env("TTS_PITCH_SEMITONES", "4")))
    tts_rate: int = field(default_factory=lambda: int(_env("TTS_RATE", "185")))
    elevenlabs_api_key: str = field(default_factory=lambda: _env("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = field(default_factory=lambda: _env("ELEVENLABS_VOICE_ID", ""))
    elevenlabs_model: str = field(default_factory=lambda: _env("ELEVENLABS_MODEL", "eleven_turbo_v2_5"))

    sounds_dir: str = field(default_factory=lambda: _env("SOUNDS_DIR", "sounds"))
    max_turns: int = field(default_factory=lambda: int(_env("MAX_TURNS", "8")))
