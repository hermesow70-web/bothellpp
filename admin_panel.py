#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль админ-панели - ПОЛНОСТЬЮ РАБОЧИЙ
Все команды для управления ботом
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

logger = logging.getLogger(__name__)

# ========== СОСТОЯНИЯ ДЛЯ АДМИН-ПАНЕЛИ ==========
class AdminStates(StatesGroup):
    waiting_for_ban_reason = State()

# ========== КОМАНДА /HELP ==========
async def cmd_help(message: types.Message, is_admin, is_gl_admin, OWNER_ID):
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
        text += "`/setadmin [ID] [тег] [роль]` - Выдать админку\n"
        text += "`/deladmin [ID]` - Удалить админа\n"
        text += "`/ban [ID] [причина]` - Забанить\n"
        text += "`/unban [ID]` - Разбанить\n"
        text += "`/all [текст]` - Рассылка"
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /ADMIN ==========
async def cmd_admin(message: types.Message, is_admin, is_gl_admin, OWNER_ID):
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
            "`/ban [ID] [причина]` - забанить\n"
            "`/unban [ID]` - разбанить\n"
            "`/all [текст]` - рассылка\n"
            "`/endo [ID]` - завершить диалог админа"
        )
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /ENDO ==========
async def cmd_endo(
    message: types.Message,
    bot, dialogs, save_all,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только для ГЛ.АДМИНА.")
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /endo [ID админа]")
        return
    
    target_admin_id = args[0]
    
    user_to_remove = None
    for uid, aid in dialogs.items():
        if aid == target_admin_id:
            user_to_remove = uid
            break
    
    if not user_to_remove:
        await message.answer("❌ У этого админа нет активного диалога.")
        return
    
    del dialogs[user_to_remove]
    save_all()
    
    try:
        await bot.send_message(
            int(target_admin_id),
            "🔚 ГЛ.АДМИН завершил ваш диалог."
        )
    except:
        pass
    
    try:
        await bot.send_message(
            int(user_to_remove),
            "🔚 Диалог завершён администратором."
        )
    except:
        pass
    
    await message.answer(f"✅ Диалог админа {target_admin_id} завершён.")

# ========== КОМАНДА /LIST ==========
async def cmd_list(message: types.Message, users, banlist, is_admin):
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

# ========== КОМАНДА /ADLIST ==========
async def cmd_adlist(message: types.Message, users, admins, is_admin):
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

# ========== КОМАНДА /SETADMIN ==========
async def cmd_setadmin(
    message: types.Message,
    users, admins, save_all, bot,
    is_gl_admin, OWNER_ID
):
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
    
    try:
        await bot.send_message(
            int(target_id),
            f"👑 Вам выданы права администратора!\nТег: {tag}\nРоль: {role}"
        )
    except:
        pass

# ========== КОМАНДА /DELADMIN ==========
async def cmd_deladmin(
    message: types.Message,
    users, admins, save_all, bot,
    is_gl_admin, OWNER_ID
):
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
    
    try:
        await bot.send_message(
            int(target_id),
            "❌ Вы лишены прав администратора."
        )
    except:
        pass

# ========== КОМАНДА /BAN ==========
async def cmd_ban(
    message: types.Message,
    users, admins, banlist, save_all, bot,
    is_gl_admin, OWNER_ID
):
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

# ========== КОМАНДА /UNBAN ==========
async def cmd_unban(
    message: types.Message,
    users, banlist, save_all, bot,
    is_gl_admin, OWNER_ID
):
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

# ========== КОМАНДА /ALL ==========
async def cmd_all(
    message: types.Message,
    users, banlist, bot,
    is_gl_admin, OWNER_ID
):
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

# ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========
def register_handlers(
    dp: Dispatcher,
    bot,
    users, admins, dialogs, banlist, save_all,
    is_admin_func, is_gl_admin_func, OWNER_ID
):
    # Команда /help
    dp.register_message_handler(
        lambda msg: cmd_help(msg, is_admin_func, is_gl_admin_func, OWNER_ID),
        commands=['help']
    )
    
    # Команда /admin
    dp.register_message_handler(
        lambda msg: cmd_admin(msg, is_admin_func, is_gl_admin_func, OWNER_ID),
        commands=['admin']
    )
    
    # Команда /endo
    dp.register_message_handler(
        lambda msg: cmd_endo(
            msg, bot, dialogs, save_all,
            is_gl_admin_func, OWNER_ID
        ),
        commands=['endo']
    )
    
    # Команда /list
    dp.register_message_handler(
        lambda msg: cmd_list(msg, users, banlist, is_admin_func),
        commands=['list']
    )
    
    # Команда /adlist
    dp.register_message_handler(
        lambda msg: cmd_adlist(msg, users, admins, is_admin_func),
        commands=['adlist']
    )
    
    # Команда /setadmin
    dp.register_message_handler(
        lambda msg: cmd_setadmin(
            msg, users, admins, save_all, bot,
            is_gl_admin_func, OWNER_ID
        ),
        commands=['setadmin']
    )
    
    # Команда /deladmin
    dp.register_message_handler(
        lambda msg: cmd_deladmin(
            msg, users, admins, save_all, bot,
            is_gl_admin_func, OWNER_ID
        ),
        commands=['deladmin']
    )
    
    # Команда /ban
    dp.register_message_handler(
        lambda msg: cmd_ban(
            msg, users, admins, banlist, save_all, bot,
            is_gl_admin_func, OWNER_ID
        ),
        commands=['ban']
    )
    
    # Команда /unban
    dp.register_message_handler(
        lambda msg: cmd_unban(
            msg, users, banlist, save_all, bot,
            is_gl_admin_func, OWNER_ID
        ),
        commands=['unban']
    )
    
    # Команда /all
    dp.register_message_handler(
        lambda msg: cmd_all(
            msg, users, banlist, bot,
            is_gl_admin_func, OWNER_ID
        ),
        commands=['all']
    )
