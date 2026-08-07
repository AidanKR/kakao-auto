"""
통합 검색 페이지 생성기 — 모든 대화를 한 칸에서 검색하는 자체완결 HTML.

- DB의 메시지를 HTML에 담아, 브라우저에서 키워드·방·날짜로 즉시 검색(하이라이트)
- 카톡 기본 검색(방 하나씩)과 달리 전 대화를 한 번에. 결과에 방·시각·보낸이 표시.
- 순수 JS(외부 라이브러리/CDN 없음). 인터넷 없이 더블클릭이면 열림.
- LLM·외부 전송 없음(전부 로컬). ⚠ 대화 내용이 HTML에 포함되니 비공개로 다루세요.

사용: python search.py            (share_dir/_viz/검색.html)
      python search.py --out x.html
"""
import argparse
import json
from pathlib import Path

import db

HERE = Path(__file__).parent

TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>카카오톡 검색</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:0;background:#f7f7f5;color:#1a1a19;
  font-family:system-ui,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
.top{position:sticky;top:0;background:#f7f7f5;border-bottom:1px solid #e6e5df;
  padding:16px 20px 12px;z-index:5}
h1{font-size:18px;font-weight:600;margin:0 0 10px}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
#q{flex:1;min-width:200px;font-size:15px;padding:9px 12px;border:1px solid #d3d1c7;border-radius:8px;background:#fff}
select,input[type=date]{font-size:13px;padding:8px 9px;border:1px solid #d3d1c7;border-radius:8px;background:#fff;color:#1a1a19}
.cnt{font-size:13px;color:#77766f;margin:9px 2px 0}
.wrap{max-width:900px;margin:0 auto;padding:8px 20px 60px}
.hit{background:#fff;border:1px solid #ececec;border-radius:10px;padding:11px 14px;margin:9px 0}
.hit .meta{font-size:12px;color:#77766f;margin-bottom:4px}
.hit .meta b{color:#2f6ea8;font-weight:600}
.hit .txt{font-size:14px;line-height:1.55;white-space:pre-wrap;word-break:break-word}
mark{background:#ffe9a8;color:#1a1a19;padding:0 1px;border-radius:2px}
.empty{color:#77766f;font-size:14px;padding:30px 4px;text-align:center}
.more{text-align:center;padding:14px;color:#2f6ea8;font-size:13.5px;cursor:pointer}
</style></head><body>
<div class="top"><div class="wrap" style="padding-bottom:0">
  <h1>카카오톡 통합 검색 __STAMP__</h1>
  <div class="controls">
    <input id="q" placeholder="검색어 (여러 단어=모두 포함)… 예: 견적 개성" autofocus>
    <select id="room"><option value="">전체 방</option></select>
    <input type="date" id="from"><input type="date" id="to">
  </div>
  <div class="cnt" id="cnt"></div>
</div></div>
<div class="wrap"><div id="res"></div></div>
<script>
const M = __DATA__;        // [[sent_at, room, sender, content], ...]
const rooms=[...new Set(M.map(m=>m[1]))].sort();
const rsel=document.getElementById("room");
rooms.forEach(r=>{const o=document.createElement("option");o.value=r;o.textContent=r;rsel.appendChild(o);});
const q=document.getElementById("q"), from=document.getElementById("from"), to=document.getElementById("to");
const res=document.getElementById("res"), cnt=document.getElementById("cnt");
let shown=0, matched=[];
function esc(s){return (s||"").replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]));}
function hl(s,terms){ let h=esc(s);
  terms.forEach(t=>{ if(!t)return; const re=new RegExp("("+t.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+")","gi");
    h=h.replace(re,"<mark>$1</mark>"); }); return h; }
function fmt(iso){ return iso&&iso.length>=16 ? iso.slice(0,10)+" "+iso.slice(11,16) : (iso||""); }
function run(){
  const terms=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const rm=rsel.value, f=from.value, t=to.value;
  matched=[];
  for(let i=0;i<M.length;i++){const m=M[i];
    if(rm && m[1]!==rm) continue;
    const d=(m[0]||"").slice(0,10); if(f&&d<f)continue; if(t&&d>t)continue;
    if(terms.length){ const low=(m[3]||"").toLowerCase();
      let ok=true; for(const term of terms){ if(!low.includes(term)){ok=false;break;} } if(!ok)continue; }
    matched.push(m);
  }
  matched.sort((a,b)=>(b[0]||"").localeCompare(a[0]||""));   // 최신 우선
  shown=0; res.innerHTML="";
  cnt.textContent = (terms.length||rm||f||t) ? (matched.length.toLocaleString()+"건") : (M.length.toLocaleString()+"건 전체 (검색어를 입력하세요)");
  render();
}
function render(){
  const terms=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const batch=matched.slice(shown, shown+200);
  const frag=document.createDocumentFragment();
  if(!matched.length){ res.innerHTML="<div class='empty'>결과가 없습니다.</div>"; return; }
  batch.forEach(m=>{const d=document.createElement("div"); d.className="hit";
    d.innerHTML="<div class='meta'><b>"+esc(m[1])+"</b> · "+fmt(m[0])+" · "+esc(m[2])+"</div>"
      +"<div class='txt'>"+hl(m[3],terms)+"</div>"; frag.appendChild(d);});
  shown+=batch.length;
  if(shown===0){} res.appendChild(frag);
  const old=document.getElementById("more"); if(old)old.remove();
  if(shown<matched.length){ const mo=document.createElement("div"); mo.id="more"; mo.className="more";
    mo.textContent="더 보기 ("+(matched.length-shown).toLocaleString()+"건 남음)"; mo.onclick=render; res.appendChild(mo); }
}
let tmr; [q,rsel,from,to].forEach(el=>el.addEventListener("input",()=>{clearTimeout(tmr);tmr=setTimeout(run,180);}));
run();
</script></body></html>
"""


def build(conn, cfg):
    limit = cfg.get("search_max_msgs", 80000)
    rows = conn.execute(
        "SELECT sent_at, room, sender, content FROM messages "
        "ORDER BY sent_at DESC LIMIT ?", (limit,)
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    data = [[sa, rm, sn or "", ct or ""] for sa, rm, sn, ct in rows]
    return data, total, limit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="출력 HTML 경로")
    args = ap.parse_args()

    cfg = {}
    p = HERE / "config.json"
    if p.exists():
        for enc in ("utf-8-sig", "utf-8", "cp949"):
            try:
                cfg = json.loads(p.read_bytes().decode(enc))
                break
            except Exception:
                continue

    conn = db.connect()
    data, total, limit = build(conn, cfg)
    conn.close()

    stamp = f"({len(data):,}건" + (f" / 전체 {total:,}건, 최신 {limit:,}건만 담음)" if total > len(data) else ")")
    html = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__STAMP__", stamp)

    if args.out:
        out = Path(args.out)
    else:
        base = Path(cfg.get("share_dir") or (HERE / "share")).expanduser() / "_viz"
        base.mkdir(parents=True, exist_ok=True)
        out = base / "검색.html"
    out.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) // 1024
    print(f"검색 페이지 생성: {out}  ({len(data):,}건, {kb:,}KB)")
    if total > len(data):
        print(f"  ⚠ 전체 {total:,}건 중 최신 {limit:,}건만 담았습니다(config search_max_msgs로 조절).")
    print("  더블클릭하면 열립니다 — 인터넷 없이 오프라인 검색.")


if __name__ == "__main__":
    main()
