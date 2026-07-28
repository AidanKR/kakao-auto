"""
정리(공유) 도구 — 하루 2번(11:50, 23:50) 스케줄러가 실행.

DB(kakao.db)에 쌓인 메시지를 공유폴더(share_dir)에 날짜별·방별 TXT로 정리한다.
매 실행마다 '그 날' 파일을 최신 상태로 다시 쓰므로(덮어쓰기) 여러 번 돌려도 안전.

출력 구조(share_dir 아래):
    2026-07-07/
        _전체.txt                (그날 전체 방 합본)
        방이름A.txt
        방이름B.txt
    kakao.db                     (copy_db=true 면 DB 사본도 함께 — 다른 PC에서 조회용)

사용:
    python consolidate.py                 # 오늘 날짜 정리
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
        except UnicodeDecodeError:
            continue
    return json.loads(data.decode("utf-8", errors="replace"))


def safe_name(room):
    return "".join(c for c in room if c.isalnum() or c in " _-").strip() or "room"


def fetch_day(day):
    """collected_at 이 해당 날짜인 메시지를 방별로 묶어서 반환: {room: [(sent_at, sender, content)]}"""
    conn = sqlite3.connect(db.DB_PATH)
    cur = conn.execute(
        "SELECT room, sent_at, sender, content FROM messages "
        "WHERE substr(collected_at,1,10)=? ORDER BY room, id",
        (day,),
    )
    grouped = {}
    for room, sent_at, sender, content in cur.fetchall():
        grouped.setdefault(room, []).append((sent_at, sender, content))
    conn.close()
    return grouped


def line(sent_at, sender, content):
    head = " ".join(x for x in (sent_at or "", sender or "") if x)
    return f"[{head}] {content}" if head else content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (기본: 오늘)")
    args = ap.parse_args()
    day = args.date or datetime.now().strftime("%Y-%m-%d")

    cfg = load_config()
    share_dir = Path(cfg.get("share_dir") or (HERE / "share")).expanduser()

    grouped = fetch_day(day)
    if not grouped:
        print(f"{day} 에 수집된 메시지가 없습니다.")
        return

    day_dir = share_dir / day
    try:
        day_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[오류] 공유폴더를 만들 수 없습니다: {share_dir}\n  {e}")
        print("  config.json 의 share_dir 경로(네트워크/공유 폴더)를 확인하세요.")
        return

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_lines = [f"# {day} 카카오톡 정리 (마지막 갱신 {stamp})", ""]

    for room, msgs in grouped.items():
        # 방별 파일
        room_path = day_dir / f"{safe_name(room)}.txt"
        with room_path.open("w", encoding="utf-8") as f:
            f.write(f"# {room} — {day} ({len(msgs)}건, 갱신 {stamp})\n\n")
            for m in msgs:
                f.write(line(*m) + "\n")
        # 합본용
        all_lines.append(f"===== {room} ({len(msgs)}건) =====")
        all_lines += [line(*m) for m in msgs]
        all_lines.append("")

    (day_dir / "_전체.txt").write_text("\n".join(all_lines), encoding="utf-8")

    # 전체 방 목록(레지스트리) — 새 방 포함, 공유폴더 루트에 항상 최신본
    try:
        conn = sqlite3.connect(db.DB_PATH)
        rooms = db.all_rooms(conn)
        conn.close()
        lines = [f"# 전체 방 목록 ({len(rooms)}개, 갱신 {stamp})", "# 방이름\t최초발견\t마지막\t누적건수", ""]
        for room, first, last, cnt in rooms:
            lines.append(f"{room}\t{first}\t{last}\t{cnt}")
        (share_dir / "rooms_seen.txt").write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        print(f"  (rooms_seen.txt 작성 실패, 무시: {e})")

    if cfg.get("copy_db", True):
        try:
            shutil.copy2(db.DB_PATH, share_dir / "kakao.db")
        except Exception as e:
            print(f"  (DB 사본 복사 실패, 무시: {e})")

    total = sum(len(v) for v in grouped.values())
    print(f"정리 완료: {day}  방 {len(grouped)}개 / 총 {total}건 → {day_dir}")


if __name__ == "__main__":
    main()
