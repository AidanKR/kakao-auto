"""
정리(공유) 도구 — 하루 2번(11:50, 23:50) 스케줄러가 실행.

DB(kakao.db)를 공유폴더(share_dir)에 **실제 메시지 날짜(sent_date)별·방별 TXT**로 정리한다.
기본은 '증분': 지난 정리 이후 새로 수집된 메시지가 속한 날짜만 다시 쓴다(구글드라이브 동기화 최소화).
--all 이면 모든 날짜를 재생성(초기 백필용).

출력(share_dir 아래):
    2026-07-07/ _전체.txt, 방이름.txt ...
    rooms_seen.txt, kakao.db(copy_db)

사용:
    python consolidate.py            # 증분(새 메시지 있는 날짜만)
    python consolidate.py --all      # 전체 날짜 재생성
    python consolidate.py --date 2026-07-06
"""
import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import db

HERE = Path(__file__).parent


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


def line(sent_at, sender, content):
    # sent_at ISO 'YYYY-MM-DDThh:mm:00' -> 'hh:mm' 만 보기 좋게
    t = sent_at[11:16] if sent_at and "T" in sent_at else (sent_at or "")
    head = " ".join(x for x in (t, sender or "") if x)
    return f"[{head}] {content}" if head else content


def dates_to_rebuild(conn, since_iso, do_all):
    """재생성할 sent_date 목록. do_all이면 전체, 아니면 since 이후 수집분이 속한 날짜만."""
    if do_all or not since_iso:
        rows = conn.execute(
            "SELECT DISTINCT sent_date FROM messages WHERE sent_date!='' ORDER BY sent_date"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT DISTINCT sent_date FROM messages "
            "WHERE sent_date!='' AND collected_at > ? ORDER BY sent_date",
            (since_iso,),
        ).fetchall()
    return [r[0] for r in rows if r[0]]


def fetch_day(conn, day):
    """sent_date=day 인 메시지를 방별로: {room: [(sent_at, sender, content)]} (시간순)."""
    cur = conn.execute(
        "SELECT room, sent_at, sender, content FROM messages "
        "WHERE sent_date=? ORDER BY room, sent_at, seq, id",
        (day,),
    )
    grouped = {}
    for room, sent_at, sender, content in cur.fetchall():
        grouped.setdefault(room, []).append((sent_at, sender, content))
    return grouped


def write_day(share_dir, day, grouped, stamp):
    day_dir = share_dir / day
    day_dir.mkdir(parents=True, exist_ok=True)
    all_lines = [f"# {day} 카카오톡 정리 (마지막 갱신 {stamp})", ""]
    for room, msgs in grouped.items():
        room_path = day_dir / f"{safe_name(room)}.txt"
        with room_path.open("w", encoding="utf-8") as f:
            f.write(f"# {room} — {day} ({len(msgs)}건, 갱신 {stamp})\n\n")
            for m in msgs:
                f.write(line(*m) + "\n")
        all_lines.append(f"===== {room} ({len(msgs)}건) =====")
        all_lines += [line(*m) for m in msgs]
        all_lines.append("")
    (day_dir / "_전체.txt").write_text("\n".join(all_lines), encoding="utf-8")
    return sum(len(v) for v in grouped.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="특정 날짜만 재생성 YYYY-MM-DD")
    ap.add_argument("--all", action="store_true", help="모든 날짜 재생성(초기 백필)")
    args = ap.parse_args()

    cfg = load_config()
    share_dir = Path(cfg.get("share_dir") or (HERE / "share")).expanduser()
    try:
        share_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[오류] 공유폴더 생성 실패: {share_dir}\n  {e}")
        return

    conn = db.connect()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    run_start = datetime.now().isoformat(timespec="seconds")

    if args.date:
        days = [args.date]
    else:
        since = db.get_meta(conn, "last_consolidate")
        days = dates_to_rebuild(conn, since, args.all)

    if not days:
        print("새로 정리할 메시지가 없습니다.")
    else:
        total = 0
        for day in days:
            grouped = fetch_day(conn, day)
            if grouped:
                total += write_day(share_dir, day, grouped, stamp)
        print(f"정리 완료: 날짜 {len(days)}개 / 총 {total}건 → {share_dir}")

    # 전체 방 목록 항상 최신본
    try:
        rooms = db.all_rooms(conn)
        lines = [f"# 전체 방 목록 ({len(rooms)}개, 갱신 {stamp})",
                 "# 방이름\t최초발견\t마지막\t누적건수", ""]
        for room, first, last, cnt in rooms:
            lines.append(f"{room}\t{first}\t{last}\t{cnt}")
        (share_dir / "rooms_seen.txt").write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        print(f"  (rooms_seen.txt 실패, 무시: {e})")

    # 증분 기준점 갱신(--date/--all 아닌 일반 실행에서만)
    if not args.date and not args.all:
        db.set_meta(conn, "last_consolidate", run_start)

    if cfg.get("copy_db", True):
        try:
            shutil.copy2(db.DB_PATH, share_dir / "kakao.db")
        except Exception as e:
            print(f"  (DB 사본 복사 실패, 무시: {e})")

    conn.close()


if __name__ == "__main__":
    main()
