"""Phase 12 Video/Strategy Knowledge Learning for Blue Forex Market AI.

Blue cannot truly learn from a YouTube URL alone. This module stores video links,
imports user-provided transcripts/notes, extracts concise trading lessons, and
applies those lessons as a lightweight knowledge filter during signal reasoning.

Safety design:
- Stores lesson summaries/rules, not full copied transcripts.
- Never forces a BUY/SELL by itself.
- Can add caution, reduce confidence, or add small context confidence when a
  learned lesson matches the current signal.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

try:
    from config import DATABASE_FILE
except Exception:  # pragma: no cover
    DATABASE_FILE = "blue_market_ai.db"

KNOWLEDGE_DIR = "knowledge"
TRANSCRIPT_DIR = os.path.join(KNOWLEDGE_DIR, "transcripts")
DEFAULT_SOURCES_FILE = os.path.join(KNOWLEDGE_DIR, "video_sources.json")
VIDEO_NOTES_TEMPLATE = os.path.join(KNOWLEDGE_DIR, "video_notes_template.md")
SOURCES_TABLE = "video_knowledge_sources"
LESSONS_TABLE = "video_knowledge_lessons"

DEFAULT_VIDEO_URLS = [
    "https://www.youtube.com/watch?v=jwjjWHzEaJc&t=188s",
    "https://www.youtube.com/watch?v=4_33Wsc9fcg&t=1167s",
    "https://www.youtube.com/watch?v=46wLDbl2_d0&t=521s&pp=0gcJCT8LAYcqIYzv",
    "https://www.youtube.com/watch?v=qEMhYlT6gwk&t=2996s",
    "https://www.youtube.com/watch?v=zCj2SWbpmOk&t=469s",
    "https://www.youtube.com/watch?v=A1LOTQ0R8ww&t=3418s",
    "https://www.youtube.com/watch?v=ZGRXswei3kI&t=2490s",
    "https://www.youtube.com/watch?v=omZpI1DbYRI&t=1363s",
    "https://www.youtube.com/watch?v=4vRHblHQWvA&t=3763s",
    "https://www.youtube.com/watch?v=CK5jXz_io38&t=159s",
    "https://www.youtube.com/watch?v=0zmD8iYhvpc&t=6081s",
]

CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "market_context": [
        "trend", "bias", "structure", "range", "sideways", "consolidation", "session",
        "london", "new york", "asia", "volatility", "dxy", "dollar", "correlation",
        "higher timeframe", "multi timeframe", "market structure", "premium", "discount",
    ],
    "entry_trigger": [
        "entry", "trigger", "confirmation", "retest", "break", "breakout", "pullback",
        "liquidity sweep", "sweep", "choch", "bos", "fvg", "fair value", "order block",
        "imbalance", "displacement", "breaker", "mitigation", "turtle soup",
    ],
    "no_trade": [
        "avoid", "don't trade", "do not trade", "no trade", "skip", "wait", "choppy",
        "messy", "low volume", "spread", "high impact", "news", "fakeout", "trap",
        "late entry", "overextended", "unclear",
    ],
    "risk_management": [
        "risk", "stop loss", "sl", "take profit", "tp", "target", "rr", "risk reward",
        "breakeven", "partial", "trail", "lot", "position size", "drawdown", "daily loss",
    ],
    "psychology": [
        "patience", "discipline", "emotion", "revenge", "overtrade", "over trading",
        "fear", "greed", "plan", "rules", "journal", "review",
    ],
}

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "your", "you", "are", "but",
    "not", "when", "then", "than", "have", "has", "had", "was", "were", "will", "can", "could",
    "should", "would", "there", "their", "they", "them", "just", "only", "very", "also", "more",
}


def _ensure_dirs() -> None:
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_dirs()
    con = sqlite3.connect(DATABASE_FILE)
    con.row_factory = sqlite3.Row
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SOURCES_TABLE}(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            video_id TEXT,
            start_seconds INTEGER DEFAULT 0,
            title TEXT,
            status TEXT DEFAULT 'source_only',
            transcript_path TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {LESSONS_TABLE}(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT,
            video_id TEXT,
            category TEXT,
            lesson_text TEXT,
            condition_text TEXT,
            action_text TEXT,
            risk_text TEXT,
            keywords TEXT,
            confidence_delta REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    con.commit()
    return con


def _seconds_from_t(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip().lower()
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    total = 0
    for amount, unit in re.findall(r"(\d+)([hms])", text):
        n = int(amount)
        if unit == "h":
            total += n * 3600
        elif unit == "m":
            total += n * 60
        else:
            total += n
    return total


def parse_video_url(url_or_id: str) -> Dict[str, Any]:
    text = (url_or_id or "").strip()
    if not text:
        return {"video_id": "", "url": "", "start_seconds": 0}
    if "youtube" not in text and "youtu.be" not in text and re.match(r"^[A-Za-z0-9_-]{8,20}$", text):
        return {"video_id": text, "url": f"https://www.youtube.com/watch?v={text}", "start_seconds": 0}
    parsed = urlparse(text)
    qs = parse_qs(parsed.query)
    video_id = ""
    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/").split("/")[0]
    elif "youtube" in parsed.netloc:
        video_id = (qs.get("v") or [""])[0]
    start = 0
    if "t" in qs:
        start = _seconds_from_t(qs.get("t", [0])[0])
    elif "start" in qs:
        start = _seconds_from_t(qs.get("start", [0])[0])
    clean_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else text
    if video_id and start:
        clean_url += f"&t={start}s"
    return {"video_id": video_id, "url": clean_url, "start_seconds": start}


def _load_default_sources() -> List[Dict[str, Any]]:
    if os.path.exists(DEFAULT_SOURCES_FILE):
        try:
            with open(DEFAULT_SOURCES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    sources = []
    for i, url in enumerate(DEFAULT_VIDEO_URLS, start=1):
        parsed = parse_video_url(url)
        parsed.update({"title": f"User strategy video {i:02d}", "status": "source_only"})
        sources.append(parsed)
    return sources


def seed_default_video_sources() -> Dict[str, Any]:
    con = _connect()
    now = datetime.utcnow().isoformat()
    added = 0
    updated = 0
    for source in _load_default_sources():
        parsed = parse_video_url(source.get("url") or source.get("video_id") or "")
        url = parsed.get("url") or source.get("url")
        video_id = parsed.get("video_id") or source.get("video_id") or ""
        start = int(parsed.get("start_seconds") or source.get("start_seconds") or 0)
        title = source.get("title") or f"YouTube strategy video {video_id}"
        cur = con.execute(f"SELECT id FROM {SOURCES_TABLE} WHERE url=? OR video_id=?", (url, video_id)).fetchone()
        if cur:
            con.execute(
                f"UPDATE {SOURCES_TABLE} SET start_seconds=?, title=COALESCE(NULLIF(title,''),?), updated_at=? WHERE id=?",
                (start, title, now, cur["id"]),
            )
            updated += 1
        else:
            con.execute(
                f"INSERT INTO {SOURCES_TABLE}(url, video_id, start_seconds, title, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                (url, video_id, start, title, "source_only", now, now),
            )
            added += 1
    con.commit(); con.close()
    return {"ok": True, "added": added, "updated": updated, "total": added + updated}


def add_video_source(url: str, title: str = "") -> Dict[str, Any]:
    parsed = parse_video_url(url)
    if not parsed.get("video_id"):
        return {"ok": False, "message": "Could not read video id from the URL."}
    con = _connect(); now = datetime.utcnow().isoformat()
    con.execute(
        f"INSERT OR IGNORE INTO {SOURCES_TABLE}(url, video_id, start_seconds, title, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
        (parsed["url"], parsed["video_id"], parsed["start_seconds"], title or f"YouTube strategy video {parsed['video_id']}", "source_only", now, now),
    )
    con.execute(f"UPDATE {SOURCES_TABLE} SET updated_at=? WHERE video_id=?", (now, parsed["video_id"]))
    con.commit(); con.close()
    return {"ok": True, "message": f"Video source saved: {parsed['video_id']}", **parsed}


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_csv_text(path: str) -> str:
    parts: List[str] = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "text" in row:
                parts.append(str(row.get("text") or ""))
            elif "lesson" in row:
                parts.append(str(row.get("lesson") or ""))
            else:
                parts.append(" ".join(str(v) for v in row.values() if v))
    return "\n".join(parts)


def _read_learning_text(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _read_csv_text(path)
    return _read_text_file(path)


def _clean_sentence(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" \t\n\r-•*0123456789.:")
    return s.strip()


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\[[^\]]{0,80}\]", " ", text)
    text = re.sub(r"\([^)]{0,40}\)", " ", text)
    raw = re.split(r"(?:\n+|(?<=[.!?])\s+|[•;])", text)
    out: List[str] = []
    for item in raw:
        s = _clean_sentence(item)
        if 25 <= len(s) <= 280:
            out.append(s)
    return out


def _category_for_sentence(sentence: str) -> Tuple[str, List[str]]:
    lower = sentence.lower()
    scores: Dict[str, int] = {}
    found: List[str] = []
    for category, words in CATEGORY_KEYWORDS.items():
        score = 0
        for w in words:
            if w in lower:
                score += 2 if " " in w else 1
                found.append(w)
        scores[category] = score
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "", []
    # Keep compact keywords only.
    compact = []
    for w in found:
        if w not in compact and len(compact) < 12:
            compact.append(w)
    return best, compact


def _extra_keywords(sentence: str, existing: Iterable[str]) -> List[str]:
    lower = sentence.lower()
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{3,}", lower) if w not in STOPWORDS]
    keywords = list(existing)
    for w in words:
        if w not in keywords:
            keywords.append(w)
        if len(keywords) >= 16:
            break
    return keywords


def _lesson_action(category: str, sentence: str) -> str:
    lower = sentence.lower()
    if category == "no_trade":
        return "Add caution or skip the setup when these conditions appear."
    if category == "risk_management":
        return "Check risk, RR, stop-loss placement and trade management before entry."
    if category == "entry_trigger":
        return "Use as an extra confluence check; do not enter until Blue's normal signal also agrees."
    if category == "market_context":
        return "Use to understand market condition before deciding BUY/SELL/WAIT."
    if category == "psychology":
        return "Use as a discipline reminder; never chase or revenge trade."
    if "wait" in lower or "skip" in lower:
        return "Prefer WAIT until the condition is clean."
    return "Use as supporting context, not as a standalone trade signal."


def _risk_text(category: str, sentence: str) -> str:
    lower = sentence.lower()
    if category == "no_trade" or any(w in lower for w in ["avoid", "skip", "news", "spread", "choppy", "messy"]):
        return "No-trade filter may reduce confidence or block weak setups."
    if category == "risk_management":
        return "Risk rule may affect lot size, SL/TP review, breakeven, partial close, or daily-loss discipline."
    return "Knowledge rule is advisory and must pass Blue's risk engine."


def extract_lessons_from_text(text: str, source_url: str = "", video_id: str = "") -> List[Dict[str, Any]]:
    lessons: List[Dict[str, Any]] = []
    seen = set()
    for sentence in _split_sentences(text):
        category, found = _category_for_sentence(sentence)
        if not category:
            continue
        norm = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
        if norm in seen:
            continue
        seen.add(norm)
        keywords = _extra_keywords(sentence, found)
        delta = 0.0
        if category == "no_trade":
            delta = -2.0
        elif category in {"entry_trigger", "market_context"}:
            delta = 1.0
        lesson = {
            "source_url": source_url,
            "video_id": video_id,
            "category": category,
            "lesson_text": sentence[:260],
            "condition_text": sentence[:220],
            "action_text": _lesson_action(category, sentence),
            "risk_text": _risk_text(category, sentence),
            "keywords": ",".join(keywords),
            "confidence_delta": delta,
        }
        lessons.append(lesson)
        if len(lessons) >= 300:
            break
    return lessons


def _save_lessons(lessons: List[Dict[str, Any]], video_id: str = "", source_url: str = "", replace_for_source: bool = True) -> int:
    con = _connect(); now = datetime.utcnow().isoformat()
    if replace_for_source and (video_id or source_url):
        con.execute(f"DELETE FROM {LESSONS_TABLE} WHERE video_id=? OR source_url=?", (video_id, source_url))
    for l in lessons:
        con.execute(
            f"""
            INSERT INTO {LESSONS_TABLE}
            (source_url, video_id, category, lesson_text, condition_text, action_text, risk_text, keywords, confidence_delta, active, created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                l.get("source_url") or source_url,
                l.get("video_id") or video_id,
                l.get("category"),
                l.get("lesson_text"),
                l.get("condition_text"),
                l.get("action_text"),
                l.get("risk_text"),
                l.get("keywords"),
                float(l.get("confidence_delta") or 0),
                1,
                now,
            ),
        )
    if video_id or source_url:
        con.execute(
            f"UPDATE {SOURCES_TABLE} SET status='learned_rules_ready', updated_at=? WHERE video_id=? OR url=?",
            (now, video_id, source_url),
        )
    con.commit(); con.close()
    return len(lessons)


def import_video_transcript(video_ref: str, path: str) -> Dict[str, Any]:
    seed_default_video_sources()
    parsed = parse_video_url(video_ref)
    video_id = parsed.get("video_id") or video_ref.strip()
    source_url = parsed.get("url") or f"manual:{video_id}"
    text = _read_learning_text(path)
    lessons = extract_lessons_from_text(text, source_url=source_url, video_id=video_id)
    saved = _save_lessons(lessons, video_id=video_id, source_url=source_url, replace_for_source=True)
    con = _connect(); now = datetime.utcnow().isoformat()
    con.execute(
        f"INSERT OR IGNORE INTO {SOURCES_TABLE}(url, video_id, start_seconds, title, status, transcript_path, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (source_url, video_id, parsed.get("start_seconds", 0), f"YouTube strategy video {video_id}", "learned_rules_ready", path, now, now),
    )
    con.execute(f"UPDATE {SOURCES_TABLE} SET transcript_path=?, status='learned_rules_ready', updated_at=? WHERE video_id=?", (path, now, video_id))
    con.commit(); con.close()
    return {
        "ok": True,
        "video_id": video_id,
        "source_url": source_url,
        "source_file": path,
        "lessons_saved": saved,
        "message": f"Imported {saved} strategy lessons from {path} for video {video_id}.",
    }


def import_video_notes(path: str, source_name: str = "manual_notes") -> Dict[str, Any]:
    text = _read_learning_text(path)
    video_id = source_name.replace(" ", "_")[:80] or "manual_notes"
    source_url = f"manual:{video_id}"
    lessons = extract_lessons_from_text(text, source_url=source_url, video_id=video_id)
    saved = _save_lessons(lessons, video_id=video_id, source_url=source_url, replace_for_source=True)
    return {"ok": True, "source_file": path, "lessons_saved": saved, "message": f"Imported {saved} lessons from notes file {path}."}


def try_fetch_public_transcript(video_ref: str, languages: Optional[List[str]] = None) -> Dict[str, Any]:
    """Try to fetch public captions if youtube_transcript_api is installed.

    This is optional. It can fail if captions are disabled, unavailable, or the API
    package is not installed. It does not download video/audio.
    """
    parsed = parse_video_url(video_ref)
    video_id = parsed.get("video_id")
    if not video_id:
        return {"ok": False, "message": "Could not read video id from that URL."}
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    except Exception:
        return {
            "ok": False,
            "message": "youtube-transcript-api is not installed. Install optional package or paste transcript/notes manually.",
        }
    try:
        langs = languages or ["en", "en-US", "hi"]
        rows = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
        text = "\n".join(str(r.get("text") or "") for r in rows)
        _ensure_dirs()
        out_path = os.path.join(TRANSCRIPT_DIR, f"{video_id}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        imported = import_video_transcript(video_id, out_path)
        imported["transcript_file"] = out_path
        return imported
    except Exception as e:
        return {"ok": False, "message": f"Could not fetch public transcript for {video_id}: {str(e)[:220]}"}


def fetch_all_public_transcripts(limit: int = 50) -> Dict[str, Any]:
    """Try to fetch public captions for all saved YouTube sources.

    This batch command is a convenience for the user's 11 video-source dataset. It
    may partially succeed depending on which videos expose public captions.
    """
    seed_default_video_sources()
    con = _connect()
    rows = con.execute(
        f"SELECT url, video_id FROM {SOURCES_TABLE} WHERE video_id IS NOT NULL AND video_id != '' ORDER BY id ASC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()
    results = []
    ok_count = 0
    fail_count = 0
    lessons_total = 0
    for row in rows:
        ref = row["url"] or row["video_id"]
        res = try_fetch_public_transcript(ref)
        results.append({"video_id": row["video_id"], "ok": bool(res.get("ok")), "message": res.get("message")})
        if res.get("ok"):
            ok_count += 1
            lessons_total += int(res.get("lessons_saved") or 0)
        else:
            fail_count += 1
    return {
        "ok": ok_count > 0,
        "attempted": len(rows),
        "success": ok_count,
        "failed": fail_count,
        "lessons_saved": lessons_total,
        "results": results,
        "message": f"Tried {len(rows)} videos: {ok_count} transcript(s) imported, {fail_count} failed, {lessons_total} lessons saved.",
    }


def video_sources_report(limit: int = 30) -> str:
    seed_default_video_sources()
    con = _connect()
    rows = con.execute(
        f"""
        SELECT s.*, COUNT(l.id) as lesson_count
        FROM {SOURCES_TABLE} s
        LEFT JOIN {LESSONS_TABLE} l ON (l.video_id=s.video_id OR l.source_url=s.url) AND l.active=1
        GROUP BY s.id
        ORDER BY s.id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    con.close()
    lines = ["Phase 12 Video Knowledge Sources"]
    for r in rows:
        t = f"t={r['start_seconds']}s" if int(r["start_seconds"] or 0) else "t=0s"
        lines.append(f"- {r['video_id'] or 'manual'} | {t} | lessons={r['lesson_count']} | {r['status']} | {r['url']}")
    return "\n".join(lines)


def _lesson_counts() -> Dict[str, int]:
    con = _connect()
    total = int(con.execute(f"SELECT COUNT(*) FROM {LESSONS_TABLE} WHERE active=1").fetchone()[0])
    by_cat = {row["category"]: int(row["c"]) for row in con.execute(f"SELECT category, COUNT(*) c FROM {LESSONS_TABLE} WHERE active=1 GROUP BY category").fetchall()}
    sources = int(con.execute(f"SELECT COUNT(*) FROM {SOURCES_TABLE}").fetchone()[0])
    learned = int(con.execute(f"SELECT COUNT(DISTINCT video_id) FROM {LESSONS_TABLE} WHERE active=1 AND video_id IS NOT NULL AND video_id != ''").fetchone()[0])
    con.close()
    return {"total_lessons": total, "sources": sources, "learned_sources": learned, **{f"cat_{k}": v for k, v in by_cat.items()}}


def video_learning_report() -> str:
    seed_default_video_sources()
    counts = _lesson_counts()
    cats = []
    for name in ["market_context", "entry_trigger", "no_trade", "risk_management", "psychology"]:
        cats.append(f"{name}: {counts.get('cat_' + name, 0)}")
    return (
        "Phase 12 Video/Strategy Knowledge Report\n"
        f"Stored video/manual sources : {counts.get('sources', 0)}\n"
        f"Sources with learned lessons: {counts.get('learned_sources', 0)}\n"
        f"Active lessons/rules        : {counts.get('total_lessons', 0)}\n"
        f"Categories                 : {', '.join(cats)}\n"
        f"Notes template             : {VIDEO_NOTES_TEMPLATE}\n"
        "Behavior                   : adds context/caution to signals; never forces live entries.\n"
    )


def _load_lessons(limit: int = 600) -> List[Dict[str, Any]]:
    con = _connect()
    rows = con.execute(
        f"SELECT * FROM {LESSONS_TABLE} WHERE active=1 ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def _match_lesson_score(lesson: Dict[str, Any], context: str) -> int:
    score = 0
    kws = [k.strip().lower() for k in str(lesson.get("keywords") or "").split(",") if k.strip()]
    for k in kws:
        if k and k in context:
            score += 2 if " " in k else 1
    cat = str(lesson.get("category") or "")
    if cat == "no_trade" and any(w in context for w in ["choppy", "sideways", "spread", "news", "low volume", "unclear", "wait"]):
        score += 3
    if cat == "entry_trigger" and any(w in context for w in ["sweep", "liquidity", "fvg", "order block", "breakout", "retest"]):
        score += 3
    if cat == "risk_management" and any(w in context for w in ["risk", "stop", "target", "rr", "lot", "breakeven"]):
        score += 2
    return score


def apply_video_knowledge(signal: Dict[str, Any]) -> Dict[str, Any]:
    lessons = _load_lessons()
    engine: Dict[str, Any] = {
        "available": bool(lessons),
        "lessons_loaded": len(lessons),
        "matches": [],
        "confidence_delta": 0,
        "decision": "NO_VIDEO_RULES" if not lessons else "NO_MATCH",
        "note": "No video/notes lessons imported yet." if not lessons else "Video knowledge loaded but no strong matching lesson found.",
    }
    if not lessons:
        signal["video_knowledge_engine"] = engine
        return signal

    parts = [
        str(signal.get("symbol") or ""),
        str(signal.get("ticker") or ""),
        str(signal.get("action") or ""),
        str(signal.get("regime") or ""),
        str(signal.get("trade_style") or ""),
        str(signal.get("analyst_reason") or ""),
        str(signal.get("human_read") or ""),
        json.dumps(signal.get("market_context") or {}, default=str),
        json.dumps(signal.get("macro_brain") or {}, default=str),
        json.dumps(signal.get("dataset_ml_engine") or {}, default=str),
    ]
    context = " ".join(parts).lower()
    scored = []
    for l in lessons:
        score = _match_lesson_score(l, context)
        if score > 0:
            scored.append((score, l))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]
    if top:
        matches = []
        total_delta = 0.0
        caution = False
        for score, lesson in top:
            cat = str(lesson.get("category") or "")
            delta = float(lesson.get("confidence_delta") or 0)
            # Keep video rules advisory. Total impact is intentionally small.
            if cat == "no_trade":
                caution = True
            total_delta += delta
            matches.append({
                "score": score,
                "category": cat,
                "lesson": str(lesson.get("lesson_text") or "")[:180],
                "action_text": lesson.get("action_text"),
            })
        total_delta = max(-5.0, min(3.0, total_delta))
        old = float(signal.get("confidence") or 50)
        new_conf = int(max(0, min(95, round(old + total_delta))))
        signal["confidence"] = new_conf
        engine.update({
            "matches": matches,
            "confidence_delta": total_delta,
            "old_confidence": old,
            "new_confidence": new_conf,
            "decision": "CAUTION" if caution else "SUPPORTING_CONTEXT",
            "note": f"Matched {len(matches)} learned video/notes rule(s). Confidence adjusted {old}% -> {new_conf}%.",
        })
        if caution and str(signal.get("action") or "WAIT").upper() in {"BUY", "SELL"} and new_conf < 85:
            signal["action_before_video_knowledge"] = signal.get("action")
            signal["action"] = "WAIT"
            engine["decision"] = "BLOCKED_BY_VIDEO_NO_TRADE_CAUTION"
            engine["note"] += " Action changed to WAIT because confidence stayed below 85 after caution rules."
        lesson_texts = "; ".join(m["lesson"] for m in matches[:2])
        add = f" Video knowledge check: {engine['decision']} — {lesson_texts}"
        signal["analyst_reason"] = (str(signal.get("analyst_reason") or "") + add).strip()
        signal["human_read"] = (str(signal.get("human_read") or "") + add).strip()
    signal["video_knowledge_engine"] = engine
    return signal


def video_learning_help() -> str:
    return (
        "Phase 12 Video/Strategy Knowledge Commands\n"
        "1) Save the 11 YouTube sources:       video seed sources\n"
        "2) Show saved links:                  video sources\n"
        "3) Check learning status:             video knowledge report\n"
        "4) Add one YouTube link:              video add source <youtube_url>\n"
        "5) Import transcript/notes for video: video import transcript <youtube_url_or_id> <path/to/transcript.txt>\n"
        "6) Import manual notes file:          video import notes <path/to/notes.md>\n"
        "7) Try public captions if installed:  video fetch transcript <youtube_url_or_id>\n"
        "8) Try all saved public captions:      video fetch all transcripts\n\n"
        "Best path: copy your own notes or an allowed transcript into knowledge/transcripts/video1.txt, then import it.\n"
        "Blue stores extracted rules/lesson summaries, not full copied video content.\n"
    )
