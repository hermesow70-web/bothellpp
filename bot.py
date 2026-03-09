#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor

from config import BOT_TOKEN, OWNER_ID
from database import (
    users, admins, dialogs, waiting_queue, pending_by_tag, banlist, complaints,
    save_all, is_admin, is_gl_admin, is_owner, is_banned,
    get_user_name, get_admin_tag
)
from keyboards import (
    main_menu, admin_menu, dialog_menu, cancel_menu, channel_keyboard
)
from states import DialogStates, BroadcastStates
from admin_panel import (
    cmd_list, cmd_adlist, cmd_complaints, cmd_setadmin, cmd_deladmin,
    cmd_ban, cmd_unban, cmd_endo, cmd_all, process_broadcast_text, process_broadcast_buttons
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ========== ТАЙМЕР ==========
async def queue_timeout(user_id: int):
    await asyncio.sleep(600)
    if str(user_id) in dialogs:
        return
    if user_id in waiting_queue:
        waiting_queue.remove(user_id)
        save_all()
        try:
            await bot.send_message(user_id, "⏰ Похоже, что все админы заняты.\nПопробуйте снова /start")
        except:
            pass

# ========== ЖАЛОБЫ ==========
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
    
    await message.answer("✅ Ваша жалоба отправлена ГЛ.АДМИНАМ.")
    
    for aid, data in admins.items():
        if data.get("role") == "ГЛ.АДМИН" or int(aid) == OWNER_ID:
            try:
                await bot.send_message(
                    int(aid),
                    f"⚠️ **ЖАЛОБА**\n\nОт: {get_user_name(user_id)} (ID: {user_id})\nТекст: {text}"
                )
            except:
                pass

# ========== СТАРТ ==========
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    await state.finish()
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    if str(user_id) not in users:
        await state.set_state(DialogStates.waiting_for_name)
        
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
        
        await message.answer("📝 Как вас зовут?")
        return
    
    if str(user_id) in dialogs:
        admin_id = dialogs[str(user_id)]
        if admin_id not in admins:
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

# ========== ОБРАБОТКА ИМЕНИ ==========
@dp.message_handler(state=DialogStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if not name:
        await message.answer("❌ Имя не может быть пустым. Введите имя:")
        return
    
    users[str(user_id)] = {
        "name": name,
        "username": message.from_user.username,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Приятно познакомиться, {name}!")
    await state.finish()
    
    if is_admin(user_id):
        await message.answer("Меню администратора:", reply_markup=admin_menu())
    else:
        await message.answer("Выберите действие:", reply_markup=main_menu())

# ========== КОМАНДА /END ==========
@dp.message_handler(commands=['end'])
async def cmd_end(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    
    if user_id_str in dialogs:
        admin_id = int(dialogs[user_id_str])
        del dialogs[user_id_str]
        save_all()
        
        try:
            await bot.send_message(admin_id, "🔚 Пользователь завершил диалог.", reply_markup=admin_menu())
        except:
            pass
        
        await message.answer(
            "✅ Диалог завершён.\n\nЕсли админ был груб, напишите #крип"
        )
        
        await state.finish()
        
        if is_admin(user_id):
            await message.answer("Меню:", reply_markup=admin_menu())
        else:
            await message.answer("Главное меню:", reply_markup=main_menu())
        return
    
    for uid, aid in dialogs.items():
        if aid == user_id_str:
            del dialogs[uid]
            save_all()
            
            try:
                await bot.send_message(
                    int(uid),
                    "🔚 Администратор завершил диалог.\n\nЕсли админ был груб, напишите #крип"
                )
            except:
                pass
            
            await message.answer("✅ Диалог завершён.")
            await state.finish()
            await message.answer("Меню:", reply_markup=admin_menu())
            return
    
    await message.answer("❌ У вас нет активного диалога.")

# ========== КОМАНДА /HELP ==========
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    
    text = "📋 **Команды:**\n`/start` - Начать\n`/end` - Завершить диалог"
    await message.answer(text)

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message_handler(lambda message: message.text == "👑 Админ-панель")
async def admin_panel_button(message: types.Message):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and not is_owner(user_id):
        await message.answer("❌ Только для ГЛ.АДМИНОВ.")
        return
    
    text = (
        "👑 **АДМИН-ПАНЕЛЬ**\n\n"
        "`/list` - список пользователей\n"
        "`/adlist` - список админов\n"
        "`/complaints` - жалобы #крип\n"
        "`/setadmin [ID] [тег] [роль]` - выдать админку\n"
        "`/deladmin [ID]` - удалить админа\n"
        "`/ban [ID] [причина]` - забанить\n"
        "`/unban [ID]` - разбанить\n"
        "`/all` - рассылка (с кнопками)\n"
        "`/endo [ID]` - завершить диалог админа"
    )
    
    await message.answer(text, parse_mode="Markdown")

# ========== РЕГИСТРАЦИЯ КОМАНД ==========
dp.register_message_handler(cmd_list, commands=['list'])
dp.register_message_handler(cmd_adlist, commands=['adlist'])
dp.register_message_handler(cmd_complaints, commands=['complaints'])
dp.register_message_handler(cmd_setadmin, commands=['setadmin'])
dp.register_message_handler(cmd_deladmin, commands=['deladmin'])
dp.register_message_handler(cmd_ban, commands=['ban'])
dp.register_message_handler(cmd_unban, commands=['unban'])
dp.register_message_handler(cmd_endo, commands=['endo'])
dp.register_message_handler(cmd_all, commands=['all'], state='*')
dp.register_message_handler(process_broadcast_text, state=BroadcastStates.waiting_for_text)
dp.register_message_handler(process_broadcast_buttons, state=BroadcastStates.waiting_for_buttons)

# ========== КНОПКИ ПОЛЬЗОВАТЕЛЯ ==========
@dp.message_handler(lambda message: message.text == "🎲 Позвать рандомно")
async def user_call_random(message: types.Message):
    user_id = message.from_user.id
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть диалог.")
        return
    waiting_queue.append(user_id)
    save_all()
    await message.answer("⏳ Вы в очереди.", reply_markup=cancel_menu())
    asyncio.create_task(queue_timeout(user_id))

@dp.message_handler(lambda message: message.text == "🔍 Позвать админа (по тегу)")
async def user_call_by_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть диалог.")
        return
    await DialogStates.user_waiting_tag.set()
    await message.answer("🔍 Введите тег админа (например #дил):", reply_markup=cancel_menu())

@dp.message_handler(state=DialogStates.user_waiting_tag)
async def process_admin_tag(message: types.Message, state: FSMContext):
    tag = message.text.strip()
    if tag == "❌ Отмена":
        await state.finish()
        await message.answer("Меню:", reply_markup=main_menu())
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
    user_id = message.from_user.id
    if admin_id not in pending_by_tag:
        pending_by_tag[admin_id] = []
    pending_by_tag[admin_id].append(user_id)
    save_all()
    await message.answer(f"✅ Запрос отправлен админу {tag}")
    await state.finish()

# ========== КНОПКИ АДМИНА ==========
@dp.message_handler(lambda message: message.text == "📋 Список диалогов")
async def admin_dialog_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    text = "📋 **Ожидающие диалоги:**\n\n"
    if waiting_queue:
        for i, uid in enumerate(waiting_queue, 1):
            text += f"{i}. {get_user_name(uid)}\n"
    else:
        text += "Нет ожидающих диалогов"
    await message.answer(text)

@dp.message_handler(lambda message: message.text == "✅ Взять диалог")
async def admin_take_dialog(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not waiting_queue:
        await message.answer("📭 Нет диалогов.")
        return
    await DialogStates.admin_waiting_choice.set()
    await message.answer("Введите номер диалога из списка:")

@dp.message_handler(state=DialogStates.admin_waiting_choice)
async def process_admin_choice(message: types.Message, state: FSMContext):
    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(waiting_queue):
            raise ValueError
        user_id = waiting_queue.pop(index)
    except:
        await message.answer("❌ Неверный номер.")
        await state.finish()
        return
    admin_id = message.from_user.id
    dialogs[str(user_id)] = str(admin_id)
    save_all()
    admin_tag = get_admin_tag(admin_id)
    try:
        await bot.send_message(user_id, f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!", reply_markup=dialog_menu())
    except:
        pass
    await message.answer(f"✅ Вы подключились к пользователю {get_user_name(user_id)}", reply_markup=dialog_menu())
    await state.finish()

# ========== ОБРАБОТКА ДИАЛОГОВ ==========
@dp.message_handler()
async def handle_dialog_messages(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    if str(user_id) in dialogs:
        admin_id = int(dialogs[str(user_id)])
        
        if text == "🔚 Завершить диалог":
            del dialogs[str(user_id)]
            save_all()
            
            try:
                await bot.send_message(admin_id, "🔚 Пользователь завершил диалог.", reply_markup=admin_menu())
            except:
                pass
            
            await message.answer("✅ Диалог завершён.", reply_markup=main_menu())
            return
        
        user_name = get_user_name(user_id)
        try:
            await bot.send_message(admin_id, f"{user_name}\n{text}")
        except:
            await message.answer("❌ Не удалось отправить сообщение.")
        return
    
    for uid, aid in dialogs.items():
        if aid == str(user_id):
            if text == "🔚 Завершить диалог":
                del dialogs[uid]
                save_all()
                
                try:
                    await bot.send_message(int(uid), "🔚 Администратор завершил диалог.\n\nЕсли админ был груб, напишите #крип")
                except:
                    pass
                
                await message.answer("✅ Диалог завершён.", reply_markup=admin_menu())
                return
            
            admin_tag = get_admin_tag(user_id)
            try:
                await bot.send_message(int(uid), f"{admin_tag}\n{text}")
            except:
                await message.answer("❌ Не удалось отправить сообщение.")
            return
    
    if is_admin(user_id):
        await message.answer("Меню:", reply_markup=admin_menu())
    else:
        await message.answer("Меню:", reply_markup=main_menu())

# ========== КНОПКА НАЗАД ==========
@dp.message_handler(lambda message: message.text == "◀️ Назад")
async def back_to_menu(message: types.Message):
    user_id = message.from_user.id
    if is_admin(user_id):
        await message.answer("Меню:", reply_markup=admin_menu())
    else:
        await message.answer("Меню:", reply_markup=main_menu())

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("БОТ ЗАПУЩЕН")
    logger.info(f"Владелец: {OWNER_ID}")
    logger.info(f"Админов: {len(admins)}")
    logger.info(f"Пользователей: {len(users)}")
    logger.info("=" * 50)
    
    executor.start_polling(dp, skip_updates=True)
