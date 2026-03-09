#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import json
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== ТВОИ ДАННЫЕ ==========
BOT_TOKEN = "8678152372:AAHEqZ5Lxe6CsSZpX0loPyOioejOFYCTtoI"
OWNER_ID = 8402407852
OWNER_TAG = "#крип"
CHANNEL_LINK = "https://t.me/+arKuZnc9R9hhNDIx"
# =================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ========== РАБОТА С ФАЙЛАМИ ==========
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def load_data(filename: str):
    try:
        with open(DATA_DIR / f"{filename}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if filename == "queue":
            return []
        return {}

def save_data(filename: str, data):
    with open(DATA_DIR / f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== ДАННЫЕ ==========
users = load_data("users")
admins = load_data("admins")
dialogs = load_data("dialogs")
waiting_queue = load_data("queue")
pending_by_tag = load_data("pending_by_tag")
banlist = load_data("banlist")
complaints = load_data("complaints")

# Добавляем владельца как ГЛ.АДМИН
if str(OWNER_ID) not in admins:
    admins[str(OWNER_ID)] = {
        "tag": OWNER_TAG,
        "role": "ГЛ.АДМИН",
        "date": datetime.now().isoformat()
    }
    save_data("admins", admins)

def save_all():
    save_data("users", users)
    save_data("admins", admins)
    save_data("dialogs", dialogs)
    save_data("queue", waiting_queue)
    save_data("pending_by_tag", pending_by_tag)
    save_data("banlist", banlist)
    save_data("complaints", complaints)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом (любая роль)"""
    return str(user_id) in admins

def is_gl_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь ГЛ.АДМИНОМ"""
    if str(user_id) not in admins:
        return False
    return admins[str(user_id)].get("role") == "ГЛ.АДМИН"

def is_owner(user_id: int) -> bool:
    """Проверка, является ли пользователь владельцем"""
    return user_id == OWNER_ID

def is_banned(user_id: int) -> bool:
    """Проверка, забанен ли пользователь"""
    return str(user_id) in banlist

def get_user_name(user_id: int) -> str:
    """Получить имя пользователя"""
    return users.get(str(user_id), {}).get("name", "Пользователь")

def get_admin_tag(user_id: int) -> str:
    """Получить тег админа"""
    return admins.get(str(user_id), {}).get("tag", "#unknown")

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🎲 Позвать рандомно"))
    kb.add(types.KeyboardButton("🔍 Позвать админа (по тегу)"))
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📋 Список диалогов"))
    kb.add(types.KeyboardButton("👑 Админ-панель"))
    return kb

def dialog_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🔚 Завершить диалог"))
    return kb

def cancel_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Отмена"))
    return kb

def channel_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔔 Подписаться", url=CHANNEL_LINK))
    return kb

# ========== ОБРАБОТКА #КРИП ==========
@dp.message_handler(lambda message: message.text and message.text.startswith('#крип'))
async def handle_crip(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    complaint_id = str(len(complaints) + 1)
    complaints[complaint_id] = {
        "user_id": user_id,
        "user_name": get_user_name(user_id),
        "text": text,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(
        "✅ Ваша жалоба отправлена ГЛ.АДМИНАМ. Они рассмотрят ситуацию."
    )
    
    # Отправляем жалобу всем ГЛ.АДМИНАМ
    for aid, data in admins.items():
        if data.get("role") == "ГЛ.АДМИН" or int(aid) == OWNER_ID:
            try:
                await bot.send_message(
                    int(aid),
                    f"⚠️ **ЖАЛОБА**\n\n"
                    f"От: {get_user_name(user_id)} (ID: {user_id})\n"
                    f"Текст: {text}"
                )
            except:
                pass

# ========== КОМАНДА /START ==========
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    # Регистрируем нового пользователя
    if str(user_id) not in users:
        users[str(user_id)] = {
            "name": message.from_user.full_name,
            "username": message.from_user.username,
            "date": datetime.now().isoformat()
        }
        save_all()
        
        # Приветствие для новых пользователей
        await message.answer(
            "👋 *Здравствуй, хочешь тёплого общения? Внимания?*\n\n"
            "❌ *ЗАБУДЬ ДРУГИХ БОТОВ!*\n"
            "✅ *У нас всё по другому, хороший функционал и без ответа ты точно не останешься!*\n\n"
            "🔐 *У НАС НИКТО НЕ ВИДИТ ДИАЛОГИ, ПОЛНАЯ АНОНИМНОСТЬ*\n"
            "*(диалоги может посмотреть только владелец и то если будет жалоба)*\n\n"
            "✨ *ПРИЯТНОГО ВАМ ОБЩЕНИЯ!*",
            parse_mode="Markdown"
        )
        
        await message.answer(
            "Если не сложно подпишись на наш канал, это НЕОБЯЗАТЕЛЬНО но нам будет приятно)",
            reply_markup=channel_keyboard()
        )
    
    # Проверяем, есть ли активный диалог
    if str(user_id) in dialogs:
        admin_id = dialogs[str(user_id)]
        if admin_id not in admins:
            # Если админа больше нет, удаляем диалог
            del dialogs[str(user_id)]
            save_all()
        else:
            admin_tag = get_admin_tag(int(admin_id))
            await message.answer(
                f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
                reply_markup=dialog_menu()
            )
            return
    
    if is_admin(user_id):
        await message.answer("Меню администратора:", reply_markup=admin_menu())
    else:
        await message.answer("Выберите действие:", reply_markup=main_menu())

# ========== КОМАНДА /END ==========
@dp.message_handler(commands=['end'])
async def cmd_end(message: types.Message):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    
    # Проверяем, есть ли пользователь в диалоге как пользователь
    if user_id_str in dialogs:
        admin_id = int(dialogs[user_id_str])
        del dialogs[user_id_str]
        save_all()
        
        try:
            await bot.send_message(
                admin_id,
                "🔚 Пользователь завершил диалог.",
                reply_markup=admin_menu()
            )
        except:
            pass
        
        await message.answer(
            "✅ Диалог завершён.\n\n"
            "Если админ был к вам невежлив, груб или нарушил правила, "
            "напишите #крип и опишите ситуацию. Ваша жалоба будет рассмотрена."
        )
        
        if is_admin(user_id):
            await message.answer("Меню:", reply_markup=admin_menu())
        else:
            await message.answer("Главное меню:", reply_markup=main_menu())
        return
    
    # Проверяем, есть ли пользователь в диалоге как админ
    for uid, aid in dialogs.items():
        if aid == user_id_str:
            del dialogs[uid]
            save_all()
            
            try:
                await bot.send_message(
                    int(uid),
                    "🔚 Администратор завершил диалог.\n\n"
                    "Если админ был к вам невежлив, груб или нарушил правила, "
                    "напишите #крип и опишите ситуацию. Ваша жалоба будет рассмотрена."
                )
            except:
                pass
            
            await message.answer("✅ Диалог завершён.")
            await message.answer("Меню:", reply_markup=admin_menu())
            return
    
    await message.answer("❌ У вас нет активного диалога.")

# ========== ИМПОРТ И ПОДКЛЮЧЕНИЕ МОДУЛЕЙ ==========
from dialogs import register_handlers as register_dialog_handlers
from admin_panel import register_handlers as register_admin_handlers

# Регистрируем обработчики диалогов (для всех админов)
register_dialog_handlers(
    dp, bot,
    users, admins, dialogs, waiting_queue, pending_by_tag, save_all,
    is_admin, is_banned, get_user_name, get_admin_tag
)

# Регистрируем обработчики админ-панели (только для ГЛ.АДМИНОВ)
register_admin_handlers(
    dp, bot,
    users, admins, dialogs, banlist, save_all,
    is_admin, is_gl_admin, OWNER_ID
)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("БОТ ЗАПУЩЕН")
    logger.info(f"Владелец: {OWNER_ID}")
    logger.info(f"Админов: {len(admins)}")
    logger.info(f"Пользователей: {len(users)}")
    logger.info("=" * 50)
    
    executor.start_polling(dp, skip_updates=True)
