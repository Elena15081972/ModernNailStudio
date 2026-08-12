import "dotenv/config";

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var ${name}. Copy .env.example to .env and fill it in.`);
  }
  return value;
}

export const config = {
  telegramToken: required("TELEGRAM_TOKEN"),
  telegramChatId: required("TELEGRAM_CHAT_ID"),
  anthropicApiKey: required("ANTHROPIC_API_KEY"),
  model: process.env.ANTHROPIC_MODEL || "claude-sonnet-5",
};
