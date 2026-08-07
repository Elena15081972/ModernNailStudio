import { chromium } from "playwright";
import { config } from "../config.js";
import { SELECTORS } from "../dikidi/selectors.js";

async function main() {
  console.log("Opening a browser window. Log into DIKIDI Business manually — take your time, solve any captcha/2FA.");
  console.log(`Login page: ${config.loginUrl}`);

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(config.loginUrl);

  console.log("Waiting for the dashboard to load after you log in...");
  await page.waitForSelector(SELECTORS.login.loggedInMarker, { timeout: 0 });

  await context.storageState({ path: config.storageStatePath });
  console.log(`Session saved to ${config.storageStatePath}. You can close the browser window now.`);

  await browser.close();
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
