import asyncio
from datetime import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    users, admins, dialogs, banlist, complaints, save_all,
    is_admin, is_gl_admin, is_owner, get_user_name
)
from states import BroadcastStates
from keyboards import admin_menu

# ========== КОМАНДА /LIST ==========
async def cmd_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    text = "📋 **Пользователи:**\n\n"
    for uid, data in users.items():
        name = data.get('name', 'Неизвестно')
        banned = " 🔴" if uid in banlist else ""
        text += f"👤 {name} | ID: {uid}{banned}\n"
    await message.answer(text)

# ========== КОМАНДА /ADLIST ==========
async def cmd_adlist(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    text = "👑 **Админы:**\n\n"
    for uid, data in admins.items():
        user_data = users.get(uid, {})
        name = user_data.get('name', 'Неизвестно')
        text += f"👤 {name} | {data['tag']} | {data['role']} | ID: {uid}\n"
    await message.answer(text)

# ========== КОМАНДА /COMPLAINTS ==========
async def cmd_complaints(message: types.Message):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    if not complaints:
        await message.answer("📭 Нет жалоб.")
        return
    text = "⚠️ **Жалобы:**\n\n"
    for cid, data in complaints.items():
        text += f"ID: {cid}\nОт: {data['user_name']}\nТекст: {data['text']}\n\n"
    await message.answer(text)

# ========== КОМАНДА /SETADMIN ==========
async def cmd_setadmin(message: types.Message):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    args = message.get_args().split()
    if len(args) < 3:
        await message.answer("❌ /setadmin [ID] [тег] [роль]\nРоли: АДМИН или ГЛ.АДМИН")
        return
    target_id, tag, role = args[0], args[1], args[2].upper()
    if role not in ["АДМИН", "ГЛ.АДМИН"]:
        await message.answer("❌ Роль: АДМИН или ГЛ.АДМИН")
        return
    if target_id not in users:
        await message.answer("❌ Пользователь не найден")
        return
    admins[target_id] = {"tag": tag, "role": role, "date": datetime.now().isoformat()}
    save_all()
    await message.answer(f"✅ Админка выдана {target_id}")

# ========== КОМАНДА /DELADMIN ==========
async def cmd_deladmin(message: types.Message):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /deladmin [ID]")
        return
    target_id = args[0]
    if target_id not in admins:
        await message.answer("❌ Админ не найден")
        return
    if target_id == str(OWNER_ID):
        await message.answer("❌ Нельзя удалить владельца")
        return
    del admins[target_id]
    save_all()
    await message.answer(f"✅ Админ {target_id} удалён")

# ========== КОМАНДА /BAN ==========
async def cmd_ban(message: types.Message):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /ban [ID]")
        return
    target_id = args[0]
    if target_id in admins:
        await message.answer("❌ Нельзя забанить админа")
        return
    banlist[target_id] = {"reason": " ", "date": datetime.now().isoformat()}
    save_all()
    await message.answer(f"✅ {target_id} забанен")

# ========== КОМАНДА /UNBAN ==========
async def cmd_unban(message: types.Message):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /unban [ID]")
        return
    target_id = args[0]
    if target_id in banlist:
        del banlist[target_id]
        save_all()
        await message.answer(f"✅ {target_id} разбанен")
    else:
        await message.answer("❌ Пользователь не в бане")

# ========== КОМАНДА /ENDO ==========
async def cmd_endo(message: types.Message):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /endo [ID админа]")
        return
    target_admin_id = args[0]
    for uid, aid in dialogs.items():
        if aid == target_admin_id:
            del dialogs[uid]
            save_all()
            await message.answer(f"✅ Диалог админа {target_admin_id} завершён")
            return
    await message.answer("❌ У этого админа нет диалога")

# ========== РАССЫЛКА ==========
async def cmd_all(message: types.Message, state: FSMContext):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        await message.answer("❌ Только ГЛ.АДМИН может делать рассылку.")
        return
    
    await BroadcastStates.waiting_for_text.set()
    await message.answer(
        "📝 Введите текст для рассылки:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))
    )

async def process_broadcast_text(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=admin_menu())
        return
    
    await state.update_data(broadcast_text=message.text)
    await BroadcastStates.waiting_for_buttons.set()
    
    await message.answer(
        "🔗 Добавьте кнопки (до 2-х). Формат: Текст1|URL1;Текст2|URL2\n"
        "Или отправьте 'пропустить' чтобы продолжить без кнопок",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("пропустить"),
            KeyboardButton("❌ Отмена")
        )
    )

async def process_broadcast_buttons(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=admin_menu())
        return
    
    data = await state.get_data()
    text = data.get("broadcast_text")
    keyboard = None
    
    if message.text != "пропустить":
        try:
            buttons_data = message.text.split(';')
            inline_kb = InlineKeyboardMarkup(row_width=2)
            for btn in buttons_data[:2]:
                btn_text, btn_url = btn.split('|')
                inline_kb.add(InlineKeyboardButton(btn_text.strip(), url=btn_url.strip()))
            keyboard = inline_kb
        except:
            await message.answer("❌ Неправильный формат. Попробуйте еще раз или отправьте 'пропустить'")
            return
    
    await message.answer("⏳ Начинаю рассылку...")
    
    sent = 0
    for uid in users:
        if uid in banlist:
            continue
        try:
            await message.bot.send_message(int(uid), text, reply_markup=keyboard)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await message.answer(f"✅ Рассылка завершена! Отправлено {sent} пользователям")
    await state.finish()
