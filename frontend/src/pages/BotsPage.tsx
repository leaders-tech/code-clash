/*
This file lets users create bots and paste Python or C++ source versions.
Edit this file when bot management or upload behavior changes.
Copy this file as a starting point for another CRUD page.
*/

import { FormEvent, useEffect, useState } from "react";
import { postJson } from "../shared/api";
import type { Bot } from "../shared/types";

const PYTHON_EXAMPLE = `import json, sys
state = json.loads(sys.stdin.read())
print("RIGHT")`;

const GAME_STATE_EXAMPLE = `{
  "game": "snake",
  "turn": 0,
  "you": 12,
  "width": 15,
  "height": 15,
  "food": [7, 4],
  "snakes": [
    {
      "id": 12,
      "name": "My Bot",
      "alive": true,
      "body": [[2, 2], [1, 2], [0, 2]]
    }
  ]
}`;

const RESULT_EXAMPLE = `UP
DOWN
LEFT
RIGHT`;

export function BotsPage() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [name, setName] = useState("");
  const [selectedBotId, setSelectedBotId] = useState<number | null>(null);
  const [language, setLanguage] = useState<"python" | "cpp">("python");
  const [filename, setFilename] = useState("bot.py");
  const [source, setSource] = useState(PYTHON_EXAMPLE);
  const [message, setMessage] = useState("");

  const load = async () => {
    const data = await postJson<{ bots: Bot[] }>("/bots/list");
    setBots(data.bots);
    if (selectedBotId === null && data.bots[0]) {
      setSelectedBotId(data.bots[0].id);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const createBot = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage("");
    await postJson("/bots/create", { name });
    setName("");
    await load();
  };

  const uploadVersion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedBotId === null) {
      setMessage("Create a bot first.");
      return;
    }
    const data = await postJson<{ version: { build_status: string; build_log: string } }>("/bots/upload-version", {
      bot_id: selectedBotId,
      language,
      filename,
      source,
    });
    setMessage(`${data.version.build_status}: ${data.version.build_log}`);
    await load();
  };

  const setActive = async (botId: number, versionId: number) => {
    await postJson("/bots/set-active-version", { bot_id: botId, version_id: versionId });
    await load();
  };

  return (
    <section className="space-y-5">
      <div className="border border-slate-200 bg-white p-5">
        <h2 className="text-2xl font-semibold">Bots</h2>
        <p className="mt-1 text-sm text-slate-600">Create a bot, then paste Python or C++ source as a version.</p>
      </div>
      <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <section className="border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-semibold">Your bots</h3>
          <form className="mt-3 space-y-2" onSubmit={createBot}>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Bot name</span>
              <input className="w-full border border-slate-300 px-3 py-2" onChange={(event) => setName(event.target.value)} placeholder="Bot name" value={name} />
            </label>
            <p className="text-sm text-slate-600">Use a short name you will recognize in tournaments and replays.</p>
            <div>
              <button className="bg-slate-900 px-3 py-2 text-white" type="submit">
                Create
              </button>
            </div>
          </form>
          <div className="mt-4 space-y-3">
            {bots.map((bot) => (
              <div className="border border-slate-100 p-3" key={bot.id}>
                <button className="font-semibold" onClick={() => setSelectedBotId(bot.id)} type="button">
                  {bot.name}
                </button>
                <p className="text-sm text-slate-600">Owner: {bot.owner_username}</p>
                <div className="mt-2 space-y-2 text-sm">
                  {bot.versions.map((version) => (
                    <div className="border-t border-slate-100 pt-2" key={version.id}>
                      <div className="flex items-center justify-between gap-2">
                        <span>
                          v{version.version_number} {version.language} {version.build_status} Elo {Math.round(version.elo)}
                        </span>
                        {version.build_status === "ready" ? (
                          <button className="border px-2 py-1" onClick={() => void setActive(bot.id, version.id)} type="button">
                            {bot.active_version_id === version.id ? "Active" : "Use"}
                          </button>
                        ) : null}
                      </div>
                      <p className="mt-1 text-slate-600">{version.build_log}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
        <section className="border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-semibold">Upload version</h3>
          <div className="mt-3 grid gap-3 text-sm lg:grid-cols-2">
            <div className="border border-slate-100 bg-slate-50 p-3">
              <h4 className="font-semibold">Game state from stdin</h4>
              <p className="mt-1 text-slate-600">Your bot receives one JSON object each turn.</p>
              <pre className="mt-2 overflow-auto border border-slate-200 bg-white p-2 font-mono text-xs leading-5">{GAME_STATE_EXAMPLE}</pre>
            </div>
            <div className="border border-slate-100 bg-slate-50 p-3">
              <h4 className="font-semibold">Result to stdout</h4>
              <p className="mt-1 text-slate-600">Print exactly one move. Extra text may be ignored or treated as a bad move.</p>
              <pre className="mt-2 overflow-auto border border-slate-200 bg-white p-2 font-mono text-xs leading-5">{RESULT_EXAMPLE}</pre>
            </div>
          </div>
          <form className="mt-3 space-y-3" onSubmit={uploadVersion}>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Bot</span>
              <select className="w-full border border-slate-300 px-3 py-2" onChange={(event) => setSelectedBotId(Number(event.target.value))} value={selectedBotId ?? ""}>
                <option value="" disabled>
                  Select bot
                </option>
                {bots.map((bot) => (
                  <option key={bot.id} value={bot.id}>
                    {bot.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Language</span>
              <select
                className="w-full border border-slate-300 px-3 py-2"
                onChange={(event) => {
                  const next = event.target.value as "python" | "cpp";
                  setLanguage(next);
                  setFilename(next === "python" ? "bot.py" : "bot.cpp");
                }}
                value={language}
              >
                <option value="python">Python</option>
                <option value="cpp">C++</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Filename</span>
              <input className="w-full border border-slate-300 px-3 py-2" onChange={(event) => setFilename(event.target.value)} value={filename} />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Source</span>
              <span className="mb-2 block text-sm text-slate-600">Read one JSON game state from stdin, then print one move: UP, DOWN, LEFT, or RIGHT.</span>
              <textarea className="h-72 w-full border border-slate-300 px-3 py-2 font-mono text-sm" onChange={(event) => setSource(event.target.value)} value={source} />
            </label>
            {message ? <p className="bg-slate-100 px-3 py-2 text-sm">{message}</p> : null}
            <button className="bg-slate-900 px-3 py-2 font-semibold text-white" type="submit">
              Upload version
            </button>
          </form>
        </section>
      </div>
    </section>
  );
}
