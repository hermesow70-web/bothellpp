from aiogram.dispatcher.filters.state import State, StatesGroup

class DialogStates(StatesGroup):
    waiting_for_name = State()
    user_waiting_tag = State()
    admin_waiting_choice = State()
    
class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_buttons = State()
