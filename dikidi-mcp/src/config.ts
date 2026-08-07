import "dotenv/config";

function required(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (!value) {
    throw new Error(`Missing required env var ${name}. Copy .env.example to .env and fill it in.`);
  }
  return value;
}

export const config = {
  loginUrl: required("DIKIDI_LOGIN_URL"),
  baseUrl: process.env.DIKIDI_BASE_URL ?? "https://web.dikidi.net",
  storageStatePath: process.env.DIKIDI_STORAGE_STATE_PATH ?? "./.dikidi-session.json",
  headless: (process.env.DIKIDI_HEADLESS ?? "true").toLowerCase() !== "false",
};
