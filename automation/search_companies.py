import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from .utils import wait_for_element
# from sms_service import get_phone_number, get_sms_code
from state.FSM import RegisterState
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loader import init_objects

class CompanySearchFlow:
    NEXT_BTN_CSS = (
        'section.flex.flex-column.flex-1.s_justify-start.pv3.ph3.s_ph5.overflow-y-auto '
        'button._1iRY-9hq7N_ErfzJ6CdfXn'
    )
    CARD_CSS = "[data-testid='pro-list-result']"
    NAME_CSS = ".IUE7kXgIsvED2G8vml4Wu, .Z4pkQxpLz9qpVDR7jJHjW"
    STOP_WORDS = {"highly", "rated", "frequently", "hired", "top", "pro", "recommended", "fastest", "response"}

    def __init__(self, driver):
        self.driver = driver

    def wait_for_element(self, by, selector, timeout=20):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def _skip_three_forms(self, timeout: int = 6):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, self.NEXT_BTN_CSS))
            )
            for _ in range(3):
                next_btn = self.driver.find_element(By.CSS_SELECTOR, self.NEXT_BTN_CSS)
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                next_btn.click()
                WebDriverWait(self.driver, timeout).until_not(EC.staleness_of(next_btn))
        except TimeoutException:
            pass

    def _close_popups(self):
        for _ in range(10):
            try:
                skip_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button//div[text()='Skip']"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", skip_button)
                self.driver.execute_script("arguments[0].click();", skip_button)
                time.sleep(0.5)
            except TimeoutException:
                break
            except Exception:
                break

    def _extract_company_name(self, card):
        lbl = card.get_attribute("aria-label")
        if lbl and not any(w in lbl.lower() for w in self.STOP_WORDS):
            return lbl.strip()
        for el in card.find_elements(By.CSS_SELECTOR, self.NAME_CSS):
            txt = el.text.strip()
            if txt and not any(w in self.STOP_WORDS for w in txt.lower().split()):
                return txt
        return None

    async def start_company(self, human_typing, bot, user_id, zip_code, service_name, state):
        try:
            await bot.send_message(user_id, "[⌛] Начинаем поиск компаний...")
            time.sleep(2)

            service_input = self.wait_for_element(By.CSS_SELECTOR, 'input[data-test="search-input"]')
            service_input.clear()
            human_typing(service_input, service_name)
            time.sleep(0.2)

            try:
                first_option = self.wait_for_element(By.CSS_SELECTOR, "ul > li:first-child", timeout=5)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", first_option)
                first_option.click()
            except Exception:
                pass

            zip_input = self.wait_for_element(By.NAME, "zip_code")
            zip_input.clear()
            human_typing(zip_input, zip_code)
            time.sleep(0.2)

            search_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="search-button"]'))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
            time.sleep(1)
            try:
                search_button.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", search_button)

            self._skip_three_forms()
            await bot.send_message(user_id, "[📍] Ищем компании по заданным параметрам...")

            try:
                WebDriverWait(self.driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.CARD_CSS))
                )
            except TimeoutException:
                await bot.send_message(user_id, "[❌] Компании не найдены (таймаут).")
                return

            time.sleep(2)
            self._close_popups()

            prev_cnt = 0
            while True:
                cards = self.driver.find_elements(By.CSS_SELECTOR, self.CARD_CSS)
                if len(cards) == prev_cnt:
                    break
                prev_cnt = len(cards)
                self.driver.execute_script("arguments[0].scrollIntoView({block:'end',behavior:'instant'});", cards[-1])
                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, self.CARD_CSS)) > prev_cnt
                    )
                except TimeoutException:
                    break

            cards = self.driver.find_elements(By.CSS_SELECTOR, self.CARD_CSS)
            company_names = []
            for card in cards:
                name = self._extract_company_name(card)
                if name and name not in company_names:
                    company_names.append(name)

            if not company_names:
                await bot.send_message(user_id, "[❌] Не удалось извлечь имена компаний.")
                return

            companies_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(company_names))
            await bot.send_message(
                user_id,
                f"[🏢] Найдены компании:\n{companies_text}\n\nНапишите номер компании для выбора."
            )

            await state.update_data({
                "driver": self.driver,
                "company_names": company_names,
                "zip_code": zip_code,
                "service_name": service_name
            })
            await state.set_state(RegisterState.waiting_for_company_number)

        except Exception as e:
            await bot.send_message(user_id, f"[❌] Ошибка поиска компаний: {str(e)}")

    async def handle_company_selection(self, bot, user_id, message_text, state):
        try:
            data = await state.get_data()
            company_names = data.get("company_names")
            if not company_names:
                await bot.send_message(user_id, "[❌] Не удалось найти список компаний.")
                return

            index = int(message_text.strip()) - 1
            target_name = company_names[index]
            await bot.send_message(user_id, f"[👣] Ищем карточку компании: {target_name}")

            cards = self.driver.find_elements(By.CSS_SELECTOR, self.CARD_CSS)

            for card in cards:
                name = self._extract_company_name(card)
                if name == target_name:
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                        time.sleep(0.5)

                        outer_container = card.find_element(By.XPATH,
                            ".//ancestor::div[contains(@class, 'bg-white') and contains(@class, 'mb0') and contains(@class, 'shadow-200')]"
                        )
                        link = outer_container.find_element(By.TAG_NAME, "a")
                        href = link.get_attribute("href")

                        if not href:
                            raise Exception("Не удалось извлечь ссылку")

                        self.driver.get(href)

                        await bot.send_message(user_id, f"[✅] Открыли страницу компании «{target_name}»")
                        await init_objects.project_creation_handler.start_project(bot, user_id)
                        return

                    except Exception as e:
                        await bot.send_message(user_id, f"[❌] Ошибка при открытии ссылки: {e}")
                        return

            await bot.send_message(user_id, "[❌] Не удалось найти карточку выбранной компании.")
        except Exception as e:
            await bot.send_message(user_id, f"[❌] Ошибка при выборе компании: {str(e)}")

    async def continue_registration_flow(self, bot, user_id: int):
        try:
            await bot.send_message(user_id, "[✅] Регистрация завершена.")
        except Exception as e:
            await bot.send_message(user_id, f"[❌] Ошибка после выбора компании: {e}")






# NEXT_BTN_CSS = (
#     'section.flex.flex-column.flex-1.s_justify-start.pv3.ph3.s_ph5.overflow-y-auto '
#     'button._1iRY-9hq7N_ErfzJ6CdfXn'
# )
#
# def skip_three_forms(driver, timeout: int = 6):
#     """
#     Если после поиска появляется промежуточная форма‑«волшебник»,
#     трижды жмём Next и ждём, пока секция исчезнет.
#     """
#     try:
#         # Секция появляется всегда; ждём её 1‑й раз
#         WebDriverWait(driver, timeout).until(
#             EC.visibility_of_element_located((By.CSS_SELECTOR, NEXT_BTN_CSS))
#         )
#
#         for _ in range(3):
#             next_btn = driver.find_element(By.CSS_SELECTOR, NEXT_BTN_CSS)
#             driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
#             next_btn.click()
#             # Ждём либо исчезновения текущей кнопки, либо появления новой
#             WebDriverWait(driver, timeout).until_not(
#                 EC.staleness_of(next_btn)
#             )
#     except TimeoutException:
#         # Форма не появилась — значит, нам и не нужно ничего нажимать
#         pass
#
# async def after_registration_flow(driver, human_typing, bot, user_id,
#                                   zip_code: str, service_name: str, state):
#     try:
#
#         await bot.send_message(user_id, "[⌛] Начинаем поиск компаний...")
#         time.sleep(2)
#
#         # Ввод сервиса
#         service_input = wait_for_element(driver, By.CSS_SELECTOR, 'input[data-test="search-input"]')
#         service_input.clear()
#         human_typing(service_input, service_name)
#         time.sleep(0.2)
#
#         # Клик по первому варианту из выпадающего списка
#         try:
#             first_option = wait_for_element(driver, By.CSS_SELECTOR, "ul > li:first-child", timeout=5)
#             driver.execute_script("arguments[0].scrollIntoView(true);", first_option)
#             first_option.click()
#         except Exception:
#             pass
#
#         time.sleep(0.2)
#
#         # Ввод zip-кода
#         zip_input = wait_for_element(driver, By.NAME, "zip_code")
#         zip_input.clear()
#         human_typing(zip_input, zip_code)
#         time.sleep(0.2)
#
#         # Нажатие кнопки поиска
#         search_button = WebDriverWait(driver, 20).until(
#             EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="search-button"]'))
#         )
#         driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
#         time.sleep(1)
#         try:
#             search_button.click()
#         except Exception:
#             driver.execute_script("arguments[0].click();", search_button)
#
#         # Пропускаем промежуточные формы
#         skip_three_forms(driver)
#
#         await bot.send_message(user_id, "[📍] Ищем компании по заданным параметрам...")
#
#         CARD_CSS = "[data-testid='pro-list-result']"
#         NAME_CSS = ".IUE7kXgIsvED2G8vml4Wu, .Z4pkQxpLz9qpVDR7jJHjW"
#         STOP_WORDS = {"highly", "rated", "frequently", "hired",
#                       "top", "pro", "recommended", "fastest", "response"}
#
#         # Ждём появления карточек
#         try:
#             WebDriverWait(driver, 60).until(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, CARD_CSS))
#             )
#         except TimeoutException:
#             await bot.send_message(user_id, "[❌] Компании не найдены (таймаут).")
#             return
#
#         def close_popup_if_present(driver):
#             """Закрывает до 3 всплывающих окон, нажимая кнопку 'Skip'."""
#             for _ in range(10):
#                 try:
#                     skip_button = WebDriverWait(driver, 5).until(
#                         EC.element_to_be_clickable((By.XPATH, "//button//div[text()='Skip']"))
#                     )
#                     driver.execute_script("arguments[0].scrollIntoView(true);", skip_button)
#                     driver.execute_script("arguments[0].click();", skip_button)
#                     time.sleep(0.5)
#                 except TimeoutException:
#                     break
#                 except Exception as e:
#                     print(f"Ошибка при попытке закрытия попапа: {e}")
#                     break
#
#         time.sleep(2)
#         close_popup_if_present(driver)
#
#         prev_cnt = 0
#         while True:
#             cards = driver.find_elements(By.CSS_SELECTOR, CARD_CSS)
#             if len(cards) == prev_cnt:
#                 break
#             prev_cnt = len(cards)
#             driver.execute_script("arguments[0].scrollIntoView({block:'end',behavior:'instant'});", cards[-1])
#             try:
#                 WebDriverWait(driver, 5).until(
#                     lambda d: len(d.find_elements(By.CSS_SELECTOR, CARD_CSS)) > prev_cnt
#                 )
#             except TimeoutException:
#                 break
#
#         cards = driver.find_elements(By.CSS_SELECTOR, CARD_CSS)
#
#         def extract_company_name(card) -> str | None:
#             lbl = card.get_attribute("aria-label")
#             if lbl and not any(w in lbl.lower() for w in STOP_WORDS):
#                 return lbl.strip()
#             for el in card.find_elements(By.CSS_SELECTOR, NAME_CSS):
#                 txt = el.text.strip()
#                 if txt and not any(w in STOP_WORDS for w in txt.lower().split()):
#                     return txt
#             return None
#
#         company_names = []
#         for card in cards:
#             name = extract_company_name(card)
#             if name and name not in company_names:
#                 company_names.append(name)
#
#         if not company_names:
#             await bot.send_message(user_id, "[❌] Не удалось извлечь имена компаний.")
#             return
#
#         companies_text = "\n".join(f"{i + 1}. {n}" for i, n in enumerate(company_names))
#         await bot.send_message(
#             user_id,
#             f"[🏢] Найдены компании:\n{companies_text}\n\nНапишите номер компании для выбора."
#         )
#
#         await state.update_data({
#             "driver": driver,
#             "company_names": company_names,
#             "zip_code": zip_code,
#             "service_name": service_name
#         })
#         await state.set_state(RegisterState.waiting_for_company_number)
#
#     except Exception as e:
#         await bot.send_message(user_id, f"[❌] Ошибка поиска компаний: {str(e)}")
#
# async def handle_company_selection(bot, user_id, message_text, state):
#     try:
#         data = await state.get_data()
#         company_names = data.get("company_names")
#         driver = data.get("driver")
#         if not company_names:
#             await bot.send_message(user_id, "[❌] Не удалось найти список компаний.")
#             return
#
#         index = int(message_text.strip()) - 1
#         target_name = company_names[index]
#         await bot.send_message(user_id, f"[👣] Ищем карточку компании: {target_name}")
#
#         CARD_CSS = "[data-testid='pro-list-result']"
#         NAME_CSS = ".IUE7kXgIsvED2G8vml4Wu, .Z4pkQxpLz9qpVDR7jJHjW"
#         OUTER_CONTAINER_CSS = "div.bg-white.mb0.m_mb2.bb.b-gray-300.bn.b-gray-300.shadow-200.br3"
#
#         cards = driver.find_elements(By.CSS_SELECTOR, CARD_CSS)
#
#         def extract_company_name(card) -> str | None:
#             lbl = card.get_attribute("aria-label")
#             if lbl:
#                 return lbl.strip()
#             for el in card.find_elements(By.CSS_SELECTOR, NAME_CSS):
#                 txt = el.text.strip()
#                 if txt:
#                     return txt
#             return None
#
#         for card in cards:
#             name = extract_company_name(card)
#             if name == target_name:
#                 try:
#                     driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
#                     time.sleep(0.5)
#
#                     try:
#                         outer_container = card.find_element(By.XPATH,
#                                                             ".//ancestor::div[contains(@class, 'bg-white') and contains(@class, 'mb0') and contains(@class, 'shadow-200')]")
#
#                         link = outer_container.find_element(By.TAG_NAME, "a")
#                         href = link.get_attribute("href")
#
#                         if not href:
#                             raise Exception("Не удалось извлечь ссылку")
#
#                         # Вместо открытия новой вкладки, просто переходим по ссылке в текущей
#                         driver.get(href)
#
#                         await bot.send_message(user_id, f"[✅] Открыли страницу компании «{target_name}»")
#                         await handle_project_creation(bot, user_id, driver)
#                         return
#                     except Exception as e:
#                         await bot.send_message(user_id, f"[❌] Ошибка при открытии ссылки: {e}")
#                         return
#
#                 except Exception as e:
#                     await bot.send_message(user_id, f"[❌] Не удалось обработать карточку: {e}")
#                     return
#
#         await bot.send_message(user_id, "[❌] Не удалось найти карточку выбранной компании.")
#     except Exception as e:
#         await bot.send_message(user_id, f"[❌] Ошибка при выборе компании: {str(e)}")
#
#
# async def continue_registration_flow(bot, user_id: int):
#     try:
#         bot.send_message(user_id, "[✅] Регистрация завершена.")
#     except Exception as e:
#         bot.send_message(user_id, f"[❌] Ошибка после выбора компании: {e}")