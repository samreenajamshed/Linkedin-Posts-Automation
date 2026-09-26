#!/usr/bin/env python3
"""Render a LinkedIn visual and host it in this GitHub repo.

Usage: GH_TOKEN=... python3 publish.py spec.json YYYY-MM-DD [prefix]   (prefix defaults to "posts"; Hammad uses "posts/hammad")
Fetches render.py from the repo, renders into ./out, uploads every output
file to posts/<date>/ and prints one JSON line with the public raw URLs.
"""
import base64, json, os, subprocess, sys, urllib.request

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
        if e.code == 404:
            return None
        raise


def upload(local, path, msg):
    existing = gh("GET", f"{API}/{path}")
    body = {"message": msg, "content": base64.b64encode(open(local, "rb").read()).decode()}
    if existing and "sha" in existing:
        body["sha"] = existing["sha"]
    gh("PUT", f"{API}/{path}", body)
    return f"{RAW}/{path}"


def main():
    spec, day = sys.argv[1], sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else "posts"
    urllib.request.urlretrieve(f"{RAW}/render.py", "render.py")
    res = subprocess.run([sys.executable, "render.py", spec, "out"], capture_output=True, text=True)
    if res.returncode != 0:
        print(json.dumps({"ok": False, "error": res.stderr[-1500:]}))
        sys.exit(1)
    palette = next((l.split(":", 1)[1].strip() for l in res.stdout.splitlines() if l.startswith("PALETTE:")), None)
    urls = {}
    for f in sorted(os.listdir("out")):
        urls[f] = upload(os.path.join("out", f), f"{prefix}/{day}/{f}", f"Visual for {day}: {f}")
    upload(spec, f"{prefix}/{day}/spec.json", f"Spec for {day}")
    print(json.dumps({"ok": True, "palette": palette, "urls": urls}))


if __name__ == "__main__":
    main()
