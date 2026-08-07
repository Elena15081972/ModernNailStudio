import { newPage } from "../browser/session.js";
import { config } from "../config.js";
import { SELECTORS } from "./selectors.js";
import type { Client } from "./types.js";

export async function listClients(search?: string): Promise<Client[]> {
  const page = await newPage();
  try {
    await page.goto(new URL(SELECTORS.clients.pageUrl, config.baseUrl).toString());

    if (search) {
      await page.fill(SELECTORS.clients.searchInput, search);
      await page.keyboard.press("Enter");
    }
    await page.waitForSelector(SELECTORS.clients.row);

    return await page.$$eval(
      SELECTORS.clients.row,
      (rows, sel) =>
        rows.map((row) => ({
          name: row.querySelector(sel.name)?.textContent?.trim() ?? "",
          phone: row.querySelector(sel.phone)?.textContent?.trim() ?? null,
        })),
      SELECTORS.clients,
    );
  } finally {
    await page.close();
  }
}
