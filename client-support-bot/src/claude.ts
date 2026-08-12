import Anthropic from "@anthropic-ai/sdk";
import { config } from "./config.js";
import { callDikidiTool, listDikidiTools } from "./dikidiMcp.js";
import { systemPrompt } from "./knowledgeBase.js";

const client = new Anthropic({ apiKey: config.anthropicApiKey });

// Ограничивает число обращений к инструментам за один ответ клиенту —
// без этого сбой в цикле tool-use мог бы уйти в бесконечный опрос DIKIDI.
const MAX_TOOL_ROUNDS = 4;

function todayInTomsk(): string {
  // Томск — UTC+7, отдельного идентификатора часового пояса в IANA для него
  // нет, но смещение совпадает с Asia/Krasnoyarsk.
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Krasnoyarsk" });
}

function extractText(content: Anthropic.ContentBlock[]): string {
  const textBlock = content.find((block) => block.type === "text");
  return textBlock?.type === "text" ? textBlock.text : "Не удалось сформировать ответ.";
}

export async function draftReply(question: string, platform: string): Promise<string> {
  const tools = await listDikidiTools();

  const messages: Anthropic.MessageParam[] = [
    {
      role: "user",
      content: `Сегодня: ${todayInTomsk()} (дата по времени Томска).\nПлощадка: ${platform}\n\nВопрос клиента:\n${question}`,
    },
  ];

  for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
    const response = await client.messages.create({
      model: config.model,
      max_tokens: 500,
      system: systemPrompt,
      tools: tools.length > 0 ? tools : undefined,
      messages,
    });

    if (response.stop_reason !== "tool_use") {
      return extractText(response.content);
    }

    messages.push({ role: "assistant", content: response.content });

    const toolResults: Anthropic.ToolResultBlockParam[] = [];
    for (const block of response.content) {
      if (block.type !== "tool_use") continue;
      try {
        const result = await callDikidiTool(block.name, block.input as Record<string, unknown>);
        toolResults.push({ type: "tool_result", tool_use_id: block.id, content: result });
      } catch (err) {
        toolResults.push({
          type: "tool_result",
          tool_use_id: block.id,
          content: `Ошибка при обращении к DIKIDI: ${err instanceof Error ? err.message : String(err)}`,
          is_error: true,
        });
      }
    }
    messages.push({ role: "user", content: toolResults });
  }

  return "Не удалось сформировать ответ — слишком много обращений к расписанию. Попробуй переформулировать вопрос.";
}
