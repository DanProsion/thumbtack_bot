import requests
from config import API_KEY_SIM
import phonenumbers
from phonenumbers import geocoder
import time

async def buy_usa_other_number(bot, user_id, max_attempts=20, delay=3):
    headers = {
        'Authorization': f'Bearer {API_KEY_SIM}',
        'Accept': 'application/json'
    }

    try:
        # 1. Проверяем баланс
        balance_resp = requests.get('https://5sim.net/v1/user/profile', headers=headers)
        balance_resp.raise_for_status()
        profile = balance_resp.json()
        balance = profile.get('balance', 0)
        print(f"Текущий баланс: {balance}")

    except Exception as e:
        return await bot.send_message(user_id, f"❌ Не удалось получить профиль и баланс: {e}")

    # 2. Покупка номера
    for attempt in range(1, max_attempts + 1):
        try:
            # 1) Покупаем номер
            buy_url = 'https://5sim.net/v1/user/buy/activation/usa/any/other'
            buy_resp = requests.get(buy_url, headers=headers)
            buy_resp.raise_for_status()
            order = buy_resp.json()
            raw_phone = order.get('phone')
            order_id = order.get('id')

            print(f"[{attempt}] ✅ Куплен номер: {raw_phone} (order id {order_id})")

            # 2) Проверяем, что это именно US-номер
            num = phonenumbers.parse(raw_phone, None)
            country_code = geocoder.region_code_for_number(num)
            if country_code == 'US':
                print(f"[{attempt}] 🎉 Номер действительно из США.")
                return order

            # 3) Если не US — отменяем и пробуем снова
            print(f"[{attempt}] ⚠️ Номер из {country_code}, а не из US, отменяем заказ и пробуем снова…")
            cancel_url = f'https://5sim.net/v1/user/cancel/{order_id}'
            cancel_resp = requests.get(cancel_url, headers=headers)
            cancel_resp.raise_for_status()
            print(f"[{attempt}] ✅ Заказ {order_id} отменён.")

        except requests.HTTPError as http_e:
            print(f"[{attempt}] ❌ HTTPError при покупке/отмене: {http_e}")
        except Exception as e:
            print(f"[{attempt}] ❌ Общая ошибка: {e}")

        # Небольшая пауза перед новой попыткой
        time.sleep(delay)

        # Если все попытки исчерпаны
    await bot.send_message(
        user_id,
        f"🚫 Не удалось получить американский номер за {max_attempts} попыток."
    )
    return None

def get_sms_code(phone_id, max_attempts=30, delay=5):
    """
    Ожидает SMS для заказа order_id и возвращает код из первого сообщения.
    :param order_id: int или str — ID заказа, полученный при buy.
    :param max_attempts: сколько раз опрашивать API перед выходом.
    :param delay: задержка между запросами в секундах.
    :return: str with code или None, если смс не пришло.
    """
    headers = {
        'Authorization': f'Bearer {API_KEY_SIM}',
        'Accept': 'application/json'
    }
    check_url = f'https://5sim.net/v1/user/check/{phone_id}'

    for attempt in range(1, max_attempts + 1):
        print("phone_id:", phone_id)
        try:
            resp = requests.get(check_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            sms_list = data.get('sms') or data.get('smssms')  # в зависимости от типа заказа
            if sms_list:
                # Обычно sms_list — список dict с полями 'code' и 'text'
                first = sms_list[0]
                code = first.get('code') or first.get('text')
                print(f"[{attempt}] ✅ Получено SMS: {first}")
                return code
            else:
                print(f"[{attempt}] ⚠️ Ещё нет SMS, статус заказа: {data.get('status')}")
        except Exception as e:
            print(f"[{attempt}] ❌ Ошибка при проверке SMS: {e}")
        time.sleep(delay)

    print(f"🚫 За {max_attempts} попыток SMS не пришло.")
    return None

