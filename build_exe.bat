@echo off
chcp 949 >nul
REM KakaoAuto.exe 빌드 (PyInstaller). 개발자/배포용. 1회 실행.
REM 결과: dist\KakaoAuto.exe  →  config.json 을 exe 옆에 두고 실행.
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python

echo [1/2] 빌드 도구·라이브러리 설치...
%PY% -m pip install --upgrade pyinstaller
%PY% -m pip install --upgrade -r requirements.txt

echo.
echo [2/2] KakaoAuto.exe 빌드 (몇 분 걸립니다)...
%PY% -m PyInstaller --onefile --name KakaoAuto ^
  --collect-submodules uiautomation ^
  --collect-submodules comtypes ^
  --hidden-import win32gui --hidden-import win32con --hidden-import win32api --hidden-import win32process ^
  --hidden-import openpyxl --hidden-import cryptography ^
  kakao.py

echo.
if exist "dist\KakaoAuto.exe" (
  echo [완료] dist\KakaoAuto.exe 생성됨.
  echo   - config.json 을 exe 와 같은 폴더에 두세요(없으면 config.example.json 복사).
  echo   - kakao.db·출력물도 exe 옆에 저장됩니다.
) else (
  echo [실패] 빌드가 안 됐습니다. 위 로그의 오류를 확인하세요.
)
pause
