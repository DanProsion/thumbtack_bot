from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from state.FSM import *
from aiogram import Bot
from loader import init_objects

router_search = Router()

@router_search.message(RegisterState.waiting_for_company_number)
async def company_number_handler(message: types.Message, state: FSMContext, bot: Bot):
    print("[DEBUG] Хендлер company_number_handler вызван")
    user_input = message.text.strip()

    if not user_input.isdigit():
        return await message.answer("[⚠️] Введите номер компании (число от 1 до 30).")

    number = int(user_input)

    if number < 1 or number > 30:
        return await message.answer("[⚠️] Номер должен быть от 1 до 30.")

    await init_objects.company_search_flow.handle_company_selection(bot, message.from_user.id, user_input, state)
