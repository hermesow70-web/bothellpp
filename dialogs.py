#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль диалогов для бота поддержки
Обмен сообщениями между пользователями и админами
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Импортируем данные из основного бота
from bot import bot, users, admins, dialogs, waiting_queue, pending_by_tag, save_all
from bot import is_admin, is_banned, get_user_name, get_admin_tag

logger = logging.getLogger(__name__)

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎲 Позвать рандомно"))
    kb.add(KeyboardButton("🔍 Позвать админа (по тегу)"))
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Список диалогов"))
    kb.add(KeyboardButton("👑 Админ-панель"))
    return kb

def dialog_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершить диалог"))
    return kb

def cancel_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

# ========== СОСТОЯНИЯ ==========
class DialogStates(StatesGroup):
    user_waiting_tag = State()
    user_in_dialog = State()
    admin_in_dialog = State()
    admin_waiting_choice = State()

# ========== ТАЙМЕР ==========
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

# ========== КНОПКИ ПОЛЬЗОВАТЕЛЯ ==========
async def user_call_random(message: types.Message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть активный диалог.")
        return
    
    if user_id not in waiting_queue:
        waiting_queue.append(user_id)
        save_all()
    
    await message.answer(
        "⏳ Вы в очереди. Админ скоро подключится.",
        reply_markup=cancel_menu()
    )
    
    asyncio.create_task(queue_timeout(user_id))
    
    for admin_id in admins.keys():
        try:
            await bot.send_message(
                int(admin_id),
                f"👤 Пользователь {get_user_name(user_id)} ищет админа."
            )
        except:
            pass

async def user_call_by_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть активный диалог.")
        return
    
    await DialogStates.user_waiting_tag.set()
    await message.answer(
        "🔍 Введите тег админа. Например: #дил",
        reply_markup=cancel_menu()
    )

async def process_admin_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    tag = message.text.strip()
    
    if tag == "❌ Отмена":
        await state.finish()
        await message.answer("Главное меню:", reply_markup=main_menu())
        return
    
    admin_id = None
    for aid, data in admins.items():
        if data.get("tag") == tag:
            admin_id = aid
            break
    
    if not admin_id:
        await message.answer("❌ Админ с таким тегом не найден.")
        await state.finish()
        return
    
    if admin_id in dialogs.values():
        await message.answer("❌ Этот админ сейчас занят.")
        await state.finish()
        return
    
    if admin_id not in pending_by_tag:
        pending_by_tag[admin_id] = []
    
    if user_id not in pending_by_tag[admin_id]:
        pending_by_tag[admin_id].append(user_id)
        save_all()
    
    await message.answer(f"✅ Запрос отправлен админу {tag}.")
    await state.finish()
    
    try:
        await bot.send_message(
            int(admin_id),
            f"👤 Пользователь {get_user_name(user_id)} позвал вас в диалог (тег {tag})."
        )
    except:
        pass

# ========== КНОПКИ АДМИНА ==========
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
    
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Взять диалог"))
    kb.add(KeyboardButton("◀️ Назад"))
    
    await message.answer(text, reply_markup=kb)

async def admin_take_dialog(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if not is_admin(admin_id):
        return
    
    if not waiting_queue and not (str(admin_id) in pending_by_tag and pending_by_tag[str(admin_id)]):
        await message.answer("📭 Нет диалогов.")
        return
    
    await DialogStates.admin_waiting_choice.set()
    await message.answer(
        "Введите номер диалога из списка выше:",
        reply_markup=cancel_menu()
    )

async def process_admin_choice(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Меню:", reply_markup=admin_menu())
        return
    
    try:
        index = int(message.text.strip()) - 1
    except:
        await message.answer("❌ Введите число.")
        return
    
    user_id = None
    
    # Сначала проверяем рандомную очередь
    if index < len(waiting_queue):
        user_id = waiting_queue.pop(index)
    else:
        # Если не нашли, проверяем очередь по тегу
        tag_index = index - len(waiting_queue)
        if str(admin_id) in pending_by_tag and tag_index < len(pending_by_tag[str(admin_id)]):
            user_id = pending_by_tag[str(admin_id)].pop(tag_index)
    
    if not user_id:
        await message.answer("❌ Неверный номер.")
        return
    
    # Создаем диалог
    dialogs[str(user_id)] = str(admin_id)
    save_all()
    
    admin_tag = get_admin_tag(admin_id)
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
            reply_markup=dialog_menu()
        )
    except:
        pass
    
    await message.answer(
        f"✅ Вы подключились к пользователю {get_user_name(user_id)}.\n"
        f"Теперь вы общаетесь. Напишите сообщение, оно уйдет пользователю.",
        reply_markup=dialog_menu()
    )
    
    # Устанавливаем состояния
    await DialogStates.admin_in_dialog.set()
    await state.update_data(dialog_user_id=user_id)
    
    # Устанавливаем состояние пользователя
    # Примечание: состояние пользователя будет установлено при первом сообщении

# ========== ОБРАБОТКА ДИАЛОГОВ ==========
async def admin_dialog_message(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    text = message.text
    
    data = await state.get_data()
    user_id = data.get("dialog_user_id")
    
    if not user_id or str(user_id) not in dialogs:
        await message.answer("❌ Диалог не найден.")
        await state.finish()
        await message.answer("Меню:", reply_markup=admin_menu())
        return
    
    if text == "🔚 Завершить диалог":
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
            f"{admin_tag}\n{text}"
        )
    except:
        await message.answer("❌ Не удалось отправить сообщение пользователю.")

async def user_dialog_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    if str(user_id) not in dialogs:
        await message.answer("❌ Диалог не найден.")
        await state.finish()
        await message.answer("Главное меню:", reply_markup=main_menu())
        return
    
    admin_id = int(dialogs[str(user_id)])
    
    if text == "🔚 Завершить диалог":
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
            "Если админ был груб, напишите #крип и опишите ситуацию."
        )
        await state.finish()
        await message.answer("Главное меню:", reply_markup=main_menu())
        return
    
    user_name = get_user_name(user_id)
    try:
        await bot.send_message(
            admin_id,
            f"{user_name}\n{text}"
        )
    except:
        await message.answer("❌ Не удалось отправить сообщение администратору.")

# ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========
def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики диалогов"""
    
    # Кнопки пользователя
    dp.register_message_handler(
        user_call_random,
        lambda message: message.text == "🎲 Позвать рандомно"
    )
    dp.register_message_handler(
        user_call_by_tag,
        lambda message: message.text == "🔍 Позвать админа (по тегу)"
    )
    dp.register_message_handler(
        process_admin_tag,
        state=DialogStates.user_waiting_tag
    )
    
    # Кнопки админа
    dp.register_message_handler(
        admin_dialog_list,
        lambda message: message.text == "📋 Список диалогов"
    )
    dp.register_message_handler(
        admin_take_dialog,
        lambda message: message.text == "✅ Взять диалог"
    )
    dp.register_message_handler(
        process_admin_choice,
        state=DialogStates.admin_waiting_choice
    )
    
    # Обработка диалогов
    dp.register_message_handler(
        admin_dialog_message,
        state=DialogStates.admin_in_dialog
    )
    dp.register_message_handler(
        user_dialog_message,
        state=DialogStates.user_in_dialog
    )
    
    # Кнопка "Назад"
    dp.register_message_handler(
        back_to_menu,
        lambda message: message.text == "◀️ Назад"
    )

async def back_to_menu(message: types.Message):
    """Возврат в меню"""
    user_id = message.from_user.id
    
    if is_admin(user_id):
        await message.answer("Меню:", reply_markup=admin_menu())
    else:
        await message.answer("Главное меню:", reply_markup=main_menu())
