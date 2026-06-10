/*
This file shows tournament creation, entry, standings, and match progress.
Edit this file when tournament workflows or settings change.
Copy this file as a starting point for another workflow page.
*/

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "../app/auth";
import { postJson } from "../shared/api";
import type { Bot, Match, Tournament, TournamentEntry } from "../shared/types";

export function TournamentsPage() {
  const { user } = useAuth();
  const [bots, setBots] = useState<Bot[]>([]);
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [entries, setEntries] = useState<TournamentEntry[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [name, setName] = useState("Snake Tournament");
  const [entryVersionId, setEntryVersionId] = useState<number | null>(null);
  const [message, setMessage] = useState("");

  const load = async (id = selectedId) => {
    const [botData, tournamentData] = await Promise.all([postJson<{ bots: Bot[] }>("/bots/list"), postJson<{ tournaments: Tournament[] }>("/tournaments/list")]);
    setBots(botData.bots);
    setTournaments(tournamentData.tournaments);
    const nextId = id ?? tournamentData.tournaments[0]?.id ?? null;
    setSelectedId(nextId);
    if (nextId !== null) {
      const detail = await postJson<{ tournament: Tournament; entries: TournamentEntry[]; matches: Match[] }>("/tournaments/detail", { tournament_id: nextId });
      setEntries(detail.entries);
      setMatches(detail.matches);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const createTournament = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = await postJson<{ tournament: Tournament }>("/tournaments/create", {
      name,
      turn_timeout_ms: 100,
      memory_limit_mb: 128,
      max_turns: 500,
      games_per_pairing: 3,
    });
    await load(data.tournament.id);
  };

  const enterTournament = async () => {
    if (selectedId === null || entryVersionId === null) {
      setMessage("Choose a tournament and bot version.");
      return;
    }
    await postJson("/tournaments/enter", { tournament_id: selectedId, bot_version_id: entryVersionId });
    setMessage("Bot entered.");
    await load(selectedId);
  };

  const startTournament = async () => {
    if (selectedId === null) {
      return;
    }
    const data = await postJson<{ created_matches: number }>("/tournaments/start", { tournament_id: selectedId });
    setMessage(`Scheduled ${data.created_matches} matches.`);
    await load(selectedId);
  };

  const readyVersions = bots.flatMap((bot) => bot.versions.filter((version) => version.build_status === "ready").map((version) => ({ bot, version })));
  const selected = tournaments.find((tournament) => tournament.id === selectedId);

  return (
    <section className="space-y-5">
      <div className="border border-slate-200 bg-white p-5">
        <h2 className="text-2xl font-semibold">Tournaments</h2>
        <p className="mt-1 text-sm text-slate-600">Create a Snake tournament, enter ready bot versions, and follow the standings as matches finish.</p>
      </div>
      <form className="border border-slate-200 bg-white p-5" onSubmit={createTournament}>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Tournament name</span>
          <input className="w-full max-w-md border border-slate-300 px-3 py-2" onChange={(event) => setName(event.target.value)} value={name} />
        </label>
        <p className="mt-2 text-sm text-slate-600">New tournaments use Snake with safe default limits: 100 ms turns, 128 MB memory, 500 max turns, and 3 games per pairing.</p>
        <div className="mt-3">
          <button className="bg-slate-900 px-3 py-2 text-white" type="submit">
            Create tournament
          </button>
        </div>
      </form>
      <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-semibold">All tournaments</h3>
          <div className="mt-3 space-y-2">
            {tournaments.map((tournament) => (
              <button className="block w-full border border-slate-100 p-3 text-left" key={tournament.id} onClick={() => void load(tournament.id)} type="button">
                <span className="font-medium">{tournament.name}</span>
                <span className="ml-2 text-sm text-slate-600">{tournament.status}</span>
              </button>
            ))}
          </div>
        </section>
        <section className="space-y-5">
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-lg font-semibold">{selected?.name ?? "Tournament detail"}</h3>
            {selected ? (
              <p className="mt-1 text-sm text-slate-600">
                {selected.status}. {selected.games_per_pairing} games per pairing.
            </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              <label className="block">
                <span className="mb-1 block text-sm font-medium">Bot version to enter</span>
                <select className="border border-slate-300 px-3 py-2" onChange={(event) => setEntryVersionId(Number(event.target.value))} value={entryVersionId ?? ""}>
                  <option value="" disabled>
                    Ready bot version
                  </option>
                  {readyVersions.map(({ bot, version }) => (
                    <option key={version.id} value={version.id}>
                      {bot.name} v{version.version_number}
                    </option>
                  ))}
                </select>
              </label>
              <button className="border px-3 py-2" onClick={() => void enterTournament()} type="button">
                Enter
              </button>
              {user?.is_admin ? (
                <button className="bg-slate-900 px-3 py-2 text-white" onClick={() => void startTournament()} type="button">
                  Start
                </button>
              ) : null}
            </div>
            {message ? <p className="mt-3 bg-slate-100 px-3 py-2 text-sm">{message}</p> : null}
          </div>
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-lg font-semibold">Standings</h3>
            <div className="mt-3 space-y-2">
              {entries.map((entry) => (
                <div className="flex justify-between border-b border-slate-100 py-2" key={entry.id}>
                  <span>
                    {entry.bot_name} v{entry.version_number}
                  </span>
                  <span>{entry.points} pts</span>
                </div>
              ))}
            </div>
          </div>
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-lg font-semibold">Matches</h3>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {matches.map((match) => (
                <div className="border border-slate-100 p-3" key={match.id}>
                  <p className="font-medium">Match {match.id}</p>
                  <p className="text-sm text-slate-600">{match.status}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
