#!/usr/bin/env ts-node
/**
 * Scenario: Upload a video to Threads (https://www.threads.com)
 *
 * Usage:
 *   ts-node src/scenarios/threads-upload.ts --video /path/to/video.mp4 --caption "My caption"
 *
 * Or called from Python:
 *   subprocess.run(["npx", "ts-node", "src/scenarios/threads-upload.ts",
 *                   "--video", video_path, "--caption", title])
 */

import * as path from "path";
import * as fs from "fs";
import {
  humanDelay,
  humanType,
  connectOrLaunch,
  loadCookies,
  saveCookies,
  injectLargeFile,
} from "../browser";

// ---------------------------------------------------------------------------
// CLI args
// ---------------------------------------------------------------------------
function parseArgs(): { videoPath: string; caption: string } {
  const args = process.argv.slice(2);
  const get = (flag: string) => {
    const idx = args.indexOf(flag);
    if (idx === -1) return null;
    return args[idx + 1] ?? null;
  };

  const videoPath = get("--video");
  const caption = get("--caption") ?? "";

  if (!videoPath) {
    console.error("❌ --video <path> is required");
    process.exit(1);
  }

  if (!fs.existsSync(videoPath)) {
    console.error(`❌ Video file not found: ${videoPath}`);
    process.exit(1);
  }

  return { videoPath: path.resolve(videoPath), caption };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  const { videoPath, caption } = parseArgs();

  const COOKIES_PATH = path.join(__dirname, "../../data/threads_cookies.json");
  const DATA_DIR = path.join(__dirname, "../../data");
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

  console.log(`📹 Video : ${videoPath}`);
  console.log(`📝 Caption: ${caption}`);

  const { browser: _browser, context, isNew } = await connectOrLaunch();
  void _browser;

  try {
    // Only restore cookies on a brand-new context (don't overwrite a live session)
    if (isNew) await loadCookies(context, COOKIES_PATH);

    // Reuse the last open page if there is one, otherwise open a new tab
    const existingPages = context.pages();
    const page =
      existingPages.length > 0
        ? existingPages[existingPages.length - 1]
        : await context.newPage();

    // -----------------------------------------------------------------------
    // 1. Go to Threads
    // -----------------------------------------------------------------------
    console.log("🌐 Navigating to Threads...");
    /*Sử dụng đoạn wait networkidle không ổn định với các trang spa, vì nó hay lỗi timeout*/
    // await page.goto("https://www.threads.com", { waitUntil: "networkidle" });
    await page.goto("https://www.threads.com", {
      waitUntil: "domcontentloaded",
      timeout: 60000,
    });
    await page.waitForSelector("body");

    await humanDelay(1500, 2500);

    // -----------------------------------------------------------------------
    // 2. Login check — if not logged in, we wait for manual login then save cookies
    // -----------------------------------------------------------------------
    const isLoggedIn = await page
      .locator('a[href*="/@"]')
      .first()
      .isVisible()
      .catch(() => false);

    if (!isLoggedIn) {
      console.log(
        "⚠️  Not logged in. Please log in manually in the browser window.",
      );
      console.log("    Waiting up to 120 seconds for login...");

      // Wait until something that only appears when logged in is visible
      await page
        .locator('[aria-label="New thread"], [data-pressable-container="true"]')
        .first()
        .waitFor({ timeout: 120_000 })
        .catch(() => {
          throw new Error(
            "Login timeout — please run again and log in within 120 s.",
          );
        });

      await saveCookies(context, COOKIES_PATH);
      console.log(`✅ Cookies saved to ${COOKIES_PATH}`);
    }

    // -----------------------------------------------------------------------
    // 3. Click New Thread / compose button
    // -----------------------------------------------------------------------
    console.log("✏️  Opening compose dialog...");

    // goto https://www.threads.com/@talilow.x
    await page.goto("https://www.threads.com/@talilow.x", {
      waitUntil: "networkidle",
    });
    // click div have aria-label="Empty text field. Type to compose a new post."
    await page
      .locator(
        'div[aria-label="Empty text field. Type to compose a new post."]',
      )
      .first()
      .click();

    await humanDelay(1000, 2000);

    // -----------------------------------------------------------------------
    // 4. Attach video file
    // -----------------------------------------------------------------------

    // Threads uses a hidden <input type="file"> triggered by clicking a media icon
    console.log("📎 Preparing media input...");

    // Đợi input file xuất hiện trong DOM
    const fileInput = page.locator('input[type="file"]').last();

    await fileInput.waitFor({
      state: "attached",
      timeout: 15000,
    });

    // Force hiện input nếu Threads đang hidden nó
    await fileInput.evaluate((el: HTMLInputElement) => {
      el.style.display = "block";
      el.style.visibility = "visible";
      el.style.opacity = "1";
    });

    // Inject trực tiếp file vào input
    await injectLargeFile(page, 'input[type="file"]', videoPath);

    console.log("⏳ Waiting for video to process...");

    // Wait until the video preview/thumbnail appears (up to 90 s for large files)
    await page
      .locator('video, [data-testid="media-preview"]')
      .first()
      .waitFor({ timeout: 90_000 })
      .catch(() =>
        console.warn("⚠️  Could not confirm video preview — continuing anyway"),
      );

    await humanDelay(1500, 2500);

    // -----------------------------------------------------------------------
    // 5. Type caption
    // -----------------------------------------------------------------------
    if (caption) {
      console.log("✍️  Typing caption...");
      const captionSelectors = [
        '[contenteditable="true"]',
        "textarea[placeholder]",
        '[data-testid="thread-composer-text-input"]',
      ];

      for (const sel of captionSelectors) {
        const el = page.locator(sel).first();
        if (await el.isVisible().catch(() => false)) {
          await humanType(page, sel, caption);
          break;
        }
      }

      await humanDelay(500, 1000);
    }

    // -----------------------------------------------------------------------
    // 6. Submit / Post
    // -----------------------------------------------------------------------
    console.log("🚀 Posting...");

    // Find div have role="button" and contains text "Post" and click
    const postButton = page
      .locator('div[role="button"]:has-text("Post")')
      .filter({
        hasText: /^Post$/,
      })
      .last();

    await postButton.click();
    // wait until see "Posting..." appear
    await page
      .getByRole("status")
      .filter({ hasText: /^Posting\.\.\.$/ })
      .waitFor({ timeout: 15000 });

    // Wait until Threads finishes posting
    const postingIndicator = page
      .getByRole("status")
      .filter({ hasText: /^Posting\.\.\.$/ });

    await postingIndicator.waitFor({
      state: "hidden",
      timeout: 300_000,
    });
    // Save refreshed cookies
    await saveCookies(context, COOKIES_PATH);

    console.log("✅ Video uploaded to Threads successfully!");
    process.exit(0);
  } catch (err) {
    console.error("❌ Error:", err);
    // Best-effort cookie save before exit
    try {
      await saveCookies(context, COOKIES_PATH);
    } catch {
      /* ignore */
    }
    console.log(
      "🔍 Browser kept open for debugging. Fix the issue and re-run the script.",
    );
    process.exit(1);
  }
}

main();
