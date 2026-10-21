# LinkedIn Posts Automation

Free daily posting for Samreena (LinkedIn + X) and Hammad (LinkedIn). No Zapier.

## How it works

1. **2 PM / 2:20 PM PKT** – Claude writes the post and saves it here in `posts/{date}/` (Hammad: `posts/hammad/{date}/`):
   `linkedin.txt`, `x.txt`, `meta.json`, plus the image (`infographic.png` or `slide-01.png` …). You get a review email with edit links.
2. **GitHub Actions** (`.github/workflows/publish.yml`) wakes up and posts through Buffer's free API:
   - 5:55 PM PKT – Hammad's LinkedIn
   - 6:55 PM PKT – Samreena's X
   - 7:55 PM PKT – Samreena's LinkedIn
   A backup run 30 minutes later posts only if the first one didn't.
3. After posting it saves `posted-linkedin.json` / `posted-x.json` in the day's folder (or `failed-….json` with the error). Claude's evening check reads that and emails the confirmation.

## Change or cancel a post

- **Change:** open the file on GitHub (the edit link is in the review email), tap the pencil, edit, *Commit changes*. Do it before the post time.
- **Cancel:** make the first line of `linkedin.txt` / `x.txt` the word `SKIP`, or delete the file.
- **Post it yourself instead:** set `"mode": "NATIVE"` in `meta.json`. The bot won't post LinkedIn that day.

## Test or post by hand

Actions tab → *Publish posts* → *Run workflow*. Pick the post, leave **Dry run** ticked to only see what would be posted, untick it to post now.

## One-time setup

Repo **Settings → Secrets and variables → Actions → New repository secret**: name `BUFFER_API_KEY`, value = the key from https://publish.buffer.com/settings/api.

Never put keys or tokens in any file here; this repo is public.

