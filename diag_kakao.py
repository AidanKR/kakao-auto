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
        print("이 파일(kakao_tree.txt) 내용을 보내주세요 — 채팅 탭 위치를 정확히 잡겠습니다.")
    except Exception as e:
        print("파일 저장 실패:", e)
        print("\n".join(lines[:200]))


if __name__ == "__main__":
    main()
