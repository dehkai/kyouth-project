# Week 1 — Job Listings ETL Pipeline

A local data pipeline that extracts job listings from raw `.mhtml` web archives, cleans and structures them, loads into a SQLite database, and profiles the result. Implements a 4-layer Medallion Architecture: Source → Bronze → Silver → Gold.

---

## Setup Instructions

### Prerequisites

- macOS / Linux / Windows
- [uv](https://docs.astral.sh/uv/) — Python package and environment manager
- Python 3.14+

### 1. Install uv

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and enter the project

```bash
git clone https://github.com/dehkai/kyouth-project.git
cd week_1
```

### 3. Install Python and dependencies

**macOS / Linux:**
```bash
uv python install
uv venv
source .venv/bin/activate
uv sync
```

**Windows (PowerShell):**
```powershell
uv python install
uv venv
.venv\Scripts\Activate.ps1
uv sync
```

**Windows (CMD):**
```cmd
uv python install
uv venv
.venv\Scripts\activate.bat
uv sync
```

### 4. Add source data

Place your `.mhtml` job listing files into:

```
data/0_source/
```

---

## Usage

All commands are run from the `week_1/` directory with the virtual environment active.

### Run individual pipeline stages

```bash
python main.py ingest     # Extract .mhtml → data/1_bronze/*.html
python main.py process    # Clean HTML    → data/2_silver/*.json
python main.py load       # Load JSON     → data/3_gold/jobs.db
python main.py profile    # Quality report on jobs.db
```

### Run full pipeline end-to-end

```bash
python main.py all
```

### Expected output

```
🥉 Bronze:...
✅ Extracted: SomeJob.mhtml
📊 Bronze Summary:
Total: 100 | Extracted: 100 | Failed: 0

🥈 Silver:...
✅ Processed: SomeJob.html
📊 Silver Summary:
Total: 100 | Processed: 84 | Skipped: 16

🥇 Gold:...
✅ Inserted: SomeJob.json
📊 Gold Summary:
Total: 84 | Inserted: 84 | Skipped: 0

--- 🔍 DATA QUALITY REPORT ---
📈 Total Records: 84
❓ Missing Values -> job_title: 0, company: 0, description: 0
📝 Avg Description Length: 2654 chars
⚠️  Shortest Description: 32 chars
   ↳ source_id: 91647393 | job_title: Software Engineer
🚨 Longest Description: 6781 chars
   ↳ source_id: 91731564 | job_title: Automation Engineer
```

---

## Project Structure

```
week_1/
├── data/
│   ├── 0_source/       # Raw .mhtml web archives (input)
│   ├── 1_bronze/       # Decoded HTML files
│   ├── 2_silver/       # Cleaned, structured JSON files
│   └── 3_gold/         # SQLite database (jobs.db)
├── src/
│   ├── ingestor.py     # Bronze layer: MHTML → HTML
│   ├── processor.py    # Silver layer: HTML → JSON
│   ├── loader.py       # Gold layer:   JSON → SQLite
│   └── profiler.py     # Quality checks on Gold layer
├── main.py             # CLI orchestrator
├── pyproject.toml      # Project config and dependencies
└── .python-version     # Pinned Python version
```

---

## Technical Reflections

### Module 1: The Extractor (Medallion & Lakehouses)
Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?

- **Answer**: Raw files act as a safety net. If parsing logic breaks or a bug is found downstream, the code can be fixed and data reprocessed without re-scraping. Without the raw files, any mistake means data is gone permanently.

### Module 2: Treatment Plant (ETL vs ELT & Scale)
Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?

- **Answer**: Cloud warehouses have massive built-in compute, so transforming inside the warehouse is cheaper and faster than pre-cleaning outside. Sequential processing is slow and fragile because one bad file blocks everything. Distributed tools like Spark split data across many machines and process in parallel, so speed scales with the number of workers rather than the number of files.

### Module 3: The Blueprint & The Vault (Storage & Contracts)
What should happen if an important field like `job_title` disappears? Why fail early instead of silently inserting nulls into DB? How does `INSERT OR IGNORE` help prevent duplicate records?

- **Answer**: A missing job title that silently becomes empty breaks every report or model that depends on it, often going unnoticed until much later. Stopping early with a clear warning makes the problem much faster to find and fix. INSERT OR IGNORE prevents duplicate records by skipping any row whose source ID already exists in the database, making the pipeline safe to run multiple times.

### Module 4: The QA Inspector & Orchestrator (Orchestration & DAGs)
What happens if `processor.py` crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?

- **Answer**: A crash leaves the pipeline in a partial state with no record of what completed. Running everything again from scratch wastes time on stages that already worked. Airflow tracks each stage as a separate task and on failure retries only the broken step, not the whole pipeline, while alerting the team automatically.
