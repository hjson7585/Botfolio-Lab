import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1"
)

# ✅ 상태 저장 파일
MODEL_STATE_FILE = "logs/model_state.json"

# ✅ 기본 모델
DEFAULT_MODELS = [
    "deepseek/deepseek-chat",
    "qwen/qwen-2.5-72b-instruct",
    "mistralai/mixtral-8x7b-instruct",
]


# ✅ 모델 상태 불러오기
def load_model_state():

    if not os.path.exists(MODEL_STATE_FILE):

        return {m: {"success": 0, "fail": 0} for m in DEFAULT_MODELS}

    with open(MODEL_STATE_FILE, "r") as f:
        return json.load(f)


# ✅ 저장
def save_model_state(state):

    with open(MODEL_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ✅ 우선순위 정렬 (성공률 기준)
def sort_models(state):

    def score(m):
        s = state[m]["success"]
        f = state[m]["fail"]

        return s - f  # 간단한 scoring

    return sorted(state.keys(), key=score, reverse=True)


# ✅ 핵심 함수
def ask_llm(prompt: str):

    state = load_model_state()

    # ✅ 자동 우선순위
    models = sort_models(state)

    print("\n[현재 모델 우선순위]")
    print(models)

    for model in models:

        try:

            print(f"\n[LLM 시도] → {model}")

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0.2,
            )

            text = response.choices[0].message.content

            usage = response.usage

            # ✅ 성공 기록
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

            print(f"\n⚠️ 실패 → {model}")

            # ✅ 실패 기록
            state[model]["fail"] += 1
            save_model_state(state)

            continue

    # ✅ 전체 실패
    return {
        "text": """
        {
          "action":"HOLD",
          "reason":"All models failed"
        }
        """,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "model": "none",
    }
