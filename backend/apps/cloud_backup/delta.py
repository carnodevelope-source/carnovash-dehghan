"""Pure tenant fixture delta logic. No production DB or archive writes.

A delta includes changed rows, new rows and tombstones for deleted rows.
The caller must validate both the base fixture and the reconstructed result
with the tenant-scoped restore validator before writing any recovery database.
"""
import hashlib
import json


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def index_fixture(fixture):
    if not isinstance(fixture, list):
        raise ValueError('Fixture must be a list')
    result = {}
    for row in fixture:
        if not isinstance(row, dict) or not {'model', 'pk', 'fields'} <= row.keys():
            raise ValueError('Invalid fixture row')
        if not isinstance(row['model'], str) or not isinstance(row['pk'], (int, str)) or not isinstance(row['fields'], dict):
            raise ValueError('Invalid fixture identity')
        identity = (row['model'], str(row['pk']))
        if identity in result:
            raise ValueError('Duplicate fixture identity')
        result[identity] = row
    return result


def fixture_digest(fixture):
    rows = index_fixture(fixture)
    return digest([rows[key] for key in sorted(rows)])


def diff_fixture(previous, current):
    before, after = index_fixture(previous), index_fixture(current)
    changed = [after[key] for key in sorted(after) if key not in before or before[key] != after[key]]
    deleted = [[model, pk] for model, pk in sorted(before.keys() - after.keys())]
    return {'version': 1, 'base_sha256': fixture_digest(previous), 'result_sha256': fixture_digest(current),
            'upserts': changed, 'deletes': deleted}


def apply_fixture(previous, delta):
    if not isinstance(delta, dict) or delta.get('version') != 1 or fixture_digest(previous) != delta.get('base_sha256'):
        raise ValueError('Base fixture mismatch')
    merged = index_fixture(previous)
    updates = index_fixture(delta.get('upserts'))
    removed = delta.get('deletes')
    if not isinstance(removed, list):
        raise ValueError('Invalid tombstones')
    deleted = set()
    for item in removed:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError('Invalid tombstone')
        key = (item[0], str(item[1]))
        if key in deleted or key not in merged or key in updates:
            raise ValueError('Conflicting tombstone')
        deleted.add(key)
    for key in deleted:
        del merged[key]
    merged.update(updates)
    result = [merged[key] for key in sorted(merged)]
    if fixture_digest(result) != delta.get('result_sha256'):
        raise ValueError('Reconstructed fixture checksum mismatch')
    return result
