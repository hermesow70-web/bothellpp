#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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

def is_gl_admin(user_id: int) -> bool:
    if str(user_id) not in admins:
        return False
    return admins[str(user_id)].get("role") in ["ГЛ.АДМИН", "ВЛАДЕЛЕЦ"]

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_banned(user_id: int) -> bool:
    return str(user_id) in banlist

def get_user_name(user_id: int) -> str:
    return users.get(str(user_id), {}).get("name", "Пользователь")

def get_admin_tag(user_id: int) -> str:
    return admins.get(str(user_id), {}).get("tag", "#unknown")

# ========== КЛАВИАТУРЫ ==========
def main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🎲 Позвать рандомно"))
    keyboard.add(KeyboardButton("🔍 Позвать админа (по тегу)"))
    return keyboard

def admin_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📋 Список диалогов"))
    keyboard.add(KeyboardButton("👑 Админ-панель"))
    return keyboard

def dialog_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔚 Завершить диалог"))
    return keyboard

def cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

# ========== КЛАССЫ СОСТОЯНИЙ ==========
class UserStates(StatesGroup):
    waiting_for_admin_tag = State()
    in_dialog = State()
    waiting_for_complaint = State()

class AdminStates(StatesGroup):
    waiting_for_tag = State()
    in_dialog = State()
    waiting_for_ban_reason = State()

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
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer(
            f"❌ Вы забанены.\nПричина: {banlist[str(user_id)]['reason']}"
        )
        return
    
    if str(user_id) not in users:
        users[str(user_id)] = {
            "name": message.from_user.first_name,
            "username": message.from_user.username,
            "registered": datetime.now().isoformat()
        }
        save_all()
    
    if is_admin(user_id):
        await message.answer(
            "👑 Меню администратора:",
            reply_markup=admin_menu()
        )
    else:
        await message.answer(
            "👋 Добро пожаловать!\n"
            "Выберите действие:",
            reply_markup=main_menu()
        )

# ========== КНОПКИ ПОЛЬЗОВАТЕЛЯ ==========
@dp.message_handler(lambda message: message.text == "🎲 Позвать рандомно")
async def user_call_random(message: types.Message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer(f"❌ Вы забанены.")
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть активный диалог.")
        return
    
    if user_id not in waiting_queue:
        waiting_queue.append(user_id)
        save_all()
    
    await message.answer(
        "⏳ Вы в очереди. Как только освободится админ, он к вам подключится."
    )
    
    asyncio.create_task(queue_timeout(user_id))

@dp.message_handler(lambda message: message.text == "🔍 Позвать админа (по тегу)")
async def user_call_by_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer(f"❌ Вы забанены.")
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть активный диалог.")
        return
    
    await UserStates.waiting_for_admin_tag.set()
    await message.answer(
        "🔍 Введите тег админа. Пример: #дил",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=UserStates.waiting_for_admin_tag)
async def process_admin_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    tag = message.text.strip()
    
    if tag == "❌ Отмена":
        await message.answer("Главное меню:", reply_markup=main_menu())
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
@dp.message_handler(lambda message: message.text == "📋 Список диалогов")
async def admin_dialog_list(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_admin(admin_id):
        return
    
    text = "📋 **Ожидающие диалоги:**\n\n"
    
    if waiting_queue:
        text += "🔹 **Рандомные вызовы:**\n"
        for i, uid in enumerate(waiting_queue, 1):
            text += f"{i}. {get_user_name(uid)}\n"
    
    if str(admin_id) in pending_by_tag and pending_by_tag[str(admin_id)]:
        text += "\n🔹 **Вызовы по тегу:**\n"
        for i, uid in enumerate(pending_by_tag[str(admin_id)], 1):
            text += f"{i}. {get_user_name(uid)}\n"
    
    if not waiting_queue and not (str(admin_id) in pending_by_tag and pending_by_tag[str(admin_id)]):
        text = "📭 Нет ожидающих диалогов."
    
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🎲 Подключиться рандомно"))
    keyboard.add(KeyboardButton("🔍 Подключиться по тегу"))
    keyboard.add(KeyboardButton("◀️ Назад"))
    
    await message.answer(text, reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "🎲 Подключиться рандомно")
async def admin_connect_random(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_admin(admin_id):
        return
    
    if not waiting_queue:
        await message.answer("📭 Нет пользователей в очереди.")
        return
    
    text = "📋 Выберите пользователя:\n\n"
    for i, uid in enumerate(waiting_queue, 1):
        text += f"{i}. {get_user_name(uid)}\n"
    
    text += "\nВведите номер пользователя:"
    
    await state.update_data(connect_type="random")
    await AdminStates.waiting_for_tag.set()
    await message.answer(text, reply_markup=cancel_keyboard())

@dp.message_handler(lambda message: message.text == "🔍 Подключиться по тегу")
async def admin_connect_by_tag(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_admin(admin_id):
        return
    
    if str(admin_id) not in pending_by_tag or not pending_by_tag[str(admin_id)]:
        await message.answer("📭 Нет пользователей, которые позвали вас.")
        return
    
    text = "📋 Выберите пользователя:\n\n"
    for i, uid in enumerate(pending_by_tag[str(admin_id)], 1):
        text += f"{i}. {get_user_name(uid)}\n"
    
    text += "\nВведите номер пользователя:"
    
    await state.update_data(connect_type="tag")
    await AdminStates.waiting_for_tag.set()
    await message.answer(text, reply_markup=cancel_keyboard())

@dp.message_handler(state=AdminStates.waiting_for_tag)
async def process_admin_connect(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if message.text == "❌ Отмена":
        await message.answer("Меню:", reply_markup=admin_menu())
        await state.finish()
        return
    
    data = await state.get_data()
    connect_type = data.get("connect_type")
    
    try:
        index = int(message.text.strip()) - 1
    except:
        await message.answer("❌ Введите номер.")
        return
    
    user_id = None
    if connect_type == "random":
        if index < 0 or index >= len(waiting_queue):
            await message.answer("❌ Неверный номер.")
            return
        user_id = waiting_queue[index]
        waiting_queue.remove(user_id)
    else:
        if str(admin_id) not in pending_by_tag or index < 0 or index >= len(pending_by_tag[str(admin_id)]):
            await message.answer("❌ Неверный номер.")
            return
        user_id = pending_by_tag[str(admin_id)][index]
        pending_by_tag[str(admin_id)].remove(user_id)
    
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
        "Теперь вы общаетесь. Напишите сообщение, оно уйдет пользователю.",
        reply_markup=dialog_keyboard()
    )
    await state.finish()

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
        await message.answer("Меню:", reply_markup=admin_menu())
        return
    
    if message.text == "🔚 Завершить диалог":
        del dialogs[str(user_id)]
        save_all()
        
        try:
            await bot.send_message(
                user_id,
                "🔚 Администратор завершил диалог.\n\n"
                "Если админ был груб, напишите #крип и опишите ситуацию."
            )
        except:
            pass
        
        await message.answer("✅ Диалог завершён.")
        await state.finish()
        await message.answer("Меню:", reply_markup=admin_menu())
        return
    
    admin_tag = get_admin_tag(admin_id)
    try:
        await bot.send_message(
            user_id,
            f"{admin_tag}\n{message.text}"
        )
    except:
        await message.answer("❌ Не удалось отправить сообщение.")

@dp.message_handler(state=UserStates.in_dialog)
async def user_dialog_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if str(user_id) not in dialogs:
        await message.answer("❌ Диалог не найден.")
        await state.finish()
        await message.answer("Главное меню:", reply_markup=main_menu())
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
        
        await message.answer("✅ Диалог завершён.")
        await state.finish()
        await message.answer("Главное меню:", reply_markup=main_menu())
        return
    
    user_name = get_user_name(user_id)
    try:
        await bot.send_message(
            admin_id,
            f"{user_name}\n{message.text}"
        )
    except:
        await message.answer("❌ Не удалось отправить сообщение.")

# ========== ЖАЛОБЫ ==========
@dp.message_handler(lambda message: message.text == "#крип")
async def complaint_with_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    await UserStates.waiting_for_complaint.set()
    await message.answer(
        "📝 Опишите ситуацию:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=UserStates.waiting_for_complaint)
async def process_complaint(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    complaint_text = message.text
    
    if complaint_text == "❌ Отмена":
        await message.answer("Главное меню:", reply_markup=main_menu())
        await state.finish()
        return
    
    complaint_id = str(random.randint(10000, 99999))
    complaints[complaint_id] = {
        "user_id": user_id,
        "user_name": get_user_name(user_id),
        "text": complaint_text,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer("✅ Жалоба отправлена администраторам.")
    await state.finish()
    
    for aid in admins.keys():
        if is_gl_admin(int(aid)):
            try:
                await bot.send_message(
                    int(aid),
                    f"⚠️ **ЖАЛОБА**\n\n"
                    f"От: {get_user_name(user_id)} (ID: {user_id})\n"
                    f"Текст: {complaint_text}"
                )
            except:
                pass

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message_handler(lambda message: message.text == "👑 Админ-панель")
async def admin_panel(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
        await message.answer("❌ У вас нет прав.")
        return
    
    text = (
        "👑 **Админ-панель**\n\n"
        "Команды:\n"
        "`/list` - список пользователей\n"
        "`/adlist` - список админов\n"
        "`/setadmin [ID] [тег] [роль]` - выдать админку\n"
        "   Роли: `АДМИН` или `ГЛ.АДМИН`\n"
        "`/deladmin [ID]` - удалить админа\n"
        "`/ban [ID] [причина]` - забанить\n"
        "`/unban [ID]` - разбанить\n"
        "`/all [текст]` - рассылка"
    )
    
    await message.answer(text)

# ========== КОМАНДЫ ==========
@dp.message_handler(commands=['list'])
async def cmd_list(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
        return
    
    if not users:
        await message.answer("📭 Нет пользователей.")
        return
    
    text = "📋 **Пользователи:**\n\n"
    for uid, data in list(users.items())[:50]:
        name = data.get("name", "Unknown")
        username = data.get("username", "")
        banned = " [ЗАБАНЕН]" if uid in banlist else ""
        text += f"👤 {name} (@{username}) | ID: {uid}{banned}\n"
    
    await message.answer(text)

@dp.message_handler(commands=['adlist'])
async def cmd_adlist(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
        return
    
    if not admins:
        await message.answer("📭 Нет админов.")
        return
    
    text = "👑 **Администраторы:**\n\n"
    for uid, data in admins.items():
        name = users.get(uid, {}).get("name", "Unknown")
        text += f"👤 {name} | {data['tag']} | Роль: {data['role']} | ID: {uid}\n"
    
    await message.answer(text)

@dp.message_handler(commands=['setadmin'])
async def cmd_setadmin(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
        await message.answer("❌ Нет прав.")
        return
    
    args = message.get_args().split()
    if len(args) < 3:
        await message.answer("❌ Использование: /setadmin [ID] [тег] [роль]")
        return
    
    target_id = args[0]
    tag = args[1]
    role = args[2].upper()
    
    if not tag.startswith("#"):
        tag = "#" + tag
    
    if role not in ["АДМИН", "ГЛ.АДМИН"]:
        await message.answer("❌ Роль должна быть АДМИН или ГЛ.АДМИН")
        return
    
    if target_id not in users:
        await message.answer("❌ Пользователь не найден.")
        return
    
    admins[target_id] = {
        "tag": tag,
        "role": role,
        "issued_by": admin_id,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Админка выдана! ID: {target_id}, Тег: {tag}, Роль: {role}")

@dp.message_handler(commands=['deladmin'])
async def cmd_deladmin(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
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
    
    if int(target_id) == OWNER_ID:
        await message.answer("❌ Нельзя удалить владельца.")
        return
    
    del admins[target_id]
    save_all()
    await message.answer(f"✅ Админ {target_id} удалён.")

@dp.message_handler(commands=['ban'])
async def cmd_ban(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
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
        "banned_by": admin_id
    }
    save_all()
    
    await message.answer(f"✅ Пользователь {target_id} забанен.")

@dp.message_handler(commands=['unban'])
async def cmd_unban(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
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

@dp.message_handler(commands=['all'])
async def cmd_all(message: types.Message):
    admin_id = message.from_user.id
    
    if not is_gl_admin(admin_id) and not is_owner(admin_id):
        await message.answer("❌ Нет прав.")
        return
    
    text = message.get_args()
    if not text:
        await message.answer("❌ Использование: /all [текст]")
        return
    
    await message.answer("⏳ Рассылка...")
    
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
    
    await message.answer(f"✅ Отправлено: {sent}\n❌ Не доставлено: {failed}")

# ========== НАЗАД ==========
@dp.message_handler(lambda message: message.text == "◀️ Назад")
async def back_to_menu(message: types.Message):
    user_id = message.from_user.id
    
    if is_admin(user_id):
        await message.answer("Меню:", reply_markup=admin_menu())
    else:
        await message.answer("Главное меню:", reply_markup=main_menu())

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("БОТ ЗАПУСКАЕТСЯ")
    logger.info(f"Владелец: {OWNER_ID}")
    logger.info("=" * 50)
    
    executor.start_polling(dp, skip_updates=True)
