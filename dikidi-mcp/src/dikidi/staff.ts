import { newPage } from "../browser/session.js";
import { config } from "../config.js";
import { SELECTORS } from "./selectors.js";
import type { StaffMember } from "./types.js";

export async function listStaff(): Promise<StaffMember[]> {
  const page = await newPage();
  try {
    await page.goto(new URL(SELECTORS.staff.pageUrl, config.baseUrl).toString());
    await page.waitForSelector(SELECTORS.staff.row);

    return await page.$$eval(
      SELECTORS.staff.row,
      (rows, sel) =>
        rows.map((row) => ({
          name: row.querySelector(sel.name)?.textContent?.trim() ?? "",
          role: row.querySelector(sel.role)?.textContent?.trim() ?? null,
        })),
      SELECTORS.staff,
    );
  } finally {
    await page.close();
  }
}
