# Tests

Offline test suite — no Docker, no engine, no network.

## Run everything

```bash
python3 -m unittest discover -s tests -v
```

## Modules

### `test_adapter_logic.py`

- `GameStateMirror`: initial state, entity events, wrapped `tick` packets
- `Adapter._normalize_actions`: wire format → engine action packets

### `test_adapter_mirror.py`

- `unit/move` event handling (the coordinate-update path that fixed the stale-position bug)

### `smoke_test.py`

End-to-end HTTP contract check against the reference AI and naive bot (stdlib only).

```bash
python3 tests/smoke_test.py
```
