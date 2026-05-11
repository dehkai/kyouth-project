import email
import quopri
from pathlib import Path


def ingest_all_mhtml(input_dir: Path, output_dir: Path) -> None:
    print("🥉 Bronze:...")

    if not input_dir.exists():
        print(f"⚠️  Source directory not found: {input_dir}")
        print("📊 Bronze Summary:\nTotal: 0 | Extracted: 0 | Failed: 0")
        return

    mhtml_files = list(input_dir.glob("*.mhtml"))
    if not mhtml_files:
        print(f"⚠️  No .mhtml files in: {input_dir}")
        print("📊 Bronze Summary:\nTotal: 0 | Extracted: 0 | Failed: 0")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(mhtml_files)
    extracted = 0
    failed = 0

    for mhtml_path in mhtml_files:
        stem = mhtml_path.stem
        raw = mhtml_path.read_bytes()
        msg = email.message_from_bytes(raw)

        html_payload = None
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=False)
                if isinstance(payload, bytes):
                    html_payload = payload
                elif isinstance(payload, str):
                    encoding = part.get("Content-Transfer-Encoding", "").lower()
                    if encoding == "quoted-printable":
                        html_payload = quopri.decodestring(payload.encode())
                    else:
                        html_payload = payload.encode()
                break

        if html_payload is None:
            print(f"⚠️  No HTML content found in: {mhtml_path.name}")
            failed += 1
            continue

        out_path = output_dir / f"{stem}.html"
        out_path.write_bytes(html_payload)
        print(f"✅ Extracted: {mhtml_path.name}")
        extracted += 1

    print(f"📊 Bronze Summary:\nTotal: {total} | Extracted: {extracted} | Failed: {failed}")
