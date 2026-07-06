"""Phase 15.16 Internet / Environment Learning Brain for Blue Forex Market AI.

Blue learns from the internet in a safe, human-like way:
1) observe public pages/RSS from trusted sources,
2) extract short market-study observations,
3) store them as memory,
4) use them as context only.

Important safety rule: internet memory can inform explanations and no-trade warnings,
but it never places orders by itself and never bypasses MT5/autopilot guardrails.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

try:
    from config import DATABASE_FILE
except Exception:  # pragma: no cover
    DATABASE_FILE = "blue_market_ai.db"

try:
    from config import (
        PHASE15_16_INTERNET_LEARNING_ENABLED,
        PHASE15_16_INTERNET_BACKGROUND_LEARN_ENABLED,
        PHASE15_16_INTERNET_MIN_HOURS_BETWEEN_RUNS,
        PHASE15_16_INTERNET_MAX_ITEMS_PER_SOURCE,
        PHASE15_16_INTERNET_REQUEST_TIMEOUT_SECONDS,
        PHASE15_16_INTERNET_ALLOW_UNTRUSTED_SOURCES,
    )
except Exception:  # pragma: no cover
    PHASE15_16_INTERNET_LEARNING_ENABLED = True
    PHASE15_16_INTERNET_BACKGROUND_LEARN_ENABLED = False
    PHASE15_16_INTERNET_MIN_HOURS_BETWEEN_RUNS = 6
    PHASE15_16_INTERNET_MAX_ITEMS_PER_SOURCE = 8
    PHASE15_16_INTERNET_REQUEST_TIMEOUT_SECONDS = 12
    PHASE15_16_INTERNET_ALLOW_UNTRUSTED_SOURCES = False

SOURCES_FILE = Path("knowledge/internet_sources.json")
MEMORY_FILE = Path("knowledge/internet_learning_memory.jsonl")
STATE_FILE = Path("phase15_16_internet_learning_state.json")
DATASET_FILE = Path("datasets/blue_internet_knowledge_dataset.csv")
REPORT_FILE = Path("reports/internet_learning_report.md")
USER_AGENT = "BlueForexMarketAI/15.16 safe learning research bot"

DEFAULT_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "DailyFX Market News RSS",
        "url": "https://www.dailyfx.com/feeds/market-news",
        "kind": "rss",
        "trusted": True,
        "enabled": True,
        "tags": ["forex", "macro", "market_news"],
    },
    {
        "name": "FXStreet News RSS",
        "url": "https://www.fxstreet.com/rss/news",
        "kind": "rss",
        "trusted": True,
        "enabled": True,
        "tags": ["forex", "macro", "market_news"],
    },
    {
        "name": "Yahoo Finance FX/Gold Headlines",
        "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=EURUSD=X,GBPUSD=X,JPY=X,GC=F,BTC-USD&region=US&lang=en-US",
        "kind": "rss",
        "trusted": True,
        "enabled": True,
        "tags": ["forex", "gold", "crypto", "headlines"],
    },
]

KEYWORD_TAGS = {
    "gold": ["gold", "xau", "xauusd", "bullion"],
    "silver": ["silver", "xag", "xagusd"],
    "eurusd": ["eurusd", "euro", "ecb", "eurozone"],
    "gbpusd": ["gbpusd", "pound", "sterling", "boe"],
    "usdjpy": ["usdjpy", "yen", "boj", "japan"],
    "btc": ["bitcoin", "btc", "crypto"],
    "usd": ["dollar", "usd", "dxy", "federal reserve", "fed", "powell"],
    "inflation": ["inflation", "cpi", "ppi", "prices"],
    "jobs": ["nfp", "nonfarm", "jobs", "payroll", "unemployment"],
    "rates": ["rate", "rates", "yield", "treasury", "bond"],
    "risk": ["risk-off", "risk off", "safe haven", "geopolitical", "war", "tariff"],
    "technical": ["support", "resistance", "breakout", "trend", "liquidity", "fvg", "order block"],
}


def _utc_now() -> datetime:
    return datetime.utcnow()


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _utc_now()).replace(microsecond=0).isoformat() + "Z"


def _safe_mkdirs() -> None:
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return default
    return default


def _write_json(path: Path, data: Any) -> None:
    _safe_mkdirs()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _load_state() -> Dict[str, Any]:
    state = _read_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("internet_learning_enabled", bool(PHASE15_16_INTERNET_LEARNING_ENABLED))
    state.setdefault("background_enabled", bool(PHASE15_16_INTERNET_BACKGROUND_LEARN_ENABLED))
    state.setdefault("last_run_at", None)
    state.setdefault("total_saved", 0)
    state.setdefault("last_message", "Internet learning has not run yet.")
    return state


def _save_state(**updates: Any) -> Dict[str, Any]:
    state = _load_state()
    state.update(updates)
    state["updated_at"] = _iso()
    _write_json(STATE_FILE, state)
    return state


def internet_learning_enabled() -> bool:
    return bool(_load_state().get("internet_learning_enabled", True))


def internet_background_enabled() -> bool:
    state = _load_state()
    return bool(state.get("internet_learning_enabled", True) and state.get("background_enabled", False))


def set_internet_learning(enabled: bool, background: Optional[bool] = None) -> str:
    updates: Dict[str, Any] = {"internet_learning_enabled": bool(enabled)}
    if background is not None:
        updates["background_enabled"] = bool(background)
    state = _save_state(**updates)
    mode = "ON" if state.get("internet_learning_enabled") else "OFF"
    bg = "ON" if state.get("background_enabled") else "OFF"
    return f"Internet Learning Brain is {mode}. Background internet learning is {bg}."


def load_sources() -> List[Dict[str, Any]]:
    _safe_mkdirs()
    data = _read_json(SOURCES_FILE, None)
    if not isinstance(data, list) or not data:
        _write_json(SOURCES_FILE, DEFAULT_SOURCES)
        return [dict(x) for x in DEFAULT_SOURCES]
    clean: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not item.get("url"):
            continue
        clean.append({
            "name": str(item.get("name") or item.get("url")),
            "url": str(item.get("url")),
            "kind": str(item.get("kind") or "auto"),
            "trusted": bool(item.get("trusted", False)),
            "enabled": bool(item.get("enabled", True)),
            "tags": list(item.get("tags") or []),
        })
    return clean


def save_sources(sources: List[Dict[str, Any]]) -> None:
    _write_json(SOURCES_FILE, sources)


def seed_default_internet_sources() -> Dict[str, Any]:
    existing = load_sources()
    urls = {x.get("url") for x in existing}
    added = 0
    for src in DEFAULT_SOURCES:
        if src["url"] not in urls:
            existing.append(dict(src))
            added += 1
    save_sources(existing)
    return {"ok": True, "added": added, "total": len(existing), "message": f"Internet sources ready. Added {added}; total {len(existing)}."}


def add_internet_source(url: str, name: str = "", trusted: bool = False, kind: str = "auto") -> Dict[str, Any]:
    url = (url or "").strip().strip('"').strip("'")
    if not re.match(r"^https?://", url, re.I):
        return {"ok": False, "message": "Use a full URL starting with https:// or http://"}
    sources = load_sources()
    for src in sources:
        if src.get("url") == url:
            src["enabled"] = True
            if name:
                src["name"] = name
            save_sources(sources)
            return {"ok": True, "message": "Source already existed; enabled it again."}
    sources.append({
        "name": name or url,
        "url": url,
        "kind": kind,
        "trusted": bool(trusted),
        "enabled": True,
        "tags": ["user_added"],
    })
    save_sources(sources)
    return {"ok": True, "message": f"Added internet source: {name or url}"}


def internet_sources_report() -> str:
    sources = load_sources()
    lines = ["Internet Learning Sources", ""]
    for i, src in enumerate(sources, start=1):
        status = "ON" if src.get("enabled", True) else "OFF"
        trust = "trusted" if src.get("trusted") else "untrusted/manual-review"
        lines.append(f"{i}. {src.get('name')} — {status}, {trust}")
        lines.append(f"   {src.get('url')}")
    if not sources:
        lines.append("No sources. Type: internet seed")
    return "\n".join(lines)


def internet_learning_help() -> str:
    return """Internet / Environment Learning Brain — Phase 15.16

What it does:
  - Reads trusted public market/news/study sources.
  - Extracts short observations like a human taking notes.
  - Stores notes in knowledge/internet_learning_memory.jsonl and SQLite.
  - Creates datasets/blue_internet_knowledge_dataset.csv for later study.
  - Shows what Blue learned in reports/internet_learning_report.md.

Safety rule:
  - Internet learning can support explanation, caution, and no-trade context.
  - It never places orders by itself and never bypasses autopilot/MT5 guardrails.

Commands:
  internet help             -> show this menu
  internet seed             -> add default trusted sources
  internet sources          -> show current sources
  internet add <url>        -> add a page/RSS source
  internet learn            -> collect and learn now
  environment learn         -> same as internet learn
  internet report           -> show latest learning memory summary
  baby brain                -> show human-like learning model
  internet on               -> enable internet learning + background internet mode
  internet off              -> disable internet learning
"""


def baby_brain_text() -> str:
    state = _load_state()
    return f"""Blue Baby-Brain Learning Model

1. See: read market environment from MT5 candles, news/calendar, internet sources, videos, journal, and backtests.
2. Notice: tag repeated concepts such as USD strength, inflation, rates, gold safe-haven demand, liquidity, trend, and risk mood.
3. Remember: save short notes with source, time, tags, and duplicate protection.
4. Practice: compare ideas with closed trades/backtests before trusting them.
5. Decide safely: internet memory can explain or warn, but cannot force a BUY/SELL order.

Current state:
  Internet learning: {'ON' if state.get('internet_learning_enabled') else 'OFF'}
  Background internet learning: {'ON' if state.get('background_enabled') else 'OFF'}
  Last run: {state.get('last_run_at') or 'never'}
  Total saved observations: {state.get('total_saved') or 0}
"""


def _clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _request(url: str) -> Tuple[Optional[str], str]:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8"},
            timeout=int(PHASE15_16_INTERNET_REQUEST_TIMEOUT_SECONDS or 12),
        )
        if resp.status_code >= 400:
            return None, f"HTTP {resp.status_code}"
        return resp.text, "ok"
    except Exception as exc:
        return None, str(exc)


def _looks_like_rss(text: str) -> bool:
    head = (text or "")[:500].lower()
    return "<rss" in head or "<feed" in head or "<channel" in head or "<item" in head or "<entry" in head


def _rss_items(text: str, limit: int) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    try:
        root = ET.fromstring(text.encode("utf-8"))
    except Exception:
        return items

    def local(tag: str) -> str:
        return tag.split("}", 1)[-1].lower()

    for node in root.iter():
        if local(node.tag) not in {"item", "entry"}:
            continue
        title = ""
        desc = ""
        link = ""
        published = ""
        for child in list(node):
            key = local(child.tag)
            val = _clean_text(child.text or "")
            if key == "title":
                title = val
            elif key in {"description", "summary", "content"} and not desc:
                desc = val
            elif key == "link" and not link:
                link = child.attrib.get("href") or val
            elif key in {"pubdate", "published", "updated"}:
                published = val
        if title:
            items.append({"title": title, "summary": desc, "url": link, "published": published})
        if len(items) >= limit:
            break
    return items


def _html_items(text: str, base_url: str, limit: int) -> List[Dict[str, str]]:
    soup = BeautifulSoup(text, "html.parser")
    for bad in soup(["script", "style", "noscript", "svg"]):
        bad.decompose()
    title = _clean_text(soup.title.get_text(" ") if soup.title else base_url)
    paragraphs = []
    for p in soup.find_all(["p", "h1", "h2", "h3", "li"]):
        txt = _clean_text(p.get_text(" "))
        if len(txt) >= 40:
            paragraphs.append(txt)
        if len(paragraphs) >= 8:
            break
    summary = " ".join(paragraphs)[:1600]
    if not title and not summary:
        return []
    return [{"title": title or base_url, "summary": summary, "url": base_url, "published": ""}][:limit]


def _tags_for_text(text: str) -> List[str]:
    lower = text.lower()
    tags = []
    for tag, words in KEYWORD_TAGS.items():
        if any(w in lower for w in words):
            tags.append(tag)
    if not tags:
        tags.append("general_market")
    return tags


def _observation_from_item(item: Dict[str, str], source: Dict[str, Any]) -> Dict[str, Any]:
    title = _clean_text(item.get("title", ""))[:220]
    summary = _clean_text(item.get("summary", ""))[:650]
    joined = (title + " " + summary).strip()
    tags = sorted(set(list(source.get("tags") or []) + _tags_for_text(joined)))
    confidence = "medium" if source.get("trusted") else "low"
    note = joined[:760]
    uid_raw = (source.get("url", "") + "|" + item.get("url", "") + "|" + title).encode("utf-8", "ignore")
    uid = hashlib.sha256(uid_raw).hexdigest()[:24]
    return {
        "id": uid,
        "created_at": _iso(),
        "source_name": source.get("name"),
        "source_url": source.get("url"),
        "item_url": item.get("url") or source.get("url"),
        "published": item.get("published") or "",
        "title": title,
        "observation": note,
        "tags": tags,
        "trusted": bool(source.get("trusted")),
        "confidence": confidence,
        "used_for_execution": False,
        "safety_note": "Context only. This internet observation cannot place or force trades.",
    }


def _existing_ids() -> set:
    ids = set()
    if MEMORY_FILE.exists():
        try:
            with MEMORY_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                        if row.get("id"):
                            ids.add(row["id"])
                    except Exception:
                        pass
        except Exception:
            pass
    try:
        con = sqlite3.connect(DATABASE_FILE)
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS internet_learning (id TEXT PRIMARY KEY, created_at TEXT, source_name TEXT, source_url TEXT, item_url TEXT, published TEXT, title TEXT, observation TEXT, tags TEXT, trusted INTEGER, confidence TEXT, used_for_execution INTEGER DEFAULT 0, safety_note TEXT)")
        for (uid,) in cur.execute("SELECT id FROM internet_learning").fetchall():
            ids.add(uid)
        con.close()
    except Exception:
        pass
    return ids


def _save_observations(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    _safe_mkdirs()
    existing = _existing_ids()
    new_rows = [r for r in rows if r.get("id") not in existing]
    if not new_rows:
        return 0
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        for row in new_rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    try:
        con = sqlite3.connect(DATABASE_FILE)
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS internet_learning (id TEXT PRIMARY KEY, created_at TEXT, source_name TEXT, source_url TEXT, item_url TEXT, published TEXT, title TEXT, observation TEXT, tags TEXT, trusted INTEGER, confidence TEXT, used_for_execution INTEGER DEFAULT 0, safety_note TEXT)")
        for row in new_rows:
            cur.execute(
                "INSERT OR IGNORE INTO internet_learning(id, created_at, source_name, source_url, item_url, published, title, observation, tags, trusted, confidence, used_for_execution, safety_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row.get("id"), row.get("created_at"), row.get("source_name"), row.get("source_url"), row.get("item_url"),
                    row.get("published"), row.get("title"), row.get("observation"), json.dumps(row.get("tags") or []),
                    1 if row.get("trusted") else 0, row.get("confidence"), 0, row.get("safety_note"),
                ),
            )
        con.commit(); con.close()
    except Exception:
        pass

    _export_dataset()
    return len(new_rows)


def _iter_memory(limit: int = 200) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if MEMORY_FILE.exists():
        try:
            with MEMORY_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass
    return rows[-limit:]


def _export_dataset() -> None:
    rows = _iter_memory(limit=5000)
    if not rows:
        return
    _safe_mkdirs()
    with DATASET_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["created_at", "source_name", "title", "observation", "tags", "trusted", "confidence", "used_for_execution", "safety_note"])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "created_at": r.get("created_at"),
                "source_name": r.get("source_name"),
                "title": r.get("title"),
                "observation": r.get("observation"),
                "tags": ",".join(r.get("tags") or []),
                "trusted": r.get("trusted"),
                "confidence": r.get("confidence"),
                "used_for_execution": False,
                "safety_note": r.get("safety_note"),
            })


def _write_report(latest_rows: List[Dict[str, Any]], errors: List[str]) -> None:
    all_rows = _iter_memory(limit=500)
    tag_counts: Dict[str, int] = {}
    for r in all_rows:
        for tag in r.get("tags") or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:12]

    lines = [
        "# Blue Internet / Environment Learning Report",
        "",
        f"Updated: {_iso()}",
        "",
        "## Safety",
        "Internet memory is context only. It cannot place orders, change SL/TP, bypass autopilot filters, or override broker guardrails.",
        "",
        "## Memory stats",
        f"Total saved observations: {len(all_rows)}",
        "Top tags: " + (", ".join(f"{k}({v})" for k, v in top_tags) if top_tags else "none yet"),
        "",
        "## Latest observations",
    ]
    for r in latest_rows[-20:]:
        lines.append(f"- **{r.get('title','Untitled')}** [{', '.join(r.get('tags') or [])}] — {r.get('observation','')[:260]}")
    if errors:
        lines.extend(["", "## Fetch warnings"])
        lines.extend([f"- {e}" for e in errors[:20]])
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def collect_internet_learning(limit_per_source: Optional[int] = None, force: bool = True) -> Dict[str, Any]:
    if not internet_learning_enabled():
        return {"ok": True, "ran": False, "saved": 0, "message": "Internet learning is OFF. Use: internet on"}
    limit = max(1, int(limit_per_source or PHASE15_16_INTERNET_MAX_ITEMS_PER_SOURCE or 8))
    sources = [s for s in load_sources() if s.get("enabled", True)]
    if not sources:
        return {"ok": False, "ran": False, "saved": 0, "message": "No enabled internet sources. Use: internet seed"}

    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    for src in sources:
        if not src.get("trusted") and not bool(PHASE15_16_INTERNET_ALLOW_UNTRUSTED_SOURCES):
            errors.append(f"Skipped untrusted source until manual review: {src.get('name')}")
            continue
        text, status = _request(src.get("url", ""))
        if not text:
            errors.append(f"{src.get('name')}: {status}")
            continue
        kind = str(src.get("kind") or "auto").lower()
        if kind == "rss" or (kind == "auto" and _looks_like_rss(text)):
            items = _rss_items(text, limit=limit)
        else:
            items = _html_items(text, src.get("url", ""), limit=limit)
        if not items:
            errors.append(f"{src.get('name')}: no readable items found")
            continue
        for item in items[:limit]:
            rows.append(_observation_from_item(item, src))

    saved = _save_observations(rows)
    state = _load_state()
    total_saved = int(state.get("total_saved") or 0) + int(saved)
    msg = f"Internet learning complete. New observations saved: {saved}. Sources checked: {len(sources)}."
    if errors:
        msg += f" Warnings: {len(errors)}."
    _save_state(last_run_at=_iso(), total_saved=total_saved, last_message=msg, last_errors=errors[-10:])
    _write_report(rows, errors)
    return {"ok": True, "ran": True, "saved": saved, "checked_sources": len(sources), "warnings": errors, "message": msg, "report_file": str(REPORT_FILE), "dataset_file": str(DATASET_FILE)}


def run_background_internet_learning_if_due() -> Dict[str, Any]:
    if not internet_background_enabled():
        return {"ok": True, "ran": False, "saved": 0, "message": "Background internet learning is OFF."}
    state = _load_state()
    last = state.get("last_run_at")
    min_hours = max(1, int(PHASE15_16_INTERNET_MIN_HOURS_BETWEEN_RUNS or 6))
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", ""))
            if _utc_now() - last_dt < timedelta(hours=min_hours):
                return {"ok": True, "ran": False, "saved": 0, "message": f"Internet learning not due yet. Minimum gap: {min_hours}h."}
        except Exception:
            pass
    return collect_internet_learning(force=False)


def internet_learning_report(max_items: int = 12) -> str:
    rows = _iter_memory(limit=300)
    state = _load_state()
    if not rows:
        return "Internet Learning Brain has no saved observations yet. Type: internet seed, then internet learn"
    tag_counts: Dict[str, int] = {}
    for r in rows:
        for tag in r.get("tags") or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = [
        "Internet Learning Brain Report",
        "",
        f"Internet learning: {'ON' if state.get('internet_learning_enabled') else 'OFF'}",
        f"Background internet learning: {'ON' if state.get('background_enabled') else 'OFF'}",
        f"Last run: {state.get('last_run_at') or 'never'}",
        f"Saved observations in memory: {len(rows)}",
        "Top memory tags: " + (", ".join(f"{k}({v})" for k, v in top_tags) if top_tags else "none"),
        "",
        "Latest observations:",
    ]
    for r in rows[-max_items:][::-1]:
        tags = ", ".join(r.get("tags") or [])
        title = r.get("title") or "Untitled"
        obs = (r.get("observation") or "")[:220]
        lines.append(f"- {title} [{tags}] — {obs}")
    lines.extend([
        "",
        "Files:",
        f"- Memory: {MEMORY_FILE}",
        f"- Dataset: {DATASET_FILE}",
        f"- Report: {REPORT_FILE}",
        "",
        "Execution safety: internet observations are context only, not automatic trade permission.",
    ])
    return "\n".join(lines)


def internet_context_for_symbol(symbol_text: str = "", max_items: int = 5) -> List[Dict[str, Any]]:
    """Return recent memory rows relevant to a symbol/context.

    This is intentionally read-only and can be used by future reason cards.
    """
    symbol_text = (symbol_text or "").lower()
    desired = set(_tags_for_text(symbol_text)) if symbol_text else set()
    rows = _iter_memory(limit=300)
    scored = []
    for r in rows:
        tags = set(r.get("tags") or [])
        score = len(tags & desired)
        if score or not desired:
            scored.append((score, r))
    scored.sort(key=lambda x: (x[0], x[1].get("created_at", "")), reverse=True)
    return [r for _, r in scored[:max_items]]
