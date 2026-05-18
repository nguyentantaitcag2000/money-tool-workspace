import { Browser, BrowserContext, chromium, Page } from "playwright";
import { spawn } from "child_process";
import * as net from "net";
import * as path from "path";
import * as fs from "fs";

// Use a non-standard port to avoid conflict with any user-running Chrome on 9222
export const CDP_PORT = 9333;

const DATA_DIR = path.join(__dirname, "../data");
const LOG_FILE = path.join(DATA_DIR, "browser.log");

function appendLog(msg: string): void {
  try {
    if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.appendFileSync(LOG_FILE, `[${new Date().toISOString()}] ${msg}\n`);
  } catch {
    /* ignore */
  }
}

// ---------------------------------------------------------------------------
// Port probe
// ---------------------------------------------------------------------------

function isPortOpen(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(1500);
    socket.on("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.on("error", () => {
      socket.destroy();
      resolve(false);
    });
    socket.on("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.connect(port, "127.0.0.1");
  });
}

// ---------------------------------------------------------------------------
// Detached Chrome launch
// ---------------------------------------------------------------------------

async function launchDetachedChrome(): Promise<void> {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

  const execPath = chromium.executablePath();
  appendLog(`Launching Chrome binary: ${execPath}`);

  // Open log file for Chrome stdout/stderr so we can debug if needed
  const logFd = fs.openSync(LOG_FILE, "a");

  spawn(
    execPath,
    [
      `--remote-debugging-port=${CDP_PORT}`,
      "--no-sandbox",
      // --enable-automation is required for CDP Browser-domain commands
      // (e.g. Browser.setDownloadBehavior used by Playwright's connectOverCDP)
      "--enable-automation",
      // Remove navigator.webdriver flag that --enable-automation would normally set
      "--disable-blink-features=AutomationControlled",
      "--disable-infobars",
      "--no-first-run",
      "--no-default-browser-check",
      "--window-size=1280,800",
      "about:blank",
    ],
    {
      // detached: true creates a new process group — Chrome won't receive
      // signals meant for our Node process (e.g. Ctrl+C in terminal).
      // Chrome is a fully independent OS process; it survives our process exit.
      detached: true,
      stdio: ["ignore", logFd, logFd],
    },
  ).unref();

  fs.closeSync(logFd);

  console.log("🚀 Launching Chrome (detached)...");
  appendLog("Chrome spawned, waiting for CDP port...");

  // Wait up to 10 s for Chrome to open its CDP port
  for (let i = 0; i < 20; i++) {
    await new Promise<void>((r) => setTimeout(r, 500));
    if (await isPortOpen(CDP_PORT)) {
      appendLog("Chrome CDP port is ready");
      return;
    }
  }
  throw new Error(`Chrome did not open port ${CDP_PORT} within 10 seconds`);
}

// ---------------------------------------------------------------------------
// Stealth
// ---------------------------------------------------------------------------

type ContextOptions = Parameters<Browser["newContext"]>[0];

const STEALTH_CONTEXT_OPTIONS: ContextOptions = {
  userAgent:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
  viewport: { width: 1280, height: 800 },
  locale: "en-US",
  timezoneId: "Asia/Ho_Chi_Minh",
  permissions: ["clipboard-read", "clipboard-write"],
  extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
};

async function applyStealthScripts(context: BrowserContext): Promise<void> {
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
    Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, "languages", {
      get: () => ["en-US", "en"],
    });
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export interface BrowserHandle {
  browser: Browser;
  context: BrowserContext;
  /** true when Chrome was just launched (no prior session in memory) */
  isNew: boolean;
}

/**
 * Connect to Chrome via CDP on CDP_PORT, launching it first if not running.
 *
 * Chrome is a fully independent OS process — it survives our Node process
 * exiting for ANY reason (error, process.exit, SIGINT, etc.).
 */
export async function connectOrLaunch(): Promise<BrowserHandle> {
  const alreadyRunning = await isPortOpen(CDP_PORT);

  if (!alreadyRunning) {
    await launchDetachedChrome();
    // Brief pause to let Chrome fully initialise its CDP server
    await new Promise<void>((r) => setTimeout(r, 500));
  } else {
    console.log(`♻️  Reusing existing Chrome on port ${CDP_PORT}`);
    appendLog("Reusing existing Chrome");
  }

  const browser = await chromium.connectOverCDP(`http://localhost:${CDP_PORT}`);
  appendLog("Connected via CDP");

  // ---- Safety net -------------------------------------------------------
  // Playwright registers internal exit/signal handlers that call browser.close().
  // browser.close() over CDP sends a "close" command which terminates Chrome.
  // We replace it with a no-op so Chrome stays alive when our process exits.
  (browser as unknown as Record<string, unknown>).close = async () => {
    appendLog("browser.close() intercepted — Chrome stays alive");
  };
  // -----------------------------------------------------------------------

  const contexts = browser.contexts();
  const isNew = !alreadyRunning || contexts.length === 0;
  const context =
    contexts.length > 0
      ? contexts[0]
      : await browser.newContext(STEALTH_CONTEXT_OPTIONS);

  await applyStealthScripts(context);
  return { browser, context, isNew };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export async function humanDelay(minMs = 300, maxMs = 900): Promise<void> {
  const ms = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
  await new Promise((resolve) => setTimeout(resolve, ms));
}

export async function humanType(
  page: Page,
  selector: string,
  text: string,
): Promise<void> {
  await page.click(selector);
  await humanDelay(100, 300);
  for (const char of text) {
    await page.keyboard.type(char, {
      delay: Math.floor(Math.random() * 80) + 30,
    });
  }
}

export async function loadCookies(
  context: BrowserContext,
  cookiesPath: string,
): Promise<void> {
  if (!fs.existsSync(cookiesPath)) return;
  const cookies = JSON.parse(fs.readFileSync(cookiesPath, "utf-8"));
  await context.addCookies(cookies);
}

export async function saveCookies(
  context: BrowserContext,
  cookiesPath: string,
): Promise<void> {
  const cookies = await context.cookies();
  fs.writeFileSync(cookiesPath, JSON.stringify(cookies, null, 2));
}

// ---------------------------------------------------------------------------
// Large-file injection (CDP-safe, no setInputFiles)
// ---------------------------------------------------------------------------

/**
 * Inject a local file (any size) into a hidden <input type="file"> without
 * using Playwright's setInputFiles().
 *
 * Strategy: call the Chrome CDP command DOM.setFileInputFiles directly via a
 * raw CDP session.  Chrome reads the file from its OWN local filesystem, so
 * zero file data travels over the CDP websocket → no 50 MB limit, no CSP
 * interference, works with all React-based sites.
 *
 * Prerequisites: the Playwright process and Chrome must share the same
 * filesystem (both running locally on the same machine), which is always true
 * when using connectOverCDP() to a local Chrome instance.
 */
export async function injectLargeFile(
  page: Page,
  inputSelector: string,
  filePath: string,
): Promise<void> {
  const fileName = path.basename(filePath);
  const fileSize = fs.statSync(filePath).size;
  console.log(
    `📎 Injecting ${fileName} (${(fileSize / 1_048_576).toFixed(1)} MB) via CDP...`,
  );

  // Open a page-level CDP session — works with connectOverCDP()
  const session = await page.context().newCDPSession(page);
  try {
    // Resolve the file input element to a backendNodeId
    const { result } = await session.send("Runtime.evaluate", {
      expression: `document.querySelector(${JSON.stringify(inputSelector)})`,
      returnByValue: false,
    });

    if (result.subtype === "null" || !result.objectId) {
      throw new Error(`File input not found: ${inputSelector}`);
    }

    const { node } = await session.send("DOM.describeNode", {
      objectId: result.objectId,
    });

    if (!node.backendNodeId) {
      throw new Error(`Could not obtain backendNodeId for: ${inputSelector}`);
    }

    // Chrome reads the file from disk — no data crosses the CDP websocket
    await session.send("DOM.setFileInputFiles", {
      files: [filePath],
      backendNodeId: node.backendNodeId,
    });
  } finally {
    await session.detach();
  }
}
