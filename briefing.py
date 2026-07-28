"""
AI 일일 브리핑 + '내가 답할 것' 감지 — ③가치 계층.

1) 규칙 기반(AI 키 없어도 작동): 방마다 마지막 메시지가 '내가 아닌 사람'이면 = 응답 대기.
   질문 여부·미답 시간·연속 메시지 수를 계산해 우선순위로 정렬 → 응답대기_날짜.txt
2) AI(키 있으면): 위 목록 + 활동요약을 LLM에 넘겨
   - 회사 상황 요약
   - 우선순위 응답 목록(요지·추천 행동)
   - 상위 건 '응답 초안'  (⚠ 자동발송 안 함. 사람이 확인 후 복붙)
   → _daily/브리핑_날짜.md

사용: python briefing.py            (오늘 기준)
      python briefing.py --days 7
"""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import db
import llm

HERE = Path(__file__).parent

QUESTION_HINTS = [
    "?", "？", "문의", "언제", "얼마", "가능", "될까", "되나요", "인가요", "나요",
    "해주", "부탁", "확인", "견적", "재고", "배송", "환불", "교환", "주문", "가격",
    "일정", "회신", "답변", "연락", "가능한가",
]


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


def my_names(cfg, conn):
    names = cfg.get("my_names") or []
    if names:
        return set(names)
    # 추론: 가장 많은 방에 등장하는 보낸이 = 계정 주인일 가능성 높음
    row = conn.execute(
        "SELECT sender, COUNT(DISTINCT room) c FROM messages "
        "WHERE sender IS NOT NULL AND sender!='' GROUP BY sender ORDER BY c DESC LIMIT 1"
    ).fetchone()
    if row:
        print(f"[briefing] my_names 미설정 → '{row[0]}'(방 {row[1]}개 등장)로 추정. config에 명시 권장.")
        return {row[0]}
    return set()


def is_question(text):
    return any(k in text for k in QUESTION_HINTS)


def age_hours(sent_at, now):
    try:
        return round((now - datetime.fromisoformat(sent_at)).total_seconds() / 3600.0, 1)
    except Exception:
        return None


def triage(conn, cfg, me, now):
    """응답 대기 방 목록(우선순위 정렬)."""
    lookback = cfg.get("briefing_lookback_days", 14)
    since_date = (now - timedelta(days=lookback)).strftime("%Y-%m-%d")
    rooms = [r[0] for r in conn.execute(
        "SELECT DISTINCT room FROM messages WHERE sent_date >= ?", (since_date,)
    ).fetchall()]

    pending = []
    for room in rooms:
        msgs = conn.execute(
            "SELECT sent_at, sender, content FROM messages WHERE room=? "
            "ORDER BY sent_at DESC, seq DESC, id DESC LIMIT 40", (room,)
        ).fetchall()
        if not msgs:
            continue
        last_at, last_sender, _ = msgs[0]
        if last_sender in me:
            continue                       # 내가 마지막 → 이미 응답함
        # 내 메시지 나오기 전까지 상대 연속 메시지(burst)
        burst = []
        for sa, snd, ct in msgs:
            if snd in me:
                break
            burst.append((sa, snd, ct))
        burst.reverse()                    # 시간순
        q = any(is_question(ct) for _, _, ct in burst)
        pending.append({
            "room": room,
            "last_at": last_at,
            "age_h": age_hours(last_at, now),
            "count": len(burst),
            "question": q,
            "burst": burst,
        })

    min_age = cfg.get("response_wait_hours", 0)
    pending = [p for p in pending if (p["age_h"] is None or p["age_h"] >= min_age)]
    # 정렬: 질문 우선 → 오래 기다린 순
    pending.sort(key=lambda p: (0 if p["question"] else 1, -(p["age_h"] or 0)))
    return pending


def write_pending_txt(share_dir, day, pending, stamp):
    d = share_dir / "_daily"
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"# 응답 대기 목록 — {day} (갱신 {stamp}) : {len(pending)}건", ""]
    for i, p in enumerate(pending, 1):
        q = "❓질문" if p["question"] else "  "
        age = f"{p['age_h']}h" if p["age_h"] is not None else "?"
        last = p["burst"][-1][2].replace("\n", " ")[:60] if p["burst"] else ""
        lines.append(f"{i:>2}. [{q}] {p['room']}  (미답 {age}, 연속 {p['count']}건)")
        lines.append(f"     ↳ {last}")
    (d / f"응답대기_{day}.txt").write_text("\n".join(lines), encoding="utf-8")
    return d


def build_ai_digest(pending, top=20):
    """LLM에 넘길 요약 텍스트(토큰 절약 위해 상위 top개, 각 방 최근 몇 줄)."""
    out = []
    for i, p in enumerate(pending[:top], 1):
        out.append(f"[{i}] 방: {p['room']} | 미답 {p['age_h']}h | 질문:{'예' if p['question'] else '아니오'}")
        for sa, snd, ct in p["burst"][-4:]:
            t = sa[11:16] if sa and "T" in sa else sa
            out.append(f"    {t} {snd}: {ct.strip()[:120]}")
    return "\n".join(out)


AI_SYSTEM = (
    "너는 한국 중소기업 대표의 업무 비서다. 카카오톡 업무 대화 요약을 받아, "
    "대표가 오늘 무엇을 챙겨야 하는지 한국어로 간결·실무적으로 정리한다. "
    "과장 없이, 확실치 않으면 추정임을 밝혀라."
)


def ai_briefing(cfg, day, pending, stats):
    digest = build_ai_digest(pending)
    user = (
        f"오늘({day}) 카카오톡 업무 현황이다.\n"
        f"- 응답 대기 방: {len(pending)}개 (질문 포함 {sum(1 for p in pending if p['question'])}개)\n"
        f"- 최근 신규 메시지: {stats.get('recent_msgs','?')}건\n\n"
        f"[응답 대기 상세]\n{digest}\n\n"
        "다음 형식(마크다운)으로 작성하라:\n"
        "## 1. 오늘 상황 요약 (3~5줄)\n"
        "## 2. 먼저 답할 것 (우선순위, 방이름 · 요지 · 추천 행동)\n"
        "## 3. 응답 초안 (상위 3~5건, 방이름 + 바로 보낼 수 있는 답변 초안)\n"
        "초안은 그대로 복붙 가능하게. 단, 확인이 필요한 값(금액·일정 등)은 [확인] 표시."
    )
    return llm.call(cfg, AI_SYSTEM, user, max_tokens=2000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="조회 기간(일). 기본은 config briefing_lookback_days")
    args = ap.parse_args()

    cfg = load_config()
    if args.days:
        cfg["briefing_lookback_days"] = args.days
    share_dir = Path(cfg.get("share_dir") or (HERE / "share")).expanduser()

    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y-%m-%d %H:%M")

    conn = db.connect()
    me = my_names(cfg, conn)
    pending = triage(conn, cfg, me, now)

    recent = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE collected_at >= ?",
        ((now - timedelta(days=1)).isoformat(timespec="seconds"),)
    ).fetchone()[0]

    d = write_pending_txt(share_dir, day, pending, stamp)
    print(f"[briefing] 응답 대기 {len(pending)}건 → {d/('응답대기_'+day+'.txt')}")

    # AI 브리핑(키 있으면)
    if cfg.get("ai_provider"):
        text = ai_briefing(cfg, day, pending, {"recent_msgs": recent})
        if text:
            (d / f"브리핑_{day}.md").write_text(
                f"# 카카오톡 일일 브리핑 — {day} (갱신 {stamp})\n\n{text}\n", encoding="utf-8")
            print(f"[briefing] AI 브리핑 작성 → {d/('브리핑_'+day+'.md')}")
    else:
        print("[briefing] ai_provider 미설정 → 규칙기반 응답대기 목록만 생성(AI 요약/초안 생략)")

    conn.close()


if __name__ == "__main__":
    main()
