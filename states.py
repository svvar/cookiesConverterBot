from aiogram.fsm.state import State, StatesGroup

class AddingPermission(StatesGroup):
    entering_name = State()
    entering_id = State()

class RemovingPermission(StatesGroup):
    entering_name = State()

class Mailing(StatesGroup):
    entering_message = State()