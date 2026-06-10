/*
This file shows the logged-in Code Clash dashboard and live update status.
Edit this file when dashboard data or websocket refresh behavior changes.
Copy this file as a starting point for another logged-in overview page.
*/

import { useEffect, useState } from "react";
import { useAuth } from "../app/auth";
import { postJson } from "../shared/api";
import { createUserSocket, type SocketStatus } from "../shared/socket";
import type { LeaderboardRow, Match, Tournament, WsMessage } from "../shared/types";

export function DashboardPage() {
  const { user } = useAuth();
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("idle");

  const load = async () => {
    const [leaderboardData, matchesData, tournamentsData] = await Promise.all([
      postJson<{ leaderboard: LeaderboardRow[] }>("/leaderboard/global"),
      postJson<{ matches: Match[] }>("/matches/list"),
      postJson<{ tournaments: Tournament[] }>("/tournaments/list"),
    ]);
    setLeaderboard(leaderboardData.leaderboard);
    setMatches(matchesData.matches);
    setTournaments(tournamentsData.tournaments);
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    const socket = createUserSocket({
      onMessage(message: WsMessage) {
        if (["match.started", "match.finished", "tournament.updated", "leaderboard.updated"].includes(message.type)) {
          void load();
        }
      },
      onStatus: setSocketStatus,
    });
    return () => socket.stop();
  }, []);

  return (
    <section className="space-y-5">
      <div className="border border-slate-200 bg-white p-5">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="mt-1 text-sm text-slate-600">
          Logged in as {user?.username}. Live updates: {socketStatus}.
        </p>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-semibold">Leaderboard</h3>
          <div className="mt-3 space-y-2">
            {leaderboard.map((row) => (
              <div className="flex justify-between border-b border-slate-100 py-2" key={row.version_id}>
                <span>
                  {row.bot_name} v{row.version_number} by {row.owner_username}
                </span>
                <strong>{Math.round(row.elo)}</strong>
              </div>
            ))}
            {leaderboard.length === 0 ? <p className="text-sm text-slate-600">No ready bot versions yet.</p> : null}
          </div>
        </section>
        <section className="border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-semibold">Recent matches</h3>
          <div className="mt-3 space-y-2">
            {matches.slice(0, 8).map((match) => (
              <div className="flex justify-between border-b border-slate-100 py-2" key={match.id}>
                <span>Match {match.id}</span>
                <span>{match.status}</span>
              </div>
            ))}
            {matches.length === 0 ? <p className="text-sm text-slate-600">No matches yet.</p> : null}
          </div>
        </section>
      </div>
      <section className="border border-slate-200 bg-white p-5">
        <h3 className="text-lg font-semibold">Tournaments</h3>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          {tournaments.map((tournament) => (
            <div className="border border-slate-100 p-3" key={tournament.id}>
              <p className="font-medium">{tournament.name}</p>
              <p className="text-sm text-slate-600">{tournament.status}</p>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}
