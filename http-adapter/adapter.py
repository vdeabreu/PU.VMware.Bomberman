"""HTTP adapter: bridges the Bomberland WebSocket engine to a team's HTTP bot.

The adapter connects to the engine as a single agent (A or B), keeps a local
mirror of the full game_state by reducing the server's event stream, and once
per tick POSTs that state to the team's bot endpoint. The bot replies with a
list of per-unit actions, which the adapter forwards back to the engine.

If the bot doesn't answer within BOT_TIMEOUT_MS, the adapter silently no-ops
for that tick (all units "stay" implicitly).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any, Optional

# aiohttp and websockets are only needed when actually running the adapter,
# not when unit-testing the pure-logic parts (mirror + action normalization).
# We import them lazily inside the async methods so that `import adapter`
# works in environments without those deps installed.

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [adapter-%(agent)s] %(message)s",
)


def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"missing required env var {name}")
    return value  # type: ignore[return-value]


class GameStateMirror:
    """Maintains a full game_state by applying engine events.

    The first packet we receive from the engine is the full initial state.
    Subsequent packets are events; we apply them here so the team bot always
    sees a fresh, complete snapshot.
    """

    def __init__(self) -> None:
        self.state: Optional[dict[str, Any]] = None

    def apply(self, packet: dict[str, Any]) -> None:
        if self.state is None:
            if self._looks_like_full_state(packet):
                self.state = packet
            return

        ptype = packet.get("type")
        if ptype == "tick":
            self.state["tick"] = packet.get("tick", self.state.get("tick", 0))
        elif ptype == "unit_state":
            data = packet.get("data", {})
            uid = data.get("unit_id")
            if uid and uid in self.state.get("unit_state", {}):
                self.state["unit_state"][uid].update(data)
        elif ptype == "entity_spawned":
            entity = packet.get("data", {})
            if entity:
                self.state.setdefault("entities", []).append(entity)
        elif ptype == "entity_expired":
            coords = packet.get("data")
            if isinstance(coords, list) and len(coords) == 2:
                x, y = coords
                self.state["entities"] = [
                    e
                    for e in self.state.get("entities", [])
                    if not (e.get("x") == x and e.get("y") == y)
                ]
        elif ptype == "entity_state":
            coords = packet.get("coordinates")
            updated = packet.get("updated_entity")
            if isinstance(coords, list) and len(coords) == 2 and updated:
                x, y = coords
                entities = self.state.get("entities", [])
                for i, e in enumerate(entities):
                    if e.get("x") == x and e.get("y") == y:
                        entities[i] = updated
                        break
        elif ptype == "unit":
            # A unit action echo. State will be reflected by follow-up
            # unit_state / entity_spawned events. Nothing to do here.
            pass

    def _looks_like_full_state(self, packet: dict[str, Any]) -> bool:
        return all(k in packet for k in ("agents", "unit_state", "entities", "world"))

    def snapshot(self) -> Optional[dict[str, Any]]:
        if self.state is None:
            return None
        return json.loads(json.dumps(self.state))


class Adapter:
    def __init__(
        self,
        connection_string: str,
        bot_endpoint: str,
        bot_timeout_ms: int,
        my_agent_id: str,
    ) -> None:
        self.connection_string = connection_string
        self.bot_endpoint = bot_endpoint
        self.bot_timeout_s = bot_timeout_ms / 1000.0
        self.my_agent_id = my_agent_id
        self.mirror = GameStateMirror()
        self.last_tick_actioned = -1
        self.log = logging.LoggerAdapter(
            logging.getLogger("adapter"), {"agent": my_agent_id}
        )

    async def run(self) -> None:
        import aiohttp
        import websockets

        self.log.info("connecting to %s", self.connection_string)
        async with websockets.connect(
            self.connection_string, max_size=None, ping_interval=20, ping_timeout=20
        ) as ws:
            self.log.info("connected as agent %s; bot=%s timeout=%.2fs",
                          self.my_agent_id, self.bot_endpoint, self.bot_timeout_s)
            async with aiohttp.ClientSession() as http:
                await asyncio.gather(
                    self._receive_loop(ws),
                    self._action_loop(ws, http),
                )

    async def _receive_loop(self, ws) -> None:
        async for raw in ws:
            try:
                packet = json.loads(raw)
            except json.JSONDecodeError:
                self.log.warning("dropping non-JSON packet: %r", raw[:80])
                continue
            self.mirror.apply(packet)

    async def _action_loop(self, ws, http) -> None:  # http: aiohttp.ClientSession
        # Wait until we have a full state.
        while self.mirror.state is None:
            await asyncio.sleep(0.05)

        tick_rate = float(self.mirror.state.get("config", {}).get("tick_rate_hz", 3))
        period = 1.0 / max(tick_rate, 0.1)
        self.log.info("action loop started at %.2f Hz (period=%.3fs)", tick_rate, period)

        while True:
            await asyncio.sleep(period)
            snap = self.mirror.snapshot()
            if snap is None:
                continue
            tick = snap.get("tick", 0)
            if tick == self.last_tick_actioned:
                continue
            self.last_tick_actioned = tick
            actions = await self._request_bot_actions(http, snap)
            for action in actions:
                await self._send_action(ws, action)

    async def _request_bot_actions(
        self, http, snap: dict[str, Any]  # http: aiohttp.ClientSession
    ) -> list[dict[str, Any]]:
        import aiohttp

        payload = {
            "tick": snap.get("tick", 0),
            "you": self.my_agent_id,
            "game_state": snap,
        }
        try:
            async with http.post(
                self.bot_endpoint,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.bot_timeout_s),
            ) as resp:
                if resp.status != 200:
                    self.log.warning("bot returned HTTP %d at tick %d", resp.status, payload["tick"])
                    return []
                body = await resp.json()
        except asyncio.TimeoutError:
            self.log.warning("bot timed out at tick %d", payload["tick"])
            return []
        except Exception as exc:  # noqa: BLE001
            self.log.warning("bot call failed at tick %d: %s", payload["tick"], exc)
            return []
        return self._normalize_actions(body, snap)

    def _normalize_actions(
        self, body: Any, snap: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Accept either {"actions": [...]} or a bare list, and translate our
        simplified wire format into Bomberland action packets."""
        if isinstance(body, dict) and "actions" in body:
            raw = body["actions"]
        elif isinstance(body, list):
            raw = body
        else:
            self.log.warning("unexpected bot response shape: %r", body)
            return []

        my_units = set(snap["agents"].get(self.my_agent_id, {}).get("unit_ids", []))
        out: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            unit_id = item.get("unit_id")
            action = item.get("action", "stay")
            if unit_id not in my_units:
                continue
            if action == "stay":
                continue
            if action in ("up", "down", "left", "right"):
                out.append({"type": "move", "move": action, "unit_id": unit_id})
            elif action == "bomb":
                out.append({"type": "bomb", "unit_id": unit_id})
            elif action == "detonate":
                coords = item.get("coordinates")
                if (
                    isinstance(coords, list)
                    and len(coords) == 2
                    and all(isinstance(c, int) for c in coords)
                ):
                    out.append(
                        {
                            "type": "detonate",
                            "coordinates": coords,
                            "unit_id": unit_id,
                        }
                    )
                else:
                    self.log.warning("detonate without valid coordinates for %s", unit_id)
            else:
                self.log.warning("ignoring unknown action %r for %s", action, unit_id)
        return out

    async def _send_action(self, ws, action: dict[str, Any]) -> None:
        try:
            await ws.send(json.dumps(action))
        except Exception as exc:  # noqa: BLE001
            self.log.warning("failed to send action %s: %s", action, exc)


async def main() -> int:
    connection_string = env("GAME_CONNECTION_STRING", required=True)
    bot_endpoint = env("BOT_ENDPOINT", required=True)
    bot_timeout_ms = int(env("BOT_TIMEOUT_MS", "300"))
    my_agent_id = env("MY_AGENT_ID", "a").lower()
    if my_agent_id not in ("a", "b"):
        raise SystemExit("MY_AGENT_ID must be 'a' or 'b'")

    adapter = Adapter(connection_string, bot_endpoint, bot_timeout_ms, my_agent_id)

    import websockets

    attempts = 0
    while True:
        try:
            await adapter.run()
            return 0
        except (OSError, websockets.exceptions.WebSocketException) as exc:
            attempts += 1
            wait = min(2 ** min(attempts, 5), 30)
            logging.getLogger("adapter").warning(
                "connection error (%s); retrying in %ds", exc, wait
            )
            await asyncio.sleep(wait)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
