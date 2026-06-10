"""Run queued matches, save replays, and update tournament rankings.

Edit this file when match execution or scheduling behavior changes.
Copy this file if another small background job loop is added.
"""

from __future__ import annotations

import asyncio
import logging
import random
from itertools import combinations
from typing import Any

from aiohttp import web

from backend.db import code_clash as dbcc
from backend.games.snake import run_snake_match
from backend.matches.elo import update_multiplayer_elo
from backend.matches.replays import compress_replay
from backend.runner import BotRunner


logger = logging.getLogger(__name__)


async def schedule_tournament_matches(db, tournament: dict[str, Any]) -> int:
    entries = await dbcc.list_tournament_entries(db, tournament["id"])
    if len(entries) < 2:
        raise ValueError("Tournament needs at least 2 bot versions.")
    if await dbcc.queued_match_count(db, tournament["id"]) > 0:
        return 0
    created = 0
    for left, right in combinations(entries, 2):
        for _ in range(tournament["games_per_pairing"]):
            await dbcc.create_match(db, tournament, random.randint(1, 2_147_483_647), [left["bot_version_id"], right["bot_version_id"]])
            created += 1
    await dbcc.update_tournament_status(db, tournament["id"], "running")
    return created


async def run_match(app: web.Application, match: dict[str, Any]) -> None:
    db = app["db"]
    runner: BotRunner = app["bot_runner"]
    hub = app["ws_hub"]
    await dbcc.mark_match_running(db, match["id"])
    await hub.broadcast({"type": "match.started", "match_id": match["id"], "tournament_id": match["tournament_id"]})
    logger.info("Running match %s", match["id"])
    try:
        bots = await dbcc.list_match_bots(db, match["id"])
        game_bots = [{"bot_version_id": bot["bot_version_id"], "bot_name": bot["bot_name"]} for bot in bots]

        async def move_fn(bot_ref: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
            bot = next(row for row in bots if row["bot_version_id"] == bot_ref["bot_version_id"])
            result = await runner.run_turn(bot, state, match["turn_timeout_ms"], match["memory_limit_mb"])
            await hub.broadcast({"type": "match.turn", "match_id": match["id"], "turn": state["turn"], "bot_version_id": bot["bot_version_id"], "move": result.get("move", "")})
            return result

        outcome = await run_snake_match(game_bots, match["seed"], match["max_turns"], move_fn)
        result = {"tournament_id": match["tournament_id"], "bots": outcome["bots"]}
        await dbcc.finish_match(db, match["id"], compress_replay(outcome["replay"]), result)

        old_ratings = {bot["bot_version_id"]: float((await dbcc.get_bot_version(db, bot["bot_version_id"]))["elo"]) for bot in bots}
        points = {bot["bot_version_id"]: next(item["points"] for item in outcome["bots"] if item["bot_version_id"] == bot["bot_version_id"]) for bot in bots}
        await dbcc.update_elos(db, update_multiplayer_elo(old_ratings, points))

        await hub.broadcast({"type": "match.finished", "match_id": match["id"], "tournament_id": match["tournament_id"], "result": result})
        await hub.broadcast({"type": "leaderboard.updated"})
        if match["tournament_id"] is not None and await dbcc.unfinished_match_count(db, match["tournament_id"]) == 0:
            await dbcc.update_tournament_status(db, match["tournament_id"], "finished")
            await hub.broadcast({"type": "tournament.updated", "tournament_id": match["tournament_id"]})
        logger.info("Finished match %s", match["id"])
    except Exception as exc:
        logger.exception("Match %s failed", match["id"])
        await dbcc.fail_match(db, match["id"], str(exc))
        await hub.broadcast({"type": "match.finished", "match_id": match["id"], "tournament_id": match["tournament_id"], "error": str(exc)})


async def scheduler_loop(app: web.Application) -> None:
    while True:
        try:
            match = await dbcc.next_queued_match(app["db"])
            if match is None:
                await asyncio.sleep(1.0)
                continue
            await run_match(app, match)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduler loop error")
            await asyncio.sleep(2.0)
