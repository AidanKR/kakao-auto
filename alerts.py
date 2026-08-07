"""
알림 모듈 — 문제 발생 시 여러 경로로 알린다(무인 운영 안전장치).

경로(설정에 따라 선택):
  1) 공유폴더(구글드라이브)의 ALERT.txt 에 기록  → 님이 드라이브에서 바로 확인
  2) 웹훅(Discord/Slack/Telegram 등) POST       → 실시간 푸시
  3) 로컬 폴더 ALERT.txt + 콘솔

외부 의존성 없음(표준 urllib). 실패해도 수집엔 지장 없음.
"""
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = __import__("appdir").APP_DIR


def _share_dir(cfg):
    sd = cfg.get("share_dir")
    if not sd:
        return None
    p = Path(sd)
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        return None


def _append(path, line):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _webhook(url, line):
    try:
        data = json.dumps({"content": line, "text": line}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  (웹훅 알림 실패, 무시: {e})")


def notify(cfg, level, message):
    """level: INFO | WARN | CRITICAL. 문제를 여러 경로로 알린다."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}"
    print(f"  *** 알림: {line}")

    # 1) 로컬 ALERT.txt
    _append(HERE / "ALERT.txt", line)
    # 2) 공유폴더 ALERT.txt(구글드라이브)
    sd = _share_dir(cfg)
    if sd:
        _append(sd / "ALERT.txt", line)
    # 3) 웹훅
    url = cfg.get("alert_webhook_url")
    if url:
        _webhook(url, f"[카톡수집기] {line}")


if __name__ == "__main__":
    # 테스트: python alerts.py "메시지"
    import json as _j
    cfg = {}
    p = HERE / "config.json"
    if p.exists():
        try:
            cfg = _j.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    msg = sys.argv[1] if len(sys.argv) > 1 else "테스트 알림"
    notify(cfg, "INFO", msg)
