/*
This file tests the replay page load form.
Edit this file when replay page controls or API calls change.
Copy this file for another small page test.
*/

import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReplayPage } from "./ReplayPage";

vi.mock("../shared/api", () => ({
  postJson: vi.fn(),
}));

describe("ReplayPage", () => {
  it("shows replay load controls", () => {
    render(<ReplayPage />);
    expect(screen.getByRole("heading", { name: "Replay" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Match id")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load replay" })).toBeInTheDocument();
  });
});
