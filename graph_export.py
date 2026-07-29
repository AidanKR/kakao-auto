"""
2D 관계망 시각화 생성기 — 방↔사람 소통 관계망을 '자체 완결 HTML'로.

- DB에서 노드(방·사람)와 연결(누가 어느 방에서 몇 건)을 뽑아 그래프 구성
- 순수 JS(외부 라이브러리/ CDN 없음) 로 2D 포스 그래프 렌더 → 인터넷 없이 더블클릭이면 열림
- 드래그로 노드 이동 / 휠로 확대 / 빈 곳 드래그로 이동
- LLM·외부 전송 없음(개인정보 유출 0, 전부 로컬)

사용: python graph_export.py            (share_dir/_viz/kakao_2d.html 생성)
      python graph_export.py --out x.html
"""
import argparse
import json
from pathlib import Path

import db

HERE = Path(__file__).parent

TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>KakaoTalk 2D 관계망</title>
<style>
  html,body{margin:0;height:100%;background:#0f1420;color:#cdd7e6;
    font-family:system-ui,"Malgun Gothic",sans-serif;overflow:hidden}
  #net{width:100vw;height:100vh;display:block;cursor:grab}
  #hud{position:fixed;top:12px;left:14px;font-size:13px;line-height:1.6;
    background:rgba(15,20,32,.75);padding:9px 13px;border-radius:10px;border:1px solid #26324a}
  #hud b{color:#7fb2ff} .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
  #find{margin-top:6px;width:150px;background:#0c1018;border:1px solid #26324a;color:#cdd7e6;
    border-radius:6px;padding:4px 7px;font-size:12px}
</style></head><body>
<div id="hud">
  <b>KakaoTalk 2D 관계망</b> __STAMP__<br>
  <span class="dot" style="background:#3a8ee6"></span>방 &nbsp;
  <span class="dot" style="background:#f0803c"></span>사람<br>
  노드 드래그 · 휠 확대 · 빈곳 드래그 이동<br>
  <input id="find" placeholder="이름 검색…">
</div>
<svg id="net"></svg>
<script>
const G = __DATA__;
const NS="http://www.w3.org/2000/svg", svg=document.getElementById("net");
let W=innerWidth, H=innerHeight;
const nodes=G.nodes, links=G.links, byId={};
nodes.forEach(n=>{byId[n.id]=n; n.x=W/2+(Math.random()-.5)*Math.min(W,900);
  n.y=H/2+(Math.random()-.5)*Math.min(H,600); n.vx=0; n.vy=0;});
links.forEach(l=>{l.s=byId[l.source]; l.t=byId[l.target];});
const root=document.createElementNS(NS,"g"); svg.appendChild(root);
const lg=document.createElementNS(NS,"g"); root.appendChild(lg);
const ng=document.createElementNS(NS,"g"); root.appendChild(ng);
const rOf=n=> n.type==="room" ? 5+Math.sqrt(n.count) : 6;
const lines=links.map(l=>{const e=document.createElementNS(NS,"line");
  e.setAttribute("stroke","#5b6b86"); e.setAttribute("stroke-opacity",".3");
  e.setAttribute("stroke-width",Math.max(.5,l.w*.6)); lg.appendChild(e); return e;});
const gEls=nodes.map(n=>{const g=document.createElementNS(NS,"g");
  const c=document.createElementNS(NS,"circle"); const r=rOf(n);
  c.setAttribute("r",r); c.setAttribute("fill",n.type==="room"?"#3a8ee6":"#f0803c");
  c.setAttribute("stroke","#0f1420"); c.setAttribute("stroke-width","1.5");
  const t=document.createElementNS(NS,"text"); t.textContent=n.name;
  t.setAttribute("x",r+3); t.setAttribute("y",4); t.setAttribute("font-size","11"); t.setAttribute("fill","#cdd7e6");
  g.appendChild(c); g.appendChild(t); g.style.cursor="grab"; ng.appendChild(g);
  n._g=g; n._c=c; return g;});
let alpha=1, raf=null;
function step(){
  for(let i=0;i<nodes.length;i++){const a=nodes[i];
    for(let j=i+1;j<nodes.length;j++){const b=nodes[j];
      let dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+.01,d=Math.sqrt(d2),f=-1400/d2,fx=dx/d*f,fy=dy/d*f;
      a.vx-=fx;a.vy-=fy;b.vx+=fx;b.vy+=fy;}}
  links.forEach(l=>{let dx=l.t.x-l.s.x,dy=l.t.y-l.s.y,d=Math.sqrt(dx*dx+dy*dy)+.01,f=(d-85)*.02,fx=dx/d*f,fy=dy/d*f;
    l.s.vx+=fx;l.s.vy+=fy;l.t.vx-=fx;l.t.vy-=fy;});
  nodes.forEach(n=>{n.vx+=(W/2-n.x)*.002;n.vy+=(H/2-n.y)*.002;});
  nodes.forEach(n=>{if(n.fx!=null){n.x=n.fx;n.y=n.fy;return;} n.x+=n.vx*alpha;n.y+=n.vy*alpha;n.vx*=.86;n.vy*=.86;});
  alpha*=.99; draw();
}
function draw(){
  for(let i=0;i<links.length;i++){const e=lines[i],l=links[i];
    e.setAttribute("x1",l.s.x);e.setAttribute("y1",l.s.y);e.setAttribute("x2",l.t.x);e.setAttribute("y2",l.t.y);}
  nodes.forEach(n=>n._g.setAttribute("transform","translate("+n.x+","+n.y+")"));
}
let ticks=0;
function run(a){ if(a) alpha=a; if(raf) return;
  (function f(){ step(); ticks++; if(alpha>.03 && ticks<800){raf=requestAnimationFrame(f);} else {raf=null;} })(); }
run(1);
let view={k:1,x:0,y:0};
function apply(){ root.setAttribute("transform","translate("+view.x+","+view.y+") scale("+view.k+")"); }
function toGraph(sx,sy){ return {x:(sx-view.x)/view.k, y:(sy-view.y)/view.k}; }
svg.addEventListener("wheel",e=>{e.preventDefault(); const s=e.deltaY<0?1.12:0.89;
  const gx=(e.clientX-view.x)/view.k, gy=(e.clientY-view.y)/view.k;
  view.k=Math.max(.15,Math.min(5,view.k*s)); view.x=e.clientX-gx*view.k; view.y=e.clientY-gy*view.k; apply();},{passive:false});
let drag=null, pan=null;
gEls.forEach((g,i)=>{const n=nodes[i];
  g.addEventListener("pointerdown",e=>{e.stopPropagation(); drag={n}; n.fx=n.x; n.fy=n.y;
    g.setPointerCapture(e.pointerId); ticks=0; run(.5);});});
svg.addEventListener("pointerdown",e=>{ pan={x:e.clientX-view.x,y:e.clientY-view.y}; });
svg.addEventListener("pointermove",e=>{
  if(drag){const p=toGraph(e.clientX,e.clientY); drag.n.fx=p.x; drag.n.fy=p.y; ticks=0; run(.3);}
  else if(pan){ view.x=e.clientX-pan.x; view.y=e.clientY-pan.y; apply(); }});
addEventListener("pointerup",()=>{ if(drag){drag.n.fx=null;drag.n.fy=null;drag=null;} pan=null; });
addEventListener("resize",()=>{W=innerWidth;H=innerHeight;});
document.getElementById("find").addEventListener("input",e=>{const q=e.target.value.trim();
  nodes.forEach(n=>{const on=q&&n.name.includes(q);
    n._c.setAttribute("stroke",on?"#ffef7a":"#0f1420"); n._c.setAttribute("stroke-width",on?"3":"1.5");
    n._g.style.opacity=(!q||on)?1:.25;});});
</script></body></html>
"""


def build_graph(conn, cfg):
    top_rooms = cfg.get("viz_top_rooms", 150)
    top_people = cfg.get("viz_top_people", 250)
    min_msgs = cfg.get("viz_min_msgs", 1)

    rooms = conn.execute(
        "SELECT room, COUNT(*) c FROM messages GROUP BY room "
        "HAVING c>=? ORDER BY c DESC LIMIT ?", (min_msgs, top_rooms)
    ).fetchall()
    people = conn.execute(
        "SELECT sender, COUNT(*) c FROM messages WHERE sender IS NOT NULL AND sender!='' "
        "GROUP BY sender HAVING c>=? ORDER BY c DESC LIMIT ?", (min_msgs, top_people)
    ).fetchall()
    room_set = {r for r, _ in rooms}
    person_set = {p for p, _ in people}

    nodes = [{"id": f"room:{r}", "name": r, "type": "room", "count": c} for r, c in rooms]
    nodes += [{"id": f"person:{p}", "name": p, "type": "person", "count": c} for p, c in people]

    links = []
    for room, sender, c in conn.execute(
        "SELECT room, sender, COUNT(*) c FROM messages "
        "WHERE sender IS NOT NULL AND sender!='' GROUP BY room, sender"
    ).fetchall():
        if room in room_set and sender in person_set:
            links.append({"source": f"person:{sender}", "target": f"room:{room}",
                          "w": round(0.4 + (c ** 0.5) / 3, 2)})
    return {"nodes": nodes, "links": links}


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
    graph = build_graph(conn, cfg)
    conn.close()

    stamp = f"(노드 {len(graph['nodes'])} · 연결 {len(graph['links'])})"
    html = TEMPLATE.replace("__DATA__", json.dumps(graph, ensure_ascii=False)).replace("__STAMP__", stamp)

    if args.out:
        out = Path(args.out)
    else:
        base = Path(cfg.get("share_dir") or (HERE / "share")).expanduser() / "_viz"
        base.mkdir(parents=True, exist_ok=True)
        out = base / "kakao_2d.html"
    out.write_text(html, encoding="utf-8")
    print(f"2D 관계망 생성: {out}  (노드 {len(graph['nodes'])}, 연결 {len(graph['links'])})")
    print("  더블클릭하면 열립니다 — 인터넷 없이 오프라인에서도 동작.")


if __name__ == "__main__":
    main()
