# Tournament-day runbook

A chronological checklist for the event. Times are examples — shift everything if your agenda differs.

## T-1 day (the evening before)

- [ ] Pull latest on the repo, re-run `./engine/pull-engine.sh` to bump the engine pin if needed
- [ ] Build the Docker images locally: `docker compose build`
- [ ] Run a full self-play match: `docker compose up --build` → watch at `http://localhost:3000/` → verify the engine shuts down cleanly at game end
- [ ] Dry-run the match runner against the reference AI playing both sides:
      `python3 match-runner/run_match.py --team-a http://localhost:8080/action --team-b http://localhost:8080/action`
- [ ] Verify the big-screen dashboard loads and renders `state.example.json` correctly on the actual projector
- [ ] Make sure your laptop's power saver won't sleep during the day
- [ ] Print or pre-open: team doc, slide deck, reference AI URL, match runner command

## T-30 min (teams arriving)

- [ ] Connect laptop to projector, test fullscreen
- [ ] Start the big-screen dashboard and leave it on a splash state
- [ ] Start the reference AI: `docker run -d --name ref-ai -p 8080:8080 bomberman-offsite/reference-ai`
- [ ] Note your laptop's LAN IP; write on the whiteboard:
      ```
      Reference AI:  http://<your-ip>:8080/action
      Organizer:     http://<your-ip>
      ```
- [ ] Confirm each team's machine is on the LAN and can `curl` the reference AI

## Kickoff (T+0)

- [ ] Project `slides/kickoff.md` (or the copy you've made in your slide tool)
- [ ] Walk through rules, REST contract, game_state, quickstart
- [ ] Demo: run the reference AI against itself live on screen
- [ ] Distribute:
      - Link to `docs/teams/`
      - Reference AI URL
      - An assigned IP/port per team (they run their bot there)
      - `README.md` of `example-bots/` for a stub they can fork
- [ ] Confirm timebox and tournament format (1v1, best of N)
- [ ] Questions

## Coding time (T+30 min → T+4h)

- [ ] Walk around every ~30 min, help teams stuck on wire format or environment
- [ ] When a team says "I think I'm ready", run a scrimmage against the reference AI:
      ```bash
      python3 match-runner/run_match.py \
        --team-a http://<team-ip>:8080/action --name-a "<team>" \
        --team-b http://localhost:8080/action  --name-b "reference-ai"
      ```
      Share the winner and tick count with them.
- [ ] ~30 min before tournament time, freeze submissions: teams stop deploying new bot versions

## Tournament (T+4h → T+5h)

- [ ] Generate the bracket / round-robin pools with your external tool — output a list of `(team_a_url, team_b_url, name_a, name_b)` pairs
- [ ] For each pair, update `big-screen/state.json` to the current match and run the match runner. Pipe its JSON into your leaderboard tool.
- [ ] Commentate. Keep tempo: ~2 min per match at worst.
- [ ] Between rounds, update `state.json` standings (a 5-line script is enough)

## Finals + reference AI exhibition (T+5h → T+5h30)

- [ ] Best-of-3 final on the projector
- [ ] Exhibition: finals winner vs. the reference AI
- [ ] Prizes

## Teardown (T+5h30+)

- [ ] `docker compose down -v` on every host that ran matches
- [ ] Archive `match-runner/out/` and `tournament.jsonl`
- [ ] Export the big-screen `state.json` as the final leaderboard
- [ ] Upload a couple of replay files somewhere retrievable for bragging rights

## Emergency plan

If the engine crashes mid-tournament: see [`05-troubleshooting.md`](05-troubleshooting.md). If a team's bot is unreachable at match time, they forfeit that match (document this in the kickoff so it's not a surprise). If the whole network goes down, fall back to running all bots locally on the organizer laptop — each team hands you their code, you run it in a throwaway Docker container on port 808X.
