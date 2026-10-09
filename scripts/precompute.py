"""Warm the FastF1 disk cache for selected completed races."""

import argparse
import os
from time import perf_counter

from f1companion.data import (
    F1DataError,
    enable_cache,
    list_races,
    load_fastest_lap_telemetry,
    load_race,
)


def main(argv: list[str] | None = None) -> int:
    """Warm race caches, continuing on friendly data errors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--rounds", type=int, nargs="+")
    parser.add_argument("--with-telemetry", nargs="+", metavar="DRIVER")
    parser.add_argument("--cache-dir")
    args = parser.parse_args(argv)
    previous = os.environ.get("F1COMPANION_CACHE_DIR")
    try:
        # Loaders call enable_cache() without arguments; keep their path consistent.
        if args.cache_dir is not None:
            os.environ["F1COMPANION_CACHE_DIR"] = args.cache_dir
        enable_cache()
        if args.rounds is None:
            try:
                rounds = list_races(args.year)["RoundNumber"].tolist()
            except F1DataError as exc:
                print(str(exc))
                return 1
        else:
            rounds = args.rounds
        failed = False
        for index, round_number in enumerate(rounds, 1):
            start = perf_counter()
            prefix = f"[{index}/{len(rounds)}] {args.year} R{round_number}"
            try:
                race = load_race(args.year, round_number)
                prefix += f" {race.info.event_name}"
                for driver in args.with_telemetry or []:
                    load_fastest_lap_telemetry(args.year, round_number, driver)
            except F1DataError as exc:
                failed = True
                print(f"{prefix} ... {exc} ({perf_counter() - start:.1f}s)")
            else:
                print(f"{prefix} ... ok ({perf_counter() - start:.1f}s)")
        return int(failed)
    finally:
        if args.cache_dir is not None:
            if previous is None:
                os.environ.pop("F1COMPANION_CACHE_DIR", None)
            else:
                os.environ["F1COMPANION_CACHE_DIR"] = previous


if __name__ == "__main__":
    raise SystemExit(main())
