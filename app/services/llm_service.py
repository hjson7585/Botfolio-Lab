# app/services/llm_service.py
import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL_STATE_FILE = "logs/model_state.json"

DEFAULT_MODELS = [
    "deepseek/deepseek-chat",
    "qwen/qwen-2.5-72b-instruct",
    "mistralai/mixtral-8x7b-instruct",
]


# ── 상태 로드: 항상 {"success": int, "fail": int} 구조 보장 ──
def load_model_state() -> dict:
    base = {m: {"success": 0, "fail": 0} for m in DEFAULT_MODELS}
    try:
        if not os.path.exists(MODEL_STATE_FILE):
            return base
        with open(MODEL_STATE_FILE, "r") as f:
            saved = json.load(f)
        # 저장된 데이터를 base에 병합 — 키 누락 방지
        for m in DEFAULT_MODELS:
            if m in saved and isinstance(saved[m], dict):
                base[m]["success"] = int(saved[m].get("success", 0))
                base[m]["fail"] = int(saved[m].get("fail", 0))
        return base
    except Exception as e:
        print(f"[model_state 로드 실패 — 기본값 사용] {e}")
        return base


def save_model_state(state: dict):
    try:
        os.makedirs("logs", exist_ok=True)
        with open(MODEL_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[model_state 저장 실패 — 무시] {e}")


def sort_models(state: dict) -> list:
    def score(m):
        entry = state.get(m, {})
        s = int(entry.get("success", 0))
        f = int(entry.get("fail", 0))
        return s - f

    return sorted(DEFAULT_MODELS, key=score, reverse=True)


def ask_llm(prompt: str) -> dict:
    # API 키 사전 점검
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[LLM 오류] OPENROUTER_API_KEY 환경변수 없음 — fallback 반환")
        return {
            "text": '{"buys":[],"sells":[],"note":"No API key"}',
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model": "none",
        }

    state = load_model_state()
    models = sort_models(state)

    print("\n[현재 모델 우선순위]")
    print(models)

    for model in models:
        try:
            print(f"\n[LLM 시도] → {model}")

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.2,
            )

            text = response.choices[0].message.content
            usage = response.usage

            # ✅ setdefault로 키 누락 완전 방어
            state.setdefault(model, {"success": 0, "fail": 0})
            state[model]["success"] = int(state[model].get("success", 0)) + 1
            save_model_state(state)

            print(f"[LLM 성공] {model} | tokens={usage.total_tokens}")
            return {
                "text": text,
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "model": model,
            }

        except Exception as e:
            print(f"\n⚠️ 실패 → {model}: {e}")
            # ✅ setdefault로 키 누락 완전 방어
            state.setdefault(model, {"success": 0, "fail": 0})
            state[model]["fail"] = int(state[model].get("fail", 0)) + 1
            save_model_state(state)
            continue

    # 전체 모델 실패 시 fallback
    print("[LLM 전체 실패] fallback 반환")
    return {
        "text": '{"buys":[],"sells":[],"note":"All models failed"}',
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "model": "none",
    }
