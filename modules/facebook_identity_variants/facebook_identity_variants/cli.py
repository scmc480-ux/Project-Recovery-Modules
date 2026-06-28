from __future__ import annotations

import argparse
import json
from pathlib import Path

from facebook_identity_variants.batch import process_batch
from facebook_identity_variants.extractor import process_export


def main() -> int:
    parser = argparse.ArgumentParser(description="Track Facebook identity variants and write optional master batch crosscheck outputs.")
    parser.add_argument(
        "--source",
        required=True,
        action="append",
        type=Path,
        help="Extracted Facebook export folder or .zip file. Repeat for multi-pack batch mode.",
    )
    parser.add_argument("--output", required=True, type=Path, help="Output directory.")
    parser.add_argument("--alias-map", type=Path, help="Optional JSON alias map for known master identity groupings.")
    parser.add_argument("--batch", action="store_true", help="Write master batch crosscheck outputs, even when one source is supplied.")
    args = parser.parse_args()

    if args.batch or len(args.source) > 1:
        summary = process_batch(args.source, args.output, args.alias_map)
    else:
        summary = process_export(args.source[0], args.output, args.alias_map)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
