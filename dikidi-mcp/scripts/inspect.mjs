import { chromium } from "playwright";
import { writeFileSync } from "node:fs";
import "dotenv/config";

const url = process.argv[2] ?? process.env.DIKIDI_LOGIN_URL;
const outName = process.argv[3] ?? "dump";

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ storageState: process.env.DIKIDI_STORAGE_STATE_PATH ?? "./.dikidi-session.json" });
const page = await context.newPage();

await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);

writeFileSync(`./scripts/${outName}.html`, await page.content());
await page.screenshot({ path: `./scripts/${outName}.png`, fullPage: true });

console.log("URL after load:", page.url());
console.log("Title:", await page.title());

await browser.close();
