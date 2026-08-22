# daily-content-digest

Serverless pipeline that fetches new content from subscribed sources daily, transcribes if audio/video, summarizes with an LLM, and pushes a brief to Telegram (or your preferred notifier).

**Design goals**: extensible source types, per-source workflow isolation, GitHub Actions native (no additional infrastructure to maintain).

**Cost**: ~$3/month for one daily source (Whisper + Claude API + free-tier GitHub Actions).

---

## Current pipelines

- **`youtube-crypto-ta`** — daily @ 08:00 AEST from one YouTube channel (workflow: `.github/workflows/youtube-crypto-ta.yml`)

Add more by copying the workflow and pointing it at a different channel ID secret.

---

## Architecture

```
GitHub Actions cron
  → Python script (scripts/main.py)
    → Source fetcher (scripts/sources/*.py) — YouTube API to find latest video
    → Transcribe (yt-dlp auto-subs, no audio download) — parse VTT → plain text
    → Summarize (GPT-4o) — structured output
    → Notify (Telegram) + commit summary to `summaries/<source-id>/YYYY-MM-DD.md`
```

**Why subtitles instead of Whisper?** YouTube blocks audio downloads from
datacenter IPs (Azure/GCP/AWS) and yt-dlp's format-selector keeps hitting
edge cases. Auto-caption endpoint is separate and much more reliable.
Trade-off: auto-cap quality < Whisper for technical terms; for crypto TA
content it's generally acceptable.

**Extension points**:
- **Another YouTube channel** → copy workflow yaml, change `SOURCE_ID` + channel ID secret
- **Podcast** → add `scripts/sources/podcast.py` fetcher (RSS + audio URL), transcribe stays the same
- **Blog / RSS** → add fetcher, skip transcribe, straight to summarize
- **Discord archive** → add fetcher (if you get read access), skip transcribe

---

## Setup

### 1. Fork or clone this repo

Create a private GitHub repo and push this code.

### 2. Set GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret**. Set:

| Secret | Where to get it |
|---|---|
| `YOUTUBE_API_KEY` | https://console.cloud.google.com/apis/credentials → enable YouTube Data API v3 |
| `YOUTUBE_CHANNEL_ID_CRYPTO_TA` | Go to the target YouTube channel → view source → find `"channelId":"UC..."`, or use https://commentpicker.com/youtube-channel-id.php |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys — used for **both** Whisper (transcription) and GPT-4o (summarization) |
| `YT_COOKIES` | See **YouTube cookies** section below — required to bypass YouTube's bot detection on GitHub Actions IPs |
| `TELEGRAM_BOT_TOKEN` | Chat with `@BotFather` on Telegram → `/newbot` → copy token |
| `TELEGRAM_CHAT_ID` | Send a message to your bot → GET `https://api.telegram.org/bot<TOKEN>/getUpdates` → find `chat.id` |

### YouTube cookies (`YT_COOKIES`)

YouTube blocks Azure / GCP / AWS datacenter IPs with "Sign in to confirm you're not a bot" — this includes GitHub Actions runners. The standard workaround is to pass browser cookies. Steps:

1. **Install a cookie exporter**:
   - Chrome: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
2. Open **youtube.com** in your browser (logged in to your Google account)
3. Click the extension icon → **Export** (for current site) → download `youtube.com_cookies.txt`
4. Open the file in a text editor → **copy the entire contents** (including the `# Netscape HTTP Cookie File` header)
5. GitHub → Settings → Secrets → **New repository secret**:
   - Name: `YT_COOKIES`
   - Value: paste the full contents

**Cookie rotation**: YouTube session cookies typically last 1–3 months. If the pipeline starts failing again with the same "Sign in to confirm you're not a bot" error weeks later, re-export cookies and update the secret.

**Isolation tip** (optional): Use a dedicated Chrome/Firefox profile signed in to a Google account you don't use for anything else. If Google flags the account for automation, you're not risking your main account.

### 3. Enable Actions

**Settings → Actions → General → Workflow permissions**: set to **Read and write** (so the workflow can commit summaries back).

### 4. First run

Go to **Actions tab → YouTube Crypto TA · Daily Digest → Run workflow**. This uses `workflow_dispatch` to test the pipeline before waiting for the daily cron.

---

## Cost breakdown (one daily source, 10-min video)

| Item | Monthly |
|---|---|
| yt-dlp auto-subs fetch | free |
| GPT-4o summarization (5K in + 1.5K out × 30) | ~$0.85 |
| YouTube Data API | free (well within 10K units/day quota) |
| GitHub Actions | free (private repo: 2000 min/month free tier) |
| Telegram | free |
| **Total** | **~$0.85/month** |

Add ~$0.85/month per additional daily source. Switch `gpt-4o` to `gpt-4o-mini` in `scripts/summarize.py` to cut summarization cost ~15× (~$0.06/month) if quality is acceptable.

---

## Roadmap

- [x] Phase 1: YouTube crypto TA daily
- [ ] Phase 2: additional YouTube channels
- [ ] Phase 3: podcast source (RSS + audio)
- [ ] Phase 4: blog / RSS source (text only, skip transcribe)
- [ ] Phase 5: optional Notion integration for summary archive

---

## Notes

- **Cron timing**: GitHub Actions cron uses UTC. `0 22 * * *` = 08:00 AEST (UTC+10 winter) / 09:00 AEDT (UTC+11 summer). Cron can delay 5–15 min under runner load, which is fine for a "morning brief" use case.
- **Transcript length**: truncated to 120K chars before sending to Claude to stay well within the 1M context window even after tokenization.
- **Dedup**: if a summary file for today already exists, the pipeline exits early. Prevents duplicate runs on manual retriggers.
