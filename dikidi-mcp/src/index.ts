#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { closeBrowser } from "./browser/session.js";
import { createAppointment } from "./dikidi/appointments.js";
import { listClients } from "./dikidi/clients.js";
import { listAppointments } from "./dikidi/schedule.js";
import { listServices } from "./dikidi/services.js";
import { listStaff } from "./dikidi/staff.js";

const server = new McpServer({ name: "dikidi-mcp", version: "0.1.0" });

server.registerTool(
  "dikidi_list_services",
  {
    title: "List DIKIDI services",
    description: "Возвращает список услуг салона (название, категория, цена, длительность) из DIKIDI Business.",
    inputSchema: {},
  },
  async () => ({
    content: [{ type: "text", text: JSON.stringify(await listServices(), null, 2) }],
  }),
);

server.registerTool(
  "dikidi_list_staff",
  {
    title: "List DIKIDI staff",
    description: "Возвращает список сотрудников/мастеров салона из DIKIDI Business.",
    inputSchema: {},
  },
  async () => ({
    content: [{ type: "text", text: JSON.stringify(await listStaff(), null, 2) }],
  }),
);

server.registerTool(
  "dikidi_list_clients",
  {
    title: "Search DIKIDI clients",
    description: "Ищет клиентов салона по имени или телефону в DIKIDI Business.",
    inputSchema: {
      search: z.string().optional().describe("Строка поиска по имени или телефону"),
    },
  },
  async ({ search }) => ({
    content: [{ type: "text", text: JSON.stringify(await listClients(search), null, 2) }],
  }),
);

server.registerTool(
  "dikidi_get_schedule",
  {
    title: "Get DIKIDI schedule",
    description: "Возвращает записи клиентов за период из журнала записей DIKIDI Business.",
    inputSchema: {
      dateFrom: z.string().describe("Дата начала периода, YYYY-MM-DD"),
      dateTo: z.string().describe("Дата конца периода, YYYY-MM-DD"),
      staffName: z.string().optional().describe("Фильтр по точному имени мастера"),
    },
  },
  async ({ dateFrom, dateTo, staffName }) => ({
    content: [
      { type: "text", text: JSON.stringify(await listAppointments(dateFrom, dateTo, staffName), null, 2) },
    ],
  }),
);

server.registerTool(
  "dikidi_create_appointment",
  {
    title: "Create a DIKIDI appointment",
    description:
      "Создаёт новую запись клиента в DIKIDI Business. Только создание — отмена и перенос записей этим инструментом не поддерживаются.",
    inputSchema: {
      date: z.string().describe("Дата записи, YYYY-MM-DD"),
      time: z.string().describe("Время записи, HH:mm"),
      serviceName: z.string().describe("Точное название услуги, как оно указано в DIKIDI"),
      staffName: z.string().describe("Точное имя мастера, как оно указано в DIKIDI"),
      clientName: z.string().describe("Имя клиента"),
      clientPhone: z.string().describe("Телефон клиента"),
    },
  },
  async (input) => {
    const result = await createAppointment(input);
    return {
      content: [{ type: "text", text: result.message }],
      isError: !result.success,
    };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);

for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, async () => {
    await closeBrowser();
    process.exit(0);
  });
}
