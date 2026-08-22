"""Extract transcript from YouTube auto-generated subtitles.

Pivoted from Whisper-based audio transcription to subtitle-based extraction
because yt-dlp keeps hitting format/bot issues on GitHub Actions IPs when
trying to download audio. Subtitles are a separate YouTube endpoint that's
much more reliable and free.

Trade-off: auto-caption quality is lower than Whisper (especially technical
terms like coin tickers). For crypto TA content this is generally acceptable
— we're extracting concepts, not verbatim transcription.

If quality becomes a problem, we can add a Whisper fallback later, or feed
the subtitle text through Claude/GPT-4o with a "normalize technical terms"
step before the actual summarize prompt.
"""
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


# Language priority order — try Chinese variants first, English as fallback
SUB_LANGS = ["zh-Hans", "zh-CN", "zh", "zh-Hant", "zh-TW", "en"]


def vtt_to_text(vtt: str) -> str:
    """Extract plain text from a WebVTT subtitle string.

    - Skip headers, timestamps, cue metadata, HTML tags
    - Dedupe consecutive identical lines (YouTube auto-caps use a cumulative
      style where each cue includes prior text)
    """
    lines = []
    prev = None
    for line in vtt.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:", "STYLE")):
            continue
        if "-->" in line:
            continue
        # Strip HTML tags e.g. <c>, <00:00:03.360><c>, </c>
        line = re.sub(r"<[^>]*>", "", line).strip()
        if not line or line == prev:
            continue
        lines.append(line)
        prev = line
    return " ".join(lines)


def transcribe(video_url: str) -> str:
    """Download YouTube auto-subs (Chinese preferred, English fallback),
    return plain-text transcript.
    """
    with TemporaryDirectory() as tmp:
        sub_stem = Path(tmp) / "subs"

        cmd = [
            "yt-dlp",
            "--write-auto-subs",
            "--sub-langs", ",".join(SUB_LANGS),
            "--skip-download",
            "--sub-format", "vtt",
            "-o", str(sub_stem),
            "--no-warnings",
        ]

        # Cookies help avoid bot detection on the subtitles endpoint too
        yt_cookies = os.environ.get("YT_COOKIES", "").strip()
        if yt_cookies:
            cookies_path = Path(tmp) / "cookies.txt"
            cookies_path.write_text(yt_cookies, encoding="utf-8")
            cmd.extend(["--cookies", str(cookies_path)])
        else:
            sys.stderr.write(
                "WARNING: YT_COOKIES not set. Subtitle endpoint is less "
                "bot-blocked than audio but may still fail without cookies.\n"
            )

        cmd.append(video_url)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write("--- yt-dlp failed ---\n")
            sys.stderr.write(f"STDOUT:\n{result.stdout}\n")
            sys.stderr.write(f"STDERR:\n{result.stderr}\n")
            sys.stderr.write("--- end yt-dlp ---\n")
            result.check_returncode()

        # yt-dlp writes files as <sub_stem>.<lang>.vtt (e.g. subs.zh-Hans.vtt)
        candidates = list(Path(tmp).glob(f"{sub_stem.name}.*.vtt"))
        if not candidates:
            raise RuntimeError(
                f"yt-dlp succeeded but no VTT produced. Tried langs={SUB_LANGS}. "
                "Video may have no auto-captions in any of these languages."
            )

        # Prefer languages in SUB_LANGS order
        chosen = None
        for lang in SUB_LANGS:
            for c in candidates:
                if f".{lang}." in c.name:
                    chosen = c
                    break
            if chosen:
                break
        chosen = chosen or candidates[0]
        print(f"Using subtitle file: {chosen.name}", file=sys.stderr)

        vtt = chosen.read_text(encoding="utf-8")
        return vtt_to_text(vtt)
