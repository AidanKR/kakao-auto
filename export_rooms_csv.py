"""
방별 CSV 내보내기 — 방 하나당 CSV 파일 하나. 메인서버에서 분석용.

DB(kakao.db)의 모든 메시지를 방별로 갈라 CSV로 저장한다(매 실행 전량 덮어쓰기).
출력(기본: share_dir/csv/ 아래):
    <방이름>.csv          ← 방 하나당 하나. 컬럼: room,date,time,datetime,sender,message
    _rooms_index.csv      ← 방 목록·파일명·건수·처음/마지막 시각(서버에서 훑기 좋게)

인코딩은 utf-8-sig(BOM) — 엑셀에서 한글 안 깨지고, pandas.read_csv 도 그대로 읽힘.
content 안의 쉼표·줄바꿈·따옴표는 csv 모듈이 표준 규칙으로 안전하게 처리한다.

사용:
    python export_rooms_csv.py             # share_dir/csv 로
    python export_rooms_csv.py --out DIR   # 다른 폴더로
"""
import argparse
import csv
import json
from pathlib import Path

import db

HERE = __import__("appdir").APP_DIR


def load_config():
    p = HERE / "config.json"
    if not p.exists():
        return {}
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return json.loads(data.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            try:
                return json.loads(data.decode(enc).replace("\\", "/"))
            except Exception:
                continue
    return {}


def safe_name(room):
    return "".join(c for c in room if c.isalnum() or c in " _-").strip() or "room"


def _unique(name, used):
    """서로 다른 방이 같은 파일명으로 뭉개지지 않게 _2, _3 붙임."""
    base, i, out = name, 2, name
    while out in used:
        out = f"{base}_{i}"
        i += 1
    used.add(out)
    return out


def export(conn, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_by_room = {}
    cur = conn.execute(
        "SELECT room, sent_date, sent_at, sender, content FROM messages "
        "ORDER BY room, sent_at, seq, id"
    )
    for room, sent_date, sent_at, sender, content in cur.fetchall():
        rows_by_room.setdefault(room, []).append((sent_date, sent_at, sender, content))

    used, index = set(), []
    for room, rows in rows_by_room.items():
        fname = _unique(safe_name(room), used) + ".csv"
        with (out_dir / fname).open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["room", "date", "time", "datetime", "sender", "message"])
            for sent_date, sent_at, sender, content in rows:
                t = sent_at[11:16] if sent_at and "T" in sent_at else ""
                w.writerow([room, sent_date or "", t, sent_at or "",
                            sender or "", content or ""])
        index.append((room, fname, len(rows),
                      rows[0][1] or "", rows[-1][1] or ""))

    with (out_dir / "_rooms_index.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["room", "file", "messages", "first", "last"])
        for r in sorted(index, key=lambda x: -x[2]):
            w.writerow(r)

    return len(index), sum(x[2] for x in index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="출력 폴더(기본: share_dir/csv)")
    args = ap.parse_args()

    cfg = load_config()
    if args.out:
        out_dir = Path(args.out).expanduser()
    else:
        share = Path(cfg.get("share_dir") or (HERE / "share")).expanduser()
        out_dir = share / "csv"

    conn = db.connect()
    try:
        n_rooms, total = export(conn, out_dir)
    finally:
        conn.close()
    print(f"방별 CSV 내보내기 완료: 방 {n_rooms}개 / 메시지 {total}건 → {out_dir}")


if __name__ == "__main__":
    main()
