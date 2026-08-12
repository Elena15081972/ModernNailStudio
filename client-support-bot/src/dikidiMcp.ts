import { existsSync } from "node:fs";
import { join } from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type Anthropic from "@anthropic-ai/sdk";
import { config } from "./config.js";

// Агенту разрешено только читать расписание, чтобы проверять реальные
// свободные окошки. Создание записей (dikidi_create_appointment) и поиск
// клиентов (dikidi_list_clients) сюда сознательно не включены — по ТЗ
// агент только консультирует и направляет на запись, а не бронирует сам.
const ALLOWED_TOOLS = new Set(["dikidi_get_schedule"]);

let clientPromise: Promise<Client | null> | null = null;

function connect(): Promise<Client | null> {
  if (!clientPromise) {
    clientPromise = doConnect();
  }
  return clientPromise;
}

async function doConnect(): Promise<Client | null> {
  const scriptPath = join(config.dikidiMcpDir, "dist", "index.js");
  if (!existsSync(scriptPath)) {
    console.warn(
      `dikidi-mcp не собран (нет ${scriptPath}) — бот продолжит работать без проверки расписания.`,
    );
    return null;
  }

  try {
    const transport = new StdioClientTransport({
      command: "node",
      args: [scriptPath],
      cwd: config.dikidiMcpDir,
    });
    const mcpClient = new Client({ name: "client-support-bot", version: "0.1.0" });
    await mcpClient.connect(transport);
    return mcpClient;
  } catch (err) {
    console.warn("Не удалось подключиться к dikidi-mcp — работаю без проверки расписания.", err);
    return null;
  }
}

export async function listDikidiTools(): Promise<Anthropic.Tool[]> {
  const client = await connect();
  if (!client) return [];

  try {
    const { tools } = await client.listTools();
    return tools
      .filter((tool) => ALLOWED_TOOLS.has(tool.name))
      .map((tool) => ({
        name: tool.name,
        description: tool.description,
        input_schema: tool.inputSchema as Anthropic.Tool.InputSchema,
      }));
  } catch (err) {
    console.warn("Не удалось получить список инструментов dikidi-mcp.", err);
    return [];
  }
}

export async function callDikidiTool(name: string, args: Record<string, unknown>): Promise<string> {
  if (!ALLOWED_TOOLS.has(name)) {
    throw new Error(`Инструмент ${name} недоступен для этого агента.`);
  }

  const client = await connect();
  if (!client) {
    throw new Error("dikidi-mcp недоступен.");
  }

  const result = await client.callTool({ name, arguments: args });
  const blocks = Array.isArray(result.content) ? result.content : [];
  const text = blocks
    .filter((block): block is { type: "text"; text: string } => block.type === "text")
    .map((block) => block.text)
    .join("\n");

  if (result.isError) {
    throw new Error(text || `Ошибка при вызове ${name}.`);
  }

  return text || "Пустой ответ от dikidi-mcp.";
}
