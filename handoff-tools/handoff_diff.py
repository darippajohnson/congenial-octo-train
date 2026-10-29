"""Metadata-only change review. No network/model calls, cache writes or publication."""
import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


def instant(value):
    if not isinstance(value, str):
        raise ValueError('Review dates must be ISO strings with timezone.')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Review dates require a timezone.')
    return parsed.astimezone(timezone.utc)


def alias(row, names, timestamp=False):
    values = []
    for name in names:
        value = row.get(name)
        if value is None or value == '':
            continue
        if not isinstance(value, str):
            raise ValueError(f'{name} must be a string.')
        if timestamp:
            try:
                value = instant(value).isoformat()
            except ValueError:
                pass  # Preserve legacy opaque version strings for comparison.
        values.append(value)
    if len(set(values)) > 1:
        raise ValueError(f'Conflicting aliases: {names}')
    return values[0] if values else None


def signature(row):
    return (alias(row, ('title', 'name')),
            alias(row, ('updated_at', 'modified_time', 'modifiedTime'), True),
            alias(row, ('content_sha256',)))


def index(rows):
    if not isinstance(rows, list):
        raise ValueError('Snapshot must be a JSON array.')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'].strip():
            raise ValueError('Each record needs a nonempty string id.')
        if row['id'] in result:
            raise ValueError('Duplicate IDs: reconcile before comparison.')
        signature(row)
        result[row['id']] = row
    return result


def compare(before, after):
    old, new = index(before), index(after)
    common = sorted(old.keys() & new.keys())
    unknown = {k for k in common if not any(signature(old[k])[1:]) or not any(signature(new[k])[1:])}
    changed = [k for k in common if k not in unknown and signature(old[k]) != signature(new[k])]
    return {'added': [new[k] for k in sorted(new.keys() - old.keys())],
            'changed': [new[k] for k in changed],
            'unknown_version': [new[k] for k in sorted(unknown)],
            'missing_from_snapshot': [old[k] for k in sorted(old.keys() - new.keys())],
            'unchanged_count': len(common) - len(unknown) - len(changed),
            'note': 'Missing is not deleted. Verify pagination/access; search metadata is not a successful read checkpoint.'}


def build_plan(before, after, state, now, complete_snapshot=False):
    """Select changed/unknown/due refs; retain every gate and unresolved task."""
    if not isinstance(complete_snapshot, bool):
        raise ValueError('complete_snapshot must be boolean.')
    if not isinstance(state, dict) or not isinstance(state.get('gates'), list) or not state['gates']:
        raise ValueError('Nonempty persistent gates required.')
    if not isinstance(state.get('tasks'), list) or not isinstance(state.get('sources'), list):
        raise ValueError('Explicit tasks and sources lists required.')
    now = instant(now)
    old, new, sources = index(before), index(after), index(state['sources'])
    diff = compare(before, after)
    reasons = {}
    for kind in ('added', 'changed', 'unknown_version', 'missing_from_snapshot'):
        for row in diff[kind]:
            reasons.setdefault(row['id'], []).append(kind)
    for key, source in sources.items():
        if key not in new:
            reasons.setdefault(key, []).append('required_source_missing')
        if source.get('review_on') != 'change':
            reasons.setdefault(key, []).append('review_trigger_unknown')
        if source.get('next_review_at') is not None and instant(source['next_review_at']) <= now:
            reasons.setdefault(key, []).append('review_due')
    for key in new:
        if key not in sources:
            reasons.setdefault(key, []).append('review_trigger_unknown')
    unresolved, due, seen = [], [], set()
    for task in state['tasks']:
        if not isinstance(task, dict) or not isinstance(task.get('id'), str) or not task['id'].strip() or task['id'] in seen:
            raise ValueError('Each task needs a distinct nonempty id.')
        seen.add(task['id'])
        if task.get('status') not in {'open', 'blocked', 'in_progress', 'done', 'cancelled'}:
            raise ValueError('Unknown task status; reconcile rather than discard.')
        review = instant(task['next_review_at']) if task.get('next_review_at') is not None else None
        if task['status'] not in {'done', 'cancelled'}:
            unresolved.append(deepcopy(task))
            if review is None or review <= now:
                due.append(task['id'])
    refs = []
    for key in sorted(reasons):
        record = new.get(key, old.get(key, {}))
        refs.append({'id': key, 'url': sources.get(key, {}).get('url', record.get('url')),
                     'title': signature(record)[0], 'reasons': sorted(set(reasons[key]))})
    return {'review_sources': refs, 'gates': deepcopy(state['gates']),
            'unresolved_tasks': unresolved, 'due_task_ids': due,
            'complete_snapshot': complete_snapshot, 'unchanged_count': diff['unchanged_count'],
            'reads_required': bool(refs),
            'no_change_candidate': complete_snapshot and not refs and not due,
            'checkpoint_policy': 'No checkpoint written. Save versions only after successful read/review; retain failures/old checkpoints. Incomplete pagination is not no-change.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--state', type=Path)
    parser.add_argument('--now')
    parser.add_argument('--complete-snapshot', action='store_true')
    args = parser.parse_args()
    try:
        before, after = (json.loads(path.read_text()) for path in (args.before, args.after))
        if args.state:
            if not args.now:
                parser.error('--state requires an explicit --now timestamp')
            result = build_plan(before, after, json.loads(args.state.read_text()), args.now, args.complete_snapshot)
        else:
            result = compare(before, after)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
