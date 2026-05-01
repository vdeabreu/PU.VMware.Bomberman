// Big-screen dashboard controller.
//
// Two data sources:
//
//   1. The Bomberland viewer is embedded in an <iframe>. By default it points
//      at http://localhost:3000/?role=spectator, which is the viewer served by
//      the engine container. Override with ?engine=<base-url> in the URL.
//
//   2. Match metadata (team names, current match, standings) is polled from a
//      local JSON file `state.json` in this directory. Your match runner or
//      your pool/bracket tool should overwrite that file between matches.
//
// state.json shape:
//   {
//     "current_match": { "a": "Team Red", "b": "Team Blue", "round": "Pool A / match 3" },
//     "standings": [ { "name": "Team Red", "wins": 2, "losses": 0 }, ... ]
//   }
//
// This file never writes; it only reads state.json (HTTP GET). Serve this
// folder with any static file server, e.g. `python3 -m http.server 8000`.

(() => {
  const params = new URLSearchParams(window.location.search);
  const engineBase = params.get("engine") || "http://localhost:3000";
  const stateUrl = params.get("state") || "state.json";
  const pollMs = Number(params.get("pollMs") || 2000);

  const viewer = document.getElementById("viewer");
  const placeholder = document.getElementById("placeholder");
  const nameA = document.getElementById("team-a-name");
  const nameB = document.getElementById("team-b-name");
  const sub = document.getElementById("match-sub");
  const standingsList = document.getElementById("standings-list");

  const spectatorUrl = `${engineBase.replace(/\/$/, "")}/?role=spectator`;
  viewer.src = spectatorUrl;
  viewer.addEventListener("load", () => placeholder.classList.add("hidden"));

  async function poll() {
    try {
      const r = await fetch(`${stateUrl}?_=${Date.now()}`, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      render(await r.json());
    } catch {
      // Silent: missing state.json is the normal "no match yet" state.
    }
  }

  function render(state) {
    const m = state.current_match || {};
    nameA.textContent = m.a || "—";
    nameB.textContent = m.b || "—";
    sub.textContent = m.round || "Live match";

    const rows = state.standings || [];
    standingsList.innerHTML = "";
    if (!rows.length) {
      const li = document.createElement("li");
      li.className = "standings-empty";
      li.textContent = "No results yet";
      standingsList.appendChild(li);
      return;
    }
    rows.forEach((row, i) => {
      const li = document.createElement("li");
      const wins = row.wins ?? 0;
      const losses = row.losses ?? 0;
      li.innerHTML = `
        <span class="rank">#${i + 1}</span>
        <span class="name">${escapeHtml(row.name || "?")}</span>
        <span class="score">${wins}W-${losses}L</span>
      `;
      standingsList.appendChild(li);
    });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  poll();
  setInterval(poll, pollMs);
})();
