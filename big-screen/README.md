# Big-screen dashboard

A single-page HTML dashboard for the tournament screen. Wraps the Bomberland viewer in an iframe, surrounds it with team names and a live standings table.

## How to run it

```bash
cd big-screen
python3 -m http.server 8000
# then open on the projector machine:
# http://localhost:8000/?engine=http://<engine-host>:3000
```

Or point it at a remote engine with the `?engine=` query param.

## Updating the overlay

The page polls `state.json` next to it every 2 s (configurable via `?pollMs=`). Copy `state.example.json` to `state.json` as a starting point, then have your match runner or tournament tool overwrite it between matches.

```json
{
  "current_match": { "a": "Team Red", "b": "Team Blue", "round": "Pool A / match 3" },
  "standings":     [ { "name": "Team Red",  "wins": 2, "losses": 0 }, ... ]
}
```

If `state.json` is missing, the team names fall back to `—` and standings show "No results yet" — useful between matches without errors in the console.

## Layout

- Top HUD: team A (left, blue) • match title (centre) • team B (right, pink)
- Centre: embedded viewer iframe, full-bleed
- Bottom: 3-row, scrollable standings list

Designed for 1920x1080. If your projector has a different aspect ratio, `style.css`'s `.stage` grid template is the only thing you'll need to adjust.
