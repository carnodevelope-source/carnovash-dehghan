"""Read-only HTTP/SSE load probe for an explicitly supplied staging URL."""

import argparse
import concurrent.futures
import json
import time
import urllib.request


def request(url, cookie, timeout):
    headers = {'Cookie': cookie} if cookie else {}
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            response.read(1024)
            return {'ok': 200 <= response.status < 400, 'status': response.status, 'seconds': time.perf_counter() - started}
    except Exception as exc:
        return {'ok': False, 'error': str(exc), 'seconds': time.perf_counter() - started}


def sse_connect(url, cookie, timeout, hold_seconds):
    headers = {'Accept': 'text/event-stream'}
    if cookie:
        headers['Cookie'] = cookie
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            deadline = time.monotonic() + hold_seconds
            while time.monotonic() < deadline:
                response.readline()
            return {'ok': response.status == 200, 'status': response.status, 'seconds': time.perf_counter() - started}
    except Exception as exc:
        return {'ok': False, 'error': str(exc), 'seconds': time.perf_counter() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--requests', type=int, default=100)
    parser.add_argument('--concurrency', type=int, default=10)
    parser.add_argument('--cookie', default='')
    parser.add_argument('--timeout', type=float, default=10)
    parser.add_argument('--sse-clients', type=int, default=0)
    parser.add_argument('--sse-hold-seconds', type=float, default=15)
    args = parser.parse_args()
    url = args.base_url.rstrip('/') + '/api/health/ready/'
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        results = list(pool.map(lambda _: request(url, args.cookie, args.timeout), range(max(1, args.requests))))
    durations = sorted(item['seconds'] for item in results)
    percentile = lambda ratio: durations[min(len(durations) - 1, int(len(durations) * ratio))]
    report = {
        'scenario': 'read_only_readiness', 'requests': len(results), 'concurrency': args.concurrency,
        'successes': sum(item['ok'] for item in results), 'failures': sum(not item['ok'] for item in results),
        'p50_seconds': percentile(.50), 'p95_seconds': percentile(.95), 'p99_seconds': percentile(.99),
    }
    if args.sse_clients:
        if not args.cookie:
            parser.error('--cookie is required for authenticated SSE clients')
        sse_url = args.base_url.rstrip('/') + '/api/live/events/'
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.sse_clients) as pool:
            sse_results = list(pool.map(
                lambda _: sse_connect(sse_url, args.cookie, args.timeout, args.sse_hold_seconds),
                range(args.sse_clients),
            ))
        report['sse'] = {
            'clients': args.sse_clients,
            'connected': sum(item['ok'] for item in sse_results),
            'failed': sum(not item['ok'] for item in sse_results),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
