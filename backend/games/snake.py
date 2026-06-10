"""Run deterministic Multiplayer Snake matches and produce replay logs.

Edit this file when Snake rules or replay data changes.
Copy this file as a starting point when adding another game engine.
"""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from typing import Any


MoveFn = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]

DIRECTIONS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}


def _starting_snakes(width: int, height: int, bot_count: int) -> list[list[tuple[int, int]]]:
    starts = [
        [(2, 2), (1, 2), (0, 2)],
        [(width - 3, height - 3), (width - 2, height - 3), (width - 1, height - 3)],
        [(width - 3, 2), (width - 2, 2), (width - 1, 2)],
        [(2, height - 3), (1, height - 3), (0, height - 3)],
        [(width // 2, 2), (width // 2, 1), (width // 2, 0)],
        [(width // 2, height - 3), (width // 2, height - 2), (width // 2, height - 1)],
        [(2, height // 2), (1, height // 2), (0, height // 2)],
        [(width - 3, height // 2), (width - 2, height // 2), (width - 1, height // 2)],
    ]
    return starts[:bot_count]


def _spawn_food(rng: random.Random, width: int, height: int, snakes: list[dict[str, Any]]) -> tuple[int, int] | None:
    occupied = {tuple(cell) for snake in snakes if snake["alive"] for cell in snake["body"]}
    open_cells = [(x, y) for y in range(height) for x in range(width) if (x, y) not in occupied]
    if not open_cells:
        return None
    return rng.choice(open_cells)


def _state_for_bot(width: int, height: int, turn: int, food: tuple[int, int] | None, snakes: list[dict[str, Any]], bot_id: int) -> dict[str, Any]:
    return {
        "game": "snake",
        "turn": turn,
        "you": bot_id,
        "width": width,
        "height": height,
        "food": list(food) if food is not None else None,
        "snakes": [
            {
                "id": snake["id"],
                "name": snake["name"],
                "alive": snake["alive"],
                "body": [list(cell) for cell in snake["body"]],
            }
            for snake in snakes
        ],
    }


async def run_snake_match(
    bots: list[dict[str, Any]],
    seed: int,
    max_turns: int,
    move_fn: MoveFn,
    width: int = 15,
    height: int = 15,
) -> dict[str, Any]:
    if len(bots) < 2 or len(bots) > 8:
        raise ValueError("Snake supports 2-8 bots.")

    rng = random.Random(seed)
    snakes = []
    for bot, body in zip(bots, _starting_snakes(width, height, len(bots)), strict=True):
        snakes.append({"id": bot["bot_version_id"], "name": bot["bot_name"], "alive": True, "body": body, "direction": "RIGHT"})
    food = _spawn_food(rng, width, height, snakes)
    replay: dict[str, Any] = {"game": "snake", "seed": seed, "width": width, "height": height, "bots": bots, "turns": []}

    for turn in range(max_turns):
        alive = [snake for snake in snakes if snake["alive"]]
        if len(alive) <= 1:
            break

        actions: dict[int, dict[str, Any]] = {}
        for snake in alive:
            state = _state_for_bot(width, height, turn, food, snakes, snake["id"])
            result = await move_fn(next(bot for bot in bots if bot["bot_version_id"] == snake["id"]), state)
            move = str(result.get("move", "")).upper()
            if move not in DIRECTIONS:
                move = snake["direction"]
            actions[snake["id"]] = {"move": move, "raw": result.get("raw", ""), "error": result.get("error", "")}

        next_heads: dict[int, tuple[int, int]] = {}
        next_bodies: dict[int, list[tuple[int, int]]] = {}
        ate_food: set[int] = set()
        for snake in alive:
            move = actions[snake["id"]]["move"]
            dx, dy = DIRECTIONS[move]
            head_x, head_y = snake["body"][0]
            new_head = (head_x + dx, head_y + dy)
            body = [new_head, *snake["body"]]
            if food is not None and new_head == food:
                ate_food.add(snake["id"])
            else:
                body.pop()
            next_heads[snake["id"]] = new_head
            next_bodies[snake["id"]] = body

        dead_ids: set[int] = set()
        head_counts: dict[tuple[int, int], int] = {}
        for head in next_heads.values():
            head_counts[head] = head_counts.get(head, 0) + 1
        body_cells = {
            cell
            for bot_id, body in next_bodies.items()
            for cell in body[1:]
            if bot_id not in dead_ids
        }
        for snake in alive:
            head = next_heads[snake["id"]]
            if head[0] < 0 or head[0] >= width or head[1] < 0 or head[1] >= height:
                dead_ids.add(snake["id"])
            elif head_counts[head] > 1:
                dead_ids.add(snake["id"])
            elif head in body_cells:
                dead_ids.add(snake["id"])

        for snake in snakes:
            if not snake["alive"]:
                continue
            if snake["id"] in dead_ids:
                snake["alive"] = False
            else:
                snake["body"] = next_bodies[snake["id"]]
                snake["direction"] = actions[snake["id"]]["move"]
        if ate_food:
            food = _spawn_food(rng, width, height, snakes)

        replay["turns"].append(
            {
                "turn": turn,
                "food": list(food) if food is not None else None,
                "actions": {str(bot_id): action for bot_id, action in actions.items()},
                "dead": sorted(dead_ids),
                "snakes": [
                    {"id": snake["id"], "alive": snake["alive"], "body": [list(cell) for cell in snake["body"]]}
                    for snake in snakes
                ],
            }
        )

    alive_ids = [snake["id"] for snake in snakes if snake["alive"]]
    if len(alive_ids) == 1:
        points = {snake["id"]: (1.0 if snake["id"] == alive_ids[0] else 0.0) for snake in snakes}
    elif len(alive_ids) > 1:
        points = {snake["id"]: (0.5 if snake["id"] in alive_ids else 0.0) for snake in snakes}
    else:
        final_dead = set(replay["turns"][-1]["dead"]) if replay["turns"] else {snake["id"] for snake in snakes}
        points = {snake["id"]: (0.5 if snake["id"] in final_dead else 0.0) for snake in snakes}

    result_bots = []
    for snake in snakes:
        point_value = points[snake["id"]]
        rank = 1 if point_value > 0 else 2
        result_bots.append({"bot_version_id": snake["id"], "points": point_value, "rank": rank, "alive": snake["alive"]})
    replay["result"] = {"bots": result_bots}
    return {"replay": replay, "bots": result_bots}
