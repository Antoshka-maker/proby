"""Telegram-бот для приёма заявок (aiogram 3).

Сценарий: меню -> имя -> телефон -> описание задачи -> подтверждение.
Заявка сохраняется в SQLite и пересылается администратору.
Настройки берутся из файла .env: BOT_TOKEN и ADMIN_CHAT_ID.
"""
import asyncio
import html
import logging
import os
import re
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
DB_PATH = os.environ.get("DB_PATH", "requests.db")

BTN_NEW = "📝 Оставить заявку"
BTN_FAQ = "❓ Частые вопросы"
BTN_CONTACTS = "📞 Контакты"
BTN_CANCEL = "✖️ Отмена"
BTN_SEND = "✅ Отправить"
BTN_RESTART = "🔄 Заполнить заново"

FAQ_TEXT = (
    "<b>Частые вопросы</b>\n\n"
    "<b>Как быстро вы отвечаете?</b>\nВ рабочее время в течение часа.\n\n"
    "<b>Сколько стоит консультация?</b>\nПервая консультация бесплатная.\n\n"
    "<b>Как оплатить?</b>\nКартой или по счёту после согласования работ."
)
CONTACTS_TEXT = (
    "<b>Контакты</b>\n\nТелефон: +7 (900) 000-00-00\nПочта: hello@example.com\n"
    "Работаем по будням с 10:00 до 19:00."
)

router = Router()


class Form(StatesGroup):
    name = State()
    phone = State()
    task = State()
    confirm = State()


def keyboard(*rows: list[KeyboardButton | str]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[b if isinstance(b, KeyboardButton) else KeyboardButton(text=b) for b in row] for row in rows],
        resize_keyboard=True,
    )


MAIN_MENU = keyboard([BTN_NEW], [BTN_FAQ, BTN_CONTACTS])
CANCEL_MENU = keyboard([BTN_CANCEL])


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT, user_id INTEGER, username TEXT,
                name TEXT, phone TEXT, task TEXT
            )"""
        )


def save_request(user_id: int, username: str | None, data: dict) -> int:
    with sqlite3.connect(DB_PATH) as db:
        cursor = db.execute(
            "INSERT INTO requests (created_at, user_id, username, name, phone, task) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), user_id, username, data["name"], data["phone"], data["task"]),
        )
        return cursor.lastrowid


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        f"Здравствуйте, {html.escape(message.from_user.first_name)}!\n"
        "Я принимаю заявки и отвечаю на частые вопросы. Выберите действие в меню.",
        reply_markup=MAIN_MENU,
    )


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Заявка отменена. Вы в главном меню.", reply_markup=MAIN_MENU)


@router.message(F.text == BTN_FAQ)
async def faq(message: Message) -> None:
    await message.answer(FAQ_TEXT)


@router.message(F.text == BTN_CONTACTS)
async def contacts(message: Message) -> None:
    await message.answer(CONTACTS_TEXT)


@router.message(F.text.in_({BTN_NEW, BTN_RESTART}))
async def new_request(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.name)
    await message.answer("Шаг 1 из 3. Как к вам обращаться?", reply_markup=CANCEL_MENU)


@router.message(Form.name, F.text)
async def get_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not 2 <= len(name) <= 60:
        await message.answer("Напишите имя от 2 до 60 символов.")
        return
    await state.update_data(name=name)
    await state.set_state(Form.phone)
    await message.answer(
        "Шаг 2 из 3. Отправьте номер телефона кнопкой ниже или напишите его текстом.",
        reply_markup=keyboard([KeyboardButton(text="📱 Отправить мой номер", request_contact=True)], [BTN_CANCEL]),
    )


@router.message(Form.phone, F.contact | F.text)
async def get_phone(message: Message, state: FSMContext) -> None:
    raw = message.contact.phone_number if message.contact else message.text
    digits = re.sub(r"\D", "", raw)
    if not 10 <= len(digits) <= 15:
        await message.answer("Не похоже на номер телефона. Пример: +7 900 123-45-67")
        return
    await state.update_data(phone="+" + digits)
    await state.set_state(Form.task)
    await message.answer("Шаг 3 из 3. Коротко опишите вашу задачу.", reply_markup=CANCEL_MENU)


@router.message(Form.task, F.text)
async def get_task(message: Message, state: FSMContext) -> None:
    task = message.text.strip()
    if len(task) < 10:
        await message.answer("Опишите задачу чуть подробнее, хотя бы в одном предложении.")
        return
    data = await state.update_data(task=task[:1000])
    await state.set_state(Form.confirm)
    await message.answer(
        "<b>Проверьте заявку</b>\n\n"
        f"Имя: {html.escape(data['name'])}\n"
        f"Телефон: {data['phone']}\n"
        f"Задача: {html.escape(data['task'])}",
        reply_markup=keyboard([BTN_SEND], [BTN_RESTART, BTN_CANCEL]),
    )


@router.message(Form.confirm, F.text == BTN_SEND)
async def confirm(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    user = message.from_user
    request_id = save_request(user.id, user.username, data)
    await message.answer(
        f"Спасибо! Заявка №{request_id} принята. Мы свяжемся с вами в ближайшее время.",
        reply_markup=MAIN_MENU,
    )
    if ADMIN_CHAT_ID:
        author = f"@{user.username}" if user.username else f"id {user.id}"
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🔔 <b>Новая заявка №{request_id}</b>\n\n"
            f"Имя: {html.escape(data['name'])}\n"
            f"Телефон: {data['phone']}\n"
            f"Задача: {html.escape(data['task'])}\n"
            f"От: {author}",
        )


@router.message(Command("id"))
async def chat_id(message: Message) -> None:
    await message.answer(f"ID этого чата: <code>{message.chat.id}</code>")


@router.message()
async def fallback(message: Message, state: FSMContext) -> None:
    if await state.get_state():
        await message.answer("Пожалуйста, ответьте на вопрос выше или нажмите «Отмена».")
    else:
        await message.answer("Я не понял сообщение. Выберите действие в меню.", reply_markup=MAIN_MENU)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
    init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
