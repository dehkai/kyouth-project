# Week 2 — Job Skill Gap Analyzer

## Project Overview

This project helps you figure out what technical skills you are missing for jobs in the market.

It works in two steps:
1. **Tag jobs** — reads job descriptions from a database and uses an LLM to extract the tech stack (languages, frameworks, tools) from each one.
2. **Find skill gaps** — compares those job skills against your resume and tells you what skills you don't have yet.

---

## Setup Instructions

### Prerequisites

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/) (package manager)
- [Ollama](https://ollama.com/) installed and running locally (for local model support)
- A Gemini API key (for cloud model support)

### Install dependencies

```bash
uv sync
```

### Configure environment variables

Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API=your_actual_gemini_api_key
```

---

## Usage

### Step 1 — Tag job descriptions

Reads untagged jobs from the database and writes `tech_stack` for each:

```bash
uv run tag_data.py
```

Optional: pass a custom database path:

```bash
uv run tag_data.py data/jobs_d1.db
```

Expected output:

```
Analyzed Job 91247023: Python, FastAPI, PostgreSQL
Analyzed Job 91347112: Java, Spring Boot, Docker
...
Total tokens used: 4821, took 12340.123ms
```

### Step 2 — Find your skill gaps

Compares resume skills against all tagged job skills:

```bash
uv run find_skill_gaps.py
```

Optional: pass custom resume and database paths:

```bash
uv run find_skill_gaps.py data/resume_d3.txt data/jobs_d1.db
```

Expected output:

```
gaps=['docker', 'kubernetes', 'spring boot', 'terraform']
```

### Test the model layer directly

```bash
uv run prompt_model.py llama3.1 "What is Python?"
uv run prompt_model.py gemini-2.5-flash-lite "List 3 frameworks"
```

---

## API / Function Reference

### `prompt_model.py`

**`prompt_model(model, prompt) → str`**
- Calls the given model with a prompt and returns the text response.
- `model`: one of the supported model names (see below)
- `prompt`: plain text string

**`call_model(model, prompt) → tuple[str, int]`**
- Returns `(response_text, token_count)`.
- Token count is 0 on error or for unsupported models.

Supported models:
- Gemini (cloud): `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3-flash-preview`
- Ollama (local): `llama3.1`, `phi3`, `deepseek-r1:1.5b`

---

### `tag_data.py`

**`tag_data(db_url) → None`**
- Reads all jobs with no `tech_stack` from the SQLite database.
- Sends them to the LLM in batches of 3.
- Parses the response and writes `tech_stack` back to the database.
- Retries up to 3 times per batch if the response format is wrong.
- `db_url`: path to the SQLite `.db` file

**`_build_prompt(batch) → str`**
- Builds the prompt for a batch of `(source_id, description)` tuples.

**`_parse_response(text, expected) → list[str] | None`**
- Parses `"Job N: skill1, skill2"` lines from the LLM response.
- Returns `None` if the count does not match `expected` (triggers retry).

---

### `find_skill_gaps.py`

**`find_skill_gaps(input_file_path, db_url) → SkillGapResult`**
- Reads resume text, extracts skills via LLM, loads job skills from DB, returns the difference.
- `input_file_path`: path to a plain text resume file
- `db_url`: path to the SQLite `.db` file
- Returns a `SkillGapResult(gaps=[...])` Pydantic model

**`_extract_resume_skills(resume_text) → set[str]`**
- Sends resume to Gemini, returns a set of lowercase skill strings.

**`_load_job_skills(db_url) → set[str]`**
- Reads all `tech_stack` entries from the database, splits by comma, returns a lowercase set.

---

## Data / Assumptions

### Database schema

```sql
CREATE TABLE jobs (
    source_id   TEXT PRIMARY KEY,
    job_title   TEXT NOT NULL,
    company     TEXT NOT NULL,
    description TEXT NOT NULL,
    tech_stack  TEXT          -- populated by tag_data.py
);
```

### Resume input

- Plain `.txt` file
- No special format required — the LLM reads it as-is

### Assumptions

- Job descriptions are truncated to 800 characters before sending to the model (to stay within token limits).
- Skill comparison is case-insensitive (all lowercased before comparing).
- A `tech_stack` of `"N/A"` is treated as untagged.
- Jobs with an existing `tech_stack` value are skipped during tagging — re-tagging requires clearing those values manually.
- The LLM response must follow `"Job N: skill1, skill2"` format exactly; mismatches trigger a retry.

### Data flow

```
jobs table (no tech_stack)
        ↓
  tag_data.py (LLM batch tagging)
        ↓
jobs table (tech_stack filled)
        ↓
  find_skill_gaps.py (LLM resume parsing + set difference)
        ↓
  SkillGapResult(gaps=[...])
```

---

## Testing

Testing was done manually by running both scripts end-to-end.

### Scenarios tested

| Scenario | How tested |
|---|---|
| Normal batch tagging | Ran `tag_data.py` on a real DB with 50+ jobs |
| Retry on bad LLM response | Observed retry logs when model returned wrong format |
| Empty DB (nothing to tag) | Cleared all jobs — confirmed "No data to tag" message |
| Missing `source_id` value in DB | Deleted a cell value — confirmed it was still processed |
| Invalid API key | Set wrong key — confirmed error message and early exit |
| Skill gap detection | Used a resume with known skills; verified gap output matched expectations |
| Unknown model name | Passed invalid model — confirmed `[Error] Unknown model` message |

### Reproducing

```bash
# Tag jobs
uv run tag_data.py data/jobs_d1.db

# Find gaps
uv run find_skill_gaps.py data/resume_d3.txt data/jobs_d1.db
```

### Determinism

- LLM output format is strictly validated (`"Job N: ..."`) — anything that does not parse is retried or skipped, so bad outputs never write garbage to the database.

---

## Limitations

- **Skill matching is exact** — `"React"` and `"React.js"` are treated as different skills and may both show up as gaps even if you know one.
- **Resume parsing depends on LLM quality** — unusual resume formats may cause skills to be missed or misread.
- **Batch failures are skipped** — if a batch fails all 3 retries, those jobs are left untagged with no further action.

---

## Architecture Reflection

### Design choices

I split the project into three files, each doing one thing. `prompt_model.py` only talks to the LLM. `tag_data.py` only reads job descriptions and saves the tech stack. `find_skill_gaps.py` only does the resume comparison. That way each file is easy to understand on its own and you can change one without breaking the others.

`prompt_model.py` exists to handle how each model gets called. The caller still picks which model to use, but all the details of actually running it — Gemini SDK, Ollama API, token counting all live in one place instead of being scattered across every script.

### Trade-offs

The big trade-off was **coverage vs. clean data**. I went with strict parsing — if the LLM reply doesn't match the expected format, the whole batch gets rejected and retried. This means some jobs get skipped, but everything that does get saved is correct. Bad skill data is harder to catch later, so I chose to have less data rather than messy data.

I also sent 3 jobs per prompt instead of one at a time. One job per prompt is easier to parse but costs more. Too many jobs per prompt makes the format hard to enforce. Three was a good middle ground.

### What I would improve

Right now if one job in a batch breaks the format, all three jobs get retried together. It would be better to retry just the one bad job on its own, so the other two don't get blocked.

