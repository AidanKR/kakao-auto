"""
진단 — 카카오톡이 띄운 창(대화방 · 채팅방 서랍)의 UIA 구조를 덤프하고 좌표를 보정한다.

카카오톡 대화방에서 받은 사진은 캐시에 .cng 로 암호화돼 있어 그대로는 못 쓴다(2026-09-22 실측).
대신 카카오톡 자신에게 '사진/동영상 모아보기 → 저장'을 시키면 평문으로 떨어진다.
그 버튼을 추측 좌표로 누르면 안 되므로(채팅 탭에서 겪은 전례), 여기서 실제 구조를 먼저 잰다.

쓰는 법:
  1) **채팅방 서랍**을 열고 사진이 여러 줄 나오는 방의 '사진/동영상' 탭까지 띄워 둔다
     (대화방 우측 위 ≡ → 채팅방 서랍 → 사진/동영상). 서랍 창 좌측에 전체 방 목록이 있어
     방마다 대화방을 열 필요가 없다(2026-09-22 실측).
  2) KakaoAuto.exe diagroom   (또는 python diag_room.py)
  3) room_tree.txt 를 개발자에게 보낸다.
  4) 안내에 따라 지점 4곳(첫 썸네일·옆 썸네일·다음 줄 썸네일·저장 버튼)에 순서대로
     마우스를 올려둔다 → 좌표가 config.json 에 저장된다.

출력: <appdir>/room_tree.txt
"""
import json
import time

HERE = __import__("appdir").APP_DIR

CLICKABLE = {"ButtonControl", "TabItemControl", "ListItemControl", "MenuItemControl",
             "HyperlinkControl", "ImageControl", "TextControl", "CheckBoxControl",
             "RadioButtonControl", "SplitButtonControl", "ToolBarControl"}


def _cursor_pos():
    """현재 마우스 화면 좌표 (ctypes, 추가 라이브러리 불필요)."""
    import ctypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def _load_cfg_raw():
    p = HERE / "config.json"
    if not p.exists():
        return {}
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return json.loads(data.decode(enc))
        except Exception:
            continue
    return {}


def _kakao_pid(auto):
    """카카오톡 메인 창의 프로세스 id. 못 찾으면 None."""
    for w in auto.GetRootControl().GetChildren():
        try:
            if (w.ClassName or "") == "EVA_Window_Dblclk" and (w.Name or "") == "카카오톡":
                return w.ProcessId
        except Exception:
            continue
    return None


def _room_windows(auto):
    """카카오톡이 띄운 최상위 창 전부(메인 창 제외).

    2026-09-22 실측: '채팅방 서랍'은 대화방과 **다른 별도 창**이고 좌측에 전체 방 목록을
    담고 있다. 클래스로 거르면(EVA_Window_Dblclk) 이 창을 놓치므로, 같은 프로세스가 띄운
    창을 모두 잡는다. 클래스는 결과에 함께 적어 둔다."""
    pid = _kakao_pid(auto)
    out = []
    for w in auto.GetRootControl().GetChildren():
        try:
            nm = (w.Name or "").strip()
            if not nm or nm == "카카오톡":
                continue
            if pid is not None and w.ProcessId != pid:
                continue
            if pid is None and (w.ClassName or "") != "EVA_Window_Dblclk":
                continue
            out.append(w)
        except Exception:
            continue
    return out


def _dump(win, lines):
    try:
        r = win.BoundingRectangle
        lines.append(f"[창 '{win.Name}'] class='{win.ClassName}' "
                     f"rect=({r.left},{r.top},{r.right},{r.bottom}) "
                     f"size={r.right - r.left}x{r.bottom - r.top}")
        base_l, base_t = r.left, r.top
    except Exception:
        lines.append(f"[창 '{win.Name}'] rect 읽기 실패")
        base_l = base_t = 0

    def walk(c, depth=0):
        if depth > 22:
            return
        try:
            children = c.GetChildren()
        except Exception:
            return
        for ch in children:
            try:
                nm = (ch.Name or "").strip()
                ct = ch.ControlTypeName
                cn = ch.ClassName or ""
                rr = ch.BoundingRectangle
                if nm or ct in CLICKABLE:
                    # 창 기준 상대좌표도 같이 적는다(창을 옮겨도 쓸 수 있게).
                    lines.append(
                        f"{'  ' * depth}- {ct} name='{nm[:48]}' class='{cn}' "
                        f"abs=({rr.left},{rr.top},{rr.right},{rr.bottom}) "
                        f"rel=({rr.left - base_l},{rr.top - base_t})")
            except Exception:
                pass
            walk(ch, depth + 1)

    walk(win)


# 서랍에서 잴 지점들. 순서대로 마우스를 올려두게 안내한다.
# thumb0/thumb1 = 그리드 가로 간격 계산용(같은 줄 인접 썸네일), thumb_row2 = 세로 간격 계산용
# (그리드 사이에 월별 헤더가 끼어 있어 세로 간격은 줄마다 다를 수 있음 — 실측으로 확인할 것).
CALIB_POINTS = [
    ("drawer_thumb0", "첫 번째(왼쪽 위) 사진 썸네일의 정중앙"),
    ("drawer_thumb1", "같은 줄 바로 오른쪽 사진 썸네일의 정중앙(가로 간격 계산용)"),
    ("drawer_thumb_row2", "다음 줄 첫 번째 사진 썸네일의 정중앙(세로 간격 계산용, 같은 줄이면 아무 사진이나 다시)"),
    ("drawer_save_btn", "하단의 '저장' 버튼"),
]


def calibrate_points(win, points=None, seconds=6):
    """여러 지점을 순서대로 안내하며 창 기준 상대좌표를 config 에 저장.

    지점마다 확인을 기다리지 않고 카운트다운으로 진행한다 — 대화방 서랍은 화면마다
    썸네일 배치가 달라질 수 있어(방마다 사진 수가 다름) 매번 실측해야 한다."""
    points = points or CALIB_POINTS
    try:
        r = win.BoundingRectangle
    except Exception:
        print("  창 좌표를 못 읽어 보정을 건너뜁니다.")
        return
    cfg = _load_cfg_raw()
    saved = {}
    for key, desc in points:
        print()
        print(f"  ── [{key}] {desc} 위에 마우스를 올려두세요 ──")
        print(f"  {seconds}초 뒤 저장합니다. 누르지 말고 올려만 두세요. (해당 지점이 없으면 그대로 두면 창 밖으로 판정돼 건너뜁니다)")
        for i in range(seconds, 0, -1):
            print(f"    {i}...", end="\r", flush=True)
            time.sleep(1)
        x, y = _cursor_pos()
        rel_x, rel_y = x - r.left, y - r.top
        ok = 0 <= rel_x <= (r.right - r.left) and 0 <= rel_y <= (r.bottom - r.top)
        print(f"  화면({x},{y}) · 창기준({rel_x},{rel_y})  {'저장함' if ok else '창 밖 — 건너뜀'}          ")
        if ok:
            cfg[key] = [rel_x, rel_y]
            saved[key] = [rel_x, rel_y]
    if saved:
        try:
            (HERE / "config.json").write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nconfig.json 에 저장: {saved}")
        except Exception as e:
            print("  저장 실패:", e)
    else:
        print("\n저장된 지점이 없습니다.")


def main():
    try:
        import uiautomation as auto
    except Exception as e:
        print("uiautomation 로드 실패:", e)
        return

    wins = _room_windows(auto)
    lines = []
    if not wins:
        msg = ("카카오톡이 띄운 창이 없습니다. 대화방이나 '채팅방 서랍'을 "
               "열어 두고 다시 실행하세요.")
        print(msg)
        lines.append(msg)
    else:
        print(f"카카오톡 창 {len(wins)}개 발견 — 구조를 뜹니다.")
        for w in wins:
            try:
                print(f"  · '{w.Name}'  class={w.ClassName}")
            except Exception:
                pass
        for w in wins:
            _dump(w, lines)
            lines.append("")

    out = HERE / "room_tree.txt"
    try:
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"저장 완료: {out}  ({len(lines)}줄)")
    except Exception as e:
        print("파일 저장 실패:", e)
        print("\n".join(lines[:200]))

    if wins:
        target = next((w for w in wins if "서랍" in (w.Name or "")), wins[0])
        print(f"\n보정 대상 창: '{target.Name}'"
              + ("  (서랍 창을 찾아 우선 선택함)" if target is not wins[0] else ""))
        calibrate_points(target)


if __name__ == "__main__":
    main()
