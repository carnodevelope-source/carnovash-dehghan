# Soak Test Report — 2026-08-25

Status: **NOT RUN / BLOCKED.** No staging stack was available, so no duration,
memory slope, listener count, DB-connection trend, event lag, or recovery data
exists.

Run the agreed staging workload long enough to expose daily cleanup and
reconnect behaviour. Include repeated navigation/mount-unmount cycles, hidden
tab transitions, SSE reconnects, a Redis outage, and graceful worker restart.
Compare start/end RSS, active listeners, timers, DB sessions, error rate, and
latency. A rising trend requires diagnosis before any canary.

`scripts/realtime_soak.py` repeatedly runs the read-only load probe for a
specified duration. Platform metrics collection and a staging target are still
external prerequisites.
