from aiogram.fsm.state import State, StatesGroup

class RegisterState(StatesGroup):
    user = State()
    waiting_for_zip = State()
    waiting_for_service = State()
    waiting_for_company_number = State()