"""
2D 관계망 시각화 생성기 — 방↔사람 + 방↔방 관계망, 클릭 상세/참여자, 날짜필터, 최근활동 색, CSV.

- DB에서 노드(방·사람)/연결(사람-방, 방-방 겹침) + 노드별 최근 메시지 임베드
- 순수 JS(외부 라이브러리/CDN 없음) 2D 포스 그래프. 인터넷 없이 더블클릭이면 열림.
- 노드 클릭→우측 패널(대화+참여자) · 날짜 필터 · 색: 타입/최근활동 · CSV 내보내기 · 검색/드래그/줌
- LLM·외부 전송 없음(전부 로컬). ⚠ 메시지 내용이 HTML에 포함되니 비공개로 다루세요.

사용: python graph_export.py            (share_dir/_viz/kakao_2d.html)
      python graph_export.py --out x.html
"""
import argparse
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import db

HERE = Path(__file__).parent

TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>KakaoTalk 2D 관계망</title>
<style>
  html,body{margin:0;height:100%;background:#0f1420;color:#cdd7e6;
    font-family:system-ui,"Malgun Gothic",sans-serif;overflow:hidden}
  #net{width:100vw;height:100vh;display:block;cursor:grab}
  #hud{position:fixed;top:12px;left:14px;font-size:13px;line-height:1.55;z-index:5;
    background:rgba(15,20,32,.78);padding:9px 13px;border-radius:10px;border:1px solid #26324a}
  #hud b{color:#7fb2ff} .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
  #hud input,#hud select{background:#0c1018;border:1px solid #26324a;color:#cdd7e6;border-radius:6px;padding:3px 6px;font-size:12px}
  #find{margin-top:6px;width:160px}
  #hud .row{margin-top:6px;display:flex;align-items:center;gap:5px;flex-wrap:wrap}
  #hud .row input[type=date]{width:118px} #hud label{font-size:12px}
  .btn{cursor:pointer;color:#9fb4cf;border:1px solid #26324a;border-radius:6px;padding:3px 7px;font-size:11px}
  .chip{display:inline-block;background:#15202f;border:1px solid #26324a;border-radius:10px;
    padding:2px 8px;margin:2px 3px 2px 0;font-size:11.5px;color:#bcd}
  .chip b{color:#f0a060}
  #panel{position:fixed;top:0;right:0;width:370px;max-width:88vw;height:100vh;background:#0c1018;
    border-left:1px solid #26324a;transform:translateX(101%);transition:transform .18s ease;
    overflow-y:auto;padding:14px 16px;box-sizing:border-box;z-index:8}
  #panel.open{transform:none}
  #panel h3{margin:.1em 24px .1em 0;color:#7fb2ff;font-size:16px;word-break:break-all}
  #panel .meta{color:#8aa0c0;font-size:12px;margin:4px 0 12px}
  #panel .msg{border-top:1px solid #1a2333;padding:7px 0;font-size:12.5px;line-height:1.55;word-break:break-word}
  #panel .msg .h{color:#f0a060;font-size:11px;margin-bottom:1px}
  #pclose{position:absolute;top:12px;right:14px;cursor:pointer;color:#8aa0c0;font-size:18px}
</style></head><body>
<div id="hud">
  <b>KakaoTalk 2D 관계망</b> __STAMP__<br>
  <span id="leg"><span class="dot" style="background:#3a8ee6"></span>방 &nbsp;
    <span class="dot" style="background:#f0803c"></span>사람</span><br>
  <input id="find" placeholder="이름 검색…">
  <div class="row"><input type="date" id="from"><span>~</span><input type="date" id="to"><span id="clr" class="btn">지움</span></div>
  <div class="row"><label>색</label>
    <select id="cmode"><option value="type">타입</option><option value="recency">최근활동</option></select>
    <label><input type="checkbox" id="rr" checked> 방↔방</label></div>
  <div class="row"><span id="csvN" class="btn">노드 CSV</span><span id="csvL" class="btn">연결 CSV</span></div>
</div>
<div id="panel"><span id="pclose">&times;</span><div id="pbody"></div></div>
<svg id="net"></svg>
<script>
const G = __DATA__;
const NS="http://www.w3.org/2000/svg", svg=document.getElementById("net");
let W=innerWidth, H=innerHeight;
const nodes=G.nodes, links=G.links, detail=G.detail||{}, byId={};
nodes.forEach(n=>{byId[n.id]=n; n.x=W/2+(Math.random()-.5)*Math.min(W,900);
  n.y=H/2+(Math.random()-.5)*Math.min(H,600); n.vx=0; n.vy=0;});
links.forEach(l=>{l.s=byId[l.source]; l.t=byId[l.target];});
const root=document.createElementNS(NS,"g"); svg.appendChild(root);
const lg=document.createElementNS(NS,"g"); root.appendChild(lg);
const ng=document.createElementNS(NS,"g"); root.appendChild(ng);
const rOf=n=> n.type==="room" ? 5+Math.sqrt(n.count) : 6;
const lines=links.map(l=>{const e=document.createElementNS(NS,"line");
  if(l.kind==="rr"){e.setAttribute("stroke","#2bb59a");e.setAttribute("stroke-opacity",".4");
    e.setAttribute("stroke-dasharray","4 3");e.setAttribute("stroke-width",Math.max(.6,Math.min(4,l.w)));}
  else{e.setAttribute("stroke","#5b6b86");e.setAttribute("stroke-opacity",".3");
    e.setAttribute("stroke-width",Math.max(.5,l.w*.6));}
  lg.appendChild(e); return e;});
function baseCol(n){return n.type==="room"?"#3a8ee6":"#f0803c";}
function dnum(iso){return iso?Date.parse(iso.slice(0,10)):0;}
const maxD=Math.max(0,...nodes.map(n=>dnum(n.last)));
function recCol(n){const d=dnum(n.last); if(!d)return "#3a5068"; const days=(maxD-d)/864e5;
  return days<=1?"#ff4d3d":days<=3?"#ff7a3c":days<=7?"#ffb454":days<=14?"#8fca5a":days<=30?"#4a90d9":"#3a5068";}
let cmode="type";
const gEls=nodes.map(n=>{const g=document.createElementNS(NS,"g");
  const c=document.createElementNS(NS,"circle"); const r=rOf(n);
  c.setAttribute("r",r); c.setAttribute("fill",baseCol(n));
  c.setAttribute("stroke","#0f1420"); c.setAttribute("stroke-width","1.5");
  const t=document.createElementNS(NS,"text"); t.textContent=n.name;
  t.setAttribute("x",r+3); t.setAttribute("y",4); t.setAttribute("font-size","11"); t.setAttribute("fill","#cdd7e6");
  g.appendChild(c); g.appendChild(t); g.style.cursor="pointer"; ng.appendChild(g);
  n._g=g; n._c=c; return g;});
function applyColors(){ nodes.forEach(n=>n._c.setAttribute("fill", cmode==="recency"?recCol(n):baseCol(n)));
  document.getElementById("leg").innerHTML = cmode==="recency"
    ? "<span class='dot' style='background:#ff4d3d'></span>최근 → <span class='dot' style='background:#4a90d9'></span>오래"
    : "<span class='dot' style='background:#3a8ee6'></span>방 &nbsp;<span class='dot' style='background:#f0803c'></span>사람"; }
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
function esc(s){return (s||"").replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]));}
function fmt(iso){ return iso&&iso.length>=16 ? iso.slice(5,10)+" "+iso.slice(11,16) : (iso||""); }
let F={from:"",to:""}, current=null;
function inRange(iso){ const d=(iso||"").slice(0,10); return (!F.from||d>=F.from)&&(!F.to||d<=F.to); }
function nodeList(n){ const l=(detail[n.id]||{}).list||[]; return (!F.from&&!F.to)?l:l.filter(m=>inRange(m[0])); }
function openPanel(n){
  current=n; const list=nodeList(n);
  const conns=links.filter(l=>l.source===n.id||l.target===n.id).length;
  const cnt={}; list.forEach(m=>{cnt[m[1]]=(cnt[m[1]]||0)+1;});
  const parts=Object.entries(cnt).sort((a,b)=>b[1]-a[1]);
  const label=n.type==="room"?"참여자":"활동한 방";
  let h="<h3>"+esc(n.name)+"</h3><div class='meta'>"+(n.type==="room"?"방":"사람")
    +" · 메시지 "+n.count+"건 · 연결 "+conns+((F.from||F.to)?" · 기간필터":"")+"</div>";
  if(parts.length){ h+="<div class='meta'>"+label+" ("+parts.length+")</div><div>";
    parts.forEach(x=>{h+="<span class='chip'>"+esc(x[0])+" <b>"+x[1]+"</b></span>";}); h+="</div>"; }
  if(!list.length){ h+="<div class='msg'>이 기간에 표시할 메시지가 없습니다(최근 임베드분 기준).</div>"; }
  list.forEach(m=>{ h+="<div class='msg'><div class='h'>"+fmt(m[0])+" · "+esc(m[1])+"</div>"+esc(m[2])+"</div>"; });
  document.getElementById("pbody").innerHTML=h; document.getElementById("panel").classList.add("open");
}
function updateViz(){
  const q=document.getElementById("find").value.trim();
  nodes.forEach(n=>{
    const dateOK=(!F.from&&!F.to)||((detail[n.id]||{}).list||[]).some(m=>inRange(m[0]));
    const searchOK=!q||n.name.includes(q); n._vis=dateOK&&searchOK;
    n._g.style.opacity=n._vis?1:.12;
    const hl=q&&n.name.includes(q);
    n._c.setAttribute("stroke",hl?"#ffef7a":"#0f1420"); n._c.setAttribute("stroke-width",hl?"3":"1.5");
  });
  const showRR=document.getElementById("rr").checked;
  lines.forEach((e,i)=>{const l=links[i];
    if(l.kind==="rr" && !showRR){ e.style.display="none"; return; } e.style.display="";
    e.style.opacity=(l.s._vis!==false&&l.t._vis!==false)?1:.08;});
  if(current) openPanel(current);
}
document.getElementById("pclose").onclick=()=>{document.getElementById("panel").classList.remove("open");current=null;};
let drag=null, pan=null, moved=false;
gEls.forEach((g,i)=>{const n=nodes[i];
  g.addEventListener("pointerdown",e=>{e.stopPropagation(); drag={n}; moved=false; n.fx=n.x; n.fy=n.y;
    g.setPointerCapture(e.pointerId);});});
svg.addEventListener("pointerdown",e=>{ pan={x:e.clientX-view.x,y:e.clientY-view.y}; });
svg.addEventListener("pointermove",e=>{
  if(drag){const p=toGraph(e.clientX,e.clientY); drag.n.fx=p.x; drag.n.fy=p.y; moved=true; ticks=0; run(.3);}
  else if(pan){ if(Math.abs(e.clientX-pan.x-view.x)+Math.abs(e.clientY-pan.y-view.y)>2) moved=true;
    view.x=e.clientX-pan.x; view.y=e.clientY-pan.y; apply(); }});
addEventListener("pointerup",()=>{ if(drag){ if(!moved) openPanel(drag.n); drag.n.fx=null;drag.n.fy=null;drag=null;} pan=null; });
addEventListener("resize",()=>{W=innerWidth;H=innerHeight;});
document.getElementById("find").addEventListener("input",updateViz);
document.getElementById("from").addEventListener("change",e=>{F.from=e.target.value;updateViz();});
document.getElementById("to").addEventListener("change",e=>{F.to=e.target.value;updateViz();});
document.getElementById("clr").onclick=()=>{F.from="";F.to="";
  document.getElementById("from").value="";document.getElementById("to").value="";
  document.getElementById("find").value="";updateViz();};
document.getElementById("cmode").addEventListener("change",e=>{cmode=e.target.value;applyColors();});
document.getElementById("rr").addEventListener("change",updateViz);
function q(s){ s=(s==null?"":""+s); return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s; }
function dl(name,txt){ const b=new Blob(["\ufeff"+txt],{type:"text/csv;charset=utf-8"});
  const u=URL.createObjectURL(b); const a=document.createElement("a"); a.href=u; a.download=name; a.click(); URL.revokeObjectURL(u); }
document.getElementById("csvN").onclick=()=>{ let c="id,name,type,count,last\n";
  nodes.forEach(n=>c+=[q(n.id),q(n.name),n.type,n.count,n.last||""].join(",")+"\n"); dl("kakao_nodes.csv",c); };
document.getElementById("csvL").onclick=()=>{ let c="source,target,weight,kind\n";
  links.forEach(l=>c+=[q(l.source),q(l.target),l.w,l.kind||"pr"].join(",")+"\n"); dl("kakao_links.csv",c); };
</script></body></html>
"""


def _clip(s, n=180):
    s = (s or "").replace("\n", " ").replace("\r", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def build_graph(conn, cfg):
    top_rooms = cfg.get("viz_top_rooms", 150)
    top_people = cfg.get("viz_top_people", 250)
    min_msgs = cfg.get("viz_min_msgs", 1)
    per = cfg.get("viz_detail_msgs", 120)
    rr_min = cfg.get("rr_min_shared", 2)        # 방-방 연결 최소 공통인원
    rr_maxpr = cfg.get("rr_max_person_rooms", 25)  # 이보다 많은 방에 있는 사람은 방-방 계산서 제외(허브 노이즈)
    rr_top = cfg.get("rr_top", 500)             # 방-방 연결 최대 개수

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

    nodes = [{"id": f"room:{r}", "name": r, "type": "room", "count": c, "last": ""} for r, c in rooms]
    nodes += [{"id": f"person:{p}", "name": p, "type": "person", "count": c, "last": ""} for p, c in people]
    nmap = {n["id"]: n for n in nodes}

    links = []
    person_rooms = defaultdict(set)
    for room, sender, c in conn.execute(
        "SELECT room, sender, COUNT(*) c FROM messages "
        "WHERE sender IS NOT NULL AND sender!='' GROUP BY room, sender"
    ).fetchall():
        if room in room_set and sender in person_set:
            links.append({"source": f"person:{sender}", "target": f"room:{room}",
                          "w": round(0.4 + (c ** 0.5) / 3, 2), "kind": "pr"})
            person_rooms[sender].add(room)

    # 방↔방: 같은 사람이 겹치는 방쌍(공통 인원수로 가중). 허브(다수 방 소속)는 제외해 노이즈 방지
    pair = defaultdict(int)
    for sender, rs in person_rooms.items():
        if len(rs) > rr_maxpr:
            continue
        for a, b in combinations(sorted(rs), 2):
            pair[(a, b)] += 1
    rr = [(a, b, w) for (a, b), w in pair.items() if w >= rr_min]
    rr.sort(key=lambda x: x[2], reverse=True)
    for a, b, w in rr[:rr_top]:
        links.append({"source": f"room:{a}", "target": f"room:{b}",
                      "w": round(min(4.0, 0.8 + w * 0.5), 2), "kind": "rr"})

    detail = {}
    for r in room_set:
        rows = conn.execute(
            "SELECT sent_at, sender, content FROM messages WHERE room=? "
            "ORDER BY sent_at DESC, id DESC LIMIT ?", (r, per)
        ).fetchall()
        lst = [[sa, sn or "", _clip(ct)] for sa, sn, ct in reversed(rows)]
        detail[f"room:{r}"] = {"list": lst}
        if lst:
            nmap[f"room:{r}"]["last"] = lst[-1][0]
    for p in person_set:
        rows = conn.execute(
            "SELECT sent_at, room, content FROM messages WHERE sender=? "
            "ORDER BY sent_at DESC, id DESC LIMIT ?", (p, per)
        ).fetchall()
        lst = [[sa, rm or "", _clip(ct)] for sa, rm, ct in reversed(rows)]
        detail[f"person:{p}"] = {"list": lst}
        if lst:
            nmap[f"person:{p}"]["last"] = lst[-1][0]

    return {"nodes": nodes, "links": links, "detail": detail}


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

    rr = sum(1 for l in graph["links"] if l.get("kind") == "rr")
    stamp = f"(노드 {len(graph['nodes'])} · 연결 {len(graph['links'])})"
    html = TEMPLATE.replace("__DATA__", json.dumps(graph, ensure_ascii=False)).replace("__STAMP__", stamp)

    if args.out:
        out = Path(args.out)
    else:
        base = Path(cfg.get("share_dir") or (HERE / "share")).expanduser() / "_viz"
        base.mkdir(parents=True, exist_ok=True)
        out = base / "kakao_2d.html"
    out.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) // 1024
    print(f"2D 관계망 생성: {out}  (노드 {len(graph['nodes'])}, 연결 {len(graph['links'])} [방-방 {rr}], {kb}KB)")
    print("  노드 클릭=대화/참여자 · 날짜필터 · 색:타입/최근활동 · CSV 내보내기. 오프라인 동작.")


if __name__ == "__main__":
    main()
