#!/usr/bin/env python3
"""Create 2k24AIE55/life-wallpaper repo, push landing page, enable GitHub Pages.
Token is read from the git credential helper and never printed."""
import json
import os
import re
import subprocess
import urllib.request

SITE = os.path.expanduser("~/workspace/lifewallpaper-site")


def get_token():
    with open(os.path.expanduser("~/.git-credentials")) as f:
        for line in f:
            if "github.com" in line:
                m = re.search(r"https://([^:]+):([^@]+)@github\.com", line)
                if m:
                    return m.group(2)
    raise RuntimeError("no github token in credential helper")


TOKEN = get_token()


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"https://api.github.com{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="ignore")


def sh(cmd, cwd=SITE):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd}: {r.stderr[:300]}")
    return r.stdout.strip()


# who am i
status, me = api("GET", "/user")
login = me["login"]
print("GitHub login:", login)

# create repo if missing
status, _ = api("GET", f"/repos/{login}/life-wallpaper")
if status == 404:
    status, repo = api("POST", "/user/repos", {
        "name": "life-wallpaper",
        "description": "The Life Wallpaper — free Android live wallpaper showing your life in weeks (Memento Mori dot grid).",
        "private": False,
        "auto_init": False,
        "has_issues": True,
        "has_wiki": False,
    })
    print("repo create status:", status)
else:
    print("repo already exists")

# init + commit + push (idempotent)
if not os.path.exists(os.path.join(SITE, ".git")):
    sh(["git", "init", "-b", "main"])
sh(["git", "add", "-A"])
# commit only if there is something to commit
st = subprocess.run(["git", "status", "--porcelain"], cwd=SITE,
                    capture_output=True, text=True).stdout.strip()
head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=SITE,
                      capture_output=True, text=True)
if st or head.returncode != 0:
    sh(["git", "-c", "user.name=Sajjad Ali", "-c", "user.email=sajjad@pakcreator.com",
        "commit", "-m",
        "Landing page for The Life Wallpaper Android app"])
else:
    print("nothing to commit")
try:
    sh(["git", "remote", "remove", "origin"])
except RuntimeError:
    pass
sh(["git", "remote", "add", "origin",
    f"https://{login}:{TOKEN}@github.com/{login}/life-wallpaper.git"])
# hide token from subsequent output: push quietly
r = subprocess.run(["git", "push", "-u", "origin", "main", "--force"],
                   cwd=SITE, capture_output=True, text=True)
print("push rc:", r.returncode, (r.stderr[-200:] if r.returncode else "ok"))
sh(["git", "remote", "set-url", "origin",
    f"https://github.com/{login}/life-wallpaper.git"])

# enable Pages
status, pages = api("POST", f"/repos/{login}/life-wallpaper/pages",
                    {"build_type": "legacy",
                     "source": {"branch": "main", "path": "/"}})
info = pages.get("html_url", pages) if isinstance(pages, dict) else pages
print("pages status:", status, info)
