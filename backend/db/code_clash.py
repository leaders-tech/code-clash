"""Store and load Code Clash bots, tournaments, matches, and rankings.

Edit this file when Code Clash tables or queries change.
Copy this file as a starting point when adding another small feature table group.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite

from backend.db.connection import utc_now_text


def _dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


async def create_bot(db: aiosqlite.Connection, owner_id: int, name: str) -> dict[str, Any]:
    now = utc_now_text()
    cursor = await db.execute(
        """
        INSERT INTO bots (owner_id, name, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        RETURNING id, owner_id, name, active_version_id, created_at, updated_at
        """,
        (owner_id, name, now, now),
    )
    bot = dict(await cursor.fetchone())
    await cursor.close()
    await db.commit()
    return bot


async def list_bots_for_user(db: aiosqlite.Connection, user_id: int, is_admin: bool = False) -> list[dict[str, Any]]:
    if is_admin:
        cursor = await db.execute(
            """
            SELECT b.*, u.username AS owner_username
            FROM bots b
            JOIN users u ON u.id = b.owner_id
            ORDER BY b.updated_at DESC, b.id DESC
            """
        )
    else:
        cursor = await db.execute(
            """
            SELECT b.*, u.username AS owner_username
            FROM bots b
            JOIN users u ON u.id = b.owner_id
            WHERE b.owner_id = ?
            ORDER BY b.updated_at DESC, b.id DESC
            """,
            (user_id,),
        )
    return [dict(row) for row in await cursor.fetchall()]


async def get_bot_for_user(db: aiosqlite.Connection, bot_id: int, user_id: int, is_admin: bool = False) -> dict[str, Any] | None:
    cursor = await db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
    bot = await cursor.fetchone()
    if bot is None:
        return None
    if not is_admin and bot["owner_id"] != user_id:
        return None
    return dict(bot)


async def create_bot_version(
    db: aiosqlite.Connection,
    bot_id: int,
    language: str,
    filename: str,
    source: str,
    build_status: str,
    build_log: str,
    artifact: bytes | None,
) -> dict[str, Any]:
    now = utc_now_text()
    cursor = await db.execute("SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version FROM bot_versions WHERE bot_id = ?", (bot_id,))
    version_number = (await cursor.fetchone())["next_version"]
    cursor = await db.execute(
        """
        INSERT INTO bot_versions (bot_id, version_number, language, filename, source, build_status, build_log, artifact, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id, bot_id, version_number, language, filename, build_status, build_log, elo, created_at
        """,
        (bot_id, version_number, language, filename, source, build_status, build_log, artifact, now),
    )
    version = dict(await cursor.fetchone())
    await cursor.close()
    if build_status == "ready":
        await db.execute("UPDATE bots SET active_version_id = ?, updated_at = ? WHERE id = ? AND active_version_id IS NULL", (version["id"], now, bot_id))
    await db.commit()
    return version


async def list_bot_versions(db: aiosqlite.Connection, bot_id: int) -> list[dict[str, Any]]:
    cursor = await db.execute(
        """
        SELECT id, bot_id, version_number, language, filename, build_status, build_log, elo, created_at
        FROM bot_versions
        WHERE bot_id = ?
        ORDER BY version_number DESC
        """,
        (bot_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def get_bot_version(db: aiosqlite.Connection, version_id: int) -> dict[str, Any] | None:
    cursor = await db.execute(
        """
        SELECT bv.*, b.name AS bot_name, b.owner_id
        FROM bot_versions bv
        JOIN bots b ON b.id = bv.bot_id
        WHERE bv.id = ?
        """,
        (version_id,),
    )
    return _dict(await cursor.fetchone())


async def set_active_version(db: aiosqlite.Connection, bot_id: int, version_id: int) -> None:
    now = utc_now_text()
    await db.execute("UPDATE bots SET active_version_id = ?, updated_at = ? WHERE id = ?", (version_id, now, bot_id))
    await db.commit()


async def create_tournament(db: aiosqlite.Connection, created_by: int, settings: dict[str, Any]) -> dict[str, Any]:
    now = utc_now_text()
    cursor = await db.execute(
        """
        INSERT INTO tournaments (name, game_key, status, turn_timeout_ms, memory_limit_mb, max_turns, games_per_pairing, created_by, created_at, updated_at)
        VALUES (?, 'snake', 'draft', ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
        """,
        (
            settings["name"],
            settings["turn_timeout_ms"],
            settings["memory_limit_mb"],
            settings["max_turns"],
            settings["games_per_pairing"],
            created_by,
            now,
            now,
        ),
    )
    tournament = dict(await cursor.fetchone())
    await cursor.close()
    await db.commit()
    return tournament


async def list_tournaments(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    cursor = await db.execute("SELECT * FROM tournaments ORDER BY created_at DESC, id DESC")
    return [dict(row) for row in await cursor.fetchall()]


async def get_tournament(db: aiosqlite.Connection, tournament_id: int) -> dict[str, Any] | None:
    cursor = await db.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
    return _dict(await cursor.fetchone())


async def add_tournament_entry(db: aiosqlite.Connection, tournament_id: int, bot_version_id: int) -> dict[str, Any]:
    cursor = await db.execute(
        """
        INSERT INTO tournament_entries (tournament_id, bot_version_id)
        VALUES (?, ?)
        ON CONFLICT(tournament_id, bot_version_id) DO UPDATE SET bot_version_id = excluded.bot_version_id
        RETURNING *
        """,
        (tournament_id, bot_version_id),
    )
    entry = dict(await cursor.fetchone())
    await cursor.close()
    await db.commit()
    return entry


async def list_tournament_entries(db: aiosqlite.Connection, tournament_id: int) -> list[dict[str, Any]]:
    cursor = await db.execute(
        """
        SELECT te.*, bv.version_number, bv.elo, b.name AS bot_name, u.username AS owner_username
        FROM tournament_entries te
        JOIN bot_versions bv ON bv.id = te.bot_version_id
        JOIN bots b ON b.id = bv.bot_id
        JOIN users u ON u.id = b.owner_id
        WHERE te.tournament_id = ?
        ORDER BY te.points DESC, te.wins DESC, bv.elo DESC, te.id
        """,
        (tournament_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def update_tournament_status(db: aiosqlite.Connection, tournament_id: int, status: str) -> None:
    await db.execute("UPDATE tournaments SET status = ?, updated_at = ? WHERE id = ?", (status, utc_now_text(), tournament_id))
    await db.commit()


async def create_match(db: aiosqlite.Connection, tournament: dict[str, Any], seed: int, bot_version_ids: list[int]) -> dict[str, Any]:
    now = utc_now_text()
    cursor = await db.execute(
        """
        INSERT INTO matches (tournament_id, game_key, status, seed, turn_timeout_ms, memory_limit_mb, max_turns, created_at)
        VALUES (?, ?, 'queued', ?, ?, ?, ?, ?)
        RETURNING *
        """,
        (
            tournament["id"],
            tournament["game_key"],
            seed,
            tournament["turn_timeout_ms"],
            tournament["memory_limit_mb"],
            tournament["max_turns"],
            now,
        ),
    )
    match = dict(await cursor.fetchone())
    await cursor.close()
    for slot, version_id in enumerate(bot_version_ids):
        await db.execute("INSERT INTO match_bots (match_id, bot_version_id, slot) VALUES (?, ?, ?)", (match["id"], version_id, slot))
    await db.commit()
    return match


async def queued_match_count(db: aiosqlite.Connection, tournament_id: int) -> int:
    cursor = await db.execute("SELECT COUNT(*) AS total FROM matches WHERE tournament_id = ?", (tournament_id,))
    return int((await cursor.fetchone())["total"])


async def unfinished_match_count(db: aiosqlite.Connection, tournament_id: int) -> int:
    cursor = await db.execute(
        "SELECT COUNT(*) AS total FROM matches WHERE tournament_id = ? AND status IN ('queued', 'running')",
        (tournament_id,),
    )
    return int((await cursor.fetchone())["total"])


async def next_queued_match(db: aiosqlite.Connection) -> dict[str, Any] | None:
    cursor = await db.execute("SELECT * FROM matches WHERE status = 'queued' ORDER BY id LIMIT 1")
    return _dict(await cursor.fetchone())


async def get_match(db: aiosqlite.Connection, match_id: int) -> dict[str, Any] | None:
    cursor = await db.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
    return _dict(await cursor.fetchone())


async def list_matches(db: aiosqlite.Connection, tournament_id: int | None = None) -> list[dict[str, Any]]:
    if tournament_id is None:
        cursor = await db.execute(
            """
            SELECT id, tournament_id, game_key, status, seed, turn_timeout_ms, memory_limit_mb, max_turns, result_json, error, created_at, started_at, finished_at
            FROM matches
            ORDER BY id DESC
            LIMIT 50
            """
        )
    else:
        cursor = await db.execute(
            """
            SELECT id, tournament_id, game_key, status, seed, turn_timeout_ms, memory_limit_mb, max_turns, result_json, error, created_at, started_at, finished_at
            FROM matches
            WHERE tournament_id = ?
            ORDER BY id DESC
            """,
            (tournament_id,),
        )
    return [dict(row) for row in await cursor.fetchall()]


async def list_match_bots(db: aiosqlite.Connection, match_id: int) -> list[dict[str, Any]]:
    cursor = await db.execute(
        """
        SELECT mb.*, bv.version_number, bv.language, bv.filename, bv.source, bv.artifact, b.name AS bot_name
        FROM match_bots mb
        JOIN bot_versions bv ON bv.id = mb.bot_version_id
        JOIN bots b ON b.id = bv.bot_id
        WHERE mb.match_id = ?
        ORDER BY mb.slot
        """,
        (match_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def mark_match_running(db: aiosqlite.Connection, match_id: int) -> None:
    await db.execute("UPDATE matches SET status = 'running', started_at = ? WHERE id = ?", (utc_now_text(), match_id))
    await db.commit()


async def finish_match(db: aiosqlite.Connection, match_id: int, replay_blob: bytes, result: dict[str, Any]) -> None:
    now = utc_now_text()
    await db.execute(
        "UPDATE matches SET status = 'finished', replay = ?, result_json = ?, finished_at = ? WHERE id = ?",
        (replay_blob, json.dumps(result, sort_keys=True), now, match_id),
    )
    for bot_result in result["bots"]:
        await db.execute(
            "UPDATE match_bots SET points = ?, final_rank = ? WHERE match_id = ? AND bot_version_id = ?",
            (bot_result["points"], bot_result["rank"], match_id, bot_result["bot_version_id"]),
        )
        if result.get("tournament_id") is not None:
            await db.execute(
                """
                UPDATE tournament_entries
                SET points = points + ?,
                    wins = wins + ?,
                    losses = losses + ?,
                    draws = draws + ?
                WHERE tournament_id = ? AND bot_version_id = ?
                """,
                (
                    bot_result["points"],
                    1 if bot_result["points"] == 1 else 0,
                    1 if bot_result["points"] == 0 else 0,
                    1 if bot_result["points"] == 0.5 else 0,
                    result["tournament_id"],
                    bot_result["bot_version_id"],
                ),
            )
    await db.commit()


async def fail_match(db: aiosqlite.Connection, match_id: int, error: str) -> None:
    await db.execute("UPDATE matches SET status = 'failed', error = ?, finished_at = ? WHERE id = ?", (error, utc_now_text(), match_id))
    await db.commit()


async def update_elos(db: aiosqlite.Connection, ratings: dict[int, float]) -> None:
    for version_id, elo in ratings.items():
        await db.execute("UPDATE bot_versions SET elo = ? WHERE id = ?", (elo, version_id))
    await db.commit()


async def global_leaderboard(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    cursor = await db.execute(
        """
        SELECT bv.id AS version_id, bv.version_number, bv.language, bv.elo, b.name AS bot_name, u.username AS owner_username
        FROM bot_versions bv
        JOIN bots b ON b.id = bv.bot_id
        JOIN users u ON u.id = b.owner_id
        WHERE bv.build_status = 'ready'
        ORDER BY bv.elo DESC, bv.id
        LIMIT 100
        """
    )
    return [dict(row) for row in await cursor.fetchall()]
