/*
This file tests the bot management page basics.
Edit this file when bot page forms or API calls change.
Copy this file for another small page test.
*/

import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BotsPage } from "./BotsPage";

vi.mock("../shared/api", () => ({
  postJson: vi.fn().mockResolvedValue({ bots: [] }),
}));

describe("BotsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows create and upload controls", async () => {
    render(<BotsPage />);
    expect(await screen.findByRole("heading", { name: "Bots" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Bot name")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload version" })).toBeInTheDocument();
  });
});
