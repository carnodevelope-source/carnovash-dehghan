"""Conservative chain-aware retention planning; no filesystem deletions.

Callers MUST independently verify the encrypted chain and subscription before
removing any archive. A failed verification must leave every archive intact.
"""
from dataclasses import dataclass
from datetime import timedelta
from .schedule import local_day, RETENTION_DAYS


@dataclass(frozen=True)
class Archive:
    name: str
    timestamp: object
    kind: str
    verified: bool


def plan_retention(archives, now, *, minimum_chains=3):
    """Return (retained, deletion_candidates), with whole dependency chains.

    Unknown, duplicate, unverified, or orphan entries fail closed.
    This function never deletes or verifies actual archive contents.
    """
    if minimum_chains < 1:
        raise ValueError('invalid_minimum_chains')
    ordered = sorted(archives, key=lambda a: (a.timestamp, a.name))
    if len({a.name for a in ordered}) != len(ordered):
        raise ValueError('duplicate_archive')
    chains = []
    for item in ordered:
        if not item.verified or item.kind not in {'full', 'incremental'}:
            raise ValueError('unverified_or_unknown_archive')
        if local_day(item.timestamp) > local_day(now):
            raise ValueError('future_archive')
        if item.kind == 'full':
            chains.append([item])
        elif not chains:
            raise ValueError('orphan_incremental')
        else:
            chains[-1].append(item)
    cutoff = local_day(now) - timedelta(days=RETENTION_DAYS)
    keep_indices = {i for i, chain in enumerate(chains) if local_day(chain[-1].timestamp) >= cutoff}
    keep_indices.update(range(max(0, len(chains) - minimum_chains), len(chains)))
    retained = [item for i, chain in enumerate(chains) if i in keep_indices for item in chain]
    candidates = [item for i, chain in enumerate(chains) if i not in keep_indices for item in chain]
    return retained, candidates
