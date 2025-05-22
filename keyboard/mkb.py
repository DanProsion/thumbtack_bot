from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

class MarkupKeyboard:
    @staticmethod
    def get_keyboard() -> ReplyKeyboardMarkup:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Начать регистрацию аккаунта")]
            ],
            resize_keyboard=True
        )
        return keyboard