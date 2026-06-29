from __future__ import annotations

import argparse
import json
from pathlib import Path

from facebook_identity_variants.batch import process_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Facebook identity variants across multiple export packs and write master crosscheck outputs.")
    parser.add_argument("--source", required=True, action="append", type=Path, help="Facebook export folder or .zip file. Repeat for multiple packs.")
    parser.add_argument("--output", required=True, type=Path, help="Batch output directory.")
    parser.add_argument("--alias-map", type=Path, help="Optional JSON alias map applied to each source pack.")
    args = parser.parse_args()

    summary = process_batch(args.source, args.output, args.alias_map)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
