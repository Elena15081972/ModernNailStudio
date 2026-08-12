import { Telegraf, type Context } from "telegraf";
import { config } from "./config.js";
import { draftReply } from "./claude.js";

const bot = new Telegraf(config.telegramToken);

function isOwner(chatId: number): boolean {
  return String(chatId) === config.telegramChatId;
}

bot.start((ctx) => {
  if (!isOwner(ctx.chat.id)) return;
  ctx.reply(
    "Привет! Пришли вопрос клиента текстом — верну готовый ответ для отправки.\n\n" +
      "Если вопрос пришёл с Авито (там нельзя сразу давать ссылки), начни команду с /avito, например:\n" +
      "/avito Сколько стоит маникюр?",
  );
});

bot.command("avito", async (ctx) => {
  if (!isOwner(ctx.chat.id)) return;
  const question = ctx.message.text.replace(/^\/avito(@\w+)?\s*/i, "").trim();
  if (!question) {
    await ctx.reply("После команды напиши вопрос клиента, например:\n/avito Сколько стоит маникюр?");
    return;
  }
  await respond(ctx, question, "Авито");
});

bot.on("text", async (ctx) => {
  if (!isOwner(ctx.chat.id)) return;
  await respond(ctx, ctx.message.text, "ВКонтакте/WhatsApp/Telegram/сайт");
});

async function respond(ctx: Context, question: string, platform: string) {
  await ctx.sendChatAction("typing");
  try {
    const answer = await draftReply(question, platform);
    await ctx.reply(answer);
  } catch (err) {
    console.error("Ошибка при обращении к Claude API:", err);
    await ctx.reply("Не получилось получить ответ от Claude. Проверь логи бота.");
  }
}

bot.launch();
console.log("client-support-bot запущен");

process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
