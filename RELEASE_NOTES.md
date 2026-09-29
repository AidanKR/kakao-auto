## 방별 CSV 이름이 대소문자만 다른 두 방을 뭉개던 버그 수정

설치 한 번, 그다음은 Enter 한 번(또는 매일 새벽 02:00 자동). **`KakaoAuto-Setup.exe`** 받아 실행하면 끝입니다.

### 이번에 고친 것 (v1.2.8)

두 PC의 `kakao.db`를 병합하던 중 실제로 겪은 버그입니다. **대소문자만 다른 두 방**(예: `KMALL09 Logistics`와 `KMALL09 LOGISTICS`)이 있으면, 방별 CSV를 내보낼 때 **Windows가 폴더명 대소문자를 구분하지 않아** 나중에 처리되는 방이 먼저 것의 CSV를 덮어썼습니다. 대화 자체(`kakao.db`)는 멀쩡했고 **CSV 내보내기 단계에서만** 한쪽 방 전체가 사라지는 문제였습니다.

- 방 이름 중복 판정을 대소문자 무시로 바꿔서, 이런 방은 이제 `_2` 접미사가 붙어 각자 CSV를 가집니다.
- 실제 충돌 사례 두 건으로 검증 완료.

### 라이선스
**Apache License 2.0** ([LICENSE](LICENSE) · [NOTICE](NOTICE)).

> 카카오톡 클라이언트 자동화는 이용약관 위반이며 계정 제재 위험이 있습니다. 본인 계정·본인 참여 대화·적법한 목적에만.

전체 변경 이력: [CHANGELOG.md](https://github.com/AidanKR/kakao-auto/blob/main/CHANGELOG.md)
