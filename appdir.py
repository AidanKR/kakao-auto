"""앱 기준 폴더 — 개발 시엔 소스 폴더, exe(PyInstaller)로 묶이면 exe 옆 폴더.
DB·config.json·출력물이 exe 옆에 저장되도록(임시폴더 유실 방지)."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):          # PyInstaller 등으로 exe 화된 경우
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent


def _set_dpi_aware():
    """모든 모듈이 이 파일을 먼저 import 하므로 여기서 프로세스를 DPI-aware 로.
    노트북+외장모니터처럼 배율(DPI)이 다른 화면이 섞이면, DPI 를 모르는 프로세스는
    윈도우가 좌표를 '가상으로 줄여서' 주기 때문에 UIA 창 좌표·마우스 좌표·클릭 위치가
    서로 어긋난다(클릭이 빗나감). Per-Monitor v2 → Per-Monitor → System 순으로 시도."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        try:   # Windows 10 1703+ : DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                return
        except Exception:
            pass
        try:   # Windows 8.1+ : PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass
        try:   # Vista+
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        pass


_set_dpi_aware()
