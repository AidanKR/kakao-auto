@echo off
chcp 949 >nul
REM 사진·파일 만료 전 백업(카톡이 캐시한 미디어를 아카이브로 복사, 중복제거). 로컬.
cd /d "%~dp0"
set PY=py -3
%PY% --version >nul 2>&1
if errorlevel 1 set PY=python
%PY% media_backup.py
pause
