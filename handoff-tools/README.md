# Handoff change review

Dependency-free Python; no network, model calls, cache writes or publication.

```sh
python handoff_diff.py before.json after.json
python handoff_diff.py before.json after.json --state state.json --now 2026-10-29T10:00:00Z --complete-snapshot
python -m unittest -v test_handoff_diff.py
```

Rows require distinct string IDs. Supports title/name and updated_at/modified_time/modifiedTime aliases, plus optional content_sha256. Conflicting aliases fail. Equivalent timezone timestamps compare equally. Missing version evidence is UNKNOWN, not unchanged.

Synthetic state example:
```json
{"gates":["No spending"],"sources":[{"id":"a","url":"https://example.org/a","review_on":"change","next_review_at":"2026-10-30T10:00:00Z"}],"tasks":[{"id":"task-a","status":"blocked","owner":"Reviewer","reason":"Awaiting evidence"}]}
```

The packet preserves gates and unresolved tasks verbatim. It selects new/changed/unknown/missing/due source references without copying bodies. Missing review triggers require review. Tasks without a review date remain due. Only explicit done/cancelled tasks are omitted; require closure receipts before setting those statuses.

Set --complete-snapshot only after enumerating every expected page/access scope. Missing rows are not deletions. before.json represents successfully READ versions, not a search watermark. After successful fetch/review, record the exact source version, evidence, check date and next trigger privately. Retain failures and old checkpoints. This tool does not write caches or advance watermarks.

A no-change candidate concerns only supplied state. It does not verify current accounts, queues, comments, revenue, permissions or publication gates. Reopen relevant sources on conflict, cache loss, stale evidence and before external action. Operators remain responsible for current facts and source fidelity.

Keep private source bodies, CRM, state and credentials out of public repositories. Tests are synthetic. Input/packet size is measurable; actual model token savings and end-to-end quality remain unmeasured.
