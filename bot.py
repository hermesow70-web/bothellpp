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

# ========== ТВОИ ДАННЫЕ ==========
BOT_TOKEN = "8678152372:AAHEqZ5Lxe6CsSZpX0loPyOioejOFYCTtoI"
OWNER_ID = 8402407852
OWNER_TAG = "#крип"
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
        return {}

def save_data(filename: str, data):
    with open(DATA_DIR / f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== ДАННЫЕ ==========
users = load_data("users")
admins = load_data("admins")
banlist = load_data("banlist")

# Добавляем владельца в админы
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
    save_data("banlist", banlist)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def is_admin(user_id: int) -> bool:
    return str(user_id) in admins

def is_gl_admin(user_id: int) -> bool:
    if str(user_id) not in admins:
        return False
    return admins[str(user_id)].get("role") == "ГЛ.АДМИН"

def is_banned(user_id: int) -> bool:
    return str(user_id) in banlist

def get_user_name(user_id: int) -> str:
    return users.get(str(user_id), {}).get("name", "Пользователь")

# ========== КОМАНДА СТАРТ ==========
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    # Регистрируем пользователя
    if str(user_id) not in users:
        users[str(user_id)] = {
            "name": message.from_user.full_name,
            "username": message.from_user.username,
            "date": datetime.now().isoformat()
        }
        save_all()
    
    await message.answer(
        "👋 Добро пожаловать!\n"
        "Используйте /help для списка команд."
    )

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    
    if is_admin(user_id):
        text = (
            "👑 **Команды администратора:**\n\n"
            "`/admin` - список команд админа\n"
        )
    else:
        text = "👋 /start - начать работу"
    
    await message.answer(text)

# ========== КОМАНДЫ ДЛЯ АДМИНОВ ==========
@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав.")
        return
    
    text = (
        "👑 **Команды администратора:**\n\n"
        "`/list` - список всех пользователей\n"
        "`/adlist` - список всех админов\n"
    )
    
    if is_gl_admin(user_id) or user_id == OWNER_ID:
        text += (
            "\n👑 **Команды ГЛ.АДМИНА:**\n\n"
            "`/setadmin [ID] [тег] [роль]` - выдать админку\n"
            "   Роли: `АДМИН` или `ГЛ.АДМИН`\n"
            "   Пример: `/setadmin 123456789 #дил АДМИН`\n\n"
            "`/deladmin [ID]` - снять админа\n"
            "`/ban [ID] [причина]` - забанить пользователя\n"
            "`/unban [ID]` - разбанить\n"
            "`/all [текст]` - рассылка всем"
        )
    
    await message.answer(text, parse_mode="Markdown")

# ========== ВЫДАТЬ АДМИНКУ ==========
@dp.message_handler(commands=['setadmin'])
async def cmd_setadmin(message: types.Message):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Нет прав.")
        return
    
    args = message.get_args().split()
    if len(args) < 3:
        await message.answer("❌ Использование: /setadmin [ID] [тег] [роль]")
        return
    
    target_id, tag, role = args[0], args[1], args[2].upper()
    
    if role not in ["АДМИН", "ГЛ.АДМИН"]:
        await message.answer("❌ Роль должна быть АДМИН или ГЛ.АДМИН")
        return
    
    if target_id not in users:
        await message.answer("❌ Пользователь не найден.")
        return
    
    admins[target_id] = {
        "tag": tag if tag.startswith("#") else f"#{tag}",
        "role": role,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Админка выдана!\nID: {target_id}\nТег: {tag}\nРоль: {role}")

# ========== УДАЛИТЬ АДМИНА ==========
@dp.message_handler(commands=['deladmin'])
async def cmd_deladmin(message: types.Message):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Нет прав.")
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /deladmin [ID]")
        return
    
    target_id = args[0]
    
    if target_id not in admins:
        await message.answer("❌ Админ не найден.")
        return
    
    if target_id == str(OWNER_ID):
        await message.answer("❌ Нельзя удалить владельца.")
        return
    
    tag = admins[target_id]["tag"]
    del admins[target_id]
    save_all()
    
    await message.answer(f"✅ Админ {target_id} ({tag}) удалён.")

# ========== СПИСОК АДМИНОВ ==========
@dp.message_handler(commands=['adlist'])
async def cmd_adlist(message: types.Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ Нет прав.")
        return
    
    if not admins:
        await message.answer("📭 Нет админов.")
        return
    
    text = "👑 **Список администраторов:**\n\n"
    for uid, data in admins.items():
        user_data = users.get(uid, {})
        name = user_data.get("name", "Неизвестно")
        text += f"👤 {name} | {data['tag']} | {data['role']} | ID: {uid}\n"
    
    await message.answer(text)

# ========== СПИСОК ПОЛЬЗОВАТЕЛЕЙ ==========
@dp.message_handler(commands=['list'])
async def cmd_list(message: types.Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ Нет прав.")
        return
    
    if not users:
        await message.answer("📭 Нет пользователей.")
        return
    
    text = "📋 **Все пользователи:**\n\n"
    for uid, data in list(users.items())[:50]:
        name = data.get("name", "Неизвестно")
        username = data.get("username", "")
        username_str = f"(@{username})" if username else ""
        banned = " 🔴 ЗАБАНЕН" if uid in banlist else ""
        text += f"👤 {name} {username_str} | ID: {uid}{banned}\n"
    
    await message.answer(text)

# ========== БАН ==========
@dp.message_handler(commands=['ban'])
async def cmd_ban(message: types.Message):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Нет прав.")
        return
    
    text = message.get_args()
    if not text:
        await message.answer("❌ Использование: /ban [ID] [причина]")
        return
    
    parts = text.split(maxsplit=1)
    target_id = parts[0]
    reason = parts[1] if len(parts) > 1 else "Без причины"
    
    if target_id not in users:
        await message.answer("❌ Пользователь не найден.")
        return
    
    if target_id in admins:
        await message.answer("❌ Нельзя забанить админа.")
        return
    
    banlist[target_id] = {
        "reason": reason,
        "date": datetime.now().isoformat(),
        "banned_by": user_id
    }
    save_all()
    
    await message.answer(f"✅ Пользователь {target_id} забанен.\nПричина: {reason}")

# ========== РАЗБАН ==========
@dp.message_handler(commands=['unban'])
async def cmd_unban(message: types.Message):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Нет прав.")
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /unban [ID]")
        return
    
    target_id = args[0]
    
    if target_id not in banlist:
        await message.answer("❌ Пользователь не в бане.")
        return
    
    del banlist[target_id]
    save_all()
    
    await message.answer(f"✅ Пользователь {target_id} разбанен.")

# ========== РАССЫЛКА ==========
@dp.message_handler(commands=['all'])
async def cmd_all(message: types.Message):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Нет прав.")
        return
    
    text = message.get_args()
    if not text:
        await message.answer("❌ Использование: /all [текст]")
        return
    
    await message.answer("⏳ Начинаю рассылку...")
    
    sent = 0
    failed = 0
    
    for uid in users.keys():
        if uid in banlist:
            failed += 1
            continue
        
        try:
            await bot.send_message(int(uid), text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await message.answer(f"✅ Рассылка завершена!\nОтправлено: {sent}\nНе доставлено: {failed}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("БОТ ЗАПУЩЕН")
    logger.info(f"Владелец: {OWNER_ID}")
    logger.info(f"Админов: {len(admins)}")
    logger.info(f"Пользователей: {len(users)}")
    logger.info("=" * 50)
    
    executor.start_polling(dp, skip_updates=True)
