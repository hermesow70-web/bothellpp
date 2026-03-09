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
    return str(user_id) in admins

def is_gl_admin(user_id: int) -> bool:
    if str(user_id) not in admins:
        return False
    return admins[str(user_id)].get("role") == "ГЛ.АДМИН"

def is_banned(user_id: int) -> bool:
    return str(user_id) in banlist

def get_user_name(user_id: int) -> str:
    return users.get(str(user_id), {}).get("name", "Пользователь")

def get_admin_tag(user_id: int) -> str:
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

# ========== ПРИВЕТСТВИЕ ==========
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
        
        # Второе сообщение с подпиской
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
    """Закончить свой диалог"""
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
                "🔚 Пользователь завершил диалог."
            )
        except:
            pass
        
        await message.answer("✅ Диалог завершён.")
        
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
                    "🔚 Администратор завершил диалог."
                )
            except:
                pass
            
            await message.answer("✅ Диалог завершён.")
            await message.answer("Меню:", reply_markup=admin_menu())
            return
    
    await message.answer("❌ У вас нет активного диалога.")

# ========== КОМАНДА /ENDO (ДЛЯ ГЛ.АДМИНА) ==========
@dp.message_handler(commands=['endo'])
async def cmd_endo(message: types.Message):
    """Закончить диалог админа по его ID"""
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только для ГЛ.АДМИНА.")
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /endo [ID админа]")
        return
    
    target_admin_id = args[0]
    
    # Ищем диалог этого админа
    user_to_remove = None
    for uid, aid in dialogs.items():
        if aid == target_admin_id:
            user_to_remove = uid
            break
    
    if not user_to_remove:
        await message.answer("❌ У этого админа нет активного диалога.")
        return
    
    # Удаляем диалог
    del dialogs[user_to_remove]
    save_all()
    
    # Уведомляем админа
    try:
        await bot.send_message(
            int(target_admin_id),
            "🔚 ГЛ.АДМИН завершил ваш диалог."
        )
    except:
        pass
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            int(user_to_remove),
            "🔚 Диалог завершён администратором."
        )
    except:
        pass
    
    await message.answer(f"✅ Диалог админа {target_admin_id} завершён.")

# ========== КОМАНДА /HELP ==========
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    
    text = "📋 **Список команд:**\n\n"
    text += "`/start` - Главное меню\n"
    text += "`/end` - Завершить текущий диалог\n"
    
    if is_admin(user_id):
        text += "\n👑 **Команды администратора:**\n"
        text += "`/admin` - Панель администратора\n"
    
    if is_gl_admin(user_id) or user_id == OWNER_ID:
        text += "\n👑👑 **Команды ГЛ.АДМИНА:**\n"
        text += "`/endo [ID]` - Завершить диалог админа\n"
        text += "`/list` - Список пользователей\n"
        text += "`/adlist` - Список админов\n"
        text += "`/setadmin` - Выдать админку\n"
        text += "`/deladmin` - Удалить админа\n"
        text += "`/ban` - Забанить\n"
        text += "`/unban` - Разбанить\n"
        text += "`/all` - Рассылка"
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /ADMIN ==========
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
            "`/all [текст]` - рассылка всем\n"
            "`/endo [ID]` - завершить диалог админа"
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
    
    # Проверяем уникальность тега
    for data in admins.values():
        if data.get("tag") == tag:
            await message.answer("❌ Такой тег уже существует.")
            return
    
    admins[target_id] = {
        "tag": tag if tag.startswith("#") else f"#{tag}",
        "role": role,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Админка выдана!\nID: {target_id}\nТег: {tag}\nРоль: {role}")
    
    # Уведомляем нового админа
    try:
        await bot.send_message(
            int(target_id),
            f"👑 Вам выданы права администратора!\nТег: {tag}\nРоль: {role}"
        )
    except:
        pass

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
    
    # Уведомляем удаленного админа
    try:
        await bot.send_message(
            int(target_id),
            "❌ Вы лишены прав администратора."
        )
    except:
        pass

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
    
    try:
        await bot.send_message(
            int(target_id),
            f"❌ Вы забанены.\nПричина: {reason}"
        )
    except:
        pass

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
    
    try:
        await bot.send_message(
            int(target_id),
            "✅ Вы разбанены. Можете снова пользоваться ботом."
        )
    except:
        pass

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

# ========== ИМПОРТ И ПОДКЛЮЧЕНИЕ ДИАЛОГОВ ==========
from dialogs import register_handlers, DialogStates

register_handlers(
    dp, bot,
    users, admins, dialogs, waiting_queue, pending_by_tag, save_all,
    is_admin, is_banned, get_user_name, get_admin_tag
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
