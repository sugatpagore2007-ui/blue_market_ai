from __future__ import annotations
import json, requests

OLLAMA_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'llama3.2:3b'


def llm_available() -> bool:
    try:
        r = requests.post(OLLAMA_URL, json={'model': OLLAMA_MODEL, 'prompt': 'hi', 'stream': False}, timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def explain_with_llm(signal: dict) -> str:
    prompt = (
        'You are a careful trading analyst. Explain this setup in simple language. '
        'Do not promise profit. Keep it educational and risk-aware. Signal JSON: ' + json.dumps(signal, default=str)[:6000]
    )
    try:
        r = requests.post(OLLAMA_URL, json={'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False}, timeout=20)
        if r.status_code == 200:
            return r.json().get('response','').strip() or signal.get('analyst_reason','')
    except Exception:
        pass
    return signal.get('analyst_reason', 'LLM brain unavailable. Using rule-based analyst reason.')


def llm_help() -> str:
    return 'Optional LLM analyst brain uses local Ollama llama3.2:3b. Install Ollama and run: ollama pull llama3.2:3b. If unavailable, Blue uses rule-based explanation.'
