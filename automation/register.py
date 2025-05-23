import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import base64
from io import BytesIO
from PIL import Image
from .utils import generate_name, generate_password
from .captcha import solve_grid_captcha_2captcha
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loader import init_objects

class ThumbtackRegister:
    def __init__(self, driver):
        self.driver = driver
        self.first_name = None
        self.last_name = None
        self.password = None
        self.email = None

    def human_typing(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.05))

    def clear_and_type(self, element, text):
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.1))

    def field_has_error(self, field_name):
        try:
            field = self.driver.find_element(By.NAME, field_name)
            error_container = field.find_element(
                By.XPATH, 'following-sibling::div[contains(@class, "FormNote_rootError__XZaKO")]'
            )
            return "Please fill out this field." in error_container.text
        except NoSuchElementException:
            return False

    def field_is_empty(self, field_name):
        try:
            field = self.driver.find_element(By.NAME, field_name)
            return not field.get_attribute("value").strip()
        except Exception:
            return True

    def safe_fill(self, field_name, value, retries=3):
        for _ in range(retries):
            try:
                element = self.driver.find_element(By.NAME, field_name)
                self.clear_and_type(element, value)
                time.sleep(random.uniform(0.5, 1.0))
                if not self.field_has_error(field_name) and not self.field_is_empty(field_name):
                    return True
            except Exception:
                continue
        return False

    def refill_invalid_fields(self, values_dict):
        for name, value in values_dict.items():
            try:
                element = self.driver.find_element(By.NAME, name)
                current = element.get_attribute("value").strip()

                if not current or self.field_has_error(name):
                    element.clear()
                    for char in value:
                        element.send_keys(char)
                        time.sleep(random.uniform(0.05, 0.1))
                    time.sleep(1)
            except Exception:
                continue

    def find_sitekey(self):
        # Пытаемся найти элемент с классом g-recaptcha и атрибутом data-sitekey
        try:
            recaptcha_div = self.driver.find_element(By.CSS_SELECTOR, 'div.g-recaptcha[data-sitekey]')
            sitekey = recaptcha_div.get_attribute('data-sitekey')
            if sitekey:
                return sitekey
        except:
            pass

        # Ищем iframe reCAPTCHA по URL и вытаскиваем sitekey из параметров src
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            for iframe in iframes:
                src = iframe.get_attribute('src')
                if src and 'google.com/recaptcha/api2/anchor' in src:
                    # В src параметр k=sitekey
                    import urllib.parse as urlparse
                    parsed = urlparse.urlparse(src)
                    params = urlparse.parse_qs(parsed.query)
                    if 'k' in params:
                        return params['k'][0]
        except:
            pass

        return None

    async def solve_captcha_and_submit(self, submit_btn, bot, user_id):
        captcha_attempts = 0

        def is_4x4_captcha():
            try:
                iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                )
                self.driver.switch_to.frame(iframe)
                table = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class^='rc-imageselect-table']"))
                )
                rows = table.find_elements(By.CSS_SELECTOR, "tr")
                is_4x4 = len(rows) == 4 and all(len(row.find_elements(By.CSS_SELECTOR, "td")) == 4 for row in rows)
                self.driver.switch_to.default_content()
                return is_4x4
            except Exception:
                self.driver.switch_to.default_content()
                return False

        def reload_captcha():
            try:
                iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                )
                self.driver.switch_to.frame(iframe)

                reload_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "recaptcha-reload-button"))
                )

                ActionChains(self.driver).move_to_element(reload_btn).pause(0.4).click().perform()

                self.driver.switch_to.default_content()
                return True
            except Exception as e:
                print(f"Ошибка при попытке обновить капчу: {e}")
                self.driver.switch_to.default_content()
                return False

        async def click_tiles(coords):
            try:
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                )
                self.driver.switch_to.frame(iframe)

                container = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class^='rc-imageselect-table']"))
                )
                container_location = container.location

                for point in coords:
                    if not isinstance(point, dict) or 'x' not in point or 'y' not in point:
                        continue
                    x, y = int(point['x']), int(point['y'])
                    abs_x = container_location['x'] + x
                    abs_y = container_location['y'] + y

                    ActionChains(self.driver).move_by_offset(abs_x, abs_y).click().perform()
                    ActionChains(self.driver).move_by_offset(-abs_x, -abs_y).perform()
                    time.sleep(0.3)

                selected_tiles = self.driver.find_elements(
                    By.CSS_SELECTOR, ".rc-imageselect-tile.rc-imageselect-tileselected"
                )
                selected_count = len(selected_tiles)
                await bot.send_message(user_id, f"[✅] После кликов выделено плиток: {selected_count}")

                self.driver.switch_to.default_content()
                return selected_count > 0
            except Exception as e:
                await bot.send_message(user_id, f"[❌] Ошибка при клике по координатам: {e}")
                self.driver.switch_to.default_content()
                return False

        async def click_button(btn_texts):
            try:
                iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                )
                self.driver.switch_to.frame(iframe)

                for text in btn_texts:
                    try:
                        btn = WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, f"//button[text()[contains(., '{text}')]]"))
                        )
                        btn.click()
                        self.driver.switch_to.default_content()
                        await bot.send_message(user_id, f"[🔘] Нажата кнопка: {text}")
                        return True
                    except:
                        continue

                self.driver.switch_to.default_content()
                return False
            except Exception as e:
                await bot.send_message(user_id, f"[❌] Ошибка при поиске кнопки: {e}")
                self.driver.switch_to.default_content()
                return False

        def clear_selected_tiles():
            try:
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                )
                self.driver.switch_to.frame(iframe)

                selected_tiles = self.driver.find_elements(
                    By.CSS_SELECTOR, ".rc-imageselect-tile.rc-imageselect-tileselected"
                )

                for tile in selected_tiles:
                    try:
                        tile.click()
                        time.sleep(0.2)
                    except:
                        continue

                self.driver.switch_to.default_content()
                return len(selected_tiles)
            except Exception:
                self.driver.switch_to.default_content()
                return 0

        def test_click_random_tile_and_check_selected():
            try:
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                )
                self.driver.switch_to.frame(iframe)

                tiles = self.driver.find_elements(By.CSS_SELECTOR, ".rc-imageselect-tile")
                if not tiles:
                    self.driver.switch_to.default_content()
                    return False

                tiles[0].click()
                time.sleep(0.5)
                selected_tiles = self.driver.find_elements(
                    By.CSS_SELECTOR, ".rc-imageselect-tile.rc-imageselect-tileselected"
                )
                result = len(selected_tiles) > 0

                if result:
                    tiles[0].click()  # отменяем выделение
                    time.sleep(0.2)

                self.driver.switch_to.default_content()
                return result
            except Exception:
                self.driver.switch_to.default_content()
                return False

        try:
            while True:
                if not is_4x4_captcha():
                    is_regular_captcha = test_click_random_tile_and_check_selected()
                    if not is_regular_captcha:
                        await bot.send_message(user_id, "[⚠️] Обнаружена капча с исчезающими плитками. Меняем...")
                        reload_captcha()
                        time.sleep(2)
                        return await self.solve_captcha_and_submit(submit_btn, bot, user_id)

                if captcha_attempts >= 25:
                    await bot.send_message(user_id, "[❌] Превышен лимит попыток решения капчи. Регистрация прервана.")
                    self.driver.quit()
                    return

                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                )
                self.driver.switch_to.frame(iframe)

                try:
                    instruction_elem = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".rc-imageselect-desc-no-canonical strong"))
                    )
                    instruction = f"Выберите все изображения, где есть {instruction_elem.text}"
                    await bot.send_message(user_id, f"[ℹ️] Инструкция к капче: {instruction}")
                except:
                    instruction = "Click on all images matching the label"
                    await bot.send_message(user_id, "[⚠️] Используем стандартную инструкцию.")

                try:
                    captcha_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class^='rc-imageselect-table']"))
                    )
                    image_base64 = captcha_element.screenshot_as_base64
                    await bot.send_message(user_id, "[📸] Скриншот капчи получен.")
                except Exception as e:
                    await bot.send_message(user_id, f"[❌] Не удалось получить изображение капчи: {e}")
                    self.driver.switch_to.default_content()
                    return
                finally:
                    self.driver.switch_to.default_content()

                captcha_attempts += 1

                coords = await solve_grid_captcha_2captcha(image_base64, instruction, bot, user_id)

                if not coords:
                    await bot.send_message(user_id,
                                           f"[⚠️] Пустой ответ от 2Captcha (попытка {captcha_attempts}/10). Обновляем капчу...")
                    reload_captcha()
                    time.sleep(1)
                    continue

                selected_any = await click_tiles(coords)
                if not selected_any:
                    await bot.send_message(user_id, "[♻️] Ни один тайл не выделился — нажимаем кнопку обновления.")
                    reload_captcha()
                    time.sleep(1)
                    continue

                clicked = await click_button(["Пропустить", "Далее", "Подтвердить"])
                if not clicked:
                    await bot.send_message(user_id,
                                           f"[⏳] Кнопка не найдена (попытка {captcha_attempts}/10). Проверим, исчезла ли капча...")

                try:
                    WebDriverWait(self.driver, 5).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                    )
                    await bot.send_message(user_id, "[✅] Капча успешно решена.")
                    break
                except:
                    cleared = clear_selected_tiles()
                    await bot.send_message(user_id, f"[🔁] Капча не исчезла. Снято {cleared} плиток. Повторяем...")
                    time.sleep(1)

            await bot.send_message(user_id, "[🚀] Форма отправлена.")

        except Exception as e:
            await bot.send_message(user_id, f"[❌] Общая ошибка при решении капчи: {e}")
            self.driver.quit()

    # Метод для получения base64 скриншота всей сетки капчи
    def get_captcha_grid_base64(self):
        iframe = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
        )
        self.driver.switch_to.frame(iframe)

        container = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "rc-imageselect-table-33"))
        )

        png = self.driver.get_screenshot_as_png()
        im = Image.open(BytesIO(png))

        location = container.location_once_scrolled_into_view
        size = container.size

        # Учитываем DPI и масштаб страницы
        # Иногда нужно умножать координаты на devicePixelRatio, но можно проверить по факту

        left = int(location['x'])
        top = int(location['y'])
        right = left + int(size['width'])
        bottom = top + int(size['height'])

        im_cropped = im.crop((left, top, right, bottom))

        buffered = BytesIO()
        im_cropped.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        self.driver.switch_to.default_content()
        return img_base64

    async def start_register(self, bot, user_id, zip_code, service_name, state):
        # Генерируем данные
        self.first_name, self.last_name = generate_name()
        self.password = generate_password()
        self.email = f"{self.first_name}sas{self.last_name}{random.randint(1000, 9999)}@gmail.com"

        await bot.send_message(user_id, f"[👤] Имя: {self.first_name} {self.last_name}")
        await bot.send_message(user_id, f"[✉️] Email: {self.email}")
        await bot.send_message(user_id, f"[🔐] Пароль: {self.password}")

        self.driver.get("https://www.thumbtack.com/register")

        WebDriverWait(self.driver, 90).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        google_btn_locator = (By.CSS_SELECTOR, "div.mv1 button")
        WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable(google_btn_locator)
        )

        time.sleep(15)

        fields = {
            "usr_first_name": self.first_name,
            "usr_last_name": self.last_name,
            "usr_email": self.email,
            "usr_password": self.password,
        }

        for field_name, value in fields.items():
            if not self.safe_fill(field_name, value):
                await bot.send_message(user_id, f"[❌] Не удалось ввести поле: {field_name}")

        self.driver.execute_script("window.scrollBy(0, 300);")
        ActionChains(self.driver).move_by_offset(random.randint(100, 300), random.randint(100, 300)).perform()
        self.refill_invalid_fields(fields)

        errors = [f for f in fields if self.field_has_error(f) or self.field_is_empty(f)]
        if errors:
            await bot.send_message(user_id, f"[⚠️] Ошибка при вводе полей: {', '.join(errors)}. Форма не отправлена.")
            return

        try:
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            time.sleep(2)

            # Проверка: редирект на главную — капчи нет
            try:
                WebDriverWait(self.driver, 20).until(EC.url_to_be("https://www.thumbtack.com/"))
                await bot.send_message(user_id, "[✅] Регистрация прошла без капчи.")
            except TimeoutException:
                # Проверка на наличие капчи
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='bframe']"))
                    )
                    await bot.send_message(user_id, "[🧩] Обнаружена капча. Начинаем решение...")
                    await self.solve_captcha_and_submit(submit_btn, bot, user_id)
                except TimeoutException:
                    await bot.send_message(user_id, "[ℹ️] Капча не обнаружена и редиректа нет. Возможно, ошибка.")

            # Ожидаем успешный редирект после решения капчи
            WebDriverWait(self.driver, 240).until(EC.url_to_be("https://www.thumbtack.com/"))
            WebDriverWait(self.driver, 120).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "input[data-test='search-input']")
            ))

            await bot.send_message(user_id, "[✅] Аккаунт успешно зарегистрирован.")
            await init_objects.company_search_flow.start_company(
                self.human_typing, bot, user_id, zip_code, service_name, state
            )

        except TimeoutException:
            await bot.send_message(user_id, "[❌] Не удалось подтвердить регистрацию: редирект на главную не произошёл.")
        except Exception as e:
            await bot.send_message(user_id, f"[❌] Ошибка при регистрации: {e}")