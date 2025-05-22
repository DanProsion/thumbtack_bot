import platform
import subprocess
from loader import init_objects

async def kill_all_browser_sessions(message, user_id):
    try:
        if init_objects.driver is not None:
            try:
                init_objects.driver.quit()
            except Exception:
                pass
            init_objects.driver = None

        if platform.system() == "Windows":
            subprocess.call("taskkill /F /IM chromedriver.exe /T", shell=True)
            subprocess.call("taskkill /F /IM chrome.exe /T", shell=True)
        else:
            subprocess.call("pkill -f chromedriver", shell=True)
            subprocess.call("pkill -f chrome", shell=True)

        await message.answer("[🧹] Все предыдущие сессии браузера полностью завершены.")
    except Exception as e:
        await message.answer(f"[❌] Ошибка при завершении всех сессий браузера: {e}")