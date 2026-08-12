import Anthropic from "@anthropic-ai/sdk";
import { config } from "./config.js";
import { systemPrompt } from "./knowledgeBase.js";

const client = new Anthropic({ apiKey: config.anthropicApiKey });

export async function draftReply(question: string, platform: string): Promise<string> {
  const message = await client.messages.create({
    model: config.model,
    max_tokens: 500,
    system: systemPrompt,
    messages: [
      {
        role: "user",
        content: `Площадка: ${platform}\n\nВопрос клиента:\n${question}`,
      },
    ],
  });

  const textBlock = message.content.find((block) => block.type === "text");
  return textBlock?.type === "text" ? textBlock.text : "Не удалось сформировать ответ.";
}
