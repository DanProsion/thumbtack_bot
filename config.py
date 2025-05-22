import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Telegram Bot Token (на будущее)
TOKEN_BOT = os.getenv("TOKEN_BOT")

# 2captcha
API_TOKEN_CAPTCHA = os.getenv("API_TOKEN_CAPTCHA")

# 5sim.net
API_KEY_SIM = os.getenv("API_KEY_SIM")


