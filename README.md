# cartmenez

A prototype webcam greeter. A laptop camera watches for people. When someone walks
up, Claude greets them **in character as Eric Cartman** and chats with them through
the laptop mic and speakers, dropping in sound bytes when a joke calls for one.

```
 webcam ──► OpenCV (face + body) ──► presence: arrived / left
                                            │
 mic ──► speech-to-text ──► Claude (Cartman persona, JSON reply) ──► TTS ──► speaker
                                            └──► sound byte from sounds/
```

| Module | What it does |
|---|---|
| `cartmenez/detector.py` | Haar face cascade + HOG body detector, with a debounce so one noisy frame doesn't trigger a greeting |
| `cartmenez/listener.py` | Mic to text through `SpeechRecognition` (Google, free) or `faster-whisper` (offline) |
| `cartmenez/brain.py` | Claude persona prompt; returns `{say, sound, sound_timing, end_conversation}` through structured outputs |
| `cartmenez/voice.py` | TTS: pitched-up `pyttsx3` (offline), any ElevenLabs voice, or print-only |
| `cartmenez/sounds.py` | Lists clips in `sounds/` so Claude can pick one by name |
| `cartmenez/main.py` | Camera loop on the main thread; conversation loop on a worker thread |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt     # macOS: brew install portaudio ffmpeg first
cp .env.example .env                # add ANTHROPIC_API_KEY
```

On Linux, also install `portaudio19-dev`, `ffmpeg` and `espeak-ng` for pyttsx3.

## Run

```bash
python -m cartmenez.main --preview          # full thing, with a camera window (q to quit)
python -m cartmenez.main --no-camera        # press Enter to fake someone arriving or leaving
python -m cartmenez.main --no-camera --text --mute   # test the persona by typing, no audio
```

## The voice

The character comes from the **persona prompt** in `brain.py`, which sets Cartman's
attitude, schemes and catchphrases. The **sound** of the voice comes from the TTS
backend:

- `TTS_BACKEND=pyttsx3` (default): your system's TTS voice pitched up
  `TTS_PITCH_SEMITONES` (default 4) so it sounds like a bratty cartoon kid. It's free,
  works offline and adds no latency.
- `TTS_BACKEND=elevenlabs`: set `ELEVENLABS_VOICE_ID` to a voice you have the rights
  to. The easy route is ElevenLabs **Voice Design**: describe "a whiny, nasal,
  self-important 10-year-old cartoon boy" and save the result.

I didn't include a clone of the real Cartman voice. That would mean training on
Trey Parker's recorded performance, which needs permission from him and the show.
If you get that permission, the ElevenLabs backend will work with that voice ID
unchanged.

## Sound bytes

Put `.wav`, `.mp3` or `.ogg` files in `sounds/`. Claude sees each file's name, plus an
optional description from `sounds/sounds.json` (see `sounds.example.json`), and can
play one before or after its line. Pre-recorded voice messages work the same way. The
folder is git-ignored, so clips never get committed.

## Tuning

Everything is set through environment variables in `.env.example`:

- `ARRIVE_FRAMES`, `LEAVE_SECONDS`, `COOLDOWN_SECONDS`: how sensitive detection is
- `CLAUDE_EFFORT`: `low` (default) gives the fastest replies; raise it for sharper banter
- `MAX_TURNS`: how many exchanges before Cartman ends the conversation

The prompt keeps the character PG-13 and tells it to roast what people say, never who
they are, because this runs in front of strangers.
