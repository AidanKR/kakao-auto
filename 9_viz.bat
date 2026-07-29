@echo off
chcp 949 >nul
REM 3D 관계망(방-사람) 생성 후 브라우저로 열기. LLM/전송 없음(로컬 처리).
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% graph_export.py --out "%~dp0kakao_2d.html"
if exist "%~dp0kakao_2d.html" start "" "%~dp0kakao_2d.html"
pause
