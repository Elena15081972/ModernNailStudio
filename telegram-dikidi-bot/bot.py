"""Telegram-бот записи клиентов в DIKIDI Business.

Сценарий:
1. Клиент пишет свободным текстом: "Запиши меня на завтра на стрижку в 14:00, Елена".
2. Бот распознаёт дату и услугу, запрашивает у DIKIDI свободные окошки на этот день
   и показывает их кнопками (InlineKeyboardMarkup).
3. Клиент нажимает на удобное время.
4. Если это первое обращение — бот просит поделиться номером телефона (кнопка
   "Отправить контакт"), чтобы найти/создать клиента в DIKIDI.
5. Бот показывает итог записи и кнопки "Подтвердить" / "Отменить".
6. Только после нажатия "Подтвердить" запись реально создаётся в DIKIDI.

Запуск: см. README.md ("Установка и запуск").
"""

from __future__ import annotations

import logging
import re
from datetime import date

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import llm
import nlp
from config import config
from dikidi_client import DikidiAPIError, build_client
from models import PendingBooking, Service, TimeSlot
from storage import PhoneStorage

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO
)
logger = logging.getLogger("dikidi_bot")

SELECT_SERVICE, CHOOSING_SLOT, AWAITING_PHONE, CONFIRMING = range(4)

_PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{9,14}\d$")

MAX_SLOT_BUTTONS_PER_ROW = 4


def _services_keyboard(services: list[Service]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(s.name, callback_data=f"service:{i}") for i, s in enumerate(services)
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def _slots_keyboard(slots: list[TimeSlot]) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(s.time, callback_data=f"slot:{i}") for i, s in enumerate(slots)]
    rows = [
        buttons[i : i + MAX_SLOT_BUTTONS_PER_ROW]
        for i in range(0, len(buttons), MAX_SLOT_BUTTONS_PER_ROW)
    ]
    rows.append([InlineKeyboardButton("Отменить", callback_data="cancel_booking")])
    return InlineKeyboardMarkup(rows)


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data="confirm:yes"),
                InlineKeyboardButton("❌ Отменить", callback_data="confirm:no"),
            ]
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Здравствуйте! 💅 Мы — ногтевая студия: маникюр, педикюр, наращивание.\n\n"
        "Напишите, на какую услугу и день хотите записаться."
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data.pop("pending", None)
    context.chat_data.pop("pending_services", None)
    await update.message.reply_text("Хорошо, отменила запись.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    parsed = nlp.parse_booking_request(text)

    if parsed.day is None:
        reply = llm.draft_reply(text)
        await update.message.reply_text(reply)
        return ConversationHandler.END

    client_name = parsed.client_name or update.effective_user.first_name or "Клиент"

    dikidi = context.bot_data["dikidi"]
    try:
        services = dikidi.list_services()
    except DikidiAPIError as exc:
        logger.exception("Не удалось получить список услуг DIKIDI")
        await update.message.reply_text(f"Не получилось связаться с DIKIDI: {exc}")
        return ConversationHandler.END

    service = nlp.extract_service(text, services)
    if service is None:
        context.chat_data["pending_ctx"] = {
            "day": parsed.day,
            "client_name": client_name,
            "services": services,
        }
        await update.message.reply_text(
            "Не поняла, на какую услугу записать. Выберите, пожалуйста:",
            reply_markup=_services_keyboard(services),
        )
        return SELECT_SERVICE

    return await _offer_slots(update, context, day=parsed.day, service=service, client_name=client_name)


async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    ctx = context.chat_data.get("pending_ctx")
    if not ctx:
        await query.edit_message_text("Сессия устарела, напишите запрос ещё раз.")
        return ConversationHandler.END

    idx = int(query.data.split(":", 1)[1])
    service = ctx["services"][idx]

    return await _offer_slots(
        update, context, day=ctx["day"], service=service, client_name=ctx["client_name"], edit=True
    )


async def _offer_slots(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    day: date,
    service: Service,
    client_name: str,
    edit: bool = False,
) -> int:
    dikidi = context.bot_data["dikidi"]

    try:
        staff_list = dikidi.list_staff(service.id)
        slots_by_time: dict[str, TimeSlot] = {}
        for staff in staff_list:
            for slot in dikidi.get_free_slots(day, service.id, staff.id):
                slots_by_time.setdefault(slot.time, slot)
    except DikidiAPIError as exc:
        logger.exception("Не удалось получить свободные слоты DIKIDI")
        text = f"Не получилось получить свободное время из DIKIDI: {exc}"
        await _reply(update, edit, text)
        return ConversationHandler.END

    slots = sorted(slots_by_time.values(), key=lambda s: s.time)

    if not slots:
        text = (
            f"На {day.strftime('%d.%m.%Y')} свободных окошек на «{service.name}» не нашла. "
            "Попробуйте другой день."
        )
        await _reply(update, edit, text)
        return ConversationHandler.END

    context.chat_data["pending"] = PendingBooking(
        day=day, service=service, client_name=client_name, slots=slots
    )

    text = (
        f"Свободное время на «{service.name}» на {day.strftime('%d.%m.%Y')}:\n"
        "выберите удобное:"
    )
    await _reply(update, edit, text, markup=_slots_keyboard(slots))
    return CHOOSING_SLOT


async def _reply(update: Update, edit: bool, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


async def choose_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    pending: PendingBooking | None = context.chat_data.get("pending")
    if pending is None:
        await query.edit_message_text("Сессия устарела, напишите запрос ещё раз.")
        return ConversationHandler.END

    idx = int(query.data.split(":", 1)[1])
    pending.chosen_slot = pending.slots[idx]

    await query.edit_message_text(
        f"Выбрано время {pending.chosen_slot.time} (мастер: {pending.chosen_slot.staff_name})."
    )

    storage: PhoneStorage = context.bot_data["storage"]
    known_phone = storage.get_phone(update.effective_user.id)
    if known_phone:
        pending.phone = known_phone
        await update.effective_chat.send_message(
            _confirmation_text(pending), reply_markup=_confirm_keyboard()
        )
        return CONFIRMING

    contact_button = KeyboardButton("Отправить номер телефона", request_contact=True)
    await update.effective_chat.send_message(
        "Чтобы оформить запись, поделитесь, пожалуйста, номером телефона "
        "(кнопкой ниже или введите текстом).",
        reply_markup=ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True),
    )
    return AWAITING_PHONE


async def cancel_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.chat_data.pop("pending", None)
    await query.edit_message_text("Хорошо, отменила запись.")
    return ConversationHandler.END


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.contact.phone_number
    return await _save_phone_and_confirm(update, context, phone)


async def receive_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not _PHONE_RE.match(text):
        await update.message.reply_text(
            "Похоже, это не номер телефона. Отправьте его в формате +79991234567 "
            "или нажмите кнопку «Отправить номер телефона»."
        )
        return AWAITING_PHONE
    return await _save_phone_and_confirm(update, context, text)


async def _save_phone_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str) -> int:
    pending: PendingBooking | None = context.chat_data.get("pending")
    if pending is None:
        await update.message.reply_text(
            "Сессия устарела, напишите запрос ещё раз.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    pending.phone = phone
    storage: PhoneStorage = context.bot_data["storage"]
    storage.save_phone(update.effective_user.id, pending.client_name, phone)

    await update.message.reply_text(
        _confirmation_text(pending), reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text("Всё верно?", reply_markup=_confirm_keyboard())
    return CONFIRMING


def _confirmation_text(pending: PendingBooking) -> str:
    slot = pending.chosen_slot
    return (
        "Проверьте запись:\n"
        f"Услуга: {pending.service.name}\n"
        f"Дата: {pending.day.strftime('%d.%m.%Y')}\n"
        f"Время: {slot.time}\n"
        f"Мастер: {slot.staff_name}\n"
        f"Клиент: {pending.client_name}\n"
        f"Телефон: {pending.phone}"
    )


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm:no":
        context.chat_data.pop("pending", None)
        await query.edit_message_text("Запись отменена.")
        return ConversationHandler.END

    pending: PendingBooking | None = context.chat_data.get("pending")
    if pending is None or pending.chosen_slot is None or pending.phone is None:
        await query.edit_message_text("Сессия устарела, напишите запрос ещё раз.")
        return ConversationHandler.END

    dikidi = context.bot_data["dikidi"]
    try:
        client_id = dikidi.find_or_create_client(pending.client_name, pending.phone)
        result = dikidi.create_appointment(
            day=pending.day,
            time=pending.chosen_slot.time,
            service_id=pending.service.id,
            staff_id=pending.chosen_slot.staff_id,
            client_id=client_id,
        )
        await query.edit_message_text(f"Готово! {result}")
    except DikidiAPIError as exc:
        logger.exception("Не удалось создать запись в DIKIDI")
        await query.edit_message_text(
            f"Не получилось создать запись в DIKIDI: {exc}\n"
            "Попробуйте ещё раз чуть позже или напишите нам напрямую."
        )

    context.chat_data.pop("pending", None)
    return ConversationHandler.END


def build_application() -> Application:
    application = Application.builder().token(config.telegram_token).build()
    application.bot_data["dikidi"] = build_client(config)
    application.bot_data["storage"] = PhoneStorage(config.storage_path)

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            SELECT_SERVICE: [CallbackQueryHandler(select_service, pattern=r"^service:\d+$")],
            CHOOSING_SLOT: [
                CallbackQueryHandler(choose_slot, pattern=r"^slot:\d+$"),
                CallbackQueryHandler(cancel_booking_callback, pattern=r"^cancel_booking$"),
            ],
            AWAITING_PHONE: [
                MessageHandler(filters.CONTACT, receive_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone_text),
            ],
            CONFIRMING: [CallbackQueryHandler(confirm_booking, pattern=r"^confirm:(yes|no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    return application


def main() -> None:
    application = build_application()
    logger.info("Бот запущен в режиме DIKIDI_MODE=%s", config.dikidi_mode)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
