"""
(옵션) 수집된 대화를 GPT로 요약. Windows/Mac 어디서든 실행 가능.

사용법:
    set OPENAI_API_KEY=sk-...        (Windows)
    python summarize.py --room "방이름" --date 2026-07-07
    python summarize.py --room "방이름" --days 7      # 최근 7일

요약 없이 그냥 뽑기만:
    python summarize.py --room "방이름" --date 2026-07-07 --raw
"""
import argparse
import os
import sqlite3
from datetime import datetime, timedelta

import db


def fetch(room, since_iso):
    conn = sqlite3.connect(db.DB_PATH)
    cur = conn.execute(
        "SELECT sent_at, sender, content FROM messages "
        "WHERE room=? AND collected_at>=? ORDER BY id",
        (room, since_iso),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def as_text(rows):
    out = []
    for sent_at, sender, content in rows:
        head = " ".join(x for x in (sent_at or "", sender or "") if x)
        out.append(f"[{head}] {content}" if head else content)
    return "\n".join(out)


def summarize(text, room):
    try:
        from openai import OpenAI
    except ImportError:
        print("openai 미설치.  pip install openai   또는  --raw 로 원문만 출력하세요.")
        return None
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 환경변수가 없습니다.")
        return None
    client = OpenAI()
    prompt = (
        f"다음은 카카오톡 대화방 '{room}' 의 대화 로그다. "
        "핵심 요약, 결정된 사항, 해야 할 일(담당자 포함), 미해결 질문을 한국어로 정리해라.\n\n"
        f"{text}"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", required=True)
    ap.add_argument("--date", help="YYYY-MM-DD (하루)")
    ap.add_argument("--days", type=int, help="최근 N일")
    ap.add_argument("--raw", action="store_true", help="요약 없이 원문만")
    args = ap.parse_args()

    if args.date:
        since = datetime.strptime(args.date, "%Y-%m-%d").isoformat(timespec="seconds")
    elif args.days:
        since = (datetime.now() - timedelta(days=args.days)).isoformat(timespec="seconds")
    else:
        since = datetime.now().strftime("%Y-%m-%d") + "T00:00:00"

    rows = fetch(args.room, since)
    if not rows:
        print("해당 조건의 메시지가 없습니다.")
        return

    text = as_text(rows)
    if args.raw:
        print(text)
        return

    result = summarize(text, args.room)
    if result:
        print(result)


if __name__ == "__main__":
    main()
