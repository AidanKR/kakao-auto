"""
진단 — 열려 있는 '대화방 창'의 UIA 구조를 덤프하고, 사진첩 버튼 좌표를 보정한다.

카카오톡 대화방에서 받은 사진은 캐시에 .cng 로 암호화돼 있어 그대로는 못 쓴다(2026-09-22 실측).
대신 카카오톡 자신에게 '사진/동영상 모아보기 → 저장'을 시키면 평문으로 떨어진다.
그 버튼을 추측 좌표로 누르면 안 되므로(채팅 탭에서 겪은 전례), 여기서 실제 구조를 먼저 잰다.

쓰는 법:
  1) 카카오톡에서 대화방을 하나 열어 둔다(사진이 있는 방이면 더 좋다).
  2) KakaoAuto.exe diagroom   (또는 python diag_room.py)
  3) room_tree.txt 를 개발자에게 보낸다.
  4) 안내가 나오면 마우스를 '사진/동영상' 버튼 위에 올려둔다 → 좌표가 config 에 저장된다.

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


def _room_windows(auto):
    """메인 창을 뺀 대화방 창들. collector.chat_windows_by_handle 과 같은 기준."""
    out = []
    for w in auto.GetRootControl().GetChildren():
        try:
            if (w.ClassName or "") == "EVA_Window_Dblclk" \
                    and (w.Name or "").strip() and (w.Name or "") != "카카오톡":
                out.append(w)
        except Exception:
            continue
    return out


def _dump(win, lines):
    try:
        r = win.BoundingRectangle
        lines.append(f"[대화방 '{win.Name}'] rect=({r.left},{r.top},{r.right},{r.bottom}) "
                     f"size={r.right - r.left}x{r.bottom - r.top}")
        base_l, base_t = r.left, r.top
    except Exception:
        lines.append(f"[대화방 '{win.Name}'] rect 읽기 실패")
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


def calibrate(win, seconds=8):
    """마우스를 '사진/동영상' 버튼에 올려두게 하고 창 기준 상대좌표를 config 에 저장."""
    try:
        r = win.BoundingRectangle
    except Exception:
        print("  창 좌표를 못 읽어 보정을 건너뜁니다.")
        return
    print()
    print("  ── 사진첩 버튼 좌표 보정 ──")
    print("  대화방에서 '사진/동영상'(또는 서랍·목록 보기) 버튼 위에 마우스를 올려두세요.")
    print(f"  {seconds}초 뒤 그 지점을 저장합니다. 누르지 말고 올려만 두세요.")
    for i in range(seconds, 0, -1):
        print(f"    {i}...", end="\r", flush=True)
        time.sleep(1)
    x, y = _cursor_pos()
    rel_x, rel_y = x - r.left, y - r.top
    print(f"  잰 좌표: 화면({x},{y}) · 창기준({rel_x},{rel_y})           ")
    if not (0 <= rel_x <= (r.right - r.left) and 0 <= rel_y <= (r.bottom - r.top)):
        print("  ⚠ 대화방 창 밖입니다. 저장하지 않습니다. 다시 실행해 주세요.")
        return
    cfg = _load_cfg_raw()
    cfg["room_album_btn"] = [rel_x, rel_y]
    cfg["_room_album_btn"] = ("대화방 '사진/동영상' 버튼의 창 기준 상대좌표 [x,y]. "
                              "메뉴 15(대화방 진단)에서 마우스를 올려두면 자동 저장.")
    try:
        (HERE / "config.json").write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  config.json 에 저장했습니다: room_album_btn = [{rel_x}, {rel_y}]")
    except Exception as e:
        print("  저장 실패:", e)


def main():
    try:
        import uiautomation as auto
    except Exception as e:
        print("uiautomation 로드 실패:", e)
        return

    wins = _room_windows(auto)
    lines = []
    if not wins:
        msg = ("열려 있는 대화방 창이 없습니다. "
               "카카오톡에서 대화방을 하나 열어 두고 다시 실행하세요.")
        print(msg)
        lines.append(msg)
    else:
        print(f"대화방 창 {len(wins)}개 발견 — 구조를 뜹니다.")
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
        calibrate(wins[0])


if __name__ == "__main__":
    main()
