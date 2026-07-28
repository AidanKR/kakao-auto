"""
카카오톡 PC 창 구조 탐지 도구 (Windows 전용)

목적: 지금 설치된 카카오톡 버전의 창/컨트롤 트리를 덤프해서,
      메시지 목록이 어느 컨트롤에 들어있는지 찾아낸다.
      (카톡 버전마다 ClassName/구조가 달라서, 수집기를 짜기 전에 먼저 실측한다)

사용법(cycle 모드 기준 — 권장):
    1) 카카오톡 로그인, 메인 창을 크게 연다
    2) 채팅 탭에서 아무 방이나 '한 번 클릭'해 오른쪽에 대화가 보이게 한다
    3) python discover.py > tree.txt
    → 이때 왼쪽 '채팅목록 리스트'와 오른쪽 '메시지 리스트'가 둘 다 트리에 찍힌다.
      Rect(L=왼쪽좌표) 로 좌/우 패널을 구분한다.

tree.txt 를 그대로 보내주면 구조에 맞춰 collector.py(chat_list_class 등)를 고정한다.
"""
import sys

try:
    import uiautomation as auto
except ImportError:
    print("uiautomation 미설치. 먼저:  pip install -r requirements.txt")
    sys.exit(1)


def dump(control, depth=0, max_depth=12):
    """UIA 컨트롤 트리를 들여쓰기로 출력."""
    if depth > max_depth:
        return
    name = (control.Name or "").replace("\n", "\\n")
    if len(name) > 60:
        name = name[:60] + "…"
    indent = "  " * depth
    try:
        r = control.BoundingRectangle
        rect = f"L{r.left},T{r.top},R{r.right},B{r.bottom}"
    except Exception:
        rect = "?"
    print(
        f"{indent}[{control.ControlTypeName}] "
        f"Class={control.ClassName!r} "
        f"AutoId={control.AutomationId!r} "
        f"Rect={rect} "
        f"Name={name!r}"
    )
    try:
        for child in control.GetChildren():
            dump(child, depth + 1, max_depth)
    except Exception as e:
        print(f"{indent}  (children 읽기 실패: {e})")


def main():
    root = auto.GetRootControl()
    found = False
    # 최상위 창들 중 카카오톡 관련 창만 골라서 덤프
    for win in root.GetChildren():
        cls = win.ClassName or ""
        nm = win.Name or ""
        is_kakao = (
            "EVA_Window" in cls          # 카톡 메인 창
            or "카카오톡" in nm
            or cls == "#32770"            # 팝업/대화방 창(다이얼로그)
            or "OnlineMainView" in cls
        )
        if not is_kakao:
            continue
        found = True
        print("=" * 80)
        print(f"TOP WINDOW  Class={cls!r}  Name={nm!r}")
        print("=" * 80)
        dump(win, 0)
        print()

    if not found:
        print("카카오톡 창을 못 찾음.")
        print("- 카톡이 로그인/실행 중인지 확인")
        print("- 대화방을 더블클릭해서 별도 창으로 띄운 뒤 다시 실행해 보세요")


if __name__ == "__main__":
    main()
