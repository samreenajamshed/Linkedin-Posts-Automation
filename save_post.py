#!/usr/bin/env python3
"""Save a prepared post into this repo so GitHub Actions can publish it.

Usage (the Claude draft run calls this inside the Higgsfield sandbox):
  GH_TOKEN=... python3 save_post.py posts/2026-10-21 linkedin.txt x.txt meta.json \
      --history '{"account":"samreena","date":"2026-10-21","pillar":"Series","topic":"Day 18: AI memory","mode":"NATIVE"}'

Uploads each local file to <folder>/<filename> (overwriting), optionally appends
one JSON line to history.jsonl (used for topic dedup and the series day count),
and prints one JSON line: {"ok": true, "files": {...raw urls...}, "edit": {...github edit urls...}}.
"""
import argparse, base64, json, os, urllib.error, urllib.request

REPO = "samreenajamshed/Linkedin-Posts-Automation"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
API = f"https://api.github.com/repos/{REPO}/contents"
TOKEN = os.environ["GH_TOKEN"]


def gh(method, url, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404 and method == "GET":
            return None
        raise RuntimeError(f"GitHub {method} {url}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")


def put(path, content_bytes, msg):
    existing = gh("GET", f"{API}/{path}")
    body = {"message": msg, "content": base64.b64encode(content_bytes).decode()}
    if existing and "sha" in existing:
        body["sha"] = existing["sha"]
    gh("PUT", f"{API}/{path}", body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--history", default="")
    a = ap.parse_args()
    folder = a.folder.strip("/")
    out = {"ok": True, "files": {}, "edit": {}}
    for f in a.files:
        name = os.path.basename(f)
        put(f"{folder}/{name}", open(f, "rb").read(), f"Post for {folder}: {name}")
        out["files"][name] = f"{RAW}/{folder}/{name}"
        out["edit"][name] = f"https://github.com/{REPO}/edit/main/{folder}/{name}"
    if a.history:
        entry = json.loads(a.history)
        existing = gh("GET", f"{API}/history.jsonl")
        old = base64.b64decode(existing["content"]).decode() if existing else ""
        if old and not old.endswith("\n"):
            old += "\n"
        put("history.jsonl", (old + json.dumps(entry, ensure_ascii=False) + "\n").encode(), f"History: {folder}")
        out["history"] = "appended"
    print(json.dumps(out))


if __name__ == "__main__":
    main()

