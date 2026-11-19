#!/usr/bin/env python3
"""Plans the daily Databento download so that each UTC day is downloaded once.

plan     Sets start and end in the nfetch config to the days that are missing.
pending  Lists the local daily .dbn.zst files that the lake lacks.
"""

import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys

NFETCH = pathlib.Path("/Users/zhou/Containers/apps/nfetch")
CONFIG = NFETCH / "daily_ohlcv1h.toml"
DAILY_FILES = NFETCH / "datasets/XNAS.ITCH/ohlcv-1h"
LAKE_TABLE = "lake.market.us_equity_ohlcv"

CONNECT_LAKE = """
INSTALL iceberg; LOAD iceberg;
CREATE SECRET (TYPE iceberg, URI 'http://localhost:8181',
               CLIENT_ID 'nqlake', CLIENT_SECRET 'nqlake-dev-secret');
ATTACH 'warehouse' AS lake (TYPE iceberg, URI 'http://localhost:8181');
"""

DAILY_FILE_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.dbn\.zst$")
ONE_DAY = dt.timedelta(days=1)


def last_day_in_lake() -> dt.date:
    query = f"{CONNECT_LAKE} SELECT max(ts_event) FROM {LAKE_TABLE};"
    result = subprocess.run(
        ["duckdb", "-csv", "-noheader", "-no-agent", "-c", query],
        capture_output=True, text=True)
    last_line = result.stdout.strip().splitlines()[-1:] or [""]
    if result.returncode != 0 or not last_line[0].isdigit():
        sys.exit("cannot read the lake. Is the nqlake-seaweedfs-1 container up?\n"
                 + result.stderr.strip())
    nanoseconds = int(last_line[0])
    return dt.datetime.fromtimestamp(nanoseconds // 10**9, dt.timezone.utc).date()


def local_daily_files() -> list[tuple[dt.date, pathlib.Path]]:
    files = []
    for path in DAILY_FILES.rglob("*.dbn.zst"):
        name = DAILY_FILE_NAME.match(path.name)
        if name:
            files.append((dt.date.fromisoformat(name.group(1)), path))
    return sorted(files)


def with_window(config_text: str, start: dt.date, end: dt.date) -> str:
    """Replaces the top-level start and end. The [[download]] entries inherit both."""
    top_level, separator, entries = config_text.partition("[[")
    for key, day in (("start", start), ("end", end)):
        top_level, replaced = re.subn(
            rf'(?m)^({key}\s*=\s*)"[^"]*"', rf'\g<1>"{day}"', top_level)
        if replaced != 1:
            sys.exit(f"{CONFIG}: expected one top-level '{key}' line, found {replaced}")
    return top_level + separator + entries


def plan(args: argparse.Namespace) -> None:
    lake_last = last_day_in_lake()
    local_days = [day for day, _ in local_daily_files()]
    last_day_held = max([lake_last, *local_days])
    start = last_day_held + ONE_DAY
    end = args.today

    print(f"lake has data up to {lake_last}")
    if last_day_held > lake_last:
        print(f"local files reach {last_day_held}; run 'pending' to load them")
    if start >= end:
        print(f"nothing to download: {end} is still open, config left unchanged")
        return
    print(f"download window: {start} .. {end} (end exclusive)")
    if args.check:
        print("check only, config left unchanged")
        return
    args.config.write_text(with_window(args.config.read_text(), start, end))
    print(f"wrote start and end to {args.config}")


def pending(args: argparse.Namespace) -> None:
    lake_last = last_day_in_lake()
    for day, path in local_daily_files():
        if day > lake_last:
            print(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    plan_command = commands.add_parser("plan", help="set start and end in the nfetch config")
    plan_command.add_argument("--check", action="store_true",
                              help="print the window, leave the config unchanged")
    plan_command.add_argument("--config", type=pathlib.Path, default=CONFIG,
                              help="config file to edit")
    plan_command.add_argument("--today", type=dt.date.fromisoformat,
                              default=dt.datetime.now(dt.timezone.utc).date(),
                              help="UTC day to treat as today (YYYY-MM-DD)")
    plan_command.set_defaults(run=plan)

    pending_command = commands.add_parser(
        "pending", help="list local daily .dbn.zst files that the lake lacks")
    pending_command.set_defaults(run=pending)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
