"""YouTube source: fetch the latest video from a channel."""
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from googleapiclient.discovery import build


@dataclass
class ContentItem:
    """Uniform shape returned by every source fetcher.

    The pipeline reads only these fields; source-specific details stay inside
    the fetcher.
    """
    title: str
    url: str
    published_at: datetime
    needs_transcription: bool = True
    audio_url: Optional[str] = None
    text_content: Optional[str] = None


class YouTubeSource:
    """Fetch the newest video from a YouTube channel via YouTube Data API v3."""

    def __init__(self):
        self.api_key = os.environ["YOUTUBE_API_KEY"]
        self.channel_id = os.environ["YOUTUBE_CHANNEL_ID"]
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def fetch_latest(self, since_hours: int = 30) -> Optional[ContentItem]:
        """Return the newest video published within the last N hours, else None.

        30-hour window is defensive against cron delays and DST shifts —
        prefer occasional re-summarization (guarded upstream by daily filename
        dedup) over missing a video.
        """
        resp = (
            self.youtube.search()
            .list(
                channelId=self.channel_id,
                part="id,snippet",
                order="date",
                maxResults=1,
                type="video",
            )
            .execute()
        )
        items = resp.get("items", [])
        if not items:
            return None

        item = items[0]
        published_at = datetime.fromisoformat(
            item["snippet"]["publishedAt"].replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) - published_at > timedelta(hours=since_hours):
            return None  # nothing new since last run

        return ContentItem(
            title=item["snippet"]["title"],
            url=f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            published_at=published_at,
            needs_transcription=True,
        )
