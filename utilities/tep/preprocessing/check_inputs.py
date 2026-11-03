"""Report metric inputs or test whether one preprocessing output group exists."""

import argparse

from tep_metrics.core.config import load_config
from tep_metrics.core.input_availability import (
    missing_metric_inputs,
    preprocessing_group_paths,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/scenario_metrics.json")
    parser.add_argument("--group", choices=[
        "core_summaries", "highway", "transit_sequences",
        "transit_waiting", "nonmotorized",
    ])
    parser.add_argument("--verbose", action="store_true",
                        help="list every missing path instead of summary counts")
    args = parser.parse_args()
    config = load_config(args.config)

    if args.group:
        missing = [path for path in preprocessing_group_paths(config)[args.group]
                   if not path.exists()]
        if missing:
            for path in missing:
                print(path)
            raise SystemExit(1)
        print(f"READY: {args.group}")
        return

    missing = missing_metric_inputs(config)
    if not missing:
        print("All enabled metrics have their direct inputs.")
        return
    for metric, paths in missing.items():
        print(f"{metric}: {len(paths)} missing direct input file(s)")
        if args.verbose:
            for path in paths:
                print(f"  MISSING {path}")


if __name__ == "__main__":
    main()
