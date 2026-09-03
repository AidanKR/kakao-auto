## KakaoTalk business chat — now fully hands-off on Windows

**Install once, and every night it runs itself.** Download `KakaoAuto-Setup.exe` below → run → done. No Python, no build.

### What you get
- **원클릭 설치** — `KakaoAuto-Setup.exe` 하나. 파이썬·빌드 필요 없음.
- **매일 새벽 02:00 무인 배치** (메뉴 `11`) — 카톡 자동 실행 → 전체 수집 → 정리 → **방별 CSV** → 실제 사진 백업 → **카톡 자동 종료**. 사람 개입 0.
- **방별 CSV** — `share_dir/csv/<방>/<방>.csv` (방마다 폴더 + CSV 하나). `utf-8-sig`, 엑셀·pandas 그대로 → 메인 서버로 옮겨 분석.
- **실제 사진만** — 이모티콘·스티커·썸네일은 빼고 진짜 이미지만 백업.
- **읽기 전용** — 메시지 전송 없음. 100% 로컬·오프라인.

### One-liner (EN)
An unattended KakaoTalk-desktop archiver for Windows: a scheduled 02:00 batch opens KakaoTalk, exports every room, writes one CSV per room (+ real photos, emoticons excluded), and closes KakaoTalk — all offline, read-only.

### 설치
1. 아래 **`KakaoAuto-Setup.exe`** 다운로드 → 실행 ("Windows가 PC를 보호했습니다" → 추가 정보 → 실행).
2. 시작 메뉴 → **KakaoAuto** → `config.json`의 `share_dir` 지정 → 메뉴 `11` 한 번(무인 자동 등록).
3. 전제: 그 시각 PC 켜짐·로그인, 카톡 자동 로그인.

> ⚠️ 카톡 클라이언트 자동화는 카카오 이용약관 위반이며 계정 제재 위험이 있습니다. 본인 소유 업무 계정·본인이 참여한 대화·적법한 목적에만. 수집물의 개인정보 처리 책임은 사용자에게 있습니다.

전체 변경 이력: [CHANGELOG.md](https://github.com/AidanKR/kakao-auto/blob/main/CHANGELOG.md)
