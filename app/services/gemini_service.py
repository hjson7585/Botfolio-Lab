import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def ask_gemini(prompt: str):

    try:

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "max_output_tokens": 50,
                "temperature": 0.2,
            },
        )

        # ✅ 토큰 usage 추출
        usage = getattr(response, "usage_metadata", None)

        input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        total_tokens = getattr(usage, "total_token_count", input_tokens + output_tokens)

        return {
            "text": response.text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    except Exception as e:

        print("\nGemini 오류")
        print(e)

        return {
            "text": """
            {
              "action":"HOLD",
              "reason":"Gemini error"
            }
            """,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
