import sqlite3
from pathlib import Path


def run_data_profile(db_path: Path) -> None:
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)

    (total,) = conn.execute("SELECT COUNT(*) FROM jobs;").fetchone()

    (null_title, null_company, null_desc) = conn.execute(
        """
        SELECT
            SUM(CASE WHEN job_title   IS NULL OR job_title   = '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN company     IS NULL OR company     = '' THEN 1 ELSE 0 END),
            SUM(CASE WHEN description IS NULL OR description = '' THEN 1 ELSE 0 END)
        FROM jobs;
        """
    ).fetchone()

    (avg_len,) = conn.execute(
        "SELECT ROUND(AVG(LENGTH(description))) FROM jobs;"
    ).fetchone()

    short_len, short_id, short_title = conn.execute(
        """
        SELECT LENGTH(description), source_id, job_title
        FROM jobs
        ORDER BY LENGTH(description) ASC
        LIMIT 1;
        """
    ).fetchone()

    long_len, long_id, long_title = conn.execute(
        """
        SELECT LENGTH(description), source_id, job_title
        FROM jobs
        ORDER BY LENGTH(description) DESC
        LIMIT 1;
        """
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
