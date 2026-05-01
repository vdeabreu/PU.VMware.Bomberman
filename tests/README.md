# Tests

Two offline test scripts — neither requires Docker, neither needs the Bomberland engine to be fetched.

## `test_adapter_logic.py`

Unit tests for the HTTP adapter's pure logic:

- `GameStateMirror`: that each of the engine's event types (initial full state, `unit_state`, `entity_spawned`, `entity_expired`, `entity_state`, `tick`) is reduced correctly into the local snapshot.
- `Adapter._normalize_actions`: that our simplified wire format is translated into Bomberland's action packet format correctly, and that malformed / hostile inputs (enemy unit ids, missing coordinates, unknown verbs, non-dict responses) are silently dropped with a warning.

Run:

```bash
python3 tests/test_adapter_logic.py
```

No network, no subprocess, no deps — runs in ~50 ms.

## `smoke_test.py`

End-to-end smoke test that boots both the reference AI and the stdlib random-mover bot as subprocesses, POSTs five realistic `game_state` packets to each, and verifies:

- `200 OK` with valid JSON
- Response is either `{"actions": [...]}` or a bare list
- Every action references one of the agent's own unit IDs
- Every action verb is in the allowed set
- `detonate` actions carry `coordinates`
- Per-call latency is under the 300 ms budget

Run:

```bash
python3 tests/smoke_test.py
```

~3 s total. Requires nothing beyond Python 3.9+ and the repo checked out.

## What these tests do **not** cover

- Actually running the Bomberland engine (fetching the submodule + Docker required)
- Full match dynamics: these are contract tests, not simulation tests
- Network resilience (timeouts, partial failures) in the adapter — those paths are tested only via code review

To cover those, do a manual dry-run:

```bash
./engine/pull-engine.sh
docker compose up --build
# Watch at http://localhost:3000/ — reference AI plays itself.
```

and then a match-runner run:

```bash
# In another terminal, with the reference AI still running on port 8080:
python3 match-runner/run_match.py \
  --team-a http://localhost:8080/action --name-a "ref-ai-a" \
  --team-b http://localhost:8080/action --name-b "ref-ai-b"
```

Do this at least once before the offsite.
