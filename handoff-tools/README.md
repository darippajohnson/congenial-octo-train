# Handoff change index
Dependency-free local utility for comparing two metadata exports. Python 3.
Run: python handoff_diff.py before.json after.json
Test: python -m unittest test_handoff_diff.py
Records: id, title, updated_at; optional content_sha256.
Only changed/new records need routine review. Missing records may reflect pagination or lost access, not deletion.
This utility does not summarize or remove source knowledge and never calls a model or network.
Keep private metadata/exports out of public repositories. All tests use synthetic IDs.
Token savings have not been measured; compare actual usage before making a performance claim.
