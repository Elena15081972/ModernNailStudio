import { newPage } from "../browser/session.js";
import { config } from "../config.js";
import { SELECTORS } from "./selectors.js";
import type { Appointment } from "./types.js";

export async function listAppointments(
  dateFrom: string,
  dateTo: string,
  staffName?: string,
): Promise<Appointment[]> {
  const page = await newPage();
  try {
    await page.goto(new URL(SELECTORS.schedule.pageUrl, config.baseUrl).toString());
    await page.fill(SELECTORS.schedule.dateFromInput, dateFrom);
    await page.fill(SELECTORS.schedule.dateToInput, dateTo);
    if (staffName) {
      await page.selectOption(SELECTORS.schedule.staffFilter, { label: staffName });
    }
    await page.waitForSelector(SELECTORS.schedule.appointmentCard);

    return await page.$$eval(
      SELECTORS.schedule.appointmentCard,
      (cards, sel) =>
        cards.map((card) => ({
          time: card.querySelector(sel.appointmentTime)?.textContent?.trim() ?? "",
          clientName: card.querySelector(sel.appointmentClient)?.textContent?.trim() ?? "",
          service: card.querySelector(sel.appointmentService)?.textContent?.trim() ?? "",
          staffName: card.querySelector(sel.appointmentStaff)?.textContent?.trim() ?? "",
        })),
      SELECTORS.schedule,
    );
  } finally {
    await page.close();
  }
}
