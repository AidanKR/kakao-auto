"""SQLite 저장 + 중복 제거. Windows/Mac 어디서든 동작(순수 파이썬)."""
import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).with_name("kakao.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room        TEXT NOT NULL,
    sender      TEXT,
    sent_at     TEXT,             -- 카톡이 준 시간 문자열(예: '오후 2:31'). 없으면 NULL
    content     TEXT NOT NULL,
    hash        TEXT NOT NULL UNIQUE,   -- 중복 방지 키
    collected_at TEXT NOT NULL     -- 우리가 수집한 시각(ISO)
);
CREATE INDEX IF NOT EXISTS idx_room_date ON messages(room, collected_at);

CREATE TABLE IF NOT EXISTS rooms (
    room        TEXT PRIMARY KEY,
    first_seen  TEXT,             -- 이 방을 처음 발견한 시각
    last_seen   TEXT,             -- 마지막으로 본 시각
    msg_count   INTEGER DEFAULT 0 -- 누적 수집 메시지 수
);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def make_hash(room, sender, sent_at, content):
    """중복 판정 키. 방+보낸이+시간+내용이 모두 같으면 같은 메시지로 본다.
    카톡 시간(sent_at)이 있으면 'ㅋㅋ' 같은 반복도 시간이 달라 구분된다.
    시간이 없으면 동일 내용 반복은 1건으로 합쳐질 수 있음(한계)."""
    raw = f"{room}\x1f{sender}\x1f{sent_at}\x1f{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def touch_room(conn, room, iso, added=0):
    """방을 방문할 때마다 레지스트리 갱신. 처음 보는 방이면 True(=새 방) 반환."""
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
    """레지스트리의 모든 방: [(room, first_seen, last_seen, msg_count)] (최초발견 순)."""
    return conn.execute(
        "SELECT room, first_seen, last_seen, msg_count FROM rooms ORDER BY first_seen"
    ).fetchall()


def insert_many(conn, rows, collected_at):
    """rows: [{room, sender, sent_at, content}, ...]
    이미 있는 메시지는 무시(INSERT OR IGNORE). 신규 저장 건수를 반환."""
    new = 0
    cur = conn.cursor()
    for r in rows:
        h = make_hash(r["room"], r.get("sender"), r.get("sent_at"), r["content"])
        cur.execute(
            "INSERT OR IGNORE INTO messages(room, sender, sent_at, content, hash, collected_at)"
            " VALUES (?,?,?,?,?,?)",
            (r["room"], r.get("sender"), r.get("sent_at"), r["content"], h, collected_at),
        )
        new += cur.rowcount
    conn.commit()
    return new
