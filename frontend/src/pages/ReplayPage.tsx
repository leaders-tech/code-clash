/*
This file shows compressed match replays after they are loaded from the backend.
Edit this file when replay playback or Snake rendering changes.
Copy this file as a starting point for another replay viewer.
*/

import { FormEvent, useEffect, useMemo, useState } from "react";
import { postJson } from "../shared/api";
import type { Replay } from "../shared/types";

export function ReplayPage() {
  const [matchId, setMatchId] = useState("");
  const [replay, setReplay] = useState<Replay | null>(null);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(300);
  const [error, setError] = useState("");

  const loadReplay = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    try {
      const data = await postJson<{ replay: Replay }>("/replays/get", { match_id: Number(matchId) });
      setReplay(data.replay);
      setStep(0);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Replay could not be loaded.");
    }
  };

  useEffect(() => {
    if (!playing || !replay) {
      return;
    }
    const timer = window.setInterval(() => {
      setStep((current) => Math.min(current + 1, replay.turns.length - 1));
    }, speed);
    return () => window.clearInterval(timer);
  }, [playing, replay, speed]);

  const frame = replay?.turns[Math.min(step, Math.max(replay.turns.length - 1, 0))];
  const cells = useMemo(() => {
    if (!replay || !frame) {
      return [];
    }
    const snakeCells = new Map<string, { id: number; alive: boolean }>();
    for (const snake of frame.snakes) {
      for (const [x, y] of snake.body) {
        snakeCells.set(`${x},${y}`, { id: snake.id, alive: snake.alive });
      }
    }
    return Array.from({ length: replay.width * replay.height }, (_, index) => {
      const x = index % replay.width;
      const y = Math.floor(index / replay.width);
      const snake = snakeCells.get(`${x},${y}`);
      const food = frame.food && frame.food[0] === x && frame.food[1] === y;
      return { x, y, snake, food };
    });
  }, [frame, replay]);

  return (
    <section className="space-y-5">
      <div className="border border-slate-200 bg-white p-5">
        <h2 className="text-2xl font-semibold">Replay</h2>
        <p className="mt-1 text-sm text-slate-600">Load a finished match and step through the Snake replay.</p>
      </div>
      <form className="border border-slate-200 bg-white p-5" onSubmit={loadReplay}>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Match id</span>
          <input className="w-full max-w-xs border border-slate-300 px-3 py-2" onChange={(event) => setMatchId(event.target.value)} placeholder="Match id" value={matchId} />
        </label>
        <p className="mt-2 text-sm text-slate-600">Open a finished match from the tournament page, then enter its match id here.</p>
        <button className="mt-3 bg-slate-900 px-3 py-2 text-white" type="submit">
          Load replay
        </button>
        {error ? <p className="px-3 py-2 text-sm text-rose-700">{error}</p> : null}
      </form>
      {replay && frame ? (
        <section className="border border-slate-200 bg-white p-5">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <button className="border px-3 py-2" onClick={() => setStep((current) => Math.max(0, current - 1))} type="button">
              Previous
            </button>
            <button className="border px-3 py-2" onClick={() => setPlaying((current) => !current)} type="button">
              {playing ? "Pause" : "Play"}
            </button>
            <button className="border px-3 py-2" onClick={() => setStep((current) => Math.min(replay.turns.length - 1, current + 1))} type="button">
              Next
            </button>
            <label className="flex items-center gap-2 text-sm">
              Speed
              <input max="1000" min="80" onChange={(event) => setSpeed(Number(event.target.value))} step="20" type="range" value={speed} />
            </label>
            <span className="text-sm text-slate-600">
              Turn {step + 1} of {replay.turns.length}
            </span>
          </div>
          <div className="grid w-full max-w-xl border border-slate-300" style={{ gridTemplateColumns: `repeat(${replay.width}, minmax(0, 1fr))` }}>
            {cells.map((cell) => (
              <div
                className={cell.food ? "aspect-square bg-rose-400" : cell.snake ? (cell.snake.alive ? "aspect-square bg-emerald-500" : "aspect-square bg-slate-400") : "aspect-square bg-slate-50"}
                key={`${cell.x},${cell.y}`}
                title={cell.snake ? `Bot ${cell.snake.id}` : cell.food ? "Food" : ""}
              />
            ))}
          </div>
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {Object.entries(frame.actions).map(([botId, action]) => (
              <div className="border border-slate-100 p-3 text-sm" key={botId}>
                Bot {botId}: {action.move}
                {action.error ? <p className="text-rose-700">{action.error}</p> : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
