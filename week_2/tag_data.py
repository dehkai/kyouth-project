import os
import re
import sqlite3
import sys
import time

import ollama as ollama_client
from dotenv import load_dotenv
from google import genai

load_dotenv()

BATCH_SIZE = 3
MAX_RETRIES = 3
RETRY_SLEEP = 2
DESC_LIMIT = 800
MODEL = "llama3.1"

OLLAMA_MODELS = {"llama3.1", "phi3", "deepseek-r1:1.5b"}
GEMINI_MODELS = {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"}


def _build_prompt(batch: list[tuple]) -> str:
    lines = [
        "You are a technical keyword extractor. Output ONLY short comma-separated technology names. No sentences. No markdown.",
        "",
        "List the technologies (languages, frameworks, tools, platforms) from each job description.",
        "One line per job: Job N: keyword1, keyword2, keyword3",
        "If nothing found: Job N: N/A",
        "",
        "CORRECT: Job 1: Python, React, PostgreSQL, Docker",
        "WRONG:   Job 1: The role requires Python expertise alongside React...",
        "",
    ]
    for i, (source_id, description) in enumerate(batch, start=1):
        lines.append(f"Job {i} (ID: {source_id}):")
        lines.append(description[:DESC_LIMIT])
        lines.append("")
    return "\n".join(lines)


def _clean_tags(raw: str) -> str:
    parts = [p.strip().rstrip(".") for p in raw.split(",")]
    keywords = [p for p in parts if p and len(p.split()) <= 5]
    return ", ".join(keywords) if keywords else "N/A"


def _parse_response(text: str, expected: int) -> list[str] | None:
    matches = re.findall(r"^Job\s+(\d+)[ \t]*:[ \t]*(.*)", text, re.MULTILINE | re.IGNORECASE)
    if len(matches) != expected:
        return None
    results = ["N/A"] * expected
    for idx_str, tags in matches:
        idx = int(idx_str) - 1
        if 0 <= idx < expected:
            results[idx] = _clean_tags(tags)
    return results


def _call_model(model: str, prompt: str, gemini_client: genai.Client | None) -> tuple[str, int]:
    if model in GEMINI_MODELS:
        response = gemini_client.models.generate_content(model=model, contents=prompt)
        tokens = response.usage_metadata.total_token_count or 0
        return response.text, tokens
    response = ollama_client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    tokens = (response.prompt_eval_count or 0) + (response.eval_count or 0)
    return response.message.content, tokens


def tag_data(db_url: str):
    start = time.time()
    total_tokens = 0
    gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API")) if MODEL in GEMINI_MODELS else None

    try:
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''"
        )
        rows = cursor.fetchall()
    except Exception as e:
        print(f"[Error] DB read failed: {e}")
        return

    if not rows:
        print("No data to tag")
        conn.close()
        elapsed = (time.time() - start) * 1000
        print(f"Total tokens used: 0, took {elapsed:.3f}ms")
        return

    for batch_idx, i in enumerate(range(0, len(rows), BATCH_SIZE)):
        batch = rows[i : i + BATCH_SIZE]
        prompt = _build_prompt(batch)
        tags = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw, tokens = _call_model(MODEL, prompt, gemini_client)
                total_tokens += tokens
                tags = _parse_response(raw, len(batch))
                if tags is not None:
                    break
                print(f"[Batch {batch_idx}] Attempt {attempt} failed: Mismatch between batch size and response")
            except Exception as e:
                msg = str(e)
                if "API_KEY_INVALID" in msg or "API key not valid" in msg:
                    print("[Error] No API key found, please set GEMINI_API in .env.")
                    conn.close()
                    return
                print(f"[Batch {batch_idx}] Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP)

        if tags is None:
            print(f"[Batch {batch_idx}] Skipping after {MAX_RETRIES} failed attempts")
            continue

        for (source_id, _), tech_stack in zip(batch, tags):
            try:
                cursor.execute("UPDATE jobs SET tech_stack = ? WHERE source_id = ?", (tech_stack, source_id))
                print(f"Analyzed Job {source_id}: {tech_stack}")
            except Exception as e:
                print(f"[Error] Failed to update job {source_id}: {e}")
        conn.commit()

    conn.close()
    elapsed = (time.time() - start) * 1000
    print(f"Total tokens used: {total_tokens}, took {elapsed:.3f}ms")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/jobs_d1.db"
    tag_data(db_path)


if __name__ == "__main__":
    main()
