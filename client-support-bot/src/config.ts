import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import "dotenv/config";

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var ${name}. Copy .env.example to .env and fill it in.`);
  }
  return value;
}

// config.ts живёт в src/ (dev) или dist/ (build) — в обоих случаях на один
// уровень ниже корня пакета, а dikidi-mcp лежит рядом как соседняя папка.
const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultDikidiMcpDir = resolve(packageRoot, "..", "dikidi-mcp");

export const config = {
  telegramToken: required("TELEGRAM_TOKEN"),
  telegramChatId: required("TELEGRAM_CHAT_ID"),
  anthropicApiKey: required("ANTHROPIC_API_KEY"),
  model: process.env.ANTHROPIC_MODEL || "claude-sonnet-5",
  // Папка dikidi-mcp (для проверки реального расписания). Необязательно —
  // если сервер там не собран или не может подключиться, бот продолжит
  // работать без проверки расписания.
  dikidiMcpDir: process.env.DIKIDI_MCP_DIR
    ? resolve(process.env.DIKIDI_MCP_DIR)
    : defaultDikidiMcpDir,
};
