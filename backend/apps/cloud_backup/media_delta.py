"""Manifest-level media changes for a tenant backup chain.

Digests must come from verified encrypted archives or a guarded media scan;
this module never trusts filenames or copies bytes on its own.
"""
import re
from .snapshot import safe_relative

SHA256 = re.compile(r'^[0-9a-f]{64}$')


def validate_media_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError('Invalid media manifest')
    for name, sha in manifest.items():
        if not isinstance(name, str) or safe_relative(name) != name or not isinstance(sha, str) or not SHA256.fullmatch(sha):
            raise ValueError('Invalid media manifest entry')
    return manifest


def diff_media(previous, current):
    before = validate_media_manifest(previous)
    after = validate_media_manifest(current)
    return {
        'upserts': {name: after[name] for name in sorted(after) if before.get(name) != after[name]},
        'deletes': sorted(before.keys() - after.keys()),
    }


def apply_media(previous, delta):
    merged = dict(validate_media_manifest(previous))
    if not isinstance(delta, dict):
        raise ValueError('Invalid media delta')
    upserts = validate_media_manifest(delta.get('upserts'))
    deletes = delta.get('deletes')
    if not isinstance(deletes, list) or len(set(deletes)) != len(deletes):
        raise ValueError('Invalid media tombstones')
    for name in deletes:
        if not isinstance(name, str) or name not in merged or name in upserts:
            raise ValueError('Conflicting media tombstone')
        del merged[name]
    merged.update(upserts)
    return merged
