import json
from pathlib import Path

from bs4 import BeautifulSoup
from pydantic import BaseModel


class JobListing(BaseModel):
    source_id: str
    job_title: str
    company: str
    description: str


def _extract(soup: BeautifulSoup) -> dict:
    og_url = soup.find("meta", property="og:url")
    source_id = og_url["content"].rstrip("/").split("/")[-1] if og_url else None

    title_tag = soup.find(attrs={"data-automation": "job-detail-title"})
    job_title = title_tag.get_text(separator=" ", strip=True) if title_tag else None

    company_tag = soup.find(attrs={"data-automation": "advertiser-name"})
    company = company_tag.get_text(separator=" ", strip=True) if company_tag else None

    desc_tag = soup.find(attrs={"data-automation": "jobAdDetails"})
    description = desc_tag.get_text(separator=" ", strip=True) if desc_tag else None

    return {
        "source_id": source_id,
        "job_title": job_title,
        "company": company,
        "description": description,
    }


def process_all_html(input_dir: Path, output_dir: Path) -> None:
    print("🥈 Silver:...")

    if not input_dir.exists():
        print(f"⚠️  Input directory not found: {input_dir}")
        print("📊 Silver Summary:\nTotal: 0 | Processed: 0 | Skipped: 0")
        return

    html_files = list(input_dir.glob("*.html"))
    if not html_files:
        print(f"⚠️  No .html files in: {input_dir}")
        print("📊 Silver Summary:\nTotal: 0 | Processed: 0 | Skipped: 0")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(html_files)
    processed = 0
    skipped = 0

    for html_path in html_files:
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        raw = _extract(soup)

        missing = [k for k, v in raw.items() if not v]
        if missing:
            for field in missing:
                print(f"⚠️  Missing {field} in: {html_path.name}")
            skipped += 1
            continue

        listing = JobListing(**raw)
        out_path = output_dir / f"{html_path.stem}.json"
        out_path.write_text(
            json.dumps(listing.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"✅ Processed: {html_path.name}")
        processed += 1

    print(f"📊 Silver Summary:\nTotal: {total} | Processed: {processed} | Skipped: {skipped}")
