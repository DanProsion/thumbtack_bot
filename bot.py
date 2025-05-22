import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN_BOT
from handlers.start import router_start
from handlers.account import router_account
from handlers.search import router_search

async def main():
    bot = Bot(token=TOKEN_BOT)
    dp = Dispatcher(storage=MemoryStorage())

    print('Bot started')
    dp.include_router(router_start)
    dp.include_router(router_account)
    dp.include_router(router_search)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
