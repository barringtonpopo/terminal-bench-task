#!/usr/bin/env python3
"""Deterministic generator for the task's input data.

No randomness: every rate and timestamp is a literal, so regenerating the
files is byte-identical, and verify.py checks exactly that. The guard at
the bottom refuses any rate whose annualised value rounds ambiguously
near a .05 boundary, so graders never argue with float rounding.
"""

import csv
import gzip
import io
import json
import sys
from pathlib import Path

OUT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).parent.parent / "funding-spread-report" / "environment" / "data"
)

# Hourly funding rates in units of 1e-7. asset: (hyperliquid, dydx).
# None means the venue does not list the asset.
RATES = {
    "BTC": (126, -21),
    "ETH": (134, 8),
    "SOL": (134, 0),
    "AVAX": (91, 34),
    "DOGE": (-47, 13),
    "LINK": (62, 62),
    "ARB": (18, -33),
    "OP": (27, -8),
    "SUI": (174, 42),
    "APT": (88, 17),
    "SEI": (-112, -29),
    "TIA": (203, 66),
    "INJ": (57, 23),
    "NEAR": (39, -11),
    "TON": (-66, -66),
    "XRP": (45, 10),
    "ADA": (31, 6),
    "DOT": (22, -17),
    "ATOM": (-38, 5),
    "LTC": (16, 3),
    "HYPE": (412, None),
    "PURR": (239, None),
    "JUP": (78, None),
    "TRX": (None, 11),
    "BCH": (None, -6),
    "ETC": (None, 21),
}

# Decoy earlier observations per venue, in the same 1e-7 units. The task
# requires the most recent observation, so these must be ignored.
DECOY_OFFSETS = (57, -34)

HOURS = ["2026-08-03T12:00:00Z", "2026-08-03T13:00:00Z", "2026-08-03T14:00:00Z"]
EPOCH_MS = {h: [1785758400000, 1785762000000, 1785765600000][i] for i, h in enumerate(HOURS)}

# Assets whose latest dYdX row has an empty rate. Rows with empty rates
# must be skipped, so the latest valid (earlier) observation applies.
DYDX_EMPTY_LATEST = {"ATOM", "LTC"}
# Hyperliquid rate strings padded with stray whitespace.
HL_PADDED = {"ETH", "SEI", "TIA"}
# Hyperliquid lines duplicated verbatim.
HL_DUPLICATED = {"BTC"}


def rate_str(units):
    return f"{units / 1e7:.7f}".rstrip("0").rstrip(".") if units else "0"


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    hl_lines = []
    for asset, (hl, _) in RATES.items():
        if hl is None:
            continue
        history = [hl + DECOY_OFFSETS[0], hl + DECOY_OFFSETS[1], hl]
        for hour, units in zip(HOURS, history):
            value = rate_str(units)
            if asset in HL_PADDED and hour == HOURS[-1]:
                value = f"  {value} "
            line = json.dumps(
                {"coin": asset, "time": hour, "funding_rate": value}
            )
            hl_lines.append(line)
            if asset in HL_DUPLICATED and hour == HOURS[-1]:
                hl_lines.append(line)
    # Interleave so nothing is conveniently sorted.
    hl_lines = hl_lines[1::2] + hl_lines[0::2]
    payload = ("\n".join(hl_lines) + "\n").encode()
    # Fixed mtime and no filename in the gzip header keep bytes stable.
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as handle:
        handle.write(payload)
    (OUT / "hyperliquid_funding.jsonl.gz").write_bytes(buffer.getvalue())

    rows = []
    for asset, (_, dd) in RATES.items():
        if dd is None:
            continue
        history = [dd + DECOY_OFFSETS[1], dd, dd]
        for i, hour in enumerate(HOURS):
            is_latest = hour == HOURS[-1]
            if asset in DYDX_EMPTY_LATEST and is_latest:
                value = ""
            else:
                value = rate_str(history[i])
            rows.append([f"{asset}-USD", str(EPOCH_MS[hour]), value])
    rows = rows[2::3] + rows[0::3] + rows[1::3]
    with (OUT / "dydx_funding.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "timestamp_ms", "rate"])
        writer.writerows(rows)

    # Rounding-ambiguity guard: every annualised value and spread must sit
    # a safe distance from a .05 rounding boundary.
    def annualised(units):
        return units / 1e7 * 24 * 365 * 100

    checked = []
    for asset, (hl, dd) in RATES.items():
        if hl is None or dd is None:
            continue
        dd_effective = dd if asset not in DYDX_EMPTY_LATEST else dd
        a, b = annualised(hl), annualised(dd_effective)
        for value in (a, b, abs(a - b)):
            distance = abs((value * 10) % 1 - 0.5)
            assert distance > 0.05, f"{asset}: {value} rounds ambiguously"
            checked.append(value)
    print(f"wrote both files, {len(checked)} values checked against rounding boundaries")


if __name__ == "__main__":
    main()
