import os
import sys

from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODELS = {"llama3.1", "phi3", "deepseek-r1:1.5b"}
GEMINI_MODELS = {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"}


def prompt_model(model: str, prompt: str) -> str:
    try:
        if model in GEMINI_MODELS:
            return _prompt_gemini(model, prompt)
        elif model in OLLAMA_MODELS:
            return _prompt_ollama(model, prompt)
        else:
            return f"[Error] Unknown model '{model}'. Supported: {OLLAMA_MODELS | GEMINI_MODELS}"
    except Exception as e:
        return f"[Error] Unexpected failure: {e}"


def _prompt_gemini(model: str, prompt: str) -> str:
    try:
        from google import genai

        api_key = os.environ.get("GEMINI_API") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return "[Gemini Error] GEMINI_API environment variable not set."

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except Exception as e:
        return f"[Gemini Error] {e}"


def _prompt_ollama(model: str, prompt: str) -> str:
    try:
        import ollama

        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.message.content
    except Exception as e:
        return f"[Ollama Error] {e}"


def main():
    if len(sys.argv) >= 3:
        model = sys.argv[1]
        prompt = sys.argv[2]
    else:
        model = "llama3.1"
        prompt = "Say hello in one sentence."

    response = prompt_model(model, prompt)
    print("--- RESPONSE ---")
    print(response)


if __name__ == "__main__":
    main()
