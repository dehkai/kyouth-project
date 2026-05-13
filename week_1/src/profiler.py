import sqlite3
from pathlib import Path

from src.utils import load_sql


def run_data_profile(db_path: Path) -> None:
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)

    (total,) = conn.execute(load_sql("count_jobs.sql")).fetchone()

    (null_title, null_company, null_desc) = conn.execute(
        load_sql("null_counts.sql")
    ).fetchone()

    (avg_len,) = conn.execute(load_sql("avg_description_length.sql")).fetchone()

    short_len, short_id, short_title = conn.execute(
        load_sql("shortest_description.sql")
    ).fetchone()

    long_len, long_id, long_title = conn.execute(
        load_sql("longest_description.sql")
    ).fetchone()

    conn.close()

    print("--- 🔍 DATA QUALITY REPORT ---")
    print(f"📈 Total Records: {total}")
    print(f"❓ Missing Values -> job_title: {null_title}, company: {null_company}, description: {null_desc}")
    print(f"📝 Avg Description Length: {int(avg_len)} chars")
    print(f"⚠️  Shortest Description: {short_len} chars")
    print(f"   ↳ source_id: {short_id} | job_title: {short_title}")
    print(f"🚨 Longest Description: {long_len} chars")
    print(f"   ↳ source_id: {long_id} | job_title: {long_title}")
