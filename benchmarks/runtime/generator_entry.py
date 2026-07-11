from __future__ import annotations

import argparse
import json
from pathlib import Path

from mmagent.benchmark_cases import generate_case_data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=Path("."))
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    root = args.run_root.resolve()
    case = json.loads((root / "case.json").read_text(encoding="utf-8"))
    generate_case_data(root, str(case["id"]), int(case["random_seed"] if args.seed is None else args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
