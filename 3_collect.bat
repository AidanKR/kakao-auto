@echo off
chcp 949 >nul
REM 수집기 실행 (창 유지, Ctrl+C 로 종료)
cd /d "%~dp0"
if not exist config.json (
  echo [안내] config.json 이 없습니다. config.example.json 을 복사해서 만듭니다...
  copy config.example.json config.json >nul
  echo config.json 을 메모장으로 열어 설정을 맞춘 뒤 저장하고 다시 실행하세요.
  notepad config.json
  pause
  exit /b
)
python collector.py
pause
