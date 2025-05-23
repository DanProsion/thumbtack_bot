import time
from selenium.webdriver.common.by import By
from state.FSM import RegisterState
from selenium.common.exceptions import TimeoutException
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