"""
3D 네트워크 시각화 생성기 — 방↔사람 소통 관계망을 '자체 완결 HTML'로.

- DB에서 노드(방·사람)와 연결(누가 어느 방에서 몇 건)을 뽑아 그래프 JSON 구성
- 3d-force-graph(CDN) 로 렌더하는 HTML 한 파일 생성(데이터 내장 → 더블클릭이면 열림)
- LLM/인터넷 전송 없음(개인정보 외부 유출 0). ※ HTML 첫 로딩 때 CDN 스크립트만 받음(인터넷 필요)

사용: python graph_export.py            (share_dir/_viz/kakao_3d.html 생성)
      python graph_export.py --out x.html
"""
import argparse
import json
from pathlib import Path

import db

HERE = Path(__file__).parent

TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>KakaoTalk 3D 관계망</title>
<style>
  body{margin:0;background:#05060a;color:#cfe;font-family:system-ui,sans-serif;overflow:hidden}
  #g{width:100vw;height:100vh}
  #hud{position:fixed;top:12px;left:14px;z-index:10;font-size:13px;line-height:1.6;
       background:rgba(10,14,22,.7);padding:10px 14px;border-radius:10px;border:1px solid #1e2a3a}
  #hud b{color:#7fd7ff} .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
</style></head><body>
<div id="hud">
  <b>KakaoTalk 3D 관계망</b> __STAMP__<br>
  <span class="dot" style="background:#7fd7ff"></span>방 &nbsp;
  <span class="dot" style="background:#ffb454"></span>사람<br>
  크기=활동량 · 선=대화량 · 드래그 회전 / 휠 확대 / 노드 클릭
</div>
<div id="g"></div>
<script src="https://unpkg.com/3d-force-graph"></script>
<script>
const DATA = __DATA__;
const G = ForceGraph3D()(document.getElementById('g'))
  .graphData(DATA)
  .backgroundColor('#05060a')
  .nodeLabel(n => `${n.name} (${n.count})`)
  .nodeColor(n => n.type==='room' ? '#7fd7ff' : '#ffb454')
  .nodeVal(n => n.val)
  .nodeOpacity(0.9)
  .linkColor(() => 'rgba(120,160,220,0.25)')
  .linkWidth(l => l.w)
  .linkDirectionalParticles(l => Math.min(4, Math.round(l.w)))
  .linkDirectionalParticleSpeed(0.006)
  .onNodeClick(n => { const d=80; const r=1+d/Math.hypot(n.x,n.y,n.z);
    G.cameraPosition({x:n.x*r,y:n.y*r,z:n.z*r}, n, 1200); });
</script></body></html>
"""


def build_graph(conn, cfg):
    top_rooms = cfg.get("viz_top_rooms", 120)
    top_people = cfg.get("viz_top_people", 200)
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

    def val(c):
        return round(2 + (c ** 0.5), 1)   # 크기: 건수 제곱근 스케일

    nodes = [{"id": f"room:{r}", "name": r, "type": "room", "count": c, "val": val(c)} for r, c in rooms]
    nodes += [{"id": f"person:{p}", "name": p, "type": "person", "count": c, "val": val(c)} for p, c in people]

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
        try:
            cfg = json.loads(p.read_bytes().decode("utf-8-sig"))
        except Exception:
            try:
                cfg = json.loads(p.read_bytes().decode("cp949"))
            except Exception:
                cfg = {}

    conn = db.connect()
    graph = build_graph(conn, cfg)
    conn.close()

    from datetime import datetime
    stamp = f"(노드 {len(graph['nodes'])} · 연결 {len(graph['links'])})"
    html = TEMPLATE.replace("__DATA__", json.dumps(graph, ensure_ascii=False)).replace("__STAMP__", stamp)

    if args.out:
        out = Path(args.out)
    else:
        base = Path(cfg.get("share_dir") or (HERE / "share")).expanduser() / "_viz"
        base.mkdir(parents=True, exist_ok=True)
        out = base / "kakao_3d.html"
    out.write_text(html, encoding="utf-8")
    print(f"3D 관계망 생성: {out}  (노드 {len(graph['nodes'])}, 연결 {len(graph['links'])})")
    print("  더블클릭하면 브라우저에서 3D로 열립니다(첫 로딩 시 인터넷 필요).")


if __name__ == "__main__":
    main()
