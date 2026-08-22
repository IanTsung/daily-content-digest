"""Transcribe audio content using OpenAI Whisper API."""
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from openai import OpenAI


def transcribe(video_url: str) -> str:
    """Download audio via yt-dlp, transcribe with Whisper, return text.

    Notes on yt-dlp + GitHub Actions:
    - YouTube often blocks Azure/GCP datacenter IPs with "Sign in to confirm
      you're not a bot". We try alternate player clients as a first-line
      workaround. If it still fails, cookies passed via YT_COOKIES secret
      is the standard fallback (see README).
    - We surface yt-dlp stderr on failure — critical for debugging
      YouTube-side breakages, which change several times a year.
    """
    client = OpenAI()

    with TemporaryDirectory() as tmp:
        audio_stem = Path(tmp) / "audio"
        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "-o", str(audio_stem),
            # Try mobile/embedded clients first — they hit less bot detection
            "--extractor-args", "youtube:player_client=web_safari,mweb,android",
            "--no-warnings",
            video_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write("--- yt-dlp failed ---\n")
            sys.stderr.write(f"CMD: {' '.join(cmd)}\n")
            sys.stderr.write(f"STDOUT:\n{result.stdout}\n")
            sys.stderr.write(f"STDERR:\n{result.stderr}\n")
            sys.stderr.write("--- end yt-dlp ---\n")
            result.check_returncode()  # raises CalledProcessError
        audio_path = audio_stem.with_suffix(".mp3")

        with audio_path.open("rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return resp.text
