"""Library of sound bytes / pre-recorded voice messages in the sounds/ folder."""

import json
from pathlib import Path

AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".m4a", ".aiff"}


class SoundLibrary:
    def __init__(self, directory: str):
        self.dir = Path(directory)
        self.files: dict[str, Path] = {}
        self.descriptions: dict[str, str] = {}
        if self.dir.is_dir():
            for p in sorted(self.dir.iterdir()):
                if p.suffix.lower() in AUDIO_EXTS:
                    self.files[p.stem] = p
            meta = self.dir / "sounds.json"
            if meta.exists():
                self.descriptions = json.loads(meta.read_text())

    @property
    def names(self) -> list[str]:
        return list(self.files)

    def catalog(self) -> str:
        if not self.files:
            return "(no sound bytes available)"
        return "\n".join(
            f"- {name}: {self.descriptions.get(name, 'no description')}" for name in self.files
        )

    def play(self, name: str) -> None:
        path = self.files.get(name)
        if path is None:
            print(f"[sounds] unknown sound: {name}")
            return
        from pydub import AudioSegment
        from pydub.playback import play

        play(AudioSegment.from_file(path))
