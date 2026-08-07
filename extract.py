"""
금액·약속·계좌 자동 추출 — 카톡 주문/정산을 손으로 옮겨 적는 시간을 줄인다.

정규식 기반(LLM 없음, 오프라인):
  - 금액 : 50,000원 / 5만원 / 3억 / ₩120000 등
  - 약속 : 내일 3시 / 오후 2시 / 8월 5일 (+ 미팅·방문 등 키워드) 등 날짜·시간
  - 계좌 : 은행명+번호 / 123-456-7890 형태

출력: share_dir/_daily/추출_금액약속.csv  (엑셀에서 바로 열림, BOM 포함)
     유형, 매칭값, 방, 시각, 보낸이, 원문

사용: python extract.py            (전체)
      python extract.py --days 30  (최근 30일)
"""
import argparse
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

import db
import briefing

HERE = Path(__file__).parent

MONEY = re.compile(
    r"(₩\s*\d[\d,]*"                       # ₩120000
    r"|\d{1,3}(?:,\d{3})+\s*원?"            # 50,000 / 50,000원
    r"|\d+\s*억(?:\s*\d+\s*만)?\s*원?"       # 3억 / 3억 5000만
    r"|\d+\s*만\s*원?"                      # 5만원 / 5만
    r"|\d{4,}\s*원)"                        # 50000원
)
ACCOUNT = re.compile(
    r"((?:신한|국민|우리|하나|농협|기업|카카오뱅크|카카오|토스|SC제일|씨티|부산|대구|경남|광주|수협|새마을|우체국)"
    r"\s*[:\s]*\d[\d\-\s]{5,}"
    r"|\b\d{2,6}-\d{2,6}-\d{2,7}\b)"
)
TIME = re.compile(r"(오전|오후)?\s*\d{1,2}\s*시(?:\s*(?:반|\d{1,2}\s*분))?")
DATE = re.compile(r"(\d{1,2}\s*월\s*\d{1,2}\s*일|\d{1,2}\s*/\s*\d{1,2}|오늘|내일|모레|글피|다음\s*주|이번\s*주)")
APPT_KW = ("미팅", "회의", "방문", "약속", "뵙", "오시", "일정", "출발", "도착", "픽업", "수령", "납품", "예약")


def clip(s, n=140):
    return (s or "").replace("\n", " ").strip()[:n]


def find_appt(text):
    t = TIME.search(text)
    d = DATE.search(text)
    if t:
        return (t.group(0) + (" " + d.group(0) if d else "")).strip()
    if d and any(k in text for k in APPT_KW):
        return d.group(0)
    return None


def extract(conn, since_date):
    rows = conn.execute(
        "SELECT sent_at, room, sender, content FROM messages "
        + ("WHERE sent_date>=? " if since_date else "")
        + "ORDER BY sent_at DESC",
        (since_date,) if since_date else (),
    ).fetchall()
    out = []
    for sa, room, sender, content in rows:
        c = content or ""
        seen = set()
        for m in MONEY.findall(c):
            v = m.strip()
            if v and ("금액", v) not in seen:
                seen.add(("금액", v)); out.append(["금액", v, room, sa, sender or "", clip(c)])
        for m in ACCOUNT.findall(c):
            v = m.strip()
            if len(re.sub(r"\D", "", v)) >= 6 and ("계좌", v) not in seen:
                seen.add(("계좌", v)); out.append(["계좌", v, room, sa, sender or "", clip(c)])
        ap = find_appt(c)
        if ap:
            out.append(["약속", ap, room, sa, sender or "", clip(c)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="최근 N일만")
    ap.add_argument("--out", help="출력 CSV 경로")
    args = ap.parse_args()

    cfg = briefing.load_config()
    since = None
    if args.days:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    conn = db.connect()
    data = extract(conn, since)
    conn.close()

    if args.out:
        out = Path(args.out)
    else:
        base = Path(cfg.get("share_dir") or (HERE / "share")).expanduser() / "_daily"
        base.mkdir(parents=True, exist_ok=True)
        out = base / "추출_금액약속.csv"

    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["유형", "매칭값", "방", "시각", "보낸이", "원문"])
        for r in data:
            r = list(r)
            r[3] = (r[3] or "")[:16].replace("T", " ")
            w.writerow(r)

    n = {"금액": 0, "약속": 0, "계좌": 0}
    for r in data:
        n[r[0]] = n.get(r[0], 0) + 1
    print(f"추출 완료: {out}")
    print(f"  금액 {n['금액']} · 약속 {n['약속']} · 계좌 {n['계좌']} (총 {len(data)}건)")


if __name__ == "__main__":
    main()
