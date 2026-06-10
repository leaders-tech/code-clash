/*
This file keeps shared TypeScript types for Code Clash API data.
Edit this file when backend JSON shapes or websocket messages change.
Copy a type pattern here when adding another shared API type.
*/

export type User = {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
};

export type BotVersion = {
  id: number;
  bot_id: number;
  version_number: number;
  language: "python" | "cpp";
  filename: string;
  build_status: "pending" | "ready" | "failed";
  build_log: string;
  elo: number;
  created_at: string;
};

export type Bot = {
  id: number;
  owner_id: number;
  owner_username: string;
  name: string;
  active_version_id: number | null;
  created_at: string;
  updated_at: string;
  versions: BotVersion[];
};

export type Tournament = {
  id: number;
  name: string;
  game_key: string;
  status: "draft" | "running" | "finished";
  turn_timeout_ms: number;
  memory_limit_mb: number;
  max_turns: number;
  games_per_pairing: number;
  created_by: number;
  created_at: string;
  updated_at: string;
};

export type TournamentEntry = {
  id: number;
  tournament_id: number;
  bot_version_id: number;
  bot_name: string;
  owner_username: string;
  version_number: number;
  elo: number;
  points: number;
  wins: number;
  losses: number;
  draws: number;
};

export type Match = {
  id: number;
  tournament_id: number | null;
  game_key: string;
  status: "queued" | "running" | "finished" | "failed";
  seed: number;
  turn_timeout_ms: number;
  memory_limit_mb: number;
  max_turns: number;
  result?: unknown;
  error: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type LeaderboardRow = {
  version_id: number;
  version_number: number;
  language: "python" | "cpp";
  elo: number;
  bot_name: string;
  owner_username: string;
};

export type Replay = {
  game: "snake";
  seed: number;
  width: number;
  height: number;
  bots: { bot_version_id: number; bot_name: string }[];
  turns: {
    turn: number;
    food: [number, number] | null;
    actions: Record<string, { move: string; raw: string; error: string }>;
    dead: number[];
    snakes: { id: number; alive: boolean; body: [number, number][] }[];
  }[];
  result: { bots: { bot_version_id: number; points: number; rank: number; alive: boolean }[] };
};

export type ApiOk<T> = {
  ok: true;
  data: T;
};

export type ApiFail = {
  ok: false;
  error: {
    code: string;
    message: string;
  };
};

export type ApiResponse<T> = ApiOk<T> | ApiFail;

export type WsMessage =
  | { type: "ws.ready"; user_id: number; connections: number }
  | { type: "pong" }
  | { type: "match.started"; match_id: number; tournament_id: number | null }
  | { type: "match.turn"; match_id: number; turn: number; bot_version_id: number; move: string }
  | { type: "match.finished"; match_id: number; tournament_id: number | null; result?: unknown; error?: string }
  | { type: "tournament.updated"; tournament_id: number }
  | { type: "leaderboard.updated" };
