from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Protocol


class AudioFileLike(Protocol):
    name: str

    def getvalue(self) -> bytes:
        """Return uploaded or recorded audio bytes."""


@dataclass(frozen=True)
class SavedAudio:
    path: str
    source: str
    filename: str
    suffix: str
    bytes_count: int


def save_audio_file(file_obj: AudioFileLike, source: str, default_suffix: str = ".wav") -> SavedAudio:
    audio_bytes = file_obj.getvalue()
    if not audio_bytes:
        raise ValueError("Audio input is empty. Record or upload a short meeting clip.")

    filename = getattr(file_obj, "name", "") or f"{source}{default_suffix}"
    suffix = _safe_suffix(filename, default_suffix)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        path = tmp.name

    return SavedAudio(
        path=path,
        source=source,
        filename=filename,
        suffix=suffix,
        bytes_count=len(audio_bytes),
    )


def remove_temp_audio(path: str | None) -> None:
    if not path:
        return

    temp_path = Path(path)
    if not temp_path.exists() or not temp_path.is_file():
        return

    temp_dir = Path(tempfile.gettempdir()).resolve()
    try:
        resolved = temp_path.resolve()
    except OSError:
        return

    if temp_dir in resolved.parents:
        temp_path.unlink(missing_ok=True)


def _safe_suffix(filename: str, default_suffix: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm"}:
        return suffix
    if default_suffix.startswith("."):
        return default_suffix
    return f".{default_suffix}"
