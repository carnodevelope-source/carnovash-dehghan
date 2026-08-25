"""Repeatedly execute the read-only load probe; no production mutation occurs."""

import argparse
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration-minutes', type=int, required=True)
    parser.add_argument('--interval-seconds', type=int, default=60)
    parser.add_argument('load_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    deadline = time.monotonic() + max(1, args.duration_minutes) * 60
    while time.monotonic() < deadline:
        result = subprocess.run([sys.executable, 'scripts/realtime_load.py', *args.load_args], check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
        time.sleep(max(1, args.interval_seconds))


if __name__ == '__main__':
    main()
