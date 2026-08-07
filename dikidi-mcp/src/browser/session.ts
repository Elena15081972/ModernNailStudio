import { existsSync } from "node:fs";
import { type Browser, type BrowserContext, chromium } from "playwright";
import { config } from "../config.js";

let browser: Browser | null = null;
let context: BrowserContext | null = null;

async function getContext(): Promise<BrowserContext> {
  if (context) return context;

  if (!existsSync(config.storageStatePath)) {
    throw new Error(
      `No saved DIKIDI session at ${config.storageStatePath}. Run "npm run login" once to log in manually and capture it.`,
    );
  }

  browser = await chromium.launch({ headless: config.headless });
  context = await browser.newContext({ storageState: config.storageStatePath });
  return context;
}

export async function newPage() {
  const ctx = await getContext();
  return ctx.newPage();
}

export async function closeBrowser(): Promise<void> {
  await context?.close();
  await browser?.close();
  context = null;
  browser = null;
}
