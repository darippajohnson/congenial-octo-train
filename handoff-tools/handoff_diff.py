"""Compare local handoff metadata snapshots; no network, paid API or model calls.
Input: JSON arrays with id, title, updated_at, optional content_sha256.
Output identifies changes; it never deletes, moves or publishes files.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

def compare(before, after):
    def index(rows):
        if not isinstance(rows, list):
            raise ValueError("Snapshot must be a JSON array.")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                raise ValueError("Each record needs a nonempty string id.")
        counts=Counter(r["id"] for r in rows)
        if any(n > 1 for n in counts.values()):
            raise ValueError("Duplicate file IDs: reconcile before comparison.")
        return {r["id"]:r for r in rows}
    old,new=index(before),index(after)
    def signature(r):
        return (r.get("title"),r.get("updated_at"),r.get("content_sha256"))
    changed=[new[k] for k in sorted(new.keys() & old.keys()) if signature(new[k]) != signature(old[k])]
    return {"added":[new[k] for k in sorted(new.keys()-old.keys())],
            "changed":changed,
            "missing_from_snapshot":[old[k] for k in sorted(old.keys()-new.keys())],
            "unchanged_count":sum(signature(new[k]) == signature(old[k]) for k in new.keys() & old.keys()),
            "note":"Missing does not mean deleted. Preserve original files and verify access/pagination."}

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("before",type=Path);p.add_argument("after",type=Path)
    a=p.parse_args()
    print(json.dumps(compare(json.loads(a.before.read_text()),json.loads(a.after.read_text())),indent=2))
