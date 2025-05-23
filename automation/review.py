import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException, TimeoutException
import re
import time
import random
from .sim import buy_usa_other_number, get_sms_code

class ProjectCreationHandler:
    def __init__(self, driver):
        self.driver = driver

    async def start_project(self, bot, user_id):
        try:
            container_selector = 'div.bg-white.flex.flex-column.h-100'
            await bot.send_message(user_id, "[🚀] Начинаем заполнение формы проекта...")

            await self.click_button_by_possible_texts(["Check availability", "Request a quote"], bot, user_id)
            await self.wait_for_element('div._140H21lwAyAeUjSFeiJkgI')
            await asyncio.sleep(1)
            await self.scroll_down(bot, user_id)

            while True:
                await self.handle_next_skip(container_selector, bot, user_id)
                await self.handle_radio_buttons(container_selector)
                await self.handle_checkboxes(container_selector)
                if await self.handle_phone_step(container_selector, bot, user_id):
                    break
                await asyncio.sleep(1)

            await bot.send_message(user_id, "[✅] Форма успешно заполнена. Все данные отправлены")

        except Exception as e:
            await bot.send_message(user_id, f"[❌] Ошибка при создании проекта: {str(e)}")

    async def scroll_down(self, bot, user_id):
        try:
            self.driver.execute_script("window.scrollBy(0, 300);")
            await asyncio.sleep(0.3)
        except Exception as e:
            await bot.send_message(user_id, f"Ошибка при скролле: {e}")

    async def click_button_by_possible_texts(self, possible_texts, bot, user_id):
        try:
            aside_xpath = "//aside[contains(@class, 'z-1') and contains(@class, '_2rBAXAM49yzLBGWgkhc3vi')]"
            aside = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, aside_xpath))
            )

            for text in possible_texts:
                try:
                    button_xpath = f".//button[.//span[contains(text(), '{text}')]]"
                    buttons = aside.find_elements(By.XPATH, button_xpath)
                    for el in buttons:
                        if el.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                            await asyncio.sleep(0.3)
                            try:
                                el.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", el)
                            return True
                except Exception:
                    continue
            await bot.send_message(user_id, f"❌ Не удалось найти кнопку с текстом из: {possible_texts} внутри aside")
            return False
        except Exception as e:
            await bot.send_message(user_id, f"❌ Ошибка при поиске aside или кнопки внутри него: {e}")
            return False

    async def click_buttons_by_text(self, texts, bot, user_id, retries=5, delay=3):
        if isinstance(texts, str):
            texts = [texts]

        try:
            for attempt in range(1, retries + 1):
                for text in texts:
                    xpath = f"//button[.//span[normalize-space(text())='{text}']]"
                    buttons = self.driver.find_elements(By.XPATH, xpath)

                    if not buttons:
                        print(f"[{attempt}] 🔍 Кнопка '{text}' не найдена.")
                        continue

                    print(f"[{attempt}] 🔍 Найдено {len(buttons)} кнопок с текстом '{text}'")
                    for idx, el in enumerate(buttons, start=1):
                        if not el.is_displayed():
                            print(f"[{attempt}] ⏭️ Кнопка #{idx} с текстом '{text}' не отображается")
                            continue

                        print(f"[{attempt}] ▶️ Попытка кликнуть по кнопке #{idx} с текстом '{text}'")
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                            await asyncio.sleep(0.3)
                            try:
                                el.click()
                                print(f"[{attempt}] ✅ Успешно кликнули (обычный click) по кнопке '{text}'")
                                return True
                            except Exception as click_e:
                                print(f"[{attempt}] ⚠️ Обычный click не сработал: {click_e}")
                                self.driver.execute_script("arguments[0].click();", el)
                                print(f"[{attempt}] ✅ Успешно кликнули (JS click) по кнопке '{text}'")
                                return True
                        except Exception as e_click:
                            print(f"[{attempt}] ❌ Ошибка при клике по кнопке #{idx} с текстом '{text}': {e_click}")
                            continue

                if attempt < retries:
                    print(f"[{attempt}] ⚠️ Не удалось нажать ни по одной кнопке из {texts}, повтор через {delay}s...")
                    time.sleep(delay)

            await bot.send_message(
                user_id,
                f"❌ Не удалось кликнуть ни по одной кнопке ({', '.join(texts)}) после {retries} попыток"
            )
            return False

        except Exception as e:
            await bot.send_message(user_id, f"❌ Общая ошибка при поиске/клике кнопок {texts}: {e}")
            print(f"❌ Общая ошибка: {e}")
            return False

    async def click_random_option_from_container(self, container_selector, max_attempts=5):
        wait = WebDriverWait(self.driver, 60)

        for attempt in range(1, max_attempts + 1):
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, container_selector)))
                containers = self.driver.find_elements(By.CSS_SELECTOR, container_selector)
                if not containers:
                    print("❌ Контейнеры не найдены.")
                    return

                valid_labels = []

                for container in containers:
                    try:
                        subblocks = container.find_elements(By.CSS_SELECTOR, 'div[class*="_2m08zU26ib4"]')
                        if not subblocks:
                            subblocks = container.find_elements(By.CSS_SELECTOR, 'div.bg-white.bb.b-gray-300')
                    except Exception:
                        continue

                    for block in subblocks:
                        try:
                            labels = block.find_elements(By.CSS_SELECTOR, 'label')
                            for label in labels:
                                text = label.text.strip()
                                if not text or 'Specific dates' in text:
                                    continue
                                if label.find_elements(By.CSS_SELECTOR, 'input[type="text"]'):
                                    continue

                                for input_type in ["checkbox", "radio"]:
                                    inputs = label.find_elements(By.CSS_SELECTOR, f'input[type="{input_type}"]')
                                    if inputs:
                                        valid_labels.append((label, inputs[0], input_type))
                                        break
                        except Exception:
                            continue

                if not valid_labels:
                    print("❌ Не найдено ни одной валидной метки.")
                    return

                label, input_elem, input_type = random.choice(valid_labels)
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                await asyncio.sleep(0.3)

                try:
                    label.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", label)
                await asyncio.sleep(0.3)

                try:
                    if input_type == "radio":
                        wait.until(lambda d: input_elem.is_selected() or input_elem.get_attribute("checked") == "true")
                    elif input_type == "checkbox":
                        wait.until(
                            lambda d: input_elem.is_selected() or input_elem.get_attribute("aria-checked") == "true")
                except TimeoutException:
                    pass

                selected = (
                    (input_type == "radio" and (input_elem.is_selected() or input_elem.get_attribute("checked") == "true"))
                    or
                    (input_type == "checkbox" and input_elem.get_attribute("aria-checked") == "true")
                )

                if selected:
                    print(f"✅ Успешный клик по «{label.text.strip()}» на попытке {attempt}")
                    return
                else:
                    print(f"⚠️ Вариант «{label.text.strip()}» не выбран, повторяем…")

            except StaleElementReferenceException:
                print(f"⚠️ StaleElementReference на попытке {attempt}, повторяем…")
            except TimeoutException:
                print(f"⚠️ Timeout при загрузке элементов на попытке {attempt}")
            except Exception as e:
                print(f"⚠️ Ошибка на попытке {attempt}: {e}")

            time.sleep(1)

        print(f"❌ Не удалось выбрать вариант за {max_attempts} попыток.")

    async def sim_phone_numbers(self, bot, user_id):
        # Ваша функция buy_usa_other_number должна быть определена где-то
        order = await buy_usa_other_number(bot, user_id)
        if not order:
            return

        raw_phone = order.get('phone', '')
        phone_id = order.get('id', '')

        if not raw_phone:
            await bot.send_message(user_id, "❌ Не вернулся номер телефона в ответе от API.")
            return

        digits = re.sub(r'\D', '', raw_phone)
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        if len(digits) != 10:
            await bot.send_message(user_id, f"❌ После обработки получилось не 10 цифр: {digits}")
            return

        try:
            wait = WebDriverWait(self.driver, 20)
            phone_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[type="tel"][data-test="request-flow-text-box"]')
            ))

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", phone_input)
            time.sleep(0.3)
            phone_input.clear()
            phone_input.send_keys(digits)
            time.sleep(0.5)

            await bot.send_message(user_id, f"[📱] Введён номер телефона: {digits}")
            if not phone_id:
                await bot.send_message(user_id, f"[❌] Не найдена телефона")
                return
            return phone_id
        except Exception as e:
            await bot.send_message(user_id, f"❌ Не удалось ввести номер телефона: {e}")
            return

    async def enter_sms_code(self, bot, user_id, order_id, max_attempts=20, delay=5):
        # get_sms_code должна быть определена где-то
        code = get_sms_code(order_id, max_attempts=max_attempts, delay=delay)
        if not code:
            await bot.send_message(user_id, f"🚫 Не удалось получить SMS-код за {max_attempts} попыток.")
            return False

        digits = re.sub(r'\D', '', code)
        if not digits:
            await bot.send_message(user_id, f"❌ В SMS не найдено цифр: {code}")
            return False

        try:
            wait = WebDriverWait(self.driver, 30)
            sms_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[data-test="request-flow-text-box"][placeholder="4-digit code"]'))
            )

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sms_input)
            await asyncio.sleep(0.3)
            sms_input.clear()
            sms_input.send_keys(digits)
            await asyncio.sleep(0.5)

            await bot.send_message(user_id, f"[🔢] Введён SMS-код: {digits}")
            return True

        except Exception as e:
            await bot.send_message(user_id, f"❌ Не удалось ввести SMS-код: {e}")
            return False

    async def select_random_checkbox(self):
        labels = self.driver.find_elements(By.CSS_SELECTOR, 'label._1T_KGYTSCiM4smv35ppVFb')
        if not labels:
            print("Не найдено ни одного чекбокса.")
            return False

        labels = labels[:]  # копия списка для безопасного удаления

        while labels:
            label = random.choice(labels)
            labels.remove(label)

            # Найдём вложенный input[type="checkbox"] внутри label
            try:
                checkbox = label.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
            except Exception:
                checkbox = None

            # 5 попыток кликнуть по одному элементу разными способами
            for attempt in range(5):
                try:
                    # Скроллим к label
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                    time.sleep(0.2)  # небольшой таймаут, чтобы страница подстроилась

                    # Попытка 1: стандартный click() по label
                    label.click()
                    return True
                except Exception as e1:
                    try:
                        # Попытка 2: JS клик по label
                        self.driver.execute_script("arguments[0].click();", label)
                        return True
                    except Exception as e2:
                        if checkbox:
                            try:
                                # Попытка 3: JS клик по чекбоксу
                                self.driver.execute_script("arguments[0].click();", checkbox)
                                return True
                            except Exception as e3:
                                pass
                # Если не удалось, подождём немного и повторим попытку
                time.sleep(0.3)

        print("Не удалось кликнуть ни по одному чекбоксу.")
        return False

    def element_exists_within_container(self, container_selector: str, element_selector: str) -> bool:
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, container_selector)
            elements = container.find_elements(By.CSS_SELECTOR, element_selector)
            return any(e.is_displayed() for e in elements)
        except Exception:
            return False

    async def wait_for_element(self, selector, timeout=10):
        wait = WebDriverWait(self.driver, timeout)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            pass

    async def handle_next_skip(self, container_selector, bot, user_id):
        if any(self.text_exists_within_container(container_selector, t) for t in ["Next", "Skip"]):
            print("Зациклились на 1")
            await self.click_buttons_by_text(["Next", "Skip"], bot, user_id)
            return True
        return False

    async def handle_radio_buttons(self, container_selector):
        if self.element_exists_within_container(container_selector, 'div.XL2ul0WqP7EQIqn1U5rlZ'):
            if self.element_exists_within_container(container_selector, 'div._2m08zU26ib4_Kp9OU_PA07'):
                print("Зациклились на 2 (селекторы)")
                await self.click_random_option_from_container('div.XL2ul0WqP7EQIqn1U5rlZ')
                return True
        return False

    async def handle_checkboxes(self, container_selector):
        if self.element_exists_within_container(container_selector, 'label._1T_KGYTSCiM4smv35ppVFb'):
            print("Зациклились на 3 (чекбоксы)")
            await self.select_random_checkbox()
            return True
        return False

    def text_exists_within_container(self, container_selector: str, text: str) -> bool:
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, container_selector)
            elements = container.find_elements(By.XPATH, f".//*[contains(text(), '{text}')]")
            return any(e.is_displayed() for e in elements)
        except Exception:
            return False

    async def handle_phone_step(self, container_selector, bot, user_id):
        while True:
            # Строгая проверка: должен быть явный заголовок шага
            if not self.text_exists_within_container(container_selector, "Review the zip and add your contact info"):
                return False
            if not self.text_exists_within_container(container_selector, "Submit"):
                return False
            if not self.text_exists_within_container(container_selector, "Double-check your zip!"):
                return False
            if not self.element_exists_within_container(container_selector, "div._3sVWix2Rl9SVKK2_CV-T0r"):
                return False

            # Проверка, что поле для телефона реально отображается
            phone_label_present = self.text_exists_within_container(container_selector, "Phone number")
            phone_input_present = self.is_phone_input_present()

            if phone_label_present and phone_input_present:
                print("Зациклились на 4 (этап с телефоном)")
                phone_id = await self.sim_phone_numbers(bot, user_id)

                # Попытка нажать "Submit" или "Next"
                click = await self.click_buttons_by_text(["Submit", "Next"], bot, user_id)
                if not click:
                    continue

                # Ввод кода
                await self.enter_sms_code(phone_id, bot, user_id)

                # Подтверждение номера
                click = await self.click_buttons_by_text(["Verify"], bot, user_id)
                if not click:
                    continue

                return True
            return False

    def is_phone_input_present(self) -> bool:
        return len(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="tel"][autocomplete="tel"]')) > 0

