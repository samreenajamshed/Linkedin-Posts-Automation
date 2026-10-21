#!/usr/bin/env python3
"""Post today's prepared post to Buffer (share now). Runs inside GitHub Actions.

Usage:
  BUFFER_API_KEY=... python3 scripts/buffer_publish.py --target samreena-linkedin [--date YYYY-MM-DD] [--dry-run]

Targets (fixed, so a post can never go to the wrong person):
  samreena-linkedin  posts/{D}/linkedin.txt        -> Samreena's LinkedIn channel
  samreena-x         posts/{D}/x.txt               -> Samreena's X channel
  hammad-linkedin    posts/hammad/{D}/linkedin.txt -> Hammad's LinkedIn channel

Post folder files (written by the 2 PM Claude draft run):
  linkedin.txt / x.txt   the exact post text. Delete the file, or make its first line SKIP, to cancel.
  meta.json              {"mode": "AUTO|NATIVE|MANUAL|SKIP", "textonly": false, "topic": "...", "alt": "image title"}
  infographic.png or slide-01.png ... slide-09.png   optional images (LinkedIn only)

Result files written next to the post (and committed by the workflow):
  posted-<network>.json  on success (also stops a second run from posting twice)
  failed-<network>.json  on failure (the run then exits 1, so GitHub emails the repo owner)
"""
import argparse, datetime, json, os, re, sys, time, urllib.error, urllib.request
from zoneinfo import ZoneInfo

REPO = "samreenajamshed/Linkedin-Posts-Automation"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
API_URL = "https://api.buffer.com"
ORG_ID = "6ab4b8b64f95d419793fe830"

TARGETS = {
    "samreena-linkedin": {"prefix": "posts", "network": "linkedin", "channel": "6ab75598ea19ca0bdef0fc3a",
                          "service": ("linkedin",), "name_has": "samreena", "max_len": 3000},
    "samreena-x": {"prefix": "posts", "network": "x", "channel": "6ab4b987ea19ca0bded1720f",
                   "service": ("twitter", "x"), "name_has": "samreena", "max_len": 280},
    "hammad-linkedin": {"prefix": "posts/hammad", "network": "linkedin", "channel": "6ab791c0ea19ca0bdef2f8bc",
                        "service": ("linkedin",), "name_has": "hammad", "max_len": 3000},
}

CHANNELS_Q = """query Channels($org: OrganizationId!) {
  channels(input: { organizationId: $org }) { id name displayName service isDisconnected isLocked }
}"""

CREATE_Q = """mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id dueAt status } }
    ... on MutationError { message }
  }
}"""


def log(msg):
    print(msg, flush=True)


def gql(query, variables):
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("BUFFER_API_KEY secret is missing. Add it under repo Settings > Secrets and variables > Actions.")
    req = urllib.request.Request(API_URL, method="POST",
                                 data=json.dumps({"query": query, "variables": variables}).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                          "User-Agent": "linkedin-posts-automation"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Buffer HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    if data.get("errors"):
        raise RuntimeError("Buffer error: " + "; ".join(e.get("message", str(e)) for e in data["errors"]))
    return data["data"]


def clean_linkedin(text):
    """Remove characters that have broken LinkedIn API posts before, without rewording."""
    text = re.sub(r"\s*\(([^()\n]*)\)", r", \1", text)  # "a (b) c" -> "a, b c"
    text = re.sub(r"[\[\]{}<>|~*\\]", "", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def find_images(folder):
    if os.path.isfile(os.path.join(folder, "infographic.png")):
        return ["infographic.png"]
    slides = []
    for i in range(1, 10):
        name = f"slide-{i:02d}.png"
        if not os.path.isfile(os.path.join(folder, name)):
            break
        slides.append(name)
    return slides


def write_result(folder, name, payload):
    with open(os.path.join(folder, name), "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=sorted(TARGETS))
    ap.add_argument("--date", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    t = TARGETS[a.target]
    day = a.date or datetime.datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d")
    folder = f"{t['prefix']}/{day}"
    net = t["network"]
    log(f"Target {a.target}, date {day}, folder {folder}")

    if os.path.exists(os.path.join(folder, f"posted-{net}.json")):
        log("Already posted today. Nothing to do.")
        return 0

    text_path = os.path.join(folder, f"{net}.txt")
    if not os.path.isfile(text_path):
        log(f"No {text_path}: nothing prepared or it was cancelled. Skipping.")
        return 0
    text = open(text_path, encoding="utf-8").read().strip()
    meta = {}
    if os.path.isfile(os.path.join(folder, "meta.json")):
        meta = json.load(open(os.path.join(folder, "meta.json"), encoding="utf-8"))
    mode = str(meta.get("mode", "AUTO")).upper()

    if not text or text.splitlines()[0].strip().upper().startswith("SKIP") or mode == "SKIP":
        log("Post marked SKIP. Not posting.")
        return 0
    if net == "linkedin" and mode in ("NATIVE", "MANUAL"):
        log(f"Mode is {mode}: she posts this one herself. Not posting.")
        return 0

    images = []
    if net == "linkedin":
        text = clean_linkedin(text)
        if not meta.get("textonly"):
            images = find_images(folder)
    if len(text) > t["max_len"]:
        err = f"Post is {len(text)} characters, over the {t['max_len']} limit. Shorten {text_path}."
        write_result(folder, f"failed-{net}.json", {"ok": False, "error": err, "at": time.strftime("%FT%TZ", time.gmtime())})
        log(err)
        return 1

    alt = str(meta.get("alt") or meta.get("topic") or "Post image")[:400]
    assets = [{"image": {"url": f"{RAW}/{folder}/{img}", "metadata": {"altText": alt}}} for img in images]
    log(f"Text: {len(text)} chars. Images: {images or 'none'}")

    if a.dry_run:
        log("DRY RUN, nothing sent. Payload:")
        log(json.dumps({"channelId": t["channel"], "text": text, "assets": assets}, indent=2, ensure_ascii=False))
        return 0

    result = {"ok": False, "target": a.target, "date": day, "images": images, "at": time.strftime("%FT%TZ", time.gmtime())}
    try:
        chans = gql(CHANNELS_Q, {"org": ORG_ID})["channels"]
        ch = next((c for c in chans if c["id"] == t["channel"]), None)
        label = f"{ch.get('name', '')} {ch.get('displayName') or ''}".lower() if ch else ""
        if not ch or str(ch["service"]).lower() not in t["service"] or t["name_has"] not in label:
            raise RuntimeError(f"Channel {t['channel']} not found or not the expected {net} account for "
                               f"'{t['name_has']}'. Reconnect it in Buffer. Seen: {label or 'nothing'}")
        if ch.get("isDisconnected") or ch.get("isLocked"):
            raise RuntimeError(f"Buffer channel '{label.strip()}' is disconnected or locked. Reconnect it in Buffer.")

        def create(with_assets):
            inp = {"channelId": t["channel"], "text": text, "schedulingType": "automatic", "mode": "shareNow",
                   "assets": with_assets}
            out = gql(CREATE_Q, {"input": inp})["createPost"]
            if not out or "post" not in out:
                raise RuntimeError("Buffer refused the post: " + str((out or {}).get("message", out)))
            return out["post"]

        attempts = [assets, assets] if assets else [[], []]
        post, errors = None, []
        for i, aset in enumerate(attempts):
            try:
                post = create(aset)
                break
            except Exception as e:  # retry once, same payload
                errors.append(str(e))
                log(f"Attempt {i + 1} failed: {e}")
                time.sleep(10)
        if post is None and assets:  # image post failed twice: fall back to text only
            log("Falling back to a text-only post.")
            post = create([])
            result["fallback"] = "posted without image: " + errors[-1][:300]
            result["images"] = []
        if post is None:
            raise RuntimeError(errors[-1])
        result.update(ok=True, post_id=post.get("id"), status=post.get("status"))
        write_result(folder, f"posted-{net}.json", result)
        fp = os.path.join(folder, f"failed-{net}.json")
        if os.path.exists(fp):
            os.remove(fp)
        log(f"Posted. Buffer post id {post.get('id')}")
        return 0
    except Exception as e:
        result["error"] = str(e)[:1000]
        write_result(folder, f"failed-{net}.json", result)
        log(f"FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

