#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SUPPORT HELPER BOT - ПОЛНАЯ ВЕРСИЯ СО ВСЕМИ РОЛЯМИ
Админ-панель: Выдать админку с выбором роли
Роли: АДМИН, ГЛ АДМИН, ТЕХ.СПЕЦИАЛИСТ, СОВЛАДЕЛЕЦ, ВЛАДЕЛЕЦ
"""

import asyncio
import logging
import json
import os
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils import executor

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

# Добавляем владельца в админы если его нет
if str(OWNER_ID) not in admins:
    admins[str(OWNER_ID)] = {
        "tag": OWNER_TAG,
        "role": "ВЛАДЕЛЕЦ",
        "issued_by": OWNER_ID,
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
    return str(user_id) in admins

def is_senior_admin(user_id: int) -> bool:
    if str(user_id) not in admins:
        return False
    role = admins[str(user_id)].get("role", "")
    return role in ["ГЛ АДМИН", "СОВЛАДЕЛЕЦ", "ВЛАДЕЛЕЦ"]

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_banned(user_id: int) -> bool:
    return str(user_id) in banlist

def get_user_name(user_id: int) -> str:
    return users.get(str(user_id), {}).get("name", "Пользователь")

def get_admin_tag(user_id: int) -> str:
    return admins.get(str(user_id), {}).get("tag", "#unknown")

def get_admin_role(user_id: int) -> str:
    return admins.get(str(user_id), {}).get("role", "АДМИН")

# ========== КЛАВИАТУРЫ ==========
def main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🎲 Позвать рандомно"))
    keyboard.add(KeyboardButton("🔍 Позвать админа (по тегу)"))
    return keyboard

def admin_menu(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🎲 Подключиться рандомно"))
    keyboard.add(KeyboardButton("🔍 Подключиться по тегу"))
    
    if is_senior_admin(user_id) or is_owner(user_id):
        keyboard.add(KeyboardButton("👑 Админ-панель"))
    
    return keyboard

def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📋 Список пользователей"))
    keyboard.add(KeyboardButton("📋 Список админов"))
    keyboard.add(KeyboardButton("➕ Выдать админку"))
    keyboard.add(KeyboardButton("➖ Удалить админа"))
    keyboard.add(KeyboardButton("🚫 Бан пользователя"))
    keyboard.add(KeyboardButton("✅ Разбан"))
    keyboard.add(KeyboardButton("📢 Рассылка"))
    keyboard.add(KeyboardButton("⚠️ Жалобы (#крип)"))
    keyboard.add(KeyboardButton("◀️ Назад"))
    return keyboard

def cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

def confirm_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("✅ Продолжить"))
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

def channel_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔔 Подписаться", url=CHANNEL_LINK))
    return keyboard

def dialog_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔚 Завершить диалог"))
    return keyboard

def role_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("АДМИН"))
    keyboard.add(KeyboardButton("ГЛ АДМИН"))
    keyboard.add(KeyboardButton("ТЕХ.СПЕЦИАЛИСТ"))
    keyboard.add(KeyboardButton("СОВЛАДЕЛЕЦ"))
    keyboard.add(KeyboardButton("ВЛАДЕЛЕЦ"))
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

# ========== КЛАССЫ СОСТОЯНИЙ ==========
class UserStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_admin_tag = State()
    in_dialog = State()
    waiting_for_complaint = State()

class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_tag = State()
    waiting_for_role = State()
    waiting_for_ban_reason = State()
    waiting_for_unban_user = State()
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_button = State()
    waiting_for_remove_admin_id = State()
    waiting_for_remove_admin_reason = State()
    in_dialog = State()  # ← ЭТО БЫЛО ПРОПУЩЕНО

# ========== ТАЙМЕР ДЛЯ ОЧЕРЕДИ ==========
async def queue_timeout(user_id: int):
    await asyncio.sleep(600)
    
    if str(user_id) in dialogs:
        return
    
    if user_id in waiting_queue:
        waiting_queue.remove(user_id)
        save_all()
        
        try:
            await bot.send_message(
                user_id,
                "⏰ Похоже, что все админы заняты.\n"
                "Попробуйте снова /start"
            )
        except:
            pass

# ========== СТАРТ ==========
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    await state.finish()
    
    if is_banned(user_id):
        await message.answer(
            f"❌ Вы забанены.\nПричина: {banlist[str(user_id)]['reason']}\n\n"
            f"Если вы считаете что наказание выдано просто так, напишите администраторам в канал"
        )
        return
    
    if str(user_id) in users:
        if str(user_id) in dialogs:
            admin_id = dialogs[str(user_id)]
            admin_tag = get_admin_tag(int(admin_id))
            await UserStates.in_dialog.set()
            await message.answer(
                f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
                reply_markup=dialog_keyboard()
            )
            return
        
        if is_admin(user_id):
            await message.answer(
                "Меню администратора:",
                reply_markup=admin_menu(user_id)
            )
        else:
            await message.answer(
                "Главное меню:",
                reply_markup=main_menu()
            )
        return
    
    await UserStates.waiting_for_name.set()
    
    await message.answer(
        "👋 Здравствуй, тебе нужна поддержка? Тебе грустно? ЗАБУДЬ ДРУГИХ БОТОВ!\n\n"
        "Наш совершенно другой, с отличным функционалом и без ответа ты точно не останешься! Мы ценим каждого пользователя!\n\n"
        "Извини что отвлекаю, можешь подписаться на наш канал, это необязательно, но мы будем рады)"
    )
    
    await message.answer("Подписка:", reply_markup=channel_keyboard())
    await message.answer("📝 Как вас зовут?")

@dp.message_handler(state=UserStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    
    users[str(user_id)] = {
        "name": name,
        "username": message.from_user.username,
        "registered": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Приятно познакомиться, {name}!")
    
    if is_admin(user_id):
        await message.answer(
            "Меню администратора:",
            reply_markup=admin_menu(user_id)
        )
    else:
        await message.answer(
            "Главное меню:",
            reply_markup=main_menu()
        )
    await state.finish()

# ========== КОМАНДА /END ==========
@dp.message_handler(commands=['end'])
async def cmd_end(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if str(user_id) in dialogs:
        admin_id = dialogs[str(user_id)]
        del dialogs[str(user_id)]
        save_all()
        
        try:
            await bot.send_message(
                int(admin_id),
                "🔚 Пользователь завершил диалог."
            )
        except:
            pass
        
        await message.answer("✅ Диалог завершён.")
        await state.finish()
        
        if is_admin(user_id):
            await message.answer(
                "Меню администратора:",
                reply_markup=admin_menu(user_id)
            )
        else:
            await message.answer(
                "Главное меню:",
                reply_markup=main_menu()
            )
        return
    
    elif str(user_id) in [v for v in dialogs.values()]:
        user_id_str = None
        for uid, aid in dialogs.items():
            if aid == str(user_id):
                user_id_str = uid
                break
        
        if user_id_str:
            del dialogs[user_id_str]
            save_all()
            
            try:
                await bot.send_message(
                    int(user_id_str),
                    "🔚 Администратор завершил диалог.\n\n"
                    "Если админ был к вам невежлив, груб и т.д., нажмите «Позвать админа» и введите тег: #крип, чтобы объяснить ситуацию."
                )
            except:
                pass
            
            await message.answer("✅ Диалог завершён.")
            await state.finish()
            
            if is_admin(user_id):
                await message.answer(
                    "Меню администратора:",
                    reply_markup=admin_menu(user_id)
                )
            else:
                await message.answer(
                    "Главное меню:",
                    reply_markup=main_menu()
                )
            return
    
    else:
        await message.answer("❌ У вас нет активного диалога.")

# ========== КНОПКИ ПОЛЬЗОВАТЕЛЯ ==========
@dp.message_handler(lambda message: message.text == "🎲 Позвать рандомно")
async def user_call_random(message: types.Message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer(
            f"❌ Вы забанены.\nПричина: {banlist[str(user_id)]['reason']}\n\n"
            f"Если вы считаете что наказание выдано просто так, напишите администраторам в канал"
        )
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть активный диалог.")
        return
    
    await message.answer(
        "❓ Вы уверены что хотите позвать рандомного Админа?",
        reply_markup=confirm_keyboard()
    )

@dp.message_handler(lambda message: message.text == "✅ Продолжить")
async def user_confirm_random(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in waiting_queue:
        waiting_queue.append(user_id)
        save_all()
    
    await message.answer(
        "⏳ Вы в очереди.",
        reply_markup=cancel_keyboard()
    )
    
    asyncio.create_task(queue_timeout(user_id))
    
    for admin_id in admins.keys():
        if not is_banned(int(admin_id)):
            try:
                await bot.send_message(
                    int(admin_id),
                    f"👤 Пользователь {get_user_name(user_id)} ищет админа."
                )
            except:
                pass

@dp.message_handler(lambda message: message.text == "❌ Отмена")
async def user_cancel(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in waiting_queue:
        waiting_queue.remove(user_id)
        save_all()
    
    if is_admin(user_id):
        await message.answer(
            "Меню администратора:",
            reply_markup=admin_menu(user_id)
        )
    else:
        await message.answer(
            "Главное меню:",
            reply_markup=main_menu()
        )

@dp.message_handler(lambda message: message.text == "🔍 Позвать админа (по тегу)")
async def user_call_by_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer(
            f"❌ Вы забанены.\nПричина: {banlist[str(user_id)]['reason']}\n\n"
            f"Если вы считаете что наказание выдано просто так, напишите администраторам в канал"
        )
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть активный диалог.")
        return
    
    await UserStates.waiting_for_admin_tag.set()
    await message.answer(
        "🔍 Введите тег админа. Пример: #Дил",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=UserStates.waiting_for_admin_tag)
async def process_admin_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    tag = message.text.strip()
    
    if tag == "❌ Отмена":
        if is_admin(user_id):
            await message.answer(
                "Меню администратора:",
                reply_markup=admin_menu(user_id)
            )
        else:
            await message.answer(
                "Главное меню:",
                reply_markup=main_menu()
            )
        await state.finish()
        return
    
    admin_id = None
    for aid, data in admins.items():
        if data.get("tag") == tag:
            admin_id = int(aid)
            break
    
    if not admin_id:
        await message.answer("❌ Админ с таким тегом не найден.")
        await state.finish()
        return
    
    if str(admin_id) in dialogs.values():
        await message.answer("❌ Этот админ сейчас занят.")
        await state.finish()
        return
    
    if str(admin_id) not in pending_by_tag:
        pending_by_tag[str(admin_id)] = []
    
    if user_id not in pending_by_tag[str(admin_id)]:
        pending_by_tag[str(admin_id)].append(user_id)
        save_all()
    
    await message.answer(f"✅ Запрос отправлен админу {tag}.")
    
    try:
        await bot.send_message(
            admin_id,
            f"👤 Пользователь {get_user_name(user_id)} зовёт вас в диалог (тег {tag})."
        )
    except:
        pass
    
    await state.finish()

# ========== КНОПКИ АДМИНА ==========
@dp.message_handler(lambda message: message.text == "🎲 Подключиться рандомно")
async def admin_connect_random(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_admin(admin_id):
        return
    
    if not waiting_queue:
        await message.answer("📭 Нет пользователей в очереди.")
        return
    
    text = "📋 Ожидающие пользователи:\n\n"
    for i, uid in enumerate(waiting_queue, 1):
        text += f"{i}. {get_user_name(uid)} (ID: {uid})\n"
    
    text += "\nВведите номер пользователя:"
    
    await AdminStates.waiting_for_user_id.set()
    await message.answer(text)

@dp.message_handler(state=AdminStates.waiting_for_user_id)
async def process_user_id_selection(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(waiting_queue):
            raise ValueError
        user_id = waiting_queue[index]
    except:
        await message.answer("❌ Неверный номер.")
        await state.finish()
        return
    
    waiting_queue.remove(user_id)
    dialogs[str(user_id)] = str(admin_id)
    save_all()
    
    admin_tag = get_admin_tag(admin_id)
    
    try:
        await bot.send_message(
            user_id,
            f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
            reply_markup=dialog_keyboard()
        )
    except:
        pass
    
    await message.answer(f"✅ Вы подключились к пользователю {get_user_name(user_id)}.")
    await AdminStates.in_dialog.set()
    await message.answer(
        "Теперь вы общаетесь в этом чате.",
        reply_markup=dialog_keyboard()
    )
    await state.finish()

@dp.message_handler(lambda message: message.text == "🔍 Подключиться по тегу")
async def admin_connect_by_tag(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_admin(admin_id):
        return
    
    if str(admin_id) not in pending_by_tag or not pending_by_tag[str(admin_id)]:
        await message.answer("📭 Нет пользователей, которые позвали вас.")
        return
    
    text = "📋 Пользователи, ожидающие вас:\n\n"
    for i, uid in enumerate(pending_by_tag[str(admin_id)], 1):
        text += f"{i}. {get_user_name(uid)} (ID: {uid})\n"
    
    text += "\nВведите номер пользователя:"
    
    await AdminStates.waiting_for_user_id.set()
    await message.answer(text)

@dp.message_handler(lambda message: message.text == "👑 Админ-панель")
async def admin_panel(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    await message.answer("👑 Админ-панель", reply_markup=admin_panel_keyboard())

# ========== ДИАЛОГИ ==========
@dp.message_handler(state=AdminStates.in_dialog)
async def admin_dialog_message(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    user_id = None
    for uid, aid in dialogs.items():
        if aid == str(admin_id):
            user_id = int(uid)
            break
    
    if not user_id:
        await message.answer("❌ Диалог не найден.")
        await state.finish()
        return
    
    if message.text == "🔚 Завершить диалог":
        del dialogs[str(user_id)]
        save_all()
        
        try:
            await bot.send_message(
                user_id,
                "🔚 Администратор завершил диалог.\n\n"
                "Если админ был к вам невежлив, груб и т.д., нажмите «Позвать админа» и введите тег: #крип, чтобы объяснить ситуацию."
            )
        except:
            pass
        
        await message.answer("✅ Диалог завершён.")
        await state.finish()
        return
    
    admin_tag = get_admin_tag(admin_id)
    try:
        await bot.send_message(
            user_id,
            f"{admin_tag}\n{message.text}"
        )
    except:
        await message.answer("❌ Не удалось отправить сообщение пользователю.")

@dp.message_handler(state=UserStates.in_dialog)
async def user_dialog_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if str(user_id) not in dialogs:
        await message.answer("❌ Диалог не найден.")
        await state.finish()
        return
    
    admin_id = int(dialogs[str(user_id)])
    
    if message.text == "🔚 Завершить диалог":
        del dialogs[str(user_id)]
        save_all()
        
        try:
            await bot.send_message(
                admin_id,
                "🔚 Пользователь завершил диалог."
            )
        except:
            pass
        
        await message.answer(
            "✅ Диалог завершён.\n\n"
            "Если админ был к вам невежлив, груб и т.д., нажмите «Позвать админа» и введите тег: #крип, чтобы объяснить ситуацию."
        )
        await state.finish()
        return
    
    user_name = get_user_name(user_id)
    try:
        await bot.send_message(
            admin_id,
            f"{user_name}\n{message.text}"
        )
    except:
        await message.answer("❌ Не удалось отправить сообщение администратору.")

# ========== ЖАЛОБЫ ==========
@dp.message_handler(lambda message: message.text == "#крип")
async def complaint_with_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer(
            f"❌ Вы забанены.\nПричина: {banlist[str(user_id)]['reason']}\n\n"
            f"Если вы считаете что наказание выдано просто так, напишите администраторам в канал"
        )
        return
    
    await UserStates.waiting_for_complaint.set()
    await message.answer(
        "📝 Опишите ситуацию: на какого админа жалоба и что произошло?",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=UserStates.waiting_for_complaint)
async def process_complaint(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    complaint_text = message.text
    
    if complaint_text == "❌ Отмена":
        if is_admin(user_id):
            await message.answer(
                "Меню администратора:",
                reply_markup=admin_menu(user_id)
            )
        else:
            await message.answer(
                "Главное меню:",
                reply_markup=main_menu()
            )
        await state.finish()
        return
    
    tags = re.findall(r'#\w+', complaint_text)
    admin_tag = tags[0] if tags else "#unknown"
    
    complaint_id = str(random.randint(10000, 99999))
    complaints[complaint_id] = {
        "user_id": user_id,
        "user_name": get_user_name(user_id),
        "admin_tag": admin_tag,
        "text": complaint_text,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer("✅ Жалоба отправлена администраторам.")
    await state.finish()
    
    for aid in admins.keys():
        if is_senior_admin(int(aid)) or int(aid) == OWNER_ID:
            try:
                await bot.send_message(
                    int(aid),
                    f"⚠️ **ЖАЛОБА**\n\n"
                    f"От: {get_user_name(user_id)} (ID: {user_id})\n"
                    f"На админа: {admin_tag}\n"
                    f"Текст: {complaint_text}\n"
                    f"ID жалобы: {complaint_id}"
                )
            except:
                pass

# ========== АДМИН-ПАНЕЛЬ (СПИСКИ) ==========
@dp.message_handler(lambda message: message.text == "📋 Список пользователей")
async def list_users(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    if not users:
        await message.answer("📭 Нет пользователей.")
        return
    
    text = "📋 **Все пользователи:**\n\n"
    for uid, data in list(users.items())[:50]:
        username = data.get("username", "")
        name = data.get("name", "Unknown")
        username_str = f"@{username}" if username else "—"
        text += f"👤 {name} | {username_str} | ID: {uid}\n"
    
    await message.answer(text)

@dp.message_handler(lambda message: message.text == "📋 Список админов")
async def list_admins(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    if not admins:
        await message.answer("📭 Нет админов.")
        return
    
    text = "👑 **Все администраторы:**\n\n"
    for uid, data in admins.items():
        user_data = users.get(uid, {})
        username = user_data.get("username", "")
        name = user_data.get("name", "Unknown")
        username_str = f"@{username}" if username else "—"
        text += f"👑 {data['tag']} | {name} | {username_str} | ID: {uid} | Роль: {data['role']}\n"
    
    await message.answer(text)

# ========== ВЫДАТЬ АДМИНКУ ==========
@dp.message_handler(lambda message: message.text == "➕ Выдать админку")
async def give_admin(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    await AdminStates.waiting_for_user_id.set()
    await message.answer(
        "👤 Введите ID пользователя, которому хотите выдать админку:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_user_id)
async def process_give_admin_user(message: types.Message, state: FSMContext):
    target_id = message.text.strip()
    
    if target_id == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    if target_id not in users:
        await message.answer("❌ Пользователь с таким ID не найден.")
        await state.finish()
        return
    
    await state.update_data(target_admin_id=target_id)
    await AdminStates.waiting_for_tag.set()
    
    await message.answer(
        "🏷 Введите тег для админа (с #, например #Дил):",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_tag)
async def process_give_admin_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip()
    
    if tag == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    if not tag.startswith("#"):
        await message.answer("❌ Тег должен начинаться с #")
        return
    
    for data in admins.values():
        if data.get("tag") == tag:
            await message.answer("❌ Такой тег уже существует.")
            return
    
    await state.update_data(admin_tag=tag)
    await AdminStates.waiting_for_role.set()
    
    await message.answer("👑 Выберите роль:", reply_markup=role_keyboard())

@dp.message_handler(state=AdminStates.waiting_for_role)
async def process_give_admin_role(message: types.Message, state: FSMContext):
    role = message.text.strip()
    valid_roles = ["АДМИН", "ГЛ АДМИН", "ТЕХ.СПЕЦИАЛИСТ", "СОВЛАДЕЛЕЦ", "ВЛАДЕЛЕЦ"]
    
    if role == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    if role not in valid_roles:
        await message.answer("❌ Выберите роль из списка.")
        return
    
    data = await state.get_data()
    target_id = data.get("target_admin_id")
    tag = data.get("admin_tag")
    
    admins[target_id] = {
        "tag": tag,
        "role": role,
        "issued_by": message.from_user.id,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Админка выдана! ID: {target_id}, Тег: {tag}, Роль: {role}")
    
    try:
        await bot.send_message(
            int(target_id),
            f"👑 Вам выданы права администратора!\nТег: {tag}\nРоль: {role}"
        )
    except:
        pass
    
    await admin_panel(message)
    await state.finish()

# ========== УДАЛИТЬ АДМИНА ==========
@dp.message_handler(lambda message: message.text == "➖ Удалить админа")
async def remove_admin(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    await AdminStates.waiting_for_remove_admin_id.set()
    await message.answer(
        "👤 Введите ID админа, которого хотите удалить:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_remove_admin_id)
async def process_remove_admin_id(message: types.Message, state: FSMContext):
    target_id = message.text.strip()
    
    if target_id == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    if target_id not in admins:
        await message.answer("❌ Админ с таким ID не найден.")
        await state.finish()
        return
    
    if int(target_id) == OWNER_ID:
        await message.answer("❌ Нельзя удалить владельца.")
        await state.finish()
        return
    
    await state.update_data(remove_admin_id=target_id)
    await AdminStates.waiting_for_remove_admin_reason.set()
    
    await message.answer(
        "📝 Введите причину удаления:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_remove_admin_reason)
async def process_remove_admin_reason(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    
    if reason == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    data = await state.get_data()
    target_id = data.get("remove_admin_id")
    admin_tag = admins[target_id]["tag"]
    
    del admins[target_id]
    save_all()
    
    await message.answer(f"✅ Админ {target_id} ({admin_tag}) удалён.")
    
    try:
        await bot.send_message(
            int(target_id),
            f"❌ Вы лишены прав администратора.\nПричина: {reason}"
        )
    except:
        pass
    
    await admin_panel(message)
    await state.finish()

# ========== БАН ==========
@dp.message_handler(lambda message: message.text == "🚫 Бан пользователя")
async def ban_user(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    await AdminStates.waiting_for_ban_reason.set()
    await message.answer(
        "👤 Введите ID пользователя для бана:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_ban_reason)
async def process_ban_id(message: types.Message, state: FSMContext):
    target_id = message.text.strip()
    
    if target_id == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    if target_id not in users:
        await message.answer("❌ Пользователь с таким ID не найден.")
        await state.finish()
        return
    
    if target_id in admins:
        if is_senior_admin(int(target_id)) or int(target_id) == OWNER_ID:
            await message.answer("❌ Нельзя забанить старшего администратора или владельца.")
            await state.finish()
            return
    
    await state.update_data(ban_target_id=target_id)
    await AdminStates.waiting_for_ban_reason.set()
    
    await message.answer(
        "📝 Введите причину бана:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_ban_reason)
async def process_ban_reason(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    
    if reason == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    data = await state.get_data()
    target_id = data.get("ban_target_id")
    
    banlist[target_id] = {
        "reason": reason,
        "date": datetime.now().isoformat(),
        "banned_by": message.from_user.id
    }
    
    if target_id in dialogs:
        admin_id = dialogs[target_id]
        del dialogs[target_id]
        try:
            await bot.send_message(
                int(admin_id),
                "🔚 Пользователь забанен, диалог завершён."
            )
        except:
            pass
    
    save_all()
    
    await message.answer(f"✅ Пользователь {target_id} забанен.\nПричина: {reason}")
    
    try:
        await bot.send_message(
            int(target_id),
            f"❌ Вы забанены.\nПричина: {reason}\n\n"
            f"Если вы считаете что наказание выдано просто так, напишите администраторам в канал"
        )
    except:
        pass
    
    await admin_panel(message)
    await state.finish()

# ========== РАЗБАН ==========
@dp.message_handler(lambda message: message.text == "✅ Разбан")
async def unban_user(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    await AdminStates.waiting_for_unban_user.set()
    await message.answer(
        "👤 Введите ID пользователя для разбана:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_unban_user)
async def process_unban(message: types.Message, state: FSMContext):
    target_id = message.text.strip()
    
    if target_id == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    if target_id not in banlist:
        await message.answer("❌ Этот пользователь не в бане.")
        await state.finish()
        return
    
    del banlist[target_id]
    save_all()
    
    await message.answer(f"✅ Пользователь {target_id} разбанен.")
    
    try:
        await bot.send_message(
            int(target_id),
            "✅ Вы разбанены. Можете снова пользоваться ботом."
        )
    except:
        pass
    
    await admin_panel(message)
    await state.finish()

# ========== ЖАЛОБЫ (ПРОСМОТР) ==========
@dp.message_handler(lambda message: message.text == "⚠️ Жалобы (#крип)")
async def show_complaints(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    if not complaints:
        await message.answer("📭 Нет жалоб.")
        return
    
    text = "⚠️ **Жалобы:**\n\n"
    for cid, data in list(complaints.items())[-10:]:
        text += f"ID: {cid}\n"
        text += f"От: {data['user_name']} (ID: {data['user_id']})\n"
        text += f"На админа: {data['admin_tag']}\n"
        text += f"Текст: {data['text']}\n"
        text += f"Дата: {data['date'][:19]}\n\n"
    
    await message.answer(text)

# ========== РАССЫЛКА ==========
@dp.message_handler(lambda message: message.text == "📢 Рассылка")
async def broadcast_start(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_senior_admin(admin_id) and not is_owner(admin_id):
        return
    
    await AdminStates.waiting_for_broadcast_text.set()
    await message.answer(
        "📝 Введите текст рассылки:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=AdminStates.waiting_for_broadcast_text)
async def broadcast_text(message: types.Message, state: FSMContext):
    text = message.text.strip()
    
    if text == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    await state.update_data(broadcast_text=text)
    await AdminStates.waiting_for_broadcast_button.set()
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("-"))
    keyboard.add(KeyboardButton("❌ Отмена"))
    
    await message.answer(
        "🔗 Добавить кнопку?\n"
        "Формат: Текст кнопки | URL\n"
        "Или отправьте '-' чтобы пропустить",
        reply_markup=keyboard
    )

@dp.message_handler(state=AdminStates.waiting_for_broadcast_button)
async def broadcast_button(message: types.Message, state: FSMContext):
    button_data = message.text.strip()
    
    if button_data == "❌ Отмена":
        await admin_panel(message)
        await state.finish()
        return
    
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    
    keyboard = None
    if button_data != "-":
        try:
            btn_text, url = button_data.split("|")
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton(btn_text.strip(), url=url.strip()))
        except:
            await message.answer("❌ Неправильный формат. Используйте: Текст | URL")
            return
    
    await message.answer("⏳ Начинаю рассылку...")
    
    sent = 0
    failed = 0
    
    for uid in list(users.keys()) + list(admins.keys()):
        if uid in banlist:
            failed += 1
            continue
        
        try:
            await bot.send_message(
                int(uid),
                broadcast_text,
                reply_markup=keyboard
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await message.answer(f"✅ Рассылка завершена!\nОтправлено: {sent}\nНе доставлено: {failed}")
    await admin_panel(message)
    await state.finish()

# ========== НАЗАД ==========
@dp.message_handler(lambda message: message.text == "◀️ Назад")
async def back_to_menu(message: types.Message):
    user_id = message.from_user.id
    
    if is_admin(user_id):
        await message.answer(
            "Меню администратора:",
            reply_markup=admin_menu(user_id)
        )
    else:
        await message.answer(
            "Главное меню:",
            reply_markup=main_menu()
        )

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("БОТ ЗАПУСКАЕТСЯ")
    logger.info(f"Владелец: {OWNER_ID} с тегом {OWNER_TAG}")
    logger.info(f"Админов в базе: {len(admins)}")
    logger.info(f"Пользователей в базе: {len(users)}")
    logger.info("=" * 50)
    
    try:
        bot.send_message(OWNER_ID, "✅ Бот успешно запущен!")
    except:
        pass
    
    executor.start_polling(dp, skip_updates=True)
