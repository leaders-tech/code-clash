"""Create Code Clash bot, match, and tournament tables.

Edit this file only if this migration has not been used yet.
Create a new migration file instead when the Code Clash schema changes.
"""

from yoyo import step


steps = [
    step(
        """
        CREATE TABLE bots (
            id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            active_version_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        ) STRICT
        """,
        "DROP TABLE bots",
    ),
    step(
        """
        CREATE TABLE bot_versions (
            id INTEGER PRIMARY KEY,
            bot_id INTEGER NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            language TEXT NOT NULL CHECK (language IN ('python', 'cpp')),
            filename TEXT NOT NULL,
            source TEXT NOT NULL,
            build_status TEXT NOT NULL CHECK (build_status IN ('pending', 'ready', 'failed')),
            build_log TEXT NOT NULL,
            artifact BLOB,
            elo REAL NOT NULL DEFAULT 1000,
            created_at TEXT NOT NULL,
            UNIQUE(bot_id, version_number)
        ) STRICT
        """,
        "DROP TABLE bot_versions",
    ),
    step(
        """
        CREATE TABLE tournaments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            game_key TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('draft', 'running', 'finished')),
            turn_timeout_ms INTEGER NOT NULL,
            memory_limit_mb INTEGER NOT NULL,
            max_turns INTEGER NOT NULL,
            games_per_pairing INTEGER NOT NULL,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        ) STRICT
        """,
        "DROP TABLE tournaments",
    ),
    step(
        """
        CREATE TABLE tournament_entries (
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            bot_version_id INTEGER NOT NULL REFERENCES bot_versions(id) ON DELETE CASCADE,
            points REAL NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            draws INTEGER NOT NULL DEFAULT 0,
            UNIQUE(tournament_id, bot_version_id)
        ) STRICT
        """,
        "DROP TABLE tournament_entries",
    ),
    step(
        """
        CREATE TABLE matches (
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER REFERENCES tournaments(id) ON DELETE SET NULL,
            game_key TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'finished', 'failed')),
            seed INTEGER NOT NULL,
            turn_timeout_ms INTEGER NOT NULL,
            memory_limit_mb INTEGER NOT NULL,
            max_turns INTEGER NOT NULL,
            replay BLOB,
            result_json TEXT NOT NULL DEFAULT '{}',
            error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT
        ) STRICT
        """,
        "DROP TABLE matches",
    ),
    step(
        """
        CREATE TABLE match_bots (
            id INTEGER PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            bot_version_id INTEGER NOT NULL REFERENCES bot_versions(id) ON DELETE CASCADE,
            slot INTEGER NOT NULL,
            points REAL NOT NULL DEFAULT 0,
            final_rank INTEGER,
            UNIQUE(match_id, bot_version_id),
            UNIQUE(match_id, slot)
        ) STRICT
        """,
        "DROP TABLE match_bots",
    ),
    step("CREATE INDEX idx_bot_versions_bot_id ON bot_versions(bot_id)", "DROP INDEX idx_bot_versions_bot_id"),
    step("CREATE INDEX idx_matches_status ON matches(status)", "DROP INDEX idx_matches_status"),
    step("CREATE INDEX idx_matches_tournament_id ON matches(tournament_id)", "DROP INDEX idx_matches_tournament_id"),
]
