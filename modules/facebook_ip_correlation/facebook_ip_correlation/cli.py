from __future__ import annotations

import argparse
import json
from pathlib import Path

from facebook_ip_correlation.extractor import process_export


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and correlate Facebook IP/location records.")
    parser.add_argument("--source", required=True, type=Path, help="Extracted Facebook export folder or .zip file.")
    parser.add_argument("--output", required=True, type=Path, help="Output directory.")
    args = parser.parse_args()

    summary = process_export(args.source, args.output)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

