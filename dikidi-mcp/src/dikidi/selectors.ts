/**
 * Every value here is a PLACEHOLDER guess, not a verified DIKIDI selector — this repo was
 * built without access to a logged-in DIKIDI Business account. Record real selectors with
 * `npm run login:dev` (see README "Calibrating selectors") and replace the strings below.
 */
export const SELECTORS = {
  login: {
    emailOrPhoneInput: 'input[name="login"]',
    passwordInput: 'input[name="password"]',
    submitButton: 'button[type="submit"]',
    // An element only present once the dashboard has loaded, used to detect a successful login.
    loggedInMarker: '[data-testid="main-nav"], nav',
  },
  services: {
    pageUrl: "/ru/owner/services/",
    row: "table.company-services-table tbody > tr[id]",
    name: "td.value a",
    // DIKIDI doesn't expose a category per row in this table (only as a filter dropdown) — no matching selector.
    category: ".service-category",
    price: "td.prices",
    durationMinutes: "td.duration",
  },
  staff: {
    pageUrl: "/settings/employees",
    row: ".employee-list__item, tr.employee-row",
    name: ".employee-name",
    role: ".employee-role",
  },
  clients: {
    pageUrl: "/clients",
    searchInput: 'input[type="search"], input[placeholder*="Поиск"]',
    row: ".client-list__item, tr.client-row",
    name: ".client-name",
    phone: ".client-phone",
  },
  schedule: {
    pageUrl: "/journal",
    dateFromInput: 'input[name="date_from"]',
    dateToInput: 'input[name="date_to"]',
    staffFilter: 'select[name="employee"]',
    appointmentCard: ".record-card, .appointment-card",
    appointmentTime: ".record-card__time",
    appointmentClient: ".record-card__client",
    appointmentService: ".record-card__service",
    appointmentStaff: ".record-card__employee",
  },
  createAppointment: {
    openButton: 'button:has-text("Добавить запись"), button:has-text("Новая запись")',
    serviceSelect: 'select[name="service"], [data-testid="service-select"]',
    staffSelect: 'select[name="employee"], [data-testid="employee-select"]',
    dateInput: 'input[name="date"]',
    timeSlot: (time: string) => `[data-time="${time}"]`,
    clientSearchInput: 'input[placeholder*="клиент" i]',
    newClientNameInput: 'input[name="client_name"]',
    newClientPhoneInput: 'input[name="client_phone"]',
    confirmButton: 'button:has-text("Записать"), button:has-text("Сохранить")',
    successToast: ".toast-success, .notification--success",
  },
};
