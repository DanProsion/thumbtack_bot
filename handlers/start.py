from aiogram import Router, types
from aiogram.filters import CommandStart
from loader import mkb

router_start = Router()

@router_start.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Приветсвую! Вы готовы?", reply_markup=mkb.get_keyboard())
