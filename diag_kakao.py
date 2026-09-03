"""
진단 — 카카오톡 메인 창의 UIA 구조를 파일로 덤프한다.
'채팅' 탭 등 클릭 대상을 추측이 아니라 실제 이름·좌표로 잡기 위한 도구.

출력: <appdir>/kakao_tree.txt  (이 내용을 개발자에게 보내면 채팅 탭 위치를 정확히 지정)
사용: python diag_kakao.py   /   KakaoAuto.exe diag
"""
HERE = __import__("appdir").APP_DIR


def main():
    try:
        import uiautomation as auto
    except Exception as e:
        print("uiautomation 로드 실패:", e)
        return

    root = auto.GetRootControl()
    main_win = None
    for w in root.GetChildren():
        try:
            if (w.ClassName or "") == "EVA_Window_Dblclk" and (w.Name or "") == "카카오톡":
                main_win = w
                break
        except Exception:
            continue

    lines = []
    if main_win is None:
        lines.append("카카오톡 메인 창을 못 찾음 — 카톡 실행/로그인 후 다시 실행하세요.")
    else:
        try:
            r = main_win.BoundingRectangle
            lines.append(f"[메인창 '카카오톡'] rect=({r.left},{r.top},{r.right},{r.bottom}) "
                         f"size={r.right - r.left}x{r.bottom - r.top}")
        except Exception:
            lines.append("[메인창] rect 읽기 실패")

        clickable = {"ButtonControl", "TabItemControl", "ListItemControl",
                     "HyperlinkControl", "MenuItemControl", "ImageControl",
                     "TextControl", "CheckBoxControl", "RadioButtonControl"}

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
                    if nm or ct in clickable:
                        lines.append(
                            f"{'  ' * depth}- {ct} name='{nm[:40]}' class='{cn}' "
                            f"rect=({rr.left},{rr.top},{rr.right},{rr.bottom})")
                except Exception:
                    pass
                walk(ch, depth + 1)

        walk(main_win)

    out = HERE / "kakao_tree.txt"
    try:
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"저장 완료: {out}  ({len(lines)}줄)")
    except Exception as e:
        print("파일 저장 실패:", e)
        print("\n".join(lines[:200]))

    if main_win is not None:
        calibrate_chat_tab(main_win)


def _cursor_pos():
    """현재 마우스 화면 좌표 (ctypes, 추가 라이브러리 불필요)."""
    import ctypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def _load_cfg_raw():
    import json
    p = HERE / "config.json"
    if not p.exists():
        return {}
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return json.loads(data.decode(enc))
        except Exception:
            try:
                return json.loads(data.decode(enc).replace("\\", "/"))
            except Exception:
                continue
    return {}


def calibrate_chat_tab(main_win, seconds=6):
    """마우스를 카톡 '채팅' 아이콘 위에 올려두면 그 좌표를 읽어 config.json 에 저장.
    왼쪽 탭 내비는 카톡이 직접 그려 UIA로 못 잡으므로, 사용자가 위치를 찍어주는 게 가장 확실."""
    import json
    import sys
    import time

    if not sys.platform.startswith("win"):
        return
    try:
        r = main_win.BoundingRectangle
    except Exception:
        print("메인창 좌표를 못 읽어 보정을 건너뜁니다.")
        return

    print()
    print("=== 채팅 탭 위치 자동 보정 ===")
    print(f"  {seconds}초 안에 **마우스를 카톡 왼쪽의 '채팅' 아이콘 위에 올려두세요** (클릭 안 해도 됨).")
    for i in range(seconds, 0, -1):
        print(f"  {i}...", end="", flush=True)
        time.sleep(1)
    print()
    try:
        sx, sy = _cursor_pos()
    except Exception as e:
        print("  마우스 좌표 읽기 실패:", e)
        return
    rel_x, rel_y = sx - r.left, sy - r.top
    inside = r.left <= sx <= r.right and r.top <= sy <= r.bottom
    print(f"  마우스 화면좌표=({sx},{sy}) → 카톡 창 기준=({rel_x},{rel_y})  창={r.right - r.left}x{r.bottom - r.top}")
    if not inside:
        print("  ⚠ 마우스가 카톡 창 밖에 있었습니다. 메뉴 14를 다시 실행해 채팅 아이콘 위에 올려두세요.")
        return

    cfg = _load_cfg_raw()
    old_ys = cfg.get("chat_tab_scan_y") or []
    new_ys = [rel_y] + [y for y in old_ys if y != rel_y]
    cfg["chat_tab_nav_x"] = rel_x
    cfg["chat_tab_scan_y"] = new_ys
    try:
        (HERE / "config.json").write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ config.json 저장: chat_tab_nav_x={rel_x}, chat_tab_scan_y 맨 앞에 {rel_y} 추가.")
        print("  이제 메뉴 1(수집) 또는 야간 배치가 프로필 탭에서도 채팅 탭으로 자동 전환됩니다.")
    except Exception as e:
        print("  config.json 저장 실패:", e)
        print(f"  수동으로 넣어주세요: \"chat_tab_nav_x\": {rel_x}, \"chat_tab_scan_y\": [{rel_y}, ...]")


if __name__ == "__main__":
    main()
