"""Extract transcript from YouTube auto-generated subtitles.

Uses the `youtube-transcript-api` library, which hits YouTube's timedtext
endpoint directly (https://www.youtube.com/api/timedtext) instead of the
main player API that yt-dlp uses.

This is a different bot-detection surface — timedtext historically works
from datacenter IPs when the player API doesn't. If timedtext also gets
blocked in the future, next fallback is a proxy or the Whisper path.
"""
import sys
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)


# Language priority — Chinese variants first, English as final fallback
SUB_LANGS = ["zh-Hans", "zh-CN", "zh", "zh-Hant", "zh-TW", "en"]


def extract_video_id(url: str) -> str:
    """Get YouTube video ID from a watch URL or short URL."""
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")
    query = parse_qs(parsed.query)
    if "v" in query:
        return query["v"][0]
    raise ValueError(f"Cannot extract video ID from URL: {url!r}")


def transcribe(video_url: str) -> str:
    """Fetch YouTube auto-caps via timedtext API, return plain-text transcript."""
    video_id = extract_video_id(video_url)
    print(
        f"Fetching transcript for {video_id} (langs: {SUB_LANGS})",
        file=sys.stderr,
    )
    try:
        entries = YouTubeTranscriptApi.get_transcript(
            video_id, languages=SUB_LANGS
        )
    except TranscriptsDisabled:
        raise RuntimeError(f"Transcripts disabled for video {video_id}")
    except NoTranscriptFound:
        raise RuntimeError(
            f"No auto-caption in {SUB_LANGS} for video {video_id}"
        )
    except VideoUnavailable:
        raise RuntimeError(f"Video {video_id} unavailable (private/removed)")

    # entries: [{"text": "...", "start": 0.0, "duration": 3.5}, ...]
    return " ".join(e["text"] for e in entries)
