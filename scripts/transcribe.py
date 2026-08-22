"""Transcribe audio content using OpenAI Whisper API."""
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from openai import OpenAI


def transcribe(video_url: str) -> str:
    """Download audio via yt-dlp, transcribe with Whisper, return text.

    YouTube blocks datacenter IPs (Azure / GCP / AWS) with
    "Sign in to confirm you're not a bot". The standard workaround is to
    pass browser cookies via --cookies. Set YT_COOKIES env var (as a GitHub
    secret) to the full Netscape cookies.txt content.

    Cookies rotate — YouTube session cookies typically last 1-3 months. If
    this starts failing with the same bot error weeks later, re-export
    cookies from your browser and update the YT_COOKIES secret.
    """
    client = OpenAI()

    with TemporaryDirectory() as tmp:
        audio_stem = Path(tmp) / "audio"

        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "-o", str(audio_stem),
            "--extractor-args", "youtube:player_client=web_safari,mweb,android",
            "--no-warnings",
        ]

        # Write cookies secret to a temp file and pass by path — yt-dlp does
        # not accept cookies content directly, only a file path.
        yt_cookies = os.environ.get("YT_COOKIES", "").strip()
        if yt_cookies:
            cookies_path = Path(tmp) / "cookies.txt"
            cookies_path.write_text(yt_cookies, encoding="utf-8")
            cmd.extend(["--cookies", str(cookies_path)])
        else:
            sys.stderr.write(
                "WARNING: YT_COOKIES not set. yt-dlp will likely be blocked "
                "on GitHub Actions IPs by YouTube bot detection. See README.\n"
            )

        cmd.append(video_url)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write("--- yt-dlp failed ---\n")
            sys.stderr.write(f"STDOUT:\n{result.stdout}\n")
            sys.stderr.write(f"STDERR:\n{result.stderr}\n")
            sys.stderr.write("--- end yt-dlp ---\n")
            result.check_returncode()

        audio_path = audio_stem.with_suffix(".mp3")
        with audio_path.open("rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return resp.text
