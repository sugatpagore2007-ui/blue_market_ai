
"""Booming Bulls channel learning tools for Blue Forex Market AI.

This module does NOT ship copied YouTube transcripts or paid-course content.
It stores the public channel as a source, optionally discovers public video URLs
with yt-dlp, optionally fetches public captions with youtube-transcript-api, and
then reuses Blue's Phase 12 lesson extractor to save concise trading rules.

The result is a knowledge/ML filter, not a guaranteed-profit strategy.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from config import DATABASE_FILE
except Exception:  # pragma: no cover
    DATABASE_FILE = "blue_market_ai.db"

from knowledge.video_learning import (
    add_video_source,
    try_fetch_public_transcript,
    import_video_notes,
    DEFAULT_SOURCES_FILE,
    LESSONS_TABLE,
    SOURCES_TABLE,
)

KNOWLEDGE_DIR = "knowledge"
DATASET_DIR = "datasets"
BOOMING_BULLS_CHANNEL_URL = "https://www.youtube.com/@BoomingBulls"
BOOMING_BULLS_VIDEOS_URL = "https://www.youtube.com/@BoomingBulls/videos"
BOOMING_BULLS_SOURCE_FILE = os.path.join(KNOWLEDGE_DIR, "booming_bulls_sources.json")
BOOMING_BULLS_VIDEO_FILE = os.path.join(KNOWLEDGE_DIR, "booming_bulls_video_sources.json")
BOOMING_BULLS_DATASET_FILE = os.path.join(DATASET_DIR, "booming_bulls_strategy_knowledge.csv")


def _ensure_dirs() -> None:
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    os.makedirs(DATASET_DIR, exist_ok=True)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DATABASE_FILE)
    con.row_factory = sqlite3.Row
    return con


def _read_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _write_json(path: str, data: Any) -> None:
    _ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def seed_booming_bulls_channel() -> Dict[str, Any]:
    """Save the channel as a learning source without copying channel content."""
    _ensure_dirs()
    payload = {
        "channel_name": "Booming Bulls",
        "handle": "@BoomingBulls",
        "channel_url": BOOMING_BULLS_CHANNEL_URL,
        "videos_url": BOOMING_BULLS_VIDEOS_URL,
        "status": "source_only",
        "learning_note": (
            "Use this as a source pointer. To learn from the channel, import your notes "
            "or fetch public captions where available. Do not copy/paywall course content."
        ),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _write_json(BOOMING_BULLS_SOURCE_FILE, payload)
    return {"ok": True, "message": f"Booming Bulls channel source saved: {BOOMING_BULLS_CHANNEL_URL}", **payload}


def fetch_booming_bulls_video_list(limit: int = 50, forex_only: bool = False) -> Dict[str, Any]:
    """Discover public video URLs from the channel using yt-dlp if installed.

    This saves only metadata/URLs. It does not download videos or copy transcript text.
    Set forex_only=True to keep videos whose titles look related to Forex/currency/gold.
    """
    _ensure_dirs()
    seed_booming_bulls_channel()
    limit = max(1, min(int(limit or 50), 300))
    try:
        import yt_dlp  # type: ignore
    except Exception:
        return {
            "ok": False,
            "message": "yt-dlp is not installed. Install optional package or add Booming Bulls video URLs manually with: video add source <url>",
        }
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "playlistend": limit,
        "ignoreerrors": True,
    }
    entries: List[Dict[str, Any]] = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(BOOMING_BULLS_VIDEOS_URL, download=False)
        for item in (info or {}).get("entries") or []:
            if not item:
                continue
            vid = item.get("id") or ""
            if not vid:
                continue
            url = item.get("url") or f"https://www.youtube.com/watch?v={vid}"
            if not str(url).startswith("http"):
                url = f"https://www.youtube.com/watch?v={vid}"
            title = item.get("title") or f"Booming Bulls video {vid}"
            if forex_only:
                hay = str(title).lower()
                forex_keys = ["forex", "currency", "eurusd", "gbpusd", "usdjpy", "xauusd", "gold", "dollar", "dxy", "intraday"]
                if not any(k in hay for k in forex_keys):
                    continue
            entries.append({"video_id": vid, "url": url, "title": title, "source_channel": "Booming Bulls", "forex_only_filter": forex_only})
    except Exception as e:
        return {"ok": False, "message": f"Could not read channel video list: {str(e)[:220]}"}

    _write_json(BOOMING_BULLS_VIDEO_FILE, entries)
    added = 0
    for e in entries:
        res = add_video_source(e["url"], title=e.get("title") or "Booming Bulls strategy video")
        if res.get("ok"):
            added += 1
    return {
        "ok": True,
        "found": len(entries),
        "added_to_video_learning": added,
        "source_file": BOOMING_BULLS_VIDEO_FILE,
        "message": f"Saved {len(entries)} Booming Bulls {'forex-related ' if forex_only else ''}video URL(s); {added} added to Blue video learning sources.",
    }



def fetch_booming_bulls_forex_video_list(limit: int = 100) -> Dict[str, Any]:
    """Discover Forex-related Booming Bulls public videos by title keywords.

    This is a source-discovery helper. It does not copy channel content. Blue can
    later try public captions or your own notes for those sources.
    """
    return fetch_booming_bulls_video_list(limit=limit, forex_only=True)


def fetch_booming_bulls_public_transcripts(limit: int = 25) -> Dict[str, Any]:
    """Try to fetch public captions for saved Booming Bulls video URLs.

    This can fail when captions are disabled, unavailable, rate-limited, or in an
    unsupported language. Manual notes still work.
    """
    limit = max(1, min(int(limit or 25), 100))
    videos = _read_json(BOOMING_BULLS_VIDEO_FILE, [])
    if not videos:
        first = fetch_booming_bulls_video_list(limit=limit)
        if not first.get("ok"):
            return first
        videos = _read_json(BOOMING_BULLS_VIDEO_FILE, [])
    ok_count = fail_count = lessons_total = 0
    results = []
    for item in videos[:limit]:
        ref = item.get("url") or item.get("video_id")
        res = try_fetch_public_transcript(ref)
        if res.get("ok"):
            ok_count += 1
            lessons_total += int(res.get("lessons_saved") or 0)
        else:
            fail_count += 1
        results.append({"video_id": item.get("video_id"), "ok": bool(res.get("ok")), "message": res.get("message")})
    return {
        "ok": ok_count > 0,
        "attempted": len(results),
        "success": ok_count,
        "failed": fail_count,
        "lessons_saved": lessons_total,
        "results": results,
        "message": f"Booming Bulls transcript import: {ok_count} succeeded, {fail_count} failed, {lessons_total} lessons saved.",
    }


def import_booming_bulls_notes(path: str) -> Dict[str, Any]:
    """Import user's own notes/summaries from Booming Bulls videos."""
    if not os.path.exists(path):
        return {"ok": False, "message": f"Notes file not found: {path}"}
    res = import_video_notes(path, source_name="booming_bulls_user_notes")
    res["message"] = "Booming Bulls notes: " + str(res.get("message"))
    return res


def _booming_video_ids() -> set[str]:
    videos = _read_json(BOOMING_BULLS_VIDEO_FILE, [])
    return {str(v.get("video_id") or "") for v in videos if v.get("video_id")}


def export_booming_bulls_knowledge_dataset() -> Dict[str, Any]:
    """Export learned Booming Bulls lessons into a compact knowledge dataset CSV.

    This is not a win/loss supervised model dataset. It is a rule/knowledge dataset
    used by Blue's video knowledge filter and can be reviewed or converted into
    labeled examples only after backtesting/demo validation.
    """
    _ensure_dirs()
    ids = _booming_video_ids()
    con = _connect()
    rows = con.execute(
        f"SELECT * FROM {LESSONS_TABLE} WHERE active=1 ORDER BY created_at DESC LIMIT 5000"
    ).fetchall()
    con.close()
    exported = []
    for r in rows:
        video_id = str(r["video_id"] or "")
        source_url = str(r["source_url"] or "")
        if ids and video_id not in ids and "booming_bulls" not in video_id.lower() and "Booming" not in source_url:
            continue
        exported.append({
            "source": "Booming Bulls",
            "video_id": video_id,
            "category": r["category"],
            "lesson_text": r["lesson_text"],
            "condition_text": r["condition_text"],
            "action_text": r["action_text"],
            "risk_text": r["risk_text"],
            "keywords": r["keywords"],
            "confidence_delta": r["confidence_delta"],
            "ml_usage": "knowledge_filter_not_supervised_win_loss",
        })
    with open(BOOMING_BULLS_DATASET_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["source", "video_id", "category", "lesson_text", "condition_text", "action_text", "risk_text", "keywords", "confidence_delta", "ml_usage"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(exported)
    return {"ok": True, "rows": len(exported), "dataset_file": BOOMING_BULLS_DATASET_FILE, "message": f"Exported {len(exported)} Booming Bulls knowledge rows to {BOOMING_BULLS_DATASET_FILE}"}


def booming_bulls_report() -> str:
    seed = _read_json(BOOMING_BULLS_SOURCE_FILE, {})
    videos = _read_json(BOOMING_BULLS_VIDEO_FILE, [])
    ids = _booming_video_ids()
    con = _connect()
    total_sources = con.execute(f"SELECT COUNT(*) AS n FROM {SOURCES_TABLE}").fetchone()["n"]
    total_lessons = con.execute(f"SELECT COUNT(*) AS n FROM {LESSONS_TABLE} WHERE active=1").fetchone()["n"]
    bb_lessons = 0
    if ids:
        placeholders = ",".join("?" for _ in ids)
        bb_lessons = con.execute(f"SELECT COUNT(*) AS n FROM {LESSONS_TABLE} WHERE active=1 AND video_id IN ({placeholders})", tuple(ids)).fetchone()["n"]
    manual_lessons = con.execute(f"SELECT COUNT(*) AS n FROM {LESSONS_TABLE} WHERE active=1 AND video_id LIKE '%booming_bulls%'").fetchone()["n"]
    con.close()
    lines = [
        "Booming Bulls Learning Status",
        f"Channel: {seed.get('channel_url') or BOOMING_BULLS_CHANNEL_URL}",
        f"Saved channel video URLs: {len(videos)}",
        f"Booming Bulls video lessons: {bb_lessons}",
        f"Booming Bulls manual-note lessons: {manual_lessons}",
        f"Total Blue video-learning sources: {total_sources}",
        f"Total active video-learning lessons: {total_lessons}",
        f"Knowledge dataset file: {BOOMING_BULLS_DATASET_FILE}",
    ]
    return "\n".join(lines)


def booming_bulls_help() -> str:
    return """Booming Bulls learning commands:

booming bulls seed
  Save @BoomingBulls as a channel learning source.

booming bulls fetch videos [limit]
  Optional: use yt-dlp to discover public video URLs from the channel.

booming bulls fetch forex videos [limit]
  Optional: discover only title-matched Forex/currency/gold videos from the channel.

booming bulls fetch transcripts [limit]
  Optional: use youtube-transcript-api to fetch public captions where available.

booming bulls import notes <path>
  Best/safest: write your own notes/summaries from videos and import them.

booming bulls export dataset
  Export learned lessons into datasets/booming_bulls_strategy_knowledge.csv.

booming bulls report
  Show channel, video and lesson counts.

Important: YouTube videos/courses are copyrighted. Blue stores source links and concise learned rules, not copied full transcripts. Use this as education/context only; supervised ML still needs real win/loss trade data from backtests or demo trades. For students/teens, keep this in paper/demo mode and do not use it for live-money trading."""
