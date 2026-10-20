#!/usr/bin/env python3
"""
指定URLのページ本文テキストの変化を検知し、Discordに差分を通知する。

- urls.yml に監視対象を列挙
- 前回のテキストを snapshots/ に保存し、今回取得分と比較
- 変化があれば Discord Webhook (環境変数 DISCORD_WEBHOOK_URL) に差分を投稿
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "urls.yml"
SNAPSHOT_DIR = ROOT / "snapshots"

DISCORD_LIMIT = 2000  # Discordメッセージの最大文字数
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 html-monitor"
)


def load_config() -> list[dict]:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    targets = data.get("targets") or []
    for t in targets:
        if "url" not in t:
            raise ValueError(f"url がない監視対象があります: {t}")
        t.setdefault("name", t["url"])
        t.setdefault("ignore_patterns", [])
    return targets


def fetch_html(url: str, retries: int = 3) -> str:
    last_err: Exception | None = None
    for i in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or r.encoding  # 日本語サイトの文字化け対策
            return r.text
        except requests.RequestException as e:
            last_err = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"取得失敗: {url} ({last_err})")


def html_to_text(html: str, ignore_patterns: list[str]) -> str:
    """HTMLから本文テキストを抽出して正規化する。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")

    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        for pat in ignore_patterns:  # 日時やカウンタなど、毎回変わる部分を除外
            line = re.sub(pat, "", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines) + "\n"


def snapshot_path(url: str) -> Path:
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return SNAPSHOT_DIR / f"{key}.txt"


def make_diff(old: str, new: str) -> tuple[str, int, int]:
    diff = list(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(), lineterm="", n=1
        )
    )[2:]  # ---/+++ ヘッダを除く
    added = sum(1 for l in diff if l.startswith("+"))
    removed = sum(1 for l in diff if l.startswith("-"))
    return "\n".join(diff), added, removed


def build_message(name: str, url: str, diff: str, added: int, removed: int) -> str:
    header = f"🔔 **変更を検知: {name}**\n<{url}>\n追加 {added} 行 / 削除 {removed} 行\n"
    fence_open, fence_close = "```diff\n", "\n```"
    room = DISCORD_LIMIT - len(header) - len(fence_open) - len(fence_close) - 30
    body = diff.replace("```", "ˋˋˋ")
    if len(body) > room:
        body = body[:room].rsplit("\n", 1)[0] + "\n… (差分が長いため省略)"
    return header + fence_open + body + fence_close


def notify_discord(content: str) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("[warn] DISCORD_WEBHOOK_URL 未設定のため通知をスキップ\n" + content)
        return
    r = requests.post(webhook, json={"content": content}, timeout=30)
    if r.status_code == 429:  # レート制限
        time.sleep(float(r.json().get("retry_after", 2)))
        r = requests.post(webhook, json={"content": content}, timeout=30)
    r.raise_for_status()


def check_target(t: dict) -> bool:
    """1件チェック。変化があれば True。"""
    url, name = t["url"], t["name"]
    text = html_to_text(fetch_html(url), t["ignore_patterns"])
    path = snapshot_path(url)

    if not path.exists():
        path.write_text(text, encoding="utf-8")
        print(f"[init] {name}: 初回スナップショットを保存")
        return False

    old = path.read_text(encoding="utf-8")
    if old == text:
        print(f"[same] {name}")
        return False

    diff, added, removed = make_diff(old, text)
    notify_discord(build_message(name, url, diff, added, removed))
    path.write_text(text, encoding="utf-8")
    print(f"[diff] {name}: +{added} -{removed}")
    return True


def main() -> int:
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    errors = []
    for t in load_config():
        try:
            check_target(t)
        except Exception as e:  # 1件の失敗で全体を止めない
            print(f"[error] {t['name']}: {e}", file=sys.stderr)
            errors.append(f"{t['name']}: {e}")

    if errors and os.environ.get("NOTIFY_ERRORS", "false").lower() == "true":
        notify_discord("⚠️ **監視エラー**\n" + "\n".join(errors)[:1900])
    return 0


if __name__ == "__main__":
    sys.exit(main())
