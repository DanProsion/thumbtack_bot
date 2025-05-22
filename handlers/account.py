from aiogram import Router, types
from aiogram.filters import Text
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from loader import init_objects
from state.FSM import *
from automation.kill_browser import kill_all_browser_sessions

router_account = Router()


@router_account.message(Text(text="Начать регистрацию аккаунта"))
async def start_registration_prompt(message: types.Message, state: FSMContext):
    await kill_all_browser_sessions(message, message.from_user.id)
    init_objects.init()
    await message.answer("Введите ZIP-код:")
    await state.set_state(RegisterState.waiting_for_zip)


@router_account.message(RegisterState.waiting_for_zip)
async def get_zip(message: types.Message, state: FSMContext):
    zip_code = message.text.strip()
    await state.update_data(zip_code=zip_code)
    await message.answer("Теперь введите название сервиса:")
    await state.set_state(RegisterState.waiting_for_service)


@router_account.message(RegisterState.waiting_for_service)
async def get_service_and_register(message: types.Message, state: FSMContext, bot: Bot):
    service = message.text.strip()
    data = await state.get_data()
    zip_code = data["zip_code"]
    user_id = message.from_user.id

    await message.answer(f"Регистрация аккаунта начата.\nZIP: {zip_code}\nСервис: {service}")

    await init_objects.thumbtack_register.start_register(bot=bot, user_id=user_id,
                                            zip_code=zip_code, service_name=service, state=state)

