import { newPage } from "../browser/session.js";
import { config } from "../config.js";
import { SELECTORS } from "./selectors.js";
import type { CreateAppointmentInput, CreateAppointmentResult } from "./types.js";

export async function createAppointment(
  input: CreateAppointmentInput,
): Promise<CreateAppointmentResult> {
  const page = await newPage();
  try {
    await page.goto(new URL(SELECTORS.schedule.pageUrl, config.baseUrl).toString());
    await page.click(SELECTORS.createAppointment.openButton);

    await page.fill(SELECTORS.createAppointment.dateInput, input.date);
    await page.click(SELECTORS.createAppointment.timeSlot(input.time));

    await page.selectOption(SELECTORS.createAppointment.serviceSelect, { label: input.serviceName });
    await page.selectOption(SELECTORS.createAppointment.staffSelect, { label: input.staffName });

    await page.fill(SELECTORS.createAppointment.clientSearchInput, input.clientPhone);
    const existingClient = await page
      .waitForSelector(`text=${input.clientName}`, { timeout: 2000 })
      .then(() => true)
      .catch(() => false);

    if (existingClient) {
      await page.click(`text=${input.clientName}`);
    } else {
      await page.fill(SELECTORS.createAppointment.newClientNameInput, input.clientName);
      await page.fill(SELECTORS.createAppointment.newClientPhoneInput, input.clientPhone);
    }

    await page.click(SELECTORS.createAppointment.confirmButton);
    await page.waitForSelector(SELECTORS.createAppointment.successToast, { timeout: 10000 });

    return {
      success: true,
      message: `Запись создана: ${input.clientName} на «${input.serviceName}» ${input.date} ${input.time} (мастер: ${input.staffName})`,
    };
  } catch (err) {
    return { success: false, message: `Не удалось создать запись: ${(err as Error).message}` };
  } finally {
    await page.close();
  }
}
