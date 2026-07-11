from mmagent.benchmark_cases import generate_case_data
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(); parser.add_argument("--run-root", type=Path); parser.add_argument("--seed", type=int)
args = parser.parse_args(); generate_case_data(args.run_root, "comprehensive_city_planning", args.seed)
