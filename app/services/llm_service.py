# app/services/llm_service.py
import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"
)

# 모델 상태 저장 파일 (Railway 에페머럴 디스크 대응: 실패해도 무시)
MODEL_STATE_FILE = "logs/model_state.json"

DEFAULT_MODELS = [
    "deepseek/deepseek-chat",
    "qwen/qwen-2.5-72b-instruct",
    "mistralai/mixtral-8x7b-instruct",
]


def load_model_state():
    try:
        if not os.path.exists(MODEL_STATE_FILE):
            return {m: {"success": 0, "fail": 0} for m in DEFAULT_MODELS}
        with open(MODEL_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # 파일 읽기 실패 시 기본값 반환 (예외 전파 X)
        return {m: {"success": 0, "fail": 0} for m in DEFAULT_MODELS}


def save_model_state(state):
    try:
        os.makedirs("logs", exist_ok=True)
        with open(MODEL_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        # ✅ 파일 저장 실패해도 예외 전파 X — ask_llm 흐름 방해하지 않음
        print(f"[model_state 저장 실패 — 무시] {e}")


def sort_models(state):
    def score(m):
        s = state.get(m, {}).get("success", 0)
        f = state.get(m, {}).get("fail", 0)
        return s - f

    return sorted(state.keys(), key=score, reverse=True)


def ask_llm(prompt: str):
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
                max_tokens=200,  # ✅ 50 → 200 (JSON 완성 보장)
                temperature=0.2,
            )

            text = response.choices[0].message.content
            usage = response.usage

            state[model]["success"] += 1
            save_model_state(state)

            return {
                "text": text,
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "model": model,
            }

        except Exception as e:
            print(f"\n⚠️ 실패 → {model}: {e}")
            state[model]["fail"] += 1
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
