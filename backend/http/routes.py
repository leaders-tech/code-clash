"""Handle Code Clash JSON endpoints outside auth and websocket routes.

Edit this file when bot, tournament, match, replay, or leaderboard APIs change.
Copy the route pattern here when adding another small endpoint group.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import web

from backend.auth.access import require_admin, require_user
from backend.db import code_clash as dbcc
from backend.db.users import list_users
from backend.http.json_api import AppError, ok, read_json
from backend.http.middleware import require_allowed_origin
from backend.matches.executor import schedule_tournament_matches
from backend.matches.replays import decompress_replay


logger = logging.getLogger(__name__)


def _int(payload: dict[str, Any], key: str, default: int | None = None) -> int:
    value = payload.get(key, default)
    if not isinstance(value, int):
        raise AppError(400, "bad_request", f"{key} must be an integer.")
    return value


async def health(request: web.Request) -> web.Response:
    return ok({"status": "ok"})


async def admin_users_list(request: web.Request) -> web.Response:
    require_admin(request)
    users = await list_users(request.app["db"])
    return ok({"users": users})


async def bots_list(request: web.Request) -> web.Response:
    user = require_user(request)
    bots = await dbcc.list_bots_for_user(request.app["db"], user["id"], bool(user["is_admin"]))
    for bot in bots:
        bot["versions"] = await dbcc.list_bot_versions(request.app["db"], bot["id"])
    return ok({"bots": bots})


async def bots_create(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    user = require_user(request)
    payload = await read_json(request)
    name = str(payload.get("name", "")).strip()
    if len(name) < 2 or len(name) > 60:
        raise AppError(400, "bad_request", "Bot name must be 2-60 characters.")
    bot = await dbcc.create_bot(request.app["db"], user["id"], name)
    logger.info("User %s created bot %s", user["id"], bot["id"])
    return ok({"bot": bot}, status=201)


async def bots_upload_version(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    user = require_user(request)
    payload = await read_json(request)
    bot_id = _int(payload, "bot_id")
    language = str(payload.get("language", "")).strip()
    filename = str(payload.get("filename", "")).strip()
    source = str(payload.get("source", ""))
    if language not in {"python", "cpp"}:
        raise AppError(400, "bad_request", "Language must be python or cpp.")
    if not filename or len(filename) > 120:
        raise AppError(400, "bad_request", "Filename is required.")
    if not source.strip() or len(source.encode("utf-8")) > 200_000:
        raise AppError(400, "bad_request", "Source is required and must be under 200 KB.")
    bot = await dbcc.get_bot_for_user(request.app["db"], bot_id, user["id"], bool(user["is_admin"]))
    if bot is None:
        raise AppError(404, "not_found", "Bot does not exist.")

    build_status = "ready"
    build_log = "Python bot saved." if language == "python" else ""
    artifact = None
    if language == "cpp":
        build_log, artifact = await request.app["bot_runner"].compile_cpp(filename, source, 128)
        build_status = "ready" if artifact is not None else "failed"
    version = await dbcc.create_bot_version(request.app["db"], bot_id, language, filename, source, build_status, build_log, artifact)
    logger.info("User %s uploaded bot version %s status=%s", user["id"], version["id"], build_status)
    return ok({"version": version}, status=201)


async def bots_set_active_version(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    user = require_user(request)
    payload = await read_json(request)
    bot_id = _int(payload, "bot_id")
    version_id = _int(payload, "version_id")
    bot = await dbcc.get_bot_for_user(request.app["db"], bot_id, user["id"], bool(user["is_admin"]))
    version = await dbcc.get_bot_version(request.app["db"], version_id)
    if bot is None or version is None or version["bot_id"] != bot_id:
        raise AppError(404, "not_found", "Bot version does not exist.")
    if version["build_status"] != "ready":
        raise AppError(400, "bad_request", "Only ready versions can be active.")
    await dbcc.set_active_version(request.app["db"], bot_id, version_id)
    return ok({"active_version_id": version_id})


async def tournaments_list(request: web.Request) -> web.Response:
    require_user(request)
    tournaments = await dbcc.list_tournaments(request.app["db"])
    return ok({"tournaments": tournaments})


async def tournaments_create(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    user = require_user(request)
    payload = await read_json(request)
    settings = {
        "name": str(payload.get("name", "Snake Tournament")).strip() or "Snake Tournament",
        "turn_timeout_ms": _int(payload, "turn_timeout_ms", 100),
        "memory_limit_mb": _int(payload, "memory_limit_mb", 128),
        "max_turns": _int(payload, "max_turns", 500),
        "games_per_pairing": _int(payload, "games_per_pairing", 3),
    }
    if not (50 <= settings["turn_timeout_ms"] <= 5000):
        raise AppError(400, "bad_request", "Turn timeout must be 50-5000 ms.")
    if not (32 <= settings["memory_limit_mb"] <= 1024):
        raise AppError(400, "bad_request", "Memory limit must be 32-1024 MB.")
    if not (10 <= settings["max_turns"] <= 5000):
        raise AppError(400, "bad_request", "Max turns must be 10-5000.")
    if not (1 <= settings["games_per_pairing"] <= 50):
        raise AppError(400, "bad_request", "Games per pairing must be 1-50.")
    tournament = await dbcc.create_tournament(request.app["db"], user["id"], settings)
    return ok({"tournament": tournament}, status=201)


async def tournaments_enter(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    user = require_user(request)
    payload = await read_json(request)
    tournament_id = _int(payload, "tournament_id")
    version_id = _int(payload, "bot_version_id")
    tournament = await dbcc.get_tournament(request.app["db"], tournament_id)
    version = await dbcc.get_bot_version(request.app["db"], version_id)
    if tournament is None or version is None:
        raise AppError(404, "not_found", "Tournament or bot version does not exist.")
    if tournament["status"] != "draft":
        raise AppError(400, "bad_request", "Only draft tournaments accept entries.")
    if not user["is_admin"] and version["owner_id"] != user["id"]:
        raise AppError(403, "forbidden", "You can only enter your own bot versions.")
    if version["build_status"] != "ready":
        raise AppError(400, "bad_request", "Only ready bot versions can enter.")
    entry = await dbcc.add_tournament_entry(request.app["db"], tournament_id, version_id)
    await request.app["ws_hub"].broadcast({"type": "tournament.updated", "tournament_id": tournament_id})
    return ok({"entry": entry})


async def tournaments_start(request: web.Request) -> web.Response:
    require_allowed_origin(request)
    require_admin(request)
    payload = await read_json(request)
    tournament_id = _int(payload, "tournament_id")
    tournament = await dbcc.get_tournament(request.app["db"], tournament_id)
    if tournament is None:
        raise AppError(404, "not_found", "Tournament does not exist.")
    if tournament["status"] != "draft":
        raise AppError(400, "bad_request", "Only draft tournaments can start.")
    try:
        created = await schedule_tournament_matches(request.app["db"], tournament)
    except ValueError as exc:
        raise AppError(400, "bad_request", str(exc)) from exc
    await request.app["ws_hub"].broadcast({"type": "tournament.updated", "tournament_id": tournament_id})
    return ok({"created_matches": created})


async def tournaments_detail(request: web.Request) -> web.Response:
    require_user(request)
    payload = await read_json(request)
    tournament_id = _int(payload, "tournament_id")
    tournament = await dbcc.get_tournament(request.app["db"], tournament_id)
    if tournament is None:
        raise AppError(404, "not_found", "Tournament does not exist.")
    entries = await dbcc.list_tournament_entries(request.app["db"], tournament_id)
    matches = await dbcc.list_matches(request.app["db"], tournament_id)
    return ok({"tournament": tournament, "entries": entries, "matches": matches})


async def matches_list(request: web.Request) -> web.Response:
    require_user(request)
    payload = await read_json(request)
    tournament_id = payload.get("tournament_id")
    if tournament_id is not None and not isinstance(tournament_id, int):
        raise AppError(400, "bad_request", "tournament_id must be an integer.")
    matches = await dbcc.list_matches(request.app["db"], tournament_id)
    return ok({"matches": matches})


async def matches_detail(request: web.Request) -> web.Response:
    require_user(request)
    payload = await read_json(request)
    match_id = _int(payload, "match_id")
    match = await dbcc.get_match(request.app["db"], match_id)
    if match is None:
        raise AppError(404, "not_found", "Match does not exist.")
    match.pop("replay", None)
    bots = await dbcc.list_match_bots(request.app["db"], match_id)
    for bot in bots:
        bot.pop("source", None)
        bot.pop("artifact", None)
    match["result"] = json.loads(match.pop("result_json") or "{}")
    return ok({"match": match, "bots": bots})


async def replays_get(request: web.Request) -> web.Response:
    require_user(request)
    payload = await read_json(request)
    match_id = _int(payload, "match_id")
    match = await dbcc.get_match(request.app["db"], match_id)
    if match is None:
        raise AppError(404, "not_found", "Match does not exist.")
    replay = decompress_replay(match["replay"])
    if replay is None:
        raise AppError(404, "not_found", "Replay is not ready.")
    return ok({"replay": replay})


async def leaderboard_global(request: web.Request) -> web.Response:
    require_user(request)
    return ok({"leaderboard": await dbcc.global_leaderboard(request.app["db"])})


def setup_api_routes(app: web.Application) -> None:
    app.router.add_get("/api/health", health)
    app.router.add_post("/api/admin/users/list", admin_users_list)
    app.router.add_post("/api/bots/list", bots_list)
    app.router.add_post("/api/bots/create", bots_create)
    app.router.add_post("/api/bots/upload-version", bots_upload_version)
    app.router.add_post("/api/bots/set-active-version", bots_set_active_version)
    app.router.add_post("/api/tournaments/list", tournaments_list)
    app.router.add_post("/api/tournaments/create", tournaments_create)
    app.router.add_post("/api/tournaments/enter", tournaments_enter)
    app.router.add_post("/api/tournaments/start", tournaments_start)
    app.router.add_post("/api/tournaments/detail", tournaments_detail)
    app.router.add_post("/api/matches/list", matches_list)
    app.router.add_post("/api/matches/detail", matches_detail)
    app.router.add_post("/api/replays/get", replays_get)
    app.router.add_post("/api/leaderboard/global", leaderboard_global)
