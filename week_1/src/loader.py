import json
import sqlite3
from pathlib import Path

from src.utils import load_sql


def load_all_jsons(input_dir: Path, output_dir: Path) -> None:
    print("🥇 Gold:...")

    if not input_dir.exists():
        print(f"⚠️  Input directory not found: {input_dir}")
        print("📊 Gold Summary:\nTotal: 0 | Inserted: 0 | Skipped: 0")
        return

    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        print(f"⚠️  No .json files in: {input_dir}")
        print("📊 Gold Summary:\nTotal: 0 | Inserted: 0 | Skipped: 0")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "jobs.db"

    conn = sqlite3.connect(db_path)
    conn.execute(load_sql("create_jobs_table.sql"))
    conn.commit()

    total = len(json_files)
    inserted = 0
    skipped = 0

    for json_path in json_files:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        cursor = conn.execute(
            load_sql("insert_job.sql"),
            (data["source_id"], data["job_title"], data["company"], data["description"]),
        )
        if cursor.rowcount == 1:
            print(f"✅ Inserted: {json_path.name}")
            inserted += 1
        else:
            print(f"⏭️  Skipped (duplicate): {json_path.name}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"📊 Gold Summary:\nTotal: {total} | Inserted: {inserted} | Skipped: {skipped}")
