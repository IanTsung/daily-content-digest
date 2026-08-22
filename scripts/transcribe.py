"""Transcribe audio content using OpenAI Whisper API."""
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from openai import OpenAI


def transcribe(video_url: str) -> str:
    """Download audio via yt-dlp, transcribe with Whisper, return text.

    yt-dlp handles YouTube, podcasts, and hundreds of other sources — reusable
    for future source types.
    """
    client = OpenAI()

    with TemporaryDirectory() as tmp:
        audio_stem = Path(tmp) / "audio"
        # yt-dlp writes final file as <stem>.mp3 (with the extractor postprocessor)
        subprocess.run(
            [
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "-o", str(audio_stem),
                video_url,
            ],
            check=True,
            capture_output=True,
        )
        audio_path = audio_stem.with_suffix(".mp3")

        with audio_path.open("rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return resp.text
