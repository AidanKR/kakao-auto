"""
독립 건강 점검기 — 스케줄러가 주기적으로(예: 30분마다) 실행.

수집기가 '완전히 죽어서' 스스로 알림도 못 보내는 상황을 잡는 유일한 안전장치다.
health.json 의 갱신 시각이 오래됐으면(=수집기 멈춤) CRITICAL 알림을 보낸다.

사용: python healthcheck.py   (6_healthcheck.bat / 스케줄러가 호출)
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import alerts
import health

HERE = Path(__file__).parent


def load_config():
    p = HERE / "config.json"
    if not p.exists():
        return {}
    data = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return json.loads(data.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            try:
                return json.loads(data.decode(enc).replace("\\", "/"))
            except Exception:
                continue
    return {}


def main():
    cfg = load_config()
    stale_min = cfg.get("health_stale_minutes", 60)

    h = health.read_health()
    if h is None:
        alerts.notify(cfg, "CRITICAL", "health.json 이 없습니다 — 수집기가 한 번도 안 돌았거나 경로 문제")
        return

    updated = h.get("updated_at")
    try:
        dt = datetime.fromisoformat(updated)
        age_min = (datetime.now() - dt).total_seconds() / 60.0
    except Exception:
        alerts.notify(cfg, "CRITICAL", f"health.json 시각 파싱 실패: {updated}")
        return

    if age_min > stale_min:
        alerts.notify(
            cfg, "CRITICAL",
            f"{int(age_min)}분째 수집 갱신 없음(기준 {stale_min}분) — 수집기 멈춤/카톡 로그아웃 의심. "
            f"마지막 상태={h.get('status')}, 마지막시각={updated}",
        )
        return

    status = h.get("status")
    if status and status != "ok":
        alerts.notify(cfg, "WARN", f"수집기 상태 '{status}': {h.get('note','')}")
        return

    print(f"[healthcheck] 정상 (갱신 {int(age_min)}분 전, 상태 ok)")


if __name__ == "__main__":
    main()
