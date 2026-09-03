"""
KakaoAuto 통합 런처 — 메뉴 하나로 모든 기능 실행. exe(build_exe.bat)로 묶으면
비개발자도 파이썬 설치 없이 KakaoAuto.exe 더블클릭만.

config.json 과 kakao.db 는 이 프로그램(또는 exe) 옆 폴더에 저장됩니다(appdir).
각 모듈은 실제 사용할 때만 로드(uiautomation 없는 환경에서도 메뉴는 뜸).

명령줄(무인 자동/예약에서 사용):
  KakaoAuto.exe nightly        [야간 배치] 전체 1회 수집 → 정리 → 종료
  KakaoAuto.exe collect        수집기만 실행(계속 반복, Ctrl+C 종료)
  KakaoAuto.exe consolidate    정리 1회 실행 후 종료
  KakaoAuto.exe dashboard      대시보드 생성 후 열기
  KakaoAuto.exe autostart      무인 자동 등록(매일 02:00 야간 배치)
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
 11) 무인 자동 설정 (매일 새벽 02:00 → 전체 수집 → 정리 → 종료)
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


NIGHTLY_TASK = "KakaoAuto Nightly"
_LEGACY_TASKS = ["KakaoAuto Consolidate AM", "KakaoAuto Consolidate PM"]


def _nightly_time():
    """config.json 의 nightly_time(HH:MM, 로컬시간=이 PC 시간). 없으면 02:00."""
    import json
    import re
    try:
        d = json.loads((APP / "config.json").read_text(encoding="utf-8"))
        t = str(d.get("nightly_time", "02:00")).strip()
        if re.match(r"^\d{1,2}:\d{2}$", t):
            hh, mm = t.split(":")
            return f"{int(hh):02d}:{mm}"
    except Exception:
        pass
    return "02:00"


def _nightly():
    """[야간 배치] 전체 1회 수집 → 정리 → 종료. 예약작업이 이걸 호출."""
    print("=== KakaoAuto 야간 배치 시작 ===")
    print("[1/2] 전체 대화 1회 수집...")
    _run("collector", ["once"])
    print("[2/2] 정리(날짜·방별 TXT)...")
    _run("consolidate")
    print("=== 완료. 종료합니다. ===")


def setup_autostart():
    """매일 지정 시각(기본 02:00)에 '전체 수집 → 정리 → 종료' 배치를 예약. 관리자 권한 불필요."""
    if not sys.platform.startswith("win"):
        print("  무인 자동 설정은 윈도우에서만 됩니다.")
        return
    import subprocess

    st = _nightly_time()
    # 예전(연속형) 잔재가 있으면 정리
    _clean_legacy(subprocess)

    r = subprocess.run(
        ["schtasks", "/create", "/tn", NIGHTLY_TASK, "/tr", _self_cmd("nightly"),
         "/sc", "daily", "/st", st, "/f"],
        capture_output=True, text=True)
    ok = r.returncode == 0
    if not ok:
        print(f"  [예약 실패] {(r.stderr or r.stdout).strip()}")

    # 02시에 PC가 깨어 있도록 절전 끄기(권한 없으면 조용히 무시 — 안내로 보완)
    for a in (["powercfg", "/change", "standby-timeout-ac", "0"],
              ["powercfg", "/change", "hibernate-timeout-ac", "0"]):
        subprocess.run(a, capture_output=True, text=True)

    print("\n  ── 무인 자동(야간 배치) ──")
    print(f"   - 매일 {st} 에: 전체 수집 → 정리 → 자동 종료  ({'등록됨' if ok else '실패(위 메시지)'})")
    print("   * 시간은 이 PC의 로컬 시간 기준입니다(한국이면 한국시간 02:00).")
    print("     바꾸려면 config.json 의 \"nightly_time\": \"02:00\" 수정 후 이 메뉴를 다시 실행.")
    print("   * 02시에 PC가 켜져 있고(절전/최대절전 꺼짐), 로그인·잠금해제 상태여야 합니다.")
    print("   * 카톡은 'PC 켤 때 자동 실행' + '자동 로그인' 을 켜두세요(무인 전제).")
    print("   * 배치가 도는 몇 분간은 이 PC의 마우스/키보드를 쓰지 마세요(GUI 조작 중).")
    print("   지금 한 번 테스트: 메뉴에서 그냥 1)수집 → 2)정리 를 돌려 보거나,")
    print("   명령창에서  KakaoAuto.exe nightly  를 직접 실행해도 됩니다.")


def _clean_legacy(subprocess):
    wd = os.path.join(_startup_dir(), "KakaoAuto_collect.cmd")
    try:
        if os.path.exists(wd):
            os.remove(wd)
    except Exception:
        pass
    for tn in _LEGACY_TASKS:
        subprocess.run(["schtasks", "/delete", "/tn", tn, "/f"],
                       capture_output=True, text=True)


def remove_autostart():
    if not sys.platform.startswith("win"):
        print("  윈도우 전용입니다.")
        return
    import subprocess
    subprocess.run(["schtasks", "/delete", "/tn", NIGHTLY_TASK, "/f"],
                   capture_output=True, text=True)
    _clean_legacy(subprocess)
    print("  무인 자동(야간 배치) 해제 완료.")


def _dashboard():
    _run("dashboard", ["--out", str(APP / "dashboard.html")])
    _open(APP / "dashboard.html")


# ── 명령줄(예약/무인에서 호출) ───────────────────────────
def _run_cli(cmd):
    cmd = cmd.lower()
    if cmd in ("nightly", "batch", "야간"):
        _nightly()
    elif cmd in ("collect", "collector"):
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
        print("  사용: nightly | collect | consolidate | dashboard | autostart | autostart-off")


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
