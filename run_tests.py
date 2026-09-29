"""Run every test for one vertical: parallel first, then the tenant-wide ('serial') tests one at a time.

    python run_tests.py                      # retail, 4 workers
    python run_tests.py --tenant galaxy
    python run_tests.py --tenant restaurant --workers 6
    python run_tests.py --tenant galaxy -- -k purchases    # extra pytest args after --

Reports: reports/<tenant>_parallel.html|xml and reports/<tenant>_serial.html|xml.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TENANTS = ("retail", "galaxy", "restaurant")


def run_phase(tenant: str, label: str, marker: str, extra: list[str], workers: int | None) -> int:
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    command = [
        sys.executable, "-m", "pytest",
        "--tenant", tenant,
        "-m", marker,
        "-o", "addopts=-v -rfEX",
        f"--junit-xml={reports / f'{tenant}_{label}.xml'}",
        f"--html={reports / f'{tenant}_{label}.html'}", "--self-contained-html",
    ]
    if workers:
        command += ["-n", str(workers), "--dist", "loadfile"]
    command += extra
    print(f"\n=== {tenant}: {label} phase ===\n{' '.join(command)}\n", flush=True)
    return subprocess.call(command, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tenant", choices=TENANTS, default="retail")
    parser.add_argument("--workers", type=int, default=4, help="parallel workers for the first phase")
    args, extra = parser.parse_known_args()
    extra = [arg for arg in extra if arg != "--"]

    parallel = run_phase(args.tenant, "parallel", "not serial", extra, args.workers)
    serial = run_phase(args.tenant, "serial", "serial", extra, None)

    # pytest exit code 5 means "no tests collected", which is fine for one of the phases.
    codes = [code for code in (parallel, serial) if code != 5]
    return max(codes, default=0)


if __name__ == "__main__":
    sys.exit(main())
