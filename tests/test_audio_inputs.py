import tempfile
import unittest
from pathlib import Path

from src.audio_inputs import remove_temp_audio, save_audio_file


class FakeAudioFile:
    def __init__(self, name: str, payload: bytes):
        self.name = name
        self._payload = payload

    def getvalue(self) -> bytes:
        return self._payload


class AudioInputTests(unittest.TestCase):
    def test_save_audio_file_writes_temp_file_with_metadata(self):
        audio = FakeAudioFile("meeting.wav", b"RIFFdemo")

        saved = save_audio_file(audio, "upload")
        self.addCleanup(remove_temp_audio, saved.path)

        self.assertEqual(saved.source, "upload")
        self.assertEqual(saved.filename, "meeting.wav")
        self.assertEqual(saved.suffix, ".wav")
        self.assertEqual(saved.bytes_count, len(b"RIFFdemo"))
        self.assertEqual(Path(saved.path).read_bytes(), b"RIFFdemo")
        self.assertIn(Path(tempfile.gettempdir()).resolve(), Path(saved.path).resolve().parents)

    def test_save_audio_file_rejects_empty_audio(self):
        with self.assertRaises(ValueError):
            save_audio_file(FakeAudioFile("empty.wav", b""), "microphone")

    def test_unknown_suffix_uses_default(self):
        saved = save_audio_file(FakeAudioFile("audio.bin", b"audio"), "microphone")
        self.addCleanup(remove_temp_audio, saved.path)

        self.assertEqual(saved.suffix, ".wav")


if __name__ == "__main__":
    unittest.main()
