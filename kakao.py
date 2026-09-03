"""
KakaoAuto 통합 런처 — 메뉴 하나로 모든 기능 실행. exe(build_exe.bat)로 묶으면
비개발자도 파이썬 설치 없이 KakaoAuto.exe 더블클릭만.

config.json 과 kakao.db 는 이 프로그램(또는 exe) 옆 폴더에 저장됩니다(appdir).
각 모듈은 실제 사용할 때만 로드(uiautomation 없는 환경에서도 메뉴는 뜸).

명령줄(무인 자동/예약에서 사용):
  KakaoAuto.exe collect        수집기만 실행(메뉴 없이, Ctrl+C 종료)
  KakaoAuto.exe consolidate    정리 1회 실행 후 종료
  KakaoAuto.exe dashboard      대시보드 생성 후 열기
  KakaoAuto.exe autostart      무인 자동 등록(부팅 시 수집 + 정리 하루 2번)
  KakaoAuto.exe autostart-off  무인 자동 해제
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
 11) 무인 자동 설정 (PC 켜면 수집 자동 + 정리 하루 2번)
 12) 무인 자동 해제
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


# ── 무인 자동(윈도우) ─────────────────────────────────────
def _self_cmd(action):
    """이 앱을 하위명령과 함께 실행하는 명령 문자열(따옴표 포함)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" {action}'          # KakaoAuto.exe
    return f'"{sys.executable}" "{os.path.join(str(APP), "kakao.py")}" {action}'


def _startup_dir():
    return os.path.join(os.environ.get("APPDATA", ""),
                        r"Microsoft\Windows\Start Menu\Programs\Startup")


def setup_autostart():
    """부팅 시 수집 자동시작(감시 재시작) + 정리 하루 2번 예약. 관리자 권한 불필요."""
    if not sys.platform.startswith("win"):
        print("  무인 자동 설정은 윈도우에서만 됩니다.")
        return
    import subprocess

    # 1) 로그인 시 수집 자동시작 — 시작프로그램 폴더에 감시(재시작) 배치
    sd = _startup_dir()
    os.makedirs(sd, exist_ok=True)
    wd = os.path.join(sd, "KakaoAuto_collect.cmd")
    lines = [
        "@echo off",
        "chcp 949 >nul",
        "title KakaoAuto Collector (auto)",
        ':loop',
        _self_cmd("collect"),
        "echo.",
        "echo [KakaoAuto] 수집기가 멈춤 - 5초 뒤 자동 재시작 (이 창을 닫으면 완전 종료)",
        "timeout /t 5 /nobreak >nul",
        "goto loop",
        "",
    ]
    try:
        with open(wd, "w", encoding="cp949", newline="\r\n") as f:
            f.write("\n".join(lines))
        startup_ok = True
    except Exception as e:
        startup_ok = False
        print(f"  [시작프로그램 등록 실패] {e}")

    # 2) 정리 하루 2번(11:50 / 23:50) — 사용자 수준 예약작업
    cons = _self_cmd("consolidate")
    sched_ok = True
    for tn, st in [("KakaoAuto Consolidate AM", "11:50"),
                   ("KakaoAuto Consolidate PM", "23:50")]:
        r = subprocess.run(
            ["schtasks", "/create", "/tn", tn, "/tr", cons,
             "/sc", "daily", "/st", st, "/f"],
            capture_output=True, text=True)
        if r.returncode != 0:
            sched_ok = False
            print(f"  [예약 실패] {tn}: {(r.stderr or r.stdout).strip()}")

    print("\n  ── 무인 자동 설정 ──")
    print(f"   - 수집 자동시작: {'등록됨' if startup_ok else '실패'}  ({wd})")
    print(f"   - 정리 자동(매일 11:50, 23:50): {'등록됨' if sched_ok else '일부 실패(위 메시지)'}")
    print("   * 지금 재부팅하거나 위 cmd를 한 번 실행하면 수집이 자동으로 시작됩니다.")
    print("   * 카톡 설정에서 'PC 켤 때 자동 실행' + '자동 로그인'을 켜두세요(무인 전제).")
    print("   * 순회 중엔 이 PC의 마우스/키보드를 사람이 쓰기 어렵습니다(전용 PC 권장).")


def remove_autostart():
    if not sys.platform.startswith("win"):
        print("  윈도우 전용입니다.")
        return
    import subprocess
    wd = os.path.join(_startup_dir(), "KakaoAuto_collect.cmd")
    try:
        if os.path.exists(wd):
            os.remove(wd)
            print(f"  삭제: {wd}")
    except Exception as e:
        print(f"  시작프로그램 삭제 실패: {e}")
    for tn in ["KakaoAuto Consolidate AM", "KakaoAuto Consolidate PM"]:
        subprocess.run(["schtasks", "/delete", "/tn", tn, "/f"],
                       capture_output=True, text=True)
    print("  무인 자동 해제 완료. (실행 중인 수집 창은 닫으면 멈춥니다)")


def _dashboard():
    _run("dashboard", ["--out", str(APP / "dashboard.html")])
    _open(APP / "dashboard.html")


# ── 명령줄(예약/무인에서 호출) ───────────────────────────
def _run_cli(cmd):
    cmd = cmd.lower()
    if cmd in ("collect", "collector"):
        _run("collector")
    elif cmd in ("consolidate", "정리"):
        _run("consolidate")
    elif cmd == "dashboard":
        _dashboard()
    elif cmd in ("autostart", "auto", "autostart-on"):
        setup_autostart()
    elif cmd in ("autostart-off", "auto-off", "unautostart"):
        remove_autostart()
    else:
        print(f"  알 수 없는 명령: {cmd}")
        print("  사용: collect | consolidate | dashboard | autostart | autostart-off")


def main():
    args = [a for a in sys.argv[1:] if a.strip()]
    if args:                                   # 명령줄 모드(메뉴 없이 1회)
        _run_cli(args[0])
        return

    actions = {
        "1": lambda: _run("collector"),
        "2": lambda: _run("consolidate"),
        "3": _dashboard,
        "4": lambda: (_run("search", ["--out", str(APP / "검색.html")]), _open(APP / "검색.html")),
        "5": lambda: (_run("graph_export", ["--out", str(APP / "kakao_2d.html")]), _open(APP / "kakao_2d.html")),
        "6": lambda: (_run("export_excel", ["--out", str(APP / "카카오톡.xlsx")]), _open(APP / "카카오톡.xlsx")),
        "7": lambda: (_run("extract", ["--out", str(APP / "추출_금액약속.csv")]), _open(APP / "추출_금액약속.csv")),
        "8": lambda: _run("media_backup"),
        "9": lambda: _run("backup"),
        "10": lambda: _run("briefing"),
        "11": setup_autostart,
        "12": remove_autostart,
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
