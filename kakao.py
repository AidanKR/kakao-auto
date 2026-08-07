"""
KakaoAuto 통합 런처 — 메뉴 하나로 모든 기능 실행. exe(build_exe.bat)로 묶으면
비개발자도 파이썬 설치 없이 KakaoAuto.exe 더블클릭만.

config.json 과 kakao.db 는 이 프로그램(또는 exe) 옆 폴더에 저장됩니다(appdir).
각 모듈은 실제 사용할 때만 로드(uiautomation 없는 환경에서도 메뉴는 뜸).
"""
import importlib
import os
import sys

import appdir

APP = appdir.APP_DIR

MENU = """
================= KakaoAuto =================
  1) 수집 시작 (실시간 · Ctrl+C 로 멈춤)
  2) 정리 (날짜·방별 TXT)
  3) 대시보드 열기
  4) 통합 검색 열기
  5) 관계망 열기
  6) 엑셀 내보내기
  7) 금액·약속 추출
  8) 사진·파일 백업
  9) DB 백업
 10) 일일 브리핑 / 응답대기
  0) 종료
============================================"""


def _open(path):
    p = str(path)
    if not os.path.exists(p):
        print(f"  (파일 없음: {p})")
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(p)  # noqa
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", p])
        else:
            import subprocess
            subprocess.run(["xdg-open", p])
    except Exception as e:
        print(f"  열기 실패(직접 열어주세요: {p}): {e}")


def _run(mod, argv=None):
    try:
        m = importlib.import_module(mod)
    except SystemExit:
        return
    except Exception as e:
        print(f"  [{mod}] 로드 실패: {e}")
        return
    old = sys.argv
    sys.argv = [mod] + (argv or [])
    try:
        m.main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\n  중단됨(메뉴로 돌아갑니다)")
    except Exception as e:
        print(f"  [{mod}] 실행 오류: {e}")
    finally:
        sys.argv = old


def main():
    actions = {
        "1": lambda: _run("collector"),
        "2": lambda: _run("consolidate"),
        "3": lambda: (_run("dashboard", ["--out", str(APP / "dashboard.html")]), _open(APP / "dashboard.html")),
        "4": lambda: (_run("search", ["--out", str(APP / "검색.html")]), _open(APP / "검색.html")),
        "5": lambda: (_run("graph_export", ["--out", str(APP / "kakao_2d.html")]), _open(APP / "kakao_2d.html")),
        "6": lambda: (_run("export_excel", ["--out", str(APP / "카카오톡.xlsx")]), _open(APP / "카카오톡.xlsx")),
        "7": lambda: (_run("extract", ["--out", str(APP / "추출_금액약속.csv")]), _open(APP / "추출_금액약속.csv")),
        "8": lambda: _run("media_backup"),
        "9": lambda: _run("backup"),
        "10": lambda: _run("briefing"),
    }
    while True:
        print(MENU)
        try:
            ch = input("선택> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if ch in ("0", "q", "Q"):
            break
        act = actions.get(ch)
        if act:
            act()
            print()
        else:
            print("  잘못된 선택입니다.")
    print("종료합니다.")


if __name__ == "__main__":
    main()
