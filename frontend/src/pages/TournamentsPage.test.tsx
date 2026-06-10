/*
This file tests the tournament page basics.
Edit this file when tournament page forms or API calls change.
Copy this file for another workflow page test.
*/

import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthContext } from "../app/auth";
import { TournamentsPage } from "./TournamentsPage";

vi.mock("../shared/api", () => ({
  postJson: vi.fn((path: string) => {
    if (path === "/bots/list") {
      return Promise.resolve({ bots: [] });
    }
    if (path === "/tournaments/list") {
      return Promise.resolve({ tournaments: [] });
    }
    return Promise.resolve({});
  }),
}));

describe("TournamentsPage", () => {
  it("shows tournament controls for admins", async () => {
    render(
      <AuthContext.Provider
        value={{
          user: { id: 1, username: "admin", is_admin: true, created_at: "", updated_at: "" },
          loading: false,
          login: vi.fn(),
          register: vi.fn(),
          logout: vi.fn(),
          reloadUser: vi.fn(),
        }}
      >
        <TournamentsPage />
      </AuthContext.Provider>,
    );
    expect(await screen.findByRole("heading", { name: "Tournaments" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create tournament" })).toBeInTheDocument();
  });
});
