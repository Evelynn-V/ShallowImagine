"""Download the 弱智吧 seed corpus.

Source: https://github.com/Leymore/ruozhiba (public collection of Tieba posts).
We only read the JSON data; nothing from the archive is executed.

The full dataset is *not* committed to this repository. Run this script to
materialize ``data/seeds/ruozhiba_titles.jsonl`` locally, then feed it to
``model/generate_data.py`` together with ``data/seeds/seed_prompts.jsonl``.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tarfile
import urllib.request
from pathlib import Path

URL = "https://codeload.github.com/Leymore/ruozhiba/tar.gz/refs/heads/main"
ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw"
SEED_DIR = ROOT / "seeds"


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        destination.write_bytes(response.read())
    print(f"wrote {destination} ({destination.stat().st_size / 1024 / 1024:.1f} MB)")


def safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"unsafe archive member: {member.name}")
        tar.extractall(destination)


def load_posts(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="fetch 弱智吧 seed titles")
    parser.add_argument("--limit", type=int, default=2000, help="max titles to keep")
    parser.add_argument("--no-download", action="store_true", help="reuse data/raw/ruozhiba.tar.gz")
    args = parser.parse_args()

    archive = RAW_DIR / "ruozhiba.tar.gz"
    if not args.no_download or not archive.exists():
        download(URL, archive)

    extract_dir = RAW_DIR / "ruozhiba"
    if extract_dir.exists():
        # Keep the extraction deterministic and safe.
        for child in sorted(extract_dir.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
    safe_extract(archive, extract_dir)

    data_dir = extract_dir / "ruozhiba-main" / "data"
    files = [
        data_dir / "ruozhiba-title-good.json",
        data_dir / "ruozhiba-title-norm.json",
    ]

    SEED_DIR.mkdir(parents=True, exist_ok=True)
    output = SEED_DIR / "ruozhiba_titles.jsonl"
    kept = 0
    seen: set[str] = set()

    with output.open("w", encoding="utf-8") as handle:
        for path in files:
            if not path.exists():
                continue
            for item in load_posts(path):
                title = (item.get("title") or "").strip()
                if not title or not (4 <= len(title) <= 60):
                    continue
                if title in seen:
                    continue
                seen.add(title)
                record = {"text": title, "source": "ruozhiba", "kind": "title"}
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                kept += 1
                if kept >= args.limit:
                    break
            if kept >= args.limit:
                break

    print(f"wrote {kept} titles to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
