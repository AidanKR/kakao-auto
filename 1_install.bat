@echo off
chcp 949 >nul
cd /d "%~dp0"

REM 파이썬 확인
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 (
  set PY=python
  python --version >nul 2>&1
)
if errorlevel 1 goto nopython

echo [확인] 파이썬 발견:
%PY% --version
echo.

echo [설치] pip 업그레이드...
%PY% -m pip install --upgrade pip
echo [설치] uiautomation / pywin32 / openai ...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [오류] 설치 실패. 인터넷 연결을 확인하세요.
  echo        오프라인 PC면, 인터넷 되는 PC에서 whl 파일을 받아와 오프라인 설치해야 합니다.
  pause
  exit /b
)
echo.
echo [완료] 설치 끝. 이제 2_discover.bat 을 실행하세요.
pause
exit /b

:nopython
echo ============================================================
echo  파이썬(Python)이 설치돼 있지 않습니다. 먼저 설치하세요.
echo ============================================================
echo  1) 열리는 페이지에서 "Download Python 3.x" 클릭
echo  2) 설치 실행 시 맨 아래  [x] Add python.exe to PATH  반드시 체크!
echo  3) 설치 끝나면 이 창 닫고 1_install.bat 을 다시 실행
echo ============================================================
start "" https://www.python.org/downloads/windows/
pause
exit /b
