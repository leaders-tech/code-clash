# Code Clash

Code Clash is a small bot programming platform for students. Users create bots, upload Python or C++ source versions, enter Snake tournaments, and watch ranked bot-vs-bot matches.

## Project Structure

- `backend/`: aiohttp backend, auth, APIs, game logic, scheduler, Docker runner, and SQLite helpers.
- `backend/games/`: modular game engines. Snake is implemented in `snake.py`.
- `backend/matches/`: match execution, replay compression, and Elo ranking helpers.
- `backend/db/`: explicit SQLite query modules.
- `frontend/`: React/Vite frontend pages for dashboard, bots, tournaments, and replays.
- `runner/`: Docker image used as the long-lived bot sandbox.
- `examples/`: starter Python and C++ Snake bots.
- `docs/`: deployment notes, including the tlfpaas Docker contract.

## Bot Interface

Each turn, Code Clash sends one JSON game-state object to the bot on `stdin`. The bot prints exactly one action to `stdout`.

Snake actions are:

```text
UP
DOWN
LEFT
RIGHT
```

Python example:

```bash
python examples/python_snake_bot.py < state.json
```

C++ source is compiled inside the sandbox runner when a version is uploaded.

## API Endpoints

All browser APIs use POST under `/api/...`.

- Auth: `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/me`
- Bots: `/api/bots/list`, `/api/bots/create`, `/api/bots/upload-version`, `/api/bots/set-active-version`
- Tournaments: `/api/tournaments/list`, `/api/tournaments/create`, `/api/tournaments/enter`, `/api/tournaments/start`, `/api/tournaments/detail`
- Matches: `/api/matches/list`, `/api/matches/detail`
- Replays: `/api/replays/get`
- Leaderboard: `/api/leaderboard/global`
- Admin: `/api/admin/users/list`

Live updates use WebSocket `/ws` with events such as `match.started`, `match.turn`, `match.finished`, `tournament.updated`, and `leaderboard.updated`.

## Local Run

Install dependencies and create local env files:

```bash
make setup
```

Start backend and frontend in two terminals:

```bash
make back
make front
```

Open the app:

```bash
make open
```

The first admin account is created on startup from:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

In production, set `ADMIN_PASSWORD` and `COOKIE_SECRET` through deployment secrets. Do not commit real secrets.

## Docker Runner

Untrusted bot code runs inside Docker, never directly in the backend process. Production match execution requires the backend container to access the Docker socket and use the sandbox image from `runner/Dockerfile`.

Useful Docker variables:

```env
BOT_RUNNER_IMAGE=code-clash-runner:local
BOT_RUNNER_CONTAINER_NAME=code-clash-bot-runner
```

## Tests

Run the full test suite:

```bash
make test
```

Run backend only:

```bash
uv run pytest
```

Run frontend unit tests:

```bash
cd frontend && npm run test
```

Run browser tests:

```bash
cd frontend && npm run test:e2e
```
