#!/usr/bin/env python3
"""Reference implementation of the task spec.

Derives the expected report from the committed data files and prints it
as a Python literal for embedding in the tests. Deliberately written
independently of solution/solve.sh, so the task carries two
implementations of the spec that must agree.
"""

import csv
import gzip
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "funding-spread-report" / "environment" / "data"


def hyperliquid_latest():
    latest = {}
    with gzip.open(DATA / "hyperliquid_funding.jsonl.gz", "rt") as handle:
        for line in handle:
            row = json.loads(line)
            coin, when = row["coin"], row["time"]
            if coin not in latest or when > latest[coin][0]:
                latest[coin] = (when, float(row["funding_rate"].strip()))
    return {coin: rate for coin, (_, rate) in latest.items()}


def dydx_latest():
    latest = {}
    with (DATA / "dydx_funding.csv").open() as handle:
        for row in csv.DictReader(handle):
            if not row["rate"].strip():
                continue
            asset = row["ticker"].removesuffix("-USD")
            when = int(row["timestamp_ms"])
            if asset not in latest or when > latest[asset][0]:
                latest[asset] = (when, float(row["rate"].strip()))
    return {asset: rate for asset, (_, rate) in latest.items()}


def expected_rows():
    hl, dd = hyperliquid_latest(), dydx_latest()
    rows = []
    for asset in hl.keys() & dd.keys():
        a = hl[asset] * 24 * 365 * 100
        b = dd[asset] * 24 * 365 * 100
        spread = abs(a - b)
        rows.append((asset, f"{a:.1f}", f"{b:.1f}", f"{spread:.1f}"))
    rows.sort(key=lambda r: (-float(r[3]), r[0]))
    return rows


if __name__ == "__main__":
    print("EXPECTED_ROWS = [")
    for row in expected_rows():
        print(f"    {row!r},")
    print("]")
