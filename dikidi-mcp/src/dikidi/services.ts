import { newPage } from "../browser/session.js";
import { config } from "../config.js";
import { SELECTORS } from "./selectors.js";
import type { Service } from "./types.js";

export async function listServices(): Promise<Service[]> {
  const page = await newPage();
  try {
    await page.goto(new URL(SELECTORS.services.pageUrl, config.baseUrl).toString());
    await page.waitForSelector(SELECTORS.services.row);

    return await page.$$eval(
      SELECTORS.services.row,
      (rows, sel) =>
        rows.map((row) => ({
          name: row.querySelector(sel.name)?.textContent?.trim() ?? "",
          category: row.querySelector(sel.category)?.textContent?.trim() ?? null,
          price: row.querySelector(sel.price)?.textContent?.trim() ?? null,
          durationMinutes: row.querySelector(sel.durationMinutes)?.textContent?.trim() ?? null,
        })),
      SELECTORS.services,
    );
  } finally {
    await page.close();
  }
}
