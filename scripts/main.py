"""Daily content digest pipeline.

Env vars:
  SOURCE_ID              — which fetcher to dispatch (e.g. "youtube-crypto-ta")
  YOUTUBE_CHANNEL_ID     — for YouTube sources
  YOUTUBE_API_KEY        — Google Cloud API key
  OPENAI_API_KEY         — Whisper transcription
  ANTHROPIC_API_KEY      — Claude summarization
  TELEGRAM_BOT_TOKEN     — notification
  TELEGRAM_CHAT_ID       — notification target

Flow:
  1. Fetch latest item from source
  2. Skip if today's summary already exists (dedup on manual retriggers)
  3. Transcribe (if audio/video) or use raw text
  4. Summarize via Claude
  5. Write summary file + notify Telegram
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# scripts/ is added to sys.path by python's default behavior when running
# `python scripts/main.py` — so `from sources import ...` resolves to
# scripts/sources/.
from sources import get_source
from transcribe import transcribe
from summarize import summarize
from notify import notify_telegram


SUMMARY_DIR = Path("summaries")


def main() -> int:
    source_id = os.environ["SOURCE_ID"]
    source = get_source(source_id)

    print(f"[{source_id}] Fetching latest content...")
    item = source.fetch_latest()
    if item is None:
        print(f"[{source_id}] No new content in the last 30h — exiting.")
        return 0

    print(f"[{source_id}] Item: {item.title}")
    print(f"[{source_id}]   URL: {item.url}")
    print(f"[{source_id}]   Published: {item.published_at.isoformat()}")

    # Dedup: skip if today's summary already exists (manual retrigger, cron
    # firing twice near midnight, etc.)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = SUMMARY_DIR / source_id / f"{today}.md"
    if out_path.exists():
        print(f"[{source_id}] Summary already exists at {out_path} — exiting.")
        return 0

    if item.needs_transcription:
        print(f"[{source_id}] Downloading + transcribing...")
        transcript = transcribe(item.audio_url or item.url)
    else:
        transcript = item.text_content or ""

    print(f"[{source_id}] Transcript: {len(transcript)} chars")
    print(f"[{source_id}] Summarizing...")
    summary = summarize(source_id, item, transcript)

    # Persist
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        f"# {today} · {item.title}\n\n"
        f"**Source**: {item.url}\n"
        f"**Published**: {item.published_at.isoformat()}\n\n"
        f"---\n\n{summary}\n",
        encoding="utf-8",
    )
    print(f"[{source_id}] Saved to {out_path}")

    # Notify (Telegram limit is 4096 chars; leave headroom)
    notify_telegram(
        f"📊 *{source_id}* · {today}\n"
        f"[{item.title}]({item.url})\n\n"
        f"{summary[:3500]}"
    )
    print(f"[{source_id}] Notified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
