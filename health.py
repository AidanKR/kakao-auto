"""
건강상태(health) 기록 — 수집기가 매 바퀴 상태를 health.json 에 남긴다.
독립 점검기(healthcheck.py)와 다른 PC가 이 파일로 '살아있는지'를 판단한다.
"""
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
HEALTH_FILE = HERE / "health.json"


def write_health(cfg, stats):
    """stats(dict)에 시각을 붙여 health.json + 공유폴더에 기록."""
    data = dict(stats)
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    text = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        HEALTH_FILE.write_text(text, encoding="utf-8")
    except Exception:
        pass
    sd = cfg.get("share_dir")
    if sd:
        try:
            p = Path(sd)
            p.mkdir(parents=True, exist_ok=True)
            (p / "health.json").write_text(text, encoding="utf-8")
        except Exception:
            pass


def read_health():
    try:
        return json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
