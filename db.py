"""SQLite 저장 + 중복 제거 + 시간 정규화(v2). Windows/Mac 어디서든 동작(순수 파이썬).

v2 변경점:
- sent_at 을 정렬가능한 ISO('YYYY-MM-DDTHH:MM:00')로 정규화(오전/오후 → 24시).
- sent_date('YYYY-MM-DD') 컬럼 추가 → 정리를 '실제 메시지 날짜' 기준으로.
- seq 컬럼 추가 → 같은 분 동일 보낸이/내용도 순번으로 구분(중복 오병합 방지).
- 기존 v1 DB는 connect() 시 자동 마이그레이션(유실 없음).
"""
import sqlite3
import hashlib
import re
from pathlib import Path

DB_PATH = __import__("appdir").APP_DIR / "kakao.db"

_MESSAGES_V2 = """
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    room         TEXT NOT NULL,
    sender       TEXT,
    sent_at      TEXT,             -- ISO 'YYYY-MM-DDTHH:MM:00' (정규화). 파싱실패시 원문
    sent_date    TEXT,             -- 'YYYY-MM-DD' (정리 그룹핑용)
    seq          INTEGER DEFAULT 0,-- 동일(방,시각,보낸이,내용) 내 순번
    content      TEXT NOT NULL,
    hash         TEXT NOT NULL UNIQUE,
    collected_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_msg_sentdate ON messages(sent_date);
CREATE INDEX IF NOT EXISTS idx_msg_room ON messages(room, sent_at);
"""

SCHEMA = _MESSAGES_V2 + """
CREATE TABLE IF NOT EXISTS rooms (
    room        TEXT PRIMARY KEY,
    first_seen  TEXT,
    last_seen   TEXT,
    msg_count   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

_LEGACY_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(오전|오후)\s+(\d{1,2}):(\d{2})$")


# ── 시간 정규화 ──────────────────────────────────────────
def ampm_to_24(ampm, hh):
    hh = int(hh)
    if ampm == "오전":
        return 0 if hh == 12 else hh
    return 12 if hh == 12 else hh + 12          # 오후


def normalize_time(date_str, ampm, hh, mi):
    """(YYYY-MM-DD, 오전/오후, hh, mi) -> (ISO, date)."""
    h24 = ampm_to_24(ampm, hh)
    return f"{date_str}T{h24:02d}:{int(mi):02d}:00", date_str


def parse_legacy_sent_at(s):
    """옛 'YYYY-MM-DD 오전 3:01' -> (iso, date). 실패시 원문 유지."""
    if not s:
        return "", ""
    m = _LEGACY_RE.match(s.strip())
    if m:
        y, mo, d, ampm, hh, mi = m.groups()
        return normalize_time(f"{y}-{mo}-{d}", ampm, hh, mi)
    if "T" in s:                                 # 이미 ISO
        return s, s[:10]
    return s, (s[:10] if len(s) >= 10 else "")


def make_hash(room, sender, sent_at, seq, content):
    raw = f"{room}\x1f{sender}\x1f{sent_at}\x1f{seq}\x1f{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── 연결 + 마이그레이션 ─────────────────────────────────
def _migrate_if_needed(conn):
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
    ).fetchone()
    if not exists:
        return
    cols = [r[1] for r in cur.execute("PRAGMA table_info(messages)").fetchall()]
    if "seq" in cols:
        return                                   # 이미 v2
    print("[db] 기존 데이터를 새 형식(ISO시간/날짜/순번)으로 마이그레이션 중...")
    cur.execute("ALTER TABLE messages RENAME TO messages_old")
    cur.executescript(_MESSAGES_V2)
    counter = {}
    rows = cur.execute(
        "SELECT room, sender, sent_at, content, collected_at FROM messages_old ORDER BY id"
    ).fetchall()
    ins = conn.cursor()
    for room, sender, sent_at_old, content, collected_at in rows:
        iso, date = parse_legacy_sent_at(sent_at_old or "")
        key = (room, sender, iso, content)
        seq = counter.get(key, 0)
        counter[key] = seq + 1
        h = make_hash(room, sender, iso, seq, content)
        ins.execute(
            "INSERT OR IGNORE INTO messages"
            "(room, sender, sent_at, sent_date, seq, content, hash, collected_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (room, sender, iso, date, seq, content, h, collected_at),
        )
    cur.execute("DROP TABLE messages_old")
    conn.commit()
    print(f"[db] 마이그레이션 완료: {len(rows)}행 변환")


def connect():
    conn = sqlite3.connect(DB_PATH)
    _migrate_if_needed(conn)
    conn.executescript(SCHEMA)
    return conn


# ── meta ─────────────────────────────────────────────────
def get_meta(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()


# ── 방 레지스트리 ───────────────────────────────────────
def touch_room(conn, room, iso, added=0):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM rooms WHERE room=?", (room,))
    is_new = cur.fetchone() is None
    if is_new:
        cur.execute(
            "INSERT INTO rooms(room, first_seen, last_seen, msg_count) VALUES (?,?,?,?)",
            (room, iso, iso, added),
        )
    else:
        cur.execute(
            "UPDATE rooms SET last_seen=?, msg_count=msg_count+? WHERE room=?",
            (iso, added, room),
        )
    conn.commit()
    return is_new


def room_count(conn):
    row = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()
    return row[0] if row else 0


def all_rooms(conn):
    return conn.execute(
        "SELECT room, first_seen, last_seen, msg_count FROM rooms ORDER BY first_seen"
    ).fetchall()


# ── 메시지 저장 ─────────────────────────────────────────
def insert_many(conn, rows, collected_at):
    """rows: [{room, sender, sent_at(ISO), sent_date, seq, content}, ...]
    이미 있는 메시지는 무시(INSERT OR IGNORE). 신규 저장 건수 반환."""
    new = 0
    cur = conn.cursor()
    for r in rows:
        h = make_hash(r["room"], r.get("sender"), r.get("sent_at"), r.get("seq", 0), r["content"])
        cur.execute(
            "INSERT OR IGNORE INTO messages"
            "(room, sender, sent_at, sent_date, seq, content, hash, collected_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (r["room"], r.get("sender"), r.get("sent_at"), r.get("sent_date"),
             r.get("seq", 0), r["content"], h, collected_at),
        )
        new += cur.rowcount
    conn.commit()
    return new
