"""
LLM 호출(선택) — OpenAI/Anthropic 둘 다 지원. 외부 SDK 없이 표준 urllib.

config.json:
  "ai_provider": "openai" | "anthropic" | ""   (빈값이면 AI 미사용 = 규칙기반만)
  "ai_api_key":  "sk-..."   (또는 환경변수 OPENAI_API_KEY / ANTHROPIC_API_KEY)
  "ai_model":    "gpt-4o-mini" (openai) / "claude-3-5-sonnet-latest" (anthropic) 등
"""
import json
import os
import urllib.request


def _key(cfg, env):
    return cfg.get("ai_api_key") or os.getenv(env) or ""


def _post(url, headers, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _openai(cfg, system, user, max_tokens):
    key = _key(cfg, "OPENAI_API_KEY")
    if not key:
        print("  [AI] OpenAI 키 없음(config ai_api_key 또는 OPENAI_API_KEY)")
        return None
    model = cfg.get("ai_model", "gpt-4o-mini")
    try:
        d = _post(
            "https://api.openai.com/v1/chat/completions",
            {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            {"model": model, "temperature": 0.2, "max_tokens": max_tokens,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}]},
        )
        return d["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [AI] OpenAI 호출 실패: {e}")
        return None


def _anthropic(cfg, system, user, max_tokens):
    key = _key(cfg, "ANTHROPIC_API_KEY")
    if not key:
        print("  [AI] Anthropic 키 없음(config ai_api_key 또는 ANTHROPIC_API_KEY)")
        return None
    model = cfg.get("ai_model", "claude-3-5-sonnet-latest")
    try:
        d = _post(
            "https://api.anthropic.com/v1/messages",
            {"Content-Type": "application/json", "x-api-key": key,
             "anthropic-version": "2023-06-01"},
            {"model": model, "max_tokens": max_tokens, "system": system,
             "messages": [{"role": "user", "content": user}]},
        )
        return "".join(b.get("text", "") for b in d.get("content", []))
    except Exception as e:
        print(f"  [AI] Anthropic 호출 실패: {e}")
        return None


def _ollama(cfg, system, user, max_tokens):
    """로컬 Ollama(외부전송 0, 무료). 먼저 'ollama serve' + 'ollama pull <model>' 필요."""
    model = cfg.get("ai_model", "llama3.1")
    host = cfg.get("ollama_host", "http://localhost:11434")
    try:
        d = _post(
            host.rstrip("/") + "/api/chat",
            {"Content-Type": "application/json"},
            {"model": model, "stream": False,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}],
             "options": {"num_predict": max_tokens}},
            timeout=180,
        )
        return (d.get("message") or {}).get("content")
    except Exception as e:
        print(f"  [AI] Ollama 호출 실패(‘ollama serve’ 실행 + ‘ollama pull {model}’ 확인): {e}")
        return None


def call(cfg, system, user, max_tokens=1500):
    """설정된 provider로 LLM 호출. 미설정/실패면 None(→ 규칙기반만 사용)."""
    provider = (cfg.get("ai_provider") or "").lower()
    if provider == "openai":
        return _openai(cfg, system, user, max_tokens)
    if provider == "anthropic":
        return _anthropic(cfg, system, user, max_tokens)
    if provider == "ollama":
        return _ollama(cfg, system, user, max_tokens)
    return None
