/*
This file checks the main browser flow for Code Clash.
Edit this file when auth, bot upload, or core navigation changes.
Copy this file when adding another end-to-end browser flow.
*/

import { expect, test } from "@playwright/test";

test("user can register, upload a Python bot, and view platform pages", async ({ page }) => {
  const username = `student_${Date.now()}`;
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Login" })).toBeVisible();
  await page.getByRole("button", { name: "Register" }).first().click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill("secret1");
  await page.locator("form").getByRole("button", { name: "Register" }).click();

  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await page.getByRole("link", { name: "Bots" }).click();
  await page.getByPlaceholder("Bot name").fill("Browser Bot");
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page.getByRole("button", { name: "Browser Bot" })).toBeVisible();
  await page.getByRole("button", { name: "Upload version" }).click();
  await expect(page.getByText("ready: Python bot saved.")).toBeVisible();

  await page.getByRole("link", { name: "Tournaments" }).click();
  await expect(page.getByRole("heading", { name: "Tournaments", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Replay" }).click();
  await expect(page.getByRole("heading", { name: "Replay" })).toBeVisible();
});
