/**
 * Long-running daemon that keeps a Playwright browser alive.
 *
 * Run once (automatically spawned by connectOrLaunch if not running):
 *   npx ts-node src/browser-server.ts
 *
 * The Playwright WS endpoint is written to data/browser.endpoint.
 * Kill this process to close the browser:
 *   kill $(cat data/browser.pid)
 */

import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";

const DATA_DIR = path.join(__dirname, "../data");
const ENDPOINT_FILE = path.join(DATA_DIR, "browser.endpoint");
const PID_FILE = path.join(DATA_DIR, "browser.pid");

async function main() {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }

  const browserServer = await chromium.launchServer({
    headless: false,
    args: [
      "--no-sandbox",
      "--disable-blink-features=AutomationControlled",
      "--disable-infobars",
      "--no-first-run",
      "--no-default-browser-check",
      "--window-size=1280,800",
    ],
  });

  const wsEndpoint = browserServer.wsEndpoint();
  fs.writeFileSync(ENDPOINT_FILE, wsEndpoint, "utf-8");
  fs.writeFileSync(PID_FILE, String(process.pid), "utf-8");

  const cleanup = async () => {
    try {
      fs.unlinkSync(ENDPOINT_FILE);
    } catch {
      /* ignore */
    }
    try {
      fs.unlinkSync(PID_FILE);
    } catch {
      /* ignore */
    }
    await browserServer.close();
    process.exit(0);
  };

  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);

  // Keep process alive indefinitely — Chrome lives as long as this process lives.
  await new Promise<never>(() => {
    /* intentionally never resolves */
  });
}

main().catch((err) => {
  console.error("Browser server error:", err);
  process.exit(1);
});
