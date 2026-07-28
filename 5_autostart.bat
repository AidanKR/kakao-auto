@echo off
chcp 949 >nul
cd /d "%~dp0"
echo ============================================================
echo  무인 자동 실행 등록 (재부팅에도 자동 지속) - 관리자 권한 불필요
echo ============================================================

REM 1) 로그인 시 수집기 자동시작 = '시작프로그램' 폴더에 실행기 등록
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
echo [1/8] 시작프로그램에 수집기 자동시작 등록...
> "%STARTUP%\KakaoCollector.bat" echo @echo off
>> "%STARTUP%\KakaoCollector.bat" echo start "" "%~dp0watchdog.bat"
if exist "%STARTUP%\KakaoCollector.bat" (echo   등록됨) else (echo   [실패] 시작프로그램 등록 실패)

REM 2~3) 하루 2번 자동 정리
echo [2/8] 매일 11:50 정리 등록...
schtasks /Create /TN "KakaoConsolidate_1150" /TR "\"%~dp0run_consolidate.bat\"" /SC DAILY /ST 11:50 /F
echo [3/8] 매일 23:50 정리 등록...
schtasks /Create /TN "KakaoConsolidate_2350" /TR "\"%~dp0run_consolidate.bat\"" /SC DAILY /ST 23:50 /F

REM 4) 30분마다 건강 점검
echo [4/8] 30분마다 건강 점검 등록...
schtasks /Create /TN "KakaoHealthCheck" /TR "\"%~dp06_healthcheck.bat\"" /SC MINUTE /MO 30 /F

REM 5) 매일 아침 브리핑/응답대기
echo [5/8] 매일 08:30 일일 브리핑 등록...
schtasks /Create /TN "KakaoBriefing" /TR "\"%~dp07_briefing.bat\"" /SC DAILY /ST 08:30 /F

REM 6) 매일 새벽 DB 백업
echo [6/8] 매일 02:00 DB 백업 등록...
schtasks /Create /TN "KakaoBackup" /TR "\"%~dp08_backup.bat\"" /SC DAILY /ST 02:00 /F

REM 7) 절전/화면보호기/잠금 끄기
echo [7/8] 절전/화면보호기/잠금 끄는 중...
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 0
powercfg /SETACTIVE SCHEME_CURRENT
reg add "HKCU\Control Panel\Desktop" /v ScreenSaveActive /t REG_SZ /d 0 /f >nul 2>&1
reg add "HKCU\Control Panel\Desktop" /v ScreenSaveTimeOut /t REG_SZ /d 0 /f >nul 2>&1
reg add "HKCU\Control Panel\Desktop" /v ScreenSaverIsSecure /t REG_SZ /d 0 /f >nul 2>&1

echo.
echo [8/8] 지금 바로 수집기를 시작할까요?
choice /M "지금 수집기 시작"
if errorlevel 2 goto after
start "" "%~dp0watchdog.bat"
:after

echo.
echo ============================================================
echo  [남은 1회 설정] '계정 로그인'이라 사람이 1번만:
echo   - 카카오톡: "PC 켤 때 자동 실행" + "자동 로그인" 켜고 1번 로그인
echo   (윈도우 암호 없으면 부팅 시 자동 로그인 - 할 것 없음)
echo ============================================================
echo  자동시작 해제: 탐색기 주소창에 shell:startup -^> KakaoCollector.bat 삭제
echo  작업 해제:  schtasks /Delete /TN KakaoBackup /F  (등)
pause
