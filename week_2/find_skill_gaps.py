import json
import re
import sqlite3
import sys
import time

from dotenv import load_dotenv
from pydantic import BaseModel

from prompt_model import prompt_model

load_dotenv()

MODEL = "gemini-2.5-flash-lite"
MAX_RETRIES = 3
RETRY_SLEEP = 1


class SkillGapResult(BaseModel):
    gaps: list[str]


def _extract_resume_skills(resume_text: str) -> set[str]:
    prompt = (
        "Extract technical skills (programming languages, frameworks, tools, platforms, databases) from this resume.\n"
        "Rules:\n"
        "- Preserve exact form as written (do NOT merge or split skills)\n"
        "- Exclude certifications, soft skills, spoken languages\n"
        "- Return ONLY a JSON array of strings. No other text.\n"
        'Example: ["Python", "Docker", "MySQL"]\n\n'
        f"Resume:\n{resume_text}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            text = prompt_model(MODEL, prompt)
            text = re.sub(r"```[^\n]*\n?", "", text).strip()
            if text.startswith("[Error]"):
                raise RuntimeError(text)
            skills = json.loads(text)
            return {s.strip().lower() for s in skills if isinstance(s, str) and s.strip()}
        except Exception as e:
            msg = str(e)
            if "API_KEY_INVALID" in msg or "API key not valid" in msg:
                print("API key not valid. Please pass a valid API key.")
                return set()
            if attempt < MAX_RETRIES:
                print(f"Attempt {attempt} failed: {e}\nRetrying in {RETRY_SLEEP}s...")
                time.sleep(RETRY_SLEEP)
            else:
                print(f"[Error] Resume skill extraction failed: {e}")
    return set()


def _load_job_skills(db_url: str) -> set[str]:
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != '' AND tech_stack != 'N/A'"
    )
    skills = set()
    for (tech_stack,) in cursor.fetchall():
        for skill in tech_stack.split(","):
            s = skill.strip().lower()
            if s and s != "n/a":
                skills.add(s)
    conn.close()
    return skills


def find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult:
    try:
        with open(input_file_path) as f:
            resume_text = f.read()
    except Exception as e:
        print(f"[Error] Cannot read resume: {e}")
        return SkillGapResult(gaps=[])

    resume_skills = _extract_resume_skills(resume_text)

    try:
        job_skills = _load_job_skills(db_url)
    except Exception as e:
        print(f"[Error] DB read failed: {e}")
        return SkillGapResult(gaps=[])

    gaps = sorted(job_skills - resume_skills)
    return SkillGapResult(gaps=gaps)


def main():
    resume_path = sys.argv[1] if len(sys.argv) > 1 else "data/resume_d3.txt"
    db_path = sys.argv[2] if len(sys.argv) > 2 else "data/jobs_d1.db"
    result = find_skill_gaps(resume_path, db_path)
    print(result)


if __name__ == "__main__":
    main()
