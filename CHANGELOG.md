# Changelog

All notable changes to **kakao-auto** are documented here.
Downloads: [Releases](https://github.com/AidanKR/kakao-auto/releases) · one-click Windows installer (`KakaoAuto-Setup.exe`).

## v1.1.1
- **공유폴더 정리** — 날짜 폴더가 루트에 쌓이던 것을 **`txt/` 하위로** 모았습니다(`txt_subdir`, 기본 `"txt"`). 루트는 `csv/ · txt/ · media/ · kakao.db` 만 남아 깔끔합니다.
- **TXT 아예 끄기** — CSV만 쓰면 `nightly_txt: false` 로 두면 날짜 폴더가 생기지 않습니다.

## v1.1.0 (최종형)
- **[Enter] 한 번 = 전체 실행** — 메뉴에서 그냥 Enter 만 누르면 **수집 → 정리(TXT) → 방별 CSV → 사진 백업**이 한 번에 이어집니다. 숫자를 여러 번 누를 필요 없음(개별 실행은 그대로 1~14).
- **운영 방식 = 카톡 켜둔 채로** — `close_kakao_after` 기본값을 `false`로. 카카오톡을 **'채팅' 탭에 켜두면** 배치가 실행·종료를 건드리지 않고 바로 수집합니다(가장 안정적).
- 메뉴 상단에 전제 안내 고정: "카카오톡을 켜고 '채팅' 탭으로 두세요".
- 무인 자동(메뉴 11)도 매일 02:00 에 같은 '전체 실행'을 수행.

## v1.0.8
- **채팅 탭 자동 전환(Ctrl+2)** — 카톡이 프로필/친구 탭에서 시작해도 수집 전에 `Ctrl+2`로 채팅 탭으로 전환(가장 확실). UIA·좌표 폴백 포함, `chat_tab_hotkey`로 조절.

## v1.0.7
- 카톡이 프로필/친구 탭에서 시작하면 채팅목록을 못 찾던 문제 → **채팅 탭 자동 클릭**(UIA 이름 검색 + 좌표 폴백 `chat_tab_offset`).

## v1.0.6
- **방별 폴더 구조** — `share_dir/csv/<방>/<방>.csv` (방마다 폴더 하나 + CSV 하나) + `_rooms_index.csv`.
- **야간 배치가 카톡까지 켜고 끔** — 02:00에 카톡 자동 실행(자동 로그인 대기 `kakao_boot_wait`) → 작업 → `taskkill`로 종료(`close_kakao_after`). 경로 자동탐지/`kakao_exe`.
- **실제 사진만(이모티콘 제외)** — 이모티콘·스티커 캐시 폴더/파일명과 작은 썸네일(`media_min_bytes` 미만) 제외. `image_only`로 이미지만.
- 야간 배치에 사진 백업 단계 포함(`nightly_media`).

## v1.0.5
- **방별 CSV 내보내기** — DB를 방 하나당 CSV 하나로(`utf-8-sig`, 컬럼 `room,date,time,datetime,sender,message`). 엑셀·pandas 그대로. 메뉴 13 / CLI `csv` / 야간 배치 포함.

## v1.0.4
- **무인 야간 배치(매일 02:00)** — 계속 도는 방식 대신 **전체 1회 수집 → 정리 → 종료**. 메뉴 11로 예약 등록(사용자 권한 `schtasks` + 절전 끄기), `nightly_time`으로 시각 변경. `collector once`.
- **일시적 오류 경보 완화** — 일회성 UIA COMError는 WARN, `error_alerts_after`(기본 3) 연속 지속 시에만 CRITICAL.

## v1.0.2 – v1.0.3
- **exe 포장 버그 수정** — 동적 로드 모듈이 exe에 빠져 `No module named 'collector'` 나던 문제 → 프로젝트 모든 모듈을 exe에 포함.
- 무인 자동 1차(연속형)·CLI 하위명령(`collect`/`consolidate`/`dashboard`) 추가(이후 v1.0.4 야간 배치로 대체).

## v1.0.1
- **원클릭 Windows 설치파일** — GitHub Actions(윈도우 러너)가 `KakaoAuto.exe`(PyInstaller) + `KakaoAuto-Setup.exe`(Inno Setup)를 자동 빌드해 릴리스에 첨부. 파이썬 설치 불필요.
- 2D 관계망 스크린샷 등 README 정비.

## v1.0.0
- 최초 공개. 카톡 PC 전체 방 자동 순회 수집(Ctrl+S 내보내기) → SQLite → 날짜·방별 TXT 정리.
- 대시보드(응답 대기·활동 히트맵·조용해진 방), 통합 검색, 엑셀, 금액·약속·계좌 추출, 사진 백업, 2D 관계망, 회전 백업(+선택 암호화), 규칙기반/로컬 LLM 브리핑. 100% 로컬·오프라인·읽기 전용.
