import time
import requests
from config import API_TOKEN_CAPTCHA

# def solve_recaptcha_v2(site_key: str, url: str, timeout: int = 150, retry_interval: int = 5) -> str:
#     # 1. Создание задачи
#     create_task_resp = requests.post(
#         'https://api.capmonster.cloud/createTask',
#         json={
#             "clientKey": API_TOKEN_CAPTCHA,
#             "task": {
#                 "type": "RecaptchaV2TaskProxyless",
#                 "websiteURL": url,
#                 "websiteKey": site_key
#             }
#         }
#     )
#
#     if create_task_resp.status_code != 200:
#         raise Exception(f"[CapMonster ERROR] HTTP ошибка при создании задачи: {create_task_resp.status_code}")
#
#     create_task_data = create_task_resp.json()
#     if create_task_data.get("errorId") != 0:
#         raise Exception(f"[CapMonster ERROR] Ошибка при создании задачи: {create_task_data}")
#
#     task_id = create_task_data.get("taskId")
#     if not task_id:
#         raise Exception(f"[CapMonster ERROR] Не получен taskId: {create_task_data}")
#
#     print(f"[INFO] Задача на капчу создана, taskId={task_id}")
#
#     # 2. Ожидание результата
#     elapsed = 0
#     while elapsed < timeout:
#         time.sleep(retry_interval)
#         elapsed += retry_interval
#
#         result_resp = requests.post(
#             'https://api.capmonster.cloud/getTaskResult',
#             json={
#                 "clientKey": API_TOKEN_CAPTCHA,
#                 "taskId": task_id
#             }
#         )
#
#         if result_resp.status_code != 200:
#             raise Exception(f"[CapMonster ERROR] HTTP ошибка при получении результата: {result_resp.status_code}")
#
#         result_data = result_resp.json()
#         if result_data.get("errorId") != 0:
#             raise Exception(f"[CapMonster ERROR] Ошибка при получении результата: {result_data}")
#
#         if result_data.get("status") == "ready":
#             print(f"[INFO] Решение получено за {elapsed} секунд")
#             return result_data["solution"]["gRecaptchaResponse"]
#
#     raise Exception("[CapMonster ERROR] Время ожидания истекло (timeout)")

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
                await bot.send_message(user_id, f"[📍] Координаты получены: {raw_coords}")
                await bot.send_message(user_id, f"[🧩] Разобранные координаты: {coords}")
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
                await bot.send_message(user_id, f"[📍] Координаты получены: {raw_coords}")
                await bot.send_message(user_id, f"[🧩] Разобранные координаты: {coords}")
                return coords
            elif result_json.get('request') == 'CAPCHA_NOT_READY':
                continue
            else:
                raise Exception(f"[2Captcha ERROR] Ошибка при решении: {result_json}")

    raise Exception("[2Captcha ERROR] Таймаут при ожидании решения")


