"""앱 기준 폴더 — 개발 시엔 소스 폴더, exe(PyInstaller)로 묶이면 exe 옆 폴더.
DB·config.json·출력물이 exe 옆에 저장되도록(임시폴더 유실 방지)."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):          # PyInstaller 등으로 exe 화된 경우
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
