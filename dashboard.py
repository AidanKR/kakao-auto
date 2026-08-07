"""
대시보드 생성기 — 열자마자 '오늘 상황'이 3초 안에 들어오는 한 장 HTML.

구성:
  1) 지표 카드   : 오늘 메시지 / 응답 대기 / 활동한 방 / 조용해진 방
  2) 먼저 답할 것 : 응답 대기 목록(질문·미답시간 우선) — briefing 규칙 재사용
  3) 활동 히트맵  : 방별 최근 14일 (진할수록 활발)
  4) 조용해진 방  : N일 이상 소식 없는 방 (놓친 관계 잡기)

전부 서버(파이썬)에서 그려 넣는 정적 HTML — JS·외부 라이브러리·CDN 없음.
LLM·외부 전송 없음(전부 로컬). ⚠ 대화 일부가 HTML에 포함되니 비공개로 다루세요.

사용: python dashboard.py            (share_dir/_daily/대시보드.html)
      python dashboard.py --out x.html
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import db
import briefing

HERE = __import__("appdir").APP_DIR


def esc(s):
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def clip(s, n=70):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def days_since(iso, now):
    try:
        return (now - datetime.fromisoformat(iso)).days
    except Exception:
        return None


CSS = """
*{box-sizing:border-box}
body{margin:0;padding:28px 22px 48px;background:#f7f7f5;color:#1a1a19;
  font-family:system-ui,"Malgun Gothic","Apple SD Gothic Neo",sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:21px;font-weight:600;margin:0 0 2px}
.sub{font-size:13px;color:#77766f;margin:0 0 24px}
h2{font-size:14px;font-weight:600;color:#52514e;margin:28px 0 10px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.card{background:#fff;border:1px solid #e6e5df;border-radius:12px;padding:16px 18px}
.card .lab{font-size:13px;color:#77766f;margin-bottom:7px}
.card .val{font-size:30px;font-weight:600;line-height:1.1;letter-spacing:-.02em}
.card .val small{font-size:14px;font-weight:400;color:#9a9992}
.red{color:#c62f2f} .amber{color:#b57200} .green{color:#2f7d32}
.box{background:#fff;border:1px solid #e6e5df;border-radius:12px;overflow:hidden}
.row{display:flex;align-items:center;gap:12px;padding:13px 16px;border-bottom:1px solid #f0efea}
.row:last-child{border-bottom:none}
.row .body{flex:1;min-width:0}
.row .name{font-size:14.5px;font-weight:500}
.row .prev{font-size:12.5px;color:#77766f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
.row .age{font-size:12.5px;white-space:nowrap;font-variant-numeric:tabular-nums}
.tag{font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px;white-space:nowrap}
.tag.q{background:#fbe9e9;color:#a32626} .tag.n{background:#eeede8;color:#6a6961}
.empty{padding:18px 16px;font-size:13.5px;color:#77766f}
table.hm{border-collapse:separate;border-spacing:3px;width:100%}
table.hm td.rn{font-size:12.5px;color:#52514e;white-space:nowrap;width:150px;
  max-width:150px;overflow:hidden;text-overflow:ellipsis;padding-right:6px}
table.hm td.c{height:20px;border-radius:3px}
.hmfoot{display:flex;justify-content:space-between;font-size:11.5px;color:#9a9992;margin-top:6px}
.legend{display:flex;align-items:center;gap:5px;font-size:11.5px;color:#77766f;margin-bottom:8px}
.legend i{width:16px;height:12px;border-radius:2px;display:inline-block}
"""


def cell_color(v, vmax):
    if v <= 0:
        return "#eeede8"
    a = 0.18 + 0.82 * (v / vmax if vmax else 1) ** 0.65
    return f"rgba(42,120,214,{round(a, 2)})"


def build(conn, cfg, now):
    today = now.strftime("%Y-%m-%d")
    quiet_days = cfg.get("quiet_days", 7)
    hm_days = cfg.get("dash_heatmap_days", 14)
    hm_rooms = cfg.get("dash_heatmap_rooms", 12)
    top_pending = cfg.get("dash_pending_top", 8)

    # 1) 지표
    msgs_today = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE sent_date=?", (today,)).fetchone()[0]
    rooms_today = conn.execute(
        "SELECT COUNT(DISTINCT room) FROM messages WHERE sent_date=?", (today,)).fetchone()[0]
    rooms_total = conn.execute("SELECT COUNT(DISTINCT room) FROM messages").fetchone()[0]

    me = briefing.my_names(cfg, conn)
    pending = briefing.triage(conn, cfg, me, now)

    # 조용해진 방
    last_rows = conn.execute(
        "SELECT room, MAX(sent_at) FROM messages GROUP BY room").fetchall()
    quiet = []
    for room, last in last_rows:
        d = days_since(last, now)
        if d is not None and d >= quiet_days:
            quiet.append((room, d, last))
    quiet.sort(key=lambda x: -x[1])

    # 히트맵
    dates = [(now - timedelta(days=i)).strftime("%Y-%m-%d")
             for i in range(hm_days - 1, -1, -1)]
    since = dates[0]
    grid = {}
    for room, sd, c in conn.execute(
        "SELECT room, sent_date, COUNT(*) FROM messages WHERE sent_date>=? "
        "GROUP BY room, sent_date", (since,)
    ).fetchall():
        grid.setdefault(room, {})[sd] = c
    ranked = sorted(grid.items(), key=lambda kv: -sum(kv[1].values()))[:hm_rooms]
    vmax = max((v for _, d in ranked for v in d.values()), default=1)

    return {
        "today": today, "msgs_today": msgs_today,
        "rooms_today": rooms_today, "rooms_total": rooms_total,
        "pending": pending[:top_pending], "pending_all": len(pending),
        "quiet": quiet, "quiet_days": quiet_days,
        "dates": dates, "ranked": ranked, "vmax": vmax,
    }


def render(d, now):
    stamp = now.strftime("%Y-%m-%d %H:%M")
    urgent = sum(1 for p in d["pending"] if p["question"])

    h = ['<!doctype html><html lang="ko"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>카카오톡 대시보드</title><style>", CSS, "</style></head><body><div class='wrap'>"]

    h.append(f"<h1>오늘 상황</h1><p class='sub'>{d['today']} · 갱신 {stamp}</p>")

    # 지표 카드
    pend_cls = " class='val red'" if d["pending_all"] else " class='val'"
    quiet_cls = " class='val amber'" if d["quiet"] else " class='val'"
    h.append("<div class='cards'>")
    h.append(f"<div class='card'><div class='lab'>오늘 메시지</div><div class='val'>{d['msgs_today']:,}</div></div>")
    h.append(f"<div class='card'><div class='lab'>응답 대기</div><div{pend_cls}>{d['pending_all']}</div></div>")
    h.append(f"<div class='card'><div class='lab'>활동한 방</div><div class='val'>{d['rooms_today']}"
             f" <small>/ {d['rooms_total']}</small></div></div>")
    h.append(f"<div class='card'><div class='lab'>조용해진 방</div><div{quiet_cls}>{len(d['quiet'])}</div></div>")
    h.append("</div>")

    # 먼저 답할 것
    h.append(f"<h2>먼저 답할 것 <span style='font-weight:400;color:#9a9992'>· 질문 {urgent}건</span></h2>")
    h.append("<div class='box'>")
    if not d["pending"]:
        h.append("<div class='empty'>모두 응답했습니다.</div>")
    for p in d["pending"]:
        last = p["burst"][-1][2] if p["burst"] else ""
        age = p["age_h"]
        agetxt = f"{int(age)}시간" if age is not None and age < 48 else (
            f"{int(age // 24)}일" if age is not None else "-")
        cls = "red" if (p["question"] and (age or 0) >= 3) else ("amber" if p["question"] else "")
        tag = "<span class='tag q'>질문</span>" if p["question"] else "<span class='tag n'>대기</span>"
        h.append(
            f"<div class='row'>{tag}<div class='body'><div class='name'>{esc(p['room'])}</div>"
            f"<div class='prev'>{esc(clip(last))}</div></div>"
            f"<div class='age {cls}'>{agetxt}</div></div>")
    h.append("</div>")

    # 히트맵
    h.append(f"<h2>최근 {len(d['dates'])}일 활동</h2>")
    h.append("<div class='legend'>적음 <i style='background:#eeede8'></i>"
             "<i style='background:rgba(42,120,214,.35)'></i>"
             "<i style='background:rgba(42,120,214,.65)'></i>"
             "<i style='background:rgba(42,120,214,1)'></i> 많음</div>")
    h.append("<div class='box' style='padding:14px 16px'>")
    if not d["ranked"]:
        h.append("<div class='empty' style='padding:4px 0'>표시할 활동이 없습니다.</div>")
    else:
        h.append("<table class='hm'>")
        for room, cnts in d["ranked"]:
            h.append(f"<tr><td class='rn' title='{esc(room)}'>{esc(room)}</td>")
            for dt in d["dates"]:
                v = cnts.get(dt, 0)
                h.append(f"<td class='c' style='background:{cell_color(v, d['vmax'])}'"
                         f" title='{dt} · {v}건'></td>")
            h.append("</tr>")
        h.append("</table>")
        h.append(f"<div class='hmfoot'><span>{d['dates'][0][5:].replace('-', '/')}</span>"
                 f"<span>오늘</span></div>")
    h.append("</div>")

    # 조용해진 방
    h.append(f"<h2>조용해진 방 <span style='font-weight:400;color:#9a9992'>"
             f"· {d['quiet_days']}일 이상</span></h2>")
    h.append("<div class='box'>")
    if not d["quiet"]:
        h.append("<div class='empty'>모든 방이 최근에 활동했습니다.</div>")
    for room, days, last in d["quiet"][:12]:
        h.append(f"<div class='row'><div class='body'><div class='name'>{esc(room)}</div>"
                 f"<div class='prev'>마지막 {esc(last[:10])}</div></div>"
                 f"<div class='age amber'>{days}일</div></div>")
    h.append("</div>")

    h.append("</div></body></html>")
    return "".join(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="출력 HTML 경로")
    args = ap.parse_args()

    cfg = briefing.load_config()
    now = datetime.now()
    conn = db.connect()
    data = build(conn, cfg, now)
    conn.close()
    html = render(data, now)

    if args.out:
        out = Path(args.out)
    else:
        base = Path(cfg.get("share_dir") or (HERE / "share")).expanduser() / "_daily"
        base.mkdir(parents=True, exist_ok=True)
        out = base / "대시보드.html"
    out.write_text(html, encoding="utf-8")
    print(f"대시보드 생성: {out}")
    print(f"  응답대기 {data['pending_all']}건 · 오늘 {data['msgs_today']}건 · "
          f"조용해진 방 {len(data['quiet'])}개")


if __name__ == "__main__":
    main()
