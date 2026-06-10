"""Test Code Clash bots, Snake, replays, Elo, and tournament scheduling.

Edit this file when Code Clash API behavior or core match rules change.
Copy a test pattern here when adding another game or tournament rule.
"""

from __future__ import annotations

import pytest

from backend.db import code_clash as dbcc
from backend.games.snake import run_snake_match
from backend.matches.elo import update_multiplayer_elo
from backend.matches.executor import schedule_tournament_matches
from backend.matches.replays import compress_replay, decompress_replay
from backend.tests.conftest import login


@pytest.mark.asyncio
async def test_bot_create_and_python_version(client, create_user, auth_headers) -> None:
    await create_user("user", "secret")
    await login(client, "user", "secret", auth_headers)

    bot_response = await client.post("/api/bots/create", json={"name": "Starter"}, headers=auth_headers)
    assert bot_response.status == 201
    bot_id = (await bot_response.json())["data"]["bot"]["id"]

    version_response = await client.post(
        "/api/bots/upload-version",
        json={"bot_id": bot_id, "language": "python", "filename": "bot.py", "source": "print('RIGHT')"},
        headers=auth_headers,
    )
    assert version_response.status == 201
    version = (await version_response.json())["data"]["version"]
    assert version["build_status"] == "ready"

    list_response = await client.post("/api/bots/list", json={})
    bots = (await list_response.json())["data"]["bots"]
    assert bots[0]["versions"][0]["id"] == version["id"]


@pytest.mark.asyncio
async def test_cpp_version_uses_runner_compile(client, create_user, auth_headers) -> None:
    await create_user("user", "secret")
    await login(client, "user", "secret", auth_headers)
    bot_id = (await (await client.post("/api/bots/create", json={"name": "Cpp"}, headers=auth_headers)).json())["data"]["bot"]["id"]

    response = await client.post(
        "/api/bots/upload-version",
        json={"bot_id": bot_id, "language": "cpp", "filename": "bot.cpp", "source": "#include <iostream>\nint main(){std::cout<<\"RIGHT\\n\";}"},
        headers=auth_headers,
    )
    assert response.status == 201
    assert (await response.json())["data"]["version"]["build_status"] == "ready"


@pytest.mark.asyncio
async def test_normal_user_can_create_tournament(client, create_user, auth_headers) -> None:
    await create_user("student", "secret")
    await login(client, "student", "secret", auth_headers)

    response = await client.post(
        "/api/tournaments/create",
        json={"name": "Student Cup", "turn_timeout_ms": 100, "memory_limit_mb": 128, "max_turns": 500, "games_per_pairing": 3},
        headers=auth_headers,
    )

    assert response.status == 201
    payload = await response.json()
    assert payload["data"]["tournament"]["name"] == "Student Cup"


@pytest.mark.asyncio
async def test_snake_replay_and_tie_points() -> None:
    bots = [{"bot_version_id": 1, "bot_name": "A"}, {"bot_version_id": 2, "bot_name": "B"}]

    async def move_fn(bot, state):
        return {"move": "UP", "raw": "UP", "error": ""}

    outcome = await run_snake_match(bots, seed=123, max_turns=5, move_fn=move_fn, width=7, height=7)
    assert outcome["replay"]["seed"] == 123
    assert outcome["replay"]["turns"]
    assert {bot["points"] for bot in outcome["bots"]} <= {0.0, 0.5, 1.0}


def test_replay_compression_round_trips() -> None:
    replay = {"game": "snake", "turns": [{"turn": 1, "actions": {"1": {"move": "RIGHT"}}}]}
    assert decompress_replay(compress_replay(replay)) == replay


def test_elo_updates_winner_up_and_loser_down() -> None:
    ratings = update_multiplayer_elo({1: 1000.0, 2: 1000.0}, {1: 1.0, 2: 0.0})
    assert ratings[1] > 1000
    assert ratings[2] < 1000


@pytest.mark.asyncio
async def test_tournament_schedules_round_robin_matches(client, db, create_user) -> None:
    await create_user("admin", "secret", True)
    first_bot = await dbcc.create_bot(db, 1, "One")
    second_bot = await dbcc.create_bot(db, 1, "Two")
    first_version = await dbcc.create_bot_version(db, first_bot["id"], "python", "one.py", "print('RIGHT')", "ready", "ok", None)
    second_version = await dbcc.create_bot_version(db, second_bot["id"], "python", "two.py", "print('RIGHT')", "ready", "ok", None)
    tournament = await dbcc.create_tournament(
        db,
        1,
        {"name": "T", "turn_timeout_ms": 100, "memory_limit_mb": 128, "max_turns": 50, "games_per_pairing": 3},
    )
    await dbcc.add_tournament_entry(db, tournament["id"], first_version["id"])
    await dbcc.add_tournament_entry(db, tournament["id"], second_version["id"])

    created = await schedule_tournament_matches(db, tournament)
    assert created == 3
    assert await dbcc.queued_match_count(db, tournament["id"]) == 3
