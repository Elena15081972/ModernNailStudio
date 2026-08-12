import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// prompt.md живёт в корне пакета, а не в src/, чтобы базу знаний можно было
// править без пересборки TypeScript.
export const systemPrompt = readFileSync(join(__dirname, "..", "prompt.md"), "utf-8");
