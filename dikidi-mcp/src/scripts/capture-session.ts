import { chromium } from "playwright";
import { config } from "../config.js";
import { SELECTORS } from "../dikidi/selectors.js";

async function main() {
  console.log("Opening a browser window. Log into DIKIDI Business manually — take your time, solve any captcha/2FA.");
  console.log(`Login page: ${config.loginUrl}`);

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(config.loginUrl, { waitUntil: "domcontentloaded", timeout: 60000 });

  console.log("Браузер открыт — войдите в аккаунт вручную.");
  console.log("Жду появления панели после входа (без ограничения по времени)...");
  await page.waitForSelector(SELECTORS.login.loggedInMarker, { timeout: 0 });

  await context.storageState({ path: config.storageStatePath });
  console.log(`Session saved to ${config.storageStatePath}. You can close the browser window now.`);

  await browser.close();
  process.exit(0);
}

main().catch((err) => {
  console.error("Что-то пошло не так:", err instanceof Error ? err.message : err);
  console.error("Окно браузера оставлено открытым для проверки. Закройте его вручную и повторите npm run login:dev.");
});
