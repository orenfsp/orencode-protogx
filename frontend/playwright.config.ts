import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {
    ...devices["Desktop Chrome"],
    channel: "chrome",
    baseURL: process.env.FSP_WEB_URL ?? "http://127.0.0.1:3000",
  },
});
