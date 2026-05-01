// Minimal "random mover" Bomberman bot in Node.js (no dependencies).
// Run it with: node random_bot.mjs
// Then point an adapter at: http://<this-host>:8080/action

import http from "node:http";

const ACTIONS = ["up", "down", "left", "right", "bomb", "stay"];
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

http
  .createServer((req, res) => {
    if (req.method !== "POST" || req.url !== "/action") {
      res.writeHead(404).end();
      return;
    }
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const payload = JSON.parse(raw || "{}");
      const me = payload.you ?? "a";
      const unitIds = payload.game_state.agents[me].unit_ids;
      const actions = unitIds.map((unit_id) => ({
        unit_id,
        action: pick(ACTIONS),
      }));
      const body = JSON.stringify({ actions });
      res.writeHead(200, { "Content-Type": "application/json" }).end(body);
    });
  })
  .listen(8080);
