from __future__ import annotations

import argparse
import json
from pathlib import Path

from facebook_identity_variants.extractor import process_export


def main() -> int:
    parser = argparse.ArgumentParser(description="Track Facebook identity variants by name, Facebook ID, and IP.")
    parser.add_argument("--source", required=True, type=Path, help="Extracted Facebook export folder or .zip file.")
    parser.add_argument("--output", required=True, type=Path, help="Output directory.")
    parser.add_argument("--alias-map", type=Path, help="Optional JSON alias map for known master identity groupings.")
    args = parser.parse_args()

    summary = process_export(args.source, args.output, args.alias_map)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
