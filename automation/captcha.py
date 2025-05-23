import time
import requests
from config import API_TOKEN_CAPTCHA

async def solve_grid_captcha_2captcha(image_base64: str, instruction: str, bot=None, user_id=None,
                                      timeout: int = 120, retry_interval: int = 5) -> list:
    await bot.send_message(user_id, "[📡] Отправляем grid-капчу (image selection) на решение через 2Captcha...")

    async def parse_coordinates(raw_coords):
        if raw_coords == "no_answer":
            return "no_answer"
        if isinstance(raw_coords, list):
            return raw_coords
        elif isinstance(raw_coords, str):
            coords = []
            pairs = raw_coords.split('|')
            for pair in pairs:
                if ',' not in pair:
                    continue  # пропускаем некорректную строку
                try:
                    x_str, y_str = pair.split(',')
                    coords.append({'x': int(x_str), 'y': int(y_str)})
                except ValueError as ve:
                    await bot.send_message(f"⚠️ Ошибка при парсинге координаты '{pair}': {ve}")
                    continue
            return coords
        else:
            return await bot.send_message(f"Неподдерживаемый тип данных координат: {type(raw_coords)}")

    data = {
        'key': API_TOKEN_CAPTCHA,
        'method': 'base64',
        'coordinatescaptcha': 1,
        'lang': 'en',
        'textinstructions': instruction,
        'can_no_answer': 1,  # Важно для обработки отсутствия нужных объектов
        'body': image_base64,
        'json': 1
    }

    resp = requests.post("http://2captcha.com/in.php", data=data)
    try:
        resp_json = resp.json()
    except Exception:
        text = resp.text.strip()
        if text.startswith("OK|"):
            task_id = text.split("|")[1]
        else:
            raise Exception(f"[2Captcha ERROR] Невалидный ответ при создании задачи: {text}")
    else:
        if resp_json.get('status') == 1:
            task_id = resp_json['request']
        else:
            raise Exception(f"[2Captcha ERROR] Ошибка при создании задачи: {resp_json}")

    await bot.send_message(user_id, f"[🕐] Ожидаем решение (ID: {task_id})")

    elapsed = 0
    while elapsed < timeout:
        time.sleep(retry_interval)
        elapsed += retry_interval

        result_resp = requests.get("http://2captcha.com/res.php", params={
            'key': API_TOKEN_CAPTCHA,
            'action': 'get',
            'id': task_id,
            'json': 1
        })

        try:
            result_json = result_resp.json()
        except Exception:
            text = result_resp.text.strip()
            if text.startswith("OK|"):
                raw_coords = text.split("|")[1]
                coords = await parse_coordinates(raw_coords)
                if coords == "no_answer":
                    await bot.send_message(user_id, f"[⭕️] Нет подходящих изображений (no_answer)")
                    return []
                await bot.send_message(user_id, f"[📍] Координаты получены")
                return coords
            elif text == "CAPCHA_NOT_READY":
                continue
            else:
                raise Exception(f"[2Captcha ERROR] Невалидный ответ при решении: {text}")
        else:
            if result_json.get('status') == 1:
                raw_coords = result_json['request']
                coords = await parse_coordinates(raw_coords)
                if coords == "no_answer":
                    await bot.send_message(user_id, f"[⭕️] Нет подходящих изображений (no_answer)")
                    return []
                await bot.send_message(user_id, f"[📍] Координаты получены")
                return coords
            elif result_json.get('request') == 'CAPCHA_NOT_READY':
                continue
            else:
                raise Exception(f"[2Captcha ERROR] Ошибка при решении: {result_json}")

    raise Exception("[2Captcha ERROR] Таймаут при ожидании решения")


