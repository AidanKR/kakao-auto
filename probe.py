"""
추출 가능성 테스트 도구 (Windows 전용)

tree.txt 결과: 이 카톡은 방목록/메시지가 UIA에 텍스트로 안 잡힘(커스텀 렌더링).
그래서 '클립보드로 대화를 복사해 읽을 수 있는지'를 먼저 확인한다.

사용법:
    1) 카카오톡 로그인
    2) 수집 테스트할 대화방을 "더블클릭"해서 '별도 창'으로 띄운다 (예: [발주] 신화 X KMALL)
    3) probe.bat 실행 (또는 python probe.py > probe.txt)
    → 그 창에서 Ctrl+A / Ctrl+C 를 자동으로 눌러 클립보드에 뭐가 복사되는지 출력한다.

출력(probe.txt)을 그대로 보내주면, 클립보드 방식 가능여부를 판단해 수집기를 그 방식으로 재작성한다.
"""
import sys
import time

try:
    import uiautomation as auto
except ImportError:
    print("uiautomation 미설치.  1_install.bat 먼저 실행")
    sys.exit(1)


def find_class(ctrl, classname, depth=0):
    """ctrl 하위에서 classname 인 첫 컨트롤을 찾는다."""
    if depth > 16:
        return None
    try:
        for c in ctrl.GetChildren():
            if (c.ClassName or "") == classname:
                return c
            r = find_class(c, classname, depth + 1)
            if r:
                return r
    except Exception:
        pass
    return None


def legacy_info(ctrl, label):
    print(f"--- {label} LegacyIAccessible(MSAA) 시도 ---")
    try:
        lp = ctrl.GetLegacyIAccessiblePattern()
    except Exception as e:
        print(f"  LegacyIAccessible 패턴 없음: {e}")
        return
    for attr in ("Name", "Value", "Description"):
        try:
            v = getattr(lp, attr)
            print(f"  {attr} = {repr(v)[:300]}")
        except Exception as e:
            print(f"  {attr} 읽기 실패: {e}")


def main():
    root = auto.GetRootControl()

    # 1) 모든 EVA_VH_ListControl_Dblclk 에 대해 MSAA 로 텍스트가 나오는지 시도
    print("=" * 70)
    print("[1] 리스트 컨트롤 MSAA 텍스트 추출 시도")
    print("=" * 70)
    found = []

    def collect(ctrl, depth=0, win=""):
        if depth > 16:
            return
        try:
            kids = ctrl.GetChildren()
        except Exception:
            return
        for c in kids:
            if (c.ClassName or "") == "EVA_VH_ListControl_Dblclk":
                found.append((win, c))
            collect(c, depth + 1, win)

    for w in root.GetChildren():
        if "EVA_Window" in (w.ClassName or ""):
            collect(w, 0, w.Name or "")
    for win, c in found:
        try:
            r = c.BoundingRectangle
            rect = f"L{r.left},T{r.top},R{r.right},B{r.bottom}"
        except Exception:
            rect = "?"
        print(f"\n[리스트] 창='{win}' Rect={rect}")
        legacy_info(c, "리스트")

    # 2) 클립보드 테스트 (별도 창으로 띄운 대화방 대상)
    print("\n" + "=" * 70)
    print("[2] 클립보드 복사 테스트 (Ctrl+A -> Ctrl+C)")
    print("=" * 70)
    target = None
    for w in root.GetChildren():
        cls = w.ClassName or ""
        nm = w.Name or ""
        if cls == "EVA_Window_Dblclk" and nm and nm != "카카오톡":
            target = w
            break
    if target is None:
        print("별도 창으로 띄운 대화방을 못 찾음.")
        print("→ 대화방을 더블클릭해 '창'으로 띄운 뒤 다시 실행하세요.")
        return

    print(f"대상 창(=방 이름): {target.Name}")
    msg = find_class(target, "EVA_VH_ListControl_Dblclk")
    if msg is None:
        print("메시지 영역을 못 찾음.")
        return
    try:
        target.SetActive()
        time.sleep(0.6)
        msg.Click(simulateMove=False)   # 메시지 영역 클릭
        time.sleep(0.4)
        auto.SetClipboardText("")       # 클립보드 비우기
        time.sleep(0.2)
        auto.SendKeys("{Ctrl}(a)")      # 전체 선택
        time.sleep(0.4)
        auto.SendKeys("{Ctrl}(c)")      # 복사
        time.sleep(0.5)
        txt = auto.GetClipboardText() or ""
    except Exception as e:
        print(f"클립보드 테스트 오류: {e}")
        return

    print(f"클립보드 글자 수: {len(txt)}")
    print("클립보드 내용(앞 2000자):")
    print("-" * 70)
    print(txt[:2000])
    print("-" * 70)
    if len(txt) > 5:
        print(">>> 클립보드 방식 가능성 있음! 이 내용을 보내주세요.")
    else:
        print(">>> 클립보드가 비었음 → 클립보드 방식 불가, OCR 로 가야 함.")


if __name__ == "__main__":
    main()
